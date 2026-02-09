from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, Integer, ForeignKey
from app.core.db import Base
from app.models.base import TimestampMixin

class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    supplier_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("suppliers.id"), nullable=True)

    email: Mapped[str] = mapped_column(String, default="")
    phone: Mapped[str] = mapped_column(String, default="")
    website: Mapped[str] = mapped_column(String, default="")
    account_ref: Mapped[str] = mapped_column(String, default="")

    lead_time_days_default: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(String, default="")

    active: Mapped[bool] = mapped_column(Boolean, default=True)
