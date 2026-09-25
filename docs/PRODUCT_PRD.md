# Product PRD — AI Sales Intelligence System

> **Status:** DRAFT — decisions of 2026-09-23 recorded; remaining open questions listed at the end
> **Version:** 0.3
> **Date:** 2026-09-23
> **Authoring order:** 1 of 9
> **Depends on:** root `AGENTS.md`
> **Primary author:** Lead / all developers review

## Purpose of this document

Defines *what* we are building and *why*: the business problem, the users, goals, MVP scope,
features, workflows, and how we will know it succeeded.

**Boundaries.** Architecture, technology choices, and implementation detail belong in
`TECHNICAL_PRD.md`. Visual design, layout, and component specification belong in
`UI_UX_DESIGN.md`. This document states *what information must be present and what the user must
be able to do*, never how a screen looks or how a service is built.

**Reading conventions.**

- Functional requirements are numbered (`FR-AREA-nn`) so later documents can reference them.
- `MUST` = MVP requirement. `SHOULD` = build if time remains. `MAY` = optional.
- `NEEDS DECISION` marks a choice a human must make. `ASSUMPTION` marks something believed true
  but not yet validated with the Excelsoft sales team.

---

## 1. Product overview

The AI Sales Intelligence System is an internal web application for Excelsoft's US sales team. It
continuously observes publicly available information about US education organizations, extracts
evidence-backed **signals**, connects related signals into **potential opportunities**, scores
those opportunities with a rules-based model that the AI explains, and lets a salesperson
interrogate the underlying evidence through an **AI Sales Advisor**.

The output of the product is not a prediction. It is a prioritized, cited, inspectable view of
what is publicly observable about an organization, plus a suggested next research or sales action
for a human to judge.

The product is used by two roles — Sales Representative and Sales Manager — and covers US
education organizations only.

---

## 2. Business problem

Excelsoft sells assessment and learning technology into US education institutions. In that
market, the moment a formal RFP is published is usually the moment it is already too late to
influence: requirements have been shaped, incumbents have had conversations, and the vendor list
is effectively set.

The information that precedes a procurement is almost always public — a board approving a budget,
a district announcing an assessment modernization program, a new CIO being appointed, a federal
award appearing on USAspending.gov, a pre-solicitation notice on SAM.gov, an institution
announcing a new online learning initiative. It is public, but it is scattered across hundreds of
separate sources, published in inconsistent formats, and individually ambiguous. No single item
is worth acting on by itself.

The business problem is therefore not access to information. It is that **no one on a small sales
team has the hours to monitor hundreds of public sources continuously, recognise which fragments
relate to each other, and judge which combinations deserve attention.**

The cost of not solving it: opportunities are discovered at RFP publication rather than months
earlier, research time is spent on organizations with no observable activity, and the reasoning
behind "why this account" lives in individual reps' heads rather than in shared, citable evidence.

> ASSUMPTION — this framing reflects the stated purpose of the project. The specific pain points
> in §3 should be confirmed with the Excelsoft US sales team before the PRD is approved.

---

## 3. Current pain points

| # | Pain point | Consequence |
|---|---|---|
| P1 | Public signals are scattered across federal procurement portals, institutional websites, and funding announcements | Monitoring is manual, partial, and stops whenever the team gets busy |
| P2 | Monitoring effort scales linearly with the number of accounts | Coverage is limited to a handful of known institutions; the rest of the market is invisible |
| P3 | A single signal is ambiguous in isolation | Reps either chase weak leads or ignore genuinely meaningful clusters of activity |
| P4 | The same event is reported by several sources | Duplicated effort and an inflated sense of how much is happening |
| P5 | Opportunities are typically noticed once an RFP is published | Requirements are already shaped; influence is minimal |
| P6 | Prioritization is based on individual judgement and memory | Inconsistent between reps, hard for a manager to review or challenge |
| P7 | The reasoning behind pursuing an account is undocumented | Managers cannot audit it; knowledge is lost when a rep moves on |
| P8 | Institutional context (size, type, enrollment, finances) lives in separate reference systems | Reps switch tools to answer basic qualifying questions |

---

## 4. Target users

### 4.1 Sales Representative

Researches organizations, reviews signals and potential opportunities, inspects evidence,
questions the AI Sales Advisor, and decides what research or sales action to take.

| Aspect | Detail |
|---|---|
| Primary goal | Spend research time on the accounts where something observable is actually happening |
| Key questions | What changed at this organization? Why does the system think it matters? What is the evidence? What should I look into next? |
| Needs from the product | Prioritized potential opportunities, inspectable evidence, an explained score, the ability to scan an organization on demand, and a grounded answer to free-text questions |
| Success for this user | Can explain, with citations, why an account deserves attention — without having read the sources personally |

### 4.2 Sales Manager

Monitors opportunities across the team's market, reviews signal activity and trends, reviews
competitor and vendor intelligence, and identifies where sales attention is required.

| Aspect | Detail |
|---|---|
| Primary goal | Direct limited sales capacity toward the highest-evidence opportunities |
| Key questions | Where is activity concentrated? What is moving this week? What are competitors doing? Is the team's attention in the right place? |
| Needs from the product | Portfolio-level metrics, signal activity over time, competitor/vendor activity, and the ability to drill into any figure down to its source evidence |
| Success for this user | Can review and challenge prioritization based on shared evidence rather than individual opinion |

> Both roles see the same intelligence. The difference is emphasis: the Representative works
> depth-first on organizations; the Manager works breadth-first across the portfolio. Role
> permissions are defined in §27 and enforced per `AUTHENTICATION.md`.

---

## 5. Target market

**United States only.** No other geography is in scope for the MVP — not as a data source, not as
a filter option, and not as a "later, easily" assumption. Source selection, institution reference
data, and procurement vocabulary are all US-specific.

---

## 6. Target organization types

| Type | Included | Notes |
|---|---|---|
| Universities | Yes | Public and private, US-based |
| Colleges | Yes | Including community colleges |
| K-12 school districts | Yes | District-level, not individual schools |
| US public-sector education organizations | Yes | State education agencies and comparable public bodies |

Out of scope: non-US institutions, corporate training buyers, individual schools within a
district, and any organization type not listed above.

**Tracked set (approved 2026-09-22, start size approved 2026-09-23).** The MVP may track 10–20
organizations. The build starts with two. Each of those two is added only after a real SAM.gov
notice or a validated page on that organization's own site is found. Further organizations are
added only after the signal-to-opportunity flow works for those two. They are chosen because they
have useful, recent public signals across more than one of the seven signal types, not because
they are well known. The named list is validated against real public sources and recorded in
`DATA_SOURCES.md` before any collection code is written. Until that list exists, no organization
name in this document is a tracked organization.

---

## 7. Product vision

A salesperson opens the system in the morning and sees, in priority order, the organizations
where publicly observable activity suggests something is changing — each with a score they can
challenge, evidence they can click through to the original public source, an explanation of why
several separate pieces of information were connected, and a concrete suggestion for what to
research next.

The product earns trust by being auditable rather than by being confident. Every claim traces
back to a public document, every score traces back to stated factors, and the system says "the
evidence is insufficient" whenever that is the truthful answer.

**Explicit anti-vision.** This is not a lead-scoring black box, not an RFP prediction engine, and
not an outreach automation tool. It does not tell a rep what will happen; it shows them what is
publicly observable and helps them decide.

---

## 8. Core product workflow

Detect → Connect → Understand → Prioritize → Provide Evidence → Suggest Next Research/Action

| Stage | What happens | What the user sees |
|---|---|---|
| Detect | Approved public sources are collected; candidate signals are extracted and validated | New signals on the organization and dashboard |
| Connect | Duplicate reports of the same event are clustered; related signals are correlated | One signal per real event, with multiple sources; correlated signal groups |
| Understand | The AI explains what the correlated signals appear to indicate, labelled as interpretation | An interpretation panel, visibly separate from the facts |
| Prioritize | Rules compute a 0–100 opportunity score from defined factors | Score plus factor breakdown plus AI explanation |
| Provide Evidence | Every claim carries its source references | An inspectable evidence list on every insight |
| Suggest Next Research/Action | The AI proposes the next research or sales step, grounded in the evidence | A recommended action with the evidence it rests on |

The four output layers — observed fact, AI interpretation, potential opportunity, recommended
action — must remain distinguishable to the user at every stage (§14, `AGENTS.md` §1).

---

## 9. Seven signal types

The taxonomy is closed (`AGENTS.md` §5). Sub-types may be documented within a category; new
categories require explicit approval.

| # | Signal type | Covers | Qualifies | Does not qualify |
|---|---|---|---|---|
| 1 | Procurement | RFP, RFI, pre-solicitation, solicitation, contract activity, procurement notices | A published pre-solicitation notice for an assessment platform | A generic vendor-registration page with no notice attached |
| 2 | Technology initiatives | Assessment modernization, digital transformation, LMS/testing modernization, technology platform initiatives | A district announcing a multi-year assessment platform modernization | A routine IT maintenance notice |
| 3 | Leadership changes | CIO, assessment leadership, technology leadership, relevant procurement/education leadership | Appointment of a new Chief Information Officer | A change in an unrelated department with no technology remit |
| 4 | Funding/budget | Public funding, grants, budget changes, funding announcements | A state grant awarded for student assessment systems | An unrelated capital works budget line |
| 5 | Strategic announcements | New programs, strategic initiatives, online learning initiatives, assessment initiatives | A university launching a new online degree program | A marketing page with no announced initiative |
| 6 | Competitor/vendor changes | Vendor adoption, platform changes, technology partnerships, competitor/vendor announcements | An institution announcing adoption of a competing assessment platform | A vendor logo on a generic partners page with no date or announcement |
| 7 | Contract/renewal | Contract activity, renewal indications, vendor agreements, expiration/renewal-related public information | A published award with a stated period of performance approaching its end | Speculation about a renewal with no public basis |

**Requirements**

- `FR-SIG-01` — Every signal MUST be assigned exactly one of the seven types.
- `FR-SIG-02` — Every signal MUST carry at least one evidence item (§14). A signal that cannot
  cite a source is not stored.
- `FR-SIG-03` — The system MUST NOT create an eighth category at runtime. Content that fits no
  category is discarded, not reclassified into the nearest fit.
- `FR-SIG-04` — Every signal MUST record its observed/published date when the source provides one,
  and MUST record that the date is unavailable when it does not. An unknown date is never guessed.

---

## 10. Signal lifecycle

A signal moves through a defined set of states. The state is visible to the user, because "this
was rejected as irrelevant" and "this was merged into another signal" are meaningful answers.

| State | Meaning | Entered when |
|---|---|---|
| `detected` | Extracted from a source, not yet validated | Extraction produces a candidate with evidence |
| `validated` | Confirmed relevant to the organization and to one of the seven types | Validation passes |
| `rejected` | Extracted but judged irrelevant, out of market, or unsupported by its evidence | Validation fails; a stated reason is retained |
| `merged` | Determined to describe the same real-world event as an existing signal | Duplicate detection matches an existing signal; evidence is added to that cluster |
| `superseded` | Later information replaces this signal's content | A newer signal about the same event supersedes it |

**Requirements**

- `FR-SIG-05` — Only `validated` signals MUST be eligible for correlation and scoring.
- `FR-SIG-06` — `rejected` signals MUST retain their rejection reason and remain inspectable, so a
  user can check what the system chose to discard.
- `FR-SIG-07` — When a signal is `merged`, the surviving signal MUST retain a source reference for
  every contributing report (§13, duplicate handling).
- `FR-SIG-08` — Signal state transitions MUST be recorded with a timestamp.

> **Decided 2026-09-23.** Sales representatives can read and research signals. They cannot edit a
> signal's type or state in the MVP. Manual correction stays a future possibility in §30.

---

## 11. Signal correlation

Correlation is the product's central idea: individual public facts are weak, but combinations are
informative.

**Requirements**

- `FR-COR-01` — The system MUST connect multiple validated signals belonging to the same
  organization into a correlated group.
- `FR-COR-02` — Each correlation MUST record and display a stated reason for the connection —
  what the signals have in common and why they are treated as related.
- `FR-COR-03` — The correlation reason MUST be presented as AI interpretation, never as observed
  fact.
- `FR-COR-04` — Correlation MUST consider signal type, organization, time proximity, and subject
  matter overlap. The precise method is defined in `AI_RAG_DESIGN.md`.
- `FR-COR-05` — A single signal MUST NOT, on its own, be presented as a potential opportunity
  unless it independently meets the threshold in §12.

Worked example of the intended behaviour:

```
Technology modernization initiative announced   (type 2, Mar)
+ New CIO appointed                             (type 3, Apr)
+ State assessment grant awarded                (type 4, May)
+ Pre-solicitation notice published             (type 1, Jun)
→ Potential opportunity, with the four signals and the stated reason for connecting them
```

---

## 12. Opportunity generation

**Requirements**

- `FR-OPP-01` — The system MUST NOT create an opportunity for every signal.
- `FR-OPP-02` — An opportunity MUST be generated only when a correlated group meets the documented
  threshold, expressed in terms of number of related signals, their types, their recency, and
  their computed score.
- `FR-OPP-03` — Every opportunity MUST belong to exactly one organization.
- `FR-OPP-04` — Every opportunity MUST expose the complete set of signals that produced it, and
  through them, all underlying evidence.
- `FR-OPP-05` — Every opportunity MUST be labelled as a **potential** opportunity in all user-
  facing copy. Language implying certainty about future procurement is prohibited.
- `FR-OPP-06` — When new signals arrive for an organization, an existing opportunity MUST be
  updated rather than duplicated, and its score recalculated.

> **Decided 2026-09-23.** Create a potential opportunity only when all of these are true: at least
> two validated signals, of different types, at least one dated within 90 days, and a rules score
> of 50 or higher (Medium band or above, weight version `v1`). One signal stays a signal.

---

## 13. Hybrid opportunity scoring

**Rules compute the number. The AI explains it.** The LLM never produces or adjusts the numeric
score (`AGENTS.md` §8).

### 13.1 Factors

| Factor | What it measures | Rationale |
|---|---|---|
| Recency | How recently the contributing signals were published or observed | Six-month-old activity is weaker evidence than last week's |
| Source reliability | The reliability rating of the sources behind the signals, per `DATA_SOURCES.md` | A federal procurement notice is stronger evidence than a general web page |
| Assessment/EdTech relevance | How closely the subject matter relates to Excelsoft's assessment and learning technology domain | A general facilities initiative is not a sales signal for us |
| Related signal strength | The number and type diversity of correlated signals | Four corroborating signals across different types beat one repeated item |
| Procurement relevance | How close the activity is to actual buying behaviour | A published pre-solicitation is closer to a purchase than a strategy statement |

### 13.2 Requirements

- `FR-SCR-01` — The score MUST be an integer from 0 to 100, produced by deterministic rule code.
- `FR-SCR-02` — The same inputs MUST always produce the same score.
- `FR-SCR-03` — The per-factor contribution breakdown MUST be stored and displayed, not just the
  total.
- `FR-SCR-04` — The AI MUST generate a plain-language explanation of the computed score, derived
  from the factor breakdown.
- `FR-SCR-05` — A score MUST NEVER be displayed without its explanation and factor breakdown.
- `FR-SCR-06` — Weights MUST be defined in one place and documented, not embedded across the code.
- `FR-SCR-07` — When an opportunity's signals change, the score MUST be recalculated and the
  previous value MUST remain visible as history, so a user can see that a score moved.

### 13.3 Approved weights and bands — version `v1`

Approved 2026-09-22 as the initial version. These numbers are the product definition of `v1`.
The running copy lives in one versioned configuration (`TECHNICAL_PRD.md` §15, `FR-SCR-06`) so the
values can be tuned during the hackathon without redesigning scoring. A change produces `v2`; it
does not silently rewrite `v1`, and every stored score records the version that produced it.

| Factor | Weight (`v1`) |
|---|---|
| Procurement relevance | 30 |
| Related signal strength | 25 |
| Assessment/EdTech relevance | 20 |
| Recency | 15 |
| Source reliability | 10 |

| Band | Range | Meaning |
|---|---|---|
| High | 75–100 | Multiple corroborating recent signals with clear procurement relevance |
| Medium | 50–74 | Genuine observable activity; worth research |
| Low | 25–49 | Early or weak indications |
| Monitor | 0–24 | Not currently actionable; keep watching |

---

## 14. Evidence requirements

Evidence is what makes the product auditable. It is a functional requirement, not a presentation
detail.

- `FR-EV-01` — Every evidence item MUST carry: source name, source URL, publication/observed date
  where available, the relevant snippet, and its relationship to the conclusion it supports.
- `FR-EV-02` — When a source provides no date, the evidence item MUST state that the date is
  unavailable. Dates are never inferred or approximated.
- `FR-EV-03` — Every signal, correlation, opportunity score explanation, AI Advisor answer, and
  recommended action MUST be traceable to its evidence within the interface.
- `FR-EV-04` — A clustered signal MUST display every contributing source reference, not only the
  first one found.
- `FR-EV-05` — Source URLs MUST point at the original public source so the user can verify
  independently.
- `FR-EV-06` — Content presented as an observed fact MUST be attributable to a source. AI-produced
  content MUST be labelled as interpretation.
- `FR-EV-07` — An insight that cannot cite evidence MUST NOT be stored, returned, or displayed.

---

## 15. AI Sales Advisor

A question-and-answer interface that answers from collected, approved project data only.

**Requirements**

- `FR-ADV-01` — Users MUST be able to ask free-text questions in the context of an organization or
  an opportunity.
- `FR-ADV-02` — Answers MUST be grounded in retrieved project data. General model knowledge is not
  an acceptable source.
- `FR-ADV-03` — Every answer MUST include citations to the evidence it used.
- `FR-ADV-04` — When retrieval returns insufficient evidence, the Advisor MUST state that
  explicitly and MUST NOT produce a speculative answer.
- `FR-ADV-05` — The Advisor MUST NOT fabricate organizations, procurement events, contracts,
  dates, vendors, leadership changes, sources, evidence, or scores.
- `FR-ADV-06` — Answers MUST distinguish what a source stated from what the system infers.
- `FR-ADV-07` — The Advisor MUST decline questions outside the product's scope rather than
  answering from general knowledge.

**Question types the MVP must handle**

| Category | Example |
|---|---|
| Organization summary | "What has been happening at this district over the last six months?" |
| Signal explanation | "Why was this leadership change recorded as a signal?" |
| Score interrogation | "Why is this opportunity scored 78?" |
| Correlation interrogation | "Why are these four signals connected?" |
| Evidence lookup | "What is the source for the funding announcement?" |
| Next step | "What should I research before contacting them?" |

> Conversation history persistence and multi-turn context depth are defined in
> `AI_RAG_DESIGN.md`. Product requirement: a user MUST be able to ask follow-up questions within a
> session without restating the organization.

---

## 16. Dashboard requirements

The dashboard is the Hybrid Intelligence Command Center (`AGENTS.md` §10). Layout and visual
treatment belong to `UI_UX_DESIGN.md`; the requirements below define what information must be
present and what must be reachable.

- `FR-DASH-01` — MUST display opportunity metrics: count of active potential opportunities, their
  distribution across score bands, and how many are new within a stated recent period.
- `FR-DASH-02` — MUST display signal metrics: total validated signals, a breakdown by the seven
  signal types, and recent signal volume.
- `FR-DASH-03` — MUST display competitor/vendor activity derived from type 6 signals.
- `FR-DASH-04` — MUST display scan status: when the last scan ran, whether a scan is currently
  running, and whether the last scan for any source failed.
- `FR-DASH-05` — MUST display prioritized potential opportunities in descending score order, each
  showing organization, score, band, and contributing signal count.
- `FR-DASH-06` — MUST display recent signal activity with type and organization.
- `FR-DASH-07` — MUST display AI insights, visibly labelled as AI interpretation.
- `FR-DASH-08` — Every metric MUST be drillable to the underlying signals or opportunities, and
  from there to evidence. A number the user cannot trace is not acceptable.
- `FR-DASH-09` — MUST indicate when displayed data comes from the cached/fallback dataset (§26).
- `FR-DASH-10` — MUST handle the empty state honestly: a new deployment with no scans shows a
  clear "no data collected yet" state, never fabricated placeholder figures.

---

## 17. Organization profile requirements

- `FR-ORG-01` — MUST display organization identity: name, type (university, college, K-12
  district, public-sector education organization), state, and website.
- `FR-ORG-02` — MUST display institutional reference/enrichment context sourced from NCES IPEDS
  where available, clearly attributed as reference data and not as a sales signal.
- `FR-ORG-03` — MUST display all signals for the organization, filterable by type and date, with
  their lifecycle state.
- `FR-ORG-04` — MUST display all potential opportunities for the organization with scores and
  bands.
- `FR-ORG-05` — MUST provide access to the AI Sales Advisor in the context of this organization.
- `FR-ORG-06` — MUST provide a Scan Now control (§21).
- `FR-ORG-07` — MUST display when the organization was last scanned, and which sources were
  covered.
- `FR-ORG-08` — MUST show an explicit empty state when no signals have been detected. "Nothing
  observable is happening" is a legitimate and useful answer.

---

## 18. Opportunity details

- `FR-OPP-07` — MUST display the opportunity score, its band, and the per-factor breakdown.
- `FR-OPP-08` — MUST display the AI-generated explanation of the score.
- `FR-OPP-09` — MUST display every contributing signal with type, date, and summary.
- `FR-OPP-10` — MUST display the stated reason the signals were correlated, labelled as AI
  interpretation.
- `FR-OPP-11` — MUST provide access to all underlying evidence, with working source URLs.
- `FR-OPP-12` — MUST display the recommended next research/action, labelled as a recommendation
  and linked to the evidence it rests on.
- `FR-OPP-13` — MUST display score history when the score has changed (`FR-SCR-07`).
- `FR-OPP-14` — MUST visually separate the four layers: observed facts, AI interpretation, the
  potential opportunity itself, and the recommended action.
- `FR-OPP-15` — MUST provide access to the AI Sales Advisor in the context of this opportunity.

---

## 19. Signal details

- `FR-SIG-09` — MUST display signal type, title/summary, observed or published date (or an
  explicit statement that no date is available), and lifecycle state.
- `FR-SIG-10` — MUST display the organization the signal belongs to.
- `FR-SIG-11` — MUST display every source reference for the signal, including all contributors
  when the signal is a cluster.
- `FR-SIG-12` — MUST display the evidence snippet for each source reference.
- `FR-SIG-13` — MUST display which opportunities, if any, this signal contributes to.
- `FR-SIG-14` — MUST distinguish the extracted factual content from any AI summary of it.
- `FR-SIG-15` — For a `rejected` signal, MUST display the stated rejection reason.

---

## 20. Search and filter requirements

- `FR-SRCH-01` — MUST allow searching for an organization by name.
- `FR-SRCH-02` — MUST allow filtering signals by signal type, organization, date range, and
  lifecycle state.
- `FR-SRCH-03` — MUST allow filtering opportunities by score band, organization, organization
  type, and date.
- `FR-SRCH-04` — MUST allow sorting opportunities by score and by recency.
- `FR-SRCH-05` — MUST allow filtering by US state.
- `FR-SRCH-06` — MUST return an explicit empty result state rather than a blank screen.
- `FR-SRCH-07` — List results MUST be paginated. The mechanism is defined in `API_CONTRACT.md`.
- `FR-SRCH-08` — Search MUST cover organizations already known to the system. Discovering
  previously unknown organizations from the open web is out of MVP scope (§24).

---

## 21. Scan Now workflow

An on-demand collection and analysis run for a single organization, triggered by a user. This is
how the product demonstrates its full pipeline live, and how a rep refreshes an account before a
conversation.

**Requirements**

- `FR-SCAN-01` — A user MUST be able to trigger a scan for a selected organization.
- `FR-SCAN-02` — A scan MUST eventually run the full pipeline: collect from approved sources →
  extract signals → validate → deduplicate/cluster → correlate → generate or update opportunities →
  recalculate scores → produce explanations and recommended actions.
  **MVP interim (discovery and collection):** until later phases land, Scan All / dashboard Scan
  Now for `tracking_status = active` organizations MAY complete after LLM-assisted candidate
  proposal, backend URL validation, persistence into `organization_sources`, and collection of those
  official pages (including the organization's own news articles) into `documents`. Later phases add
  signal extraction and the downstream stages without changing this requirement's end state.
- `FR-SCAN-03` — The user MUST see that the scan is running and which stage it has reached. The
  interface MUST NOT appear frozen.
- `FR-SCAN-04` — On completion, the user MUST see what changed: new signals, updated signals, new
  or updated opportunities, and score movements.
- `FR-SCAN-05` — If an individual source fails or is unavailable, the scan MUST continue with the
  remaining sources and MUST report which source failed and why.
- `FR-SCAN-06` — A scan MUST respect source rate limits and usage restrictions
  (`DATA_SOURCES.md`). Users MUST NOT be able to trigger scans rapidly enough to breach them.
- `FR-SCAN-07` — Only one scan per organization MUST run at a time. A second request while one is
  running joins the running scan rather than starting a duplicate.
- `FR-SCAN-08` — Scan results MUST be persisted; a scan is not a transient view.
- `FR-SCAN-09` — If a scan yields no new signals, that MUST be reported as a successful scan with
  no changes — not as an error, and never by fabricating results.
- `FR-SCAN-10` — A user MUST be able to trigger **Scan All**, which scans every tracked
  organization.
- `FR-SCAN-11` — Scan All MUST run the same pipeline as Scan Now for each organization
  (`FR-SCAN-02`). It is a batch of per-organization scans, not a different kind of analysis.
- `FR-SCAN-12` — Scan All MUST respect the one-scan-per-organization rule (`FR-SCAN-07`) and source
  rate limits (`FR-SCAN-06`). Organizations are not scanned in an unbounded parallel burst.
- `FR-SCAN-13` — While Scan All is running, the user MUST see which organizations are pending,
  running, complete, or failed, and MUST see the same per-source failure reporting as a single
  scan.

> NEEDS DECISION — the target completion time for a single-organization scan, which determines
> whether the demo can run one live. A scan that takes several minutes changes the demo script
> (§29). To be confirmed once source latency is measured; the technical approach for long-running
> requests is an open question in `TECHNICAL_PRD.md`.

---

## 22. Scheduled scanning

- `FR-SCHED-01` — The system MUST scan tracked organizations automatically on a schedule, without
  a user present.
- `FR-SCHED-02` — Scheduled scans MUST run the same pipeline as Scan Now, so results are
  identical in kind.
- `FR-SCHED-03` — Per-source collection frequency MUST follow `DATA_SOURCES.md` and MUST respect
  each source's rate limits and usage restrictions.
- `FR-SCHED-04` — Every scheduled run MUST record start time, end time, sources attempted,
  sources failed, and signals produced.
- `FR-SCHED-05` — Scan status and the last successful run MUST be visible on the dashboard
  (`FR-DASH-04`).
- `FR-SCHED-06` — A failed scheduled scan MUST NOT silently substitute cached data. Failure is
  reported as failure (§26).

> **Decided 2026-09-23.** Scan Now is the demo. Scheduled scanning is optional and is the first
> feature dropped if time is limited. If it is built later, it still follows the cadence in
> `DATA_SOURCES.md`.

---

## 23. MVP scope

The eleven-step workflow from `AGENTS.md` §13 must work end to end before any optional feature is
built. Each step below has an acceptance criterion that can be demonstrated.

| # | Step | Acceptance criterion |
|---|---|---|
| MVP-01 | Find/select organization | A user can search tracked organizations by name and open a profile |
| MVP-02 | Collect public information | A scan retrieves real content from at least two approved sources and persists it with URL and retrieval timestamp |
| MVP-03 | Detect signals | Collected content produces typed signals, each carrying at least one evidence item |
| MVP-04 | Validate signals | Irrelevant candidates are rejected with a stated reason and are inspectable |
| MVP-05 | Deduplicate/cluster | The same event from two sources produces one signal with two source references |
| MVP-06 | Connect related signals | At least two validated signals are correlated with a displayed reason |
| MVP-07 | Generate potential opportunity | A correlated group meeting the threshold produces exactly one potential opportunity |
| MVP-08 | Calculate hybrid score | A 0–100 score is computed by rules, reproducible, with a stored factor breakdown and an AI explanation |
| MVP-09 | Show evidence | Every signal, score, and insight can be traced to source name, URL, date where available, and snippet |
| MVP-10 | Ask the AI Sales Advisor | A grounded, cited answer is returned, and insufficient evidence is stated explicitly when true |
| MVP-11 | Recommend next research/action | A recommendation is produced and linked to the evidence supporting it |

### 23.1 Supporting MVP features

Authentication with the two roles (§27), the dashboard (§16), organization profile (§17),
opportunity details (§18), signal details (§19), search and filter (§20), Scan Now and Scan All
(§21), scheduled scanning (§22), and the cached fallback dataset (§26).

### 23.2 Priority for a one-week, three-developer build

| Priority | Scope | Reasoning |
|---|---|---|
| P0 — must work for the demo | MVP-01 through MVP-11, auth, organization profile, opportunity details, evidence display, Scan Now and Scan All | This is the product; without the full chain there is nothing to show |
| P1 — build if the chain is working | Dashboard metrics, search and filter, scheduled scanning, score history | Valuable, but each is meaningless without P0 |
| P2 — only if time genuinely remains | Trend visualization over time, competitor/vendor summary views | Presentation polish on top of working intelligence |

### 23.3 Realism constraints

A three-developer team has roughly five working days. The MVP is therefore deliberately bounded:
a limited set of tracked organizations rather than open-ended discovery, a small number of
approved sources rather than broad coverage, one scan path used by both manual and scheduled runs,
and read-only intelligence for signals and opportunities (no editing of those rows). Managers may
create and update organization identity and tracking status after live website validation
(`FR-ORG-09`, `FR-ROLE-05`). The tracked set is 10–20 organizations,
selected for observable activity across several signal types (§6).

---

## 24. Out-of-scope features

Restating `AGENTS.md` §13 with the reason each is deferred. Nothing here is a judgement about
long-term value; each is excluded because it does not serve the one-week MVP.

| Excluded | Why deferred |
|---|---|
| Full CRM integration | Requires a target CRM, credentials, and field mapping; consumes the week without improving the intelligence itself |
| Email automation | Outreach is a different product; the MVP ends at recommending research/action |
| LinkedIn automation | Outreach, plus platform terms that conflict with our collection constraints |
| Large-scale internet crawling | Explicitly prohibited; collection is targeted at approved sources |
| Mobile application | A second client for a desktop research workflow |
| Enterprise SSO | Email/password with two roles is sufficient for an internal hackathon build |
| Complex geographic forecasting | Analytics on top of a dataset we will not have at sufficient volume |
| Advanced admin platform | Configuration can be handled by the team directly during the week |
| Complex enterprise infrastructure, Kubernetes, Kafka, microservices, distributed systems | Operational overhead with no product benefit at this scale |

Also out of MVP scope as a product matter: discovering organizations not already tracked (§20),
manual editing of signals or opportunities (§10), and multi-tenant or customer-facing deployment.

Nothing is added because it sounds impressive.

---

## 25. Real-data strategy

- `FR-DATA-01` — Real public information MUST be the primary data source. Mock data MUST NEVER be
  the primary product data.
- `FR-DATA-02` — Collection MUST be limited to sources documented and approved in
  `DATA_SOURCES.md`.
- `FR-DATA-03` — The system MUST NOT bypass authentication, access controls, robots restrictions,
  rate limits, paywalls, or CAPTCHAs.
- `FR-DATA-04` — The system MUST NOT crawl broadly. Collection is targeted at approved
  organizations and sources.
- `FR-DATA-05` — Raw retrieved content, its source URL, and its retrieval timestamp MUST be
  persisted alongside anything derived from it, so every downstream claim stays traceable.
- `FR-DATA-06` — Sources MUST NOT be invented. Adding a source requires documenting and approving
  it first.
- `FR-DATA-07` — IPEDS data MUST be treated as institutional reference/enrichment only and MUST
  NOT be presented as a real-time sales signal.

The source register — purpose, access method, frequency, fields, reliability, limitations, usage
restrictions, and fallback behaviour — is owned by `DATA_SOURCES.md`.

---

## 26. Fallback cached data strategy

The cached dataset exists for exactly one reason: so a live demonstration does not fail because a
public source is temporarily unavailable.

- `FR-FB-01` — Cached/fallback data MUST NOT be the primary data path.
- `FR-FB-02` — Cached data MUST be real content previously retrieved from approved sources, with
  its original source URL and retrieval timestamp preserved. It is a snapshot, not invented data.
- `FR-FB-03` — Whenever cached data is displayed, it MUST be visibly labelled as cached, with the
  date it was originally retrieved.
- `FR-FB-04` — The system MUST NOT silently substitute cached data for a live result. A source
  failure is reported as a source failure (`FR-SCAN-05`, `FR-SCHED-06`).
- `FR-FB-05` — Cached data MUST NOT be used to fabricate signals, opportunities, scores, or
  evidence that were never observed.
- `FR-FB-06` — The cached dataset MUST be limited to the demonstration organizations.

---

## 27. User roles

Two roles, stored and enforced as `SALES_REP` and `SALES_MANAGER`. Login and session are handled
by Clerk; FastAPI verifies the authenticated user and enforces the role. The mechanism is defined
in `AUTHENTICATION.md` and `TECHNICAL_PRD.md` §10. This section defines only the product-level
capability difference.

**Approved 2026-09-22.** Both roles can see every tracked organization. There is no
ownership or assignment filter in the MVP.

| Capability | `SALES_REP` | `SALES_MANAGER` |
|---|---|---|
| View dashboard | Yes | Yes |
| Search and open every tracked organization | Yes | Yes |
| View organization profile | Yes | Yes |
| Create or update organization identity (name, type, state, official website) | No | Yes |
| Add or reject official same-domain page sources | No | Yes |
| Activate or deactivate tracking | No | Yes |
| View signals and evidence | Yes | Yes |
| View opportunities, scores, explanations | Yes | Yes |
| Use the AI Sales Advisor | Yes | Yes |
| Trigger Scan Now and Scan All | Yes | Yes |
| View portfolio-wide metrics across all tracked organizations | Yes | Yes |
| View competitor/vendor intelligence summary | Yes | Yes |

For the MVP both roles see the same intelligence. Organization **identity** writes are manager-only so the tracked set stays curated. There is still no separate manager-only screen — Add/Edit/Activate controls appear on the shared Organizations pages for managers only (`UI_UX_DESIGN.md`).

- `FR-ROLE-01` — Every user MUST have exactly one role: `SALES_REP` or `SALES_MANAGER`.
- `FR-ROLE-02` — Authorization MUST be enforced server-side on every protected operation,
  regardless of what the interface exposes.
- `FR-ROLE-03` — Both roles MUST see identical evidence for any item they can both access. The
  system does not show a manager a different set of facts.
- `FR-ROLE-04` — List and detail queries MUST NOT filter organizations, signals, or opportunities
  by the calling user. Assignment is out of MVP scope.
- `FR-ROLE-05` — Only `SALES_MANAGER` MAY create or update organization identity fields and
  `tracking_status`. `SALES_REP` MUST receive `403 INSUFFICIENT_PERMISSION` on those write
  operations.
- `FR-ORG-09` — Before creating or changing an organization's `website_url`, the system MUST
  live-validate that the official public website is reachable over HTTPS (or HTTP redirecting to
  HTTPS), is not gated by login/CAPTCHA/paywall markers checked by the fetcher, and store the
  final URL after redirects. A failed validation MUST NOT write or update the row.
- `FR-ORG-10` — Only `SALES_MANAGER` MAY add an official same-domain page URL to an organization
  (`organization_sources`). The URL MUST pass the same live validation as `FR-ORG-09` and MUST
  stay on the organization's official host. Registry APIs (SAM.gov, IPEDS, USAspending) MUST NOT
  be added through this path.

---

## 28. Success criteria

### 28.1 Functional success

| # | Criterion | How it is verified |
|---|---|---|
| S1 | The eleven-step MVP workflow runs end to end on real public data | Execute MVP-01 to MVP-11 against a tracked organization |
| S2 | At least two approved sources are collected successfully | Scan log shows successful retrieval with URLs and timestamps |
| S3 | Signals are produced across at least three of the seven types | Signal list filtered by type |
| S4 | Duplicate detection demonstrably merges one real event reported by two sources | One signal showing two source references |
| S5 | At least one opportunity is produced from correlated signals with a displayed reason | Opportunity detail view |
| S6 | Scores are reproducible | Recompute the same opportunity and get the same number |
| S7 | Every displayed score has a factor breakdown and an AI explanation | Inspect every opportunity in the demo set |
| S8 | Every AI insight traces to evidence with a working source URL | Click through evidence links |
| S9 | The Advisor states "insufficient evidence" when asked something the data cannot support | Ask a deliberately unsupported question |
| S10 | Both roles can authenticate and reach their views | Log in as each role |

### 28.2 Trust and integrity success

| # | Criterion |
|---|---|
| T1 | No fabricated organization, event, contract, date, vendor, leadership change, source, or score appears anywhere in the product |
| T2 | Observed fact, AI interpretation, potential opportunity, and recommended action are visually distinguishable on every screen that shows them |
| T3 | No user-facing copy claims that an RFP will definitely happen |
| T4 | Every broken or missing source is reported as such, never hidden and never replaced with invented content |
| T5 | Cached/fallback data is labelled wherever it appears |

### 28.3 Demonstration success

The demo runs end to end, on real public data, without a fabricated step, and a viewer who
challenges any number on screen can be shown its evidence within two clicks.

---

## 29. Hackathon demo workflow

A demonstration script that exercises the full product rather than a highlight reel. Target
length: 8–10 minutes.

| Step | Action | What it proves |
|---|---|---|
| 1 | Log in as Sales Representative | Authentication and role-based access work |
| 2 | Open the dashboard | Opportunity metrics, signal metrics, competitor/vendor activity, and scan status are real and populated |
| 3 | Search and open a tracked organization | Organization identity and IPEDS reference context, clearly labelled as reference data |
| 4 | Show the organization's existing signals, filtered by type | Multiple signal types detected from real public sources |
| 5 | Open a signal that was clustered from two sources | Duplicate detection: one event, multiple source references |
| 6 | Run **Scan Now** | The live pipeline: collect → extract → validate → deduplicate → correlate → score, with visible progress |
| 7 | Open the resulting potential opportunity | Score, band, factor breakdown, AI explanation, and the stated reason the signals were connected |
| 8 | Click through to evidence | Real source URLs opening real public pages with the cited content |
| 9 | Ask the AI Sales Advisor "why is this scored as it is?" | Grounded, cited answer derived from project data |
| 10 | Ask the Advisor a question the data cannot support | The system states that evidence is insufficient instead of inventing an answer |
| 11 | Show the recommended next research/action | The product ends at a human decision, not an automated claim |
| 12 | Log in as Sales Manager | Portfolio view: where activity is concentrated and where attention is needed |

**Contingency.** If a public source is unavailable during the demo, step 6 reports the source
failure honestly and continues with the remaining sources; the cached dataset covers the
previously retrieved content, visibly labelled as cached (§26). The demo never silently pretends a
failed source succeeded.

> NEEDS DECISION — the specific organization used for steps 3–11. It must have genuine, publicly
> observable activity across at least three signal types. Selection depends on §23.3 and
> `DATA_SOURCES.md`.

---

## 30. Future possibilities — explicitly NOT MVP

Everything in this section is out of scope for the hackathon. It is recorded so that good ideas
are not lost and not smuggled into the build.

| Possibility | Note |
|---|---|
| Organization discovery from the open web | Currently limited to tracked organizations; would require a defined, compliant discovery method |
| Manual correction of signal type or state | Requires write paths, permissions, and an audit trail (§10) |
| Opportunity triage states (reviewed, dismissed, pursuing) | Useful workflow; adds state management not needed to prove the intelligence works |
| Organization ownership and assignment to reps | Explicitly not in the MVP (`FR-ROLE-04`). Both roles see every tracked organization |
| Alerting and notifications on new high-score opportunities | Natural next step once scoring is trusted |
| Trend analysis over longer time horizons | Requires accumulated history the hackathon will not have |
| Additional signal categories beyond the seven | Closed taxonomy; requires explicit approval |
| Additional data sources and third-party providers | Requires approval and documentation in `DATA_SOURCES.md` |
| CRM integration, email and LinkedIn outreach | Deferred per §24 |
| Enterprise SSO, mobile application, advanced admin | Deferred per §24 |
| Feedback loop where rep outcomes tune the scoring weights | Valuable long term; needs outcome data that does not exist yet |

---

## 31. Risks and assumptions

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | An approved public source is slow, rate-limited, or unavailable during the build or demo | Pipeline stalls; demo fails | Per-source failure isolation (`FR-SCAN-05`); labelled cached fallback (§26) |
| R2 | Tracked organizations show too little recent activity to demonstrate correlation | The core idea cannot be shown | Select demonstration organizations on observed activity, not on name recognition (§23.3) |
| R3 | LLM provider free-tier limits are reached mid-build | AI features stop working | Provider-configurable abstraction (`AGENTS.md` §7) allows switching |
| R4 | Extraction quality is poor on unstructured institutional web pages | Noisy or wrong signals | Validation stage with stated rejection reasons (§10); prefer structured official sources |
| R5 | Scoring weights produce unconvincing rankings | Demo lacks credibility | Weights defined in one place (`FR-SCR-06`) and tunable without code restructuring |
| R6 | Scope creep from optional features | MVP chain incomplete | P0/P1/P2 priority (§23.2); out-of-scope list (§24) |
| R7 | Three developers block on an unagreed interface | Parallel work stalls | Contract-first integration (`AGENTS.md` §12, `API_CONTRACT.md`) |
| R8 | A single-organization scan is too slow to run live | Demo script must change | Measure early; decision flagged in §21 |

**Assumptions**

| # | Assumption | Validation |
|---|---|---|
| A1 | The business problem and pain points in §2–§3 reflect the Excelsoft US sales team's reality | Confirm with the sales team before approval |
| A2 | Enough public signal activity exists across the tracked organizations to produce meaningful correlations within the build week | Verify during source research in `DATA_SOURCES.md` |
| A3 | Approved sources permit the intended access under their published terms | Confirm per source in `DATA_SOURCES.md` |
| A4 | A free or available LLM provider and open-source embedding model are sufficient for the required quality | Verify during implementation |

---

## Open questions

Consolidated from the sections above; each requires a human decision before or during
implementation.

### Decided

| # | Decision |
|---|---|
| Q1 | Track 10–20 US education organizations, chosen for recent public signals across multiple signal types. Named list is validated in `DATA_SOURCES.md`, not in this document |
| Q2 | Scoring weights `v1` approved: 30 / 25 / 20 / 15 / 10 (§13.3) |
| Q3 | Weights live in one versioned configuration. This section is the product definition; the running copy is configuration |
| Q4 | **Decided 2026-09-23.** At least two validated signals of different types, one within 90 days, rules score 50 or higher |
| Q5 | Both `SALES_REP` and `SALES_MANAGER` see every tracked organization. No assignment filter |
| Q6 | **Decided 2026-09-23.** No manual edit of signal type or state in the MVP |
| Q7 | **Decided 2026-09-23.** Scan Now is the demo. Scheduled scanning is optional and is the first cut |
| Q9 | **Decided 2026-09-23.** Start with two organizations, chosen only after real public evidence. Names are recorded in `DATA_SOURCES.md`, not here |
| — | Lowest score band is named **Monitor** (0–24), not "Minimal" |
| — | Scan All is in the MVP, as a batch of per-organization scans (`FR-SCAN-10`–`FR-SCAN-13`) |
| — | Authentication is Clerk. Authorization and business roles stay in FastAPI |

### Still open

| # | Question | Section | Recommendation |
|---|---|---|---|
| Q8 | What is the acceptable completion time for a live single-organization scan? | §21 | Measure source latency early; it determines the demo script |
