"""QuotePart: MIS-style part (job_type REQUIRED, material, finished W/H, qty, sides). Using base TimestampMixin from base."""
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, Integer, ForeignKey
from app.core.db import Base
from app.models.base import TimestampMixin


class QuotePart(Base, TimestampMixin):
    __tablename__ = "quote_parts"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    quote_id: Mapped[str] = mapped_column(String, ForeignKey("quotes.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String, default="")
    job_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    material_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("materials.id", ondelete="SET NULL"), nullable=True, index=True)
    finished_w_mm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    finished_h_mm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    sides: Mapped[int] = mapped_column(Integer, default=1)
    preferred_sheet_size_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("material_sizes.id", ondelete="SET NULL"), nullable=True)
    waste_pct_override: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    setup_minutes_override: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    machine_key_override: Mapped[Optional[str]] = mapped_column(String, nullable=True)
