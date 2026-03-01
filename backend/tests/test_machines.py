"""Tests for machines API: meta merge on update."""
import pytest
import app.models  # noqa: F401 - register all tables
from app.models.base import new_id
from app.models.machine import Machine


def test_machine_meta_merge_preserves_ink_keys(db_session, app_with_auth_bypass):
    """Update with partial meta must not wipe ink/time keys. Merge existing + incoming."""
    from fastapi.testclient import TestClient

    m = Machine(
        id=new_id(),
        name=f"Test Machine {new_id()[:8]}",
        category="printer_sheet",
        process="uv_flatbed",
        active=True,
        sort_order=0,
        meta={
            "sheet_max_width_mm": 3200,
            "sheet_max_height_mm": 2000,
            "ink_cost_per_litre_gbp": 180,
            "ink_ml_per_sqm_100pct": 8,
            "speed_sqm_per_hour": 12,
            "default_coverage_pct": 15,
        },
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)

    client = TestClient(app_with_auth_bypass)
    # Payload only includes sheet dimensions (typical edit form); must not remove ink keys
    r = client.put(
        f"/api/machines/{m.id}",
        json={
            "meta": {
                "sheet_max_width_mm": 3100,
                "sheet_max_height_mm": 1900,
            },
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    meta = data.get("meta") or {}
    # Incoming keys updated
    assert meta.get("sheet_max_width_mm") == 3100
    assert meta.get("sheet_max_height_mm") == 1900
    # Existing ink/time keys preserved
    assert meta.get("ink_cost_per_litre_gbp") == 180
    assert meta.get("ink_ml_per_sqm_100pct") == 8
    assert meta.get("speed_sqm_per_hour") == 12
    assert meta.get("default_coverage_pct") == 15
