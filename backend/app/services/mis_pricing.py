"""MIS-style quotation pricing: price_quote, input_hash, nesting solver.

Using JobType, get_jobtype_defaults from app.services.job_routing.
Using hashlib.sha256 pattern from app.services.document_context.
"""
from __future__ import annotations

import hashlib
import json
import math
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.quote import Quote
from app.models.quote_part import QuotePart
from app.models.quote_price_snapshot import QuotePriceSnapshot
from app.models.machine import Machine
from app.models.machine_rate import MachineRate
from app.models.material import Material
from app.models.material_size import MaterialSize
from app.models.rate import Rate
from app.services.job_routing import (
    JOBTYPE_DEFAULTS,
    JobType,
    MachineKey,
    ProductionLane,
    get_jobtype_defaults,
    normalize_job_type,
)

BLEED_MM = 3
GUTTER_MM = 10


def _pricing_version() -> str:
    """Stable identifier: hash of job type routing defaults + config."""
    payload = json.dumps({"jobtype_defaults": JOBTYPE_DEFAULTS, "version": settings.PRICING_VERSION}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _input_hash_payload(db: Session, quote: Quote, parts: list[QuotePart]) -> dict:
    """Build canonical dict for input_hash. Exclude timestamps. Routing from part.job_type."""
    quote_data = {
        "id": quote.id,
        "customer_id": quote.customer_id,
        "name": (quote.name or "")[:256],
    }

    parts_data = []
    for p in sorted(parts, key=lambda x: x.id):
        part_row = {
            "id": p.id,
            "name": p.name or "",
            "job_type": p.job_type,
            "material_id": p.material_id,
            "finished_w_mm": p.finished_w_mm,
            "finished_h_mm": p.finished_h_mm,
            "quantity": p.quantity,
            "sides": p.sides,
            "preferred_sheet_size_id": p.preferred_sheet_size_id,
            "waste_pct_override": p.waste_pct_override,
            "setup_minutes_override": p.setup_minutes_override,
            "machine_key_override": p.machine_key_override,
        }
        parts_data.append(part_row)

        # Material pricing inputs
        if p.material_id:
            mat = db.query(Material).filter(Material.id == p.material_id).first()
            if mat:
                mat_sizes = (
                    db.query(MaterialSize)
                    .filter(MaterialSize.material_id == mat.id, MaterialSize.active == True)
                    .order_by(MaterialSize.sort_order.asc(), MaterialSize.width_mm.asc())
                    .all()
                )
                sizes_list = []
                for ms in mat_sizes:
                    sizes_list.append({
                        "id": ms.id,
                        "width_mm": ms.width_mm,
                        "height_mm": ms.height_mm,
                        "cost_per_sheet_gbp": ms.cost_per_sheet_gbp,
                        "cost_per_lm_gbp": ms.cost_per_lm_gbp,
                    })
                if not sizes_list and mat.type == "sheet":
                    sizes_list.append({
                        "id": None,
                        "width_mm": mat.sheet_width_mm,
                        "height_mm": mat.sheet_height_mm,
                        "cost_per_sheet_gbp": mat.cost_per_sheet_gbp,
                        "cost_per_lm_gbp": None,
                    })
                part_row["_material_sizes"] = sizes_list

    return {
        "pricing_version": _pricing_version(),
        "quote": quote_data,
        "parts": parts_data,
    }


def compute_input_hash(db: Session, quote: Quote, parts: list[QuotePart]) -> str:
    """Deterministic SHA256 hex of canonical pricing inputs."""
    payload = _input_hash_payload(db, quote, parts)
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _load_sheet_sizes(db: Session, material: Material) -> list[dict]:
    """Sheet sizes for nesting: id, width_mm, height_mm, cost_per_sheet_gbp or cost_per_sqm."""
    sizes = (
        db.query(MaterialSize)
        .filter(MaterialSize.material_id == material.id, MaterialSize.active == True)
        .filter(MaterialSize.height_mm.isnot(None))
        .order_by(MaterialSize.sort_order.asc(), MaterialSize.width_mm.asc())
        .all()
    )
    if sizes:
        return [
            {
                "id": s.id,
                "label": s.label or f"{s.width_mm:.0f}x{(s.height_mm or 0):.0f}",
                "width_mm": float(s.width_mm),
                "height_mm": float(s.height_mm or 0),
                "cost_per_sheet_gbp": float(s.cost_per_sheet_gbp) if s.cost_per_sheet_gbp is not None else None,
                "cost_per_sqm": None,
            }
        for s in sizes
        ]
    if material.type == "sheet" and material.sheet_width_mm and material.sheet_height_mm:
        return [{
            "id": None,
            "label": f"{material.sheet_width_mm:.0f}x{material.sheet_height_mm:.0f}",
            "width_mm": float(material.sheet_width_mm),
            "height_mm": float(material.sheet_height_mm),
            "cost_per_sheet_gbp": float(material.cost_per_sheet_gbp) if material.cost_per_sheet_gbp else None,
            "cost_per_sqm": None,
        }]
    return []


def _nest_sheet(
    w_mm: float,
    h_mm: float,
    qty: int,
    sheet: dict,
    waste_pct: float,
) -> dict | None:
    """Compute nesting for one sheet size. Returns candidate dict or None if invalid."""
    sw = sheet["width_mm"]
    sh = sheet["height_mm"]
    bleed = BLEED_MM
    gutter = GUTTER_MM
    wb = w_mm + 2 * bleed
    hb = h_mm + 2 * bleed

    def fit(sheet_w: float, sheet_h: float) -> int:
        fx = int((sheet_w + gutter) / (wb + gutter)) if (wb + gutter) > 0 else 0
        fy = int((sheet_h + gutter) / (hb + gutter)) if (hb + gutter) > 0 else 0
        return fx * fy

    per_a = fit(sw, sh)
    per_b = fit(sw, sh) if wb != hb else 0
    if wb != hb:
        per_b = fit(sh, sw)
    per_sheet = max(per_a, per_b)
    if per_sheet <= 0:
        return None

    sheets_required = math.ceil(qty / per_sheet)
    area_used_sqm = qty * (w_mm * h_mm) / 1e6
    usable_w = sw - 2 * bleed
    usable_h = sh - 2 * bleed
    area_bought_sqm = sheets_required * (usable_w * usable_h) / 1e6
    waste = 1 - (area_used_sqm / area_bought_sqm) if area_bought_sqm > 0 else 0

    mat_cost = None
    if sheet.get("cost_per_sheet_gbp") is not None:
        mat_cost = sheets_required * sheet["cost_per_sheet_gbp"]
    elif sheet.get("cost_per_sqm") is not None:
        mat_cost = area_bought_sqm * sheet["cost_per_sqm"]

    return {
        "sheet_size_id": sheet["id"],
        "label": sheet.get("label") or f"{sw:.0f}x{sh:.0f}",
        "width_mm": sw,
        "height_mm": sh,
        "per_sheet": per_sheet,
        "sheets_required": sheets_required,
        "area_used_sqm": round(area_used_sqm, 6),
        "area_bought_sqm": round(area_bought_sqm, 6),
        "waste_pct": round(waste, 4),
        "material_cost": round(mat_cost, 2) if mat_cost is not None else None,
    }


def _select_sheet_candidate(
    candidates: list[dict],
    preferred_id: str | None,
) -> tuple[dict | None, list[dict]]:
    """Best candidate + top 3 alternatives. Prefer preferred_sheet_size_id if valid."""
    valid = [c for c in candidates if c is not None]
    if not valid:
        return None, []

    def sort_key(x: dict) -> tuple:
        mc = x.get("material_cost")
        return (mc if mc is not None else 999999.0, x.get("sheets_required", 0), x.get("waste_pct", 0))

    preferred = None
    if preferred_id:
        preferred = next((c for c in valid if c.get("sheet_size_id") == preferred_id), None)

    if preferred:
        others = sorted([c for c in valid if c != preferred], key=sort_key)
        return preferred, others[:3]

    valid.sort(key=sort_key)
    return valid[0], valid[1:4]


REQUIRED_META_KEYS = ("speed_sqm_per_hour", "ink_cost_per_litre_gbp", "ink_ml_per_sqm_100pct", "default_coverage_pct")


def _machine_meta_warnings(machine: Machine) -> list[str]:
    """Return warnings for missing machine.meta keys. Does not compute values."""
    meta = getattr(machine, "meta", None) or {}
    missing = [k for k in REQUIRED_META_KEYS if meta.get(k) is None]
    if not missing:
        return []
    return [f"machine.meta missing: {', '.join(missing)}"]


def _compute_print_min(machine: Machine, printed_area_sqm: float) -> tuple[float | None, list[str]]:
    """Compute print minutes from machine.meta.speed_sqm_per_hour. Returns (print_min, warnings)."""
    meta = getattr(machine, "meta", None) or {}
    speed = meta.get("speed_sqm_per_hour")
    if speed is None or (isinstance(speed, (int, float)) and speed <= 0):
        return None, ["machine.meta.speed_sqm_per_hour missing"]
    speed_f = float(speed)
    if speed_f <= 0:
        return None, ["machine.meta.speed_sqm_per_hour missing"]
    print_min = (printed_area_sqm / speed_f) * 60
    return round(print_min, 2), []


def _compute_ink(
    machine: Machine, printed_area_sqm: float
) -> tuple[dict, float, list[str]]:
    """Compute ink cost from machine.meta. Returns (ink_dict, ink_cost_gbp, warnings).
    Always returns { coverage_pct, ink_ml, ink_cost_gbp }; ink_cost_gbp=0 when meta missing."""
    meta = getattr(machine, "meta", None) or {}
    cost_per_litre = meta.get("ink_cost_per_litre_gbp")
    ml_per_sqm = meta.get("ink_ml_per_sqm_100pct")
    coverage_pct = meta.get("default_coverage_pct", 15)
    if isinstance(coverage_pct, (int, float)):
        coverage_pct = float(coverage_pct)
    else:
        coverage_pct = 15.0

    missing = []
    if cost_per_litre is None:
        missing.append("ink_cost_per_litre_gbp")
    if ml_per_sqm is None:
        missing.append("ink_ml_per_sqm_100pct")

    if missing:
        return (
            {
                "coverage_pct": round(coverage_pct, 1),
                "ink_ml": 0.0,
                "ink_cost_gbp": 0.0,
            },
            0.0,
            [f"machine.meta missing: {', '.join(missing)}"],
        )

    ink_ml = printed_area_sqm * float(ml_per_sqm) * (coverage_pct / 100)
    ink_cost_gbp = (ink_ml / 1000) * float(cost_per_litre)
    return (
        {
            "coverage_pct": round(coverage_pct, 1),
            "ink_ml": round(ink_ml, 2),
            "ink_cost_gbp": round(ink_cost_gbp, 2),
        },
        ink_cost_gbp,
        [],
    )


def _resolve_machine(db: Session, job_type: str, lane: str) -> tuple[Any | None, list[str]]:
    """Resolve active Machine by process (never by machine_key).
    Sheet jobs (LARGE_FORMAT_SHEET / LF_SHEET) → uv_flatbed.
    Roll jobs (LARGE_FORMAT_ROLL / LF_ROLL) → eco_solvent_roll.
    Tie-break: lowest sort_order, then name. Returns (machine, warnings)."""
    if job_type == JobType.LARGE_FORMAT_ROLL or lane == ProductionLane.LF_ROLL:
        process = "eco_solvent_roll"
    elif job_type == JobType.LARGE_FORMAT_SHEET or lane == ProductionLane.LF_SHEET:
        process = "uv_flatbed"
    else:
        return None, [f"No machine resolver for job_type={job_type} lane={lane}"]

    machine = (
        db.query(Machine)
        .filter(Machine.process == process, Machine.active == True)
        .order_by(Machine.sort_order.asc(), Machine.name.asc())
        .first()
    )
    if not machine:
        return None, [f"No active machine found for process {process}"]
    return machine, []


def _apply_machine_rates(
    db: Session,
    machine: Machine,
    printed_area_sqm: float,
    laminate_sqm: float | None,
    setup_minutes_override: float | None = None,
) -> tuple[list[dict], float, float, list[str], float, float, float]:
    """Load MachineRate rows and apply print_sqm, laminate_sqm. Returns (rates_applied, total_cost, setup_min, warnings, setup_cost_sum, print_cost_sum, finishing_cost_sum)."""
    rates = (
        db.query(MachineRate)
        .filter(MachineRate.machine_id == machine.id, MachineRate.active == True)
        .order_by(MachineRate.sort_order.asc())
        .all()
    )
    rates_applied: list[dict] = []
    total_cost = 0.0
    setup_min = 0.0
    setup_cost_sum = 0.0
    print_cost_sum = 0.0
    finishing_cost_sum = 0.0
    warnings: list[str] = []

    for r in rates:
        if r.operation_key == "print_sqm":
            qty = printed_area_sqm
        elif r.operation_key == "laminate_sqm":
            qty = laminate_sqm if laminate_sqm is not None else 0.0
        elif r.operation_key == "white_ink_sqm":
            qty = 0.0
            warnings.append("white_ink_sqm: no flag yet; qty=0")
        else:
            continue

        unit_cost = float(r.cost_per_unit_gbp or 0)
        setup_cost = float(r.setup_cost_gbp or 0)
        min_charge = float(r.min_charge_gbp or 0)
        setup_mins = float(r.setup_minutes or 0)
        if r.operation_key == "print_sqm" and setup_minutes_override is not None:
            setup_mins = setup_minutes_override

        base = setup_cost + qty * unit_cost
        cost = max(min_charge, base) if min_charge > 0 else base

        setup_cost_sum += setup_cost
        if r.operation_key == "print_sqm":
            print_cost_sum += cost
        elif r.operation_key == "laminate_sqm":
            finishing_cost_sum += cost

        rates_applied.append({
            "operation_key": r.operation_key,
            "unit": r.unit or "sqm",
            "qty": round(qty, 6),
            "unit_cost_gbp": round(unit_cost, 4),
            "setup_minutes": round(setup_mins, 2),
            "setup_cost_gbp": round(setup_cost, 4),
            "min_charge_gbp": round(min_charge, 4),
            "cost_gbp": round(cost, 2),
        })
        total_cost += cost
        setup_min += setup_mins

    return rates_applied, total_cost, setup_min, warnings, setup_cost_sum, print_cost_sum, finishing_cost_sum


def _price_part(
    db: Session,
    part: QuotePart,
    job_type: str,
    rates_by_type: dict,
) -> dict:
    """Price one part. Returns part slice with nesting, cost breakdown, alternatives."""
    defaults = get_jobtype_defaults(job_type)
    waste_pct = part.waste_pct_override if part.waste_pct_override is not None else defaults["default_waste_pct"]
    setup_min = part.setup_minutes_override if part.setup_minutes_override is not None else defaults["default_setup_minutes"]

    machine_key = part.machine_key_override or defaults["default_machine_key"]
    legacy_warning = ""
    if machine_key == MachineKey.ACUITY_PRIME:
        machine_key = MachineKey.NYALA
        legacy_warning = "Part referenced inactive Acuity; routed to Nyala (history preserved)"

    lane = defaults["lane"]
    default_production = {
        "lane": lane,
        "machine_key": machine_key,
        "machine_name": None,
        "quantities": {
            "printed_area_sqm": None,
            "material_bought_sqm": None,
            "sheets_required": None,
            "roll_length_m": None,
        },
        "rates_applied": [],
        "time": {"setup_min": 0.0, "print_min": None, "total_min": 0.0},
        "ink": {"coverage_pct": 15.0, "ink_ml": 0.0, "ink_cost_gbp": 0.0},
        "warnings": [],
    }

    result = {
        "part_id": part.id,
        "part_name": part.name or "",
        "material_id": part.material_id,
        "finished_w_mm": part.finished_w_mm,
        "finished_h_mm": part.finished_h_mm,
        "quantity": part.quantity,
        "sides": part.sides,
        "routing": {
            "job_type": job_type,
            "lane": lane,
            "machine_key": machine_key,
        },
        "selected_sheet": None,
        "alternatives": [],
        "production": default_production,
        "material_cost": None,
        "setup_cost": 0.0,
        "print_cost": 0.0,
        "finishing_cost": 0.0,
        "total_cost": 0.0,
        "sell_price": 0.0,
        "sell_price_note": "placeholder 1.5x markup",
        "warnings": [legacy_warning] if legacy_warning else [],
    }

    if not part.material_id:
        result["warnings"].append("No material selected")
        result["production"]["warnings"].append("No material selected")
        return result

    mat = db.query(Material).filter(Material.id == part.material_id).first()
    if not mat:
        result["warnings"].append("Material not found")
        result["production"]["warnings"].append("Material not found")
        return result

    if not part.finished_w_mm or not part.finished_h_mm or part.quantity <= 0:
        result["warnings"].append("Invalid dimensions or quantity")
        result["production"]["warnings"].append("Invalid dimensions or quantity")
        return result

    w_mm = float(part.finished_w_mm)
    h_mm = float(part.finished_h_mm)
    qty = part.quantity

    if mat.type == "sheet":
        sizes = _load_sheet_sizes(db, mat)
        if not sizes:
            result["warnings"].append("No sheet sizes for material")
            result["production"]["warnings"].append("No sheet sizes for material")
            return result

        candidates = []
        for s in sizes:
            cand = _nest_sheet(w_mm, h_mm, qty, s, waste_pct)
            if cand:
                candidates.append(cand)

        selected, alternatives = _select_sheet_candidate(candidates, part.preferred_sheet_size_id)
        if not selected:
            result["warnings"].append("Item too large for any sheet size")
            result["production"]["warnings"].append("Item too large for any sheet size")
            return result

        result["selected_sheet"] = selected
        result["alternatives"] = alternatives
        result["material_cost"] = selected.get("material_cost")
        if selected.get("material_cost") is None and not any(s.get("cost_per_sheet_gbp") for s in sizes):
            result["warnings"].append("No sheet cost; material cost unavailable")

        lane = defaults["lane"]
        printed_area_sqm = selected.get("area_used_sqm", 0.0)
        material_bought_sqm = selected.get("area_bought_sqm")
        sheets_required = selected.get("sheets_required")

        machine, mach_warnings = _resolve_machine(db, job_type, lane)
        result["warnings"].extend(mach_warnings)

        if machine:
            meta_warnings = _machine_meta_warnings(machine)
            result["warnings"].extend(meta_warnings)
            setup_override = float(part.setup_minutes_override) if part.setup_minutes_override is not None else None
            rates_applied, total_machine_cost, setup_min, rate_warnings, setup_cost_sum, print_cost_sum, finishing_cost_sum = _apply_machine_rates(
                db, machine, printed_area_sqm, printed_area_sqm, setup_minutes_override=setup_override
            )
            result["warnings"].extend(rate_warnings)
            print_min, print_warnings = _compute_print_min(machine, printed_area_sqm)
            ink_dict, ink_cost_gbp, ink_warnings = _compute_ink(machine, printed_area_sqm)
            total_machine_cost += ink_cost_gbp
            result["warnings"].extend(print_warnings)
            result["warnings"].extend(ink_warnings)
            total_min = setup_min + (print_min or 0)
            result["setup_cost"] = round(setup_cost_sum, 2)
            result["print_cost"] = round(print_cost_sum, 2)
            result["finishing_cost"] = round(finishing_cost_sum, 2)
            result["production"] = {
                "lane": lane,
                "machine_key": machine_key,
                "machine_name": machine.name,
                "quantities": {
                    "printed_area_sqm": round(printed_area_sqm, 6),
                    "material_bought_sqm": round(material_bought_sqm, 6) if material_bought_sqm is not None else None,
                    "sheets_required": sheets_required,
                    "roll_length_m": None,
                },
                "rates_applied": rates_applied,
                "time": {"setup_min": round(setup_min, 2), "print_min": print_min, "total_min": round(total_min, 2)},
                "ink": ink_dict,
                "warnings": meta_warnings + rate_warnings + print_warnings + ink_warnings,
            }
        else:
            ink_dict = {"coverage_pct": 15.0, "ink_ml": 0.0, "ink_cost_gbp": 0.0}
            no_machine_warnings = mach_warnings + [
                "Machine not resolved: print_min=null, ink_cost_gbp=0, no rates. Run seed or check machines.process/active."
            ]
            result["warnings"].extend(no_machine_warnings)
            result["setup_cost"] = 0.0
            result["print_cost"] = 0.0
            result["finishing_cost"] = 0.0
            result["production"] = {
                "lane": lane,
                "machine_key": machine_key,
                "machine_name": None,
                "quantities": {
                    "printed_area_sqm": round(printed_area_sqm, 6),
                    "material_bought_sqm": round(material_bought_sqm, 6) if material_bought_sqm is not None else None,
                    "sheets_required": sheets_required,
                    "roll_length_m": None,
                },
                "rates_applied": [],
                "time": {"setup_min": 0.0, "print_min": None, "total_min": 0.0},
                "ink": ink_dict,
                "warnings": no_machine_warnings,
            }
            total_machine_cost = 0.0

        total_cost = (selected.get("material_cost") or 0) + total_machine_cost
        result["total_cost"] = round(total_cost, 2)
        result["sell_price"] = round(total_cost * 1.5, 2)
    else:
        lane = defaults["lane"]
        printed_area_sqm = qty * w_mm * h_mm / 1e6
        machine, mach_warnings = _resolve_machine(db, job_type, lane)
        result["warnings"].extend(mach_warnings)
        result["warnings"].append("Roll materials: nesting not implemented; material_cost placeholder")

        if machine:
            meta_warnings = _machine_meta_warnings(machine)
            result["warnings"].extend(meta_warnings)
            setup_override = float(part.setup_minutes_override) if part.setup_minutes_override is not None else None
            rates_applied, total_machine_cost, setup_min, rate_warnings, setup_cost_sum, print_cost_sum, finishing_cost_sum = _apply_machine_rates(
                db, machine, printed_area_sqm, printed_area_sqm, setup_minutes_override=setup_override
            )
            result["warnings"].extend(rate_warnings)
            print_min, print_warnings = _compute_print_min(machine, printed_area_sqm)
            ink_dict, ink_cost_gbp, ink_warnings = _compute_ink(machine, printed_area_sqm)
            total_machine_cost += ink_cost_gbp
            result["warnings"].extend(print_warnings)
            result["warnings"].extend(ink_warnings)
            total_min = setup_min + (print_min or 0)
            result["setup_cost"] = round(setup_cost_sum, 2)
            result["print_cost"] = round(print_cost_sum, 2)
            result["finishing_cost"] = round(finishing_cost_sum, 2)
            result["production"] = {
                "lane": lane,
                "machine_key": machine_key,
                "machine_name": machine.name,
                "quantities": {
                    "printed_area_sqm": round(printed_area_sqm, 6),
                    "material_bought_sqm": None,
                    "sheets_required": None,
                    "roll_length_m": None,
                },
                "rates_applied": rates_applied,
                "time": {"setup_min": round(setup_min, 2), "print_min": print_min, "total_min": round(total_min, 2)},
                "ink": ink_dict,
                "warnings": meta_warnings + rate_warnings + print_warnings + ink_warnings,
            }
        else:
            ink_dict = {"coverage_pct": 15.0, "ink_ml": 0.0, "ink_cost_gbp": 0.0}
            no_machine_warnings = mach_warnings + [
                "Machine not resolved: print_min=null, ink_cost_gbp=0, no rates. Run seed or check machines.process/active."
            ]
            result["warnings"].extend(no_machine_warnings)
            result["setup_cost"] = 0.0
            result["print_cost"] = 0.0
            result["finishing_cost"] = 0.0
            result["production"] = {
                "lane": lane,
                "machine_key": machine_key,
                "machine_name": None,
                "quantities": {
                    "printed_area_sqm": round(printed_area_sqm, 6),
                    "material_bought_sqm": None,
                    "sheets_required": None,
                    "roll_length_m": None,
                },
                "rates_applied": [],
                "time": {"setup_min": 0.0, "print_min": None, "total_min": 0.0},
                "ink": ink_dict,
                "warnings": no_machine_warnings,
            }
            total_machine_cost = 0.0

        material_cost = 0.0
        result["material_cost"] = None
        result["total_cost"] = round(material_cost + total_machine_cost, 2)
        result["sell_price"] = round((material_cost + total_machine_cost) * 1.5, 2)

    # Guarantee production is always on the returned dict (required by /calculate)
    if "production" not in result:
        result["production"] = default_production
    return result


def price_quote(db: Session, quote_id: str) -> dict:
    """Full quote pricing. Does NOT persist. Returns QuotePriceResult."""
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise ValueError("Quote not found")
    parts = db.query(QuotePart).filter(QuotePart.quote_id == quote_id).order_by(QuotePart.id).all()

    rates = db.query(Rate).filter(Rate.active == True).all()
    rates_by_type = {
        r.rate_type: {
            "setup_minutes": r.setup_minutes,
            "hourly_cost_gbp": r.hourly_cost_gbp,
            "run_speed": r.run_speed or {},
        }
        for r in rates
    }

    priced_parts = []
    totals_by_lane = {}
    for p in parts:
        part_job_type = normalize_job_type(p.job_type)
        pr = _price_part(db, p, part_job_type, rates_by_type)
        priced_parts.append(pr)
        lane = pr["routing"].get("lane", "unknown")
        totals_by_lane[lane] = totals_by_lane.get(lane, 0) + (pr.get("total_cost") or 0)

    total_cost = sum(pr.get("total_cost") or 0 for pr in priced_parts)
    total_sell = sum(pr.get("sell_price") or 0 for pr in priced_parts)
    all_warnings = []
    for pr in priced_parts:
        all_warnings.extend([f"{pr['part_name']}: {w}" for w in pr.get("warnings", [])])

    input_hash = compute_input_hash(db, quote, parts)
    pv = _pricing_version()

    return {
        "pricing_version": pv,
        "input_hash": input_hash,
        "parts": priced_parts,
        "totals": {
            "total_cost": round(total_cost, 2),
            "total_sell": round(total_sell, 2),
        },
        "totals_by_lane": {k: round(v, 2) for k, v in totals_by_lane.items()},
        "warnings": all_warnings,
    }
