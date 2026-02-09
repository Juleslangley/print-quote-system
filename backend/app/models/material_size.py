from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, Boolean, Integer, ForeignKey
from app.core.db import Base
from app.models.base import TimestampMixin


class MaterialSize(Base, TimestampMixin):
    __tablename__ = "material_sizes"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    material_id: Mapped[str] = mapped_column(String, ForeignKey("materials.id"), index=True)
    label: Mapped[str] = mapped_column(String)
    width_mm: Mapped[float] = mapped_column(Float)
    height_mm: Mapped[float] = mapped_column(Float)
    cost_per_sheet_gbp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
