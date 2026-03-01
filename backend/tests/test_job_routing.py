from fastapi.testclient import TestClient

from app.models.base import new_id
from app.models.material import Material
from app.models.job import Job
from app.services.job_routing import (
    JobType,
    apply_defaults_to_item_options,
    get_jobtype_defaults,
)
from app.services.job_service import create_job


def test_default_routing_for_new_job(db_session):
    job_id, _ = create_job(db_session, title="Routing default job")
    db_session.commit()
    job = db_session.query(Job).filter(Job.id == job_id).first()
    assert job is not None
    assert job.job_type == JobType.LARGE_FORMAT_SHEET

    defaults = get_jobtype_defaults(job.job_type)
    assert defaults["lane"] == "LF_SHEET"
    assert defaults["default_machine_key"] == "NYALA"


def test_non_destructive_waste_override_kept_when_job_type_changes():
    options = {"waste_pct": 0.22}
    applied = apply_defaults_to_item_options(options, JobType.LARGE_FORMAT_ROLL)
    assert applied["waste_pct"] == 0.22
    assert applied["setup_minutes"] == 20


def test_materials_filter_by_job_type(db_session, app_with_auth_bypass):
    roll_only = Material(
        id=new_id(),
        name="Roll only test material",
        type="roll",
        supplier="",
        supplier_id=None,
        active=True,
        meta={"allowed_job_types": [JobType.LARGE_FORMAT_ROLL]},
    )
    sheet_only = Material(
        id=new_id(),
        name="Sheet only test material",
        type="sheet",
        supplier="",
        supplier_id=None,
        active=True,
        meta={"allowed_job_types": [JobType.LARGE_FORMAT_SHEET]},
    )
    db_session.add_all([roll_only, sheet_only])
    db_session.commit()

    client = TestClient(app_with_auth_bypass)
    roll_res = client.get(f"/api/materials?job_type={JobType.LARGE_FORMAT_ROLL}")
    assert roll_res.status_code == 200, roll_res.text
    roll_ids = {m["id"] for m in roll_res.json()}
    assert roll_only.id in roll_ids
    assert sheet_only.id not in roll_ids

    sheet_res = client.get(f"/api/materials?job_type={JobType.LARGE_FORMAT_SHEET}")
    assert sheet_res.status_code == 200, sheet_res.text
    sheet_ids = {m["id"] for m in sheet_res.json()}
    assert sheet_only.id in sheet_ids
    assert roll_only.id not in sheet_ids

