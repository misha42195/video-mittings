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

FastAPI service (`src/api/main.py`, `app = FastAPI(...)`), routes added via routers as the service grows. `main.py` also wires `CORSMiddleware` (origins from `Settings.cors_allow_origins`) so the browser-based `apps/web` client can call the API cross-origin in dev.

Two feature modules split the user/auth concerns — `auth` (tokens: mint/verify, plus the registration and login HTTP flows) and `users` (the `User` model itself: creation, lookup by email/id) — each following the same commands/queries/schemas/exceptions layout as the top-level meetings code. `auth` depends on `users` (registration creates a user, login looks one up); `users` does not depend on `auth`.

- `config.py` — `pydantic-settings` `Settings` (env-driven: `DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRES_MINUTES`, `CORS_ALLOW_ORIGINS` — defaults to `["http://localhost:3000"]`, the web app's dev origin), cached via `get_settings()`.
- `database.py` — async SQLAlchemy engine/session (`asyncpg` driver), `Base`, `get_db` dependency. Tables are created on startup via the app's `lifespan`.
- `models.py` — SQLAlchemy models outside the `users`/`auth` split: `Meeting` (`owner_id` FK to `users.id`; every meeting belongs to exactly one user).
- `schemas.py` — Pydantic request/response DTOs for meetings: `MeetingCreate`/`MeetingResponse`.
- `exceptions.py` — `MeetingNotFoundError`, raised by meeting query handlers; routers translate it into an `HTTPException`.
- `commands.py` / `queries.py` — meetings CQRS: `CreateMeetingCommand` + `CreateMeetingHandler` (writes) vs. `ListMeetingsQuery`/`GetMeetingQuery` + their handlers (reads, both scoped to `owner_id` — a user only ever sees their own meetings; `GetMeetingHandler` raises `MeetingNotFoundError` for a missing id *or* another user's meeting, so ownership never leaks via a 403 vs. 404 distinction).
- `routers/meetings.py` — thin HTTP layer, all routes require auth via `auth.dependencies.CurrentUser`: `POST /meetings` (201), `GET /meetings` (list, own meetings only), `GET /meetings/{id}` (404 if missing or not owned).

### `users/` — the `User` model

- `models.py` — the `User` SQLAlchemy model (`email` unique/indexed, `hashed_password`).
- `security.py` — password hashing (`bcrypt`): `hash_password` / `verify_password`.
- `exceptions.py` — `EmailAlreadyRegisteredError`.
- `commands.py` — `CreateUserCommand` + `CreateUserHandler` (writes): hashes the password, raises `EmailAlreadyRegisteredError` on a duplicate email, returns the persisted `User`.
- `queries.py` — `GetUserByEmailQuery` / `GetUserByIdQuery` + handlers (reads): return `User | None`, no raising — callers (in `auth`) decide what a miss means.
- No router yet — nothing outside `auth` calls into `users` over HTTP today; add one here when user-facing endpoints (profile, search, etc.) are needed.

### `auth/` — tokens, registration, login

- `security.py` — JWT creation/decoding (`pyjwt`): `create_access_token` / `decode_access_token`.
- `schemas.py` — HTTP-facing DTOs: `UserRegister`, `Token`.
- `exceptions.py` — `InvalidCredentialsError`.
- `commands.py` — `RegisterUserCommand` + `RegisterUserHandler` (writes): delegates to `users.commands.CreateUserHandler` to create the row, then mints a `Token`.
- `queries.py` — `AuthenticateUserQuery` + `AuthenticateUserHandler` (reads only, no state mutation): looks the user up via `users.queries.GetUserByEmailHandler`, verifies the password with `users.security.verify_password`, raises `InvalidCredentialsError` on any mismatch/miss, else mints a `Token`.
- `dependencies.py` — `get_current_user` (`CurrentUser` annotated alias): `OAuth2PasswordBearer` dependency that decodes the bearer JWT and loads the `User` via `users.queries.GetUserByIdHandler`, raising 401 if the token is missing/invalid or the user no longer exists. Used by any router that requires authentication (e.g. `routers/meetings.py`).
- `router.py` — thin HTTP layer: `POST /auth/register` and `POST /auth/login` (OAuth2 password form; `username` field carries the login, which is the user's email) build a command/query, call its handler, and map domain exceptions (`EmailAlreadyRegisteredError` → 409, `InvalidCredentialsError` → 401) to HTTP status codes. Both return `{access_token, token_type}`.

Handlers everywhere (meetings, `users`, `auth`) take an `AsyncSession` and know nothing about FastAPI/HTTP, so they're testable and callable directly (see `tests/test_auth_handlers.py`, `tests/test_users_handlers.py`).

`[tool.ruff.lint]` selects `E, F, I, UP, B`. `[tool.mypy]` runs in `strict = true` mode — new code must be fully typed.

## CQRS pattern

Every use case that touches data is split into a **command** (write) or **query** (read):

- A frozen `@dataclass(frozen=True, slots=True)` describing the input — e.g. `CreateMeetingCommand`, `ListMeetingsQuery`.
- A `<Name>Handler` class next to it, constructed with `db: AsyncSession`, exposing a single `async def handle(self, command_or_query) -> ...`.

Commands live in `commands.py`, queries in `queries.py` — each module (top-level for meetings, `users/`, `auth/`) has its own pair of files. Handlers are plain Python + SQLAlchemy — no `Request`, no `HTTPException`, no FastAPI dependency injection — which is what makes them directly unit-testable without spinning up HTTP (see `tests/test_auth_handlers.py`, `tests/test_users_handlers.py`). Commands mutate state and return the persisted model (or a `Token`); queries only read and never call `db.add`/`db.commit`. A handler in one module may call another module's handler directly (e.g. `auth.commands.RegisterUserHandler` calls `users.commands.CreateUserHandler`) — that's the mechanism for cross-module composition, not HTTP or events.

Routers (`routers/meetings.py`, `auth/router.py`) are the only layer that knows about HTTP: a route builds the command/query from the validated Pydantic payload plus the `CurrentUser`/`DbDep` dependencies, calls `Handler(db).handle(...)`, and translates domain exceptions from that module's `exceptions.py` into `HTTPException`s (see e.g. `EmailAlreadyRegisteredError` → 409, `MeetingNotFoundError` → 404). Routers never touch `AsyncSession` queries directly.

Conventions for adding a new use case:

- Name the dataclass `<Verb><Noun>Command` or `<Verb><Noun>Query`.
- Put the pair in `commands.py` if it mutates state, `queries.py` if it's read-only — never mix a write into a query handler.
- Raise/add domain exceptions in that module's `exceptions.py` instead of raising `HTTPException` from a handler; let the router do that translation.
- Scope any command/query touching user-owned rows by `owner_id` in the query itself (see `ListMeetingsQuery`, `GetMeetingQuery`) so ownership is enforced in the handler, not reconstructed in the router.
- Decide which module a new use case belongs in by what it touches: mutating/reading the `User` row itself → `users`; minting/verifying tokens or the register/login HTTP flow → `auth`; anything else stays at the top level (or becomes its own module, following the same commands/queries/schemas/exceptions layout, once it's more than a router + a model).

## Tests

`tests/` has two layers:
- `test_auth_e2e.py` / `test_meetings_e2e.py` — e2e tests (`pytest` + `httpx.AsyncClient` against the real ASGI app) that exercise the HTTP API and a real Postgres database rather than mocks.
- `test_auth_handlers.py` / `test_users_handlers.py` — unit tests calling the command/query handlers directly (no HTTP layer), enabled by the CQRS split above.

`tests/conftest.py` creates/drops tables per session and truncates them after each test. Point `TEST_DATABASE_URL` at a different database if you don't want tests touching your dev `video_meetings` DB. It also has two fixtures for authenticated requests: `register_user` (factory: registers+logs in a fresh user, returns a `{"Authorization": "Bearer ..."}` header dict) and `auth_headers` (headers for a single default user) — reused by any router's e2e tests that require auth, not just meetings.
