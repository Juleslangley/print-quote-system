from sqlalchemy import Boolean, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class DocumentTemplate(Base, TimestampMixin):
    __tablename__ = "document_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    key: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String, default="Document template")
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
