"""Natural language transaction handler using AI service."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import google.generativeai as genai
from telegram import Update, constants
from telegram.ext import ContextTypes

from bot.common import get_logger, log_handler_invocation
from bot.services.ai_service import get_ai_service
from bot.services.analytics_service import get_analytics_service
from bot.services.categories import create_default_categories, fetch_user_categories
from bot.utils.amounts import format_currency
from bot.utils.time_utils import convert_utc_to_local, get_now_utc
from database import SessionLocal
from models import Category, Transaction

logger = get_logger("handlers.natural_language")


def _process_ai_date(date_str: str) -> tuple[datetime, datetime.date]:
    """Process date string from AI and convert to datetime UTC with timezone handling.
    
    This function handles the conversion of date strings from AI responses to datetime
    objects, ensuring proper timezone handling (Colombia timezone) and preserving
    exact time for "today" dates.
    
    Logic:
    - If AI date == today in Colombia: Use current UTC datetime (preserves exact time)
    - If AI date is different (yesterday, etc.): Use that date at noon UTC
    
    Args:
        date_str: Date string in YYYY-MM-DD format from AI response
    
    Returns:
        Tuple of (transaction_date: datetime UTC-aware, transaction_date_obj: date)
    """
    try:
        # Parse date string to date object
        ai_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Get current time in Colombia timezone
        now_utc = get_now_utc()
        now_colombia = convert_utc_to_local(now_utc, "America/Bogota")
        today_colombia = now_colombia.date()
        
        # If AI date is today in Colombia, use exact current time
        if ai_date == today_colombia:
            # Use current UTC datetime (preserves exact time for chronological order)
            transaction_date = now_utc
            transaction_date_obj = ai_date
            logger.debug(
                "AI date is today in Colombia, using exact current time: %s",
                transaction_date
            )
        else:
            # For other dates, use noon UTC to avoid timezone edge cases
            transaction_date = datetime.combine(
                ai_date,
                datetime.min.time().replace(hour=12),  # Noon UTC
                tzinfo=timezone.utc
            )
            transaction_date_obj = ai_date
            logger.debug(
                "AI date is not today, using noon UTC: %s",
                transaction_date
            )
        
        return transaction_date, transaction_date_obj
    
    except ValueError as e:
        logger.error("Invalid date format from AI: %s", date_str)
        # Fallback to current date with exact time
        now_utc = get_now_utc()
        return now_utc, now_utc.date()


def _classify_intent(text: str) -> str:
    """Classify if user wants to REGISTER a transaction or QUERY financial data.
    
    Args:
        text: User's message text
    
    Returns:
        "register" or "query" based on classification
    
    Raises:
        RuntimeError: If classification fails
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not configured")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    prompt = f"""Eres un clasificador de intenciones para un bot financiero. Tu trabajo es determinar si el usuario quiere REGISTRAR una transacción o CONSULTAR información financiera.

MENSAJE DEL USUARIO: "{text}"

INSTRUCCIONES:
- Si el usuario quiere REGISTRAR un gasto o ingreso (ej: "Gaste 20k", "Gaste 50 lucas en comida", "Recibí 1 palo"), responde: "register"
- Si el usuario quiere CONSULTAR información (ej: "¿Cuánto gasté?", "¿Cuánto gasté en comida?", "Muéstrame mis gastos del mes", "¿Cuántas transacciones tengo?"), responde: "query"
- Si es ambiguo o no está claro, inclínate por "query"

Responde SOLO con una palabra: "register" o "query", sin explicaciones, sin comillas, sin texto adicional.

Respuesta:"""

    try:
        response = model.generate_content(prompt)
        classification = response.text.strip().lower()
        
        # Clean up response
        classification = classification.replace('"', '').replace("'", "").strip()
        
        if classification not in ["register", "query"]:
            # Default to query if unclear
            logger.warning("Unclear classification '%s', defaulting to 'query'", classification)
            return "query"
        
        logger.debug("Classified intent as: %s for text: %s", classification, text[:50])
        return classification
    
    except Exception as e:
        logger.error("Error classifying intent: %s", e, exc_info=True)
        # Default to query on error (safer, won't try to register incorrectly)
        return "query"


async def process_user_text_input(
    text: str,
    user_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    message_obj,
) -> None:
    """Process user text input (from text message or transcribed audio).
    
    This function handles the core logic of classifying intent (REGISTER vs QUERY)
    and routing to the appropriate handler. It's shared between text messages
    and transcribed voice messages.
    
    Args:
        text: User's text input (from message or transcription)
        user_id: Telegram user ID
        context: Bot context
        message_obj: Telegram Message object for sending responses
    """
    # Skip empty messages
    if not text or not text.strip():
        return
    
    # Pre-filter: Skip very short messages (likely not financial-related)
    # This prevents wasting API quota on messages like "Hola" or "Gracias"
    # Note: We allow queries without numbers (e.g., "¿Cuánto gasté?")
    if len(text.strip()) < 3:
        return
    
    # Skip if user is in an active conversation (check user_data for pending flows)
    # This prevents interference with existing conversation handlers
    if context.user_data.get("pending_transaction") or context.user_data.get("budget_flow"):
        return
    
    try:
        # Send typing action immediately to improve UX
        chat = message_obj.chat if message_obj else None
        if chat:
            await context.bot.send_chat_action(chat_id=chat.id, action=constants.ChatAction.TYPING)
        
        # Step 1: Classify intent (REGISTER or QUERY)
        try:
            intent = _classify_intent(text)
        except Exception as e:
            logger.error("Error classifying intent: %s", e, exc_info=True)
            # Default to register to maintain backward compatibility
            intent = "register"
        
        # Step 2: Route to appropriate handler
        if intent == "query":
            # Handle as analytics query
            await _handle_query(message_obj, context, text, user_id)
        else:
            # Handle as transaction registration (existing logic)
            await _handle_register(message_obj, context, text, user_id)
    
    except Exception as e:
        logger.error("Unexpected error in process_user_text_input: %s", e, exc_info=True)
        if message_obj:
            await message_obj.reply_text(
                "😅 Ocurrió un error al procesar tu mensaje. Intenta nuevamente."
            )


async def handle_text_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle text messages and parse them as natural language transactions.
    
    This handler processes free-form text messages and attempts to extract
    transaction information using the AI service. It only processes messages
    that are not part of active conversation flows.
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    log_handler_invocation(logger, "handle_text_message", update)
    
    telegram_user = update.effective_user
    if not telegram_user or not update.message or not update.message.text:
        return
    
    user_id = telegram_user.id
    text = update.message.text.strip()
    
    # Process using shared function
    await process_user_text_input(text, user_id, context, update.message)


async def _handle_register(
    message_obj,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    user_id: int,
) -> None:
    """Handle transaction registration from natural language.
    
    Args:
        message_obj: Telegram Message object for sending responses
        context: Bot context
        text: User's text input
        user_id: Telegram user ID
    """
    # Setup: Get user categories
    with SessionLocal() as session:
        # Ensure user has default categories
        create_default_categories(session, user_id)
        
        # Fetch all user categories
        categories = fetch_user_categories(session, user_id)
        
        if not categories:
            await message_obj.reply_text(
                "No tienes categorías configuradas. Usa /categorias para crear algunas."
            )
            return
        
        # AI Magic: Parse transaction
        try:
            ai_service = get_ai_service()
            result = ai_service.parse_transaction(text, categories)
        except (ValueError, RuntimeError) as e:
            logger.warning("AI parsing failed for text '%s': %s", text, e)
            await message_obj.reply_text(
                "😅 No entendí bien ese gasto.\n\n"
                "Intenta así:\n"
                "• _'Gaste 20k en taxi'_\n"
                "• _'Recibí 500k de nómina'_",
                parse_mode="Markdown"
            )
            return
        except Exception as e:
            logger.error("Unexpected error in AI service: %s", e, exc_info=True)
            await message_obj.reply_text(
                "😅 No entendí bien ese gasto.\n\n"
                "Intenta así:\n"
                "• _'Gaste 20k en taxi'_\n"
                "• _'Recibí 500k de nómina'_",
                parse_mode="Markdown"
            )
            return
        
        # Validate result
        if not result:
            await message_obj.reply_text(
                "😅 No entendí bien ese gasto.\n\n"
                "Intenta así:\n"
                "• _'Gaste 20k en taxi'_\n"
                "• _'Recibí 500k de nómina'_",
                parse_mode="Markdown"
            )
            return
        
        # Get category for response
        category_id = result["category_id"]
        category = next((c for c in categories if c.id == category_id), None)
        if not category:
            logger.error("Category ID %s not found in user categories", category_id)
            await message_obj.reply_text(
                "Error: La categoría seleccionada no existe. Intenta nuevamente."
            )
            return
        
        # Process AI date with timezone handling
        date_str = result["date"]
        transaction_date, transaction_date_obj = _process_ai_date(date_str)
        
        # Persistence: Create Transaction
        transaction = Transaction(
            user_id=user_id,
            category_id=category_id,
            amount=result["amount"],
            description=result["description"] if result["description"] else None,
            transaction_date=transaction_date,
        )
        session.add(transaction)
        session.commit()
        
        # Format response
        amount_formatted = format_currency(result["amount"])
        description_text = result["description"] if result["description"] else "Sin descripción"
        
        # Format date for display (use local format)
        date_display = transaction_date_obj.strftime("%d/%m/%Y")
        
        # Determine transaction type emoji
        type_emoji = "💸" if result["type"] == "expense" else "💰"
        type_text = "Gasto" if result["type"] == "expense" else "Ingreso"
        
        response = (
            f"✅ **{type_text} registrado**\n\n"
            f"📝 {description_text}\n"
            f"💰 {amount_formatted}\n"
            f"📂 {category.name}\n"
            f"📅 {date_display}"
        )
        
        await message_obj.reply_text(response, parse_mode="Markdown")
        
        logger.info(
            "Natural language transaction created: user_id=%s, amount=%s, category=%s, date=%s",
            user_id,
            result["amount"],
            category.name,
            date_str,
        )


async def _handle_query(
    message_obj,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    user_id: int,
) -> None:
    """Handle analytics query from natural language.
    
    Args:
        message_obj: Telegram Message object for sending responses
        context: Bot context
        text: User's query text
        user_id: Telegram user ID
    """
    try:
        # Send typing action again before executing query to keep indicator active
        # This is important for long-running queries (7-14 seconds)
        chat = message_obj.chat if message_obj else None
        if chat:
            await context.bot.send_chat_action(chat_id=chat.id, action=constants.ChatAction.TYPING)
        
        analytics_service = get_analytics_service()
        answer = analytics_service.answer_question(text, user_id)
        await message_obj.reply_text(answer)
        
        logger.info(
            "Analytics query answered for user_id=%s: %s",
            user_id,
            text[:50],
        )
    
    except ValueError as e:
        logger.warning("Analytics query failed for text '%s': %s", text, e)
        await message_obj.reply_text(
            f"😅 No pude procesar tu consulta. Intenta reformularla o usar comandos específicos como /reporte_mes"
        )
    except RuntimeError as e:
        logger.error("Error in analytics service: %s", e, exc_info=True)
        await message_obj.reply_text(
            "😅 Ocurrió un error al procesar tu consulta. Intenta nuevamente."
        )
    except Exception as e:
        logger.error("Unexpected error in analytics query: %s", e, exc_info=True)
        await message_obj.reply_text(
            "😅 Ocurrió un error inesperado. Intenta reformular tu pregunta."
        )

