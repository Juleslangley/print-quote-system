"""Build sample context for document template preview."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from jinja2 import Environment, BaseLoader, select_autoescape
from sqlalchemy.orm import Session

from app.services.document_context import build_context
from app.services.document_expand import expand_jinja_blocks as expand_jinja_blocks_py


def _jinja_env() -> Environment:
    return Environment(
        loader=BaseLoader(),
        autoescape=select_autoescape(enabled_extensions=("html", "xml")),
    )


def _sample_po_context() -> dict[str, Any]:
    """Sample context for purchase_order templates."""
    class MockPO:
        id = 12345
        po_number = "PO012345"
        order_date = datetime(2025, 2, 23, tzinfo=timezone.utc)
        required_by = datetime(2025, 3, 1, tzinfo=timezone.utc)
        expected_by = None
        delivery_name = "Acme Ltd"
        delivery_address = "123 High Street, London, EC1 4AA"
        notes = "Please deliver to loading bay."
        internal_notes = ""
        subtotal_gbp = 150.0
        vat_gbp = 30.0
        total_gbp = 180.0

    class MockSupplier:
        id = "sup_sample"
        name = "Sample Supplier Ltd"
        address = "42 Industrial Park"
        city = "Manchester"
        postcode = "M1 2AB"
        country = "UK"
        email = "orders@supplier.example"
        phone = "+44 161 123 4567"

    class MockLine:
        def __init__(self, desc: str, code: str, qty: float, uom: str, cost: float):
            self.description = desc
            self.supplier_product_code = code
            self.qty = qty
            self.uom = uom
            self.unit_cost_gbp = cost
            self.line_total_gbp = qty * cost

    lines = [
        MockLine("Vinyl sign 500x300mm", "VIN-500", 10.0, "sheet", 8.50),
        MockLine("Laminate finish", "LAM-01", 10.0, "sheet", 2.00),
    ]

    return {
        "company": {"name": "Chartwell Press"},
        "po": MockPO(),
        "supplier": MockSupplier(),
        "delivery": {"name": "Acme Ltd", "address": "123 High Street, London, EC1 4AA"},
        "lines": lines,
        "totals": {"subtotal": 150.0, "vat": 30.0, "total": 180.0},
        "notes": "Please deliver to loading bay.",
        "terms": "",
        "vat_rate": 0.20,
    }


def _sample_quote_context() -> dict[str, Any]:
    """Sample context for quote templates."""
    class MockQuote:
        id = "quo_sample"
        quote_number = "Q-2025-001"
        status = "draft"
        subtotal_sell = 250.0
        vat = 50.0
        total_sell = 300.0

    class MockItem:
        def __init__(self, title: str, qty: int, cost: float, sell: float):
            self.title = title
            self.qty = qty
            self.cost_total = cost
            self.sell_total = sell

    items = [
        MockItem("Banner 900x600mm", 1, 45.0, 65.0),
        MockItem("Installation", 1, 0, 35.0),
    ]

    return {
        "company": {"name": "Chartwell Press"},
        "quote": MockQuote(),
        "items": items,
    }


def _sample_invoice_context() -> dict[str, Any]:
    """Sample context for invoice (similar to PO)."""
    ctx = _sample_po_context()
    ctx["invoice"] = ctx["po"]
    return ctx


def _sample_production_order_context() -> dict[str, Any]:
    """Sample context for production_order (job, batch, stores)."""
    class MockStore:
        def __init__(self, name: str, items: list):
            self.store_name = name
            self.line_items = items

    class MockLineItem:
        def __init__(self, component: str, description: str, qty: int):
            self.component = component
            self.description = description
            self.qty = qty

    stores = [
        MockStore("Store A", [
            MockLineItem("Sign A1", "Main fascia", 2),
            MockLineItem("Sign A2", "Side panel", 1),
        ]),
        MockStore("Store B", [
            MockLineItem("Sign B1", "Window graphic", 1),
        ]),
    ]

    class MockJob:
        id = "job_sample"
        job_no = "J-2025-001"
        title = "Sample Job"
        barcode_svg = "<svg xmlns='http://www.w3.org/2000/svg'><rect width='100' height='50' fill='#000'/></svg>"

    class MockBatch:
        stores = stores

    return {
        "company": {"name": "Chartwell Press"},
        "job": MockJob(),
        "batch": MockBatch(),
    }


def get_preview_context(
    doc_type: str,
    entity_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> dict[str, Any]:
    """
    Return context for preview.
    - If doc_type==purchase_order and entity_id provided and db given -> real PO context from build_context.
    - Else -> mock context fallback.
    """
    if doc_type == "purchase_order" and entity_id and db:
        ctx = build_context(doc_type, entity_id, db)
        if ctx:
            return ctx
    fns = {
        "purchase_order": _sample_po_context,
        "quote": _sample_quote_context,
        "invoice": _sample_invoice_context,
        "credit_note": _sample_invoice_context,
        "production_order": _sample_production_order_context,
    }
    fn = fns.get(doc_type, _sample_po_context)
    return fn()


def render_preview(
    template_html: str | None,
    template_css: str | None,
    content: str,
    doc_type: str,
    entity_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> str:
    """Render template to HTML for preview. Uses template_html+template_css if set, else content."""
    ctx = get_preview_context(doc_type, entity_id, db)
    env = _jinja_env()

    if template_html or template_css:
        body = expand_jinja_blocks_py(template_html or "")
        css_block = f"<style>\n{template_css or ''}\n</style>" if template_css else ""
        html_doc = f"""<!doctype html>
<html>
<head><meta charset="utf-8">{css_block}</head>
<body>{body}</body>
</html>"""
        tpl = env.from_string(html_doc)
        return tpl.render(**ctx)

    body = expand_jinja_blocks_py(content or "")
    tpl = env.from_string(body)
    return tpl.render(**ctx)
