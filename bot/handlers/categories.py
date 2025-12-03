"""Category management handlers."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from bot.common import get_logger, log_handler_invocation
from bot.utils.callback_manager import CallbackManager, CallbackType
from bot.conversation_states import (
    CATEGORY_ADD_NAME,
    CATEGORY_ADD_TYPE,
    CATEGORY_MENU,
    CATEGORY_RENAME_NAME,
    CATEGORY_RENAME_SELECT,
)
from bot.keyboards import (
    build_category_action_keyboard,
    category_management_keyboard,
)
from bot.services.categories import fetch_user_categories
from database import SessionLocal
from models import Category, CategoryType

logger = get_logger("handlers.categories")


async def category_management_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    text: Optional[str] = None,
) -> int:
    log_handler_invocation(logger, "category_management_menu", update)
    target_text = text or "Gestión de categorías. ¿Qué te gustaría hacer?"
    if update.callback_query:
        await update.callback_query.edit_message_text(
            target_text,
            reply_markup=category_management_keyboard(),
        )
    else:
        await update.message.reply_text(
            target_text, reply_markup=category_management_keyboard()
        )
    return CATEGORY_MENU


async def category_menu_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "category_menu_selection", update)
    query = update.callback_query
    await query.answer()
    try:
        action = CallbackManager.parse_category_manage(query.data)
    except ValueError as e:
        logger.warning("Error parsing category manage callback: %s", e)
        await query.edit_message_text(
            "Error al procesar la selección. Intenta nuevamente con /categorias."
        )
        return ConversationHandler.END

    if action == "add":
        context.user_data["category_operation"] = {}
        await query.edit_message_text("¿Cómo se llama la nueva categoría?")
        return CATEGORY_ADD_NAME

    user_id = update.effective_user.id
    with SessionLocal() as session:
        categories = fetch_user_categories(session, user_id)

    if action == "delete":
        if not categories:
            await query.edit_message_text(
                "No encontré categorías registradas. Empieza creando una con el botón Agregar."
            )
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Gestión de categorías. ¿Qué te gustaría hacer?",
                reply_markup=category_management_keyboard(),
            )
            return CATEGORY_MENU

        # Construir teclado con CallbackManager
        rows = []
        current_row = []
        for category in categories:
            current_row.append(
                InlineKeyboardButton(
                    text=category.name,
                    callback_data=CallbackManager.delete_category(category.id),
                )
            )
            if len(current_row) == 2:
                rows.append(current_row)
                current_row = []
        if current_row:
            rows.append(current_row)
            await query.edit_message_text(
                "Selecciona la categoría que deseas eliminar:",
                reply_markup=InlineKeyboardMarkup(rows),
            )
        return CATEGORY_MENU

    if action == "rename":
        if not categories:
            await query.edit_message_text(
                "No encontré categorías para renombrar. Empieza creando una con el botón Agregar."
            )
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Gestión de categorías. ¿Qué te gustaría hacer?",
                reply_markup=category_management_keyboard(),
            )
            return CATEGORY_MENU

        # Construir teclado con CallbackManager
        rows = []
        current_row = []
        for category in categories:
            current_row.append(
                InlineKeyboardButton(
                    text=category.name,
                    callback_data=CallbackManager.rename_category(category.id),
                )
            )
            if len(current_row) == 2:
                rows.append(current_row)
                current_row = []
        if current_row:
            rows.append(current_row)
        await query.edit_message_text(
            "Selecciona la categoría que quieres renombrar:",
            reply_markup=InlineKeyboardMarkup(rows),
        )
        return CATEGORY_RENAME_SELECT

    await query.edit_message_text("Acción no reconocida. Intenta nuevamente con /categorias.")
    return ConversationHandler.END


async def category_add_name_received(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "category_add_name_received", update)
    name = update.message.text.strip()

    if not name:
        await update.message.reply_text(
            "Necesito un nombre válido para la categoría. Intenta de nuevo."
        )
        return CATEGORY_ADD_NAME

    context.user_data.setdefault("category_operation", {})
    context.user_data["category_operation"]["name"] = name

    await update.message.reply_text(
        "¿De qué tipo es la categoría?",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Ingreso", callback_data=CallbackManager.category_add_type("income")
                    ),
                    InlineKeyboardButton(
                        "Gasto", callback_data=CallbackManager.category_add_type("expense")
                    ),
                ]
            ]
        ),
    )
    return CATEGORY_ADD_TYPE


async def category_add_type_selected(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "category_add_type_selected", update)
    query = update.callback_query
    await query.answer()

    operation = context.user_data.get("category_operation", {})
    name = operation.get("name")

    if not name:
        await query.edit_message_text(
            "Perdí el nombre de la categoría. Vuelve a intentarlo con /categorias."
        )
        context.user_data.pop("category_operation", None)
        return ConversationHandler.END

    try:
        type_value = CallbackManager.parse_category_add_type(query.data)
    except ValueError as e:
        logger.warning("Error parsing category add type callback: %s", e)
        await query.edit_message_text(
            "Error al procesar la selección. Intenta nuevamente con /categorias."
        )
        context.user_data.pop("category_operation", None)
        return ConversationHandler.END
    if type_value not in (CategoryType.INCOME.value, CategoryType.EXPENSE.value):
        await query.edit_message_text(
            "Tipo inválido. Usa /categorias para intentarlo de nuevo."
        )
        context.user_data.pop("category_operation", None)
        return ConversationHandler.END

    user_id = update.effective_user.id
    category_type = CategoryType(type_value)

    with SessionLocal() as session:
        existing = session.execute(
            select(Category)
            .where(
                Category.user_id == user_id,
                Category.name == name,
                Category.type == category_type,
            )
            .limit(1)
        ).scalar_one_or_none()

        if existing:
            await query.edit_message_text(
                "Ya tienes una categoría con ese nombre y tipo. Usa otro nombre."
            )
            context.user_data.pop("category_operation", None)
            return ConversationHandler.END

        new_category = Category(
            user_id=user_id,
            name=name,
            type=category_type,
            is_default=False,
        )
        session.add(new_category)
        session.commit()

    context.user_data.pop("category_operation", None)

    await query.edit_message_text(f"Categoría '{name}' creada correctamente.")
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Gestión de categorías. ¿Qué te gustaría hacer?",
        reply_markup=category_management_keyboard(),
    )
    return CATEGORY_MENU


async def category_delete_selected(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "category_delete_selected", update)
    query = update.callback_query
    await query.answer()

    try:
        category_id = CallbackManager.parse_delete_category(query.data)
    except ValueError as e:
        logger.warning("Error parsing delete category callback: %s", e)
        await query.edit_message_text(
            "Selección inválida. Usa /categorias para intentarlo de nuevo."
        )
        return ConversationHandler.END

    user_id = update.effective_user.id

    with SessionLocal() as session:
        category = session.get(Category, category_id)
        if not category or category.user_id != user_id:
            await query.edit_message_text(
                "No pude encontrar esa categoría. Intenta nuevamente."
            )
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Gestión de categorías. ¿Qué te gustaría hacer?",
                reply_markup=category_management_keyboard(),
            )
            return CATEGORY_MENU

        session.delete(category)
        session.commit()

    await query.edit_message_text("Categoría eliminada exitosamente.")
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Gestión de categorías. ¿Qué te gustaría hacer?",
        reply_markup=category_management_keyboard(),
    )
    return CATEGORY_MENU


async def category_rename_selected(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "category_rename_selected", update)
    query = update.callback_query
    await query.answer()

    try:
        category_id = CallbackManager.parse_rename_category(query.data)
    except ValueError as e:
        logger.warning("Error parsing rename category callback: %s", e)
        await query.edit_message_text(
            "Selección inválida. Usa /categorias para intentarlo de nuevo."
        )
        return ConversationHandler.END

    context.user_data["category_operation"] = {"category_id": category_id}
    await query.edit_message_text(
        "Escribe el nuevo nombre para la categoría seleccionada."
    )
    return CATEGORY_RENAME_NAME


async def category_rename_name_received(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "category_rename_name_received", update)
    new_name = update.message.text.strip()
    if not new_name:
        await update.message.reply_text(
            "Necesito un nombre válido. Intenta nuevamente."
        )
        return CATEGORY_RENAME_NAME

    operation = context.user_data.get("category_operation", {})
    category_id = operation.get("category_id")
    if not category_id:
        await update.message.reply_text(
            "Perdí el rastro de la categoría. Empieza de nuevo con /categorias."
        )
        context.user_data.pop("category_operation", None)
        return ConversationHandler.END

    user_id = update.effective_user.id

    with SessionLocal() as session:
        category = session.get(Category, category_id)
        if not category or category.user_id != user_id:
            await update.message.reply_text(
                "No pude encontrar esa categoría. Empieza de nuevo con /categorias."
            )
            context.user_data.pop("category_operation", None)
            return ConversationHandler.END

        duplicate = session.execute(
            select(Category)
            .where(
                Category.user_id == user_id,
                Category.type == category.type,
                Category.name == new_name,
                Category.id != category.id,
            )
            .limit(1)
        ).scalar_one_or_none()
        if duplicate:
            await update.message.reply_text(
                "Ya existe otra categoría con ese nombre en el mismo tipo. Usa un nombre diferente."
            )
            return CATEGORY_RENAME_NAME

        category.name = new_name
        session.commit()

    context.user_data.pop("category_operation", None)
    await update.message.reply_text(f"Categoría renombrada a '{new_name}'.")
    await update.message.reply_text(
        "Gestión de categorías. ¿Qué te gustaría hacer?",
        reply_markup=category_management_keyboard(),
    )
    return CATEGORY_MENU


async def cancel_category_management(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    log_handler_invocation(logger, "cancel_category_management", update)
    context.user_data.pop("category_operation", None)
    await update.message.reply_text("Gestión de categorías cancelada.")
    return ConversationHandler.END

