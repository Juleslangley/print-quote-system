from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, ForeignKey, Integer
from app.core.db import Base
from app.models.base import TimestampMixin


class CustomerContactMethod(Base, TimestampMixin):
    __tablename__ = "customer_contact_methods"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    contact_id: Mapped[str] = mapped_column(String, ForeignKey("customer_contacts.id"), index=True)

    kind: Mapped[str] = mapped_column(String)  # phone, email, whatsapp, other
    label: Mapped[str] = mapped_column(String, default="")  # Work, Mobile, Direct, Accounts, etc.
    value: Mapped[str] = mapped_column(String, default="")

    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    can_sms: Mapped[bool] = mapped_column(Boolean, default=False)
    can_whatsapp: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
