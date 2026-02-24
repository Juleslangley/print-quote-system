from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func

from app.core.db import Base


class DocumentTemplateVersion(Base):
    __tablename__ = "document_template_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    template_id: Mapped[str] = mapped_column(
        String, ForeignKey("document_templates.id", ondelete="CASCADE"), index=True
    )
    template_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_css: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
