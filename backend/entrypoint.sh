#!/bin/sh
set -e
# Run migrations before starting the app (idempotent on fresh DB)
alembic upgrade head
# Always start the web server: default uvicorn, or exec passed CMD
if [ $# -gt 0 ]; then
  exec "$@"
else
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000
fi
