"""Unit tests for document_context line sorting and build_context."""
import pytest

import app.models  # noqa: F401
from app.models.base import new_id
from app.models.supplier import Supplier
from app.models.material import Material
from app.models.material_size import MaterialSize
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_order_line import PurchaseOrderLine
from app.services.document_context import build_context


def test_line_sorting_materials_before_services_before_delivery_before_misc(
    db_session, supplier_id
):
    """
    Lines are sorted by bucket: materials, services, delivery, misc.
    Within materials: sheet before roll, then material_name, thickness, size, description.
    Within other buckets: description.
    """
    # Create materials: sheet and roll
    sheet_mat = Material(
        id=new_id(),
        name="Foamex 3mm",
        type="sheet",
        supplier_id=supplier_id,
        meta={"thickness": "3mm"},
    )
    roll_mat = Material(
        id=new_id(),
        name="Vinyl roll",
        type="roll",
        supplier_id=supplier_id,
    )
    db_session.add_all([sheet_mat, roll_mat])
    db_session.flush()

    sheet_size = MaterialSize(
        id=new_id(),
        material_id=sheet_mat.id,
        label="1220x915",
        width_mm=1220,
        height_mm=915,
    )
    roll_size = MaterialSize(
        id=new_id(),
        material_id=roll_mat.id,
        label="500mm",
        width_mm=500,
        height_mm=None,
    )
    db_session.add_all([sheet_size, roll_size])
    db_session.flush()

    po = PurchaseOrder(supplier_id=supplier_id, status="draft")
    db_session.add(po)
    db_session.flush()

    # Create lines in "wrong" order: delivery, misc, material (roll), material (sheet), service
    lines_data = [
        {"description": "Delivery to site", "material_id": None, "material_size_id": None},
        {"description": "Sundries", "material_id": None, "material_size_id": None},
        {"description": "Vinyl", "material_id": roll_mat.id, "material_size_id": roll_size.id},
        {"description": "Foamex sheets", "material_id": sheet_mat.id, "material_size_id": sheet_size.id},
        {"description": "Lamination service", "material_id": None, "material_size_id": None},
    ]
    for i, ld in enumerate(lines_data):
        line = PurchaseOrderLine(
            id=new_id(),
            po_id=po.id,
            sort_order=i,
            description=ld["description"],
            material_id=ld.get("material_id"),
            material_size_id=ld.get("material_size_id"),
            qty=1,
            uom="sheet",
            unit_cost_gbp=10.0,
            line_total_gbp=10.0,
            active=True,
        )
        db_session.add(line)
    db_session.commit()

    ctx = build_context("purchase_order", str(po.id), db_session)
    assert "lines" in ctx
    ordered_descriptions = [l.description for l in ctx["lines"]]

    # Expected: materials (sheet before roll), services, delivery, misc
    # Foamex (sheet) before Vinyl (roll)
    # Then Lamination (service), then Delivery, then Sundries (misc)
    assert ordered_descriptions[0] == "Foamex sheets"
    assert ordered_descriptions[1] == "Vinyl"
    assert ordered_descriptions[2] == "Lamination service"
    assert ordered_descriptions[3] == "Delivery to site"
    assert ordered_descriptions[4] == "Sundries"

    # Cleanup
    db_session.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po.id).delete()
    db_session.query(PurchaseOrder).filter(PurchaseOrder.id == po.id).delete()
    db_session.commit()
    db_session.query(MaterialSize).filter(MaterialSize.id.in_([sheet_size.id, roll_size.id])).delete()
    db_session.query(Material).filter(Material.id.in_([sheet_mat.id, roll_mat.id])).delete()
    db_session.commit()


def test_build_context_returns_empty_for_invalid_entity_id(db_session):
    assert build_context("purchase_order", None, db_session) == {}
    assert build_context("purchase_order", "", db_session) == {}
    assert build_context("purchase_order", "not-a-number", db_session) == {}
    assert build_context("purchase_order", "999999", db_session) == {}


def test_build_context_canonical_shape(db_session, supplier_id):
    """Context has po, supplier, company, delivery, lines, totals, notes, terms."""
    po = PurchaseOrder(supplier_id=supplier_id, status="draft", delivery_name="Acme", delivery_address="123 St")
    db_session.add(po)
    db_session.flush()
    line = PurchaseOrderLine(
        id=new_id(),
        po_id=po.id,
        description="Test",
        qty=2,
        unit_cost_gbp=5.0,
        line_total_gbp=10.0,
        active=True,
    )
    db_session.add(line)
    db_session.commit()

    ctx = build_context("purchase_order", str(po.id), db_session)
    assert "po" in ctx
    assert ctx["po"].id == po.id
    assert "supplier" in ctx
    assert "company" in ctx
    assert ctx["company"]["name"] == "Chartwell Press"
    assert "delivery" in ctx
    assert ctx["delivery"]["name"] == "Acme"
    assert ctx["delivery"]["address"] == "123 St"
    assert "lines" in ctx
    assert len(ctx["lines"]) == 1
    assert "totals" in ctx
    assert "subtotal" in ctx["totals"]
    assert "vat" in ctx["totals"]
    assert "total" in ctx["totals"]
    assert "notes" in ctx
    assert "terms" in ctx

    db_session.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po.id).delete()
    db_session.query(PurchaseOrder).filter(PurchaseOrder.id == po.id).delete()
    db_session.commit()
