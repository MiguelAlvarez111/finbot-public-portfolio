"""Core command handlers."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import os

import jwt
from sqlalchemy import func, select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes, ConversationHandler

from bot.common import get_logger, log_handler_invocation
from bot.keyboards import (
    build_budgets_menu_keyboard,
    build_main_menu_keyboard,
    build_settings_menu_keyboard,
    build_settings_reset_confirmation_keyboard,
)
from bot.handlers.categories import category_management_menu
from bot.handlers.reporting import generate_transactions_excel
from bot.handlers.transactions import _format_transaction_button_text as format_transaction_button_text
from bot.utils.amounts import format_currency
from bot.utils.callback_manager import CallbackManager
from bot.utils.time_utils import get_now_utc
from database import SessionLocal
from models import Budget, Category, CategoryType, Goal, Transaction, User

logger = get_logger("handlers.core")


async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler para el dashboard. Comando global que cancela cualquier flujo activo."""
    log_handler_invocation(logger, "dashboard", update)
    telegram_user = update.effective_user
    message = update.message

    if not telegram_user or not message:
        logger.warning("Missing user or message when handling /dashboard command.")
        return ConversationHandler.END

    # Limpiar estado de conversación para cancelar cualquier flujo activo
    context.user_data.clear()

    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        await message.reply_text(
            "No hay una clave secreta configurada para generar el acceso al dashboard."
        )
        return

    payload = {
        "user_id": telegram_user.id,
        "exp": get_now_utc() + timedelta(minutes=1),
    }

    try:
        token = jwt.encode(payload, secret_key, algorithm="HS256")
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception(
            "Error generating dashboard token for user %s: %s",
            telegram_user.id,
            exc,
        )
        await message.reply_text(
            "No pude generar el enlace del dashboard en este momento. Intenta nuevamente más tarde."
        )
        return

    if isinstance(token, bytes):
        token = token.decode("utf-8")

    dashboard_base_url = os.getenv(
        "DASHBOARD_URL", "https://mi-dashboard.railway.app"
    ).rstrip("/")
    auth_link = f"{dashboard_base_url}/auth?token={token}"

    await message.reply_text(
        "Aquí tienes tu enlace temporal al dashboard:\n"
        f"{auth_link}\n"
        "⚠️ El enlace caduca en 1 minuto."
    )
    return ConversationHandler.END


async def user_guide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    log_handler_invocation(logger, "user_guide", update)
    telegram_user = update.effective_user
    if not telegram_user:
        return

    guide_text = (
        "🧭 **Guía rápida de uso**\n\n"
        "1. **Primeros pasos**\n"
        "   - Escribe /start para iniciar y completa el onboarding.\n"
        "   - Usa el menú persistente para acceder rápido a las funciones principales.\n\n"
        "2. **Registrar movimientos**\n"
        "   - Escribe o graba un audio como si fuera tu amigo: _'Gaste 20 lucas en almuerzo'_\n"
        "   - O mándame una foto de la factura y la proceso automáticamente.\n\n"
        "3. **Seguir tus finanzas**\n"
        "   - *📊 Reporte* genera un gráfico con la distribución de gastos.\n"
        "   - *📈 Dashboard* abre un panel web temporal con más métricas.\n"
        "   - /exportar descarga un Excel con todas tus transacciones.\n\n"
        "4. **Control y alertas**\n"
        "   - Desde *🎯 Metas* puedes crear objetivos o aportar a los existentes.\n"
        "   - *⚖️ Presupuestos* te deja configurar y revisar tus límites mensuales.\n"
        "   - *⚙️ Ajustes* ofrece utilidades adicionales como resetear la cuenta.\n\n"
        "¿Ideas o mejoras? ¡Escríbeme por este chat!"
    )

    await update.message.reply_text(guide_text, parse_mode="Markdown")


async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler para el menú de ajustes. Comando global que cancela cualquier flujo activo."""
    log_handler_invocation(logger, "settings_menu", update)
    telegram_user = update.effective_user
    message = update.message
    if not telegram_user or not message:
        return ConversationHandler.END

    # Limpiar estado de conversación para cancelar cualquier flujo activo
    context.user_data.clear()

    await message.reply_text(
        "Ajustes disponibles:",
        reply_markup=build_settings_menu_keyboard(),
    )
    return ConversationHandler.END


async def settings_reset_prompt(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Muestra el mensaje de confirmación para resetear la cuenta."""
    log_handler_invocation(logger, "settings_reset_prompt", update)
    query = update.callback_query
    if not query:
        return

    await query.answer()
    await query.edit_message_text(
        "⚠️ Esta acción borrará todos tus datos (gastos, ingresos, metas y presupuestos). "
        "No se puede deshacer.\n\n¿Estás seguro?",
        reply_markup=build_settings_reset_confirmation_keyboard(),
    )


async def settings_reset_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Cancela el reset y vuelve al menú de Ajustes."""
    log_handler_invocation(logger, "settings_reset_cancel", update)
    query = update.callback_query
    if not query:
        return

    await query.answer()
    await query.edit_message_text(
        "Ajustes disponibles:",
        reply_markup=build_settings_menu_keyboard(),
    )


async def settings_reset_confirm(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Borra todos los datos del usuario y resetea la cuenta."""
    log_handler_invocation(logger, "settings_reset_confirm", update)
    query = update.callback_query
    await query.answer()
    telegram_id = query.from_user.id

    # 1) Borrar datos en BD
    with SessionLocal() as session:
        user = (
            session.query(User)
            .filter(User.telegram_id == telegram_id)
            .first()
        )

        if user is not None:
            # Borrar entidades relacionadas al usuario explícitamente
            # Aunque cascade debería funcionar, lo hacemos explícito para asegurar
            session.query(Transaction).filter_by(user_id=user.telegram_id).delete()
            session.query(Budget).filter_by(user_id=user.telegram_id).delete()
            session.query(Goal).filter_by(user_id=user.telegram_id).delete()
            # Borrar categorías personalizadas (las default se recrean en onboarding)
            session.query(Category).filter_by(
                user_id=user.telegram_id, is_default=False
            ).delete()
            # Finalmente borrar el usuario (esto también borrará cualquier relación restante)
            session.delete(user)
            session.commit()

    # 2) Actualizar el mensaje de confirmación con botón inline
    reset_message = (
        "✅ Tu cuenta ha sido reseteada.\n\n"
        "A partir de ahora empezamos desde cero.\n\n"
        "Pulsa el botón de abajo para volver a configurar tus categorías y preferencias."
    )
    restart_keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔁 Empezar de nuevo",
                    callback_data=CallbackManager.onboarding("restart"),
                )
            ]
        ]
    )
    try:
        await query.edit_message_text(
            reset_message,
            reply_markup=restart_keyboard,
        )
    except BadRequest:
        # Si no se puede editar (mensaje muy viejo, etc.), enviar mensaje nuevo
        logger.warning("No se pudo editar el mensaje de reset, enviando uno nuevo.")
        await query.message.chat.send_message(
            reset_message,
            reply_markup=restart_keyboard,
        )


async def settings_export_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handler para exportar CSV desde el menú de ajustes."""
    log_handler_invocation(logger, "settings_export_handler", update)
    query = update.callback_query
    chat = update.effective_chat
    telegram_user = update.effective_user
    if not query or not chat or not telegram_user:
        return

    await query.answer()
    await query.edit_message_text("📦 Preparando tu archivo de transacciones...")

    buffer = await asyncio.to_thread(generate_transactions_excel, telegram_user.id)

    await context.bot.send_document(
        chat_id=chat.id,
        document=buffer,
        filename="reporte_finanzas.xlsx",
    )
    await context.bot.send_message(
        chat_id=chat.id,
        text="✅ Archivo generado. También puedes usar /exportar.",
        reply_markup=build_settings_menu_keyboard(),
    )


async def settings_delete_recent_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handler para eliminar últimos registros desde el menú de ajustes."""
    log_handler_invocation(logger, "settings_delete_recent_handler", update)
    query = update.callback_query
    telegram_user = update.effective_user
    if not query or not telegram_user:
        return

    await query.answer()

    with SessionLocal() as session:
        transactions = list(
            session.execute(
                select(Transaction)
                .where(Transaction.user_id == telegram_user.id)
                .order_by(Transaction.transaction_date.desc())
                .limit(5)
            ).scalars()
        )

    if not transactions:
        await query.edit_message_text(
            "No encontré transacciones recientes.",
            reply_markup=build_settings_menu_keyboard(),
        )
        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=format_transaction_button_text(transaction),
                    callback_data=CallbackManager.delete_transaction(transaction.id),
                )
            ]
            for transaction in transactions
        ]
        + [
            [
                InlineKeyboardButton(
                    "⬅️ Volver a ajustes",
                    callback_data="settings:back",
                )
            ]
        ]
    )

    await query.edit_message_text(
        "Selecciona una transacción para eliminarla:",
        reply_markup=keyboard,
    )


async def settings_quick_stats(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Muestra estadísticas rápidas del usuario."""
    log_handler_invocation(logger, "settings_quick_stats", update)
    query = update.callback_query
    telegram_user = update.effective_user
    if not query or not telegram_user:
        return

    await query.answer()

    now = get_now_utc()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1)

    with SessionLocal() as session:
        # Total gastos del mes
        expenses_query = (
            select(func.sum(Transaction.amount))
            .join(Category, Transaction.category_id == Category.id)
            .where(
                Transaction.user_id == telegram_user.id,
                Category.type == CategoryType.EXPENSE,
                Transaction.transaction_date >= month_start,
                Transaction.transaction_date < next_month,
            )
        )
        total_expenses = session.execute(expenses_query).scalar() or 0

        # Total ingresos del mes
        income_query = (
            select(func.sum(Transaction.amount))
            .join(Category, Transaction.category_id == Category.id)
            .where(
                Transaction.user_id == telegram_user.id,
                Category.type == CategoryType.INCOME,
                Transaction.transaction_date >= month_start,
                Transaction.transaction_date < next_month,
            )
        )
        total_income = session.execute(income_query).scalar() or 0

        # Balance
        balance = total_income - total_expenses

        # Categoría más gastada
        top_category_query = (
            select(Category.name, func.sum(Transaction.amount).label("total"))
            .join(Transaction, Transaction.category_id == Category.id)
            .where(
                Transaction.user_id == telegram_user.id,
                Category.type == CategoryType.EXPENSE,
                Transaction.transaction_date >= month_start,
                Transaction.transaction_date < next_month,
            )
            .group_by(Category.name)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(1)
        )
        top_category_result = session.execute(top_category_query).first()

        user = session.get(User, telegram_user.id)
        currency = user.default_currency if user else "COP"

    stats_text = (
        f"📊 **Estadísticas del mes actual**\n\n"
        f"💰 **Ingresos**: {format_currency(total_income)}\n"
        f"💸 **Gastos**: {format_currency(total_expenses)}\n"
        f"💵 **Balance**: {format_currency(balance)}\n\n"
    )

    if top_category_result:
        stats_text += f"🏆 **Categoría más gastada**: {top_category_result[0]}\n"
        stats_text += f"   Total: {format_currency(top_category_result[1])}\n"

    stats_text += f"\n💱 **Moneda**: {currency}"

    await query.edit_message_text(
        stats_text,
        parse_mode="Markdown",
        reply_markup=build_settings_menu_keyboard(),
    )


async def settings_change_currency(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Inicia el flujo para cambiar la moneda del usuario."""
    log_handler_invocation(logger, "settings_change_currency", update)
    query = update.callback_query
    if not query:
        return

    await query.answer()

    currency_options = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🇨🇴 COP (Peso colombiano)", callback_data=CallbackManager.settings("currency", "COP")),
            ],
            [
                InlineKeyboardButton("⬅️ Volver", callback_data=CallbackManager.settings("back")),
            ],
        ]
    )

    await query.edit_message_text(
        "💰 **Moneda**\n\n"
        "Por ahora, FinBot solo soporta COP (Peso colombiano).\n"
        "Tu configuración se mantendrá en COP.\n\n"
        "Otras monedas estarán disponibles en futuras actualizaciones.",
        reply_markup=currency_options,
        parse_mode="Markdown",
    )


async def settings_currency_selected(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Procesa la selección de moneda."""
    log_handler_invocation(logger, "settings_currency_selected", update)
    query = update.callback_query
    telegram_user = update.effective_user
    if not query or not telegram_user:
        return

    await query.answer()

    try:
        parts = CallbackManager.parse_settings(query.data)
        if len(parts) < 2 or parts[0] != "currency":
            raise ValueError("Formato inválido para selección de moneda")
        currency = parts[1]
    except ValueError as e:
        logger.warning("Error parsing currency callback: %s", e)
        await query.edit_message_text(
            "Error al procesar la selección. Intenta nuevamente.",
            reply_markup=build_settings_menu_keyboard(),
        )
        return

    # Enforce COP-only: regardless of selection, set to COP
    currency = "COP"

    with SessionLocal() as session:
        user = session.get(User, telegram_user.id)
        if user:
            user.default_currency = currency
            session.commit()
            await query.edit_message_text(
                "✅ Tu moneda está configurada en COP (Peso colombiano).\n\n"
                "Por ahora, FinBot solo soporta COP. Los montos se mostrarán siempre en formato colombiano.",
                reply_markup=build_settings_menu_keyboard(),
            )
        else:
            await query.edit_message_text(
                "No se encontró tu usuario. Usa /start para configurar el bot.",
                reply_markup=build_settings_menu_keyboard(),
            )


async def settings_gamification(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Muestra el estado de gamificación del usuario."""
    log_handler_invocation(logger, "settings_gamification", update)
    query = update.callback_query
    telegram_user = update.effective_user
    if not query or not telegram_user:
        return

    await query.answer()

    with SessionLocal() as session:
        user = session.get(User, telegram_user.id)
        if not user:
            await query.edit_message_text(
                "No se encontró tu usuario. Usa /start para configurar el bot.",
                reply_markup=build_settings_menu_keyboard(),
            )
            return

        # Verificar si existen campos de gamificación
        has_gamification = hasattr(user, "streak_days") and hasattr(user, "total_points")

        if not has_gamification:
            gamification_text = (
                "🎮 **Gamificación**\n\n"
                "El sistema de gamificación está en desarrollo.\n"
                "Próximamente podrás ganar puntos, mantener rachas y desbloquear logros.\n\n"
                "¡Mantente al día!"
            )
        else:
            streak_days = getattr(user, "streak_days", 0)
            total_points = getattr(user, "total_points", 0)
            level = getattr(user, "level", 1)

            # Calcular nivel basado en puntos
            if total_points < 100:
                level_text = "1 - Iniciante"
            elif total_points < 500:
                level_text = "2 - Aprendiz"
            elif total_points < 1500:
                level_text = "3 - Practicante"
            elif total_points < 5000:
                level_text = "4 - Experto"
            else:
                level_text = "5 - Maestro Financiero"

            gamification_text = (
                f"🎮 **Tu Progreso**\n\n"
                f"🔥 **Racha actual**: {streak_days} días consecutivos\n"
                f"⭐ **Puntos totales**: {total_points}\n"
                f"📊 **Nivel**: {level_text}\n\n"
                f"💡 Registra una transacción mañana para mantener tu racha!"
            )

    await query.edit_message_text(
        gamification_text,
        parse_mode="Markdown",
        reply_markup=build_settings_menu_keyboard(),
    )


async def settings_back_to_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Regresa al menú principal desde ajustes."""
    log_handler_invocation(logger, "settings_back_to_menu", update)
    query = update.callback_query
    if not query:
        return

    await query.answer()

    # Eliminar el inline keyboard del mensaje del submenú
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except BadRequest:
        # Si ya fue editado o no tiene inline keyboard, lo ignoramos
        pass

    # Cambiar el texto del mensaje para indicar que salió al menú principal
    try:
        await query.edit_message_text(
            "Has vuelto al menú principal.\n\n"
            "Usa los botones de abajo para continuar. 😊"
        )
    except BadRequest:
        # Si no se puede editar texto (por ejemplo ya se editó), lo ignoramos
        pass

    # Enviar un mensaje nuevo con el menú principal usando el teclado de reply
    try:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Menú principal:",
            reply_markup=build_main_menu_keyboard(),
        )
    except BadRequest:
        pass


async def settings_back(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Regresa al menú de ajustes."""
    log_handler_invocation(logger, "settings_back", update)
    query = update.callback_query
    if not query:
        return

    await query.answer()
    await query.edit_message_text(
        "Ajustes disponibles:",
        reply_markup=build_settings_menu_keyboard(),
    )


async def settings_categories(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Abre el menú de gestión de categorías desde ajustes."""
    log_handler_invocation(logger, "settings_categories", update)
    query = update.callback_query
    if not query:
        return

    await query.answer()
    # Reutilizar el handler de categorías
    await category_management_menu(
        update,
        context,
        text="Gestión de categorías. ¿Qué te gustaría hacer?",
    )


async def show_usage_tips(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Muestra tips de uso del bot con enfoque AI-First.
    
    Comando global que cancela cualquier flujo de conversación activo.
    """
    log_handler_invocation(logger, "show_usage_tips", update)
    message = update.message
    if not message:
        return ConversationHandler.END

    # Limpiar estado de conversación para cancelar cualquier flujo activo
    context.user_data.clear()

    usage_text = (
        "🤖 **¡Soy Inteligente! No necesitas botones.**\n\n"
        "Solo escríbeme o mándame un audio como si fuera tu amigo:\n"
        "• _'Gaste 20 lucas en almuerzo'_\n"
        "• _'Me pagaron 500k'_\n"
        "• _'¿Cuánto he gastado en comida este mes?'_\n\n"
        "📸 O mándame una foto de la factura.\n\n"
        "¡Inténtalo ahora! 👇"
    )

    await message.reply_text(usage_text, parse_mode="Markdown")
    return ConversationHandler.END


async def settings_budgets_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Abre el menú de presupuestos desde ajustes."""
    log_handler_invocation(logger, "settings_budgets_handler", update)
    query = update.callback_query
    if not query:
        return

    await query.answer()
    
    # Limpiar estado de conversación para cancelar cualquier flujo activo
    context.user_data.clear()

    await query.edit_message_text(
        "Gestiona tus presupuestos:",
        reply_markup=build_budgets_menu_keyboard(),
    )


async def settings_guide_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Muestra la guía de usuario desde ajustes."""
    log_handler_invocation(logger, "settings_guide_handler", update)
    query = update.callback_query
    if not query:
        return

    await query.answer()

    guide_text = (
        "🧭 **Guía rápida de uso**\n\n"
        "1. **Primeros pasos**\n"
        "   - Escribe /start para iniciar y completa el onboarding.\n"
        "   - Usa el menú persistente para acceder rápido a las funciones principales.\n\n"
        "2. **Registrar movimientos**\n"
        "   - Escribe o graba un audio como si fuera tu amigo: _'Gaste 20 lucas en almuerzo'_\n"
        "   - O mándame una foto de la factura y la proceso automáticamente.\n\n"
        "3. **Seguir tus finanzas**\n"
        "   - *📊 Reporte* genera un gráfico con la distribución de gastos.\n"
        "   - *📈 Dashboard* abre un panel web temporal con más métricas.\n"
        "   - /exportar descarga un Excel con todas tus transacciones.\n\n"
        "4. **Control y alertas**\n"
        "   - Desde *🎯 Metas* puedes crear objetivos o aportar a los existentes.\n"
        "   - *⚖️ Presupuestos* te deja configurar y revisar tus límites mensuales.\n"
        "   - *⚙️ Ajustes* ofrece utilidades adicionales como resetear la cuenta.\n\n"
        "¿Ideas o mejoras? ¡Escríbeme por este chat!"
    )

    await query.edit_message_text(
        guide_text,
        parse_mode="Markdown",
        reply_markup=build_settings_menu_keyboard(),
    )


