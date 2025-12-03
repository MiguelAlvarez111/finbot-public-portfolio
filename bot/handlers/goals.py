"""Goal management handlers."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import List

from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from bot.common import get_logger, log_handler_invocation
from bot.utils.callback_manager import CallbackManager
from bot.conversation_states import (
    GOAL_CONTRIBUTION_AMOUNT,
    GOAL_CONTRIBUTION_SELECT,
    GOAL_NAME_INPUT,
    GOAL_TARGET_INPUT,
)
from bot.keyboards import build_goals_menu_keyboard
from bot.utils.amounts import format_currency, parse_amount
from database import SessionLocal
from models import Goal

logger = get_logger("handlers.goals")


async def goals_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler para el menú de metas. Comando global que cancela cualquier flujo activo."""
    log_handler_invocation(logger, "goals_menu", update)
    telegram_user = update.effective_user
    message = update.message

    if not telegram_user or not message:
        return ConversationHandler.END

    # Limpiar estado de conversación para cancelar cualquier flujo activo
    context.user_data.clear()

    await message.reply_text(
        "¿Qué quieres hacer con tus metas?",
        reply_markup=build_goals_menu_keyboard(),
    )
    return ConversationHandler.END


async def start_goal_creation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "start_goal_creation", update)
    telegram_user = update.effective_user
    if not telegram_user:
        return ConversationHandler.END

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("¿Cuál es el nombre de la meta?")
    elif update.message:
        await update.message.reply_text("¿Cuál es el nombre de la meta?")
    else:
        return ConversationHandler.END

    return GOAL_NAME_INPUT


async def goal_name_received(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "goal_name_received", update)
    name = (update.message.text or "").strip()
    if not name:
        await update.message.reply_text(
            "Necesito un nombre válido para la meta."
        )
        return GOAL_NAME_INPUT

    context.user_data["goal_creation"] = {"name": name}
    await update.message.reply_text("¿Cuál es el monto objetivo?")
    return GOAL_TARGET_INPUT


async def goal_target_received(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "goal_target_received", update)
    data = context.user_data.get("goal_creation")
    if not data:
        await update.message.reply_text(
            "Perdí el nombre de la meta. Inicia otra vez desde el menú de Metas."
        )
        return ConversationHandler.END

    try:
        target_amount = parse_amount(update.message.text)
    except (InvalidOperation, AttributeError):
        await update.message.reply_text(
            "Monto inválido. Ingresa un número positivo."
        )
        return GOAL_TARGET_INPUT

    telegram_user = update.effective_user
    if not telegram_user:
        return ConversationHandler.END

    name = data["name"]

    with SessionLocal() as session:
        goal = session.execute(
            select(Goal)
            .where(Goal.user_id == telegram_user.id, Goal.name == name)
            .limit(1)
        ).scalar_one_or_none()

        if goal:
            goal.target_amount = target_amount
            if goal.current_amount is None:
                goal.current_amount = Decimal("0")
        else:
            goal = Goal(
                user_id=telegram_user.id,
                name=name,
                target_amount=target_amount,
                current_amount=Decimal("0"),
            )
            session.add(goal)
        session.commit()

    context.user_data.pop("goal_creation", None)
    await update.message.reply_text(
        f"Meta '{name}' configurada con un objetivo de {format_currency(target_amount)}."
    )
    return ConversationHandler.END


async def cancel_goal_creation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "cancel_goal_creation", update)
    context.user_data.pop("goal_creation", None)
    await update.message.reply_text("Creación de meta cancelada.")
    return ConversationHandler.END


async def start_goal_contribution(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "start_goal_contribution", update)
    telegram_user = update.effective_user
    if not telegram_user:
        return ConversationHandler.END

    with SessionLocal() as session:
        goals = [
            goal
            for goal in session.execute(
                select(Goal)
                .where(Goal.user_id == telegram_user.id)
                .order_by(Goal.name)
            ).scalars()
        ]

    if not goals:
        response_text = (
            "No tienes metas registradas. Usa la opción 'Crear meta' para agregar una."
        )
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(response_text)
        elif update.message:
            await update.message.reply_text(response_text)
        return ConversationHandler.END

    rows: List[List[InlineKeyboardButton]] = []
    current_row: List[InlineKeyboardButton] = []
    for goal in goals:
        current_row.append(
            InlineKeyboardButton(goal.name, callback_data=CallbackManager.goal_contribution(goal.id))
        )
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)

    reply_markup = InlineKeyboardMarkup(rows)

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "Selecciona la meta a la que quieres aportar:",
            reply_markup=reply_markup,
        )
    elif update.message:
        await update.message.reply_text(
            "Selecciona la meta a la que quieres aportar:",
            reply_markup=reply_markup,
        )
    else:
        return ConversationHandler.END

    return GOAL_CONTRIBUTION_SELECT


async def goal_contribution_selected(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "goal_contribution_selected", update)
    query = update.callback_query
    await query.answer()

    try:
        goal_id = CallbackManager.parse_goal_contribution(query.data)
    except (ValueError, IndexError):
        await query.edit_message_text(
            "Selección inválida. Usa la opción 'Aportar a meta' para intentarlo nuevamente."
        )
        return ConversationHandler.END

    telegram_user = update.effective_user
    if not telegram_user:
        return ConversationHandler.END

    with SessionLocal() as session:
        goal = session.get(Goal, goal_id)
        if not goal or goal.user_id != telegram_user.id:
            await query.edit_message_text(
                "No pude encontrar la meta seleccionada. Intenta de nuevo desde el menú de Metas."
            )
            return ConversationHandler.END

    context.user_data["goal_contribution"] = {
        "goal_id": goal_id,
        "goal_name": goal.name,
    }

    await query.edit_message_text(
        f"Meta: {goal.name}\n¿Cuánto deseas aportar?"
    )
    return GOAL_CONTRIBUTION_AMOUNT


async def goal_contribution_amount_received(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "goal_contribution_amount_received", update)
    data = context.user_data.get("goal_contribution")
    if not data:
        await update.message.reply_text(
            "Perdí la meta seleccionada. Empieza nuevamente desde el menú de Metas."
        )
        return ConversationHandler.END

    try:
        contribution = parse_amount(update.message.text)
    except (InvalidOperation, AttributeError):
        await update.message.reply_text(
            "Monto inválido. Ingresa un número positivo."
        )
        return GOAL_CONTRIBUTION_AMOUNT

    telegram_user = update.effective_user
    if not telegram_user:
        return ConversationHandler.END

    goal_id = data["goal_id"]

    with SessionLocal() as session:
        goal = session.get(Goal, goal_id)
        if not goal or goal.user_id != telegram_user.id:
            await update.message.reply_text(
                "No pude encontrar la meta. Empieza nuevamente desde Metas."
            )
            context.user_data.pop("goal_contribution", None)
            return ConversationHandler.END

        current_amount = goal.current_amount or Decimal("0")
        goal.current_amount = current_amount + contribution
        session.commit()

        target_amount = goal.target_amount or Decimal("0")
        if target_amount > 0:
            progress = (
                goal.current_amount / target_amount * Decimal("100")
            ).quantize(Decimal("0.01"))
        else:
            progress = Decimal("0")

        response = (
            f"Aporte registrado para '{goal.name}'.\n"
            f"Acumulado: {format_currency(goal.current_amount)} / {format_currency(target_amount)} ({progress}%)."
        )

    context.user_data.pop("goal_contribution", None)
    await update.message.reply_text(response)
    return ConversationHandler.END


async def cancel_goal_contribution(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "cancel_goal_contribution", update)
    context.user_data.pop("goal_contribution", None)
    await update.message.reply_text("Aporte a meta cancelado.")
    return ConversationHandler.END


