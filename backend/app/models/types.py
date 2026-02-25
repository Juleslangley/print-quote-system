"""
Shared SQLAlchemy types.

We use Postgres in production, but tests and local tooling sometimes use SQLite.
SQLite can't compile Postgres-only types like JSONB, so we provide a safe variant:

- On Postgres: JSONB
- Elsewhere (e.g. SQLite): JSON
"""

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

# Use JSONB on Postgres, JSON on other dialects (SQLite, etc.)
JSONB_COMPAT = JSON().with_variant(JSONB, "postgresql")

