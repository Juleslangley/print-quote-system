from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, Integer, JSON
from app.core.db import Base
from app.models.base import TimestampMixin


class Machine(Base, TimestampMixin):
    __tablename__ = "machines"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True, unique=True)
    # DB column is "type" (NOT NULL); Python uses "category" for clarity
    category: Mapped[str] = mapped_column("type", String, index=True)  # printer_sheet | printer_roll | cutter | finisher
    process: Mapped[str] = mapped_column(String, default="")  # uv_flatbed | latex_roll | eco_roll | router | knife_cut etc
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(String, default="")
    config: Mapped[dict] = mapped_column(JSON, default=dict)  # DB legacy NOT NULL; use meta for capability data
    meta: Mapped[dict] = mapped_column(JSON, default=dict)  # capability config (max sheet size, roll width, etc.)