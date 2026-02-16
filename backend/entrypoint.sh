#!/bin/sh
set -e
# Run migrations before starting the app (idempotent on fresh DB)
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
