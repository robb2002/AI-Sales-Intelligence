# AI Sales Intelligence System — Excelsoft

Authoritative orientation document for every human and AI agent working in this repository.
Read this before writing any code, document, or plan.

**Current project stage: APPROVED DOCUMENTATION.**
The PRDs, design, contract, schema, and implementation plan are the source of truth.
Do not implement a phase until that phase is explicitly requested.
Do not invent requirements, sources, endpoints, or schema.
Do not create test files unless explicitly requested.

---

## 1. What we are building

An AI-powered Sales Intelligence platform for Excelsoft's **US sales team**.

The platform continuously observes **publicly available information** about US education
organizations and surfaces **signals** that may indicate changing needs, procurement activity,
technology initiatives, funding, leadership changes, strategic direction, vendor activity, or
contract activity.

### What this product is NOT

It does **not** predict that an RFP will definitely happen. It does not claim certainty about
future procurement. It surfaces publicly observable evidence and helps a human decide where to
spend research and sales attention.

### The four-way distinction (non-negotiable)

Every insight the system presents must clearly separate:

| Layer | Meaning |
|---|---|
| Observed fact | What a public source actually stated, with a citation |
| AI interpretation | What the system infers from those facts |
| Potential opportunity | A correlated set of signals that may be worth pursuing |
| Recommended research/action | What a human should do next |

Collapsing these layers — presenting interpretation as fact, or an opportunity as a certainty —
is a product defect, not a styling preference.

---

## 2. Users

**Sales Representative** — researches organizations, views signals, understands potential
opportunities, questions the AI Sales Advisor, reviews evidence, decides what research or action
to take.

**Sales Manager** — monitors overall opportunities, reviews signal activity and trends, reviews
competitor/vendor intelligence, and identifies where sales attention may be required.

## 3. Target market

United States only. Target organizations are universities, colleges, K-12 school districts, and
US public-sector education organizations.

---

## 4. Core product concept

Detect → Connect → Understand → Prioritize → Provide Evidence → Suggest Next Research/Action

The pipeline:

```
Public source
  → New information
  → Signal extraction
  → Duplicate detection
  → Signal validation
  → Related signal detection
  → Signal correlation
  → Potential opportunity
  → Hybrid opportunity score
  → Evidence
  → AI Sales Advisor
  → Recommended next research/action
```

A single weak signal is never treated as a guaranteed opportunity.

---

## 5. The seven core signal types

1. **Procurement** — RFP, RFI, pre-solicitation, solicitation, contract activity, procurement notices
2. **Technology initiatives** — assessment modernization, digital transformation, LMS/testing modernization, technology platform initiatives
3. **Leadership changes** — CIO, assessment leadership, technology leadership, relevant procurement/education leadership
4. **Funding/budget** — public funding, grants, budget changes, funding announcements
5. **Strategic announcements** — new programs, strategic initiatives, online learning initiatives, assessment initiatives
6. **Competitor/vendor changes** — vendor adoption, platform changes, technology partnerships, competitor/vendor announcements
7. **Contract/renewal** — contract activity, renewal indications, vendor agreements, expiration/renewal-related public information

This taxonomy is closed. Additional core signal categories require explicit approval.

---

## 6. Data strategy

Real public information is the **primary** data source. Mock data is never the primary product
data. A small cached/demo fallback dataset may exist for one reason only: to keep a live
demonstration from failing when a public source is temporarily unavailable. It must be visibly
labelled as cached/fallback wherever it is displayed.

Collection is hybrid: official APIs, public feeds/data services, permitted public web collection,
and selected official organization websites.

**Hard limits.** Do not crawl the internet at large. Do not bypass authentication, access
controls, robots restrictions, rate limits, paywalls, CAPTCHAs, or any other technical
restriction. Do not invent sources.

Authoritative sources identified so far:

| Source | Role |
|---|---|
| [SAM.gov](https://sam.gov/opportunities) | Federal contract opportunities, procurement/pre-solicitation/solicitation/award/sole-source notices |
| [USAspending.gov](https://api.usaspending.gov/) | Federal award and spending information, organization/agency/recipient context |
| [NCES IPEDS](https://nces.ed.gov/ipeds/) | Postsecondary institution reference and enrichment data — **not** a real-time signal source |
| Selected official organization websites | Technology initiatives, strategic announcements, leadership changes, vendor announcements, funding information |

The exact, verified source list lives in `docs/DATA_SOURCES.md`. Specific organization websites
must be researched and documented there **before** any collection code is written. Third-party
data providers require explicit approval.

---

## 7. AI strategy

The AI layer is **provider-configurable**. Business logic must never be coupled to one LLM vendor.

```
Application → AI Service → LLM Provider Adapter → Configurable Provider
```

The initial provider is chosen during implementation based on available free access, and swapping
providers later must not require rewriting business logic. Embeddings use a free/open-source model
suitable for a hackathon. LangChain is used where it genuinely helps.

RAG flow:

```
Source documents → Clean → Chunk → Metadata → Embeddings → pgvector
  → Retriever → LLM → Grounded answer → Evidence/citations
```

The AI Sales Advisor answers **only** from collected and approved project data. When evidence is
insufficient, it must say so explicitly rather than filling the gap.

**Never fabricate** organizations, procurement events, contracts, dates, vendors, leadership
changes, sources, evidence, or scores.

---

## 8. Opportunity scoring

Scoring is hybrid: **rules compute the number, AI explains it.** The LLM alone never determines
the numeric score.

Scoring factors: recency, source reliability, assessment/EdTech relevance, number and strength of
related signals, and procurement relevance. Exact weights are defined and documented in the
relevant PRD.

The UI always shows both the score and its explanation.

---

## 9. Correlation, duplicates, and evidence

**Correlation.** Not every signal becomes an opportunity. The system connects multiple relevant
signals (for example: technology modernization + leadership change + funding announcement +
procurement activity) into a potential opportunity, and shows *why* those signals were connected.

**Duplicates.** When the same event appears across several sources, cluster the evidence into a
single signal/event rather than producing five independent opportunities. Keep every source
reference on the cluster.

**Evidence.** Every important AI-generated insight carries source name, source URL,
publication/observed date where available, the relevant snippet, and its relationship to the AI
conclusion. Evidence must be easy to inspect in the UI.

---

## 10. Visual direction — Premium Hybrid

Normal product surfaces are clean enterprise: light background, white cards, strong navy/deep-blue
structure, professional typography, generous spacing. AI and intelligence surfaces use subtle
darker panels and indigo/purple accents — visually distinct, never a gaming UI.

Status colors: amber/orange = opportunity/attention, green = positive/healthy, red = risk,
blue/indigo = AI/intelligence.

The main dashboard is a **Hybrid Intelligence Command Center**: opportunity metrics, signal
metrics, competitor/vendor activity and scan status across the top; prioritized opportunities,
signal activity, and AI insights in the main area.

Full design system and screen definitions belong in `docs/UI_UX_DESIGN.md`.

---

## 11. Technology

| Layer | Choice |
|---|---|
| Frontend | React, Vite, Tailwind CSS, Zustand, TanStack Query, Recharts |
| Backend | Python, FastAPI |
| Database | Supabase PostgreSQL with pgvector |
| AI/RAG | LangChain, configurable LLM provider, open-source embeddings |
| Web collection | Requests, BeautifulSoup, Playwright only when JS rendering is required |
| Scheduling | APScheduler |
| Auth | Clerk for authentication. FastAPI for authorization of `SALES_REP` and `SALES_MANAGER`. Not FastAPI-native auth. Not Supabase Auth |
| Deployment | Hosted frontend, hosted backend, Supabase database |

**Authentication boundary.** Clerk answers who the user is: sign-up, sign-in, sign-out, passwords,
session, and identity. FastAPI answers what that user may do. Supabase PostgreSQL stores the
application role, keyed by the Clerk user id, and does not store passwords or Clerk secrets. Both
roles can see every tracked organization; there is no assignment filter in the MVP. The mechanism
is defined in `docs/AUTHENTICATION.md`.

---

## 12. Team and workflow

| Developer | Ownership |
|---|---|
| Developer 1 | Frontend / UI |
| Developer 2 | Backend / API / Database |
| Developer 3 | AI / RAG / Data ingestion |

Developers integrate through the documented contract in `docs/API_CONTRACT.md`, never through
verbal agreement or by reading each other's implementation.

Git workflow: feature branch → Pull Request → review → main/develop. No direct uncontrolled
changes to shared branches.

---

## 13. MVP

The end-to-end workflow that must work before any optional feature is considered:

1. Find/select organization
2. Collect public information
3. Detect signals
4. Validate signals
5. Deduplicate/cluster
6. Connect related signals
7. Generate potential opportunity
8. Calculate hybrid opportunity score
9. Show evidence
10. Ask the AI Sales Advisor about the organization/opportunity
11. Generate recommended next research/action

### Explicitly out of MVP

Full CRM integration, email automation, LinkedIn automation, large-scale internet crawling, mobile
application, enterprise SSO, complex geographic forecasting, advanced admin platform, complex
enterprise infrastructure, Kubernetes, Kafka, unnecessary microservices, complex distributed
systems.

Nothing gets added because it sounds impressive.

---

## 14. Documentation map

| Document | Responsibility |
|---|---|
| `docs/PRODUCT_PRD.md` | Business problem, users, goals, MVP, features, workflows, scope, success criteria |
| `docs/TECHNICAL_PRD.md` | System, frontend, backend, AI, and database architecture; ingestion, auth, deployment, security, integration boundaries |
| `docs/UI_UX_DESIGN.md` | Design system, colors, typography, spacing, components, pages, states, dashboard, opportunity/signal views, AI advisor, responsive behavior |
| `docs/AI_RAG_DESIGN.md` | AI responsibilities, extraction, validation, correlation, score explanation, RAG, embeddings, retrieval, prompting, grounding, evidence, hallucination controls, Advisor |
| `docs/DATA_SOURCES.md` | Verified public sources with purpose, type, access method, frequency, fields, reliability, limitations, usage restrictions, fallback behavior |
| `docs/API_CONTRACT.md` | Endpoints, request/response shapes, errors, pagination, filtering, auth requirements |
| `docs/DATABASE_DESIGN.md` | Tables, relationships, indexes, vector storage, metadata, constraints, audit fields |
| `docs/AUTHENTICATION.md` | Login, roles, authorization, session/token strategy, protected routes, backend authorization |
| `docs/IMPLEMENTATION_PLAN.md` | One-week phased plan, dependencies, developer ownership, per-phase validation, integration points, MVP-first ordering |

Scoped guidance also lives in `frontend/AGENTS.md`, `backend/AGENTS.md`, and the rule files under
`.cursor/rules/`.

---

## 15. Documentation authority

Documents are written in dependency order, and **every later document must respect earlier
approved documents.**

When a later document or implementation reveals a conflict with an approved decision, do not
silently change the earlier decision. Instead:

1. Identify the conflict precisely.
2. Explain why it matters.
3. Propose the smallest necessary change.
4. Wait for approval before editing the source-of-truth document.

Do not invent requirements. Do not expand scope without approval.

---

## 16. Working agreement for AI agents

- Follow the approved documents. If code and a document disagree, the document wins until it is changed through the conflict protocol in §15.
- Implement only the requested phase in `docs/IMPLEMENTATION_PLAN.md`. Validate that phase manually before starting the next one.
- Must-have work comes before should-have and nice-to-have. If time slips, cut in the order that plan gives. Do not cut evidence, the rules score, or the insufficient-evidence response.
- Do not add a dependency, service, or abstraction the technical PRD does not name. Approved extras already recorded: Clerk, `lucide-react`, React Router, PyJWT (Clerk token verification only).
- Keep changes inside the files the task needs. Do not edit unrelated files.
- Use a feature branch. Do not commit directly to the shared branch.
- Do not create test files unless the user explicitly asks for them.
- Unverified facts stay marked `NEEDS VERIFICATION`. Do not turn them into code assumptions.
- The six open implementation decisions in `docs/IMPLEMENTATION_PLAN.md` are resolved during validation. Do not change the architecture to close them early.
- When a requirement is ambiguous, ask. Do not guess a threshold, URL, vector width, or endpoint.
- A meaningful architecture change is proposed against the source document first. It is not hidden in a pull request.
