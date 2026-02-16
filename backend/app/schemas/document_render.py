from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DocumentRenderOut(BaseModel):
    id: str
    doc_type: str
    entity_id: str
    template_id: str
    file_id: str
    created_by_user_id: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

