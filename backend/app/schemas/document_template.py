from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class DocumentTemplateCreate(BaseModel):
    doc_type: str
    name: str = ""
    engine: str = "html_jinja"
    content: Optional[str] = ""
    template_html: Optional[str] = None
    template_json: Optional[str] = None
    template_css: Optional[str] = None
    is_active: bool = True


class DocumentTemplateUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    template_html: Optional[str] = None
    template_json: Optional[str] = None
    template_css: Optional[str] = None
    is_active: Optional[bool] = None


class DocumentTemplatePreview(BaseModel):
    template_html: Optional[str] = None
    template_css: Optional[str] = None
    content: Optional[str] = None
    doc_type: str = "purchase_order"
    entity_id: Optional[str] = None
    template_version_id: Optional[str] = None


class DocumentTemplateVersionOut(BaseModel):
    id: str
    template_id: str
    version_num: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentTemplateOut(BaseModel):
    id: str
    doc_type: str
    name: str
    engine: str
    content: str = "{}"
    template_html: Optional[str] = None
    template_json: Optional[str] = None
    template_css: Optional[str] = None
    current_version_id: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("content", mode="before")
    @classmethod
    def coerce_content(cls, v: Optional[str]) -> str:
        return v if v is not None else "{}"

    class Config:
        from_attributes = True

