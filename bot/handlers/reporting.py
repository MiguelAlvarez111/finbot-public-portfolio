"""Reporting handlers with blocking workloads offloaded to threads."""

from __future__ import annotations

import asyncio
import io
from datetime import datetime, timezone

import matplotlib
import pandas as pd
from sqlalchemy import func, select, text
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from bot.common import get_logger, log_handler_invocation
from bot.utils.time_utils import get_now_utc
from database import SessionLocal, engine
from models import Category, CategoryType, Transaction

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  # isort:skip

logger = get_logger("handlers.reporting")


def _get_month_boundaries(reference: datetime) -> tuple[datetime, datetime]:
    start = reference.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def _generate_monthly_report_chart(
    user_id: int,
    month_start: datetime,
    next_month: datetime,
) -> io.BytesIO | None:
    with SessionLocal() as session:
        aggregate_query = (
            select(
                Category.name.label("category_name"),
                func.sum(Transaction.amount).label("total_amount"),
            )
            .join(Transaction, Transaction.category_id == Category.id)
            .where(
                Transaction.user_id == user_id,
                Category.type == CategoryType.EXPENSE,
                Transaction.transaction_date >= month_start,
                Transaction.transaction_date < next_month,
            )
            .group_by(Category.name)
            .order_by(func.sum(Transaction.amount).desc())
        )
        results = session.execute(aggregate_query).all()

    df = pd.DataFrame(
        [(row.category_name, row.total_amount) for row in results],
        columns=["category_name", "total_amount"],
    )

    if df.empty:
        return None

    df["total_amount"] = df["total_amount"].astype(float)

    fig, ax = plt.subplots(figsize=(7.5, 6))
    ax.pie(
        df["total_amount"],
        autopct="%1.1f%%",
        startangle=90,
        pctdistance=0.7,
    )
    ax.axis("equal")
    ax.set_title("Distribución de gastos del mes actual")
    ax.legend(
        df["category_name"],
        loc="center left",
        bbox_to_anchor=(1, 0.5),
        title="Categorías",
    )
    plt.tight_layout()

    image_buffer = io.BytesIO()
    fig.savefig(image_buffer, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    image_buffer.seek(0)
    return image_buffer


def generate_transactions_excel(user_id: int) -> io.BytesIO:
    query = text(
        """
        SELECT
            t.id,
            t.amount,
            t.transaction_date,
            t.description,
            c.name AS category_name,
            c.type AS category_type
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        WHERE t.user_id = :user_id
        ORDER BY t.transaction_date ASC
        """
    )

    with engine.connect() as connection:
        df = pd.read_sql(
            query,
            connection,
            params={"user_id": user_id},
        )

    if not df.empty:
        df["amount"] = df["amount"].astype(float)
        df["transaction_date"] = (
            pd.to_datetime(df["transaction_date"], utc=True)
            .dt.tz_convert("America/Bogota")
            .dt.tz_localize(None)
        )

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Transacciones")
    output.seek(0)
    return output


async def monthly_report(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handler para el reporte mensual. Comando global que cancela cualquier flujo activo."""
    log_handler_invocation(logger, "monthly_report", update)
    telegram_user = update.effective_user
    chat = update.effective_chat
    if not telegram_user or not chat:
        return ConversationHandler.END

    # Limpiar estado de conversación para cancelar cualquier flujo activo
    context.user_data.clear()

    await context.bot.send_message(
        chat_id=chat.id,
        text="🐺 Generando tu reporte, dame un segundo...",
    )

    now = get_now_utc()
    month_start, next_month = _get_month_boundaries(now)

    buffer = await asyncio.to_thread(
        _generate_monthly_report_chart,
        telegram_user.id,
        month_start,
        next_month,
    )

    if not buffer:
        await context.bot.send_message(
            chat_id=chat.id,
            text="No encontré gastos registrados en el mes actual.",
        )
        return ConversationHandler.END

    await context.bot.send_photo(chat_id=chat.id, photo=buffer)
    return ConversationHandler.END


async def export_transactions(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    log_handler_invocation(logger, "export_transactions", update)
    telegram_user = update.effective_user
    chat = update.effective_chat
    if not telegram_user or not chat:
        return

    await context.bot.send_message(
        chat_id=chat.id,
        text="📦 Preparando tu archivo de transacciones...",
    )

    buffer = await asyncio.to_thread(
        generate_transactions_excel,
        telegram_user.id,
    )

    await context.bot.send_document(
        chat_id=chat.id,
        document=buffer,
        filename="reporte_finanzas.xlsx",
    )


