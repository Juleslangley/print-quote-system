"""Job domain service: create jobs and generate job numbers."""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.base import new_id
from app.models.job import Job
from app.models.job_no_sequence import JobNoSequence
from app.core.config import settings
from app.services.job_routing import normalize_job_type


SEQUENCE_NAME = "default"


def generate_job_no(db: Session) -> str:
    """Generate next job number (e.g. J0001). Single place for format; prefix from config."""
    row = db.query(JobNoSequence).filter(JobNoSequence.name == SEQUENCE_NAME).with_for_update().first()
    if not row:
        row = JobNoSequence(name=SEQUENCE_NAME, next_val=1)
        db.add(row)
        db.flush()
    num = row.next_val
    row.next_val = num + 1
    db.flush()
    prefix = getattr(settings, "JOB_NO_PREFIX", "J")
    return f"{prefix}{num:04d}"


def create_job(
    db: Session,
    customer_id: Optional[str] = None,
    title: Optional[str] = None,
    job_type: Optional[str] = None,
) -> tuple[str, str]:
    """Create a job and return (job_id, job_no)."""
    job_no = generate_job_no(db)
    job_id = new_id()
    job = Job(
        id=job_id,
        job_no=job_no,
        customer_id=customer_id,
        title=title or "",
        status="open",
        job_type=normalize_job_type(job_type),
    )
    db.add(job)
    db.flush()
    return job_id, job_no
