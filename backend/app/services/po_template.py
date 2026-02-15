from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.base import new_id
from app.models.document_template import DocumentTemplate

PO_TEMPLATE_KEY = "purchase_order"

DEFAULT_PO_TEMPLATE_CONFIG: dict[str, Any] = {
    "template_name": "Standard Industry PO",
    "document_title": "PURCHASE ORDER",
    "company_name": "Your Company Name Ltd",
    "company_address": "Company Address Line 1\nCompany Address Line 2\nPostcode",
    "company_email": "accounts@your-company.com",
    "company_phone": "+44 (0)0000 000000",
    "company_vat": "VAT: GB123456789",
    "header_note": "Please supply in accordance with this purchase order.",
    "payment_terms": "Payment terms: 30 days end of month unless agreed otherwise.",
    "delivery_terms": "Delivery terms: deliver to the address on this PO unless agreed in writing.",
    "footer_note": "Please acknowledge receipt of this PO and confirm your expected delivery date.",
    "accent_color": "#1F2937",
    "table_style": "boxed",  # boxed | clean
    "show_supplier_contact": True,
    "show_delivery_block": True,
    "show_notes_block": True,
    "show_internal_notes": False,
    "show_zebra_rows": True,
}

_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
_ALLOWED_TABLE_STYLES = {"boxed", "clean"}


def _str(value: Any, default: str, max_len: int = 5000) -> str:
    if isinstance(value, str):
        return value.strip()[:max_len]
    return default


def _bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    return default


def _color(value: Any, default: str) -> str:
    if isinstance(value, str):
        candidate = value.strip()
        if _HEX_COLOR_RE.match(candidate):
            return candidate.upper()
    return default


def normalize_po_template_config(raw: Any) -> dict[str, Any]:
    cfg = deepcopy(DEFAULT_PO_TEMPLATE_CONFIG)
    if not isinstance(raw, dict):
        return cfg

    cfg["template_name"] = _str(raw.get("template_name"), cfg["template_name"], 120)
    cfg["document_title"] = _str(raw.get("document_title"), cfg["document_title"], 120)
    cfg["company_name"] = _str(raw.get("company_name"), cfg["company_name"], 200)
    cfg["company_address"] = _str(raw.get("company_address"), cfg["company_address"], 2000)
    cfg["company_email"] = _str(raw.get("company_email"), cfg["company_email"], 200)
    cfg["company_phone"] = _str(raw.get("company_phone"), cfg["company_phone"], 200)
    cfg["company_vat"] = _str(raw.get("company_vat"), cfg["company_vat"], 200)
    cfg["header_note"] = _str(raw.get("header_note"), cfg["header_note"], 1000)
    cfg["payment_terms"] = _str(raw.get("payment_terms"), cfg["payment_terms"], 2000)
    cfg["delivery_terms"] = _str(raw.get("delivery_terms"), cfg["delivery_terms"], 2000)
    cfg["footer_note"] = _str(raw.get("footer_note"), cfg["footer_note"], 2000)
    cfg["accent_color"] = _color(raw.get("accent_color"), cfg["accent_color"])

    style = _str(raw.get("table_style"), cfg["table_style"], 20).lower()
    cfg["table_style"] = style if style in _ALLOWED_TABLE_STYLES else cfg["table_style"]

    cfg["show_supplier_contact"] = _bool(raw.get("show_supplier_contact"), cfg["show_supplier_contact"])
    cfg["show_delivery_block"] = _bool(raw.get("show_delivery_block"), cfg["show_delivery_block"])
    cfg["show_notes_block"] = _bool(raw.get("show_notes_block"), cfg["show_notes_block"])
    cfg["show_internal_notes"] = _bool(raw.get("show_internal_notes"), cfg["show_internal_notes"])
    cfg["show_zebra_rows"] = _bool(raw.get("show_zebra_rows"), cfg["show_zebra_rows"])
    return cfg


def get_po_template_record(db: Session) -> DocumentTemplate | None:
    return db.query(DocumentTemplate).filter(DocumentTemplate.key == PO_TEMPLATE_KEY).first()


def get_po_template_config(db: Session) -> dict[str, Any]:
    row = get_po_template_record(db)
    if not row:
        return deepcopy(DEFAULT_PO_TEMPLATE_CONFIG)
    return normalize_po_template_config(row.config)


def upsert_po_template_config(db: Session, config: Any) -> tuple[DocumentTemplate, dict[str, Any]]:
    cfg = normalize_po_template_config(config)
    row = get_po_template_record(db)
    if not row:
        row = DocumentTemplate(
            id=new_id(),
            key=PO_TEMPLATE_KEY,
            name=cfg["template_name"],
            config=cfg,
            active=True,
        )
    else:
        row.name = cfg["template_name"]
        row.config = cfg
        row.active = True
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, cfg


def reset_po_template_config(db: Session) -> tuple[DocumentTemplate, dict[str, Any]]:
    return upsert_po_template_config(db, deepcopy(DEFAULT_PO_TEMPLATE_CONFIG))
