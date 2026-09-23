# Implementation Plan

> **Status:** DRAFT — awaiting approval
> **Version:** 0.3
> **Date:** 2026-09-23
> **Depends on:** every approved document in `docs/` and `AGENTS.md`
> **Primary author:** Lead, agreed with all three developers

## Purpose

One week, three developers, one workflow working on real public data:

Organization → public data → signal → validation → correlation → opportunity → score → evidence → AI Advisor.

No new libraries, no new product rules, no test files. Validation in this plan is manual. Schema, API shapes, and prompts stay inside the documents already written. A change to a contract is written down before code follows it.

Assumed calendar: five working days. Phases 0 through 4 are the week. Phase 5 is what happens only after Phase 4 is done.

---

## 1. What to build, and what to cut

### Must have

If this list is incomplete, the demo does not happen. Do not start a should-have while a must-have is broken.

| # | Outcome | Where it is specified |
|---|---|---|
| M1 | Clerk sign-in, sign-out, `GET /api/v1/me`, both roles, unprovisioned user gets 403 | `AUTHENTICATION.md`, `API_CONTRACT.md` §2 |
| M2 | At least two tracked organizations, chosen for real public activity, with validated website rows only after `DATA_SOURCES.md` §5.2 | `PRODUCT_PRD.md` §6, `DATA_SOURCES.md` §5.3 |
| M3 | SAM.gov Get Opportunities fetch stored as a document, inside the application cap of 10 requests per 24 hours. That cap is not SAM.gov's official quota | `DATA_SOURCES.md` §2 |
| M4 | One official website page fetched the same way | `DATA_SOURCES.md` §5 |
| M5 | Extraction, validation, evidence with a verbatim snippet and a stored URL | `AI_RAG_DESIGN.md` §§3–5 and §12 |
| M6 | Dedup tiers 1–3 so the same notice is not five signals | `AI_RAG_DESIGN.md` §6 |
| M7 | Correlation of at least two signal types, one potential opportunity, rules score `v1` with five factors | `AI_RAG_DESIGN.md` §§8–10 |
| M8 | Score explanation when the model is up. If it is down, the number still shows and the explanation says unavailable | `AI_RAG_DESIGN.md` §11 |
| M9 | Opportunity and signal screens show evidence and the four layers | `UI_UX_DESIGN.md` §§18–21 and §27 |
| M10 | Scan Now from the organization page, progress by polling, failure of one source does not kill the others | `API_CONTRACT.md` §9 |
| M11 | Advisor answers from retrieved chunks, cites evidence, and says insufficient evidence when retrieval is empty | `AI_RAG_DESIGN.md` §§23 and 28 |

### Should have

Start these only after M1–M11 work on one organization.

| # | Outcome | Cut when |
|---|---|---|
| S1 | Dashboard metrics, top opportunities, recent signals | The killer path is still failing on day 5 |
| S2 | List filters and organization search | Same |
| S3 | IPEDS reference band for postsecondary orgs | The file dictionary is not verified, or day 5 is already full |
| S4 | USAspending for a recipient that resolves to one entity | Lookup is ambiguous or SAM quota is the priority |
| S5 | A third, fourth, or fifth official website | Two sites already prove a second source |
| S6 | Score history sparkline | The latest score and `previous_value` already return from the API |
| S7 | Scheduled daily scan | Scan Now already runs the same pipeline |
| S8 | Dedup tier 4 (embedding similarity) | The embedding model is not chosen, or tiers 1–3 already merge the demo notices |

### Nice to have

Do not start these until the should-have list in progress is actually done.

| # | Outcome |
|---|---|
| N1 | Scan All batch panel |
| N2 | Competitor/vendor briefing panel |
| N3 | Signal volume chart and score-distribution chart |
| N4 | Organization timeline tab |
| N5 | Playwright for a JavaScript-only page |
| N6 | Approximate vector index |

### If the week slips, cut in this order

Cut from the top of this list first. Never cut evidence, the rules score, or the insufficient-evidence path to save time.

1. S7 scheduled scan. Scan Now is the demo. This is the first feature dropped if time is limited
2. N1–N6
3. S6 sparkline, S5 extra websites, S4 USAspending, S3 IPEDS. IPEDS and USAspending are deferred for the first demo
4. S1 dashboard and S2 filters
5. S8 tier-4 dedup
6. Do not cut M1–M11. If M3 is blocked by the application SAM.gov cap, demo from documents already stored and label them cached. Do not invent notices.

---

## 2. Ownership

| Developer | Writes | Does not write |
|---|---|---|
| 1 Frontend | `frontend/` against `UI_UX_DESIGN.md` and `API_CONTRACT.md` | FastAPI, collectors, prompts |
| 2 Backend | Schema migration, repositories, routes, scoring engine | Prompt text, collectors, page layout |
| 3 AI and data | `app/ingestion`, `app/ai`, `app/scheduler`, prompt files, source rows | React, route handlers |

Shared files (`docs/`, `AGENTS.md`) change only through a short review. Feature branch, then pull request. No direct commits to the shared branch.

Developer 2 may ship contract-shaped empty lists on day 1 so Developer 1 can render real screens. Those responses come from the database, including an empty database. They are not hand-written fake organizations. Nothing synthetic is seeded as a signal, score, or evidence row.

---

## 3. Phase 0 — Unblock the week

**When:** morning of day 1. Stop other feature work until this phase is done.

### Objective

Remove the decisions and accounts that would otherwise stall the pipeline.

### Frontend tasks

- Confirm `VITE_CLERK_PUBLISHABLE_KEY` and `VITE_API_BASE_URL` load from env.
- Do not build screens yet.

### Backend tasks

- Create the Supabase project and the empty schema from `DATABASE_DESIGN.md`. Leave the vector column off until the embedding width is known, or add it in the same morning if the model is already chosen.
- Confirm Clerk verification with `CLERK_SECRET_KEY` against a throwaway token.
- Set Clerk public metadata `role` to `SALES_REP` and `SALES_MANAGER` on the two demo users. The first `/api/v1/me` call syncs each into `app_users`.

### AI/data tasks

- Confirm which SAM.gov production path returns 200 (`DATA_SOURCES.md` D1). The official quota (D2) is still unverified. Until then the application stops at 10 requests per 24 hours. That cap is not SAM.gov's official quota.
- Spend at most two of those requests today: one search, one description only if the search row has no usable title snippet.
- With a human, pick two organizations that have something public to show. Validate each official URL with `DATA_SOURCES.md` §5.2 and add the rows to §5.3 before any website fetch.

### Dependencies

Approved docs. A Clerk development instance. A Supabase database. A SAM.gov API key. A hosting choice if embeddings will run in-process (`TECHNICAL_PRD.md` T1 and T2).

### Expected result

Both developers can sign in as provisioned users. One SAM.gov response is stored or the failure is written down with the status code. Two website URLs are either approved in `DATA_SOURCES.md` or explicitly rejected.

### Manual validation

- Call `GET /api/v1/health` with no token. Expect `200` and `{"status":"ok"}`.
- Call `GET /api/v1/me` with no token. Expect `401` `AUTH_MISSING`.
- Call it with the sales-rep Clerk token. Expect that role. Repeat for the manager.
- Call it with a Clerk user who has no `publicMetadata.role`. Expect `403` `USER_NOT_PROVISIONED`.

### Integration point

Developer 2 and Developer 3 agree the first `documents` insert shape. Developer 1 does not need data yet.

### Definition of done

Health and `/me` behave as above. The SAM.gov path and quota are written into the team's notes. `DATA_SOURCES.md` §5.3 has two approved rows or a written reason a candidate failed §5.2. No application feature beyond this.

---

## 4. Phase 1 — Shell and tracked organizations

**When:** rest of day 1.

### Objective

A signed-in user can open the app and see the real tracked organizations, or an honest empty state.

### Frontend tasks

- Vite app, Tailwind tokens from `UI_UX_DESIGN.md` §2.7, `lucide-react` icons.
- Clerk provider, `/login`, redirect when signed out, sign out clears the query cache.
- App shell: sidebar, header, page title. No dashboard charts.
- Organizations list from `GET /api/v1/organizations`, including search box wired to `q`.
- Loading, empty, and error states for that list.

### Backend tasks

- `GET /api/v1/me`, `GET /api/v1/health`, `GET /api/v1/organizations`, `GET /api/v1/organizations/{id}`.
- Seed only the organization rows the human approved in Phase 0. No signals.

### AI/data tasks

- Persist the Phase 0 SAM.gov payload into `documents` if that was not finished in the morning.
- Do not run extraction yet.
- If the embedding model is chosen, record its width for Developer 2. If it is not chosen, say so and leave dedup tier 4 and the Advisor index for Phase 4.

### Dependencies

Phase 0.

### Expected result

Both roles see the same organization list. An unknown person with a Clerk account cannot.

### Manual validation

- Sign in as each role. The same organizations appear.
- Search with one character. The list stays empty and does not error (`API_CONTRACT.md` §6.1).
- Search with a real name substring. That organization remains.
- Open a bad UUID. The API returns 404. The UI shows the not-found state.
- Sign out. A refresh of an app route lands on `/login`.

### Integration point

First real API list on a real screen. This is the first frontend–backend join.

### Definition of done

The checks above pass on a machine that is not the author's. Organization names on screen match the database. No placeholder organization was typed into the UI.

---

## 5. Phase 2 — Public data to a validated signal

**When:** day 2.

### Objective

A stored document becomes validated signals with evidence, or a rejected signal with a reason. The UI can show both.

### Frontend tasks

- Organization profile header from `GET /api/v1/organizations/{id}` without IPEDS required. If `ipeds` is null, omit the reference band.
- Signals tab: `GET /api/v1/signals?organization_id=`.
- Signal detail: type, state, date or "date unavailable", every evidence item, rejection reason when rejected.
- Do not build the opportunity page yet.

### Backend tasks

- Tables and routes for documents, signals, evidence if the Phase 0 migration did not include them.
- `GET /api/v1/signals` and `GET /api/v1/signals/{id}` matching the contract, including the default of validated-only and an explicit `state=rejected`.

### AI/data tasks

- Normalizer for the SAM.gov JSON already stored, and for one fetched official page.
- `extract_signals_v1` with schema validation.
- Verbatim snippet check, URL check, seven-type check, organization check.
- Write `signals`, `evidence`, and `signal_state_events`.
- Rejected rows stay in the database.
- One website fetch only, of an allowlisted URL, after `robots.txt`. Wait at least five seconds. Do not crawl.

### Dependencies

Phase 1 organizations. Phase 0 documents. SAM.gov quota: do not run a new search if today's two requests were already spent. Reuse the stored document.

### Expected result

At least one validated signal with evidence, or a written finding that this organization's stored page produced only rejections. Rejections are visible and explained. An empty extraction is a successful outcome, not a fake signal.

### Manual validation

- Open the signal. The snippet text appears in the stored document body.
- The evidence URL does not contain `api_key`.
- A signal whose snippet was altered in a dry run is rejected with `SNIPPET_NOT_IN_SOURCE` and does not show as validated.
- Date is the source date or "date unavailable". It is not today's date unless the source said today.
- The other role sees the same signal.

### Integration point

Developer 3's writer and Developer 2's reader use the same columns. Developer 1 renders that payload without renaming fields.

### Definition of done

The manual checks pass for every validated signal created today. No eighth signal type exists. IPEDS was not turned into a signal.

---

## 6. Phase 3 — Correlation, score, opportunity

**When:** day 3.

### Objective

Two validated signals of different types become one potential opportunity with a reproducible score and visible evidence.

### Frontend tasks

- Opportunity list and detail in the order required by `UI_UX_DESIGN.md` §27: facts, then score, then correlation, then recommended action.
- `ScoreDisplay` requires value, band, factors, and explanation status. Do not ship a badge that shows only the number.
- Evidence rail or drawer with every evidence row from the detail payload.
- If there is only one signal type so far, show the signals and an empty opportunity state. Do not loosen the two-type rule.

### Backend tasks

- Scoring function from `AI_RAG_DESIGN.md` §10, weights `v1`, no AI import.
- `opportunities`, `opportunity_signals`, `opportunity_scores`.
- `GET /api/v1/opportunities` and `GET /api/v1/opportunities/{id}`.
- One opportunity row per organization.

### AI/data tasks

- Dedup tiers 1–3 before correlation.
- Correlation and the working generation rule in `AI_RAG_DESIGN.md` §9 (two types, one within 90 days, score at least 50). That rule is still marked unapproved in the product doc. Do not invent a different threshold.
- Persist correlation text as interpretation.
- Call the score explanation after the number is stored. On failure, leave `explanation_status` as `unavailable`.
- Recommendation only when it cites a real evidence id. Otherwise leave it null.

### Dependencies

Phase 2 validated signals. If both signals are the same type, Developer 3 fetches the second allowlisted page or reuses a second stored document. Do not lower the rule to one signal.

### Expected result

One opportunity whose factor points sum to `value`, whose band matches `v1`, and whose evidence opens the stored URLs.

### Manual validation

- Recompute the five factors by hand from the signal types, dates, and source labels. The total matches.
- Run the score function twice. The same inputs return the same number.
- The explanation, if present, quotes that same number. If it quotes another number, it is not stored.
- Correlation text does not say an RFP will be issued.
- A single-signal organization has zero opportunities.
- Merging two copies of the same notice does not increase related-signal strength.

### Integration point

First full intelligence object on screen: score, factors, signals, evidence. This is the second join, and the one the demo depends on.

### Definition of done

The hand recomputation matches. Evidence links from the UI do not 500 and do not include the SAM.gov key. The empty and insufficient cases are visible, not hidden.

---

## 7. Phase 4 — Scan Now and the Advisor

**When:** day 4.

### Objective

From the organization page, a person can run Scan Now and see stages, then ask the Advisor something the evidence can answer and something it cannot.

### Frontend tasks

- Scan Now button, stage stepper, per-source failure row, result summary (`UI_UX_DESIGN.md` §§32–33).
- Poll `GET /api/v1/scans/{scan_id}` about every 2 seconds until a terminal status. Stop polling then.
- Advisor panel on the organization and on the opportunity. Scope stays visible.
- Render `answered`, `insufficient_evidence`, `out_of_scope`, and `unavailable` as designed. Insufficient evidence is not a red error.

### Backend tasks

- `POST /api/v1/organizations/{id}/scans` returns 202, or 200 with `joined_existing` true.
- `GET /api/v1/scans/{id}` returns stage, source results, and change counts.
- Advisor routes `POST /api/v1/advisor/questions` and `GET /api/v1/advisor/sessions/{id}`.
- Rate-limit a burst of scan posts and Advisor posts with 429 and `retry_after_seconds`.
- Restart behavior: a scan left `running` becomes `interrupted` on process start.

### AI/data tasks

- Scan orchestrator calls the same extract, validate, dedupe, correlate, and score path as the manual scripts from days 2 and 3.
- One failed source is recorded. The other source still runs.
- Chunk and embed documents only if the model and vector width exist. If they do not, ship the Advisor as `unavailable` with the reason recorded, and do not block the score.
- If embeddings exist: sufficiency gate, then `advisor_answer_v1`. Citations must be retrieved chunk ids. Drop unknown ids. If none remain, return `insufficient_evidence` and do not call the model again.
- Filter retrieval by that organization's id before similarity.

### Dependencies

Phase 3. Embedding decision for the Advisor half. SAM.gov quota: Scan Now must not fire a new search if the daily budget is spent. It still refreshes the website page and reuses stored SAM.gov documents.

### Expected result

A scan started in the UI finishes or fails visibly. The Advisor either cites a stored snippet or states that evidence is insufficient. A question about an unrelated country is `out_of_scope`.

### Manual validation

- Start Scan Now. The stage label changes. The page stays usable.
- Start it again while running. The same `scan_id` comes back. A second run does not appear in the database.
- Force a website timeout or a bad URL in a dry run. SAM.gov or the other source still completes. The summary names the failure.
- Ask why the score is what it is. The answer uses the stored number.
- Ask for a vendor that is not in the snippets. The answer does not name one, or it returns insufficient evidence.
- Ask what the weather will be. The answer is out of scope and has no evidence list.
- Sign in as the other role and open the same opportunity. Same score and same evidence.

### Integration point

Third join: the UI drives the pipeline and the Advisor. Do this on day 4, not on the morning of the demo.

### Definition of done

The checks above pass once on the demo database, not only on a laptop database. Cached rows, if any were used because a source failed, show `data_origin` `cached`.

---

## 8. Phase 5 — Demo hardening, then extras

**When:** day 5. Extras start only after the definition of done below.

### Objective

Run the demo script once on the demo environment. Then, and only then, pick up should-have work in the cut order's reverse.

### Frontend tasks

- Fix the breaks found in the demo rehearsal. Spacing and color tokens only where a screen is wrong or confusing.
- If time remains: dashboard from `GET /api/v1/dashboard`, then filters already specified on the list endpoints.
- Do not add Scan All, charts, or a competitor panel unless S1 and S2 are done.

### Backend tasks

- Demo Clerk instance and demo database, separate from daily development.
- `GET /api/v1/dashboard` only if the frontend is ready to use it.
- Scheduled job only after Scan Now is stable. Same function, not a second pipeline.

### AI/data tasks

- Rehearse with the SAM.gov quota in mind. Prefer stored documents over a live search during the second rehearsal.
- IPEDS load only if the data dictionary for that year has been read (`DATA_SOURCES.md` D5).
- USAspending only for an organization that resolves to one recipient. If autocomplete returns several, store nothing and move on.
- Write the cached snapshot for the demo organizations from real rows already fetched. Do not type a notice.

### Dependencies

Phase 4 passed on the demo environment.

### Expected result

A person who was not the author can follow `PRODUCT_PRD.md` §29 steps 1 through 11. Step 12, the manager login, shows the same evidence. Dashboard and charts may be absent.

### Manual validation

Walk this script and write pass or fail. Do not skip step 10.

1. Sign in as `SALES_REP`.
2. Open an organization that has signals.
3. Open a signal. Count the evidence rows against the database.
4. Run Scan Now or show the latest finished scan if the quota is spent. The screen must say which.
5. Open the potential opportunity. Read the score, the five factors, and the correlation text aloud.
6. Open each evidence URL that claims to be public. Confirm the snippet is on that page, or that the record still says the deep link is unverified and shows the official site root plus the source id.
7. Ask the Advisor why the score is what it is.
8. Ask a question the corpus cannot answer. Expect insufficient evidence.
9. Sign in as `SALES_MANAGER`. Open the same opportunity. The score matches.

### Integration point

Full rehearsal. Defects are fixed in the owning developer's area and rechecked. No drive-by edits in another developer's folders.

### Definition of done

Steps 1–9 pass. Any failed source is visible. No sentence on screen says an RFP will definitely happen. No score is missing its factor list.

---

## 9. What each person does when blocked

| Block | What to do | What not to do |
|---|---|---|
| SAM.gov quota spent | Use the stored document. Build validation and the UI | Scrape sam.gov. Invent a notice |
| Embedding model still unknown | Finish score, evidence, and Scan Now | Invent a vector width |
| Website fails `robots.txt` | Mark it skipped. Use the other approved site | Change user agent to sneak past |
| Opportunity rule yields nothing | Show the empty state. Fetch the second real source | Create an opportunity from one signal |
| Clerk or database down | Stop and fix Phase 0 | Fake `/me` in the client |
| Contract field missing | Add it to `API_CONTRACT.md` first, then both sides | Add a quiet JSON field |

---

## 10. Daily join

Fifteen minutes at the start of each day. Only blockers and the cut list.

| Day | Must be true by the end |
|---|---|
| 1 | Phase 0 and Phase 1 |
| 2 | Phase 2 |
| 3 | Phase 3 |
| 4 | Phase 4 |
| 5 | Phase 5 rehearsal |

If a day slips, the next morning's first act is to cut the next should-have, not to start it.

---

## Open implementation decisions

These six items stay open on purpose. Resolve them during implementation and validation. Closing one of them must not change the application architecture, add a dependency, or hard-code a name, endpoint, model, host, or performance target.

1. **Initial organizations.** Select the first two TARGET organizations only after validating real evidence from SAM.gov or the organization's official website. Do not hard-code organization names into business logic. Store them as database records (`DATA_SOURCES.md` §5.3).
2. **SAM.gov production endpoint.** Validate the documented production paths with the issued API key. Use only the path that returns a successful response. Do not invent or assume an endpoint (`DATA_SOURCES.md` D1).
3. **SAM.gov API quota.** The 10-request daily cap is an MVP safeguard. Verify the quota on the issued key before raising or changing that cap. Do not describe the temporary cap as SAM.gov's official quota (`DATA_SOURCES.md` D2).
4. **LLM and embedding model.** Both stay configurable. Call them only through the provider and embedding adapters. Choosing a model later must not require a change to the core application architecture. Leave the vector width unset until the embedding model is chosen.
5. **Hosting.** The hosting target stays open. Do not add hosting-specific architecture until that target is selected.
6. **Live scan duration.** Measure the real end-to-end scan during implementation. Do not set an artificial performance target before that measurement exists (`PRODUCT_PRD.md` Q8).

Already settled, and not reopened by the list above: store only fetched URLs, and create a potential opportunity only at two validated signals of different types, one within 90 days, and a rules score of 50 or higher.
