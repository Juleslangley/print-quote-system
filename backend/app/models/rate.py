from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, Boolean, JSON
from app.core.db import Base
from app.models.base import TimestampMixin

class Rate(Base, TimestampMixin):
    __tablename__ = "rates"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    rate_type: Mapped[str] = mapped_column(String, index=True)  # print_flatbed/print_roll/cut_knife/cut_router/laminate/pack
    setup_minutes: Mapped[float] = mapped_column(Float, default=10.0)
    hourly_cost_gbp: Mapped[float] = mapped_column(Float, default=35.0)
    run_speed: Mapped[dict] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
