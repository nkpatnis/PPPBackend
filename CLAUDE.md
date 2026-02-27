# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run with Docker (primary workflow):**
```bash
docker compose up --build        # build and start with hot reload (dev default)
docker compose up                # start without rebuilding
docker compose down              # stop
docker compose logs -f api       # tail api logs
```

Hot reload is enabled automatically in development via `docker-compose.override.yml`, which overrides the production gunicorn command with `uvicorn --reload` and mounts `./app` into the container. Changes to any file under `app/` restart the server instantly without rebuilding.

To run **without** the override (production-like):
```bash
docker compose -f docker-compose.yml up --build
```

**Local development (requires a running MySQL instance):**
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Database migrations:**
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

**No test suite exists yet.** When adding tests, use `pytest`.

## Architecture

All routes are mounted under `/api/v1`. The router in `app/api/v1/routes.py` aggregates endpoint modules:
- `POST /api/v1/auth/register` — creates a user, returns `UserResponse`
- `POST /api/v1/auth/login` — accepts JSON (not OAuth2 form), returns `Token`
- `GET/PUT/DELETE /api/v1/users/me` — protected by Bearer token

**Auth flow:** `get_current_user` in `app/core/security.py` is a FastAPI dependency used on all protected routes. It decodes the JWT, looks up `User` by `id` (stored as string in `sub`), and returns the ORM object directly.

**DB sessions:** `get_db()` in `app/db/session.py` is a generator dependency injected per-request. Sessions are never shared across requests.

**Adding a new model:** Create `app/models/<name>.py`, import it in `alembic/env.py` (alongside the existing `user` import) so Alembic detects it, then run `alembic revision --autogenerate`.

**Adding a new endpoint group:** Create `app/api/v1/endpoints/<name>.py` with an `APIRouter`, then register it in `app/api/v1/routes.py`.

## Key Constraints

- `bcrypt` is pinned to `4.0.1` — passlib is incompatible with bcrypt ≥ 4.1.
- Passwords are validated to ≤ 72 bytes (UTF-8) at the schema layer (`UserCreate`, `LoginRequest`) to avoid bcrypt truncation.
- `DATABASE_URL` must use the `mysql+pymysql://` driver scheme.
- Alembic reads `DATABASE_URL` from `app/core/config.settings` at migration time, so the env var must be set when running migrations outside Docker.
