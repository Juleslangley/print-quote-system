from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.permissions import require_admin, require_sales
from app.core.db import get_db
from app.schemas.po_template import POTemplateIn, POTemplateOut
from app.services.po_template import (
    DEFAULT_PO_TEMPLATE_CONFIG,
    PO_TEMPLATE_KEY,
    get_po_template_config,
    get_po_template_record,
    reset_po_template_config,
    upsert_po_template_config,
)

router = APIRouter()


def _to_out(row, cfg: dict) -> POTemplateOut:
    return POTemplateOut(
        id=row.id if row else None,
        key=PO_TEMPLATE_KEY,
        name=(row.name if row else cfg.get("template_name", "Standard Industry PO")),
        config=cfg,
        default_config=DEFAULT_PO_TEMPLATE_CONFIG,
        updated_at=getattr(row, "updated_at", None) if row else None,
    )


@router.get("/po-template", response_model=POTemplateOut)
def get_po_template(
    db: Session = Depends(get_db),
    _=Depends(require_sales),
):
    row = get_po_template_record(db)
    cfg = get_po_template_config(db)
    return _to_out(row, cfg)


@router.put("/po-template", response_model=POTemplateOut)
def update_po_template(
    payload: POTemplateIn,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    row, cfg = upsert_po_template_config(db, payload.config)
    return _to_out(row, cfg)


@router.post("/po-template/reset", response_model=POTemplateOut)
def reset_po_template(
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    row, cfg = reset_po_template_config(db)
    return _to_out(row, cfg)
