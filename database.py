import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


def _cleanup_database_url(raw_value: Optional[str]) -> Optional[str]:
    if not raw_value:
        return raw_value

    cleaned = raw_value.strip()

    if cleaned.startswith("${{"):
        if "}}" in cleaned:
            reference, remainder = cleaned.split("}}", maxsplit=1)
            remainder = remainder.strip()
            if remainder:
                return remainder
            referenced_key = reference[3:].strip()
            if referenced_key:
                return os.getenv(referenced_key)
        elif "}" in cleaned:
            _, remainder = cleaned.split("}", maxsplit=1)
            remainder = remainder.strip()
            if remainder:
                return remainder

    return cleaned


DATABASE_URL = _cleanup_database_url(os.environ.get("DATABASE_URL"))

if not DATABASE_URL:
    raise ValueError("Error: La variable de entorno DATABASE_URL no está configurada.")


engine = create_engine(
    DATABASE_URL,
    future=True,
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()


