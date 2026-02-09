from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, Boolean, JSON
from app.core.db import Base
from app.models.base import TimestampMixin

class MarginProfile(Base, TimestampMixin):
    """
    Commercial policy container.

    rounding examples:
      {"mode":"NEAREST", "step":0.05}           -> nearest 5p
      {"mode":"UP", "step":1.00}               -> round UP to whole pounds
      {"mode":"PSYCH_99"}                      -> 19.99 / 24.99 style
      {"mode":"NONE"}                          -> no rounding (still 2dp)
    """
    __tablename__ = "margin_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)

    # Margin targets
    target_margin_pct: Mapped[float] = mapped_column(Float, default=0.40)  # used if no sell provided
    min_margin_pct: Mapped[float] = mapped_column(Float, default=0.25)     # enforce floor

    # Minimum sell charge per line (not quote) – v1
    min_sell_gbp: Mapped[float] = mapped_column(Float, default=0.0)

    # Optional max discount control later; keep in config
    rounding: Mapped[dict] = mapped_column(JSON, default=lambda: {"mode": "NEAREST", "step": 0.01})

    active: Mapped[bool] = mapped_column(Boolean, default=True)
