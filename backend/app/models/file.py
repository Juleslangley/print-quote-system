from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, ForeignKey
from app.core.db import Base
from app.models.base import TimestampMixin


class File(Base, TimestampMixin):
    __tablename__ = "files"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    storage_key: Mapped[str] = mapped_column(String, unique=True, index=True)
    mime: Mapped[str] = mapped_column(String, default="application/octet-stream")
    size: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String, default="")
    uploaded_by: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
