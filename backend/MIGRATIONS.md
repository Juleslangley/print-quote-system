# Alembic migrations

Migrations use `app.core.config` (DATABASE_URL from `.env`) and `app.models` so `Base.metadata` includes all tables.

## First-time setup (add purchase orders tables)

Ensure the database already has base tables (e.g. from running the app once so `Base.metadata.create_all()` has run). Then:

```bash
cd backend
# Optional: use a venv and install deps first
# python -m venv .venv && source .venv/bin/activate  # or Windows: .venv\Scripts\activate
# pip install -r requirements.txt

alembic upgrade head
```

This creates `purchase_orders_sequence`, `purchase_orders`, and `purchase_order_lines` (and records the migration in `alembic_version`).

## Creating a new migration (autogenerate)

After changing models:

```bash
cd backend
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

## Verify

After `alembic upgrade head`, start the backend and call:

```http
GET /api/purchase-orders
Authorization: Bearer <token>
```

Response should be `200` with body `[]` (or a list of POs).

## Commands

- `alembic upgrade head` – apply all pending migrations
- `alembic current` – show current revision
- `alembic history` – list revisions
