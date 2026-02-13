from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, Integer
from app.core.db import Base
from app.models.base import TimestampMixin


class PackingStoreLineItem(Base, TimestampMixin):
    __tablename__ = "packing_store_line_items"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    store_job_id: Mapped[str] = mapped_column(String, ForeignKey("packing_store_jobs.id", ondelete="CASCADE"), index=True)
    component: Mapped[str] = mapped_column(String, default="")
    description: Mapped[str] = mapped_column(String, default="")
    qty: Mapped[int] = mapped_column(Integer, default=0)
