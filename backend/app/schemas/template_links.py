from typing import Optional
from pydantic import BaseModel

class TemplateOperationAdd(BaseModel):
    operation_id: str
    sort_order: int = 0
    params_override: dict = {}

class TemplateOperationUpdate(BaseModel):
    sort_order: Optional[int] = None
    params_override: Optional[dict] = None

class TemplateOperationOut(BaseModel):
    id: str
    template_id: str
    operation_id: str
    sort_order: int
    params_override: dict
    class Config:
        from_attributes = True

class TemplateOperationReorderItem(BaseModel):
    link_id: str
    sort_order: int

class TemplateOperationReorder(BaseModel):
    items: list[TemplateOperationReorderItem]

class TemplateAllowedMaterialAdd(BaseModel):
    material_id: str

class TemplateAllowedMaterialOut(BaseModel):
    id: str
    template_id: str
    material_id: str
    class Config:
        from_attributes = True
