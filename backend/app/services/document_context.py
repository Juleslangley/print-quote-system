"""Build document rendering context from DB. Canonical shapes for each doc_type."""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.material import Material
from app.models.material_size import MaterialSize
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_order_line import PurchaseOrderLine
from app.models.supplier import Supplier

COMPANY_NAME = "Chartwell Press"

# Bucket order for line sorting: materials (0), services (1), delivery (2), misc (3)
BUCKET_MATERIALS = 0
BUCKET_SERVICES = 1
BUCKET_DELIVERY = 2
BUCKET_MISC = 3

# Material type order: sheet (0) before roll (1)
MAT_TYPE_SHEET = 0
MAT_TYPE_ROLL = 1


def _line_bucket(line: PurchaseOrderLine, desc_lower: str) -> int:
    """Classify line into bucket for sorting. Handles nulls safely."""
    if not line.material_id:
        if "delivery" in desc_lower:
            return BUCKET_DELIVERY
        if any(kw in desc_lower for kw in ("service", "finish", "lamina", "install", "setup", "labour")):
            return BUCKET_SERVICES
        return BUCKET_MISC
    return BUCKET_MATERIALS


def _material_sort_key(line: PurchaseOrderLine, material: Optional[Material], size: Optional[MaterialSize]) -> tuple:
    """Stable sort key for material lines: type, material_name, thickness, size, description."""
    mat_type = MAT_TYPE_SHEET if (material and (material.type or "").lower() == "sheet") else MAT_TYPE_ROLL
    mat_name = (material and material.name) or ""
    thickness = ""
    if material and material.meta and isinstance(material.meta, dict):
        thickness = str(material.meta.get("thickness", ""))
    # Size: sheet = "WxH", roll = "Wmm"
    size_str = ""
    if size:
        if size.height_mm is not None and size.height_mm > 0:
            size_str = f"{size.width_mm or 0:.0f}x{size.height_mm:.0f}"
        else:
            size_str = f"{size.width_mm or 0:.0f}mm"
    desc = (line.description or "").strip()
    return (mat_type, mat_name, thickness, size_str, desc)


def _other_bucket_sort_key(line: PurchaseOrderLine) -> str:
    """Sort key for non-material lines: description."""
    return (line.description or "").strip()


def _sort_po_lines(
    lines: list[PurchaseOrderLine],
    material_map: dict[str, Material],
    size_map: dict[str, MaterialSize],
) -> list[PurchaseOrderLine]:
    """Deterministic sort: bucket (materials, services, delivery, misc), then within-bucket keys."""
    def key(line: PurchaseOrderLine) -> tuple:
        desc_lower = (line.description or "").lower()
        bucket = _line_bucket(line, desc_lower)
        if bucket == BUCKET_MATERIALS:
            mat = material_map.get(line.material_id) if line.material_id else None
            size = size_map.get(line.material_size_id) if line.material_size_id else None
            return (bucket, _material_sort_key(line, mat, size))
        return (bucket, _other_bucket_sort_key(line))

    return sorted(lines, key=key)


def build_context(doc_type: str, entity_id: Optional[str], db: Session) -> dict[str, Any]:
    """
    Build canonical document context for rendering.
    - purchase_order + entity_id: load PO, supplier, lines from DB, deterministic sort.
    - Other doc_types or missing entity_id: returns empty dict (caller uses mock).
    """
    if doc_type != "purchase_order" or not entity_id:
        return {}

    try:
        po_id = int(entity_id)
    except (ValueError, TypeError):
        return {}

    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        return {}

    supplier = db.query(Supplier).filter(Supplier.id == po.supplier_id).first()
    raw_lines = (
        db.query(PurchaseOrderLine)
        .filter(PurchaseOrderLine.po_id == po_id, PurchaseOrderLine.active.is_(True))
        .all()
    )

    material_ids = {l.material_id for l in raw_lines if l.material_id}
    size_ids = {l.material_size_id for l in raw_lines if l.material_size_id}
    material_map = {m.id: m for m in db.query(Material).filter(Material.id.in_(material_ids)).all()}
    size_map = {s.id: s for s in db.query(MaterialSize).filter(MaterialSize.id.in_(size_ids)).all()}

    lines = _sort_po_lines(raw_lines, material_map, size_map)

    return {
        "po": po,
        "supplier": supplier,
        "company": {"name": COMPANY_NAME},
        "delivery": {
            "name": po.delivery_name or "",
            "address": po.delivery_address or "",
        },
        "lines": lines,
        "totals": {
            "subtotal": po.subtotal_gbp or 0,
            "vat": po.vat_gbp or 0,
            "total": po.total_gbp or 0,
        },
        "notes": po.notes or "",
        "terms": po.internal_notes or "",
        "vat_rate": 0.20,
    }
