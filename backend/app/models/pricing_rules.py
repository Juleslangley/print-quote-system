from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, Boolean, JSON, ForeignKey
from app.core.db import Base
from app.models.base import TimestampMixin

class TemplatePricingRule(Base, TimestampMixin):
    """
    Optional per-template commercial tweaks.

    Think:
    - fixed margin for that template
    - min charge higher than default
    - or a markup/discount factor
    """
    __tablename__ = "template_pricing_rules"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    template_id: Mapped[str] = mapped_column(String, ForeignKey("product_templates.id"), index=True, unique=True)

    # If set, overrides margin profile target_margin_pct for this template
    target_margin_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_sell_gbp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # multiplier on final sell (e.g. 1.10 for +10%, 0.95 for -5%)
    sell_multiplier: Mapped[float] = mapped_column(Float, default=1.0)

    # If set, force a margin profile for this template
    margin_profile_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("margin_profiles.id"), nullable=True)

    active: Mapped[bool] = mapped_column(Boolean, default=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)


class CustomerPricingRule(Base, TimestampMixin):
    """
    Customer overrides.

    Applies at:
      - customer global
      - customer+category (rigid/roll)
      - customer+template

    Precedence:
      template-specific > category > global
    """
    __tablename__ = "customer_pricing_rules"

    id: Mapped[str] = mapped_column(String, primary_key=True)

    customer_id: Mapped[str] = mapped_column(String, ForeignKey("customers.id"), index=True)

    # Scoping
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # rigid/roll or None
    template_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("product_templates.id"), nullable=True)

    # Commercial knobs
    margin_profile_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("margin_profiles.id"), nullable=True)
    target_margin_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_sell_gbp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sell_multiplier: Mapped[float] = mapped_column(Float, default=1.0)

    active: Mapped[bool] = mapped_column(Boolean, default=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
