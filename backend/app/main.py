import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.core.db import Base, engine
import app.models  # noqa: F401 - register all tables
from app.api import auth, customers, materials, material_sizes, rates, templates, quotes, quote_parts, seed, machines, machine_rates, operations, template_admin, document_templates
from app.api import customer_contacts, customer_contact_methods, users
from app.api import margin_profiles, pricing_rules, suppliers, purchase_orders, purchase_order_lines, backup, health, jobs, packing

logger = logging.getLogger(__name__)

app = FastAPI(title="Print Quote System", version="0.1.0")


@app.on_event("startup")
async def startup_log():
    print("✅ Backend running at http://127.0.0.1:8000")


@app.exception_handler(ValueError)
def value_error_handler(request: Request, exc: ValueError):
    """Convert ORM-level ValueError (e.g. po_number immutable) to HTTP 400."""
    if "po_number cannot be updated once created" in str(exc):
        return JSONResponse(status_code=400, content={"detail": "po_number cannot be updated once created"})
    raise exc


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception):
    """Return 500 with error detail so the frontend can show it (e.g. DB connection errors)."""
    from fastapi import HTTPException
    if isinstance(exc, HTTPException):
        raise exc
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


# Allow frontend from common dev origins (any port on localhost / 127.0.0.1)
_cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3002",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tables are managed by Alembic. Run `alembic upgrade head` before starting the app.
# Optionally warn at startup if key tables appear missing.
try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1 FROM purchase_orders LIMIT 1"))
except Exception as e:
    if "does not exist" in str(e).lower() or "relation" in str(e).lower():
        logger.warning(
            "Database tables may be missing. Run: alembic upgrade head. Original error: %s",
            e,
        )
    else:
        logger.warning("Database check at startup: %s", e)

# Optional: add columns to existing tables (dev-safe; skip if tables/columns already exist)
# Use a short statement timeout to avoid blocking startup if DB is locked (e.g. migration running).
try:
    with engine.begin() as conn:
        conn.execute(text("SET LOCAL statement_timeout = '5000'"))  # 5s max per statement
        conn.execute(text("ALTER TABLE materials ADD COLUMN IF NOT EXISTS meta JSONB DEFAULT '{}'"))
        conn.execute(text("ALTER TABLE materials ADD COLUMN IF NOT EXISTS supplier_id VARCHAR REFERENCES suppliers(id)"))
        conn.execute(text("ALTER TABLE materials ADD COLUMN IF NOT EXISTS nominal_code VARCHAR DEFAULT ''"))
        conn.execute(text("ALTER TABLE materials ADD COLUMN IF NOT EXISTS supplier_product_code VARCHAR DEFAULT ''"))
        conn.execute(text("ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS supplier_id VARCHAR REFERENCES suppliers(id)"))
        # Customers: add new columns for expanded schema
        for col, col_type in [
            ("phone", "VARCHAR DEFAULT ''"),
            ("website", "VARCHAR DEFAULT ''"),
            ("billing_name", "VARCHAR DEFAULT ''"),
            ("billing_email", "VARCHAR DEFAULT ''"),
            ("billing_phone", "VARCHAR DEFAULT ''"),
            ("billing_address", "VARCHAR DEFAULT ''"),
            ("vat_number", "VARCHAR DEFAULT ''"),
            ("account_ref", "VARCHAR DEFAULT ''"),
            ("notes", "VARCHAR DEFAULT ''"),
            ("meta", "JSONB DEFAULT '{}'"),
            ("active", "BOOLEAN DEFAULT true"),
            ("default_margin_profile_id", "VARCHAR"),
            ("created_at", "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"),
            ("updated_at", "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"),
        ]:
            conn.execute(text(f"ALTER TABLE customers ADD COLUMN IF NOT EXISTS {col} {col_type}"))
        conn.execute(text("ALTER TABLE quotes ADD COLUMN IF NOT EXISTS contact_id VARCHAR REFERENCES customer_contacts(id)"))
        for col, col_type in [
            ("margin_profile_id", "VARCHAR"),
            ("target_margin_pct", "DOUBLE PRECISION"),
            ("discount_pct", "DOUBLE PRECISION DEFAULT 0"),
            ("rounding_override", "JSONB DEFAULT '{}'"),
            ("totals_locked", "BOOLEAN DEFAULT false"),
        ]:
            conn.execute(text(f"ALTER TABLE quotes ADD COLUMN IF NOT EXISTS {col} {col_type}"))
        conn.execute(text("ALTER TABLE customer_contacts ADD COLUMN IF NOT EXISTS mobile_phone VARCHAR DEFAULT ''"))
        for col in ("first_name", "last_name", "job_title"):
            conn.execute(text(f"ALTER TABLE customer_contacts ADD COLUMN IF NOT EXISTS {col} VARCHAR DEFAULT ''"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR DEFAULT ''"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT true"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS menu_allow JSONB DEFAULT '[]'"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS menu_deny JSONB DEFAULT '[]'"))
        # Machines: add new columns (Python "category" maps to DB column "type")
        for col, col_type in [
            ("type", "VARCHAR DEFAULT 'printer_sheet'"),
            ("process", "VARCHAR DEFAULT ''"),
            ("sort_order", "INTEGER DEFAULT 0"),
            ("notes", "VARCHAR DEFAULT ''"),
            ("config", "JSONB DEFAULT '{}'"),
            ("meta", "JSONB DEFAULT '{}'"),
            ("created_at", "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"),
            ("updated_at", "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"),
        ]:
            conn.execute(text(f"ALTER TABLE machines ADD COLUMN IF NOT EXISTS {col} {col_type}"))
except Exception as e:
    logger.warning("Startup ALTERs skipped (non-fatal): %s", e)
# Note: Schema is managed by Alembic. ALTERs above are legacy dev adds; prefer adding columns via migrations.

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(seed.router, prefix="/api", tags=["seed"])
app.include_router(customers.router, prefix="/api", tags=["customers"])
app.include_router(customer_contacts.router, prefix="/api", tags=["customer-contacts"])
app.include_router(customer_contact_methods.router, prefix="/api", tags=["customer-contact-methods"])
app.include_router(materials.router, prefix="/api", tags=["materials"])
app.include_router(material_sizes.router, prefix="/api", tags=["material-sizes"])
app.include_router(suppliers.router, prefix="/api", tags=["suppliers"])
app.include_router(purchase_orders.router, prefix="/api", tags=["purchase-orders"])
app.include_router(purchase_order_lines.router, prefix="/api", tags=["purchase-order-lines"])
app.include_router(rates.router, prefix="/api", tags=["rates"])
app.include_router(margin_profiles.router, prefix="/api", tags=["margin-profiles"])
app.include_router(pricing_rules.router, prefix="/api", tags=["pricing-rules"])
app.include_router(machines.router, prefix="/api", tags=["machines"])
app.include_router(machine_rates.router, prefix="/api", tags=["machine-rates"])
app.include_router(operations.router, prefix="/api", tags=["operations"])
app.include_router(templates.router, prefix="/api", tags=["templates"])
app.include_router(template_admin.router, prefix="/api", tags=["template-admin"])
app.include_router(document_templates.router, prefix="/api", tags=["document-templates"])
app.include_router(quotes.router, prefix="/api", tags=["quotes"])
app.include_router(quote_parts.router, prefix="/api", tags=["quote-parts"])
app.include_router(jobs.router, prefix="/api")
app.include_router(packing.router, prefix="/api")
app.include_router(backup.router, prefix="/api", tags=["backup"])