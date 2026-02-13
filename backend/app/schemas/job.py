from typing import Optional
from pydantic import BaseModel


class JobCreate(BaseModel):
    customer_id: Optional[str] = None
    title: Optional[str] = None


class JobOut(BaseModel):
    id: str
    job_no: str
    customer_id: Optional[str] = None
    title: str
    status: str

    class Config:
        from_attributes = True


class JobCreateOut(BaseModel):
    id: str
    job_no: str
