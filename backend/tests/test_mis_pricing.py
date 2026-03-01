"""Tests for MIS-style quotation: input_hash, lock-price no-op, auto-unlock."""
import pytest
import app.models  # noqa: F401 - register all tables
from app.models.base import new_id
from app.models.quote import Quote
from app.models.quote_part import QuotePart
from app.models.quote_price_snapshot import QuotePriceSnapshot
from app.models.customer import Customer
from app.models.machine import Machine
from app.models.machine_rate import MachineRate
from app.models.material import Material
from app.models.material_size import MaterialSize
from app.services.mis_pricing import compute_input_hash, price_quote


def test_nesting_best_sheet_selected(db_session):
    """2 sheet sizes with prices -> verify best selected and alternatives sorted."""
    cust = db_session.query(Customer).first()
    if not cust:
        cust = Customer(id=new_id(), name="Test")
        db_session.add(cust)
        db_session.flush()

    mat = Material(
        id=new_id(),
        name="Test Sheet",
        type="sheet",
        waste_pct_default=0.05,
    )
    db_session.add(mat)
    db_session.flush()

    # Add 2 sheet sizes: 1000x1000 @ £20, 2000x1000 @ £35 (cheaper per sqm for large)
    s1 = MaterialSize(
        id=new_id(),
        material_id=mat.id,
        label="1000x1000",
        width_mm=1000,
        height_mm=1000,
        cost_per_sheet_gbp=20.0,
        active=True,
    )
    s2 = MaterialSize(
        id=new_id(),
        material_id=mat.id,
        label="2000x1000",
        width_mm=2000,
        height_mm=1000,
        cost_per_sheet_gbp=35.0,
        active=True,
    )
    db_session.add_all([s1, s2])
    db_session.flush()

    q = Quote(
        id=new_id(),
        quote_number=f"Q-TEST-{new_id()[:8]}",
        customer_id=cust.id,
        status="draft",
        pricing_version="v1",
        default_job_type="LARGE_FORMAT_SHEET",
    )
    db_session.add(q)
    db_session.flush()

    p = QuotePart(
        id=new_id(),
        quote_id=q.id,
        name="P",
        job_type="LARGE_FORMAT_SHEET",
        material_id=mat.id,
        finished_w_mm=400,
        finished_h_mm=400,
        quantity=10,
        sides=1,
    )
    db_session.add(p)
    db_session.commit()

    result = price_quote(db_session, q.id)
    assert len(result["parts"]) == 1
    part_result = result["parts"][0]
    assert part_result["selected_sheet"] is not None
    assert part_result["selected_sheet"]["per_sheet"] > 0
    assert part_result["selected_sheet"]["material_cost"] is not None
    alts = part_result.get("alternatives", [])
    assert len(alts) <= 3
    costs = [a.get("material_cost") or 999999 for a in alts]
    assert costs == sorted(costs)


def test_input_hash_determinism(db_session):
    """Same inputs => same hash."""
    cust = db_session.query(Customer).first()
    if not cust:
        cust = Customer(id=new_id(), name="Test")
        db_session.add(cust)
        db_session.flush()

    mat = db_session.query(Material).filter(Material.type == "sheet").first()
    if not mat:
        mat = Material(
            id=new_id(),
            name="Test Sheet",
            type="sheet",
            sheet_width_mm=1220,
            sheet_height_mm=2440,
            cost_per_sheet_gbp=18.0,
            waste_pct_default=0.05,
        )
        db_session.add(mat)
        db_session.flush()

    q = Quote(
        id=new_id(),
        quote_number=f"Q-TEST-{new_id()[:8]}",
        customer_id=cust.id,
        status="draft",
        pricing_version="v1",
        default_job_type="LARGE_FORMAT_SHEET",
        name="Test Quote",
    )
    db_session.add(q)
    db_session.flush()

    p = QuotePart(
        id=new_id(),
        quote_id=q.id,
        name="Part 1",
        job_type="LARGE_FORMAT_SHEET",
        material_id=mat.id,
        finished_w_mm=500,
        finished_h_mm=500,
        quantity=10,
        sides=1,
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(q)
    db_session.refresh(p)
    parts = [p]

    h1 = compute_input_hash(db_session, q, parts)
    h2 = compute_input_hash(db_session, q, parts)
    assert h1 == h2


def test_input_hash_changes_with_qty(db_session):
    """Changing qty => different hash."""
    cust = db_session.query(Customer).first()
    if not cust:
        cust = Customer(id=new_id(), name="Test")
        db_session.add(cust)
        db_session.flush()

    mat = db_session.query(Material).filter(Material.type == "sheet").first()
    if not mat:
        mat = Material(
            id=new_id(),
            name="Test Sheet",
            type="sheet",
            sheet_width_mm=1220,
            sheet_height_mm=2440,
            cost_per_sheet_gbp=18.0,
            waste_pct_default=0.05,
        )
        db_session.add(mat)
        db_session.flush()

    q = Quote(
        id=new_id(),
        quote_number=f"Q-TEST-{new_id()[:8]}",
        customer_id=cust.id,
        status="draft",
        pricing_version="v1",
        default_job_type="LARGE_FORMAT_SHEET",
    )
    db_session.add(q)
    db_session.flush()

    p = QuotePart(
        id=new_id(),
        quote_id=q.id,
        name="P",
        job_type="LARGE_FORMAT_SHEET",
        material_id=mat.id,
        finished_w_mm=500,
        finished_h_mm=500,
        quantity=10,
        sides=1,
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    parts = [p]

    h1 = compute_input_hash(db_session, q, parts)
    p.quantity = 20
    h2 = compute_input_hash(db_session, q, parts)
    assert h1 != h2


def test_input_hash_changes_with_job_type(db_session):
    """Changing part.job_type => different hash."""
    cust = db_session.query(Customer).first()
    if not cust:
        cust = Customer(id=new_id(), name="Test")
        db_session.add(cust)
        db_session.flush()

    mat = db_session.query(Material).filter(Material.type == "sheet").first()
    if not mat:
        mat = Material(
            id=new_id(),
            name="Test Sheet",
            type="sheet",
            sheet_width_mm=1220,
            sheet_height_mm=2440,
            cost_per_sheet_gbp=18.0,
            waste_pct_default=0.05,
        )
        db_session.add(mat)
        db_session.flush()

    q = Quote(
        id=new_id(),
        quote_number=f"Q-TEST-{new_id()[:8]}",
        customer_id=cust.id,
        status="draft",
        pricing_version="v1",
        default_job_type="LARGE_FORMAT_SHEET",
    )
    db_session.add(q)
    db_session.flush()

    p = QuotePart(
        id=new_id(),
        quote_id=q.id,
        name="P",
        job_type="LARGE_FORMAT_SHEET",
        material_id=mat.id,
        finished_w_mm=500,
        finished_h_mm=500,
        quantity=10,
        sides=1,
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    parts = [p]

    h1 = compute_input_hash(db_session, q, parts)
    p.job_type = "LARGE_FORMAT_ROLL"
    h2 = compute_input_hash(db_session, q, parts)
    assert h1 != h2


def test_lock_price_no_op(db_session, app_with_auth_bypass):
    """Lock once => revision 1. Lock again with no changes => created=false, revision still 1."""
    from fastapi.testclient import TestClient
    client = TestClient(app_with_auth_bypass)

    cust = db_session.query(Customer).first()
    if not cust:
        cust = Customer(id=new_id(), name="Test")
        db_session.add(cust)
        db_session.flush()

    mat = db_session.query(Material).filter(Material.type == "sheet").first()
    if not mat:
        mat = Material(
            id=new_id(),
            name="Test Sheet",
            type="sheet",
            sheet_width_mm=1220,
            sheet_height_mm=2440,
            cost_per_sheet_gbp=18.0,
            waste_pct_default=0.05,
        )
        db_session.add(mat)
        db_session.flush()

    q = Quote(
        id=new_id(),
        quote_number=f"Q-TEST-{new_id()[:8]}",
        customer_id=cust.id,
        status="draft",
        pricing_version="v1",
        default_job_type="LARGE_FORMAT_SHEET",
    )
    db_session.add(q)
    db_session.flush()

    p = QuotePart(
        id=new_id(),
        quote_id=q.id,
        name="P",
        job_type="LARGE_FORMAT_SHEET",
        material_id=mat.id,
        finished_w_mm=500,
        finished_h_mm=500,
        quantity=10,
        sides=1,
    )
    db_session.add(p)
    db_session.commit()

    r1 = client.post(f"/api/quotes/{q.id}/lock-price")
    assert r1.status_code == 200
    data1 = r1.json()
    assert data1["created"] is True
    assert data1["snapshot"]["revision"] == 1

    r2 = client.post(f"/api/quotes/{q.id}/lock-price")
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["created"] is False
    assert data2["snapshot"]["revision"] == 1


def test_auto_unlock(db_session, app_with_auth_bypass):
    """Quote PRICED; patch a part => quote becomes DRAFT; snapshots remain."""
    from fastapi.testclient import TestClient
    client = TestClient(app_with_auth_bypass)

    cust = db_session.query(Customer).first()
    if not cust:
        cust = Customer(id=new_id(), name="Test")
        db_session.add(cust)
        db_session.flush()

    mat = db_session.query(Material).filter(Material.type == "sheet").first()
    if not mat:
        mat = Material(
            id=new_id(),
            name="Test Sheet",
            type="sheet",
            sheet_width_mm=1220,
            sheet_height_mm=2440,
            cost_per_sheet_gbp=18.0,
            waste_pct_default=0.05,
        )
        db_session.add(mat)
        db_session.flush()

    q = Quote(
        id=new_id(),
        quote_number=f"Q-TEST-{new_id()[:8]}",
        customer_id=cust.id,
        status="priced",
        pricing_version="v1",
        default_job_type="LARGE_FORMAT_SHEET",
    )
    db_session.add(q)
    db_session.flush()

    p = QuotePart(
        id=new_id(),
        quote_id=q.id,
        name="P",
        job_type="LARGE_FORMAT_SHEET",
        material_id=mat.id,
        finished_w_mm=500,
        finished_h_mm=500,
        quantity=10,
        sides=1,
    )
    db_session.add(p)
    db_session.commit()

    snap = QuotePriceSnapshot(
        id=new_id(),
        quote_id=q.id,
        revision=1,
        pricing_version="v1",
        input_hash="abc123",
        result_json={},
    )
    db_session.add(snap)
    db_session.commit()

    r = client.patch(
        f"/api/quote-parts/{p.id}",
        json={"quantity": 15},
    )
    assert r.status_code == 200

    db_session.refresh(q)
    assert q.status == "draft"

    snap_count = db_session.query(QuotePriceSnapshot).filter(QuotePriceSnapshot.quote_id == q.id).count()
    assert snap_count == 1


def test_machine_rate_min_charge_and_formula(db_session):
    """Epson machine with print_sqm £1.85, setup 10, min £15. Assert min charge and formula."""
    cust = db_session.query(Customer).first()
    if not cust:
        cust = Customer(id=new_id(), name="Test")
        db_session.add(cust)
        db_session.flush()

    # Create Epson machine (eco_solvent_roll) with print_sqm rate
    epson = Machine(
        id=new_id(),
        name="Epson SureColor",
        category="printer_roll",
        process="eco_solvent_roll",
        active=True,
        sort_order=10,
    )
    db_session.add(epson)
    db_session.flush()

    rate = MachineRate(
        id=new_id(),
        machine_id=epson.id,
        operation_key="print_sqm",
        unit="sqm",
        cost_per_unit_gbp=1.85,
        setup_minutes=10,
        setup_cost_gbp=0,
        min_charge_gbp=15,
        active=True,
    )
    db_session.add(rate)
    db_session.flush()

    # Use sort_order=1 so our machine is picked before any seed machines (typically 25+)
    epson.sort_order = 1
    db_session.add(epson)
    db_session.commit()

    mat = Material(
        id=new_id(),
        name="Test Roll",
        type="roll",
        waste_pct_default=0.05,
    )
    db_session.add(mat)
    db_session.flush()

    q = Quote(
        id=new_id(),
        quote_number=f"Q-TEST-{new_id()[:8]}",
        customer_id=cust.id,
        status="draft",
        pricing_version="v1",
        default_job_type="LARGE_FORMAT_ROLL",
    )
    db_session.add(q)
    db_session.flush()

    # Small printed_area_sqm: 1 × 100×100mm = 0.01 sqm. base = 0 + 0.01*1.85 = 0.0185 < 15 -> cost = 15
    p_small = QuotePart(
        id=new_id(),
        quote_id=q.id,
        name="Small",
        job_type="LARGE_FORMAT_ROLL",
        material_id=mat.id,
        finished_w_mm=100,
        finished_h_mm=100,
        quantity=1,
        sides=1,
    )
    db_session.add(p_small)

    # Large printed_area_sqm: 10 × 1000×1000mm = 10 sqm. base = 0 + 10*1.85 = 18.5 > 15 -> cost = 18.5
    p_large = QuotePart(
        id=new_id(),
        quote_id=q.id,
        name="Large",
        job_type="LARGE_FORMAT_ROLL",
        material_id=mat.id,
        finished_w_mm=1000,
        finished_h_mm=1000,
        quantity=10,
        sides=1,
    )
    db_session.add(p_large)
    db_session.commit()

    result = price_quote(db_session, q.id)
    assert len(result["parts"]) == 2

    small_part = next(p for p in result["parts"] if p["part_name"] == "Small")
    assert small_part["production"]["machine_name"] == "Epson SureColor"
    print_rates = [r for r in small_part["production"]["rates_applied"] if r["operation_key"] == "print_sqm"]
    assert len(print_rates) == 1
    assert print_rates[0]["cost_gbp"] == 15  # min charge applies
    assert print_rates[0]["qty"] == 0.01  # 1 * 0.1 * 0.1 = 0.01 sqm

    large_part = next(p for p in result["parts"] if p["part_name"] == "Large")
    print_rates_large = [r for r in large_part["production"]["rates_applied"] if r["operation_key"] == "print_sqm"]
    assert len(print_rates_large) == 1
    expected_cost = 10 * 1.85  # 10 sqm * £1.85
    assert print_rates_large[0]["cost_gbp"] == round(expected_cost, 2)
    assert print_rates_large[0]["qty"] == 10.0  # 10 * 1.0 * 1.0 = 10 sqm

    # Production block includes time and ink
    assert "time" in small_part["production"]
    assert "ink" in small_part["production"]
    time = small_part["production"]["time"]
    assert "setup_min" in time
    assert "print_min" in time
    assert "total_min" in time
    ink = small_part["production"]["ink"]
    assert "coverage_pct" in ink
    assert "ink_ml" in ink
    assert "ink_cost_gbp" in ink
