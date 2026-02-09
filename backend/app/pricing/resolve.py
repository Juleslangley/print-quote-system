from typing import Optional
from sqlalchemy.orm import Session
from app.models.pricing_rules import TemplatePricingRule, CustomerPricingRule
from app.models.margin_profile import MarginProfile
from app.models.quote import Quote
from app.models.customer import Customer
from app.models.template import ProductTemplate
from app.pricing.money import d


def resolve_customer_pricing_rule(db: Session, customer_id: str, category: str, template_id: str) -> Optional[CustomerPricingRule]:
    """
    Precedence:
      1) customer+template
      2) customer+category
      3) customer global
    """
    r = (
        db.query(CustomerPricingRule)
        .filter(CustomerPricingRule.customer_id == customer_id,
                CustomerPricingRule.template_id == template_id,
                CustomerPricingRule.active == True)
        .first()
    )
    if r:
        return r

    r = (
        db.query(CustomerPricingRule)
        .filter(CustomerPricingRule.customer_id == customer_id,
                CustomerPricingRule.template_id == None,
                CustomerPricingRule.category == category,
                CustomerPricingRule.active == True)
        .first()
    )
    if r:
        return r

    return (
        db.query(CustomerPricingRule)
        .filter(CustomerPricingRule.customer_id == customer_id,
                CustomerPricingRule.template_id == None,
                CustomerPricingRule.category == None,
                CustomerPricingRule.active == True)
        .first()
    )


def resolve_margin_profile_for_quote(
    db: Session,
    *,
    quote: Quote,
    customer: Customer,
    template: ProductTemplate,
    t_rule: Optional[TemplatePricingRule],
    c_rule: Optional[CustomerPricingRule],
):
    # precedence for profile id:
    # quote.margin_profile_id > customer rule > template rule > customer default
    profile_id = None
    if quote.margin_profile_id:
        profile_id = quote.margin_profile_id
    elif c_rule and c_rule.margin_profile_id:
        profile_id = c_rule.margin_profile_id
    elif t_rule and t_rule.margin_profile_id:
        profile_id = t_rule.margin_profile_id
    elif customer and customer.default_margin_profile_id:
        profile_id = customer.default_margin_profile_id

    profile = None
    if profile_id:
        profile = db.query(MarginProfile).filter(MarginProfile.id == profile_id, MarginProfile.active == True).first()

    # defaults
    target_margin = d(profile.target_margin_pct if profile else 0.40)
    min_margin = d(profile.min_margin_pct if profile else 0.25)
    min_sell = d(profile.min_sell_gbp if profile else 0.0)
    rounding = (profile.rounding if profile else {"mode": "NEAREST", "step": 0.01}) or {"mode": "NEAREST", "step": 0.01}

    # quote-level target margin override wins (apply last)
    if t_rule and t_rule.target_margin_pct is not None:
        target_margin = d(t_rule.target_margin_pct)
    if c_rule and c_rule.target_margin_pct is not None:
        target_margin = d(c_rule.target_margin_pct)
    if quote.target_margin_pct is not None:
        target_margin = d(quote.target_margin_pct)

    # min sell overrides (template then customer)
    if t_rule and t_rule.min_sell_gbp is not None:
        min_sell = d(t_rule.min_sell_gbp)
    if c_rule and c_rule.min_sell_gbp is not None:
        min_sell = d(c_rule.min_sell_gbp)

    # rounding override at quote level
    if quote.rounding_override and len(quote.rounding_override) > 0:
        rounding = quote.rounding_override

    # multipliers
    sell_multiplier = d(1.0)
    if t_rule:
        sell_multiplier *= d(t_rule.sell_multiplier or 1.0)
    if c_rule:
        sell_multiplier *= d(c_rule.sell_multiplier or 1.0)

    return {
        "profile_id": profile_id,
        "profile_name": (profile.name if profile else None),
        "target_margin": target_margin,
        "min_margin": min_margin,
        "min_sell": min_sell,
        "rounding": rounding,
        "sell_multiplier": sell_multiplier,
    }
