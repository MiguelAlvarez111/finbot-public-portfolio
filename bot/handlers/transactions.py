"""Expense and income flow handlers."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional

from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from bot.common import get_logger, log_handler_invocation
from bot.utils.callback_manager import CallbackManager
from bot.utils.time_utils import get_now_utc
from bot.conversation_states import (
    EXPENSE_AMOUNT,
    EXPENSE_CATEGORY,
    EXPENSE_DESCRIPTION_DECISION,
    EXPENSE_DESCRIPTION_INPUT,
    INCOME_AMOUNT,
    INCOME_CATEGORY,
)
from bot.keyboards import build_category_keyboard
from bot.services.categories import create_default_categories, get_default_category
from bot.utils.amounts import format_currency, parse_amount
from database import SessionLocal
from models import Category, CategoryType, Transaction

logger = get_logger("handlers.transactions")


def _store_pending_transaction(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    amount: Decimal,
    category_type: CategoryType,
) -> None:
    context.user_data["pending_transaction"] = {
        "amount": amount,
        "type": category_type.value,
    }


def _get_pending_transaction(
    context: ContextTypes.DEFAULT_TYPE,
) -> Optional[Dict[str, object]]:
    return context.user_data.get("pending_transaction")


def _clear_pending_transaction(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("pending_transaction", None)


async def _send_category_prompt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    category_type: CategoryType,
) -> None:
    log_handler_invocation(logger, "send_category_prompt", update)
    telegram_user = update.effective_user
    if not telegram_user:
        return

    with SessionLocal() as session:
        create_default_categories(session, telegram_user.id)
        categories = [
            category
            for category in session.execute(
                select(Category)
                .where(
                    Category.user_id == telegram_user.id,
                    Category.type == category_type,
                )
                .order_by(Category.name)
            ).scalars()
        ]

    if not categories:
        await update.message.reply_text(
            "No encontré categorías para este tipo. Escribe una descripción para usar la categoría general."
        )
        return

    keyboard = build_category_keyboard(categories)

    await update.message.reply_text(
        "¿En qué categoría? (o escribe una descripción)",
        reply_markup=keyboard,
    )


async def start_expense(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "start_expense", update)
    await update.message.reply_text("¿Cuál es el monto?")
    context.user_data["pending_transaction"] = {"type": CategoryType.EXPENSE.value}
    return EXPENSE_AMOUNT


async def expense_amount_received(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "expense_amount_received", update)
    try:
        amount = parse_amount(update.message.text)
    except (InvalidOperation, AttributeError):
        await update.message.reply_text(
            "Monto no válido. Intenta nuevamente con un número positivo."
        )
        return EXPENSE_AMOUNT

    _store_pending_transaction(
        context,
        amount=amount,
        category_type=CategoryType.EXPENSE,
    )
    await _send_category_prompt(update, context, CategoryType.EXPENSE)
    return EXPENSE_CATEGORY


async def expense_category_selected(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "expense_category_selected", update)
    query = update.callback_query
    await query.answer()

    pending = _get_pending_transaction(context)
    if not pending:
        await query.edit_message_text(
            "No pude recuperar la información del monto. Intenta con /gasto de nuevo."
        )
        return ConversationHandler.END

    amount = pending.get("amount")
    if amount is None:
        await query.edit_message_text(
            "No pude recuperar la información del monto. Intenta con /gasto de nuevo."
        )
        _clear_pending_transaction(context)
        return ConversationHandler.END

    try:
        category_id = CallbackManager.parse_category(query.data)
    except ValueError as e:
        logger.warning("Error parsing category callback: %s", e)
        await query.edit_message_text(
            "Selección inválida. Usa /gasto para intentarlo nuevamente."
        )
        _clear_pending_transaction(context)
        return ConversationHandler.END

    telegram_user = update.effective_user
    if not telegram_user:
        await query.edit_message_text(
            "No pude identificar al usuario. Intenta con /gasto de nuevo."
        )
        _clear_pending_transaction(context)
        return ConversationHandler.END

    with SessionLocal() as session:
        category = session.get(Category, category_id)
        if not category or category.user_id != telegram_user.id:
            await query.edit_message_text(
                "No pude identificar la categoría seleccionada. Usa /gasto para intentarlo nuevamente."
            )
            _clear_pending_transaction(context)
            return ConversationHandler.END

    pending["category_id"] = category_id
    pending["category_name"] = category.name

    await query.edit_message_text(
        f"Registrarás {format_currency(amount)} en la categoría {category.name}. ¿Quieres agregar una descripción?",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Sí, agregar", callback_data=CallbackManager.expense_desc("yes")
                    ),
                    InlineKeyboardButton(
                        "No, guardar", callback_data=CallbackManager.expense_desc("no")
                    ),
                ]
            ]
        ),
    )
    return EXPENSE_DESCRIPTION_DECISION


async def expense_description_decision(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "expense_description_decision", update)
    query = update.callback_query
    await query.answer()

    pending = _get_pending_transaction(context)
    if not pending:
        await query.edit_message_text(
            "No encontré la información previa. Usa /gasto para empezar otra vez."
        )
        return ConversationHandler.END

    amount = pending.get("amount")
    category_id = pending.get("category_id")
    category_name = pending.get("category_name")
    if amount is None or category_id is None:
        await query.edit_message_text(
            "Perdí algunos datos del registro. Empieza nuevamente con /gasto."
        )
        _clear_pending_transaction(context)
        return ConversationHandler.END

    telegram_user = update.effective_user
    if not telegram_user:
        _clear_pending_transaction(context)
        await query.edit_message_text(
            "No pude identificar al usuario. Empieza nuevamente con /gasto."
        )
        return ConversationHandler.END

    try:
        choice = CallbackManager.parse_expense_desc(query.data)
    except ValueError as e:
        logger.warning("Error parsing expense_desc callback: %s", e)
        await query.edit_message_text(
            "Error al procesar la selección. Intenta nuevamente."
        )
        return ConversationHandler.END

    if choice == "yes":
        await query.edit_message_text("Perfecto, escribe la descripción del gasto.")
        return EXPENSE_DESCRIPTION_INPUT

    if choice == "no":
        with SessionLocal() as session:
            transaction = Transaction(
                user_id=telegram_user.id,
                category_id=category_id,
                amount=amount,
                description=None,
            )
            session.add(transaction)
            session.commit()

        _clear_pending_transaction(context)
        await query.edit_message_text(
            f"Gasto registrado correctamente en la categoría {category_name or 'seleccionada'}.\n\n"
            "💡 **Tip:** La próxima vez no necesitas comandos. Solo escríbeme 'Gaste 50k' y yo hago el resto.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    await query.edit_message_text("Opción inválida. Empieza nuevamente con /gasto.")
    _clear_pending_transaction(context)
    return ConversationHandler.END


async def expense_description_received(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    log_handler_invocation(logger, "expense_description_received", update)
    pending = _get_pending_transaction(context)
    if not pending:
        await update.message.reply_text(
            "No encontré un monto previo. Usa /gasto para empezar otra vez."
        )
        return ConversationHandler.END

    amount = pending.get("amount")
    if amount is None:
        await update.message.reply_text(
            "No pude recuperar el monto. Usa /gasto para empezar otra vez."
        )
        _clear_pending_transaction(context)
        return ConversationHandler.END

    description = update.message.text.strip()
    if not description:
        await update.message.reply_text("Necesito una descripción válida.")
        return (
            EXPENSE_DESCRIPTION_INPUT
            if pending.get("category_id")
            else EXPENSE_CATEGORY
        )

    user_id = update.effective_user.id
    category_id = pending.get("category_id")

    with SessionLocal() as session:
        if category_id is not None:
            category = session.get(Category, category_id)
            if not category or category.user_id != user_id:
                await update.message.reply_text(
                    "La categoría seleccionada ya no está disponible. Empieza nuevamente con /gasto."
                )
                _clear_pending_transaction(context)
                return ConversationHandler.END
        else:
            category = get_default_category(
                session, user_id, CategoryType.EXPENSE
            )
            if not category:
                await update.message.reply_text(
                    "No existe una categoría general. Crea una categoría y vuelve a intentarlo."
                )
                return ConversationHandler.END

        transaction = Transaction(
            user_id=user_id,
            category_id=category.id,
            amount=amount,
            description=description,
        )
        session.add(transaction)
        session.commit()
        category_name = category.name

    _clear_pending_transaction(context)

    await update.message.reply_text(
        f"Gasto registrado correctamente en la categoría {category_name}.\n\n"
        "💡 **Tip:** La próxima vez no necesitas comandos. Solo escríbeme 'Gaste 50k' y yo hago el resto.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def start_income(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "start_income", update)
    await update.message.reply_text("¿Cuál es el monto?")
    context.user_data["pending_transaction"] = {"type": CategoryType.INCOME.value}
    return INCOME_AMOUNT


async def income_amount_received(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "income_amount_received", update)
    try:
        amount = parse_amount(update.message.text)
    except (InvalidOperation, AttributeError):
        await update.message.reply_text(
            "Monto no válido. Intenta nuevamente con un número positivo."
        )
        return INCOME_AMOUNT

    _store_pending_transaction(
        context,
        amount=amount,
        category_type=CategoryType.INCOME,
    )
    await _send_category_prompt(update, context, CategoryType.INCOME)
    return INCOME_CATEGORY


async def income_category_selected(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "income_category_selected", update)
    query = update.callback_query
    await query.answer()

    pending = _get_pending_transaction(context)
    if not pending:
        await query.edit_message_text(
            "No pude recuperar la información del monto. Intenta con /ingreso de nuevo."
        )
        return ConversationHandler.END

    amount = pending.get("amount")
    if amount is None:
        await query.edit_message_text(
            "No pude recuperar la información del monto. Intenta con /ingreso de nuevo."
        )
        _clear_pending_transaction(context)
        return ConversationHandler.END

    try:
        category_id = CallbackManager.parse_category(query.data)
    except ValueError as e:
        logger.warning("Error parsing category callback: %s", e)
        await query.edit_message_text(
            "Selección inválida. Usa /ingreso para intentarlo nuevamente."
        )
        _clear_pending_transaction(context)
        return ConversationHandler.END
    user_id = update.effective_user.id

    with SessionLocal() as session:
        category_name = None
        transaction = Transaction(
            user_id=user_id,
            category_id=category_id,
            amount=amount,
        )
        session.add(transaction)
        session.commit()

        category = session.get(Category, category_id)
        if category:
            category_name = category.name

    _clear_pending_transaction(context)

    await query.edit_message_text(
        f"Ingreso registrado correctamente en la categoría {category_name or 'seleccionada'}.\n\n"
        "💡 **Tip:** La próxima vez no necesitas comandos. Solo escríbeme 'Recibí 500k' y yo hago el resto.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def income_description_received(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    log_handler_invocation(logger, "income_description_received", update)
    pending = _get_pending_transaction(context)
    if not pending:
        await update.message.reply_text(
            "No encontré un monto previo. Usa /ingreso para empezar otra vez."
        )
        return ConversationHandler.END

    amount = pending.get("amount")
    if amount is None:
        await update.message.reply_text(
            "No pude recuperar el monto. Usa /ingreso para empezar otra vez."
        )
        _clear_pending_transaction(context)
        return ConversationHandler.END

    description = update.message.text.strip()
    if not description:
        await update.message.reply_text(
            "Necesito una descripción válida o elige una categoría."
        )
        return INCOME_CATEGORY

    user_id = update.effective_user.id

    with SessionLocal() as session:
        category = get_default_category(
            session, user_id, CategoryType.INCOME
        )
        if not category:
            await update.message.reply_text(
                "No existe una categoría general de ingresos. Crea una categoría y vuelve a intentarlo."
            )
            return ConversationHandler.END
        category_name = category.name
        transaction = Transaction(
            user_id=user_id,
            category_id=category.id,
            amount=amount,
            description=description,
        )
        session.add(transaction)
        session.commit()

    _clear_pending_transaction(context)

    await update.message.reply_text(
        f"Ingreso registrado correctamente en la categoría {category_name}.\n\n"
        "💡 **Tip:** La próxima vez no necesitas comandos. Solo escríbeme 'Recibí 500k' y yo hago el resto.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def cancel_transaction(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "cancel_transaction", update)
    _clear_pending_transaction(context)
    await update.message.reply_text(
        "Registro cancelado. Usa el menú principal para intentarlo nuevamente."
    )
    return ConversationHandler.END


def _format_transaction_button_text(transaction: Transaction) -> str:
    now = get_now_utc().date()
    tx_date = transaction.transaction_date.date()

    if tx_date == now:
        date_label = "Hoy"
    else:
        date_label = transaction.transaction_date.strftime("%d %b").capitalize()

    amount = f"{transaction.amount:.2f}".rstrip("0").rstrip(".")
    description = transaction.description or "Sin descripción"
    return f"{date_label} - {amount} - {description}"


async def show_recent_transactions(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    log_handler_invocation(logger, "show_recent_transactions", update)
    telegram_user = update.effective_user
    if not telegram_user:
        return

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
        await update.message.reply_text("No encontré transacciones recientes.")
        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=_format_transaction_button_text(transaction),
                    callback_data=f"del_tx_{transaction.id}",
                )
            ]
            for transaction in transactions
        ]
    )

    await update.message.reply_text(
        "Selecciona una transacción para eliminarla:", reply_markup=keyboard
    )


async def delete_transaction_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    log_handler_invocation(logger, "delete_transaction_callback", update)
    query = update.callback_query
    await query.answer()

    try:
        transaction_id = CallbackManager.parse_delete_transaction(query.data)
    except (ValueError, IndexError):
        await query.edit_message_text(
            "No pude interpretar la transacción seleccionada. Usa /ultimos para intentarlo de nuevo."
        )
        return

    telegram_user = update.effective_user
    if not telegram_user:
        await query.edit_message_text("No pude identificar al usuario.")
        return

    with SessionLocal() as session:
        transaction = session.get(Transaction, transaction_id)
        if not transaction or transaction.user_id != telegram_user.id:
            await query.edit_message_text(
                "No encontré la transacción, tal vez ya fue eliminada."
            )
            return

        session.delete(transaction)
        session.commit()

    # Mostrar confirmación con botones de navegación
    navigation_keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⬅️ Volver a ajustes",
                    callback_data=CallbackManager.settings("back"),
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Volver al menú",
                    callback_data=CallbackManager.settings("back_to_menu"),
                )
            ],
        ]
    )

    await query.edit_message_text(
        "Transacción eliminada correctamente.\n\n¿Qué deseas hacer ahora?",
        reply_markup=navigation_keyboard,
    )


