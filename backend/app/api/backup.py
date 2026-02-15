"""
Backup and restore app data as JSON. Admin-only.
Backup: export all configured tables to a single JSON file (download).
Restore: upload JSON file; truncates tables and re-inserts (replaces data).
"""
import json
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import text, DateTime, Boolean
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.api.permissions import require_admin
from app.models.user import User
from app.models.supplier import Supplier
from app.models.customer import Customer
from app.models.margin_profile import MarginProfile
from app.models.machine import Machine
from app.models.operation import Operation
from app.models.material import Material
from app.models.material_size import MaterialSize
from app.models.rate import Rate
from app.models.template import ProductTemplate
from app.models.machine_rate import MachineRate
from app.models.customer_contact import CustomerContact
from app.models.customer_contact_method import CustomerContactMethod
from app.models.template_links import TemplateOperation, TemplateAllowedMaterial
from app.models.pricing_rules import TemplatePricingRule, CustomerPricingRule
from app.models.quote import Quote, QuoteItem
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_order_line import PurchaseOrderLine
from app.models.po_sequences import PoSequenceRow

router = APIRouter()

# Order: parents before children (for insert). Truncate uses reverse order with CASCADE.
BACKUP_TABLES = [
    ("users", User),
    ("suppliers", Supplier),
    ("customers", Customer),
    ("margin_profiles", MarginProfile),
    ("machines", Machine),
    ("operations", Operation),
    ("materials", Material),
    ("material_sizes", MaterialSize),
    ("product_templates", ProductTemplate),
    ("rates", Rate),
    ("machine_rates", MachineRate),
    ("customer_contacts", CustomerContact),
    ("customer_contact_methods", CustomerContactMethod),
    ("template_operations", TemplateOperation),
    ("template_allowed_materials", TemplateAllowedMaterial),
    ("template_pricing_rules", TemplatePricingRule),
    ("customer_pricing_rules", CustomerPricingRule),
    ("quotes", Quote),
    ("quote_items", QuoteItem),
    ("po_sequences", PoSequenceRow),
    ("purchase_orders", PurchaseOrder),
    ("purchase_order_lines", PurchaseOrderLine),
]


def _row_to_dict(row: Any) -> dict:
    out = {}
    for c in row.__table__.columns:
        v = getattr(row, c.key)
        if v is None:
            out[c.key] = None
        elif isinstance(v, (datetime, date)):
            out[c.key] = v.isoformat()
        elif isinstance(v, (dict, list)):
            out[c.key] = v
        else:
            out[c.key] = v
    return out


@router.get("/backup")
def download_backup(db: Session = Depends(get_db), _=Depends(require_admin)):
    """Export all app data as JSON. Returns a file download."""
    payload = {"version": 1, "tables": {}}
    for table_name, model in BACKUP_TABLES:
        rows = db.query(model).all()
        payload["tables"][table_name] = [_row_to_dict(r) for r in rows]
    body = json.dumps(payload, indent=2)
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=quote-backup.json"},
    )


@router.post("/backup/restore")
def restore_backup(file: UploadFile, db: Session = Depends(get_db), _=Depends(require_admin)):
    """Replace app data with uploaded backup JSON. Truncates then re-inserts."""
    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Upload a .json backup file")
    try:
        raw = file.file.read()
        payload = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    tables = payload.get("tables")
    if not isinstance(tables, dict):
        raise HTTPException(status_code=400, detail="Backup must have a 'tables' object")

    # Truncate all backup tables in reverse order (children first) so FKs are satisfied
    for table_name, model in reversed(BACKUP_TABLES):
        try:
            db.execute(text(f'TRUNCATE TABLE "{model.__table__.name}" RESTART IDENTITY CASCADE'))
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Truncate {table_name}: {e}")

    def _coerce_row(model_cls: type, d: dict) -> dict:
        out = {}
        for c in model_cls.__table__.columns:
            k = c.key
            if k not in d:
                continue
            v = d[k]
            if v is None:
                out[k] = None
            elif isinstance(c.type, DateTime) and isinstance(v, str):
                try:
                    out[k] = datetime.fromisoformat(v.replace("Z", "+00:00"))
                except ValueError:
                    out[k] = v
            elif isinstance(c.type, Boolean) and isinstance(v, str):
                out[k] = v.lower() in ("true", "1", "yes")
            else:
                out[k] = v
        return out

    # Insert in dependency order
    for table_name, model in BACKUP_TABLES:
        rows = tables.get(table_name)
        if not isinstance(rows, list) or len(rows) == 0:
            continue
        for row_dict in rows:
            try:
                kwargs = _coerce_row(model, row_dict)
                obj = model(**kwargs)
                db.add(obj)
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=500, detail=f"Insert {table_name}: {e}")
    db.commit()
    return {"ok": True, "message": "Restore complete"}
