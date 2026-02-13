from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from app.core.db import Base
from app.models.base import TimestampMixin


class JobVersion(Base, TimestampMixin):
    __tablename__ = "job_versions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_json: Mapped[dict] = mapped_column(JSONB, default=dict)
