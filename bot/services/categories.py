"""Category related persistence helpers."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Category, CategoryType

DEFAULT_CATEGORY_DEFINITIONS: List[Dict[str, object]] = [
    {"name": "General", "type": CategoryType.EXPENSE, "is_default": True},
    {"name": "Comida", "type": CategoryType.EXPENSE, "is_default": False},
    {"name": "Transporte", "type": CategoryType.EXPENSE, "is_default": False},
    {"name": "Casa", "type": CategoryType.EXPENSE, "is_default": False},
    {"name": "Ocio", "type": CategoryType.EXPENSE, "is_default": False},
    {"name": "Suscripciones", "type": CategoryType.EXPENSE, "is_default": False},
    {"name": "Salud", "type": CategoryType.EXPENSE, "is_default": False},
    {"name": "Educación", "type": CategoryType.EXPENSE, "is_default": False},
    {"name": "Regalos", "type": CategoryType.EXPENSE, "is_default": False},
    {"name": "General Ingreso", "type": CategoryType.INCOME, "is_default": True},
    {"name": "Salario", "type": CategoryType.INCOME, "is_default": False},
    {"name": "Inversiones", "type": CategoryType.INCOME, "is_default": False},
]


def create_default_categories(
    session: Session,
    user_id: int,
    *,
    selected_names: Optional[Iterable[str]] = None,
) -> None:
    """Ensure the user has the selected default categories."""
    existing_names = {
        row.name
        for row in session.execute(
            select(Category.name).where(Category.user_id == user_id)
        )
    }

    desired_names = (
        {name.strip() for name in selected_names} if selected_names else None
    )

    categories_to_add: List[Category] = []
    for definition in DEFAULT_CATEGORY_DEFINITIONS:
        name = definition["name"]
        if name in existing_names:
            continue
        if desired_names is not None and name not in desired_names:
            continue
        categories_to_add.append(
            Category(
                user_id=user_id,
                name=name,
                type=definition["type"],
                is_default=definition["is_default"],
            )
        )

    if categories_to_add:
        session.add_all(categories_to_add)
        session.commit()


def get_default_category(
    session: Session,
    user_id: int,
    category_type: CategoryType,
) -> Optional[Category]:
    """Return the default category of a type for the user."""
    return session.execute(
        select(Category)
        .where(
            Category.user_id == user_id,
            Category.type == category_type,
            Category.is_default.is_(True),
        )
        .limit(1)
    ).scalar_one_or_none()


def fetch_user_categories(session: Session, user_id: int) -> List[Category]:
    """Fetch all categories for the user ordered by type and name."""
    return list(
        session.execute(
            select(Category)
            .where(Category.user_id == user_id)
            .order_by(Category.type, Category.name)
        ).scalars()
    )


def ensure_categories_exist(
    session: Session,
    user_id: int,
    category_names: Sequence[str],
    *,
    category_type: CategoryType,
    is_default: bool = False,
) -> None:
    """Create categories that do not exist yet for the user."""
    normalized_names = {name.strip() for name in category_names if name.strip()}
    if not normalized_names:
        return

    existing = {
        row.name
        for row in session.execute(
            select(Category.name).where(
                Category.user_id == user_id,
                Category.type == category_type,
            )
        )
    }

    to_create = normalized_names - existing
    if not to_create:
        return

    session.add_all(
        [
            Category(
                user_id=user_id,
                name=name,
                type=category_type,
                is_default=is_default,
            )
            for name in to_create
        ]
    )
    session.commit()


