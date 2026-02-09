from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, JSON
from app.core.db import Base
from app.models.base import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    full_name: Mapped[str] = mapped_column(String, default="")
    role: Mapped[str] = mapped_column(String, default="admin")  # admin/sales/production
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    menu_allow: Mapped[list] = mapped_column(JSON, default=list)  # list[str]
    menu_deny: Mapped[list] = mapped_column(JSON, default=list)   # list[str]