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
uv build                             # build sdist + wheel into dist/
```

There is no test suite yet.

## Architecture

Single-package FastAPI service. The app is instantiated in `src/api/main.py` (`app = FastAPI(...)`); routes are added directly to it as the service grows — there's currently just a `/health` endpoint. The package name (`api`) and the `src/api` layout are wired together via `uv_build` in `pyproject.toml`.

`[tool.ruff.lint]` selects `E, F, I, UP, B`. `[tool.mypy]` runs in `strict = true` mode — new code must be fully typed.
