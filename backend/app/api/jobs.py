"""Core Jobs API: create and list jobs."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.api.permissions import require_admin
from app.models.user import User
from app.models.job import Job
from app.services.job_service import create_job
from app.schemas.job import JobCreate, JobOut, JobCreateOut

router = APIRouter()


@router.post("/jobs", response_model=JobCreateOut)
def create_job_endpoint(
    payload: JobCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    job_id, job_no = create_job(db, customer_id=payload.customer_id, title=payload.title)
    db.commit()
    return {"id": job_id, "job_no": job_no}


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    q = db.query(Job).order_by(Job.job_no.desc())
    if status:
        q = q.filter(Job.status == status)
    return q.all()
