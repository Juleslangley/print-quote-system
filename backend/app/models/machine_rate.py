from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, Integer, Float, ForeignKey
from app.core.db import Base
from app.models.base import TimestampMixin


class MachineRate(Base, TimestampMixin):
    __tablename__ = "machine_rates"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    machine_id: Mapped[str] = mapped_column(String, ForeignKey("machines.id"), index=True)
    operation_key: Mapped[str] = mapped_column(String)  # e.g. print_uv, print_roll, cut_zund
    unit: Mapped[str] = mapped_column(String)  # sqm | lm | hour | sheet | job
    cost_per_unit_gbp: Mapped[float] = mapped_column(Float, default=0.0)
    setup_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    setup_cost_gbp: Mapped[float] = mapped_column(Float, default=0.0)
    min_charge_gbp: Mapped[float] = mapped_column(Float, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(String, default="")
