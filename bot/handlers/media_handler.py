"""Media handler for processing photos (receipts/bills) with OCR and voice messages."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from telegram import Update, constants
from telegram.ext import ContextTypes

from bot.common import get_logger, log_handler_invocation
from bot.handlers.natural_language import _process_ai_date, process_user_text_input
from bot.services.ai_service import get_ai_service
from bot.services.categories import create_default_categories, fetch_user_categories
from bot.utils.amounts import format_currency
from database import SessionLocal
from models import Category, Transaction

logger = get_logger("handlers.media_handler")


async def handle_photo_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle photo messages and extract transaction data using OCR.
    
    This handler processes photos (typically receipts/bills) and attempts to extract
    transaction information using the AI service with vision capabilities.
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    log_handler_invocation(logger, "handle_photo_message", update)
    
    telegram_user = update.effective_user
    if not telegram_user or not update.message or not update.message.photo:
        return
    
    user_id = telegram_user.id
    
    # Skip if user is in an active conversation
    if context.user_data.get("pending_transaction") or context.user_data.get("budget_flow"):
        return
    
    try:
        # Send chat action to show user that bot is processing photo
        chat = update.effective_chat
        if chat:
            await context.bot.send_chat_action(chat_id=chat.id, action=constants.ChatAction.UPLOAD_PHOTO)
        
        # Send "processing" message first for better UX
        processing_msg = await update.message.reply_text("📸 Analizando la factura...")
        
        # Download the largest photo (last in the list)
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        
        # Download photo as bytes
        photo_bytes = await photo_file.download_as_bytearray()
        
        # Setup: Get user categories
        with SessionLocal() as session:
            # Ensure user has default categories
            create_default_categories(session, user_id)
            
            # Fetch all user categories
            categories = fetch_user_categories(session, user_id)
            
            if not categories:
                await processing_msg.edit_text(
                    "No tienes categorías configuradas. Usa /categorias para crear algunas."
                )
                return
            
            # AI Magic: Parse transaction from image
            try:
                ai_service = get_ai_service()
                # Pass empty text and image_data for OCR processing
                result = ai_service.parse_transaction(
                    text="", 
                    categories=categories,
                    image_data=bytes(photo_bytes)
                )
            except (ValueError, RuntimeError) as e:
                logger.warning("AI OCR parsing failed for photo: %s", e)
                await processing_msg.edit_text(
                    "🤖 No pude leer bien esa foto.\n\n"
                    "**💡 Tips:**\n"
                    "• Intenta con mejor luz.\n"
                    "• Enfoca solo el total y el comercio.\n"
                    "• O escríbeme: _'Gaste 50k en mercado'_",
                    parse_mode="Markdown"
                )
                return
            except Exception as e:
                logger.error("Unexpected error in AI OCR service: %s", e, exc_info=True)
                await processing_msg.edit_text(
                    "🤖 No pude leer bien esa foto.\n\n"
                    "**💡 Tips:**\n"
                    "• Intenta con mejor luz.\n"
                    "• Enfoca solo el total y el comercio.\n"
                    "• O escríbeme: _'Gaste 50k en mercado'_",
                    parse_mode="Markdown"
                )
                return
            
            # Validate result
            if not result:
                await processing_msg.edit_text(
                    "🤖 No pude leer bien esa foto.\n\n"
                    "**💡 Tips:**\n"
                    "• Intenta con mejor luz.\n"
                    "• Enfoca solo el total y el comercio.\n"
                    "• O escríbeme: _'Gaste 50k en mercado'_",
                    parse_mode="Markdown"
                )
                return
            
            # Get category for response
            category_id = result["category_id"]
            category = next((c for c in categories if c.id == category_id), None)
            if not category:
                logger.error("Category ID %s not found in user categories", category_id)
                await processing_msg.edit_text(
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
                f"✅ **{type_text} registrado desde foto**\n\n"
                f"📝 {description_text}\n"
                f"💰 {amount_formatted}\n"
                f"📂 {category.name}\n"
                f"📅 {date_display}"
            )
            
            await processing_msg.edit_text(response, parse_mode="Markdown")
            
            logger.info(
                "Photo OCR transaction created: user_id=%s, amount=%s, category=%s, date=%s",
                user_id,
                result["amount"],
                category.name,
                date_str,
            )
    
    except Exception as e:
        logger.error("Unexpected error in handle_photo_message: %s", e, exc_info=True)
        await update.message.reply_text(
            "😅 Ocurrió un error al procesar la foto. Intenta nuevamente."
        )


async def handle_voice_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle voice messages and extract transaction data using speech-to-text.
    
    This handler processes voice messages and attempts to extract
    transaction information using the AI service with audio capabilities.
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    log_handler_invocation(logger, "handle_voice_message", update)
    
    telegram_user = update.effective_user
    if not telegram_user or not update.message or not update.message.voice:
        return
    
    user_id = telegram_user.id
    
    # Skip if user is in an active conversation
    if context.user_data.get("pending_transaction") or context.user_data.get("budget_flow"):
        return
    
    try:
        # Send chat action to show user that bot is recording/listening
        # This looks great - it appears the bot is actively listening/recording
        chat = update.effective_chat
        if chat:
            await context.bot.send_chat_action(chat_id=chat.id, action=constants.ChatAction.RECORD_VOICE)
        
        # Send "processing" message first for better UX
        processing_msg = await update.message.reply_text("🎤 Escuchando...")
        
        # Download the voice message
        voice = update.message.voice
        voice_file = await voice.get_file()
        
        # Download voice as bytes
        voice_bytes = await voice_file.download_as_bytearray()
        
        # Step 1: Transcribe audio to text
        try:
            ai_service = get_ai_service()
            transcribed_text = ai_service.transcribe_audio(bytes(voice_bytes))
            logger.info("Texto detectado en voz: %s", transcribed_text[:100])
        except (ValueError, RuntimeError) as e:
            logger.warning("Audio transcription failed: %s", e)
            await processing_msg.edit_text(
                "🤖 No pude entender el audio. Intenta hablar más claro o enviar el gasto por texto."
            )
            return
        except Exception as e:
            logger.error("Unexpected error in audio transcription: %s", e, exc_info=True)
            await processing_msg.edit_text(
                "🤖 No pude entender el audio. Intenta hablar más claro o enviar el gasto por texto."
            )
            return
        
        # Step 2: Delete processing message and process transcribed text using shared logic
        # This allows voice messages to work with both transactions and analytics queries
        await processing_msg.delete()
        await process_user_text_input(transcribed_text, user_id, context, update.message)
    
    except Exception as e:
        logger.error("Unexpected error in handle_voice_message: %s", e, exc_info=True)
        await update.message.reply_text(
            "😅 Ocurrió un error al procesar el audio. Intenta nuevamente."
        )

