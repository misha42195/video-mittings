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
- `models.py` — SQLAlchemy models: `User`, `Meeting` (`owner_id` FK to `users.id`; every meeting belongs to exactly one user).
- `schemas.py` — Pydantic request/response models (the HTTP-facing DTOs — kept separate from the commands/queries below): `UserRegister`/`Token` for auth, `MeetingCreate`/`MeetingResponse` for meetings.
- `security.py` — password hashing (`bcrypt`) and JWT creation/decoding (`pyjwt`): `create_access_token` / `decode_access_token`.
- `dependencies.py` — `get_current_user` (`CurrentUser` annotated alias): `OAuth2PasswordBearer` dependency that decodes the bearer JWT (`decode_access_token`) and loads the `User`, raising 401 if the token is missing/invalid or the user no longer exists. Used by any router that requires authentication.
- `exceptions.py` — domain exceptions (`EmailAlreadyRegisteredError`, `InvalidCredentialsError`, `MeetingNotFoundError`) raised by command/query handlers; routers translate them into `HTTPException`s.
- `commands.py` / `queries.py` — CQRS split, one command/query + handler pair per use case. Auth: `RegisterUserCommand` + `RegisterUserHandler` (writes) vs. `AuthenticateUserQuery` + `AuthenticateUserHandler` (reads only, no state mutation — login just checks credentials and mints a stateless JWT). Meetings: `CreateMeetingCommand` + `CreateMeetingHandler` (writes) vs. `ListMeetingsQuery`/`GetMeetingQuery` + their handlers (reads, both scoped to `owner_id` — a user only ever sees their own meetings; `GetMeetingHandler` raises `MeetingNotFoundError` for a missing id *or* another user's meeting, so ownership never leaks via a 403 vs. 404 distinction). Handlers take an `AsyncSession` and know nothing about FastAPI/HTTP, so they're testable and callable directly (see `tests/test_auth_handlers.py`).
- `routers/auth.py` — thin HTTP layer: `POST /auth/register` and `POST /auth/login` (OAuth2 password form; `username` field carries the login, which is the user's email) build a command/query, call its handler, and map domain exceptions to HTTP status codes. Both return `{access_token, token_type}`.
- `routers/meetings.py` — thin HTTP layer, all routes require auth via `CurrentUser`: `POST /meetings` (201), `GET /meetings` (list, own meetings only), `GET /meetings/{id}` (404 if missing or not owned).

`[tool.ruff.lint]` selects `E, F, I, UP, B`. `[tool.mypy]` runs in `strict = true` mode — new code must be fully typed.

## Tests

`tests/` has two layers:
- `test_auth_e2e.py` / `test_meetings_e2e.py` — e2e tests (`pytest` + `httpx.AsyncClient` against the real ASGI app) that exercise the HTTP API and a real Postgres database rather than mocks.
- `test_auth_handlers.py` — unit tests calling the command/query handlers directly (no HTTP layer), enabled by the CQRS split above.

`tests/conftest.py` creates/drops tables per session and truncates them after each test. Point `TEST_DATABASE_URL` at a different database if you don't want tests touching your dev `video_meetings` DB. It also has two fixtures for authenticated requests: `register_user` (factory: registers+logs in a fresh user, returns a `{"Authorization": "Bearer ..."}` header dict) and `auth_headers` (headers for a single default user) — reused by any router's e2e tests that require auth, not just meetings.
