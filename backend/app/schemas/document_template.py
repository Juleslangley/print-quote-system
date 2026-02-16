from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DocumentTemplateCreate(BaseModel):
    doc_type: str
    name: str = ""
    engine: str = "html_jinja"
    content: str = ""
    is_active: bool = True


class DocumentTemplateUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None


class DocumentTemplateOut(BaseModel):
    id: str
    doc_type: str
    name: str
    engine: str
    content: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

