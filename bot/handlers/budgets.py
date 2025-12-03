"""Budget management handlers."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from bot.common import get_logger, log_handler_invocation
from bot.utils.callback_manager import CallbackManager
from bot.utils.time_utils import get_now_utc
from bot.conversation_states import (
    BUDGET_AMOUNT_INPUT,
    BUDGET_CATEGORY_SELECT,
)
from bot.keyboards import (
    build_budgets_menu_keyboard,
    build_category_action_keyboard,
)
from bot.utils.amounts import format_currency, parse_amount
from database import SessionLocal
from models import Budget, Category, CategoryType, Transaction

logger = get_logger("handlers.budgets")


async def budgets_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler para el menú de presupuestos. Comando global que cancela cualquier flujo activo."""
    log_handler_invocation(logger, "budgets_menu", update)
    telegram_user = update.effective_user
    message = update.message

    if not telegram_user or not message:
        return ConversationHandler.END

    # Limpiar estado de conversación para cancelar cualquier flujo activo
    context.user_data.clear()

    await message.reply_text(
        "Gestiona tus presupuestos:",
        reply_markup=build_budgets_menu_keyboard(),
    )
    return ConversationHandler.END


async def start_budget(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "start_budget", update)
    telegram_user = update.effective_user
    if not telegram_user:
        return ConversationHandler.END

    with SessionLocal() as session:
        categories = [
            category
            for category in session.execute(
                select(Category)
                .where(
                    Category.user_id == telegram_user.id,
                    Category.type == CategoryType.EXPENSE,
                )
                .order_by(Category.name)
            ).scalars()
        ]

    if not categories:
        response_text = (
            "No encontré categorías de gasto. Crea una desde el menú de categorías antes de configurar un presupuesto."
        )
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(response_text)
        elif update.message:
            await update.message.reply_text(response_text)
        return ConversationHandler.END

    # Usar CallbackManager para generar callbacks de categorías de presupuesto
    rows = []
    current_row = []
    for category in categories:
        current_row.append(
            InlineKeyboardButton(
                text=category.name,
                callback_data=CallbackManager.budget_category(category.id),
            )
        )
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)
    keyboard = InlineKeyboardMarkup(rows)
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "¿Para qué categoría quieres un presupuesto?",
            reply_markup=keyboard,
        )
    elif update.message:
        await update.message.reply_text(
            "¿Para qué categoría quieres un presupuesto?",
            reply_markup=keyboard,
        )
    else:
        return ConversationHandler.END
    return BUDGET_CATEGORY_SELECT


async def budget_category_selected(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "budget_category_selected", update)
    query = update.callback_query
    await query.answer()

    try:
        category_id = CallbackManager.parse_budget_category(query.data)
    except ValueError as e:
        logger.warning("Error parsing budget category callback: %s", e)
        await query.edit_message_text(
            "Selección inválida. Usa la opción de presupuestos para intentarlo nuevamente."
        )
        return ConversationHandler.END

    telegram_user = update.effective_user
    if not telegram_user:
        return ConversationHandler.END

    with SessionLocal() as session:
        category = session.get(Category, category_id)
        if (
            not category
            or category.user_id != telegram_user.id
            or category.type != CategoryType.EXPENSE
        ):
            await query.edit_message_text(
                "No pude identificar la categoría seleccionada. Intenta nuevamente desde Presupuestos."
            )
            return ConversationHandler.END

    context.user_data["budget_flow"] = {"category_id": category_id}
    await query.edit_message_text("¿Cuál es el monto mensual?")
    return BUDGET_AMOUNT_INPUT


async def budget_amount_received(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "budget_amount_received", update)
    flow = context.user_data.get("budget_flow")
    if not flow:
        await update.message.reply_text(
            "Perdí la categoría seleccionada. Empieza de nuevo desde el menú de Presupuestos."
        )
        return ConversationHandler.END

    try:
        amount = parse_amount(update.message.text)
    except Exception:
        await update.message.reply_text("Monto inválido. Ingresa un número positivo.")
        return BUDGET_AMOUNT_INPUT

    telegram_user = update.effective_user
    if not telegram_user:
        return ConversationHandler.END

    category_id = flow.get("category_id")

    # Calcular fechas del mes actual
    now = get_now_utc()
    month_start = date(now.year, now.month, 1)
    last_day = monthrange(now.year, now.month)[1]
    month_end = date(now.year, now.month, last_day)

    with SessionLocal() as session:
        budget = session.execute(
            select(Budget)
            .where(
                Budget.user_id == telegram_user.id,
                Budget.category_id == category_id,
            )
            .limit(1)
        ).scalar_one_or_none()

        if budget:
            budget.amount = amount
            budget.start_date = month_start
            budget.end_date = month_end
        else:
            budget = Budget(
                user_id=telegram_user.id,
                category_id=category_id,
                amount=amount,
                start_date=month_start,
                end_date=month_end,
            )
            session.add(budget)
        session.commit()

        category = session.get(Category, category_id)
        category_name = category.name if category else "Categoría"

    context.user_data.pop("budget_flow", None)

    # Teclado de navegación después de guardar
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

    await update.message.reply_text(
        f"Presupuesto guardado correctamente.\n\n"
        f"Presupuesto mensual para {category_name}: {format_currency(amount)}.\n\n"
        f"¿Qué deseas hacer ahora?",
        reply_markup=navigation_keyboard,
    )
    return ConversationHandler.END


async def view_budgets(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    log_handler_invocation(logger, "view_budgets", update)
    telegram_user = update.effective_user
    chat = update.effective_chat
    query = update.callback_query
    if query:
        await query.answer()

    if not telegram_user or not chat:
        return

    now = get_now_utc()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1)

    with SessionLocal() as session:
        budgets = list(
            session.execute(
                select(Budget)
                .where(Budget.user_id == telegram_user.id)
                .options(joinedload(Budget.category))
            ).scalars()
        )

        if not budgets:
            response_text = (
                "Aún no tienes presupuestos configurados.\n\n"
                "Elige 'Configurar presupuesto' para crear uno."
            )
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "➕ Configurar presupuesto",
                            callback_data="budgets:create",
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
            if query:
                await query.edit_message_text(response_text, reply_markup=keyboard)
            else:
                await context.bot.send_message(
                    chat_id=chat.id,
                    text=response_text,
                    reply_markup=keyboard,
                )
            return

        lines: List[str] = []
        for budget in budgets:
            category_name = budget.category.name if budget.category else "Categoría"
            spent_value = session.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.user_id == telegram_user.id,
                    Transaction.category_id == budget.category_id,
                    Transaction.transaction_date >= month_start,
                    Transaction.transaction_date < next_month,
                )
            ).scalar()

            if spent_value is None:
                spent = Decimal("0")
            elif isinstance(spent_value, Decimal):
                spent = spent_value
            else:
                spent = Decimal(spent_value)

            budget_amount_value = budget.amount or Decimal("0")
            budget_amount = (
                budget_amount_value
                if isinstance(budget_amount_value, Decimal)
                else Decimal(budget_amount_value)
            )
            if budget_amount <= 0:
                percentage = Decimal("0")
            else:
                percentage = (
                    spent / budget_amount * Decimal("100")
                ).quantize(Decimal("0.01"))

            lines.append(
                f"{category_name}: {format_currency(spent)} / {format_currency(budget_amount)} gastados ({percentage}%)."
            )

    response = "\n".join(lines)
    if query:
        await query.edit_message_text(response)
    else:
        await context.bot.send_message(chat_id=chat.id, text=response)


async def cancel_budget_flow(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "cancel_budget_flow", update)
    context.user_data.pop("budget_flow", None)
    await update.message.reply_text("Gestión de presupuesto cancelada.")
    return ConversationHandler.END


