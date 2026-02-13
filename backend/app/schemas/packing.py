from typing import Optional
from pydantic import BaseModel


class PackingBatchCreate(BaseModel):
    job_id: str
    name: str = ""


class PackingBatchOut(BaseModel):
    id: str
    job_id: str
    name: str

    class Config:
        from_attributes = True


class PackingStoreJobOut(BaseModel):
    id: str
    batch_id: str
    store_name: str
    status: str
    box_count: Optional[int] = None
    notes: Optional[str] = None
    packed_at: Optional[str] = None
    dispatched_at: Optional[str] = None

    class Config:
        from_attributes = True


class PackingStoreLineItemOut(BaseModel):
    id: str
    store_job_id: str
    component: str
    description: str
    qty: int

    class Config:
        from_attributes = True


class PackingStoreJobUpdate(BaseModel):
    status: Optional[str] = None
    box_count: Optional[int] = None
    notes: Optional[str] = None


class PackingStoreJobDetailOut(PackingStoreJobOut):
    line_items: list[PackingStoreLineItemOut] = []
