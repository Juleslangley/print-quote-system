import os
from pathlib import Path

FILES = {}

def add(path: str, content: str):
    FILES[path] = content.lstrip("\n")

# -----------------------------
# Root
# -----------------------------
add("README.md", r"""
# Print Quote System (Nyala + HP Roll + Zünd) — Starter Repo

## Run
1) Copy env:
   cp .env.example .env

2) Start:
   docker compose up --build

Backend docs:
- http://localhost:8000/docs

Frontend:
- http://localhost:3000

## Seed dev data
POST http://localhost:8000/api/seed/dev

Creates:
- admin user: admin@local / admin123
- demo customer
- 2 materials
- rates
- 2 templates

## Quick test flow
1) Seed: POST /api/seed/dev
2) Login: POST /api/auth/login  -> token
3) List customers: GET /api/customers (auth)
4) Create quote: POST /api/quotes (auth)
5) Add item: POST /api/quotes/{id}/items (auth)
""")

add(".env.example", r"""
POSTGRES_USER=quote
POSTGRES_PASSWORD=quote
POSTGRES_DB=quote

DATABASE_URL=postgresql+psycopg://quote:quote@db:5432/quote
JWT_SECRET=change_me_super_secret
PRICING_VERSION=v1.0.0
""")

add("docker-compose.yml", r"""
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  backend:
    build: ./backend
    environment:
      DATABASE_URL: ${DATABASE_URL}
      JWT_SECRET: ${JWT_SECRET}
      PRICING_VERSION: ${PRICING_VERSION}
    ports:
      - "8000:8000"
    depends_on:
      - db

  frontend:
    build: ./frontend
    environment:
      NEXT_PUBLIC_API_BASE: http://localhost:8000
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  pgdata:
""")

# -----------------------------
# Backend
# -----------------------------
add("backend/Dockerfile", r"""
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir -U pip

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
""")

add("backend/requirements.txt", r"""
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.34
psycopg[binary]==3.2.1
pydantic==2.9.2
pydantic-settings==2.5.2
python-jose==3.3.0
passlib[bcrypt]==1.7.4
""")

add("backend/app/__init__.py", r"")

add("backend/app/main.py", r"""
from fastapi import FastAPI
from app.core.db import Base, engine
from app.api import auth, customers, materials, rates, templates, quotes, seed

app = FastAPI(title="Print Quote System", version="0.1.0")

# Starter: auto-create tables. For production, move to Alembic migrations.
Base.metadata.create_all(bind=engine)

app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(seed.router, prefix="/api", tags=["seed"])
app.include_router(customers.router, prefix="/api", tags=["customers"])
app.include_router(materials.router, prefix="/api", tags=["materials"])
app.include_router(rates.router, prefix="/api", tags=["rates"])
app.include_router(templates.router, prefix="/api", tags=["templates"])
app.include_router(quotes.router, prefix="/api", tags=["quotes"])
""")

# core
add("backend/app/core/__init__.py", r"")

add("backend/app/core/config.py", r"""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str = "dev"
    PRICING_VERSION: str = "v1.0.0"

settings = Settings()
""")

add("backend/app/core/db.py", r"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
""")

add("backend/app/core/security.py", r"""
from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)

def create_access_token(subject: str, minutes: int = 60 * 24) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=minutes)
    payload = {"sub": subject, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
""")

# models
add("backend/app/models/__init__.py", r"")

add("backend/app/models/base.py", r"""
import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, func

def new_id() -> str:
    return str(uuid.uuid4())

class TimestampMixin:
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
""")

add("backend/app/models/user.py", r"""
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from app.core.db import Base
from app.models.base import TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="admin")  # admin/sales/production
""")

add("backend/app/models/customer.py", r"""
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from app.core.db import Base
from app.models.base import TimestampMixin

class Customer(Base, TimestampMixin):
    __tablename__ = "customers"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    email: Mapped[str] = mapped_column(String, default="")
""")

add("backend/app/models/material.py", r"""
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, Boolean
from app.core.db import Base
from app.models.base import TimestampMixin

class Material(Base, TimestampMixin):
    __tablename__ = "materials"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    type: Mapped[str] = mapped_column(String)  # sheet/roll
    supplier: Mapped[str] = mapped_column(String, default="")

    # sheet fields
    cost_per_sheet_gbp: Mapped[float | None] = mapped_column(Float, nullable=True)
    sheet_width_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    sheet_height_mm: Mapped[float | None] = mapped_column(Float, nullable=True)

    # roll fields
    cost_per_lm_gbp: Mapped[float | None] = mapped_column(Float, nullable=True)
    roll_width_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_billable_lm: Mapped[float | None] = mapped_column(Float, nullable=True)

    waste_pct_default: Mapped[float] = mapped_column(Float, default=0.05)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
""")

add("backend/app/models/rate.py", r"""
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
    run_speed: Mapped[dict] = mapped_column(JSON, default={})
    active: Mapped[bool] = mapped_column(Boolean, default=True)
""")

add("backend/app/models/template.py", r"""
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
    rules: Mapped[dict] = mapped_column(JSON, default={})
    active: Mapped[bool] = mapped_column(Boolean, default=True)
""")

add("backend/app/models/quote.py", r"""
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, ForeignKey, JSON
from app.core.db import Base
from app.models.base import TimestampMixin

class Quote(Base, TimestampMixin):
    __tablename__ = "quotes"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    quote_number: Mapped[str] = mapped_column(String, unique=True, index=True)
    customer_id: Mapped[str] = mapped_column(String, ForeignKey("customers.id"))
    status: Mapped[str] = mapped_column(String, default="draft")
    pricing_version: Mapped[str] = mapped_column(String)
    notes_internal: Mapped[str] = mapped_column(String, default="")
    subtotal_sell: Mapped[float] = mapped_column(Float, default=0.0)
    vat: Mapped[float] = mapped_column(Float, default=0.0)
    total_sell: Mapped[float] = mapped_column(Float, default=0.0)

class QuoteItem(Base, TimestampMixin):
    __tablename__ = "quote_items"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    quote_id: Mapped[str] = mapped_column(String, ForeignKey("quotes.id"))
    template_id: Mapped[str] = mapped_column(String, ForeignKey("product_templates.id"))
    title: Mapped[str] = mapped_column(String)
    qty: Mapped[int] = mapped_column(default=1)
    width_mm: Mapped[float] = mapped_column(Float)
    height_mm: Mapped[float] = mapped_column(Float)
    sides: Mapped[int] = mapped_column(default=1)
    options: Mapped[dict] = mapped_column(JSON, default={})
    cost_total: Mapped[float] = mapped_column(Float, default=0.0)
    sell_total: Mapped[float] = mapped_column(Float, default=0.0)
    margin_pct: Mapped[float] = mapped_column(Float, default=0.0)
    calc_snapshot: Mapped[dict] = mapped_column(JSON, default={})
""")

# schemas
add("backend/app/schemas/__init__.py", r"")

add("backend/app/schemas/auth.py", r"""
from pydantic import BaseModel, EmailStr

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
""")

add("backend/app/schemas/customer.py", r"""
from pydantic import BaseModel

class CustomerCreate(BaseModel):
    name: str
    email: str = ""

class CustomerOut(BaseModel):
    id: str
    name: str
    email: str
    class Config:
        from_attributes = True
""")

add("backend/app/schemas/material.py", r"""
from pydantic import BaseModel

class MaterialCreate(BaseModel):
    name: str
    type: str  # sheet/roll
    supplier: str = ""
    cost_per_sheet_gbp: float | None = None
    sheet_width_mm: float | None = None
    sheet_height_mm: float | None = None
    cost_per_lm_gbp: float | None = None
    roll_width_mm: float | None = None
    min_billable_lm: float | None = None
    waste_pct_default: float = 0.05

class MaterialOut(BaseModel):
    id: str
    name: str
    type: str
    supplier: str
    cost_per_sheet_gbp: float | None
    sheet_width_mm: float | None
    sheet_height_mm: float | None
    cost_per_lm_gbp: float | None
    roll_width_mm: float | None
    min_billable_lm: float | None
    waste_pct_default: float
    class Config:
        from_attributes = True
""")

add("backend/app/schemas/rate.py", r"""
from pydantic import BaseModel

class RateCreate(BaseModel):
    rate_type: str
    setup_minutes: float = 10.0
    hourly_cost_gbp: float = 35.0
    run_speed: dict = {}

class RateOut(BaseModel):
    id: str
    rate_type: str
    setup_minutes: float
    hourly_cost_gbp: float
    run_speed: dict
    class Config:
        from_attributes = True
""")

add("backend/app/schemas/template.py", r"""
from pydantic import BaseModel

class TemplateCreate(BaseModel):
    name: str
    category: str  # rigid/roll
    default_material_id: str
    rules: dict = {}

class TemplateOut(BaseModel):
    id: str
    name: str
    category: str
    default_material_id: str
    rules: dict
    class Config:
        from_attributes = True
""")

add("backend/app/schemas/quote.py", r"""
from pydantic import BaseModel

class QuoteCreate(BaseModel):
    customer_id: str
    notes_internal: str = ""

class QuoteOut(BaseModel):
    id: str
    quote_number: str
    customer_id: str
    status: str
    pricing_version: str
    notes_internal: str
    subtotal_sell: float
    vat: float
    total_sell: float
    class Config:
        from_attributes = True

class QuoteItemCreate(BaseModel):
    template_id: str
    title: str
    qty: int
    width_mm: float
    height_mm: float
    sides: int = 1
    options: dict = {}

class QuoteItemOut(BaseModel):
    id: str
    quote_id: str
    template_id: str
    title: str
    qty: int
    width_mm: float
    height_mm: float
    sides: int
    options: dict
    cost_total: float
    sell_total: float
    margin_pct: float
    calc_snapshot: dict
    class Config:
        from_attributes = True
""")

# pricing
add("backend/app/pricing/__init__.py", r"")

add("backend/app/pricing/money.py", r"""
from decimal import Decimal, ROUND_HALF_UP

def d(x) -> Decimal:
    return Decimal(str(x))

def money(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
""")

add("backend/app/pricing/finishing.py", r"""
from __future__ import annotations
from decimal import Decimal
from app.pricing.money import d, money

def perimeter_m(width_mm: Decimal, height_mm: Decimal) -> Decimal:
    return (d(2) * (width_mm + height_mm)) / d(1000)

def finish_cost_block(block: dict, *, width_mm: Decimal, height_mm: Decimal, print_sqm: Decimal, qty: int, rates_by_type: dict) -> dict:
    btype = block["type"]
    rate_type = block.get("rate_type")
    params = block.get("params", {}) or {}

    rate = rates_by_type.get(rate_type)
    if not rate:
        return {"name": btype, "minutes": d(0), "cost": d(0), "meta": {"warning": f"Missing rate {rate_type}"}}

    setup_min = d(rate["setup_minutes"])
    hourly = d(rate["hourly_cost_gbp"])
    run_speed = rate.get("run_speed", {}) or {}

    per_m = perimeter_m(width_mm, height_mm)
    run_min = d(0)
    consumable = d(0)

    if btype == "CUT_STRAIGHT":
        m_per_min = d(run_speed.get("m_per_min", {}).get("straight", 6))
        run_min = per_m / m_per_min
    elif btype == "CUT_CONTOUR":
        m_per_min = d(run_speed.get("m_per_min", {}).get("contour", 2))
        run_min = per_m / m_per_min
        weed = params.get("weed_min_per_sqm")
        if weed is not None:
            run_min += d(weed) * print_sqm
    elif btype == "ROUTER_CUT":
        m_per_min = d(run_speed.get("router_m_per_min", 1.2))
        run_min = per_m / m_per_min
    elif btype == "LAMINATE_ROLL":
        lam_cost_per_sqm = d(params.get("lam_cost_per_sqm", 1.10))
        consumable = lam_cost_per_sqm * print_sqm
        sqm_per_hr = d(run_speed.get("sqm_per_hour", 30))
        run_min = (print_sqm / sqm_per_hr) * d(60)
    elif btype == "PACK_STANDARD":
        minutes_per_item = d(params.get("minutes_per_item", 0.5))
        run_min = minutes_per_item * d(qty)
    else:
        return {"name": btype, "minutes": d(0), "cost": d(0), "meta": {"warning": f"Unknown finish type {btype}"}}

    total_min = setup_min + run_min
    labour = (total_min / d(60)) * hourly
    cost = money(labour + consumable)
    return {"name": btype, "minutes": total_min, "cost": cost, "meta": {"perimeter_m": str(per_m), "consumable": str(consumable), "rate_type": rate_type}}
""")

add("backend/app/pricing/engine.py", r"""
from __future__ import annotations
from decimal import Decimal
from app.pricing.money import d, money
from app.pricing.finishing import finish_cost_block

def sqm(width_mm: Decimal, height_mm: Decimal) -> Decimal:
    return (width_mm * height_mm) / d(1_000_000)

def ceil_div(a: int, b: int) -> int:
    return (a + b - 1) // b

def calculate_item(*, template: dict, material: dict, rates_by_type: dict, item_input: dict) -> dict:
    qty = int(item_input["qty"])
    width_mm = d(item_input["width_mm"])
    height_mm = d(item_input["height_mm"])
    sides = int(item_input.get("sides", 1))
    options = item_input.get("options", {}) or {}

    rules = template.get("rules", {}) or {}
    category = template["category"]

    bleed_mm = d(rules.get("bleed_mm", 3))
    width_b = width_mm + bleed_mm * d(2)
    height_b = height_mm + bleed_mm * d(2)

    coverage = (options.get("coverage_class") or rules.get("coverage_class") or "medium").lower()
    ink_map = rules.get("ink_allowance_per_sqm_gbp", {"light": 0.60, "medium": 0.90, "heavy": 1.20})
    ink_allow = d(ink_map.get(coverage, ink_map.get("medium", 0.90)))

    waste_pct = d(options.get("waste_pct") if "waste_pct" in options else rules.get("waste_pct", material.get("waste_pct_default", 0.05)))
    print_mode = options.get("print_mode") or rules.get("print_mode") or "standard"
    white = bool(options.get("white", False))

    finish_blocks = rules.get("finish_blocks", []) or []
    snapshot: dict = {
        "inputs": {"qty": qty, "width_mm": str(width_mm), "height_mm": str(height_mm), "sides": sides, "bleed_mm": str(bleed_mm)},
        "category": category,
        "coverage_class": coverage,
        "print_mode": print_mode,
        "white": white,
    }

    material_cost = d(0)
    ink_cost = d(0)
    print_labour = d(0)

    if category == "rigid":
        sheet_w = d(material["sheet_width_mm"])
        sheet_h = d(material["sheet_height_mm"])
        cost_per_sheet = d(material["cost_per_sheet_gbp"])

        gutter = d(rules.get("gutter_mm", 10))
        fit_x = int((sheet_w + gutter) // (width_b + gutter))
        fit_y = int((sheet_h + gutter) // (height_b + gutter))
        items_per_sheet = fit_x * fit_y
        if items_per_sheet <= 0:
            raise ValueError("Item too large for selected sheet")

        base_sheets = ceil_div(qty, items_per_sheet)
        setup_waste_sheets = int(rules.get("setup_waste_sheets", 1))
        waste_sheets = setup_waste_sheets + int((d(base_sheets) * waste_pct).to_integral_value())
        total_sheets = base_sheets + waste_sheets

        material_cost = money(d(total_sheets) * cost_per_sheet)

        print_sqm = sqm(width_b, height_b) * d(qty) * d(sides)
        ink_cost = money(print_sqm * ink_allow)

        rate = rates_by_type.get("print_flatbed")
        if not rate:
            raise ValueError("Missing rate print_flatbed")

        setup_min = d(rate["setup_minutes"])
        hourly = d(rate["hourly_cost_gbp"])
        sqm_per_hr = d((rate.get("run_speed", {}).get("sqm_per_hour", {}) or {}).get(print_mode, 35))
        white_mult = d((rate.get("run_speed", {}) or {}).get("white_multiplier", 1.35))

        if white:
            ink_cost = money(d(ink_cost) * white_mult)

        run_hours = print_sqm / sqm_per_hr
        print_labour = money((setup_min / d(60)) * hourly + run_hours * hourly)

        snapshot["rigid"] = {
            "sheet_w_mm": str(sheet_w),
            "sheet_h_mm": str(sheet_h),
            "items_per_sheet": items_per_sheet,
            "base_sheets": base_sheets,
            "waste_sheets": waste_sheets,
            "total_sheets": total_sheets,
            "print_sqm": str(print_sqm),
        }

    elif category == "roll":
        roll_w = d(material["roll_width_mm"])
        cost_per_lm = d(material["cost_per_lm_gbp"])
        min_bill = d(material.get("min_billable_lm") or 0)

        setup_waste_lm = d(rules.get("setup_waste_lm", 1.0))

        fits_a = width_b <= roll_w
        lm_a = (height_b / d(1000)) * d(qty)
        fits_b = height_b <= roll_w
        lm_b = (width_b / d(1000)) * d(qty)

        if not (fits_a or fits_b):
            raise ValueError("Item too large for selected roll width")

        if fits_a and (not fits_b or lm_a <= lm_b):
            chosen = "A"
            lm_total = lm_a
        else:
            chosen = "B"
            lm_total = lm_b

        lm_total = lm_total + setup_waste_lm
        lm_total = lm_total * (d(1) + waste_pct)

        if lm_total < min_bill:
            lm_total = min_bill

        material_cost = money(lm_total * cost_per_lm)

        print_sqm = sqm(width_b, height_b) * d(qty) * d(sides)
        ink_cost = money(print_sqm * ink_allow)

        rate = rates_by_type.get("print_roll")
        if not rate:
            raise ValueError("Missing rate print_roll")

        setup_min = d(rate["setup_minutes"])
        hourly = d(rate["hourly_cost_gbp"])
        sqm_per_hr = d((rate.get("run_speed", {}).get("sqm_per_hour", {}) or {}).get(print_mode, 25))

        run_hours = print_sqm / sqm_per_hr
        print_labour = money((setup_min / d(60)) * hourly + run_hours * hourly)

        snapshot["roll"] = {
            "roll_width_mm": str(roll_w),
            "orientation": chosen,
            "lm_total": str(lm_total),
            "print_sqm": str(print_sqm),
        }
    else:
        raise ValueError(f"Unknown category {category}")

    # finishing
    finish_costs = []
    finish_total = d(0)
    print_sqm_val = d(snapshot[category]["print_sqm"])

    for block in finish_blocks:
        res = finish_cost_block(
            block,
            width_mm=width_b,
            height_mm=height_b,
            print_sqm=print_sqm_val,
            qty=qty,
            rates_by_type=rates_by_type,
        )
        finish_costs.append({
            "name": res["name"],
            "minutes": str(res["minutes"]),
            "cost": float(res["cost"]),
            "meta": res["meta"],
        })
        finish_total += d(res["cost"])

    cost_total = money(d(material_cost) + d(ink_cost) + d(print_labour) + money(finish_total))

    # v1 selling rule: target margin fixed per template (default 40%)
    target_margin = d(rules.get("target_margin_pct", 0.40))
    sell_total = money(cost_total / (d(1) - target_margin))
    margin_pct = d(0) if sell_total == 0 else (sell_total - cost_total) / sell_total

    snapshot["costs"] = {
        "material_cost": float(material_cost),
        "ink_cost": float(ink_cost),
        "print_labour_cost": float(print_labour),
        "finish_costs": finish_costs,
        "finish_total": float(money(finish_total)),
        "cost_total": float(cost_total),
        "target_margin_pct": float(target_margin),
        "sell_total": float(sell_total),
        "margin_pct": float(margin_pct),
    }

    return {"cost_total": float(cost_total), "sell_total": float(sell_total), "margin_pct": float(margin_pct), "snapshot": snapshot}
""")

# API
add("backend/app/api/__init__.py", r"""
from . import auth, customers, materials, rates, templates, quotes, seed
""")

add("backend/app/api/deps.py", r"""
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import decode_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("missing sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user
""")

add("backend/app/api/auth.py", r"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import verify_password, create_access_token
from app.schemas.auth import LoginIn, TokenOut
from app.models.user import User

router = APIRouter()

@router.post("/auth/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user.id)
    return TokenOut(access_token=token)
""")

add("backend/app/api/seed.py", r"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import hash_password
from app.models.base import new_id
from app.models.user import User
from app.models.material import Material
from app.models.rate import Rate
from app.models.template import ProductTemplate
from app.models.customer import Customer

router = APIRouter()

@router.post("/seed/dev")
def seed_dev(db: Session = Depends(get_db)):
    # admin user
    if db.query(User).count() == 0:
        db.add(User(
            id=new_id(),
            email="admin@local",
            password_hash=hash_password("admin123"),
            role="admin",
        ))

    # customer
    if db.query(Customer).count() == 0:
        db.add(Customer(id=new_id(), name="Demo Customer", email="demo@customer.local"))

    # materials
    if db.query(Material).count() == 0:
        foamex = Material(
            id=new_id(),
            name="3mm Foamex 1220x2440",
            type="sheet",
            supplier="Generic",
            cost_per_sheet_gbp=18.00,
            sheet_width_mm=1220,
            sheet_height_mm=2440,
            waste_pct_default=0.05,
        )
        vinyl = Material(
            id=new_id(),
            name="Monomeric Vinyl 1370",
            type="roll",
            supplier="Generic",
            cost_per_lm_gbp=2.20,
            roll_width_mm=1370,
            min_billable_lm=2.0,
            waste_pct_default=0.07,
        )
        db.add_all([foamex, vinyl])
        db.flush()

        # rates
        db.add_all([
            Rate(id=new_id(), rate_type="print_flatbed", setup_minutes=15, hourly_cost_gbp=45,
                 run_speed={"sqm_per_hour":{"standard":45,"fine":25},"white_multiplier":1.35}),
            Rate(id=new_id(), rate_type="print_roll", setup_minutes=10, hourly_cost_gbp=40,
                 run_speed={"sqm_per_hour":{"standard":25,"fine":15}}),
            Rate(id=new_id(), rate_type="cut_knife", setup_minutes=5, hourly_cost_gbp=35,
                 run_speed={"m_per_min":{"straight":6,"contour":2}}),
            Rate(id=new_id(), rate_type="cut_router", setup_minutes=10, hourly_cost_gbp=55,
                 run_speed={"router_m_per_min":1.2}),
            Rate(id=new_id(), rate_type="laminate", setup_minutes=10, hourly_cost_gbp=35,
                 run_speed={"sqm_per_hour":30}),
            Rate(id=new_id(), rate_type="pack", setup_minutes=0, hourly_cost_gbp=28, run_speed={}),
        ])
        db.flush()

        # templates
        db.add_all([
            ProductTemplate(
                id=new_id(),
                name="3mm Foamex Board (Nyala)",
                category="rigid",
                default_material_id=foamex.id,
                rules={
                    "bleed_mm": 3,
                    "gutter_mm": 10,
                    "setup_waste_sheets": 1,
                    "waste_pct": 0.05,
                    "coverage_class": "medium",
                    "print_mode": "standard",
                    "ink_allowance_per_sqm_gbp": {"light":0.60,"medium":0.90,"heavy":1.20},
                    "target_margin_pct": 0.40,
                    "finish_blocks": [
                        {"type":"CUT_STRAIGHT","rate_type":"cut_knife"},
                        {"type":"PACK_STANDARD","rate_type":"pack","params":{"minutes_per_item":0.5}}
                    ]
                },
            ),
            ProductTemplate(
                id=new_id(),
                name="Window Vinyl Contour Cut (HP + Zünd)",
                category="roll",
                default_material_id=vinyl.id,
                rules={
                    "bleed_mm": 3,
                    "setup_waste_lm": 1.0,
                    "waste_pct": 0.07,
                    "coverage_class": "heavy",
                    "print_mode": "standard",
                    "ink_allowance_per_sqm_gbp": {"light":0.60,"medium":0.90,"heavy":1.20},
                    "target_margin_pct": 0.45,
                    "finish_blocks": [
                        {"type":"LAMINATE_ROLL","rate_type":"laminate","params":{"lam_cost_per_sqm":1.10}},
                        {"type":"CUT_CONTOUR","rate_type":"cut_knife","params":{"weed_min_per_sqm":6}},
                        {"type":"PACK_STANDARD","rate_type":"pack","params":{"minutes_per_item":0.7}}
                    ]
                },
            )
        ])

    db.commit()
    return {"ok": True, "admin": {"email": "admin@local", "password": "admin123"}}
""")

add("backend/app/api/customers.py", r"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.customer import Customer
from app.models.base import new_id
from app.schemas.customer import CustomerCreate, CustomerOut
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/customers", response_model=list[CustomerOut])
def list_customers(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(Customer).order_by(Customer.name.asc()).all()

@router.post("/customers", response_model=CustomerOut)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    c = Customer(id=new_id(), name=payload.name, email=payload.email)
    db.add(c); db.commit(); db.refresh(c)
    return c
""")

add("backend/app/api/materials.py", r"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.material import Material
from app.models.base import new_id
from app.schemas.material import MaterialCreate, MaterialOut
from app.api.deps import require_admin

router = APIRouter()

@router.get("/materials", response_model=list[MaterialOut])
def list_materials(db: Session = Depends(get_db), _=Depends(require_admin)):
    return db.query(Material).order_by(Material.name.asc()).all()

@router.post("/materials", response_model=MaterialOut)
def create_material(payload: MaterialCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    m = Material(id=new_id(), **payload.model_dump())
    db.add(m); db.commit(); db.refresh(m)
    return m
""")

add("backend/app/api/rates.py", r"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.rate import Rate
from app.models.base import new_id
from app.schemas.rate import RateCreate, RateOut
from app.api.deps import require_admin

router = APIRouter()

@router.get("/rates", response_model=list[RateOut])
def list_rates(db: Session = Depends(get_db), _=Depends(require_admin)):
    return db.query(Rate).order_by(Rate.rate_type.asc()).all()

@router.post("/rates", response_model=RateOut)
def create_rate(payload: RateCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    r = Rate(id=new_id(), **payload.model_dump())
    db.add(r); db.commit(); db.refresh(r)
    return r
""")

add("backend/app/api/templates.py", r"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.template import ProductTemplate
from app.models.base import new_id
from app.schemas.template import TemplateCreate, TemplateOut
from app.api.deps import require_admin, get_current_user

router = APIRouter()

@router.get("/templates", response_model=list[TemplateOut])
def list_templates(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(ProductTemplate).order_by(ProductTemplate.name.asc()).all()

@router.post("/templates", response_model=TemplateOut)
def create_template(payload: TemplateCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    t = ProductTemplate(id=new_id(), **payload.model_dump())
    db.add(t); db.commit(); db.refresh(t)
    return t
""")

add("backend/app/api/quotes.py", r"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.config import settings
from app.models.base import new_id
from app.models.quote import Quote, QuoteItem
from app.models.customer import Customer
from app.models.template import ProductTemplate
from app.models.material import Material
from app.models.rate import Rate
from app.schemas.quote import QuoteCreate, QuoteOut, QuoteItemCreate, QuoteItemOut
from app.api.deps import get_current_user
from app.pricing.engine import calculate_item

router = APIRouter()

def next_quote_number() -> str:
    import time
    return f"Q{int(time.time())}"

@router.post("/quotes", response_model=QuoteOut)
def create_quote(payload: QuoteCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    cust = db.query(Customer).filter(Customer.id == payload.customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")

    q = Quote(
        id=new_id(),
        quote_number=next_quote_number(),
        customer_id=payload.customer_id,
        status="draft",
        pricing_version=settings.PRICING_VERSION,
        notes_internal=payload.notes_internal,
        subtotal_sell=0.0,
        vat=0.0,
        total_sell=0.0,
    )
    db.add(q); db.commit(); db.refresh(q)
    return q

@router.get("/quotes/{quote_id}", response_model=QuoteOut)
def get_quote(quote_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(Quote).filter(Quote.id == quote_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")
    return q

@router.get("/quotes/{quote_id}/items", response_model=list[QuoteItemOut])
def list_items(quote_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(QuoteItem).filter(QuoteItem.quote_id == quote_id).all()

@router.post("/quotes/{quote_id}/items", response_model=QuoteItemOut)
def add_item(quote_id: str, payload: QuoteItemCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(Quote).filter(Quote.id == quote_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")

    t = db.query(ProductTemplate).filter(ProductTemplate.id == payload.template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")

    m = db.query(Material).filter(Material.id == t.default_material_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Default material missing for template")

    rates = db.query(Rate).all()
    rates_by_type = {
        r.rate_type: {"setup_minutes": r.setup_minutes, "hourly_cost_gbp": r.hourly_cost_gbp, "run_speed": r.run_speed}
        for r in rates
    }

    calc = calculate_item(
        template={"category": t.category, "rules": t.rules},
        material={
            "type": m.type,
            "waste_pct_default": m.waste_pct_default,
            "cost_per_sheet_gbp": m.cost_per_sheet_gbp,
            "sheet_width_mm": m.sheet_width_mm,
            "sheet_height_mm": m.sheet_height_mm,
            "cost_per_lm_gbp": m.cost_per_lm_gbp,
            "roll_width_mm": m.roll_width_mm,
            "min_billable_lm": m.min_billable_lm,
        },
        rates_by_type=rates_by_type,
        item_input=payload.model_dump(),
    )

    item = QuoteItem(
        id=new_id(),
        quote_id=q.id,
        template_id=t.id,
        title=payload.title,
        qty=payload.qty,
        width_mm=payload.width_mm,
        height_mm=payload.height_mm,
        sides=payload.sides,
        options=payload.options,
        cost_total=calc["cost_total"],
        sell_total=calc["sell_total"],
        margin_pct=calc["margin_pct"],
        calc_snapshot=calc["snapshot"],
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    # Update quote totals
    items = db.query(QuoteItem).filter(QuoteItem.quote_id == q.id).all()
    subtotal = sum(i.sell_total for i in items)
    q.subtotal_sell = round(subtotal, 2)
    q.vat = round(q.subtotal_sell * 0.20, 2)
    q.total_sell = round(q.subtotal_sell + q.vat, 2)
    db.add(q); db.commit()

    return item
""")

# -----------------------------
# Frontend (minimal Next.js)
# -----------------------------
add("frontend/Dockerfile", r"""
FROM node:20-alpine
WORKDIR /app
COPY package.json /app/package.json
RUN npm install
COPY . /app
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "-H", "0.0.0.0", "-p", "3000"]
""")

add("frontend/package.json", r"""
{
  "name": "print-quote-frontend",
  "private": true,
  "version": "0.1.0",
  "scripts": {
    "dev": "next dev"
  },
  "dependencies": {
    "next": "14.2.6",
    "react": "18.3.1",
    "react-dom": "18.3.1"
  }
}
""")

add("frontend/next.config.js", r"""
/** @type {import('next').NextConfig} */
const nextConfig = {};
module.exports = nextConfig;
""")

add("frontend/lib/api.ts", r"""
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export async function api(path: string, opts: RequestInit = {}) {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers: any = { "Content-Type": "application/json", ...(opts.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
""")

add("frontend/app/layout.tsx", r"""
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui", margin: 20 }}>{children}</body>
    </html>
  );
}
""")

add("frontend/app/page.tsx", r"""
"use client";

import { useState } from "react";
import { api } from "../lib/api";

export default function Home() {
  const [email, setEmail] = useState("admin@local");
  const [password, setPassword] = useState("admin123");
  const [msg, setMsg] = useState("");

  async function seed() {
    const base = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
    const res = await fetch(`${base}/api/seed/dev`, { method: "POST" });
    setMsg("Seed: " + (await res.text()));
  }

  async function login() {
    const out = await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem("token", out.access_token);
    setMsg("Logged in.");
  }

  return (
    <div>
      <h1>Print Quote System</h1>

      <button onClick={seed}>Seed Dev Data</button>

      <h2>Login</h2>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email" />
        <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="password" type="password" />
        <button onClick={login}>Login</button>
      </div>

      <p style={{ whiteSpace: "pre-wrap" }}>{msg}</p>

      <p>
        Go to <a href="/quotes">Quotes</a>
      </p>
    </div>
  );
}
""")

add("frontend/app/quotes/page.tsx", r"""
"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";

export default function Quotes() {
  const [customers, setCustomers] = useState<any[]>([]);
  const [quoteId, setQuoteId] = useState<string>("");

  useEffect(() => {
    (async () => {
      try {
        const c = await api("/api/customers");
        setCustomers(c);
      } catch {
        // not logged in yet
      }
    })();
  }, []);

  async function createQuote(customer_id: string) {
    const q = await api("/api/quotes", { method: "POST", body: JSON.stringify({ customer_id }) });
    setQuoteId(q.id);
  }

  return (
    <div>
      <h1>Quotes</h1>
      <p>Select a customer to create a quote.</p>

      <ul>
        {customers.map((c) => (
          <li key={c.id}>
            {c.name} <button onClick={() => createQuote(c.id)}>Create Quote</button>
          </li>
        ))}
      </ul>

      {quoteId && (
        <p>
          Created quote: <a href={`/quotes/${quoteId}`}>{quoteId}</a>
        </p>
      )}
    </div>
  );
}
""")

add("frontend/app/quotes/[id]/page.tsx", r"""
"use client";

import { useEffect, useState } from "react";
import { api } from "../../../lib/api";

export default function QuoteDetail({ params }: any) {
  const id = params.id as string;
  const [quote, setQuote] = useState<any>(null);
  const [templates, setTemplates] = useState<any[]>([]);
  const [items, setItems] = useState<any[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const [title, setTitle] = useState("Line Item");
  const [qty, setQty] = useState(1);
  const [w, setW] = useState(500);
  const [h, setH] = useState(500);

  async function refresh() {
    const q = await api(`/api/quotes/${id}`);
    const t = await api("/api/templates");
    const it = await api(`/api/quotes/${id}/items`);
    setQuote(q);
    setTemplates(t);
    setItems(it);
    if (!selectedTemplate && t.length) setSelectedTemplate(t[0].id);
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function addItem() {
    await api(`/api/quotes/${id}/items`, {
      method: "POST",
      body: JSON.stringify({
        template_id: selectedTemplate,
        title,
        qty,
        width_mm: w,
        height_mm: h,
        sides: 1,
        options: {},
      }),
    });
    await refresh();
  }

  if (!quote) return <div>Loading…</div>;

  return (
    <div>
      <h1>Quote {quote.quote_number}</h1>
      <p>
        Subtotal: £{quote.subtotal_sell.toFixed(2)} | VAT: £{quote.vat.toFixed(2)} | Total: £{quote.total_sell.toFixed(2)}
      </p>

      <h2>Add item</h2>
      <div style={{ display: "grid", gap: 8, maxWidth: 520 }}>
        <label>
          Template
          <select value={selectedTemplate} onChange={(e) => setSelectedTemplate(e.target.value)}>
            {templates.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          Title
          <input value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>

        <label>
          Qty
          <input type="number" value={qty} onChange={(e) => setQty(parseInt(e.target.value || "1"))} />
        </label>

        <label>
          Width (mm)
          <input type="number" value={w} onChange={(e) => setW(parseFloat(e.target.value || "0"))} />
        </label>

        <label>
          Height (mm)
          <input type="number" value={h} onChange={(e) => setH(parseFloat(e.target.value || "0"))} />
        </label>

        <button onClick={addItem}>Add + Recalc</button>
      </div>

      <h2>Items</h2>
      <ul>
        {items.map((it) => (
          <li key={it.id} style={{ marginBottom: 12 }}>
            <b>{it.title}</b> — {it.qty} × {it.width_mm}×{it.height_mm}mm
            <br />
            Cost £{it.cost_total.toFixed(2)} | Sell £{it.sell_total.toFixed(2)} | Margin {(it.margin_pct * 100).toFixed(1)}%
            <details>
              <summary>Calc snapshot</summary>
              <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(it.calc_snapshot, null, 2)}</pre>
            </details>
          </li>
        ))}
      </ul>
    </div>
  );
}
""")

# -----------------------------
# Writer
# -----------------------------
def write_all():
    for path, content in FILES.items():
        p = Path(path)
        if p.parent != Path("."):
            p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    print(f"Wrote {len(FILES)} files.")
    print("Next:")
    print("  cp .env.example .env")
    print("  docker compose up --build")
    print("Then seed:")
    print("  POST http://localhost:8000/api/seed/dev")

if __name__ == "__main__":
    write_all()
