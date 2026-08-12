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

UI components come from `@heroui/react` (v3 — no provider needed, compound components like `Card.Header`); styles are wired via `@import "@heroui/styles";` in `globals.css` alongside Tailwind.

- `src/lib/api.ts` — thin fetch-based client for `apps/api`. Base URL from `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`, see `.env.example`). Exports typed functions per endpoint (e.g. `registerUser`) and an `ApiError` (carries HTTP `status`) so callers can branch on specific codes (e.g. 409 for a duplicate email).
- `src/app/register/page.tsx` — registration page (`POST /auth/register`): email/password form built from HeroUI `Form`/`TextField`/`Card`, calls `registerUser`, stores the returned JWT in `localStorage` (`access_token`) and redirects to `/` on success.

The api's CORS policy (`CORS_ALLOW_ORIGINS` in `apps/api/src/api/config.py`) must include this app's origin for browser calls to succeed — see `apps/api/CLAUDE.md`.

## Definition of done for UI changes

Any change that touches rendered UI (new component, layout/styling tweak, new page, copy change, etc.) is **not done** until both of the following have happened — a clean `typecheck`/`lint`/`build` is necessary but not sufficient:

1. **Visual check in a real browser via Playwright MCP.** Start the dev server and use the Playwright MCP browser tools (`mcp__playwright__browser_navigate`, `browser_snapshot`/`browser_take_screenshot`, `browser_click`/`browser_type`, `browser_console_messages`, etc.) to actually load the affected page(s) and confirm the change renders and behaves as intended, including the states it touches (loading, error/invalid, empty, hover/focus, light+dark if relevant). Do not report the task complete from reading code alone or from typecheck/lint/build passing.
2. **Review against the `ui-ux-pro-max` skill.** Run it against the changed UI (design-system check for new pages, or targeted `--domain ux`/`--stack nextjs` searches for smaller tweaks) and address what it flags — accessibility, touch targets, forms/feedback, typography, etc.

Only once both checks have been done can the task be considered complete.
