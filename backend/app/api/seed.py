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

    try:
        seed_machines(db)
    except Exception:
        db.rollback()
        raise

    db.commit()
    return {"ok": True, "admin": {"email": "admin@local", "password": "admin123"}}
