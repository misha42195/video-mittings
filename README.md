# video-meetings

Monorepo:

- `apps/web` — Next.js (TypeScript, App Router, Tailwind, ESLint, Prettier), npm workspace
- `apps/api` — FastAPI, managed with [uv](https://docs.astral.sh/uv/), linted with [ruff](https://docs.astral.sh/ruff/), type-checked with [mypy](https://mypy.readthedocs.io/)
- `packages` — shared packages consumed by the apps above (empty for now)

## Setup

```bash
npm install        # installs root + apps/web (npm workspaces)
cd apps/api && uv sync && cd ../..   # installs the Python venv for apps/api
```

## Commands

Run from the repo root:

```bash
npm run dev         # run web + api together
npm run dev:web      # web only  — http://localhost:3000
npm run dev:api      # api only  — http://localhost:8000

npm run build        # build both apps
npm run build:web
npm run build:api

npm run lint          # lint both apps
npm run format        # format both apps
npm run typecheck     # typecheck both apps
```

Each of `lint`, `format`, and `typecheck` also has `:web` / `:api` variants (e.g. `npm run lint:api`) to target a single app.

Under the hood, `apps/web` scripts run via npm/next/eslint/prettier/tsc, and `apps/api` scripts shell out to `uv run` (ruff, mypy, fastapi).
