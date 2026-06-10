"""SQLite persistence for user accounts.

Intentionally minimal — SQLAlchemy Core/ORM with a single `users` table.
No migrations framework is used; the table is created at startup.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Generator

from sqlalchemy import Boolean, Column, DateTime, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import settings

_DB_PATH = settings.base_dir / "data" / "users.db"
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{_DB_PATH}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class _Base(DeclarativeBase):
    pass


class User(_Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="radiologist")   # "admin" | "chief_physician" | "radiologist"
    department = Column(String, nullable=True)     # e.g. "Radiology", "Oncology"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)


def init_db() -> None:
    _Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
