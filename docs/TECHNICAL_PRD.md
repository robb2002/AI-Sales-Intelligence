# Technical PRD — AI Sales Intelligence System

> **Status:** DRAFT — decisions of 2026-09-23 recorded
> **Version:** 0.3
> **Date:** 2026-09-23
> **Authoring order:** 2 of 9
> **Depends on:** root `AGENTS.md`, `docs/PRODUCT_PRD.md` (business source of truth)
> **Primary author:** Lead architect, reviewed by all three developers

## Purpose of this document

The complete technical architecture for the product approved in `PRODUCT_PRD.md`, and the
integration boundaries that let three developers work independently for one week.

**Boundaries.** This document defines architecture and the contracts between components. It does
not define the schema (`DATABASE_DESIGN.md`), the endpoint catalogue (`API_CONTRACT.md`), prompts
and retrieval detail (`AI_RAG_DESIGN.md`), the source register (`DATA_SOURCES.md`), the auth
mechanism (`AUTHENTICATION.md`), or visual design (`UI_UX_DESIGN.md`). Where a name appears here —
a table, an endpoint, a module — it is *indicative*, and the document that owns it is
authoritative.

**Technology is fixed** by `AGENTS.md` §11 and restated in the request. This document does not
re-open those choices; it decides how they are assembled.

**Conventions.** Architecture decisions are numbered `AD-nn` and summarized in §29. Product
requirements are referenced by their `PRODUCT_PRD.md` IDs, for example `FR-SCAN-03`.

---

## 1. System architecture

### 1.1 Shape

One React single-page application, one FastAPI backend, one Supabase PostgreSQL database. The
backend is a **single deployable process** that hosts the HTTP API, the scheduler, the ingestion
pipeline, and the AI service.

```
┌──────────────────────────┐
│  Browser (SPA)           │   React + Vite + Tailwind
│  Zustand · TanStack Query│   Recharts
└───────────┬──────────────┘
            │  HTTPS / JSON  (api/v1, contract in API_CONTRACT.md)
┌───────────▼──────────────────────────────────────────────┐
│  FastAPI application (single process)                    │
│                                                          │
│  API layer        routes · auth · validation · errors    │
│  Service layer    orchestration · business rules         │
│    ├── Scan orchestrator                                 │
│    ├── Signal pipeline (extract→validate→dedupe→correl.) │
│    ├── Scoring engine (deterministic)                    │
│    └── AI service → LLM provider adapter                 │
│  Ingestion        collectors · source registry · limiter │
│  Scheduler        APScheduler (in-process)               │
│  Repository layer data access (single path to the DB)    │
└───────────┬───────────────────────────┬──────────────────┘
            │ asyncpg / SQLAlchemy      │ HTTPS (outbound)
┌───────────▼─────────────┐   ┌─────────▼──────────────────┐
│ Supabase PostgreSQL     │   │ Approved public sources    │
│ + pgvector              │   │ SAM.gov · USAspending.gov  │
│ relational + embeddings │   │ IPEDS · official org sites │
└─────────────────────────┘   └────────────────────────────┘
                              ┌────────────────────────────┐
                              │ Configurable LLM provider  │
                              │ (via adapter only)         │
                              └────────────────────────────┘
```

### 1.2 AD-01 — Monolith, deliberately

**Decision.** One backend process, not a set of services.

**Reasoning.** Three developers, five working days, and a data volume measured in tens of
organizations. Every service boundary we add costs a deployment, a contract, and a debugging
surface. `AGENTS.md` §13 rules out Kubernetes, Kafka, and microservices; this decision also rules
out Redis, Celery, and any separate worker deployment for the MVP. §7 and §9 below show how
long-running scans and scheduling are handled without them.

**Consequence.** The process is stateful in one respect — in-flight scans and scheduled jobs live
in its memory — which drives AD-03 (single worker) and AD-04 (database-backed run state).

### 1.3 Request and data flow

Two flows exist, and they meet in the database.

**Write flow (ingestion, minutes-scale, asynchronous).** Scheduler or user trigger → scan
orchestrator → collectors fetch from approved sources → raw documents persisted with URL and
retrieval timestamp (`FR-DATA-05`) → signal pipeline (§21) → scoring pipeline (§22) → results
persisted.

**Read flow (user-facing, milliseconds-scale, synchronous).** SPA → API route → service →
repository → PostgreSQL → JSON response. The read path never calls an external source and never
calls an LLM, with one exception: the AI Advisor (§23), which is synchronous but bounded.

Separating these is the single most important structural property of the system. A slow or failing
public source degrades ingestion; it never makes the dashboard slow or unavailable.

---

## 2. Frontend architecture

**Owner:** Developer 1.

### 2.1 Structure

Feature-sliced, so that a feature's components, hooks, and types sit together and two developers
rarely touch the same file.

```
frontend/src/
  main.tsx, App.tsx          app bootstrap, providers, router
  routes/                    route definitions and guards
  features/
    auth/                    login, session bootstrap
    dashboard/               command centre (FR-DASH-01..10)
    organizations/           search, profile (FR-ORG-01..08)
    signals/                 list, filters, detail (FR-SIG-09..15)
    opportunities/           list, detail, score panel (FR-OPP-07..15)
    advisor/                 AI Sales Advisor (FR-ADV-01..07)
    scans/                   Scan Now trigger and progress (FR-SCAN-01..09)
  components/ui/             shared primitives (design system)
  components/evidence/       evidence viewer, used by every feature
  api/                       typed client: one module per contract resource
  stores/                    Zustand stores (UI state only)
  lib/                       formatting, constants, query client config
  types/                     types mirroring API_CONTRACT.md
```

### 2.2 State ownership

**AD-13.** TanStack Query owns all server state — fetching, caching, invalidation, loading and
error status. Zustand owns only local UI state: active filters, selected items, panel visibility,
advisor draft input. Server data is never copied into a Zustand store.

Query keys are structured `[resource, scope, params]` so that a completed scan can invalidate
exactly the affected organization's signals and opportunities.

### 2.3 API layer

All HTTP lives in `src/api/`. Components never call `fetch` directly. One module per contract
resource, each exporting typed functions whose request and response types mirror
`API_CONTRACT.md`. A single configured client attaches the auth token, sets the base URL from
build configuration, and normalizes the error envelope (§13) into a typed error the UI can switch
on.

Types are hand-written from the contract rather than generated, because adding a codegen toolchain
costs more than it saves at this size. If the contract and the types drift, the contract wins.

### 2.4 Scan progress without sockets

Triggering a scan returns a scan run identifier. The UI then polls that run with TanStack Query's
`refetchInterval` until it reaches a terminal state, rendering the current stage (`FR-SCAN-03`).
Polling is stopped on terminal states and when the component unmounts. No WebSocket, no
server-sent events, no additional infrastructure.

### 2.5 Presentation invariants the architecture must support

The API must supply what the UI is required to show: a score is never returned without its factor
breakdown and explanation (`FR-SCR-05`), every insight carries evidence (`FR-EV-03`), and
cached/fallback data carries a flag (`FR-FB-03`). These are response-shape obligations in
`API_CONTRACT.md`, not client-side decorations.

### 2.6 Build

Vite. Environment configuration is build-time (`VITE_API_BASE_URL`). The production build is
static files served by the frontend host. No server-side rendering.

**Approved 2026-09-23.** Client routing uses React Router in declarative mode (`BrowserRouter`,
`Routes`). No framework mode, no route loaders.

---

## 3. Backend architecture

**Owner:** Developer 2 for API/services/repositories; Developer 3 for ingestion and AI.

### 3.1 Layering

```
API routes  →  Services  →  Repositories  →  PostgreSQL
Ingestion   →  Services  ↗
AI service  →  Repositories ↗
```

Routes validate input, resolve the caller's identity and role, and delegate. They contain no
business logic. Services contain no SQL. Repositories are the only code that touches the database,
and ingestion and AI reach data through those same repositories rather than opening their own
connections.

### 3.2 Module structure

```
backend/app/
  main.py                 app factory, middleware, lifespan (scheduler start/stop)
  api/
    deps.py               shared dependencies (current user, role guard, pagination)
    v1/                   one router module per resource
  core/
    config.py             typed settings (§15)
    logging.py            structured logging setup (§14)
    errors.py             exception hierarchy + handlers (§13)
    security.py           Clerk session verification, Clerk user profile fetch, app_users upsert
  services/
    scan_orchestrator.py  drives a scan run end to end
    signal_service.py     extraction, validation, dedupe, correlation orchestration
    opportunity_service.py
    advisor_service.py
    evidence_service.py
  scoring/
    weights.py            the single definition of factors and weights (FR-SCR-06)
    engine.py             deterministic score computation
  ingestion/
    registry.py           approved source registry, loaded from config
    limiter.py            per-source rate limiting and politeness
    fetcher.py            HTTP/Playwright access with robots and allowlist enforcement
    collectors/           one module per approved source
    normalizer.py         raw payload → normalized document
  ai/
    service.py            AIService — the only entry point for model calls
    adapters/             one adapter per provider, selected by configuration
    embeddings.py         embedding model access
    prompts/              versioned prompt templates
    rag/                  chunking, indexing, retrieval
  repositories/           data access, one module per aggregate
  schemas/                Pydantic request/response models
  scheduler/
    jobs.py               job definitions
    runner.py             APScheduler wiring
```

### 3.3 Async model

FastAPI runs async. Outbound HTTP for collection and LLM calls is async. CPU-bound work —
embedding computation if run locally, scoring arithmetic — is dispatched to a thread pool so it
cannot block the event loop and make the dashboard unresponsive.

---

## 4. Database architecture

**Owner:** Developer 2. Schema is owned by `DATABASE_DESIGN.md`; this section covers access and
topology only.

### 4.1 AD-05 — Direct PostgreSQL connection

**Decision.** The backend connects to Supabase over the standard PostgreSQL protocol using
SQLAlchemy (async) with asyncpg, not through the Supabase REST client.

**Reasoning.** The workload needs pgvector similarity queries, multi-table joins for evidence
assembly, and transactional pipeline writes. Expressing those through a REST client is awkward and
slower. Supabase is used here as managed PostgreSQL plus pgvector.

**Consequence.** Row Level Security is not the enforcement mechanism. The backend holds database
credentials and **authorization is enforced in the application layer** (`FR-ROLE-02`, §11). The
database credential is never exposed to the browser.

### 4.2 Connection management

A single async connection pool, sized small (the free tier limits connections). Ingestion runs in
the same process and shares the pool, which is another reason scans are sequential rather than
massively parallel (§7.4).

### 4.3 Migrations

Alembic, with migration files committed to the repository and applied by Developer 2. Schema
changes are documented in `DATABASE_DESIGN.md` before they are applied, so the other two
developers learn about a change from the document rather than from a broken query.

### 4.4 Vector storage

pgvector in the same database as the relational data, not a separate vector store. Keeping
embeddings beside their source rows means a retrieval hit can join directly to its organization,
signal, and evidence, which is exactly what citation assembly requires (§24). Embedding dimension
and index type are set in `DATABASE_DESIGN.md` once the embedding model is chosen (§5.4).

### 4.5 Data volume expectations

Tens of organizations, hundreds to low thousands of raw documents, thousands of chunks. This fits
comfortably in a free-tier Postgres and justifies the absence of caching infrastructure: at this
volume, an indexed query is fast enough that adding Redis would be pure overhead.

---

## 5. AI service architecture

**Owner:** Developer 3.

### 5.1 The boundary

```
Services (business logic)
      │  never imports a vendor SDK
      ▼
AIService              one entry point for every model call
      ▼
LLMProviderAdapter     interface
      ▼
<Provider>Adapter      selected at startup by configuration
```

**AD-07.** No module outside `app/ai/adapters/` may import a provider SDK. No provider name, model
name, or key is hardcoded anywhere (§15, §16). Switching providers is a configuration change.

The adapter interface is deliberately narrow — a completion call, a structured/JSON-constrained
call, and an embedding call. Narrow interfaces are portable; if one provider offers a distinctive
feature, using it in business logic would defeat the decision.

*Illustrative shape only; the authoritative definition is in `AI_RAG_DESIGN.md`:*

```python
class LLMProviderAdapter(Protocol):
    async def complete(self, prompt: Prompt, *, context: list[Chunk]) -> Completion: ...
    async def complete_structured(self, prompt: Prompt, schema: type[BaseModel]) -> BaseModel: ...
    async def embed(self, texts: list[str]) -> list[Vector]: ...
```

### 5.2 Responsibilities of the AI service

Signal extraction from normalized documents, signal validation support, correlation reasoning,
score *explanation*, Advisor answers, and recommended next actions. Everything the AI service
returns is labelled as AI-produced so the UI can keep the four layers distinct (`FR-EV-06`).

### 5.3 What the AI service must not do

It does not compute the opportunity score (`FR-SCR-01`; enforced structurally by §22 — the scoring
engine has no dependency on the AI service). It does not decide which sources to collect. It never
receives write access to the database independent of a service.

### 5.4 Embeddings

Embeddings are accessed through the embedding adapter so the deployment can change without touching
callers.

> **Decided 2026-09-25 (updated).** Hosted Azure OpenAI embeddings on the same resource/key as
> chat. Model: `text-embedding-3-small` (deployment name in `EMBEDDING_MODEL`), vector width
> **1536**. Chat stays `interns-gpt-4.1`. Local/Groq embedding paths were removed from the default
> product path. Switching width requires a migration and a full re-index.

### 5.5 LangChain, used narrowly

LangChain provides document loaders, text splitters, and retriever plumbing. Application control
flow — the scan orchestrator, the pipeline stages, the scoring engine — is our own code. Chains and
agents are not used for orchestration; they would obscure the stage boundaries that make the
pipeline debuggable and divisible between developers.

---

## 6. RAG architecture

**Owner:** Developer 3. Retrieval strategy, chunk sizes, and prompts are detailed in
`AI_RAG_DESIGN.md`; this is the architectural skeleton.

### 6.1 Indexing (write path, during ingestion)

```
Raw document → Clean → Chunk → Attach metadata → Embed → Store chunk + vector (pgvector)
```

Metadata attached to every chunk must include organization, source, source URL, observed or
published date (or an explicit "not available"), and the identifier of the raw document it came
from. **This is a hard architectural requirement, not an optimization:** retrieval cannot produce a
citation for metadata that was never stored, and `FR-EV-01` requires every cited item to carry
source name, URL, date where available, and snippet.

### 6.2 Retrieval (read path, during an Advisor question)

```
Question → Embed → Vector search in pgvector, filtered by organization
         → Top-k chunks with metadata
         → Sufficiency check
         → Prompt assembly (question + retrieved context + grounding instructions)
         → LLM
         → Grounded answer + citations resolved from chunk metadata
```

Filtering by organization before similarity search is mandatory, not a refinement. It is what
prevents evidence from one institution being cited in an answer about another — a fabrication in
`FR-ADV-05` terms.

### 6.3 The sufficiency gate

Between retrieval and generation sits an explicit check: if retrieval returns nothing above the
relevance threshold, the service returns an "insufficient evidence" result **without calling the
LLM** (`FR-ADV-04`). Implementing this as a gate rather than as prompt wording means the honest
answer does not depend on the model choosing to be honest.

---

## 7. Data ingestion architecture

**Owner:** Developer 3.

### 7.1 Scan run as the unit of work

Every collection and analysis run — manual (`FR-SCAN-01`) or scheduled (`FR-SCHED-02`) — is a
**scan run** recorded in the database with its status, current stage, per-source outcomes, counts
of what changed, start and end times, and any failure reasons. Manual and scheduled scans execute
the identical code path; only the trigger differs.

**AD-09.** Each pipeline stage persists its output before the next begins. The cost is extra
writes; the benefits are decisive for this project: a failed run is inspectable rather than lost,
a stage can be re-run in isolation during development, and three developers can work on different
stages against real intermediate data.

### 7.2 AD-02 — Asynchronous execution without a task queue

**Decision.** `POST` to trigger a scan returns `202 Accepted` with a scan run resource immediately.
The work runs as an asyncio background task in the same process. The client polls the run resource
for progress (§2.4).

**Reasoning.** This satisfies `FR-SCAN-03` (visible progress), `FR-SCAN-08` (persisted results),
and the §21 concern about scan latency, without Celery, Redis, or a worker deployment. The database
row, not a broker, is the source of truth for run state.

**Consequence and mitigation.** A process restart orphans in-flight runs. On startup the
application marks any run still `running` as `interrupted` with a stated reason, rather than
leaving a run that appears to be progressing forever.

### 7.3 AD-04 — One scan per organization

`FR-SCAN-07` is enforced in the database, not in process memory: a uniqueness constraint permitting
at most one active run per organization. A second request returns the existing run rather than
starting a duplicate. Enforcing it in the database means the guarantee survives a restart and does
not depend on the process being singular.

### 7.4 Concurrency policy

Within a run, sources are fetched with bounded concurrency; across runs, a small global limit
applies. Scheduled scans process organizations sequentially. The constraint is not CPU — it is
politeness to public sources (`FR-DATA-03`) and the connection pool (§4.2).

**Scan All** (`FR-SCAN-10`–`FR-SCAN-13`, approved 2026-09-22) creates one scan run per tracked
organization and feeds those runs through this same limit. It does not start every organization at
once. The API returns a batch resource the client polls; each child run keeps its own stage,
per-source outcome, and the one-active-run-per-organization rule. Organizations already scanning
are attached to, not duplicated.

### 7.5 Failure isolation

**AD-10 (partial).** Each source is collected inside its own error boundary. A source that times
out, rate-limits, or returns an error is recorded as a failed source on the run, and the run
continues with the remaining sources (`FR-SCAN-05`). A run in which some sources failed completes
with a partial status that names what failed and why — it is never reported as a clean success, and
never silently topped up with cached data (`FR-FB-04`).

Retries use bounded exponential backoff and apply only to transient failures. A 403, a robots
disallow, or an authentication wall is **not** retried; it is a permanent refusal that the system
respects (`FR-DATA-03`).

### 7.6 Fallback dataset

The cached dataset is real content previously retrieved from approved sources, stored with its
original URL and retrieval timestamp (`FR-FB-02`), and flagged at the row level. The flag
propagates through every derived record and every API response so the UI can label it
(`FR-FB-03`). It is read only when a live source fails **and** the failure is reported alongside
it; there is no code path that substitutes cached data silently.

---

## 8. Web collection architecture

**Owner:** Developer 3.

### 8.1 Source registry

**AD-10.** Collection is driven by a registry of approved sources loaded from configuration, with
one entry per source recording its type, base URL or API endpoint, access method, rate limit,
politeness delay, and reliability rating. The registry is the machine-readable counterpart of
`DATA_SOURCES.md`, which remains authoritative.

A collector cannot fetch a URL that is not permitted by its registry entry. The allowlist check
sits in the shared fetcher, not in individual collectors, so compliance cannot be forgotten in a
new collector (`FR-DATA-02`, `FR-DATA-04`).

### 8.2 Access tiers

| Tier | Method | Used for |
|---|---|---|
| 1 | Official API | SAM.gov, USAspending.gov — structured, documented, preferred |
| 2 | Public data file / feed | IPEDS reference data (`FR-DATA-07`: enrichment only) |
| 3 | Requests + BeautifulSoup | Static pages on approved official organization websites |
| 3a | `httpx` (async) | Async outbound HTTP for URL validation, website page fetch, and the Azure OpenAI adapter (AD-07). It is the async stand-in for Requests inside the FastAPI process. BeautifulSoup still does all HTML parsing. No browser-impersonation client and no second extraction library |
| 4 | Playwright | Only where a page genuinely requires JavaScript rendering |

Playwright is a last resort because it multiplies the deployment footprint (a browser binary in
the backend image). Its use must be justified per source in `DATA_SOURCES.md`.

### 8.3 Compliance controls, enforced centrally

Every outbound fetch passes through the shared fetcher, which enforces: allowlist membership,
robots restrictions, per-source rate limit and politeness delay, request timeout, honest
identifying user agent, and bounded retry. The prohibitions in `FR-DATA-03` — no bypassing
authentication, access controls, robots, rate limits, paywalls, or CAPTCHAs — are structural: there
is no code path that can do so, and adding one would require modifying the shared fetcher, which is
a reviewable change.

### 8.4 Raw content persistence

Every successful fetch persists the raw payload, the exact URL, the HTTP status, a content hash,
and the retrieval timestamp *before* any parsing (`FR-DATA-05`). Parsing failures therefore never
lose the evidence, and every downstream claim can be traced to bytes actually retrieved.

---

## 9. Scheduling architecture

**Owner:** Developer 3.

**AD-03.** APScheduler runs in-process, started and stopped by the FastAPI lifespan handler. Jobs
are declared in code and configured by settings, so no job store is required; there are no
user-created schedules to persist.

**The single-worker constraint.** Because the scheduler is in-process, the backend must run as
**one worker process**. Two workers would mean two schedulers and duplicated scans. This is
recorded as a deployment requirement in §27, and it is acceptable at this scale — but it is a real
constraint that must not be forgotten when someone later sees a "scale up workers" setting.

Scheduled jobs for the MVP: a periodic scan sweep over tracked organizations (`FR-SCHED-01`),
whose cadence follows the decision in `PRODUCT_PRD.md` §22 and per-source frequency in
`DATA_SOURCES.md`; and a startup reconciliation job that marks interrupted runs (§7.2). Each run
records start, end, sources attempted, sources failed, and signals produced (`FR-SCHED-04`).

Jobs are configured with `coalesce` and a maximum of one concurrent instance, so a slow sweep does
not stack up behind itself.

---

## 10. Authentication architecture

**Owner:** Developer 2 for the FastAPI verification dependency and the role store. Developer 1 for
the Clerk frontend integration. The full mechanism is owned by `AUTHENTICATION.md`.

**AD-15 — approved 2026-09-22.** Clerk authenticates. FastAPI authorizes.

```
Browser  →  Clerk (email/password login, session)
         →  session token on each API request
FastAPI  →  verifies the Clerk session
         →  loads SALES_REP or SALES_MANAGER from our database
         →  enforces the role on the route
```

| Concern | Owner |
|---|---|
| Login, session, password storage, user identity | Clerk |
| Business roles `SALES_REP` and `SALES_MANAGER` | Our database, enforced by FastAPI |
| Mapping a Clerk user id to a role | Our user table |

The backend does not issue its own tokens, does not store passwords, and does not implement a
login form. Every protected route verifies the Clerk session and then applies the role check.
Roles are not read from Clerk as the source of permission; Clerk proves who the user is, and our
table says what they may do. That keeps authorization in the application layer, consistent with
AD-05.

Enterprise SSO remains out of MVP. Email/password through Clerk satisfies the login method in
`AGENTS.md` §11. Clerk itself is an approved addition to the stack (explicit decision, 2026-09-22);
it is not a second authorization system.

**Approved 2026-09-23.** FastAPI verifies the Clerk session token with PyJWT against the Clerk
instance's JWKS, fetched with `CLERK_SECRET_KEY`. The token's `azp` must be one of
`CORS_ALLOWED_ORIGINS`. PyJWT only verifies tokens; it never issues them.

A user who authenticates in Clerk but has no role row is denied. Roles are assigned by the team
during the hackathon, not self-selected at sign-up.

---

## 11. Authorization

Authorization is enforced **server-side on every protected operation** (`FR-ROLE-02`), in the route
layer via a shared dependency that resolves the caller and asserts the required role. The
frontend's role awareness is a usability feature and carries no security weight.

**Approved 2026-09-22.** Both `SALES_REP` and `SALES_MANAGER` see every tracked organization
(`PRODUCT_PRD.md` `FR-ROLE-04`). Authorization is role-based, not record-based. List queries do
not filter by the calling user. Organization assignment is out of MVP scope; adding it later means
every list query gains an ownership filter, which is a schema and contract change, not a flag.

Both roles receive identical evidence for any item both can access (`FR-ROLE-03`); no filtering is
applied to evidence based on role.

---

## 12. API architecture

**Owner:** Developer 2. The endpoint catalogue is owned by `API_CONTRACT.md`.

**AD-06.** REST over JSON under a versioned prefix (`/api/v1`). Resource-oriented paths, standard
HTTP semantics, offset-based pagination (simpler than cursors and adequate at this volume), and
filtering via query parameters (`FR-SRCH-01..08`).

Key architectural properties the contract must preserve:

- **Long-running operations return a resource, not a blocked connection.** Triggering a scan
  returns `202` with a run resource to poll (§7.2).
- **Composite responses.** A score is never returned alone; the response carries the factor
  breakdown and explanation (`FR-SCR-05`). An insight is never returned without its evidence
  references (`FR-EV-03`). This keeps the UI from having to fetch three endpoints to render one
  honest card, and makes the invariant enforceable on the server.
- **Cached-data flag.** Any response containing fallback-derived data carries the flag
  (`FR-FB-03`).
- **One error envelope** for every failure (§13).

Every request and response is a Pydantic model. The generated OpenAPI document is a useful
cross-check for the three developers, but `API_CONTRACT.md` remains the agreed contract: the
document is written first and the code conforms to it, not the reverse.

---

## 13. Error handling

A typed exception hierarchy rooted at one application exception, with subclasses for validation,
not-found, authorization, conflict, external-source failure, and AI-provider failure. Registered
exception handlers convert them into a single error envelope; unhandled exceptions become a generic
500 that logs the detail server-side and never leaks internals to the client.

```json
{ "error": { "code": "SCAN_ALREADY_RUNNING", "message": "...", "details": { } } }
```

Three domain-specific rules matter more than the mechanics:

1. **Source failures are data, not exceptions.** A failed collector is recorded on the scan run and
   surfaced to the user as a partial result (`FR-SCAN-05`). It does not fail the request.
2. **AI failures degrade honestly.** If the provider is unavailable, the affected insight is absent
   and labelled as unavailable. Nothing is ever substituted from model knowledge or cached content
   to fill the gap.
3. **Insufficient evidence is a successful response** describing insufficiency (`FR-ADV-04`), not
   an error status.

---

## 14. Logging

Structured JSON logs to stdout, collected by the hosting platform. No separate logging
infrastructure.

Every scan run has an identifier that appears on every log line it produces, so one run's path
through collection, extraction, validation, deduplication, correlation, and scoring can be read
end to end. API requests carry a request identifier.

Logged at minimum: scan lifecycle and stage transitions, per-source fetch outcomes with status and
duration, counts at each pipeline stage (candidates, validated, rejected, merged), scoring inputs
and result, AI calls with provider, model, latency, and token usage where available, and all
errors with context.

**Never logged:** credentials, API keys, tokens, or full prompt/response bodies containing them.
Prompt logging for debugging is behind a configuration flag, off by default in production.

---

## 15. Configuration

A single typed settings object (`pydantic-settings`) loaded once at startup, read from environment
variables with `.env` support for local development. Modules receive settings by injection rather
than importing a global, which keeps them independently testable later.

Configuration is validated at startup and the process fails fast with a clear message if a required
value is missing — preferable to discovering a missing API key midway through a demo scan.

Three configuration groups deserve special mention:

- **Scoring weights** (`FR-SCR-06`) live in `app/scoring/weights.py` as a single versioned
  definition, not scattered as literals. Version `v1` is approved in `PRODUCT_PRD.md` §13.3
  (30 / 25 / 20 / 15 / 10; bands High, Medium, Low, Monitor). Each computed score records the
  version that produced it. Tuning during the hackathon creates a new version; it does not edit
  `v1` in place.
- **The source registry** (§8.1) is configuration, so adding an approved source is a config and
  documentation change rather than a code change.
- **AI provider selection** is configuration, per AD-07.

`.env.example` is committed with placeholder values only. A populated `.env` is never committed.

---

## 16. Environment variables

Names and purposes only; values are never recorded in this repository.

| Variable | Scope | Purpose |
|---|---|---|
| `DATABASE_URL` | Backend | Supabase PostgreSQL connection string |
| `APP_ENV` | Backend | `local` / `production` |
| `LOG_LEVEL` | Backend | Logging verbosity |
| `CLERK_SECRET_KEY` | Backend | Verifies Clerk session tokens. Never sent to the browser |
| `CLERK_PUBLISHABLE_KEY` | Frontend | Clerk client key, exposed as `VITE_CLERK_PUBLISHABLE_KEY` |
| `CORS_ALLOWED_ORIGINS` | Backend | Permitted frontend origins |
| `LLM_PROVIDER` | Backend | Selects the adapter (AD-07). MVP discovery uses `azure_openai` when configured |
| `LLM_MODEL` | Backend | Model or Azure deployment name for the selected provider |
| `LLM_API_KEY` | Backend | Provider credential (Azure OpenAI key when `LLM_PROVIDER=azure_openai`) |
| `LLM_TIMEOUT_SECONDS` | Backend | Bound on model calls |
| `AZURE_OPENAI_ENDPOINT` | Backend | Azure OpenAI resource endpoint when using `azure_openai` |
| `AZURE_OPENAI_API_VERSION` | Backend | Azure OpenAI API version string |
| `EMBEDDING_MODEL` | Backend | Open-source embedding model identifier |
| `EMBEDDING_API_URL` | Backend | Only if hosted embeddings are chosen (§5.4) |
| `SAM_GOV_API_KEY` | Backend | SAM.gov data service credential |
| `SAM_GOV_SEARCH_URL` | Backend | Documented Get Opportunities search URL. Default `https://api.sam.gov/opportunities/v2/search`. Switch to the `/prod/` path only after a keyed `200` (`DATA_SOURCES.md` D1) |
| `SAM_GOV_DAILY_REQUEST_CAP` | Backend | Application safeguard (default 10). Not SAM.gov's official quota |
| `SAM_GOV_SEARCH_LIMIT` | Backend | Max notices per search page (default 25, max 1000) |
| `SCAN_SCHEDULE_CRON` | Backend | Scheduled sweep cadence (§9) |
| `SCAN_MAX_CONCURRENT_SOURCES` | Backend | Politeness bound (§7.4). Max website requests in flight at once, across hosts |
| `SCAN_ORG_CONCURRENCY` | Backend | Max concurrent organization discovery runs inside one Scan All batch |
| `SCAN_MAX_PAGES_PER_ORGANIZATION` | Backend | Cap on approved pages validated and collected per organization per scan (default 10) |
| `SCAN_NEWS_ARTICLES_PER_HUB` | Backend | Articles collected from an organization's own news hub per scan (default 5, `DATA_SOURCES.md` §5.2b) |
| `SCAN_REFRESH_HOURS` | Backend | A page collected within this window is reused, not fetched again. Default 0: every Scan Now fetches live. Scheduled scans use 24 |
| `HTTP_TIMEOUT_SECONDS` | Backend | Read timeout for website requests (default 15; connect timeout 10) |
| `HTTP_USER_AGENT` | Backend | Honest client identification (§8.3) |
| `ENABLE_FALLBACK_DATASET` | Backend | Whether cached fallback may be read (§7.6) |
| `VITE_API_BASE_URL` | Frontend | Backend base URL, build-time |

> NEEDS VERIFICATION — whether SAM.gov requires an API key for the endpoints we intend to use, and
> under what quota. To be confirmed during source research in `DATA_SOURCES.md`.

---

## 17. Security

| Area | Control |
|---|---|
| Secrets | Environment variables only; never committed; `.env.example` holds placeholders |
| Database credentials | Held by the backend alone; never reach the browser (AD-05) |
| Transport | HTTPS everywhere, provided by the hosting platforms |
| Passwords | Stored and hashed by Clerk only. The application never receives or stores a password |
| Authorization | Server-side on every protected route (§11) |
| Input validation | Pydantic on every request body and query parameter |
| SQL injection | Parameterized queries through SQLAlchemy; no string-built SQL |
| CORS | Explicit origin allowlist from configuration |
| Outbound collection | Central enforcement of allowlist, robots, and rate limits (§8.3) |
| Error responses | Single envelope; internals never leaked |
| Logging | Secrets and tokens never logged (§14) |

### 17.1 Prompt injection from collected content

This deserves separate treatment because it is the security issue most specific to this product.
Content fetched from public web pages is fed into LLM prompts for extraction and for Advisor
answers. That content is **untrusted input**, and a page could contain text designed to manipulate
the model.

Controls: retrieved content is always delimited and labelled as untrusted data within the prompt,
never concatenated into the instruction section; system instructions state that content within the
data section is information to analyse and never an instruction to follow; extraction uses
structured output constrained to a schema, so a manipulated response fails validation rather than
propagating; and extracted entities are validated against the organization being scanned before
persistence. Detail belongs in `AI_RAG_DESIGN.md`; the architectural requirement is that no code
path concatenates raw source content into an instruction.

---

## 18. Rate limiting

Two distinct concerns, often confused.

**Outbound (the important one).** Per-source rate limits and politeness delays from the registry
(§8.1), applied in the shared fetcher via an in-process limiter. Since there is exactly one backend
process (AD-03), an in-process limiter is genuinely sufficient — this is a case where the monolith
removes the need for shared state in Redis. Limits are set conservatively below each source's
published limit.

**Inbound.** A modest per-user limit on scan triggers, so that a user cannot drive outbound traffic
past source limits by clicking repeatedly (`FR-SCAN-06`). The one-active-scan-per-organization
constraint (§7.3) already absorbs most of this; the inbound limit covers rapid triggering across
different organizations. Advisor questions are similarly bounded to control provider cost. Both are
enforced in a FastAPI dependency using in-process counters.

---

## 19. Source validation

Two distinct validations share a name and must not be conflated.

**Source access validation (before fetching).** Is this source in the approved registry? Is this
specific URL within its permitted scope? Do robots restrictions permit it? Are we within the rate
limit? A failure here means the fetch does not happen (§8.3).

**Source content validation (after fetching).** Did the response arrive with the expected status
and content type? Does the payload parse? Has the content changed since last retrieval, by content
hash? Unchanged content short-circuits the pipeline for that document, which is the cheapest
deduplication available. Unparseable content is recorded as a source failure with the raw payload
retained (§8.4), never discarded and never guessed at.

Source reliability ratings from `DATA_SOURCES.md` are attached to every document at collection
time and carried through to scoring, where reliability is a factor (`PRODUCT_PRD.md` §13.1).

---

## 20. Duplicate detection

Detecting that several sources describe one real-world event (`FR-SIG-07`) is done in ascending
order of cost, so that expensive comparison runs only on what survives.

| Tier | Method | Catches |
|---|---|---|
| 1 | Content hash of the normalized document | The identical document re-fetched |
| 2 | Canonical identifier match (e.g. a procurement notice identifier) where the source provides one | The same official record surfaced twice |
| 3 | Candidate narrowing: same organization, same signal type, overlapping time window | Reduces the comparison set before embedding work |
| 4 | Embedding similarity above a configured threshold within the narrowed set | The same event described in different words by different sources |

A match merges the incoming candidate into the existing signal: the signal moves to `merged` state,
and — critically — **every contributing source reference is retained on the surviving signal**
(`FR-SIG-07`, `FR-EV-04`). Merging must never discard evidence; a merge that loses a source
reference is a defect, because the multi-source evidence is precisely what makes a clustered signal
more credible than a single report.

The similarity threshold is configuration, not a literal, because it will need tuning against real
collected content.

> **Decided 2026-09-23.** Tier 4 uses the same embedding model as RAG. The initial cosine threshold
> is 0.86. Tune it later on real embeddings. Do not add a second embedding model.

---

## 21. Signal processing pipeline

**Owner:** Developer 3. Each stage reads persisted input and writes persisted output (AD-09).

```
[1] Collect      approved sources → raw documents (+URL, +timestamp, +reliability)
[2] Normalize    raw payload → normalized document (text, title, dates, metadata)
[3] Extract      normalized document → candidate signals, each with evidence
                 (AI, structured output, constrained to the seven types)
[4] Validate     candidate → validated | rejected(+reason)
[5] Deduplicate  validated → new signal | merged into existing (+source reference)
[6] Correlate    validated signals for an organization → correlated groups (+stated reason)
[7] Score        correlated group → opportunity + score + factor breakdown   [deterministic]
[8] Explain      score + breakdown → explanation, recommended action          [AI]
[9] Index        normalized documents → chunks + embeddings → pgvector
```

Architectural properties worth stating explicitly:

- **Stage 3 output is schema-constrained.** Extraction returns structured data validated against a
  Pydantic model. A response that does not conform is rejected rather than coerced, which is what
  prevents a malformed or manipulated model output from becoming a signal (§17.1).
- **Stage 3 cannot invent a type.** The type is constrained to the seven approved values
  (`FR-SIG-03`); content matching none is discarded, not assigned to the nearest fit.
- **Every candidate carries evidence from birth.** A candidate signal is created with references to
  the exact document and snippet that produced it. There is no later step that "adds" evidence, so
  `FR-SIG-02` and `FR-EV-07` cannot be violated by omission.
- **Stage 4 rejections persist with reasons** (`FR-SIG-06`), because the user is entitled to see
  what was discarded.
- **Stage 5 precedes stage 6.** Correlating before deduplicating would treat five reports of one
  event as five corroborating signals and inflate the score — the exact failure `AGENTS.md` §9
  warns against.
- **Stage 7 is deterministic and has no AI dependency.** Stage 8 receives the computed result and
  only writes prose.
- **Stage 9 is independent** of stages 3–8 and can run in parallel; the Advisor needs the index,
  the pipeline does not.

Ordering constraint: stages 1–5 are per-document; stages 6–8 are per-organization and run after all
of that organization's documents are processed in the run.

---

## 22. Opportunity scoring pipeline

**Owner:** Developer 2 (engine) with Developer 3 (explanation).

```
Correlated signal group
   → gather factor inputs   recency, source reliability, EdTech relevance,
                            related signal strength, procurement relevance
   → apply weights          from the single versioned weight definition (§15)
   → integer 0–100 + per-factor breakdown        [pure function, no I/O, no AI]
   → threshold check → create or update opportunity (FR-OPP-02, FR-OPP-06)
   → persist score + breakdown + weight version + previous score (FR-SCR-07)
   → AI explanation of the computed result       [AI, cannot alter the number]
```

**AD-12.** The scoring engine is a pure function: same inputs, same output (`FR-SCR-02`). It
performs no database or network access and has no reference to the AI service, so the prohibition
in `FR-SCR-01` is structural rather than a matter of discipline. Factor inputs are gathered by the
caller and passed in.

Score history is retained so a changed score remains explicable (`FR-OPP-13`), and each stored score
records which weight version produced it — otherwise a weight change during the build week would
silently invalidate every previous explanation.

The relevance factors (assessment/EdTech relevance, procurement relevance) are computed from signal
type, extracted metadata, and configured keyword/term sets rather than from a model call, keeping
the whole score reproducible.

---

## 23. AI Advisor pipeline

**Owner:** Developer 3. Synchronous, unlike ingestion, because a user is waiting.

```
Question + scope (organization or opportunity) + role check
   → Embed question
   → Retrieve from pgvector, FILTERED BY SCOPE           ← mandatory (§6.2)
   → Sufficiency gate → if insufficient: return "insufficient evidence", no LLM call
   → Assemble prompt: instructions | question | retrieved context marked as untrusted data
   → LLM call (bounded timeout)
   → Validate response references only supplied context
   → Resolve citations from chunk metadata → evidence items
   → Return answer + citations + interpretation labelling
```

Latency is bounded by a configured timeout; on timeout the user is told the Advisor is unavailable
rather than shown a partial or substituted answer (§13). Conversation context within a session is
held per `AI_RAG_DESIGN.md`; the architectural requirement is that follow-up questions retain scope
without the user restating the organization.

The Advisor reads only. It cannot create signals, opportunities, or scores.

---

## 24. Evidence and citation pipeline

Evidence is a first-class entity created at collection time, not assembled at display time.

```
Fetch → raw document persisted (URL, retrieval timestamp, source, reliability)
      → normalized document references the raw document
      → evidence item: source name, URL, published/observed date or explicit "unavailable",
        snippet, and its relationship to the conclusion            (FR-EV-01, FR-EV-02)
      → signals, correlations, score explanations, Advisor answers, and recommended actions
        all reference evidence items by identifier                  (FR-EV-03)
      → API responses include resolved evidence with the insight    (§12)
```

Two structural guarantees:

1. **No orphan insights.** The schema requires at least one evidence reference on any insight-
   bearing row, so `FR-EV-07` is enforced by the database rather than by every service remembering.
   `DATABASE_DESIGN.md` owns the constraint.
2. **No lossy merges.** Clustering adds source references; it never removes them (§20), so
   `FR-EV-04` holds through deduplication.

Citations resolve to the original public URL (`FR-EV-05`). The system stores no copy that it
presents as the source, and dates are never inferred (`FR-SIG-04`, `FR-EV-02`).

---

## 25. Deployment architecture

```
Frontend host (static)  ──HTTPS──▶  Backend host (single container, 1 worker)
                                          │
                                          ├──▶ Supabase PostgreSQL + pgvector
                                          ├──▶ Approved public sources (outbound)
                                          └──▶ LLM provider (outbound)
```

Three managed services, no infrastructure we operate. The frontend is a static build on a static
host. The backend is one container. The database is Supabase.

Deployment requirements that follow from earlier decisions:

- **Exactly one backend worker** (AD-03): more than one duplicates the scheduler.
- **The backend must not be scaled to zero / aggressively idled**, or scheduled scans will not run
  and in-flight scans will be interrupted. This constrains host selection (§27).
- **Memory headroom** depends on the §5.4 embedding decision and on whether Playwright is needed
  (§8.2); a browser binary plus an embedding model will not fit a minimal free tier.

Migrations are applied by Developer 2 before the corresponding backend deploy.

---

## 26. Local development architecture

```
Terminal 1   npm run dev       Vite dev server, proxying /api to localhost
Terminal 2   uvicorn --reload  FastAPI
Database     shared Supabase development project
```

**Decision: a shared Supabase development project rather than local PostgreSQL in Docker.** It
removes Docker and the pgvector extension setup from every developer's first day, and it means all
three developers see the same data while integrating — which matters more than isolation over five
days. The trade-off is accepted: developers can disrupt each other's data, and the schema is shared,
so migrations are coordinated through Developer 2.

Local specifics: each developer has their own `.env` from `.env.example`; the scheduler is disabled
locally by default so nobody's laptop makes unexpected outbound requests to public sources; scans
are triggered manually during development.

> **Decided 2026-09-23.** One shared Supabase project for the team and the demo. Do not create a
> second project per developer.

---

## 27. Production / hackathon architecture

For this project, "production" is the demonstration environment. Two environments only:
development (§26) and demo/production. No staging — a third environment would consume time that
should go into the MVP chain.

> **NEEDS DECISION — hosting targets.** Selection criteria, in priority order, derived from the
> decisions above:
>
> 1. Backend host must support a long-running always-on container that is not idled to zero (§25),
>   because the scheduler and in-process background scans depend on it.
> 2. Backend host memory must accommodate the embedding decision (§5.4) and Playwright if required.
> 3. Both hosts must support environment-variable configuration and deploy from the repository.
> 4. Free or low-cost tier for a one-week project.
>
> Criterion 1 is the sharp one: several popular free tiers sleep idle applications, which would
> silently break scheduled scanning (`FR-SCHED-01`) and interrupt scans. This must be verified
> against the chosen host before Day 1 of implementation, not discovered on demo day.

Demo-day resilience: the demo database is separate from development; the cached fallback dataset
covers the demonstration organizations (`FR-FB-06`); source failures surface honestly and the demo
script accommodates them (`PRODUCT_PRD.md` §29 contingency).

---

## 28. Team development boundaries

### 28.1 Ownership

| Boundary | Owner | Owns | Does not touch |
|---|---|---|---|
| Frontend | Developer 1 | `frontend/` entirely | Backend code |
| Backend API & data | Developer 2 | `app/api`, `app/services` (API-facing), `app/repositories`, `app/schemas`, `app/scoring`, migrations, `AUTHENTICATION.md`, `DATABASE_DESIGN.md`, `API_CONTRACT.md` | Ingestion internals, AI internals, frontend |
| AI / RAG / Ingestion | Developer 3 | `app/ingestion`, `app/ai`, `app/scheduler`, pipeline services, `AI_RAG_DESIGN.md`, `DATA_SOURCES.md` | API routes, frontend, schema changes without Developer 2 |

The pipeline-stage structure (AD-09) is what makes the backend split workable: Developers 2 and 3
share a codebase but touch different directories, meeting at the repository layer and the scan run
record.

### 28.2 The three contracts

Everything crossing a boundary crosses through a document, never through reading someone's code.

| Contract | Between | Document |
|---|---|---|
| HTTP API | Developer 1 ↔ Developer 2 | `API_CONTRACT.md` |
| Database schema | Developer 2 ↔ Developer 3 | `DATABASE_DESIGN.md` |
| AI service interface | Developer 3 ↔ Developers 1 & 2 | `AI_RAG_DESIGN.md`, surfaced via `API_CONTRACT.md` |

A contract change is agreed and documented **before** either side implements against it, because
both sides are building simultaneously.

### 28.3 Unblocking parallel work

The dependency risk is that Developer 1 cannot build screens until endpoints exist, and Developer 3
cannot produce signals until the schema exists. Two mechanisms:

1. **Contract and schema first.** `API_CONTRACT.md` and `DATABASE_DESIGN.md` are written and agreed
   before feature implementation begins. Sequencing belongs to `IMPLEMENTATION_PLAN.md`.
2. **Contract-shaped stub endpoints.** Developer 2 delivers routes that return contract-shaped
   responses early, so Developer 1 can build real screens against real response shapes.

> **Guardrail on stubs, stated explicitly because it touches a core product rule.** Stub responses
> are development scaffolding. They must live behind a configuration flag that is off outside local
> development, must be obviously synthetic, and must be gone before the demonstration. They are not
> the "cached fallback dataset" (§7.6), which is real previously-retrieved content. Nothing
> synthetic may ever reach a user-facing surface, per `FR-DATA-01` and the truthfulness rules in
> `AGENTS.md` §7.

### 28.4 Integration points

The riskiest moments are where boundaries meet: first real signal written by ingestion and read by
the API; first opportunity rendered end to end in the UI; first Advisor answer with citations
rendered; first Scan Now run driven from the UI through to visible results. Each should be
scheduled as an explicit integration checkpoint in `IMPLEMENTATION_PLAN.md`, not left to the final
day.

---

## 29. Architecture decisions summary

| ID | Decision | Rationale | Main trade-off |
|---|---|---|---|
| AD-01 | Single FastAPI process hosting API, scheduler, ingestion, and AI | Three developers, five days, small data volume | Process becomes stateful; drives AD-03 |
| AD-02 | Async scans as in-process background tasks with DB-backed run state and client polling | Meets `FR-SCAN-03`/`FR-SCAN-08` without Celery or Redis | Restart interrupts in-flight runs; handled by startup reconciliation |
| AD-03 | Exactly one backend worker | In-process APScheduler must be singular | No horizontal scaling; acceptable at this volume |
| AD-04 | One-active-scan-per-organization enforced in the database | Survives restarts; no distributed lock needed | — |
| AD-05 | Direct PostgreSQL connection to Supabase; app-layer authorization | pgvector and joins need real SQL | RLS not used; auth enforcement is our responsibility |
| AD-06 | REST, versioned, offset pagination, one error envelope | Simplest thing that meets the contract need | Offset pagination degrades at large volume; not reached here |
| AD-07 | Narrow LLM adapter; no vendor SDK outside adapters | Provider swappable by configuration | Cannot use provider-specific features in business logic |
| AD-08 | Open-source embeddings behind the same abstraction | Cost and portability | Deployment option unresolved (§5.4) |
| AD-09 | Every pipeline stage persists its output | Inspectable, resumable, divisible between developers | More writes |
| AD-10 | Central source registry and shared fetcher enforcing compliance | Compliance cannot be forgotten in a new collector | All collection must go through one path |
| AD-11 | Evidence created at collection time; insights reference it | `FR-EV-07` enforceable in the schema | — |
| AD-12 | Scoring engine is a pure function with no AI dependency | `FR-SCR-01`/`FR-SCR-02` structurally guaranteed | Relevance factors must be computable without a model |
| AD-13 | TanStack Query owns server state; Zustand owns UI state only | Prevents stale mirrored data | — |
| AD-14 | Contract-first with flagged, non-shipping stub endpoints | Unblocks parallel work | Requires discipline; guarded by §28.3 |
| AD-15 | Clerk authenticates; FastAPI authorizes `SALES_REP` / `SALES_MANAGER` | Faster than building login for a one-week build; roles stay in our database (AD-05) | A third-party identity dependency; a Clerk outage blocks sign-in |

**Rejected, and why:** Redis (no shared state needed with one process, §18); Celery or RQ (AD-02
covers async work); Kafka (no event-streaming requirement); Kubernetes (one container); separate
vector database (pgvector co-located with relational data is required for citation joins,
§4.4); microservices (three developers, one week); WebSockets (polling is sufficient for scan
progress, §2.4); server-side rendering (internal tool, no SEO or first-paint requirement).

---

## 30. Component dependency map

```
Frontend ──depends on──▶ API contract ──implemented by──▶ API routes
                                                             │
                                          ┌──────────────────┼──────────────────┐
                                          ▼                  ▼                  ▼
                                    Services          Scoring engine      AI service
                                          │             (no deps)              │
                                          ▼                                    ▼
                                   Repositories ◀──────────────────── LLM adapter
                                          │                                    │
                                          ▼                                    ▼
                               PostgreSQL + pgvector              Configurable provider
                                          ▲
                                          │
                        Ingestion ◀── Source registry ◀── DATA_SOURCES.md
                             ▲
                        Scheduler
```

| Component | Depends on | Blocks |
|---|---|---|
| Frontend features | API contract, then real endpoints | Nothing |
| API routes | Schemas, services, auth dependency | Frontend |
| Services | Repositories, scoring engine, AI service | API routes |
| Repositories | Database schema | Services, ingestion, AI |
| Database schema | `DATABASE_DESIGN.md` | Almost everything — write it first |
| Scoring engine | Weight definition only | Opportunity generation |
| AI service | Provider adapter, configuration | Extraction, explanation, Advisor |
| RAG retrieval | Embedding model choice, pgvector schema | Advisor |
| Ingestion | Source registry, `DATA_SOURCES.md`, repositories | Signals, therefore everything downstream |
| Scheduler | Scan orchestrator | Scheduled scanning only |

**Critical path.** `DATABASE_DESIGN.md` and `API_CONTRACT.md` gate the most parallel work; the
embedding model decision (§5.4) gates the schema; the hosting decision (§27) gates deployment and
should be settled before implementation begins. Sequencing is owned by `IMPLEMENTATION_PLAN.md`.

---

## 31. Performance and limits

| Concern | Expectation |
|---|---|
| Read endpoints | Sub-second from indexed PostgreSQL at this volume |
| Advisor answer | Dominated by retrieval plus one bounded LLM call |
| Single-organization scan | Dominated by source latency and per-source politeness delays; measure early (`PRODUCT_PRD.md` §21 open question) |
| Concurrent users | A small internal team; no load-balancing requirement |
| Caching | None beyond TanStack Query on the client. At this data volume a cache layer would add infrastructure and staleness bugs for no measurable gain |

---

## 32. Fallback and resilience summary

| Failure | Behaviour |
|---|---|
| One public source unavailable | Recorded as a failed source on the run; other sources continue; run completes as partial (`FR-SCAN-05`) |
| All sources unavailable | Run completes as failed with reasons; existing stored data still serves the UI |
| LLM provider unavailable | Affected insight absent and labelled unavailable; the score still computes (AD-12); nothing fabricated |
| Database unavailable | The application is down; no offline mode. Accepted at this scale |
| Backend restart mid-scan | Interrupted runs reconciled at startup (§7.2) |
| Demo-day source outage | Cached fallback covers demonstration organizations, visibly labelled, with the live failure still reported (§7.6) |

---

## Open questions

| # | Question | Section | Blocks | Recommendation |
|---|---|---|---|---|
| T1 | Embedding model deployment: in-process or hosted API? | §5.4 | — | **Decided 2026-09-25.** Hosted Azure OpenAI `text-embedding-3-small`, width 1536; chat `interns-gpt-4.1` |
| T2 | Backend and frontend hosting targets | §27 | Deployment | Must be a backend host that does not idle to zero |
| T3 | ~~Supabase Auth or FastAPI-native?~~ | §10 | — | **Decided:** Clerk authenticates; FastAPI authorizes (AD-15) |
| T4 | LLM provider selection | §5.1 | — | **Decided 2026-09-23.** Provider stays pending. Business logic uses the LLM adapter only |
| T5 | Duplicate-detection similarity threshold, and whether tier 4 reuses the RAG embedding model | §20 | — | **Decided 2026-09-23.** Same model as RAG. Initial threshold 0.86, configurable |
| T6 | Shared development database or one Supabase project per developer? | §26 | — | **Decided 2026-09-23.** One shared Supabase project for the team and the demo |
| T7 | Does SAM.gov require an API key for the endpoints we need, and at what quota? | §16 | Ingestion | Key is required. Official quota is still unverified. The application cap is in `DATA_SOURCES.md` D2 |
| T8 | Is Playwright required for any approved source? | §8.2 | — | **Decided 2026-09-23.** Do not use Playwright unless a selected official page requires JavaScript |
