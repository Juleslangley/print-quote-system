from app.models.machine import Machine
from app.models.machine_rate import MachineRate
from app.models.base import new_id


def upsert_machine(db, name: str, **kwargs):
    m = db.query(Machine).filter(Machine.name == name).first()
    if not m:
        m = Machine(id=new_id(), name=name, **kwargs)
        db.add(m)
        db.flush()
        print(f"  ✓ Created machine: {name}")
    else:
        for k, v in kwargs.items():
            setattr(m, k, v)
        db.add(m)
        db.flush()
        print(f"  ✓ Updated machine: {name}")
    return m


def upsert_rate(db, machine, operation_key: str, unit: str, **kwargs):
    r = db.query(MachineRate).filter(
        MachineRate.machine_id == machine.id,
        MachineRate.operation_key == operation_key
    ).first()

    if not r:
        r = MachineRate(
            id=new_id(),
            machine_id=machine.id,
            operation_key=operation_key,
            unit=unit,
            **kwargs
        )
        db.add(r)
        print(f"     + Created rate: {machine.name} / {operation_key}")
    else:
        r.unit = unit
        for k, v in kwargs.items():
            setattr(r, k, v)
        db.add(r)
        print(f"     + Updated rate: {machine.name} / {operation_key}")

    return r


def seed_machines(db):
    print("🔧 Seeding machines...")

    # -----------------------------
    # SwissQ Nyala 5
    # -----------------------------
    nyala = upsert_machine(
        db,
        "SwissQ Nyala 5",
        category="printer_sheet",
        process="uv_flatbed",
        active=True,
        sort_order=10,
        notes="UV flatbed sheet printer",
        meta={
            "sheet_max_width_mm": 3200,
            "sheet_max_height_mm": 2000,
            "supports_white": True,
            "ink_family": "UV",
            "speed_sqm_per_hour": 55,
            "ink_cost_per_litre_gbp": 45,
            "ink_ml_per_sqm_100pct": 12,
            "default_coverage_pct": 18,
        }
    )

    upsert_rate(db, nyala, "print_sqm", "sqm",
        cost_per_unit_gbp=2.25,
        setup_minutes=10,
        setup_cost_gbp=0,
        min_charge_gbp=20,
        active=True,
        sort_order=10
    )

    upsert_rate(db, nyala, "white_ink_sqm", "sqm",
        cost_per_unit_gbp=0.75,
        setup_minutes=0,
        setup_cost_gbp=0,
        min_charge_gbp=0,
        active=True,
        sort_order=20
    )

    # -----------------------------
    # Fujifilm Acuity Prime
    # -----------------------------
    acuity = upsert_machine(
        db,
        "Fujifilm Acuity Prime",
        category="printer_sheet",
        process="uv_flatbed",
        active=False,  # Deactivated: removed from default routing; kept for history
        sort_order=20,
        notes="UV flatbed sheet printer",
        meta={
            "sheet_max_width_mm": 2500,
            "sheet_max_height_mm": 1250,
            "supports_white": True,
            "ink_family": "UV"
        }
    )

    upsert_rate(db, acuity, "print_sqm", "sqm",
        cost_per_unit_gbp=2.05,
        setup_minutes=8,
        setup_cost_gbp=0,
        min_charge_gbp=18,
        active=True,
        sort_order=10
    )

    # -----------------------------
    # Epson SureColor (EcoSolvent Roll)
    # -----------------------------
    epson = upsert_machine(
        db,
        "Epson SureColor",
        category="printer_roll",
        process="eco_solvent_roll",
        active=True,
        sort_order=25,
        notes="Eco-solvent roll printer",
        meta={
            "roll_max_width_mm": 1600,
            "ink_family": "EcoSolvent",
            "min_lm_billable_default": 1.0,
            "speed_sqm_per_hour": 18,
            "ink_cost_per_litre_gbp": 120,
            "ink_ml_per_sqm_100pct": 10,
            "default_coverage_pct": 15,
        }
    )

    upsert_rate(db, epson, "print_sqm", "sqm",
        cost_per_unit_gbp=1.85,
        setup_minutes=10,
        setup_cost_gbp=0,
        min_charge_gbp=15,
        active=True,
        sort_order=10
    )

    upsert_rate(db, epson, "laminate_sqm", "sqm",
        cost_per_unit_gbp=0.90,
        setup_minutes=5,
        setup_cost_gbp=0,
        min_charge_gbp=10,
        active=True,
        sort_order=20
    )

    # -----------------------------
    # HP SC 8600 (EcoSolvent 1600) - kept for history
    # -----------------------------
    hp = upsert_machine(
        db,
        "HP SC 8600",
        category="printer_roll",
        process="eco_solvent_roll",
        active=True,
        sort_order=30,
        notes="1600mm Eco-solvent roll printer",
        meta={
            "roll_max_width_mm": 1600,
            "ink_family": "EcoSolvent",
            "min_lm_billable_default": 1.0
        }
    )

    upsert_rate(db, hp, "print_sqm", "sqm",
        cost_per_unit_gbp=1.85,
        setup_minutes=10,
        setup_cost_gbp=0,
        min_charge_gbp=15,
        active=True,
        sort_order=10
    )

    upsert_rate(db, hp, "laminate_sqm", "sqm",
        cost_per_unit_gbp=0.90,
        setup_minutes=5,
        setup_cost_gbp=0,
        min_charge_gbp=10,
        active=True,
        sort_order=20
    )

    # -----------------------------
    # Zünd Cutter
    # -----------------------------
    zund = upsert_machine(
        db,
        "Zünd",
        category="cutter",
        process="digital_cut",
        active=True,
        sort_order=40,
        notes="Digital cutting table",
        meta={
            "bed_width_mm": 3200,
            "bed_height_mm": 2200,
            "tools": [
                {"key": "cut", "name": "Cut", "speed_m_per_min": 10},
                {"key": "route", "name": "Route", "speed_m_per_min": 2},
                {"key": "crease", "name": "Crease", "speed_m_per_min": 15},
            ]
        }
    )

    upsert_rate(db, zund, "cut_hour", "hour",
        cost_per_unit_gbp=35.0,
        setup_minutes=10,
        setup_cost_gbp=0,
        min_charge_gbp=15,
        active=True,
        sort_order=10
    )

    db.commit()
    print("✅ Machine seeding complete.")
