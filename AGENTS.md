# AGENTS.md

## Cursor Cloud specific instructions

### Architecture

Three-tier print quote system: PostgreSQL 16 → FastAPI backend (:8000) → Next.js frontend (:3000). See `docker-compose.yml` for the canonical service layout and `Makefile` for common commands.

### Running services locally (without Docker)

1. **PostgreSQL**: Must be running on port 5432. Start with `sudo pg_ctlcluster 16 main start`.
2. **Backend**: `cd backend && source .venv/bin/activate && PYTHONPATH=/workspace/backend uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
3. **Frontend**: `cd frontend && npm run dev`
4. Frontend proxies `/api/*` to the backend via `next.config.js` rewrites.

### .env

Copy `.env.example` to `.env` and set `DATABASE_URL=postgresql+psycopg://quote:quote@localhost:5432/quote` and `JWT_SECRET=dev-secret-key-change-in-prod`. The backend reads `.env` from the repo root via `app/core/config.py`.

### Alembic migration gotcha

Migration `014_material_custom_length_available` uses `op.add_column` (no `IF NOT EXISTS`) but the baseline migration `000_baseline.py` already includes that column. On a fresh database, run migrations up to 013, then `alembic stamp 014_mat_custom_length`, then `alembic upgrade head`:

```
alembic upgrade 013_mat_sizes_length
alembic stamp 014_mat_custom_length
alembic upgrade head
```

### Seeding dev data

After migrations, seed with `curl -X POST http://127.0.0.1:8000/api/seed/dev`. This creates admin user (`admin@local` / `admin123`), demo customer, materials, rates, and product templates.

### Tests

- **Backend**: `cd backend && source .venv/bin/activate && PYTHONPATH=/workspace/backend pytest tests/ -v`
  - 33/36 tests pass. 3 tests in `test_promote_concurrent.py` fail with "No active purchase_order document template" — this is a pre-existing issue (tests require a document template that may not exist after fresh seed).
- **Frontend type-check**: `cd frontend && npx tsc --noEmit`
- **Frontend build**: `cd frontend && npx next build`
- **E2E**: `cd frontend && CI=1 npx playwright test` (requires all 3 services running + seeded data + Playwright browsers installed)

### Lint

No ESLint configuration is present in this codebase. TypeScript type-checking (`tsc --noEmit`) serves as the primary frontend lint.

### System dependencies for WeasyPrint

The backend requires system libraries for PDF generation: `libcairo2 libpango-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf-2.0-0 shared-mime-info fonts-dejavu-core`. These are listed in the backend `Dockerfile`.
