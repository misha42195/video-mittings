# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Structure

npm-workspaces monorepo:

- `apps/web` — Next.js (TypeScript, App Router, Tailwind v4). See `apps/web/CLAUDE.md`.
- `apps/api` — FastAPI, managed with [uv](https://docs.astral.sh/uv/). See `apps/api/CLAUDE.md`.
- `packages` — shared packages consumed by the apps above (empty for now).

`apps/api` is a uv/Python project, not an npm workspace — it's not listed in the root `workspaces` field, and its scripts are wired into the root `package.json` by shelling out to `uv run` from `apps/api`.

## Commands

Run from the repo root:

```bash
npm install                          # installs root + apps/web (npm workspaces)
cd apps/api && uv sync && cd ../..   # installs the apps/api venv

npm run dev          # web + api together (concurrently)
npm run dev:web        # web only  — http://localhost:3000
npm run dev:api        # api only  — http://localhost:8000

npm run build          # build both apps
npm run lint            # lint both apps
npm run format            # format both apps
npm run typecheck          # typecheck both apps
npm run test            # run tests (currently apps/api only — apps/web has none yet)
```

Each of `lint`, `format`, `typecheck`, and `build` also has `:web` / `:api` variants (e.g. `npm run lint:api`) to target a single app — see each app's own CLAUDE.md for the underlying per-app commands (eslint/prettier/tsc for web, ruff/mypy/uv for api). `test` currently only has a `test:api` variant since `apps/web` has no test suite yet; `apps/api`'s tests need `docker-compose up -d` (postgres) running first.

## Keeping docs in sync

When a change alters the project's architecture — a new app or package, a moved/renamed directory, a swapped framework or package manager, a new/changed root or per-app script — update this file and the relevant `apps/*/CLAUDE.md` (and `README.md`) in the same change. Stale docs here are worse than no docs, since future Claude Code sessions treat this file as ground truth.
