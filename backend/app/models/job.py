from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, Text
from app.core.db import Base
from app.models.base import TimestampMixin
from app.services.job_routing import JobType


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_no: Mapped[str] = mapped_column(String, unique=True, index=True)
    customer_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("customers.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="open", index=True)
    job_type: Mapped[str] = mapped_column(String, default=JobType.LARGE_FORMAT_SHEET, index=True)
