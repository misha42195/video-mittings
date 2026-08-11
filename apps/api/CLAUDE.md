# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Run from `apps/api/` (or via the root scripts in `../../package.json`, e.g. `npm run dev:api` from the repo root):

```bash
uv sync                              # install/sync the venv from pyproject.toml + uv.lock
uv run fastapi dev src/api/main.py   # dev server with reload — http://localhost:8000 (docs at /docs)
uv run ruff check .                  # lint
uv run ruff format .                 # format
uv run mypy src                      # typecheck (strict mode)
uv run pytest                        # e2e tests — needs postgres running (docker-compose up -d)
uv build                             # build sdist + wheel into dist/
```

Copy `.env.example` to `.env` before running the dev server or tests (`DATABASE_URL`, `JWT_SECRET_KEY`, etc.). `docker-compose.yml` at the repo root brings up the `postgres` service the default `DATABASE_URL` points at.

## Architecture

Single-package FastAPI service (`src/api/main.py`, `app = FastAPI(...)`), routes added via routers as the service grows.

- `config.py` — `pydantic-settings` `Settings` (env-driven: `DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRES_MINUTES`), cached via `get_settings()`.
- `database.py` — async SQLAlchemy engine/session (`asyncpg` driver), `Base`, `get_db` dependency. Tables are created on startup via the app's `lifespan`.
- `models.py` — SQLAlchemy models (`User`).
- `schemas.py` — Pydantic request/response models (the HTTP-facing DTOs — kept separate from the commands/queries below).
- `security.py` — password hashing (`bcrypt`) and JWT creation (`pyjwt`).
- `exceptions.py` — domain exceptions (`EmailAlreadyRegisteredError`, `InvalidCredentialsError`) raised by command/query handlers; routers translate them into `HTTPException`s.
- `commands.py` / `queries.py` — CQRS split for the auth logic: `RegisterUserCommand` + `RegisterUserHandler` (writes) vs. `AuthenticateUserQuery` + `AuthenticateUserHandler` (reads only, no state mutation — login just checks credentials and mints a stateless JWT). Handlers take an `AsyncSession` and know nothing about FastAPI/HTTP, so they're testable and callable directly (see `tests/test_auth_handlers.py`).
- `routers/auth.py` — thin HTTP layer: `POST /auth/register` and `POST /auth/login` (OAuth2 password form; `username` field carries the login, which is the user's email) build a command/query, call its handler, and map domain exceptions to HTTP status codes. Both return `{access_token, token_type}`.

`[tool.ruff.lint]` selects `E, F, I, UP, B`. `[tool.mypy]` runs in `strict = true` mode — new code must be fully typed.

## Tests

`tests/` has two layers:
- `test_auth_e2e.py` — e2e tests (`pytest` + `httpx.AsyncClient` against the real ASGI app) that exercise auth over the HTTP API and a real Postgres database rather than mocks.
- `test_auth_handlers.py` — unit tests calling the command/query handlers directly (no HTTP layer), enabled by the CQRS split above.

`tests/conftest.py` creates/drops tables per session and truncates them after each test. Point `TEST_DATABASE_URL` at a different database if you don't want tests touching your dev `video_meetings` DB.
