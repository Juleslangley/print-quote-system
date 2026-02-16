# Alembic migrations

Migrations use `app.core.config` (DATABASE_URL from `.env`) and `app.models` so `Base.metadata` includes all tables.

## Purchase orders

The `purchase_orders` table uses Postgres native autoincrement for `id`:

- `id`: `BIGINT` primary key with autoincrement (BIGSERIAL/IDENTITY)
- No custom sequences; Postgres identity/autoincrement handles `id`
- PO numbers are derived from `id` after insert: `PO` + 7 zero-padded digits (e.g. `PO0000001`)
