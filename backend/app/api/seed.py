from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import hash_password
from app.models.base import new_id
from app.models.user import User
from app.models.material import Material
from app.models.rate import Rate
from app.models.template import ProductTemplate
from app.models.customer import Customer
from app.models.operation import Operation
from app.models.template_links import TemplateOperation
from app.models.margin_profile import MarginProfile
from app.models.supplier import Supplier
from app.models.document_template import DocumentTemplate
from app.seed.machines import seed_machines

router = APIRouter()


def upsert_supplier(db: Session, name: str, **kwargs) -> None:
    s = db.query(Supplier).filter(Supplier.name == name).first()
    if not s:
        s = Supplier(id=new_id(), name=name, **kwargs)
        db.add(s)
    else:
        for k, v in kwargs.items():
            if hasattr(s, k):
                setattr(s, k, v)
        db.add(s)


def upsert_material(db: Session, name: str, **kwargs) -> Material:
    m = db.query(Material).filter(Material.name == name).first()
    if not m:
        m = Material(id=new_id(), name=name, **kwargs)
        db.add(m)
    else:
        for k, v in kwargs.items():
            if hasattr(m, k):
                setattr(m, k, v)
        db.add(m)
    db.flush()
    return m

@router.post("/seed/dev")
def seed_dev(db: Session = Depends(get_db)):
    # admin user
    if db.query(User).count() == 0:
        db.add(User(
            id=new_id(),
            email="admin@local",
            password_hash=hash_password("admin123"),
            role="admin",
        ))

    if db.query(User).filter(User.email == "sales@local").first() is None:
        db.add(User(id=new_id(), email="sales@local", password_hash=hash_password("sales123"), role="sales"))

    if db.query(User).filter(User.email == "production@local").first() is None:
        db.add(User(id=new_id(), email="production@local", password_hash=hash_password("prod123"), role="production"))

    if db.query(User).filter(User.email == "packer@local").first() is None:
        db.add(User(id=new_id(), email="packer@local", password_hash=hash_password("packer123"), role="packer"))

    # customer
    if db.query(Customer).count() == 0:
        db.add(Customer(id=new_id(), name="Demo Customer", email="demo@customer.local"))

    # operations (reusable operation library)
    if db.query(Operation).count() == 0:
        ops = [
            Operation(id=new_id(), code="CUT_STRAIGHT", name="Cut Straight", rate_type="cut_knife", calc_model="PERIM_M", params={}, active=True),
            Operation(id=new_id(), code="CUT_CONTOUR", name="Cut Contour", rate_type="cut_knife", calc_model="CONTOUR_PERIM_M", params={"weed_min_per_sqm": 6}, active=True),
            Operation(id=new_id(), code="ROUTER_CUT", name="Router Cut", rate_type="cut_router", calc_model="ROUTER_PERIM_M", params={}, active=True),
            Operation(id=new_id(), code="LAMINATE_ROLL", name="Laminate", rate_type="laminate", calc_model="LAM_SQM", params={"lam_cost_per_sqm": 1.10}, active=True),
            Operation(id=new_id(), code="PACK_STANDARD", name="Pack Standard", rate_type="pack", calc_model="ITEM", params={"minutes_per_item": 0.6}, active=True),
        ]
        db.add_all(ops)
        db.flush()

    # margin profiles
    if db.query(MarginProfile).count() == 0:
        db.add_all([
            MarginProfile(
                id=new_id(),
                name="Standard Trade",
                target_margin_pct=0.40,
                min_margin_pct=0.25,
                min_sell_gbp=15.00,
                rounding={"mode": "NEAREST", "step": 0.05},
                active=True,
            ),
            MarginProfile(
                id=new_id(),
                name="Premium Retail",
                target_margin_pct=0.55,
                min_margin_pct=0.40,
                min_sell_gbp=25.00,
                rounding={"mode": "PSYCH_99"},
                active=True,
            ),
        ])
        db.flush()

    # suppliers
    upsert_supplier(db, "Amari Digital Supplies", website="", lead_time_days_default=1)
    upsert_supplier(db, "Spandex", website="", lead_time_days_default=2)
    upsert_supplier(db, "Antalis", website="", lead_time_days_default=2)
    db.flush()
    amari = db.query(Supplier).filter(Supplier.name == "Amari Digital Supplies").first()

    # link Demo Customer to Standard Trade margin profile if unset
    std = db.query(MarginProfile).filter(MarginProfile.name == "Standard Trade").first()
    demo = db.query(Customer).filter(Customer.name == "Demo Customer").first()
    if std and demo and demo.default_margin_profile_id is None:
        demo.default_margin_profile_id = std.id
        db.add(demo)

    # materials (always upsert demo materials so they exist after seed)
    foamex = upsert_material(
        db,
        "3mm Foamex 1220x2440",
        type="sheet",
        supplier="Generic",
        supplier_id=amari.id if amari else None,
        cost_per_sheet_gbp=18.00,
        sheet_width_mm=1220,
        sheet_height_mm=2440,
        waste_pct_default=0.05,
    )
    vinyl = upsert_material(
        db,
        "Monomeric Vinyl 1370",
        type="roll",
        supplier="Generic",
        supplier_id=amari.id if amari else None,
        cost_per_lm_gbp=2.20,
        roll_width_mm=1370,
        min_billable_lm=2.0,
        waste_pct_default=0.07,
    )
    # rates, templates and template_operations only when none exist yet
    if db.query(ProductTemplate).count() == 0:
        db.add_all([
            Rate(id=new_id(), rate_type="print_flatbed", setup_minutes=15, hourly_cost_gbp=45,
                 run_speed={"sqm_per_hour":{"standard":45,"fine":25},"white_multiplier":1.35}),
            Rate(id=new_id(), rate_type="print_roll", setup_minutes=10, hourly_cost_gbp=40,
                 run_speed={"sqm_per_hour":{"standard":25,"fine":15}}),
            Rate(id=new_id(), rate_type="cut_knife", setup_minutes=5, hourly_cost_gbp=35,
                 run_speed={"m_per_min":{"straight":6,"contour":2}}),
            Rate(id=new_id(), rate_type="cut_router", setup_minutes=10, hourly_cost_gbp=55,
                 run_speed={"router_m_per_min":1.2}),
            Rate(id=new_id(), rate_type="laminate", setup_minutes=10, hourly_cost_gbp=35,
                 run_speed={"sqm_per_hour":30}),
            Rate(id=new_id(), rate_type="pack", setup_minutes=0, hourly_cost_gbp=28, run_speed={}),
        ])
        db.flush()

        foamex_template = ProductTemplate(
            id=new_id(),
            name="3mm Foamex Board (Nyala)",
            category="rigid",
            default_material_id=foamex.id,
            rules={
                "bleed_mm": 3,
                "gutter_mm": 10,
                "setup_waste_sheets": 1,
                "waste_pct": 0.05,
                "coverage_class": "medium",
                "print_mode": "standard",
                "ink_allowance_per_sqm_gbp": {"light":0.60,"medium":0.90,"heavy":1.20},
                "target_margin_pct": 0.40,
                "finish_blocks": [
                    {"type":"CUT_STRAIGHT","rate_type":"cut_knife"},
                    {"type":"PACK_STANDARD","rate_type":"pack","params":{"minutes_per_item":0.5}}
                ]
            },
        )
        vinyl_template = ProductTemplate(
            id=new_id(),
            name="Window Vinyl Contour Cut (HP + Zünd)",
            category="roll",
            default_material_id=vinyl.id,
            rules={
                "bleed_mm": 3,
                "setup_waste_lm": 1.0,
                "waste_pct": 0.07,
                "coverage_class": "heavy",
                "print_mode": "standard",
                "ink_allowance_per_sqm_gbp": {"light":0.60,"medium":0.90,"heavy":1.20},
                "target_margin_pct": 0.45,
                "finish_blocks": [
                    {"type":"LAMINATE_ROLL","rate_type":"laminate","params":{"lam_cost_per_sqm":1.10}},
                    {"type":"CUT_CONTOUR","rate_type":"cut_knife","params":{"weed_min_per_sqm":6}},
                    {"type":"PACK_STANDARD","rate_type":"pack","params":{"minutes_per_item":0.7}}
                ]
            },
        )
        db.add_all([foamex_template, vinyl_template])
        db.flush()

        op_map = {o.code: o for o in db.query(Operation).all()}
        db.add_all([
            TemplateOperation(id=new_id(), template_id=foamex_template.id, operation_id=op_map["CUT_STRAIGHT"].id, sort_order=10, params_override={}),
            TemplateOperation(id=new_id(), template_id=foamex_template.id, operation_id=op_map["PACK_STANDARD"].id, sort_order=20, params_override={"minutes_per_item": 0.5}),
            TemplateOperation(id=new_id(), template_id=vinyl_template.id, operation_id=op_map["LAMINATE_ROLL"].id, sort_order=10, params_override={"lam_cost_per_sqm": 1.10}),
            TemplateOperation(id=new_id(), template_id=vinyl_template.id, operation_id=op_map["CUT_CONTOUR"].id, sort_order=20, params_override={"weed_min_per_sqm": 6}),
            TemplateOperation(id=new_id(), template_id=vinyl_template.id, operation_id=op_map["PACK_STANDARD"].id, sort_order=30, params_override={"minutes_per_item": 0.7}),
        ])

    # document templates (HTML, Jinja2)
    has_po_doc_tpl = (
        db.query(DocumentTemplate)
        .filter(DocumentTemplate.doc_type == "purchase_order")
        .count()
        > 0
    )
    if not has_po_doc_tpl:
        po_html = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <style>
      @page { size: A4; margin: 18mm; }
      body { font-family: DejaVu Sans, Arial, sans-serif; font-size: 12px; color: #111; }
      .row { display: flex; justify-content: space-between; gap: 18px; }
      .muted { color: #666; }
      .title { font-size: 20px; font-weight: 700; letter-spacing: 0.5px; }
      .box { border: 1px solid #ddd; padding: 10px 12px; border-radius: 8px; }
      table { width: 100%; border-collapse: collapse; margin-top: 10px; }
      th, td { border-bottom: 1px solid #eee; padding: 8px 6px; vertical-align: top; }
      th { text-align: left; background: #f5f5f7; font-weight: 700; }
      .right { text-align: right; }
      .totals { margin-top: 12px; width: 280px; margin-left: auto; }
      .totals td { border: none; padding: 4px 0; }
      .footer { margin-top: 18px; font-size: 11px; color: #666; }
    </style>
  </head>
  <body>
    <div class="row" style="align-items:flex-start;">
      <div>
        <div class="title">Chartwell Press</div>
        <div class="muted">Purchase Order</div>
      </div>
      <div class="box" style="min-width: 260px;">
        <div><strong>PO No:</strong> {{ po.po_number if po.po_number and not po.po_number.startswith('DRAFT-') else 'Draft' }}</div>
        <div><strong>Order date:</strong> {{ po.order_date.strftime('%d/%m/%Y') if po.order_date else '' }}</div>
        {% if po.required_by %}<div><strong>Required by:</strong> {{ po.required_by.strftime('%d/%m/%Y') }}</div>{% endif %}
        {% if po.expected_by %}<div><strong>Expected by:</strong> {{ po.expected_by.strftime('%d/%m/%Y') }}</div>{% endif %}
      </div>
    </div>

    <div class="row" style="margin-top: 14px;">
      <div class="box" style="flex:1;">
        <div style="font-weight:700; margin-bottom: 6px;">Supplier</div>
        <div>{{ supplier.name if supplier else po.supplier_id }}</div>
        {% if supplier and supplier.address %}<div class="muted">{{ supplier.address }}</div>{% endif %}
        {% if supplier and supplier.city %}<div class="muted">{{ supplier.city }}</div>{% endif %}
        {% if supplier and supplier.postcode %}<div class="muted">{{ supplier.postcode }}</div>{% endif %}
        {% if supplier and supplier.country %}<div class="muted">{{ supplier.country }}</div>{% endif %}
        {% if supplier and supplier.email %}<div class="muted">{{ supplier.email }}</div>{% endif %}
        {% if supplier and supplier.phone %}<div class="muted">{{ supplier.phone }}</div>{% endif %}
      </div>
      <div class="box" style="flex:1;">
        <div style="font-weight:700; margin-bottom: 6px;">Delivery</div>
        {% if po.delivery_name %}<div>{{ po.delivery_name }}</div>{% endif %}
        {% if po.delivery_address %}<div class="muted">{{ po.delivery_address }}</div>{% endif %}
      </div>
    </div>

    {% if po.notes %}
      <div class="box" style="margin-top: 14px;">
        <div style="font-weight:700; margin-bottom: 6px;">Notes</div>
        <div>{{ po.notes }}</div>
      </div>
    {% endif %}

    <table>
      <thead>
        <tr>
          <th>Description</th>
          <th>Supplier code</th>
          <th class="right">Qty</th>
          <th>UOM</th>
          <th class="right">Unit cost</th>
          <th class="right">Line total</th>
        </tr>
      </thead>
      <tbody>
        {% for line in lines %}
          <tr>
            <td>{{ line.description or '—' }}</td>
            <td>{{ line.supplier_product_code or '—' }}</td>
            <td class="right">{{ '%.2f'|format(line.qty or 0) }}</td>
            <td>{{ line.uom or '—' }}</td>
            <td class="right">£{{ '%.2f'|format(line.unit_cost_gbp or 0) }}</td>
            <td class="right">£{{ '%.2f'|format(line.line_total_gbp or 0) }}</td>
          </tr>
        {% endfor %}
        {% if not lines or (lines|length) == 0 %}
          <tr><td colspan="6" class="muted">No lines</td></tr>
        {% endif %}
      </tbody>
    </table>

    <table class="totals">
      <tr><td class="muted">Subtotal</td><td class="right">£{{ '%.2f'|format(po.subtotal_gbp or 0) }}</td></tr>
      <tr><td class="muted">VAT</td><td class="right">£{{ '%.2f'|format(po.vat_gbp or 0) }}</td></tr>
      <tr><td style="font-weight:700;">Total</td><td class="right" style="font-weight:700;">£{{ '%.2f'|format(po.total_gbp or 0) }}</td></tr>
    </table>

    <div class="footer">
      Generated by Chartwell Press · Please quote PO number on all correspondence.
    </div>
  </body>
</html>
"""
        db.add(DocumentTemplate(
            id=new_id(),
            doc_type="purchase_order",
            name="Default Purchase Order",
            engine="html_jinja",
            content=po_html,
            is_active=True,
        ))

    try:
        seed_machines(db)
    except Exception:
        db.rollback()
        raise

    db.commit()
    return {"ok": True, "admin": {"email": "admin@local", "password": "admin123"}}
