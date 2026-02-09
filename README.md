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
- Admin: http://localhost:3000/admin (Materials, Rates, Operations, Templates, Margin profiles). If admin sublinks show 404, rebuild the frontend: `docker compose build frontend --no-cache && docker compose up -d frontend`.

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
