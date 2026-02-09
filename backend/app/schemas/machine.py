from typing import Optional
from pydantic import BaseModel, field_validator


class MachineCreate(BaseModel):
    name: str
    category: str  # printer_sheet | printer_roll | cutter | finisher
    process: str = ""
    active: bool = True
    sort_order: int = 0
    notes: str = ""
    meta: dict = {}


class MachineUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    process: Optional[str] = None
    active: Optional[bool] = None
    sort_order: Optional[int] = None
    notes: Optional[str] = None
    meta: Optional[dict] = None


class MachineOut(BaseModel):
    id: str
    name: str
    category: str
    process: str
    active: bool
    sort_order: int
    notes: str
    meta: dict = {}

    class Config:
        from_attributes = True

    @field_validator("meta", mode="before")
    @classmethod
    def meta_default(cls, v):
        return v if v is not None else {}


class MachineReorderIn(BaseModel):
    ids: list[str]  # ordered list of machine ids
