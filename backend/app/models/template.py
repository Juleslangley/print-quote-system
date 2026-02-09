from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, JSON
from app.core.db import Base
from app.models.base import TimestampMixin

class ProductTemplate(Base, TimestampMixin):
    __tablename__ = "product_templates"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    category: Mapped[str] = mapped_column(String)  # rigid/roll
    default_material_id: Mapped[str] = mapped_column(String)
    default_machine_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    rules: Mapped[dict] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
