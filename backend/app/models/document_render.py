from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, ForeignKey, String, func, Index

from app.core.db import Base


class DocumentRender(Base):
    __tablename__ = "document_renders"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    doc_type: Mapped[str] = mapped_column(String, index=True)
    entity_id: Mapped[str] = mapped_column(String, index=True)
    template_id: Mapped[str] = mapped_column(String, ForeignKey("document_templates.id", ondelete="RESTRICT"), index=True)
    file_id: Mapped[str] = mapped_column(String, ForeignKey("files.id", ondelete="RESTRICT"), index=True)
    created_by_user_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_document_renders_doc_type_entity_id", "doc_type", "entity_id"),
    )

