from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session

from app.models.purchase_order import PurchaseOrder
from app.services.document_renderer import render_purchase_order_for_session


def transition_po_status(db: Session, po: PurchaseOrder, new_status: str, user_id: Optional[str]) -> None:
    """
    Single source of truth for PO status transitions.

    Hardening rules:
    - Only render when transitioning from non-processed -> processed
    - If already processed, do not render again
    - Rendering and status update are committed once by the caller
    """
    old_status = po.status
    if new_status == old_status:
        return

    if new_status == "processed" and old_status != "processed":
        # Render within the caller's DB transaction; do not commit inside renderer.
        render_purchase_order_for_session(db, po.id, user_id)

    po.status = new_status
    db.add(po)

