"""Common utilities for bot handlers."""

from __future__ import annotations

import logging
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger under the `bot` hierarchy."""
    return logging.getLogger(f"bot.{name}")


async def debug_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log updates at debug level for traceability."""
    logger = get_logger("debug")
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    logger.debug(
        "Update recibido user_id=%s chat_id=%s raw=%s",
        user_id,
        chat_id,
        update.to_dict() if hasattr(update, "to_dict") else str(update),
    )


async def log_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Centralised error logging for the application."""
    logger = get_logger("error")
    update_repr: Optional[str]
    if isinstance(update, Update):
        try:
            update_repr = update.to_dict()
        except Exception:  # pragma: no cover - best effort logging
            update_repr = repr(update)
    else:
        update_repr = repr(update)

    logger.exception(
        "Error no controlado procesando update=%s: %s",
        update_repr,
        context.error,
    )


def log_handler_invocation(
    logger: logging.Logger,
    handler_name: str,
    update: Optional[Update],
) -> None:
    """Log metadata when a handler is invoked to aid debugging."""
    if not logger.isEnabledFor(logging.INFO):
        return

    if not update:
        logger.info("[%s] Invocado sin update.", handler_name)
        return

    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    message_text = (
        update.message.text if update.message and update.message.text else None
    )
    callback_data = update.callback_query.data if update.callback_query else None
    logger.info(
        "[%s] user_id=%s chat_id=%s message=%r callback=%r",
        handler_name,
        user_id,
        chat_id,
        message_text,
        callback_data,
    )


