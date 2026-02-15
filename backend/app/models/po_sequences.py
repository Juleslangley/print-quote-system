"""Concurrency-safe PO number sequence table. One row per logical sequence (e.g. purchase_order)."""
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, func
from app.core.db import Base


class PoSequenceRow(Base):
    """
    Database-backed sequence for generating unique PO numbers.
    Use SELECT ... FOR UPDATE when reading to lock the row under concurrent requests.
    """
    __tablename__ = "po_sequences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
