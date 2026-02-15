from typing import Optional

from pydantic import BaseModel


class DocumentTemplateOut(BaseModel):
    id: str
    doc_type: str
    name: str
    active: bool

    file_id: Optional[str] = None
    filename: str = ""

    # file metadata (nullable when no file)
    file_storage_key: Optional[str] = None
    file_mime: Optional[str] = None
    file_size: Optional[int] = None

    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentTemplateTypesOut(BaseModel):
    types: list[str]

