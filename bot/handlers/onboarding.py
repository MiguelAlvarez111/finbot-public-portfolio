"""Onboarding conversation for new users."""

from __future__ import annotations

import re
from typing import Iterable, List, Set

from sqlalchemy.orm import Session
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes, ConversationHandler

from bot.common import get_logger, log_handler_invocation
from bot.utils.callback_manager import CallbackManager
from bot.conversation_states import (
    ONBOARDING_CATEGORY_CHOICES,
    ONBOARDING_COMPLETE,
    ONBOARDING_CUSTOM_INPUT,
    ONBOARDING_DEMO,
    ONBOARDING_WELCOME,
)
from bot.keyboards import build_onboarding_category_keyboard, build_main_menu_keyboard
from bot.services.categories import (
    DEFAULT_CATEGORY_DEFINITIONS,
    create_default_categories,
    ensure_categories_exist,
)
from database import SessionLocal
from models import CategoryType, User

logger = get_logger("handlers.onboarding")

LOCKED_DEFAULTS = {"General", "General Ingreso"}
ONBOARDING_CATEGORY_NAMES = [
    definition["name"] for definition in DEFAULT_CATEGORY_DEFINITIONS
]

USAGE_TIPS_MESSAGE = (
    "🤖 **¡Soy Inteligente! No necesitas botones.**\n\n"
    "Solo escríbeme o mándame un audio como si fuera tu amigo:\n"
    "• _'Gaste 20 lucas en almuerzo'_\n"
    "• _'Me pagaron 500k'_\n"
    "• _'¿Cuánto he gastado en comida este mes?'_\n\n"
    "📸 O mándame una foto de la factura.\n\n"
    "¡Inténtalo ahora! 👇"
)

COMMANDS_OVERVIEW = (
    "Estas son algunas de las opciones del menú principal:\n"
    "• 📊 Reporte – Obtén un gráfico del mes actual.\n"
    "• 📈 Dashboard – Abre el panel temporal con más métricas.\n"
    "• 🎯 Metas – Crea o aporta a tus objetivos de ahorro.\n"
    "• ⚖️ Presupuestos – Configura y revisa tus presupuestos.\n"
    "• ⚙️ Ajustes – Accede a herramientas avanzadas como resetear la cuenta.\n\n"
    "Si necesitas más comandos avanzados escribe /help."
)


def _ensure_user(session: Session, telegram_id: int, chat_id: int) -> User:
    user = session.get(User, telegram_id)
    if not user:
        user = User(telegram_id=telegram_id, chat_id=chat_id)
        session.add(user)
        session.commit()
        logger.info("Created new user %s", telegram_id)
    elif user.chat_id != chat_id:
        user.chat_id = chat_id
        session.commit()
    return user


async def onboarding_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "onboarding_start", update)
    telegram_user = update.effective_user
    chat = update.effective_chat
    message = update.message

    if not telegram_user or not chat or not message:
        return ConversationHandler.END

    # Toda la lógica de BD se resuelve dentro de la sesión
    with SessionLocal() as session:
        user = _ensure_user(session, telegram_user.id, chat.id)
        is_onboarded = bool(user.is_onboarded)

    # Fuera del with NO volvemos a tocar `user`
    if is_onboarded:
        await message.reply_text(
            "¡Qué gusto verte de nuevo! 👋\n"
            "Estoy listo para ayudarte con tus finanzas. Usa el menú para comenzar.\n\n"
            f"{COMMANDS_OVERVIEW}",
            reply_markup=build_main_menu_keyboard(),
        )
        return ConversationHandler.END

    # Flujo de onboarding inicial
    context.user_data["onboarding"] = {
        "selected_defaults": set(ONBOARDING_CATEGORY_NAMES),
        "custom_categories": [],
    }

    first_name = telegram_user.first_name or telegram_user.full_name or "allí"
    await message.reply_text(
        f"¡Hola {first_name}! Soy tu asistente financiero 🤖\n"
        "Te ayudo a registrar gastos, ingresos y a entender tus finanzas personales."
    )
    await message.reply_text(
        "Para empezar, quiero mostrarte lo que puedo hacer.\n\n"
        "**Prueba decirme o mandarme un audio:**\n"
        "_'Gaste 20k en almuerzo ayer'_\n\n"
        "¿Te animas a probar ahora o configuramos primero?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🧪 Probar Demo", callback_data=CallbackManager.onboarding("demo")
                    ),
                    InlineKeyboardButton(
                        "⚙️ Configurar", callback_data=CallbackManager.onboarding("skip_demo")
                    )
                ]
            ]
        ),
    )
    return ONBOARDING_DEMO


async def onboarding_restart(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Inicia el flujo de onboarding desde un callback (después de reset)."""
    log_handler_invocation(logger, "onboarding_restart", update)
    query = update.callback_query
    if not query:
        return ConversationHandler.END

    await query.answer()
    telegram_user = query.from_user
    chat = query.message.chat

    if not telegram_user or not chat:
        return ConversationHandler.END

    # Toda la lógica de BD se resuelve dentro de la sesión
    with SessionLocal() as session:
        user = _ensure_user(session, telegram_user.id, chat.id)
        # Marcar como no onboarded para forzar el flujo completo
        user.is_onboarded = False
        session.commit()

    # Flujo de onboarding inicial
    context.user_data["onboarding"] = {
        "selected_defaults": set(ONBOARDING_CATEGORY_NAMES),
        "custom_categories": [],
    }

    first_name = telegram_user.first_name or telegram_user.full_name or "allí"
    await context.bot.send_message(
        chat_id=chat.id,
        text=(
            f"¡Hola {first_name}! Soy tu asistente financiero 🤖\n"
            "Te ayudo a registrar gastos, ingresos y a entender tus finanzas personales."
        )
    )
    await context.bot.send_message(
        chat_id=chat.id,
        text=(
            "Para empezar, quiero mostrarte lo que puedo hacer.\n\n"
            "**Prueba decirme o mandarme un audio:**\n"
            "_'Gaste 20k en almuerzo ayer'_\n\n"
            "¿Te animas a probar ahora o configuramos primero?"
        ),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🧪 Probar Demo", callback_data=CallbackManager.onboarding("demo")
                    ),
                    InlineKeyboardButton(
                        "⚙️ Configurar", callback_data=CallbackManager.onboarding("skip_demo")
                    )
                ]
            ]
        ),
    )
    return ONBOARDING_DEMO


async def onboarding_demo_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Maneja la elección del usuario en el demo de onboarding."""
    log_handler_invocation(logger, "onboarding_demo_handler", update)
    query = update.callback_query
    if not query:
        return ConversationHandler.END
    
    await query.answer()
    
    try:
        action_parts = CallbackManager.parse_onboarding(query.data)
        action = action_parts[0] if action_parts else ""
    except ValueError as e:
        logger.warning("Error parsing onboarding callback: %s", e)
        try:
            await query.edit_message_text(
                "Error al procesar la selección. Intenta nuevamente."
            )
        except BadRequest:
            pass
        return ONBOARDING_DEMO
    
    if action == "skip_demo":
        # Saltar demo y ir directamente a categorías
        try:
            await query.edit_message_text(
                "Estas son categorías sugeridas. Toca para activar o desactivar las que quieras conservar."
            )
        except BadRequest as e:
            if "message is not modified" in str(e).lower():
                pass
            else:
                raise
        data = context.user_data.setdefault(
            "onboarding",
            {
                "selected_defaults": set(ONBOARDING_CATEGORY_NAMES),
                "custom_categories": [],
            },
        )
        selected: Set[str] = set(data["selected_defaults"])
        try:
            await query.edit_message_reply_markup(
                reply_markup=build_onboarding_category_keyboard(
                    ONBOARDING_CATEGORY_NAMES,
                    selected,
                )
            )
        except BadRequest as e:
            if "message is not modified" in str(e).lower():
                pass
            else:
                raise
        return ONBOARDING_CATEGORY_CHOICES
    elif action == "demo":
        # Esperar input del usuario para el demo
        try:
            await query.edit_message_text(
                "¡Perfecto! 🧪\n\n"
                "Ahora prueba escribiéndome o mandándome un audio como:\n"
                "_'Gaste 20k en almuerzo ayer'_\n\n"
                "Te mostraré cómo lo proceso automáticamente.",
                parse_mode="Markdown",
            )
        except BadRequest as e:
            if "message is not modified" in str(e).lower():
                pass
            else:
                raise
        return ONBOARDING_DEMO
    else:
        return ONBOARDING_DEMO


async def onboarding_demo_process(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Procesa el texto o audio durante el demo de onboarding."""
    log_handler_invocation(logger, "onboarding_demo_process", update)
    telegram_user = update.effective_user
    message = update.message
    
    if not telegram_user or not message:
        return ONBOARDING_DEMO
    
    user_id = telegram_user.id
    text = message.text or ""
    
    # Si es un audio, transcribirlo primero
    if message.voice and not text:
        try:
            from bot.services.ai_service import get_ai_service
            from telegram import constants
            
            # Enviar indicador de procesamiento
            chat = update.effective_chat
            if chat:
                await context.bot.send_chat_action(
                    chat_id=chat.id, 
                    action=constants.ChatAction.RECORD_VOICE
                )
            
            # Descargar audio
            voice_file = await message.voice.get_file()
            audio_bytes = await voice_file.download_as_bytearray()
            
            # Transcribir
            ai_service = get_ai_service()
            text = ai_service.transcribe_audio(bytes(audio_bytes))
            
            if not text or not text.strip():
                await message.reply_text(
                    "🤖 No pude entender el audio. Intenta escribiéndolo o graba nuevamente."
                )
                return ONBOARDING_DEMO
        except Exception as e:
            logger.error("Error transcribing audio in demo: %s", e, exc_info=True)
            await message.reply_text(
                "🤖 Hubo un error al procesar el audio. Intenta escribiéndolo."
            )
            return ONBOARDING_DEMO
    
    if not text.strip():
        await message.reply_text(
            "Por favor, escribe algo como: _'Gaste 20k en almuerzo ayer'_",
            parse_mode="Markdown"
        )
        return ONBOARDING_DEMO
    
    # Importar aquí para evitar circular imports
    from bot.services.ai_service import get_ai_service
    from bot.services.categories import create_default_categories, fetch_user_categories
    from bot.handlers.natural_language import _process_ai_date
    from bot.utils.amounts import format_currency
    from models import Category, Transaction
    
    try:
        with SessionLocal() as session:
            # Crear categoría temporal "General" si no existe
            create_default_categories(session, user_id)
            categories = fetch_user_categories(session, user_id)
            
            if not categories:
                await message.reply_text(
                    "No pude procesar el demo. Intenta configurar primero."
                )
                return ONBOARDING_DEMO
            
            # Procesar con IA
            ai_service = get_ai_service()
            result = ai_service.parse_transaction(
                text=text,
                categories=categories,
            )
            
            # Validar resultado
            if not result:
                await message.reply_text(
                    "🤖 No pude entender eso. Intenta con: _'Gaste 20k en almuerzo'_",
                    parse_mode="Markdown"
                )
                return ONBOARDING_DEMO
            
            # Procesar fecha
            transaction_date, transaction_date_obj = _process_ai_date(result["date"])
            
            # Encontrar categoría
            category = next(
                (cat for cat in categories if cat.id == result["category_id"]),
                None
            )
            
            if not category:
                await message.reply_text(
                    "🤖 No pude encontrar la categoría. Intenta nuevamente."
                )
                return ONBOARDING_DEMO
            
            # Crear transacción (guardarla realmente para que el usuario vea el resultado)
            transaction = Transaction(
                user_id=user_id,
                category_id=category.id,
                amount=result["amount"],
                description=result.get("description", ""),
                transaction_date=transaction_date,
            )
            session.add(transaction)
            session.commit()
            
            # Mensaje de éxito
            amount_str = format_currency(result["amount"])
            description_text = ""
            if result.get("description"):
                description_text = f"Descripción: {result.get('description', '')}\n"
            
            await message.reply_text(
                f"¡Perfecto! ✅\n\n"
                f"Registré: **{amount_str}** en **{category.name}**\n"
                f"Fecha: {transaction_date_obj.strftime('%d/%m/%Y')}\n"
                f"{description_text}\n"
                f"¡Así de fácil es! Ahora configuremos tus categorías reales...",
                parse_mode="Markdown"
            )
            
            # Pasar al flujo de categorías
            data = context.user_data.setdefault(
                "onboarding",
                {
                    "selected_defaults": set(ONBOARDING_CATEGORY_NAMES),
                    "custom_categories": [],
                },
            )
            selected: Set[str] = set(data["selected_defaults"])
            
            await message.reply_text(
                "Estas son categorías sugeridas. Toca para activar o desactivar las que quieras conservar.",
                reply_markup=build_onboarding_category_keyboard(
                    ONBOARDING_CATEGORY_NAMES,
                    selected,
                )
            )
            return ONBOARDING_CATEGORY_CHOICES
            
    except Exception as e:
        logger.error("Error processing demo transaction: %s", e, exc_info=True)
        await message.reply_text(
            "🤖 Hubo un error al procesar. Intenta nuevamente o elige 'Configurar' para continuar."
        )
        return ONBOARDING_DEMO


async def onboarding_category_choice(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "onboarding_category_choice", update)
    query = update.callback_query
    await query.answer()

    data = context.user_data.setdefault(
        "onboarding",
        {
            "selected_defaults": set(ONBOARDING_CATEGORY_NAMES),
            "custom_categories": [],
        },
    )
    selected: Set[str] = set(data["selected_defaults"])

    try:
        action_parts = CallbackManager.parse_onboarding(query.data)
        action = action_parts[0] if action_parts else ""
    except ValueError as e:
        logger.warning("Error parsing onboarding callback: %s", e)
        try:
            await query.edit_message_text(
                "Error al procesar la selección. Intenta nuevamente."
            )
        except BadRequest:
            pass
        return ONBOARDING_CATEGORY_CHOICES

    if action == "start":
        text = (
            "Estas son categorías sugeridas. Toca para activar o desactivar las que quieras conservar."
        )
    elif action == "toggle" and len(action_parts) > 1:
        category_name = ":".join(action_parts[1:])
        if category_name in LOCKED_DEFAULTS:
            await query.answer("Esta categoría es obligatoria para el bot.", show_alert=True)
        elif category_name in selected:
            selected.remove(category_name)
        else:
            selected.add(category_name)
        data["selected_defaults"] = selected
        text = (
            "Categorías seleccionadas. Ajusta las que necesites y presiona continuar."
        )
    elif action == "next":
        if not selected:
            await query.answer(
                "Selecciona al menos una categoría antes de continuar.",
                show_alert=True,
            )
            return ONBOARDING_CATEGORY_CHOICES
        try:
            await query.edit_message_text(
                "¿Quieres añadir alguna categoría personalizada ahora? (ej: 'Mascotas', 'Gimnasio')\n"
                "Puedes escribir una lista separada por comas o escribe 'no' para omitir."
            )
        except BadRequest as e:
            if "message is not modified" in str(e).lower():
                pass
            else:
                raise
        return ONBOARDING_CUSTOM_INPUT
    else:
        return ONBOARDING_CATEGORY_CHOICES

    try:
        await query.edit_message_text(
            text,
            reply_markup=build_onboarding_category_keyboard(
                ONBOARDING_CATEGORY_NAMES,
                selected,
            ),
        )
    except BadRequest as e:
        # Ignorar error "Message is not modified" cuando el usuario hace clic muy rápido
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise
    return ONBOARDING_CATEGORY_CHOICES


def _parse_custom_categories(message: str) -> List[str]:
    if not message:
        return []
    if message.strip().lower() in {"no", "ninguna"}:
        return []
    raw_items = re.split(r",|\n", message)
    cleaned = [item.strip() for item in raw_items if item.strip()]
    return cleaned


async def onboarding_custom_categories(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "onboarding_custom_categories", update)
    onboarding_data = context.user_data.get("onboarding")
    if not onboarding_data:
        await update.message.reply_text(
            "Algo salió mal con el proceso de onboarding. Intenta nuevamente con /start."
        )
        return ConversationHandler.END

    categories = _parse_custom_categories(update.message.text or "")
    onboarding_data["custom_categories"] = categories

    if categories:
        await update.message.reply_text(
            "Perfecto, añadiré estas categorías personalizadas:\n"
            f"- " + "\n- ".join(categories)
        )
    else:
        await update.message.reply_text("Sin categorías personalizadas por ahora.")

    await update.message.reply_text(
        "Cuando estés listo, presiona finalizar para guardar todo.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Finalizar 🚀", callback_data=CallbackManager.onboarding("finish")
                    )
                ]
            ]
        ),
    )
    return ONBOARDING_COMPLETE


async def onboarding_finish(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "onboarding_finish", update)
    if update.callback_query:
        await update.callback_query.answer()

    telegram_user = update.effective_user
    chat = update.effective_chat
    if not telegram_user or not chat:
        return ConversationHandler.END

    onboarding_data = context.user_data.get("onboarding", {})
    selected_defaults: Iterable[str] = onboarding_data.get(
        "selected_defaults", ONBOARDING_CATEGORY_NAMES
    )
    custom_categories: Iterable[str] = onboarding_data.get(
        "custom_categories", []
    )

    selected_with_locked = set(selected_defaults).union(LOCKED_DEFAULTS)

    with SessionLocal() as session:
        user = _ensure_user(session, telegram_user.id, chat.id)
        create_default_categories(
            session,
            user.telegram_id,
            selected_names=selected_with_locked,
        )
        ensure_categories_exist(
            session,
            user.telegram_id,
            custom_categories,
            category_type=CategoryType.EXPENSE,
            is_default=False,
        )
        user.is_onboarded = True
        session.commit()

    context.user_data.pop("onboarding", None)

    # Primero enviar el mensaje educativo
    await context.bot.send_message(
        chat_id=chat.id,
        text=(
            "¡Todo listo! 🎉\n\n"
            f"{USAGE_TIPS_MESSAGE}"
        ),
        parse_mode="Markdown",
    )
    
    # Luego mostrar el menú principal
    await context.bot.send_message(
        chat_id=chat.id,
        text=(
            "Menú principal:\n\n"
            f"{COMMANDS_OVERVIEW}"
        ),
        reply_markup=build_main_menu_keyboard(),
    )
    return ConversationHandler.END


