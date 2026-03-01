from typing import Optional
from pydantic import BaseModel
from app.services.job_routing import JobType


class JobCreate(BaseModel):
    customer_id: Optional[str] = None
    title: Optional[str] = None
    job_type: Optional[str] = JobType.LARGE_FORMAT_SHEET


class JobOut(BaseModel):
    id: str
    job_no: str
    customer_id: Optional[str] = None
    title: str
    status: str
    job_type: str = JobType.LARGE_FORMAT_SHEET

    class Config:
        from_attributes = True


class JobCreateOut(BaseModel):
    id: str
    job_no: str
