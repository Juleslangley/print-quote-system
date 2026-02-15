#!/usr/bin/env bash
# Start PostgreSQL (Docker) and the backend for local dev.
# Run from project root: ./start-db-and-backend.sh

set -e
cd "$(dirname "$0")"

echo "==> Checking Docker..."
if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Starting Docker Desktop..."
  open -a Docker 2>/dev/null || open -a "Docker Desktop" 2>/dev/null
  echo "Waiting for Docker to be ready (up to 60s)..."
  for i in $(seq 1 20); do
    sleep 3
    if docker info >/dev/null 2>&1; then
      echo "Docker is ready."
      break
    fi
    [[ $i -eq 20 ]] && { echo "Docker did not start in time."; exit 1; }
  done
fi

echo "==> Starting PostgreSQL (db container)..."
docker compose up -d db

echo "==> Waiting for Postgres to accept connections..."
for i in $(seq 1 30); do
  if docker compose exec -T db pg_isready -U quote -d quote 2>/dev/null; then
    echo "Postgres is ready."
    break
  fi
  sleep 1
  [[ $i -eq 30 ]] && { echo "Postgres did not become ready in time."; exit 1; }
done

echo "==> Starting backend on http://127.0.0.1:8000 ..."
cd backend
source .venv/bin/activate
exec python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
