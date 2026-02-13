from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, Integer, Text, DateTime
from app.core.db import Base
from app.models.base import TimestampMixin


class PackingStoreJob(Base, TimestampMixin):
    __tablename__ = "packing_store_jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    batch_id: Mapped[str] = mapped_column(String, ForeignKey("packing_batches.id", ondelete="CASCADE"), index=True)
    store_name: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, default="pending", index=True)  # pending | packed | dispatched
    box_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    packed_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    dispatched_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
