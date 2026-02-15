from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, attributes
from sqlalchemy import String, Float, ForeignKey, DateTime, func, event
from app.core.db import Base
from app.models.base import TimestampMixin

IMMUTABLE_PO_NUMBER_MSG = "po_number cannot be updated once created"


class PurchaseOrder(Base, TimestampMixin):
    __tablename__ = "purchase_orders"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    po_number: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True, nullable=True)
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


def _is_promotion(oldvalue, value) -> bool:
    """True when changing from draft (DRAFT-*) to final (PO + 7 digits)."""
    if not value or not oldvalue or oldvalue is attributes.NO_VALUE:
        return False
    s_old, s_new = str(oldvalue), str(value)
    return (
        s_old.startswith("DRAFT-")
        and len(s_new) == 9
        and s_new.startswith("PO")
        and s_new[2:].isdigit()
    )


def _po_number_set_listener(target: "PurchaseOrder", value, oldvalue, initiator):
    """ORM-level guard: only allow create or promotion (DRAFT-* -> PO*)."""
    state = attributes.instance_state(target)
    if not state.persistent:
        return value  # new instance (create path)
    if value == oldvalue:
        return value  # no change
    if oldvalue is attributes.NO_VALUE:
        return value  # load/init
    if _is_promotion(oldvalue, value):
        return value  # promote draft to final via get_next_po_number
    raise ValueError(IMMUTABLE_PO_NUMBER_MSG)


event.listen(PurchaseOrder.po_number, "set", _po_number_set_listener, retval=True)


def _reject_po_number_change(mapper, connection, target):
    """before_update: allow only promotion (DRAFT-* -> PO*); reject other po_number changes."""
    state = attributes.instance_state(target)
    if not state.persistent:
        return
    hist = state.attrs.po_number.history
    if not hist.has_changes():
        return
    oldvalue, _, newvalue = hist.deleted, hist.unchanged, hist.added
    oldval = (oldvalue[0] if oldvalue else None) or attributes.NO_VALUE
    newval = (newvalue[0] if newvalue else None)
    if _is_promotion(oldval, newval):
        return
    raise ValueError(IMMUTABLE_PO_NUMBER_MSG)


@event.listens_for(PurchaseOrder, "before_update")
def _before_purchase_order_update(mapper, connection, target):
    _reject_po_number_change(mapper, connection, target)
