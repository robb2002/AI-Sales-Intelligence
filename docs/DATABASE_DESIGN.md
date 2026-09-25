# Database Design

> **Status:** DRAFT — awaiting approval
> **Version:** 0.1
> **Date:** 2026-09-23
> **Depends on:** `TECHNICAL_PRD.md` AD-05, `API_CONTRACT.md`, `AUTHENTICATION.md` §9, `AI_RAG_DESIGN.md` §§13–17, `DATA_SOURCES.md`
> **Primary author:** Developer 2 (Backend/API/Database)

## Purpose

The Supabase PostgreSQL schema, including pgvector. Column names match `API_CONTRACT.md`. This document does not add tables the API does not read or the pipeline does not write.

No migration files are included. Row Level Security is not used. The backend connects with its own database role and enforces Clerk plus `SALES_REP` / `SALES_MANAGER` in FastAPI (AD-05, AD-15).

Primary keys are `uuid`. Timestamps are `timestamptz` stored in UTC. Closed sets are `text` columns with a `CHECK` constraint, using the enum values in `API_CONTRACT.md` §1.2. A lookup table for two roles or seven signal types is not worth a join.

`created_at` is set on insert. `updated_at` is set on insert and on every update. Rows that are only inserted (scores, state events, AI turns) have `created_at` and no `updated_at`.

---

## 1. Table list

| Table | Why it exists |
|---|---|
| `app_users` | Clerk user id and the application role |
| `organizations` | The 10–20 tracked institutions, plus IPEDS reference on the same row |
| `sources` | Approved origins from `DATA_SOURCES.md` |
| `documents` | Raw fetched content, URL, hash, retrieval time |
| `document_chunks` | Chunk text, citation metadata, and the embedding |
| `signals` | One signal, including a cluster's surviving row and rejected rows |
| `evidence` | Source name, URL, date, snippet. This is the signal's source reference |
| `opportunities` | At most one potential opportunity per organization |
| `opportunity_signals` | Which signals belong to that opportunity |
| `opportunity_scores` | Rules score, factor points, explanation, history |
| `signal_state_events` | Each state change and when it happened (`FR-SIG-08`) |
| `scan_batches` | One Scan All |
| `scan_runs` | One organization pipeline run |
| `advisor_sessions` | Advisor scope for follow-up questions |
| `ai_interactions` | Briefings, explanations, recommendations, and Advisor turns |

Not created, and why:

| Omitted | Reason |
|---|---|
| `roles` | Two values. A check constraint on `app_users.role` is enough |
| `embeddings` as its own table | The vector sits on `document_chunks` |
| `signal_sources` as a second table | A source reference is an `evidence` row |
| A correlation graph | `opportunity_signals` is the correlated set. `signals.merged_into_signal_id` is the cluster |
| `ipeds` as its own table | A handful of reference fields on `organizations` |
| An audit-log table | `created_at`, `updated_at`, and `signal_state_events` cover the MVP |
| Password or session tables | Clerk |

---

## 2. Relationships

```
app_users

sources ──< documents ──< document_chunks
                │
                └──< evidence >── signals >── organizations
                         │            │
                         │            ├── merged_into_signal_id (self)
                         │            └──< signal_state_events
                         │
opportunity_signals >── signals
         │
         └── opportunities ──< opportunity_scores
                    │
                    └── organizations

scan_batches ──< scan_runs >── organizations
ai_interactions >── advisor_sessions
                >── evidence (via evidence_ids)
```

One organization has many signals, at most one opportunity, and many scan runs. One signal has many evidence rows. One document has many chunks. A merged signal points at the surviving signal and does not delete its evidence.

---

## 3. app_users

Maps a Clerk identity to exactly one application role (`AUTHENTICATION.md` §9). No password or token. Email and role are synced from Clerk on authenticated requests.

| Column | Type | Null | Notes |
|---|---|---|---|
| `user_id` | uuid | no | Primary key. API `user_id` |
| `clerk_user_id` | text | no | Unique. API `clerk_user_id`. Clerk account id |
| `email` | text | no | Primary email copied from Clerk |
| `role` | text | no | `SALES_REP` or `SALES_MANAGER` |
| `created_at` | timestamptz | no | |
| `updated_at` | timestamptz | no | |

**Indexes:** unique on `clerk_user_id`.

**Constraints:** `role` check. A row is upserted only when Clerk returns a valid `publicMetadata.role`. A Clerk user with no role metadata is `403 USER_NOT_PROVISIONED`.

---

## 4. organizations

| Column | Type | Null | Notes |
|---|---|---|---|
| `organization_id` | uuid | no | Primary key |
| `name` | text | no | Stored official name. The model must not rename it |
| `organization_type` | text | no | API enum: `university`, `college`, `k12_district`, `public_sector_education` |
| `market_role` | text | no | `target` or `competitor` (`DATA_SOURCES.md` target data model) |
| `tracking_status` | text | no | `active` or `inactive`. MVP scans use `active` only |
| `state_code` | char(2) | yes | USPS |
| `website_url` | text | yes | Official site root URL (for example `https://asu.edu`). Deep pages wait for `DATA_SOURCES.md` §5.3 |
| `ipeds_unit_id` | text | yes | Unique when present. Null for K-12 and agencies |
| `ipeds_collection_year` | text | yes | |
| `ipeds_release` | text | yes | `final` or `provisional` |
| `ipeds_source_url` | text | yes | Default meaning https://nces.ed.gov/ipeds/ until a deeper URL is verified |
| `ipeds_attributes` | jsonb | yes | Array of `{key, label, value}` from the loaded file only |
| `briefing_text` | text | yes | Organization briefing. Null when none |
| `briefing_status` | text | yes | `ready` or `unavailable` |
| `created_at` | timestamptz | no | |
| `updated_at` | timestamptz | no | |

**Indexes:** `organization_type`, `market_role`, `tracking_status`, `state_code`, unique `ipeds_unit_id` where not null, unique `website_url` where not null.

**Constraints:** `organization_type` check. `market_role` check. `tracking_status` check. `ipeds_release` check when not null. `ipeds_attributes` is not evidence and is never given a signal type.

`signal_count`, `opportunity_count`, and `last_scanned_at` in the API are queries, not stored counters.

Country is not a column. The product is United States only (`AGENTS.md` §3).

---

## 5. sources

One row per approved origin listed in `DATA_SOURCES.md`. Today that is SAM.gov, USAspending, and IPEDS only. Named organization websites are added only when a human writes them into `DATA_SOURCES.md` §5.3 — never as auto-created `website:<organization_id>` rows.

| Column | Type | Null | Notes |
|---|---|---|---|
| `source_id` | uuid | no | Primary key |
| `source_key` | text | no | Unique. Registry keys such as `sam_gov`, `usaspending`, `ipeds`. Future §5.3 sites use a stable key from that register |
| `name` | text | no | Evidence `source_name` for API/file origins |
| `official_url` | text | no | Registry entry URL from `DATA_SOURCES.md` |
| `source_kind` | text | no | `official_api`, `official_data_file`, `official_website` |
| `reliability_label` | text | yes | `official_api` or `official_website`. Null for IPEDS, which is not scored |
| `created_at` | timestamptz | no | |
| `updated_at` | timestamptz | no | |

**Constraints:** `source_kind` check. `reliability_label` null or one of the two scored labels in `DATA_SOURCES.md` §6.

**Decided 2026-09-24.** The organization's main site URL lives on `organizations.website_url`. Discovered page URLs live in `organization_sources` (§5a). Website documents do **not** require a `sources` row.

---

## 5b. source_request_log

Outbound calls to registry APIs so the application can enforce the SAM.gov safeguard of 10 requests per 24 hours (`DATA_SOURCES.md` §2.4). This is not a product-facing table.

| Column | Type | Null | Notes |
|---|---|---|---|
| `request_id` | uuid | no | Primary key |
| `source_key` | text | no | e.g. `sam_gov` |
| `requested_at` | timestamptz | no | |
| `http_status` | integer | yes | |
| `outcome` | text | no | `ok`, `error`, `quota_blocked`, `rejected` |
| `detail` | text | yes | Safe reason. Never the API key |

**Indexes:** `(source_key, requested_at)`.

**Constraints:** `outcome` check. Counts toward the daily cap use `ok`, `error`, and `rejected` only — a `quota_blocked` row records that the app refused to call out.

---

## 5a. organization_sources

Validated official **page** URLs for a tracked organization. Used by MVP discovery Scan and by
manager-added same-domain pages (`API_CONTRACT.md` §6.3a). Content fetch reads approved rows here;
it does not invent URLs.

| Column | Type | Null | Notes |
|---|---|---|---|
| `organization_source_id` | uuid | no | Primary key |
| `organization_id` | uuid | no | Foreign key to `organizations` |
| `url` | text | no | Final validated URL after redirects. Never an LLM-only string |
| `source_title` | text | yes | Short title from discovery or the page |
| `page_category` | text | no | Page category for discovery UI only — not a new signal type. Values: `procurement`, `technology`, `digital_learning`, `assessment`, `funding`, `leadership`, `strategic_initiative`, `partnership`, `news` (the organization's own news hub, `DATA_SOURCES.md` §5.2b) |
| `status` | text | no | `approved` or `rejected` |
| `extraction_status` | text | no | `pending`, `extracting`, `extracted`, `failed`. Default `pending`. `failed` means the page had no readable text without JavaScript |
| `is_official` | boolean | no | True when the final host is the org domain or a subdomain |
| `rejection_reason` | text | yes | Set when `status` is `rejected` |
| `last_validated_at` | timestamptz | no | Last successful validation attempt |
| `created_at` | timestamptz | no | |
| `updated_at` | timestamptz | no | |

**Indexes:** `(organization_id)`, `(status)`, unique `(organization_id, url)`.

**Constraints:** `page_category` check. `status` check. `extraction_status` check. `url` not empty.

Re-running discovery upserts on `(organization_id, url)` and refreshes `source_title`, `page_category`, `status`, `last_validated_at`. It does not insert duplicates. `url` is the exact final URL that was fetched; a `www` or trailing-slash variant of the same page is replaced, not kept as a second row.

---

## 6. documents

The bytes that were actually fetched (`FR-DATA-05`).

| Column | Type | Null | Notes |
|---|---|---|---|
| `document_id` | uuid | no | Primary key |
| `source_id` | uuid | yes | Foreign key to `sources`. Required for SAM.gov, USAspending, and IPEDS. Null for website documents — those use `organization_id` + `organization_source_id` and the org root on `organizations.website_url` |
| `organization_id` | uuid | yes | Foreign key. Null until a SAM.gov or USAspending record is matched. Required for a website fetch |
| `organization_source_id` | uuid | yes | Foreign key to `organization_sources`, `ON DELETE SET NULL`. The approved page this document came from. For a news article it is the news hub that linked to it. Null for SAM.gov and USAspending |
| `external_id` | text | yes | `noticeId`, award id, or UnitID when the source has one |
| `source_url` | text | no | URL that was fetched. Not a model string. No API key |
| `title` | text | yes | |
| `body_text` | text | no | Normalized text used for snippets and chunks. Empty string is not stored |
| `content_hash` | text | no | Hash of the normalized body |
| `published_on` | date | yes | Null means unavailable |
| `http_status` | integer | yes | |
| `data_origin` | text | no | `live` or `cached` |
| `retrieved_at` | timestamptz | no | Time of the fetch that produced the stored body. For cached rows, the original fetch time |
| `created_at` | timestamptz | no | |

**Indexes:** `(source_id, external_id)` unique where `external_id` is not null. `(organization_id, source_url)` unique where `external_id` is null and `organization_id` is not null: one current website document per organization and URL. `(source_id, content_hash)` so an unchanged document is not re-embedded. `(organization_id)`. `(organization_source_id)`.

**Constraints:** `data_origin` check. `body_text` length greater than 0. At least one of `source_id` or `organization_source_id` is set.

**Decided 2026-09-24.** A website page has one current document per organization and URL. An unchanged body (same hash) changes nothing. A changed body updates that same row in place (`body_text`, `content_hash`, `title`, `published_on`, `http_status`, `retrieved_at`), so `document_id` stays stable; its chunks are deleted and rebuilt, and it is extracted again. Website evidence later uses the organization name / page title for `source_name` and the `official_website` reliability label from `DATA_SOURCES.md` §6 — not a per-org `sources` row.

When evidence exists (signal phase): if an `evidence` row points at the old body, the old version is kept as history instead of being overwritten, marked not current, and is never used for new extraction or Advisor retrieval. The signal it supports may move to `superseded` if the new body no longer supports it. That rule adds an `is_current` flag and narrows the unique index to current rows; it is added with the evidence table, not before.

---

## 7. document_chunks and embeddings

One row per chunk. The embedding is a column on that row, not another table.

| Column | Type | Null | Notes |
|---|---|---|---|
| `chunk_id` | uuid | no | Primary key. Citation record id for retrieval |
| `document_id` | uuid | no | Foreign key. Delete chunks if the document is removed |
| `organization_id` | uuid | no | Foreign key. Copied from the document when it is known. A chunk without an organization is not inserted (`AI_RAG_DESIGN.md` §15) |
| `signal_id` | uuid | yes | Foreign key when this chunk is tied to one signal |
| `source_name` | text | no | |
| `source_url` | text | no | Stored URL |
| `published_on` | date | yes | |
| `content_role` | text | no | `signal_source` or `reference` |
| `data_origin` | text | no | `live` or `cached` |
| `chunk_text` | text | no | Verbatim slice of `documents.body_text` |
| `chunk_index` | integer | no | Order within the document |
| `embedding` | vector(N) | yes | Null until the embed call succeeds |
| `embedding_model` | text | yes | The `EMBEDDING_MODEL` value that produced `embedding` |
| `retrieved_at` | timestamptz | no | Copied from the document |
| `created_at` | timestamptz | no | |

**N = 1536** for Azure `text-embedding-3-small` (**Updated 2026-09-25**, B1). Changing the embedding model/width requires a new migration and a full re-index.

**Indexes:** `(organization_id)`, `(document_id, chunk_index)` unique, `(signal_id)`.

**Vector index:** not required at hackathon volume. Exact cosine search filtered by `organization_id` is acceptable (`AI_RAG_DESIGN.md` §17). Add an HNSW index only after N is known and a search is actually slow. Queries must ignore rows whose `embedding_model` is not the current model.

**Retrieval:** filter `organization_id` first, optionally `content_role` or `signal_id`, then cosine distance on `embedding`. The citation is this row's `source_name`, `source_url`, `published_on`, and `chunk_text`. The query never trusts a URL from the model.

**Constraints:** `content_role` and `data_origin` checks. `chunk_text` length greater than 0. `embedding` and `embedding_model` are both null or both set.

---

## 8. signals

| Column | Type | Null | Notes |
|---|---|---|---|
| `signal_id` | uuid | no | Primary key |
| `organization_id` | uuid | no | Foreign key |
| `signal_type` | text | no | One of the seven API values |
| `state` | text | no | `detected`, `validated`, `rejected`, `merged`, `superseded` |
| `title` | text | no | |
| `summary` | text | no | `summary_layer` is always `fact` |
| `published_on` | date | yes | API `date`. Null means unavailable |
| `merged_into_signal_id` | uuid | yes | Self foreign key. Set only when `state` is `merged` |
| `rejection_reason` | text | yes | Required when `state` is `rejected`. Codes from `AI_RAG_DESIGN.md` §5 |
| `ai_summary` | text | yes | Interpretation. Null if none |
| `data_origin` | text | no | |
| `created_at` | timestamptz | no | |
| `updated_at` | timestamptz | no | |

**Indexes:** `(organization_id, signal_type, state)`, `(organization_id, published_on)`, `(merged_into_signal_id)`.

**Constraints:**

- Type and state checks.
- `state = rejected` if and only if `rejection_reason` is not null.
- `state = merged` if and only if `merged_into_signal_id` is not null.
- `merged_into_signal_id` cannot equal `signal_id`.
- Only `validated` signals may be referenced from `opportunity_signals`.

`source_count` in the API is `count(evidence)` for this signal plus evidence that was merged onto it. Merged evidence stays on the surviving signal (§9). The incoming signal row remains so the merge event is visible.

Dedup tier 2 uses `documents.external_id` plus `signal_type` and `organization_id`. There is no separate fingerprint table.

---

## 9. evidence

This table is the signal source reference. It is also what the Advisor cites.

| Column | Type | Null | Notes |
|---|---|---|---|
| `evidence_id` | uuid | no | Primary key |
| `signal_id` | uuid | yes | Foreign key. Set when the snippet supports a signal. Advisor-only citations of a reference chunk may leave this null |
| `document_id` | uuid | no | Foreign key |
| `chunk_id` | uuid | yes | Foreign key when the snippet is a chunk |
| `source_id` | uuid | yes | Foreign key to `sources`. Set for SAM.gov / USAspending / IPEDS documents. Null for website documents (source name resolved from the organization) |
| `source_url` | text | no | Copied from the document. Must not contain a query key named `api_key` |
| `published_on` | date | yes | |
| `snippet` | text | no | Verbatim substring of `documents.body_text` for that `document_id` |
| `relationship` | text | no | Interpretation of why the snippet supports the parent |
| `data_origin` | text | no | |
| `retrieved_at` | timestamptz | no | |
| `created_at` | timestamptz | no | |

**Indexes:** `(signal_id)`, `(document_id)`, `(chunk_id)`.

**Constraints:** `snippet` length greater than 0. Application rule, checked before insert: `snippet` is a substring of the parent document body (`AI_RAG_DESIGN.md` §5). A signal that is `validated` or `merged` onto a survivor must have at least one evidence row (`FR-SIG-02`). The database does not express that with a cross-table check. The pipeline rejects the candidate first.

A merge copies nothing away. Additional evidence rows point at the surviving `signal_id`. Old rows are not deleted (`FR-EV-04`).

`source_name` in the API is `sources.name` through `document.source_id` when that FK is set (SAM.gov, USAspending, IPEDS). For website documents (`source_id` null), it is the organization name or page title from `organization_sources`. It is not copied onto every evidence row.

---

## 10. Signal relationships

Two mechanisms, no extra graph table.

**Cluster.** `signals.merged_into_signal_id` points at the surviving signal. Every evidence row for the cluster uses that surviving id. The merged row stays in `signals` with `state = merged`.

**Correlation.** `opportunity_signals` lists the validated signals that were grouped into one potential opportunity. The reason text lives on `opportunities.correlation_text`, not on each pair. Pairwise "why A relates to B" rows are not stored. The hackathon shows one reason for the set (`FR-COR-02`).

---

## 11. opportunities

| Column | Type | Null | Notes |
|---|---|---|---|
| `opportunity_id` | uuid | no | Primary key |
| `organization_id` | uuid | no | Foreign key. **Unique.** One opportunity per organization |
| `label` | text | no | Always `potential_opportunity` |
| `correlation_text` | text | no | Interpretation |
| `recommended_action_text` | text | yes | Null when no cited recommendation was produced |
| `data_origin` | text | no | `cached` if any contributing evidence is cached |
| `created_at` | timestamptz | no | |
| `updated_at` | timestamptz | no | |

**Indexes:** unique `organization_id`.

A later scan updates this row and inserts a new `opportunity_scores` row. It does not insert a second opportunity. If the new score is below 50, the row remains (`AI_RAG_DESIGN.md` §25).

---

## 12. opportunity_signals

| Column | Type | Null | Notes |
|---|---|---|---|
| `opportunity_id` | uuid | no | Foreign key, cascade delete |
| `signal_id` | uuid | no | Foreign key. Must be `validated` |
| `created_at` | timestamptz | no | |

**Primary key:** `(opportunity_id, signal_id)`.

**Index:** `signal_id` so a signal detail can list `opportunity_ids`.

Replacing the set on rescore deletes rows for signals that left the group and inserts the current set in the same transaction as the new score.

---

## 13. opportunity_scores

Append-only. The API current score is the latest row by `scored_at`. `previous_value` is the `value` of the prior row, or null on the first score.

| Column | Type | Null | Notes |
|---|---|---|---|
| `score_id` | uuid | no | Primary key |
| `opportunity_id` | uuid | no | Foreign key |
| `value` | smallint | no | 0 through 100. Rules output only |
| `band` | text | no | `high`, `medium`, `low`, `monitor` |
| `weight_version` | text | no | `v1` until a later version is approved |
| `procurement_relevance` | smallint | no | 0–30 |
| `related_signal_strength` | smallint | no | 0–25 |
| `assessment_edtech_relevance` | smallint | no | 0–20 |
| `recency` | smallint | no | 0–15 |
| `source_reliability` | smallint | no | 0–10 |
| `explanation_text` | text | yes | |
| `explanation_status` | text | no | `ready` or `unavailable` |
| `scored_at` | timestamptz | no | API `scored_at` |

**Indexes:** `(opportunity_id, scored_at desc)`.

**Constraints:**

- `value` between 0 and 100.
- Each factor between 0 and its max.
- `value` equals the sum of the five factor columns.
- `band` matches the `v1` ranges for that `value` while `weight_version` is `v1`.
- `explanation_status = ready` if and only if `explanation_text` is not null.
- No column is named in a way that the application would fill it from the model. The insert happens before the explanation update. A failed explanation leaves `explanation_status = unavailable` and does not change `value`.

Explanation evidence ids are `ai_interactions` rows of kind `score_explanation` pointing at this `score_id`, not a second copy of the number.

---

## 14. signal_state_events

| Column | Type | Null | Notes |
|---|---|---|---|
| `event_id` | uuid | no | Primary key |
| `signal_id` | uuid | no | Foreign key |
| `from_state` | text | yes | Null on the first insert |
| `to_state` | text | no | |
| `reason` | text | yes | Rejection code or merge note |
| `created_at` | timestamptz | no | |

**Index:** `(signal_id, created_at)`.

The pipeline inserts one event in the same transaction as the signal update. This is the audit trail for signal state. There is no general change-data-capture table.

---

## 15. scan_batches and scan_runs

### 15.1 scan_batches

| Column | Type | Null | Notes |
|---|---|---|---|
| `batch_id` | uuid | no | Primary key |
| `created_at` | timestamptz | no | |

Batch status in the API is derived from child runs, not stored.

### 15.2 scan_runs

| Column | Type | Null | Notes |
|---|---|---|---|
| `scan_id` | uuid | no | Primary key |
| `batch_id` | uuid | yes | Foreign key. Null for Scan Now |
| `organization_id` | uuid | no | Foreign key |
| `trigger` | text | no | `manual` or `scheduled` |
| `requested_by_user_id` | uuid | yes | Foreign key to `app_users`, `ON DELETE SET NULL`. The signed-in user who started a manual scan. Null for scheduled scans and for runs created before this column |
| `status` | text | no | API scan status |
| `stage` | text | yes | API scan stage. Null when queued or finished |
| `sources` | jsonb | no | Array of `{source_name, status, detail}`. Default `[]` |
| `signals_created` | integer | no | Default 0 |
| `signals_updated` | integer | no | Default 0 |
| `opportunities_created` | integer | no | Default 0 |
| `opportunities_updated` | integer | no | Default 0 |
| `candidates_found` | integer | no | Default 0. MVP discovery count |
| `sources_approved` | integer | no | Default 0. MVP discovery count |
| `sources_rejected` | integer | no | Default 0. MVP discovery count |
| `documents_collected` | integer | no | Default 0. Documents inserted or replaced because their content changed in this run. Unchanged pages add 0 |
| `error_detail` | text | yes | Safe failure summary. Never secrets |
| `started_at` | timestamptz | yes | |
| `finished_at` | timestamptz | yes | |
| `created_at` | timestamptz | no | |
| `updated_at` | timestamptz | no | |

**Indexes:** `(organization_id, started_at desc)`. Partial unique index on `organization_id` where `status` is `queued` or `running`. That is the one-active-scan rule (AD-04).

**Constraints:** status and trigger checks. `stage` null or a scan stage. Counts greater than or equal to 0. `finished_at` is null while status is `queued` or `running`.

`joined_existing` is not stored. The API sets it when the insert hits the partial unique index and returns the existing row.

Score movements in the scan payload are read from `opportunity_scores` for that `organization_id` with `scored_at` inside the run window. They are not copied onto the scan row.

Startup marks `queued` and `running` rows as `interrupted` (`TECHNICAL_PRD.md` §7.2).

---

## 16. advisor_sessions and ai_interactions

### 16.1 advisor_sessions

| Column | Type | Null | Notes |
|---|---|---|---|
| `session_id` | uuid | no | Primary key |
| `scope_type` | text | no | `organization` or `opportunity` |
| `scope_id` | uuid | no | The organization or opportunity id |
| `organization_id` | uuid | no | Foreign key. Always the organization in scope, so retrieval cannot cross tenants of the data |
| `created_at` | timestamptz | no | |
| `updated_at` | timestamptz | no | |

**Constraints:** `scope_type` check. If `scope_type` is `organization`, `scope_id` equals `organization_id`. If `opportunity`, `scope_id` must exist in `opportunities` and that row's `organization_id` must match.

### 16.2 ai_interactions

Every model result that is kept: score explanation, correlation, recommendation, organization briefing, competitor briefing, and Advisor turns. Prompt version is stored so a later prompt does not pretend to be the old text.

| Column | Type | Null | Notes |
|---|---|---|---|
| `ai_interaction_id` | uuid | no | Primary key |
| `kind` | text | no | `score_explanation`, `correlation`, `recommendation`, `org_briefing`, `competitor_briefing`, `advisor_user`, `advisor_answer` |
| `session_id` | uuid | yes | Foreign key. Required for Advisor kinds |
| `scan_id` | uuid | yes | Foreign key when the scan produced it |
| `organization_id` | uuid | yes | Foreign key |
| `opportunity_id` | uuid | yes | Foreign key |
| `score_id` | uuid | yes | Foreign key for `score_explanation` |
| `prompt_id` | text | yes | From `AI_RAG_DESIGN.md` §20. Null for `advisor_user` |
| `prompt_version` | text | yes | |
| `advisor_status` | text | yes | Set on `advisor_answer` |
| `body_text` | text | no | The stored prose or the user message |
| `content_layer` | text | yes | `fact`, `interpretation`, `recommended_action`. Null for a user turn |
| `evidence_ids` | uuid[] | no | Default `{}`. Ids must exist in `evidence` at insert time. The application checks. An array is used so this table does not need a junction for the hackathon |
| `created_at` | timestamptz | no | |

**Indexes:** `(session_id, created_at)`, `(opportunity_id, kind, created_at desc)`, `(organization_id, kind, created_at desc)`.

**Constraints:** `kind` check. Advisor kinds require `session_id`. `score_explanation` requires `score_id`. `advisor_status` uses the API enum when kind is `advisor_answer`.

The session read returns the latest turns, at most 4 user and 4 advisor, oldest first. Older rows may remain. They are not sent to the model (`AI_RAG_DESIGN.md` §23).

Organization briefing text is also copied onto `organizations.briefing_text` so the profile does not have to search this table. The interaction row is the record of which prompt produced it.

---

## 17. Audit

| Need | Where |
|---|---|
| Who the user is | `app_users`. No password audit |
| When a row was written or changed | `created_at`, `updated_at` |
| When a signal changed state, and why | `signal_state_events` |
| When a document was fetched | `documents.retrieved_at` |
| When a score was computed, and under which weights | `opportunity_scores.scored_at`, `weight_version` |
| Which prompt wrote an AI text | `ai_interactions.prompt_id`, `prompt_version` |
| Whether a fact is cached | `data_origin` and `retrieved_at` on documents, chunks, evidence, signals, opportunities |

There is no `created_by` on intelligence rows. Scans are system writes. Advisor turns are tied to a session, not to a second copy of the Clerk id. Adding `user_id` on `advisor_sessions` is optional and not required for the MVP, because both roles see the same sessions' underlying evidence. Do not add it unless a later decision says sessions are private.

---

## 18. How API reads are satisfied

| API field | Query |
|---|---|
| `GET /me` | `app_users` by `clerk_user_id` |
| Organization list | `organizations` plus counts |
| Signal `source_count` and `evidence` | `evidence` joined to `sources` |
| Opportunity score | Latest `opportunity_scores` row |
| `previous_value` | The row before that |
| Dashboard band counts | Latest score per opportunity |
| Scan changes | Count columns on `scan_runs` |
| Advisor session | `advisor_sessions` and `ai_interactions` |

No view is required for the MVP. The repository may add a SQL view later without changing these tables.

---

## 19. Integrity rules the application must enforce

The database holds the foreign keys and the checks above. These rules stay in the pipeline because they look at text, not only keys:

- Snippet is a verbatim substring of the document body.
- A validated signal has at least one evidence row.
- Evidence URL equals the document URL.
- Score value is computed in `app/scoring/` and inserted as given. No trigger calls an LLM.
- Advisor `evidence_ids` are a subset of ids that were retrieved for that organization.
- `ipeds_attributes` keys come from the loaded data dictionary.

---

## Open questions

| # | Item | Status |
|---|---|---|
| B1 | Vector dimension N | **Updated 2026-09-25.** Azure OpenAI `text-embedding-3-small` via embedding adapter → `vector(1536)`. Chat remains Azure `interns-gpt-4.1`. Local/Groq embedding defaults removed. |
| B2 | ANN index | **Deferred.** Exact search until volume says otherwise |
| B3 | `evidence_ids` as `uuid[]` | **Chosen** to avoid a junction table. The application must reject unknown ids. A junction is only worth adding if that check is skipped |
| B4 | IPEDS column names inside `ipeds_attributes` | Still `NEEDS VERIFICATION` in `DATA_SOURCES.md` D5. The jsonb array can hold them without a schema change |
| B5 | Named organizations and website `sources` rows | **Updated 2026-09-23.** Ten TARGET organizations are seeded. Two are `active` (ASU, UCF). Page URLs from MVP discovery land in `organization_sources` (§5a). Registry `sources` website rows and `DATA_SOURCES.md` §5.3 collection allowlist remain for content fetch |
