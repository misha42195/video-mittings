@AGENTS.md

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Run from `apps/web/` (or via the root scripts in `../../package.json`, e.g. `npm run dev:web` from the repo root):

```bash
npm run dev         # dev server (Turbopack) — http://localhost:3000
npm run build        # production build (Turbopack)
npm run start         # serve the production build
npm run lint           # eslint (flat config, eslint.config.mjs)
npm run format          # prettier --write .
npm run typecheck        # tsc --noEmit
```

There is no test suite yet.

## Architecture

Next.js App Router project (`src/app`), TypeScript, Tailwind CSS v4 (via `@tailwindcss/postcss`, no `tailwind.config` file — theme is configured in CSS). Path alias `@/*` maps to `src/*` (`tsconfig.json`). ESLint uses the flat-config format, extending `eslint-config-next`'s `core-web-vitals` and `typescript` rule sets.

The app is currently the unmodified `create-next-app` starter (`src/app/page.tsx`, `layout.tsx`, `globals.css`) — no custom routes, components, or data-fetching layer exist yet.

