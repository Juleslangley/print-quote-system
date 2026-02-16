from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, attributes
from sqlalchemy import String, Float, ForeignKey, DateTime, BigInteger, func, event
from app.core.db import Base
from app.models.base import TimestampMixin

IMMUTABLE_PO_NUMBER_MSG = "po_number cannot be updated once created"


def po_number_from_id(po_id: int) -> str:
    """Generate PO number from integer id: PO + 7 zero-padded digits."""
    return f"PO{po_id:07d}"


class PurchaseOrder(Base, TimestampMixin):
    __tablename__ = "purchase_orders"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
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


def _is_valid_po_number_set(target: "PurchaseOrder", oldvalue, value) -> bool:
    """Allow setting po_number from None to PO{id:07d} (post-insert). Reject all other changes."""
    if value == oldvalue or oldvalue is attributes.NO_VALUE:
        return True
    if oldvalue is not None and str(oldvalue).strip() != "":
        return False  # Cannot change existing po_number
    # Allow None -> PO{id:07d} when value matches id
    if not value or not hasattr(target, "id") or target.id is None:
        return False
    expected = po_number_from_id(int(target.id))
    return str(value) == expected


def _po_number_set_listener(target: "PurchaseOrder", value, oldvalue, initiator):
    """ORM-level guard: only allow initial set from None to PO{id:07d} after insert."""
    if value == oldvalue or oldvalue is attributes.NO_VALUE:
        return value
    if _is_valid_po_number_set(target, oldvalue, value):
        return value
    raise ValueError(IMMUTABLE_PO_NUMBER_MSG)


event.listen(PurchaseOrder.po_number, "set", _po_number_set_listener, retval=True)


def _reject_po_number_change(mapper, connection, target):
    """before_update: reject any po_number change (it is derived from id)."""
    state = attributes.instance_state(target)
    if not state.persistent:
        return
    hist = state.attrs.po_number.history
    if not hist.has_changes():
        return
    raise ValueError(IMMUTABLE_PO_NUMBER_MSG)


@event.listens_for(PurchaseOrder, "after_insert")
def _after_purchase_order_insert(mapper, connection, target):
    """Set po_number from id after insert: PO + 7 zero-padded digits."""
    from sqlalchemy import update
    if target.id is not None:
        po_num = po_number_from_id(int(target.id))
        connection.execute(
            update(PurchaseOrder.__table__)
            .where(PurchaseOrder.__table__.c.id == target.id)
            .values(po_number=po_num)
        )
        # Update in-memory object so it's consistent
        attributes.set_committed_value(target, "po_number", po_num)
