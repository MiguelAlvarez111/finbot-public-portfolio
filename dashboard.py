import os
from decimal import Decimal
from functools import wraps
from typing import Any, Callable, TypeVar, cast

import jwt
from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.orm import selectinload

from database import SessionLocal
from models import Category, Transaction


F = TypeVar("F", bound=Callable[..., Any])

secret_key = os.getenv("SECRET_KEY")
if not secret_key:
    raise RuntimeError("SECRET_KEY environment variable is not set for the dashboard.")

app = Flask(__name__)
app.secret_key = secret_key

app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
app.config.setdefault("PREFERRED_URL_SCHEME", "https")


def login_required(view: F) -> F:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any):
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for("unauthorized"))
        return cast(Any, view)(*args, **kwargs)

    return cast(F, wrapped)


@app.route("/auth")
def auth_callback() -> Any:
    token = request.args.get("token")
    if not token:
        abort(400, description="Falta el token de autenticación.")

    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
    except ExpiredSignatureError:
        abort(401, description="El token ha expirado. Solicita un nuevo enlace desde Telegram.")
    except InvalidTokenError:
        abort(401, description="Token inválido.")

    user_id = payload.get("user_id")
    if not user_id:
        abort(400, description="El token no contiene un usuario válido.")

    session["user_id"] = user_id

    return redirect(url_for("dashboard_home"))


@app.route("/")
@login_required
def dashboard_home() -> str:
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("unauthorized"))

    db = SessionLocal()
    try:
        transactions = (
            db.query(Transaction)
            .options(selectinload(Transaction.category))
            .filter(Transaction.user_id == user_id)
            .order_by(Transaction.transaction_date.desc())
            .all()
        )

        total_income = Decimal("0")
        total_expense = Decimal("0")

        for tx in transactions:
            amount = Decimal(tx.amount)
            category = tx.category

            tx.is_income = False  # type: ignore[attr-defined]
            tx.is_expense = False  # type: ignore[attr-defined]
            tx.abs_amount = amount.copy_abs()  # type: ignore[attr-defined]

            if not isinstance(category, Category) or not category.type:
                continue

            category_type = category.type.value
            if category_type == "income":
                total_income += amount.copy_abs()
                tx.is_income = True  # type: ignore[attr-defined]
            elif category_type == "expense":
                total_expense += amount.copy_abs()
                tx.is_expense = True  # type: ignore[attr-defined]

        balance = total_income - total_expense

    finally:
        db.close()

    return render_template(
        "dashboard.html",
        user=user_id,
        transactions=transactions,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
    )


@app.route("/unauthorized")
def unauthorized() -> Any:
    return (
        "No estás autenticado. Solicita un nuevo enlace en Telegram con /dashboard.",
        401,
    )


@app.route("/logout")
def logout() -> Any:
    session.clear()
    return redirect(url_for("unauthorized"))


