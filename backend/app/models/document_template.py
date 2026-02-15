from typing import Optional

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class DocumentTemplate(Base, TimestampMixin):
    """
    Stores admin-managed template files for PDFs we generate (PO, invoice, quote, etc.).
    The actual bytes live in UPLOADS_DIR (see api/document_templates.py); this table stores metadata + the file_id pointer.
    """

    __tablename__ = "document_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    # purchase_order | invoice | quote | credit_note | production_order
    doc_type: Mapped[str] = mapped_column(String, unique=True, index=True)

    name: Mapped[str] = mapped_column(String, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    file_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String, default="")

