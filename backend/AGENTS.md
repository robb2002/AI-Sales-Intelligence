# Backend — Agent Guide

Read the root `AGENTS.md` first. This file does not override it.

**Owners:** Developer 2 (API, database, scoring) and Developer 3 (ingestion, AI, RAG, scheduler).

**Implement only the backend or AI tasks in the requested phase of `docs/IMPLEMENTATION_PLAN.md`.** Finish that phase's manual checks before the next phase.

## Documents you implement

| Document | What you take from it |
|---|---|
| `docs/API_CONTRACT.md` | Paths, bodies, enums, errors, pagination |
| `docs/DATABASE_DESIGN.md` | Tables and columns. Do not rename them |
| `docs/AUTHENTICATION.md` | Clerk verification, then role from `app_users` |
| `docs/AI_RAG_DESIGN.md` | Extraction, grounding, score explanation, Advisor |
| `docs/DATA_SOURCES.md` | The only sources and endpoints that may be called |
| `docs/TECHNICAL_PRD.md` | Process shape, scan execution, layering |
| `docs/IMPLEMENTATION_PLAN.md` | Must / should / nice, and what to cut |

## Stack

Python, FastAPI, Supabase PostgreSQL, pgvector, LangChain for splitting and retrieval only, a configurable LLM adapter, open-source embeddings, Requests, BeautifulSoup, APScheduler. Playwright only for a URL that `DATA_SOURCES.md` has already marked as requiring JavaScript.

No Redis, Celery, Kafka, or a second service. One process, one worker.

## Layering

```
Routes → services → repositories → PostgreSQL
Ingestion and AI → services → the same repositories
Services → AIService → provider adapter
```

Routes validate and authorize. They contain no business rules and no SQL. Services contain no SQL. Only repositories touch the database.

## Auth

Verify the Clerk bearer token, then load `SALES_REP` or `SALES_MANAGER` from `app_users`. Do not issue JWTs. Do not store passwords. Do not use Supabase Auth. Missing or bad tokens are 401. A valid user with no role is 403. Both roles may call every protected route. Do not filter rows by user.

`GET /api/v1/health` is the only public route.

## API and data

Match `API_CONTRACT.md`. Same error envelope for every failure. A score response includes the five factors. Evidence URLs are stored URLs and never contain `api_key`.

Schema changes go into `DATABASE_DESIGN.md` before a migration. Do not set the vector width until the embedding model is chosen. Do not add a table the design rejected.

## AI and collection

The scoring function does not call a model. The model explains the stored number. Snippets must be verbatim substrings. The model does not supply URLs. If retrieval is empty, return insufficient evidence and do not call the model.

Collect only sources and endpoints listed in `DATA_SOURCES.md`. Respect robots, rate limits, and the SAM.gov daily budget. Do not invent a notice when a source fails.

## Do not

- Create test files unless explicitly asked.
- Edit `frontend/` pages.
- Add a dependency to get around a missing contract field.
- Start Scan All, the scheduler, or USAspending while the must-have scan path is unfinished.
