# Frontend — Agent Guide

Read the root `AGENTS.md` first. This file does not override it.

**Owner:** Developer 1.

**Implement only when a frontend task in `docs/IMPLEMENTATION_PLAN.md` is explicitly requested.** Do not skip ahead to dashboard, charts, or Scan All while Scan Now and the opportunity screen are unfinished.

## Documents you implement

| Document | What you take from it |
|---|---|
| `docs/UI_UX_DESIGN.md` | Tokens, components, layout, states, accessibility |
| `docs/API_CONTRACT.md` | Every path, field, enum, and error code |
| `docs/AUTHENTICATION.md` | Clerk sign-in, route guard, `GET /api/v1/me` |
| `docs/IMPLEMENTATION_PLAN.md` | What is must / should / nice, and this phase's checks |

## Stack

React, Vite, Tailwind CSS, Zustand, TanStack Query, Recharts, `lucide-react`, Clerk's React SDK.

Do not add a component library, CSS-in-JS, another data library, or another state library.

## State

TanStack Query owns server data. Zustand owns filters, open panels, and drafts. Do not copy API data into Zustand.

Poll a scan only while `status` is `queued` or `running`, then stop.

## API

Call only paths in `docs/API_CONTRACT.md`. The client sends the Clerk session token as `Authorization: Bearer`. It does not build a login API.

If a screen needs a field the contract does not have, stop and update the contract first. Do not invent a key. Do not hardcode an organization, signal, score, or evidence snippet.

## UI rules

- Use semantic tokens from `UI_UX_DESIGN.md`. No raw hex in components.
- Indigo means AI. Amber means opportunity or attention. Score bands use the documented band colors, not green-to-red.
- A score component requires value, band, factors, and explanation status.
- Every data view has loading, empty, error, and populated states. Insufficient evidence and cached data have their own components. They are not blank and not red errors.
- Build the named components in `UI_UX_DESIGN.md` §40. Do not invent a second button or card style.
- Desktop first. Do not hide scores, evidence, AI labels, or the cached marker at narrow widths.
- Meet the accessibility basics in `UI_UX_DESIGN.md` §39: contrast, visible focus, keyboard, labels, meaning not by color alone.

## Auth

Signed-out users go to `/login` (Clerk). A 401 clears the session and returns to login. A 403 `USER_NOT_PROVISIONED` or `USER_WITHOUT_ROLE` shows the no-role page, not a login loop. Both roles see the same data.

## Do not

- Create test files unless explicitly asked.
- Edit `backend/` or ingestion code.
- Polish a should-have screen while the current phase's manual checks fail.
