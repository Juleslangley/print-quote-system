from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.base import new_id
from app.models.pricing_rules import TemplatePricingRule, CustomerPricingRule
from app.schemas.pricing_rules import (
    TemplatePricingRuleCreate, TemplatePricingRuleUpdate, TemplatePricingRuleOut,
    CustomerPricingRuleCreate, CustomerPricingRuleUpdate, CustomerPricingRuleOut
)
from app.api.deps import require_admin, get_current_user

router = APIRouter()

# -------------------------
# Template pricing rules
# -------------------------

@router.get("/template-pricing-rules", response_model=list[TemplatePricingRuleOut])
def list_template_rules(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(TemplatePricingRule).all()

@router.get("/template-pricing-rules/{rule_id}", response_model=TemplatePricingRuleOut)
def get_template_rule(rule_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    r = db.query(TemplatePricingRule).filter(TemplatePricingRule.id == rule_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Template pricing rule not found")
    return r

@router.post("/template-pricing-rules", response_model=TemplatePricingRuleOut)
def create_template_rule(payload: TemplatePricingRuleCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    exists = db.query(TemplatePricingRule).filter(TemplatePricingRule.template_id == payload.template_id).first()
    if exists:
        raise HTTPException(status_code=409, detail="Template pricing rule already exists for this template")
    r = TemplatePricingRule(id=new_id(), **payload.model_dump())
    db.add(r); db.commit(); db.refresh(r)
    return r

@router.put("/template-pricing-rules/{rule_id}", response_model=TemplatePricingRuleOut)
def update_template_rule(rule_id: str, payload: TemplatePricingRuleUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    r = db.query(TemplatePricingRule).filter(TemplatePricingRule.id == rule_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Template pricing rule not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(r, k, v)
    db.add(r); db.commit(); db.refresh(r)
    return r

@router.delete("/template-pricing-rules/{rule_id}")
def delete_template_rule(rule_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    r = db.query(TemplatePricingRule).filter(TemplatePricingRule.id == rule_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Template pricing rule not found")
    db.delete(r); db.commit()
    return {"ok": True}

# -------------------------
# Customer pricing rules
# -------------------------

@router.get("/customer-pricing-rules", response_model=list[CustomerPricingRuleOut])
def list_customer_rules(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(CustomerPricingRule).all()

@router.get("/customers/{customer_id}/pricing-rules", response_model=list[CustomerPricingRuleOut])
def list_rules_for_customer(customer_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(CustomerPricingRule).filter(CustomerPricingRule.customer_id == customer_id).all()

@router.post("/customer-pricing-rules", response_model=CustomerPricingRuleOut)
def create_customer_rule(payload: CustomerPricingRuleCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    # Optional: prevent exact duplicates
    exists = (
        db.query(CustomerPricingRule)
        .filter(
            CustomerPricingRule.customer_id == payload.customer_id,
            CustomerPricingRule.category == payload.category,
            CustomerPricingRule.template_id == payload.template_id,
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="A pricing rule already exists for this customer scope (category/template)")
    r = CustomerPricingRule(id=new_id(), **payload.model_dump())
    db.add(r); db.commit(); db.refresh(r)
    return r

@router.put("/customer-pricing-rules/{rule_id}", response_model=CustomerPricingRuleOut)
def update_customer_rule(rule_id: str, payload: CustomerPricingRuleUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    r = db.query(CustomerPricingRule).filter(CustomerPricingRule.id == rule_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Customer pricing rule not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(r, k, v)
    db.add(r); db.commit(); db.refresh(r)
    return r

@router.delete("/customer-pricing-rules/{rule_id}")
def delete_customer_rule(rule_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    r = db.query(CustomerPricingRule).filter(CustomerPricingRule.id == rule_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Customer pricing rule not found")
    db.delete(r); db.commit()
    return {"ok": True}
