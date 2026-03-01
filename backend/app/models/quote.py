from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, ForeignKey, JSON, Boolean
from app.core.db import Base
from app.models.base import TimestampMixin

class Quote(Base, TimestampMixin):
    __tablename__ = "quotes"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    quote_number: Mapped[str] = mapped_column(String, unique=True, index=True)
    job_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_id: Mapped[str] = mapped_column(String, ForeignKey("customers.id"))
    # MIS-style: default_job_type for UI when adding parts (optional); name for display
    default_job_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(256), default="")
    contact_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("customer_contacts.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String, default="draft")
    pricing_version: Mapped[str] = mapped_column(String)
    notes_internal: Mapped[str] = mapped_column(String, default="")

    # Quote totals (stored)
    subtotal_sell: Mapped[float] = mapped_column(Float, default=0.0)
    vat: Mapped[float] = mapped_column(Float, default=0.0)
    total_sell: Mapped[float] = mapped_column(Float, default=0.0)

    # --- QUOTE LEVEL COMMERCIAL CONTROLS ---
    margin_profile_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("margin_profiles.id"), nullable=True)
    target_margin_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # quote discount applied after item sells (v1)
    discount_pct: Mapped[float] = mapped_column(Float, default=0.0)

    # optional rounding override at quote level
    rounding_override: Mapped[dict] = mapped_column(JSON, default=dict)

    # if true, recalculation endpoints should respect locks unless explicitly forced
    totals_locked: Mapped[bool] = mapped_column(Boolean, default=False)


class QuoteItem(Base, TimestampMixin):
    __tablename__ = "quote_items"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    quote_id: Mapped[str] = mapped_column(String, ForeignKey("quotes.id"))
    template_id: Mapped[str] = mapped_column(String, ForeignKey("product_templates.id"))
    title: Mapped[str] = mapped_column(String)
    qty: Mapped[int] = mapped_column(default=1)
    width_mm: Mapped[float] = mapped_column(Float)
    height_mm: Mapped[float] = mapped_column(Float)
    sides: Mapped[int] = mapped_column(default=1)
    options: Mapped[dict] = mapped_column(JSON, default=dict)

    # engine results (stored)
    cost_total: Mapped[float] = mapped_column(Float, default=0.0)
    sell_total: Mapped[float] = mapped_column(Float, default=0.0)
    margin_pct: Mapped[float] = mapped_column(Float, default=0.0)

    calc_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)

    # --- LINE LEVEL COMMERCIAL CONTROLS ---
    sell_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    manual_sell_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    manual_discount_pct: Mapped[float] = mapped_column(Float, default=0.0)
    manual_reason: Mapped[str] = mapped_column(String, default="")
