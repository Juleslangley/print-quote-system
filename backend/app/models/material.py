from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, Boolean, JSON, ForeignKey
from app.core.db import Base
from app.models.base import TimestampMixin

class Material(Base, TimestampMixin):
    __tablename__ = "materials"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    nominal_code: Mapped[str] = mapped_column(String, default="", index=True)
    supplier_product_code: Mapped[str] = mapped_column(String, default="", index=True)
    type: Mapped[str] = mapped_column(String)  # sheet/roll

    # keep legacy string
    supplier: Mapped[str] = mapped_column(String, default="")

    # NEW: proper supplier link
    supplier_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("suppliers.id"), nullable=True)

    # sheet fields
    cost_per_sheet_gbp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sheet_width_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sheet_height_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # roll fields
    cost_per_lm_gbp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    roll_width_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_billable_lm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    waste_pct_default: Mapped[float] = mapped_column(Float, default=0.05)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)