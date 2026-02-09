import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, func

def new_id() -> str:
    return str(uuid.uuid4())

class TimestampMixin:
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
