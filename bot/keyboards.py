"""Inline keyboard factories."""

from __future__ import annotations

from typing import Iterable, List, Sequence, Set

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from bot.utils.callback_manager import CallbackManager
from models import Category


def build_category_keyboard(categories: Iterable[Category]) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    current_row: List[InlineKeyboardButton] = []

    for category in categories:
        current_row.append(
            InlineKeyboardButton(
                text=category.name,
                callback_data=CallbackManager.category(category.id),
            )
        )
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []

    if current_row:
        rows.append(current_row)

    return InlineKeyboardMarkup(rows)


def build_category_action_keyboard(
    categories: Sequence[Category], *, prefix: str
) -> InlineKeyboardMarkup:
    """Construye teclado de categorías con prefijo dinámico.
    
    Args:
        categories: Lista de categorías.
        prefix: Prefijo del callback (ej: "dc:" para delete, "rc:" para rename, "bc:" para budget).
    
    Note:
        Este método mantiene compatibilidad con prefijos dinámicos, pero ahora
        se recomienda usar CallbackManager directamente en el código que llama.
    """
    rows: List[List[InlineKeyboardButton]] = []
    current_row: List[InlineKeyboardButton] = []

    for category in categories:
        current_row.append(
            InlineKeyboardButton(
                text=category.name,
                callback_data=f"{prefix}{category.id}",
            )
        )
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []

    if current_row:
        rows.append(current_row)

    return InlineKeyboardMarkup(rows)


def category_management_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("➕ Agregar", callback_data=CallbackManager.category_manage("add")),
                InlineKeyboardButton("➖ Eliminar", callback_data=CallbackManager.category_manage("delete")),
            ],
            [InlineKeyboardButton("✏️ Renombrar", callback_data=CallbackManager.category_manage("rename"))],
            [
                InlineKeyboardButton(
                    "⬅️ Volver a ajustes",
                    callback_data=CallbackManager.settings("back"),
                )
            ],
        ]
    )


def build_onboarding_category_keyboard(
    categories: Sequence[str],
    selected: Set[str],
) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    current_row: List[InlineKeyboardButton] = []

    for category in categories:
        prefix = "✅" if category in selected else "⬜️"
        current_row.append(
            InlineKeyboardButton(
                text=f"{prefix} {category}",
                callback_data=CallbackManager.onboarding("toggle", category),
            )
        )
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []

    if current_row:
        rows.append(current_row)

    rows.append(
        [
            InlineKeyboardButton(
                "Continuar ➡️",
                callback_data=CallbackManager.onboarding("next"),
            )
        ]
    )
    return InlineKeyboardMarkup(rows)


MAIN_MENU_LAYOUT = [
    ["📊 Reporte", "📈 Dashboard"],
    ["🎯 Metas", "⚙️ Ajustes"],
]


def build_main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        MAIN_MENU_LAYOUT,
        resize_keyboard=True,
        one_time_keyboard=False,
        is_persistent=True,
    )


def build_goals_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ Crear meta",
                    callback_data=CallbackManager.goals("create"),
                ),
                InlineKeyboardButton(
                    "📥 Aportar a meta",
                    callback_data=CallbackManager.goals("contribute"),
                ),
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Volver al menú",
                    callback_data=CallbackManager.settings("back_to_menu"),
                )
            ],
        ]
    )


def build_budgets_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ Configurar presupuesto",
                    callback_data=CallbackManager.budgets("create"),
                )
            ],
            [
                InlineKeyboardButton(
                    "📋 Ver presupuestos",
                    callback_data=CallbackManager.budgets("view"),
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


def build_settings_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⚖️ Presupuestos",
                    callback_data=CallbackManager.settings("budgets"),
                )
            ],
            [
                InlineKeyboardButton(
                    "🗂️ Gestionar categorías",
                    callback_data=CallbackManager.settings("categories"),
                )
            ],
            [
                InlineKeyboardButton(
                    "📊 Estadísticas rápidas",
                    callback_data=CallbackManager.settings("quick_stats"),
                )
            ],
            [
                InlineKeyboardButton(
                    "📥 Exportar datos (.xlsx)",
                    callback_data=CallbackManager.settings("export"),
                )
            ],
            [
                InlineKeyboardButton(
                    "⏮️ Ver últimos gastos",
                    callback_data=CallbackManager.settings("delete_recent"),
                )
            ],
            [
                InlineKeyboardButton(
                    "📚 Guía de Usuario",
                    callback_data=CallbackManager.settings("guide"),
                )
            ],
            [
                InlineKeyboardButton(
                    "🎮 Gamificación",
                    callback_data=CallbackManager.settings("gamification"),
                )
            ],
            [
                InlineKeyboardButton(
                    "🔄 Resetear cuenta",
                    callback_data=CallbackManager.settings("reset"),
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


def build_settings_reset_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Sí, borrar todo",
                    callback_data=CallbackManager.settings("confirm_reset"),
                ),
                InlineKeyboardButton(
                    "❌ Cancelar",
                    callback_data=CallbackManager.settings("cancel_reset"),
                ),
            ]
        ]
    )


