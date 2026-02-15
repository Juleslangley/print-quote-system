from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean
from app.core.db import Base
from app.models.base import TimestampMixin


class Employer(Base, TimestampMixin):
    __tablename__ = "employers"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    contact_name: Mapped[str] = mapped_column(String, default="")
    email: Mapped[str] = mapped_column(String, default="")
    phone: Mapped[str] = mapped_column(String, default="")
    role: Mapped[str] = mapped_column(String, default="")
    notes: Mapped[str] = mapped_column(String, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
