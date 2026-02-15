from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_serializer


class POTemplateIn(BaseModel):
    config: dict[str, Any]


class POTemplateOut(BaseModel):
    id: str | None = None
    key: str
    name: str
    config: dict[str, Any]
    default_config: dict[str, Any]
    updated_at: datetime | None = None

    @field_serializer("updated_at")
    def serialize_dt(self, v: datetime | None, _info):
        return v.isoformat() if v is not None else None
