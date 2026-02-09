from typing import Optional
from pydantic import BaseModel

class TemplateCreate(BaseModel):
    name: str
    category: str  # rigid/roll
    default_material_id: str
    default_machine_id: Optional[str] = None
    rules: dict = {}
    active: bool = True

class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    default_material_id: Optional[str] = None
    default_machine_id: Optional[str] = None
    rules: Optional[dict] = None
    active: Optional[bool] = None

class TemplateOut(BaseModel):
    id: str
    name: str
    category: str
    default_material_id: str
    default_machine_id: Optional[str]
    rules: dict
    active: bool

    class Config:
        from_attributes = True
