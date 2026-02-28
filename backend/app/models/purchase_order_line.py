from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign
from sqlalchemy import String, Float, Integer, Boolean, BigInteger, ForeignKey
from app.core.db import Base
from app.models.base import TimestampMixin


class PurchaseOrderLine(Base, TimestampMixin):
    __tablename__ = "purchase_order_lines"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    po_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("purchase_orders.id", ondelete="CASCADE"), index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    material_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("materials.id"), nullable=True, index=True)
    material_size_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("material_sizes.id"), nullable=True, index=True)
    description: Mapped[str] = mapped_column(String, default="")
    supplier_product_code: Mapped[str] = mapped_column(String, default="")
    qty: Mapped[float] = mapped_column(Float, default=0.0)
    uom: Mapped[str] = mapped_column(String, default="sheet")
    unit_cost_gbp: Mapped[float] = mapped_column(Float, default=0.0)
    line_total_gbp: Mapped[float] = mapped_column(Float, default=0.0)
    received_qty: Mapped[float] = mapped_column(Float, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    po = relationship(
        "PurchaseOrder",
        primaryjoin="foreign(PurchaseOrderLine.po_id)==PurchaseOrder.id",
        back_populates="lines",
    )
