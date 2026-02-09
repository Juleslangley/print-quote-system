from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, JSON
from app.core.db import Base
from app.models.base import TimestampMixin


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)

    email: Mapped[str] = mapped_column(String, default="")
    phone: Mapped[str] = mapped_column(String, default="")
    website: Mapped[str] = mapped_column(String, default="")

    billing_name: Mapped[str] = mapped_column(String, default="")
    billing_email: Mapped[str] = mapped_column(String, default="")
    billing_phone: Mapped[str] = mapped_column(String, default="")
    billing_address: Mapped[str] = mapped_column(String, default="")

    vat_number: Mapped[str] = mapped_column(String, default="")
    account_ref: Mapped[str] = mapped_column(String, default="")
    notes: Mapped[str] = mapped_column(String, default="")

    # future-proof overrides (min charge, rounding, margin profile etc.)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)

    active: Mapped[bool] = mapped_column(Boolean, default=True)

    default_margin_profile_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
