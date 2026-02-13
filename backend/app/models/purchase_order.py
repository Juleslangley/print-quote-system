from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, ForeignKey, DateTime, func
from app.core.db import Base
from app.models.base import TimestampMixin


class PurchaseOrder(Base, TimestampMixin):
    __tablename__ = "purchase_orders"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    po_number: Mapped[str] = mapped_column(String, unique=True, index=True)
    supplier_id: Mapped[str] = mapped_column(String, ForeignKey("suppliers.id"), index=True)
    status: Mapped[str] = mapped_column(String, default="draft")
    currency: Mapped[str] = mapped_column(String, default="GBP")
    order_date: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    required_by: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    expected_by: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_name: Mapped[str] = mapped_column(String, default="")
    delivery_address: Mapped[str] = mapped_column(String, default="")
    notes: Mapped[str] = mapped_column(String, default="")
    internal_notes: Mapped[str] = mapped_column(String, default="")
    subtotal_gbp: Mapped[float] = mapped_column(Float, default=0.0)
    vat_gbp: Mapped[float] = mapped_column(Float, default=0.0)
    total_gbp: Mapped[float] = mapped_column(Float, default=0.0)
    created_by_user_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"), nullable=True, index=True)
