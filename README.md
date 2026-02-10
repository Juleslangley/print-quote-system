# Print Quote System (Nyala + HP Roll + Zünd) — Starter Repo

## Setup instructions

1. **Clone the repo**
   ```bash
   git clone <repo-url>
   cd print-quote-system
   ```

2. **Create environment file** (no secrets in repo)
   ```bash
   cp .env.example .env
   ```
   Edit `.env`: set `DATABASE_URL` (e.g. `postgresql+psycopg://quote:quote@db:5432/quote` when using Docker) and `JWT_SECRET`. Do not commit `.env`.

3. **Start with Docker** (see below).

---

## Docker instructions

- **Start the stack:** `docker compose up --build` (or `make up` for detached).
- **Stop:** `docker compose down` (or `make down`).
- **Fresh DB:** `make reset` (down -v then up --build).

DB data persists in a named volume (`pgdata`). No absolute local paths; same behaviour on every machine.

---

## Two-machine workflow

**Home:**
```bash
git add .
git commit -m "..."
git push
```

**Office:**
```bash
git pull
docker compose up --build
```

Then open http://localhost:3000 (frontend) and http://localhost:8000/docs (backend).

---

## Run (quick reference)

Backend docs:
- http://localhost:8000/docs

Frontend:
- http://localhost:3000
- Admin: http://localhost:3000/admin (Materials, Rates, Operations, Templates, Margin profiles). If admin sublinks show 404, rebuild the frontend: `docker compose build frontend --no-cache && docker compose up -d frontend`.

## Seed dev data
POST http://localhost:8000/api/seed/dev

Creates:
- admin user: admin@local / admin123
- demo customer
- 2 materials
- rates
- 2 templates

## Backing up your data
After re-entering materials, customers, etc., save a copy so you can restore if the DB is ever reset:

```bash
./scripts/backup-db.sh
```
Saves to `backups/quote_YYYYMMDD_HHMM.sql`. To restore later:
```bash
./scripts/restore-db.sh backups/quote_20250208_1200.sql
```
Requires Docker Compose and the `db` service running.

## Quick test flow
1) Seed: POST /api/seed/dev
2) Login: POST /api/auth/login  -> token
3) List customers: GET /api/customers (auth)
4) Create quote: POST /api/quotes (auth)
5) Add item: POST /api/quotes/{id}/items (auth)
