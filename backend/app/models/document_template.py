from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, String, Text, Index

from app.core.db import Base
from app.models.base import TimestampMixin


class DocumentTemplate(Base, TimestampMixin):
    __tablename__ = "document_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    doc_type: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String, default="")
    engine: Mapped[str] = mapped_column(String, default="html_jinja")
    content: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        Index("ix_document_templates_doc_type_is_active", "doc_type", "is_active"),
    )

