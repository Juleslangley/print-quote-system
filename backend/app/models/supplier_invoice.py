from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, ForeignKey, DateTime, Text
from app.core.db import Base
from app.models.base import TimestampMixin


class SupplierInvoice(Base, TimestampMixin):
    __tablename__ = "supplier_invoices"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    supplier_id: Mapped[str] = mapped_column(String, ForeignKey("suppliers.id"), index=True)
    invoice_number: Mapped[str] = mapped_column(String, default="", index=True)
    invoice_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    currency: Mapped[str] = mapped_column(String, default="GBP")
    subtotal_gbp: Mapped[float] = mapped_column(Float, default=0.0)
    vat_gbp: Mapped[float] = mapped_column(Float, default=0.0)
    total_gbp: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String, default="uploaded")  # uploaded|suggested|matched|mismatch|duplicate
    matched_po_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("purchase_orders.id"), nullable=True, index=True)
    match_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    match_notes: Mapped[str] = mapped_column(String, default="")
    file_path: Mapped[str] = mapped_column(String, default="")  # e.g. invoices/<id>.pdf
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
