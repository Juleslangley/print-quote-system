from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from app.core.db import Base


class EventsOutbox(Base):
    __tablename__ = "events_outbox"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    event_type: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
