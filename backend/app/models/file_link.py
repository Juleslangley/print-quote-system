from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey
from app.core.db import Base
from app.models.base import TimestampMixin


class FileLink(Base, TimestampMixin):
    __tablename__ = "file_links"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    file_id: Mapped[str] = mapped_column(String, ForeignKey("files.id", ondelete="CASCADE"), index=True)
    entity_type: Mapped[str] = mapped_column(String, index=True)
    entity_id: Mapped[str] = mapped_column(String, index=True)
    tag: Mapped[str] = mapped_column(String, default="", index=True)
