from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, ForeignKey, Integer
from app.core.db import Base
from app.models.base import TimestampMixin


class CustomerContact(Base, TimestampMixin):
    __tablename__ = "customer_contacts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(String, ForeignKey("customers.id"), index=True)

    # Person fields (CRM-style; use these going forward)
    first_name: Mapped[str] = mapped_column(String, default="")
    last_name: Mapped[str] = mapped_column(String, default="")
    job_title: Mapped[str] = mapped_column(String, default="")
    department: Mapped[str] = mapped_column(String, default="")

    # Legacy / backwards compatibility
    name: Mapped[str] = mapped_column(String, index=True)
    email: Mapped[str] = mapped_column(String, default="")
    phone: Mapped[str] = mapped_column(String, default="")
    mobile_phone: Mapped[str] = mapped_column(String, default="")
    role: Mapped[str] = mapped_column(String, default="")  # e.g. Buyer, Accounts, Marketing
    notes: Mapped[str] = mapped_column(String, default="")

    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    sort_order: Mapped[int] = mapped_column(Integer, default=0)
