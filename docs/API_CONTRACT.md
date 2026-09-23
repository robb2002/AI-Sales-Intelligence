# API Contract

> **Status:** DRAFT — awaiting approval
> **Version:** 0.1
> **Date:** 2026-09-23
> **Authoring order:** 6 of 9
> **Depends on:** `PRODUCT_PRD.md`, `TECHNICAL_PRD.md` AD-06, `AUTHENTICATION.md`, `AI_RAG_DESIGN.md`, `DATA_SOURCES.md`
> **`DATABASE_DESIGN.md`:** still a placeholder. JSON names in this document are the contract. The schema must adopt them. It does not invent a second set of names.
> **Primary author:** Developer 2, agreed with Developer 1 and Developer 3

## Purpose

The only interface between the React app and FastAPI. Both sides build against this file. A field that is not here is not returned and is not required.

Login, logout, and passwords are Clerk. This API does not implement them (`AUTHENTICATION.md`).

Examples use angle-bracket placeholders. They are not sample organizations, notices, or scores.

---

## 1. Conventions

| Item | Rule |
|---|---|
| Base path | `/api/v1` |
| Format | JSON. `Content-Type: application/json` |
| Names | `snake_case` for fields and query parameters |
| Ids | UUID strings |
| Timestamps | ISO-8601 UTC, `YYYY-MM-DDTHH:MM:SSZ` |
| Dates | `YYYY-MM-DD`, or `null` when the source did not provide one |
| Missing date | `date` is `null` and `date_status` is `unavailable`. Never omit the pair. Never send a guessed date |
| Booleans | `true` / `false`. Absent means the field was not allowed, not false |
| Null | A nullable field is present and `null`. Do not drop the key |
| Auth header | `Authorization: Bearer <Clerk session token>` on every path except `GET /api/v1/health` |
| Roles | `SALES_REP` and `SALES_MANAGER`. Both may call every protected endpoint. Responses are not filtered by user (`FR-ROLE-04`) |

### 1.1 Content layers

User-facing prose that the AI produced or that quotes a source includes `content_layer`:

| Value | Meaning |
|---|---|
| `fact` | What a stored source stated |
| `interpretation` | What the system inferred |
| `potential_opportunity` | The correlated set. The noun in copy is still "potential opportunity" |
| `recommended_action` | A next step for a human |

### 1.2 Enums

**Organization type:** `university`, `college`, `k12_district`, `public_sector_education`

**Signal type:** `procurement`, `technology_initiative`, `leadership_change`, `funding_budget`, `strategic_announcement`, `competitor_vendor`, `contract_renewal`

**Signal state:** `detected`, `validated`, `rejected`, `merged`, `superseded`

**Score band:** `high` (75–100), `medium` (50–74), `low` (25–49), `monitor` (0–24)

**Score factor key:** `procurement_relevance`, `related_signal_strength`, `assessment_edtech_relevance`, `recency`, `source_reliability`

**Data origin:** `live` or `cached`

**Scan status:** `queued`, `running`, `succeeded`, `partial`, `failed`, `interrupted`

**Scan stage:** `collecting`, `extracting`, `validating`, `deduplicating`, `correlating`, `scoring`

**Source result:** `succeeded`, `failed`, `skipped`

**Advisor status:** `answered`, `insufficient_evidence`, `out_of_scope`, `unavailable`

---

## 2. Authentication

Clerk has already signed the user in. These rules are from `AUTHENTICATION.md` §10.

| Situation | HTTP | `error.code` |
|---|---|---|
| Missing or empty bearer token | 401 | `AUTH_MISSING` |
| Token invalid or not from this Clerk instance | 401 | `AUTH_INVALID` |
| Token expired | 401 | `AUTH_EXPIRED` |
| Valid token, no application user row | 403 | `USER_NOT_PROVISIONED` |
| Valid token, role missing or not one of the two codes | 403 | `USER_WITHOUT_ROLE` |
| Valid role, operation not allowed for that role | 403 | `INSUFFICIENT_PERMISSION` |

A 401 or 403 body contains no organizations, signals, scores, or evidence.

There is no login, logout, or refresh endpoint.

### 2.1 Current user

| | |
|---|---|
| Method / path | `GET /api/v1/me` |
| Auth | Bearer required |
| Roles | `SALES_REP`, `SALES_MANAGER` |
| Request | No body. No query |
| Pagination / filter / sort | None |

**200**

```json
{
  "user_id": "<uuid>",
  "clerk_user_id": "<clerk id>",
  "role": "SALES_REP"
}
```

`role` is the PostgreSQL value, not a Clerk metadata claim.

**Errors:** 401 and 403 as in §2.

**Validation:** none beyond the token.

The sidebar uses this role. Display name and email come from the Clerk session on the client, not from this payload (`AUTHENTICATION.md` §9).

### 2.2 Health

| | |
|---|---|
| Method / path | `GET /api/v1/health` |
| Auth | Public |
| Roles | None |
| Request | None |

**200**

```json
{ "status": "ok" }
```

No version secrets, no counts, no user data. Any other failure on this path may be an empty 500. It is the only public route.

---

## 3. Error envelope

Every error body, including 401 and 403:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "<plain sentence>",
    "details": {}
  }
}
```

| HTTP | When | `code` |
|---|---|---|
| 400 | Query or body failed validation | `VALIDATION_ERROR` |
| 401 | §2 | `AUTH_MISSING`, `AUTH_INVALID`, `AUTH_EXPIRED` |
| 403 | §2 | `USER_NOT_PROVISIONED`, `USER_WITHOUT_ROLE`, `INSUFFICIENT_PERMISSION` |
| 404 | Id not in the database | `NOT_FOUND` |
| 429 | Scan or Advisor limit | `SCAN_RATE_LIMITED`, `ADVISOR_RATE_LIMITED` |
| 500 | Unhandled server failure | `INTERNAL_ERROR` |

`details` for `VALIDATION_ERROR` is a map of field name to a short reason. For `NOT_FOUND`, `details.resource` is `organization`, `signal`, `opportunity`, `scan`, `scan_batch`, `evidence`, or `advisor_session`. For 429, `details.retry_after_seconds` is an integer.

`message` does not include stack traces, tokens, or provider keys.

`SCAN_ALREADY_RUNNING` is not an error. A second Scan Now returns the running scan with `joined_existing` true (§8).

---

## 4. Pagination

List endpoints use offset pagination.

| Query | Rule |
|---|---|
| `limit` | Integer. Default 20. Minimum 1. Maximum 100 |
| `offset` | Integer. Default 0. Minimum 0 |

```json
{
  "data": [],
  "page": { "limit": 20, "offset": 0, "total": 0 }
}
```

`total` is the count after filters, before limit. `data` is empty when nothing matches. That is 200, not 404.

An invalid `limit` or `offset` is 400 `VALIDATION_ERROR`.

---

## 5. Shared objects

### 5.1 Evidence

```json
{
  "evidence_id": "<uuid>",
  "source_name": "<registry or website name>",
  "source_url": "<stored public url>",
  "date": null,
  "date_status": "unavailable",
  "snippet": "<verbatim text from the source>",
  "relationship": "<why this snippet supports the parent>",
  "relationship_layer": "interpretation",
  "data_origin": "live",
  "retrieved_at": "<timestamp>"
}
```

`source_url` never contains an API key. `snippet` is text that was stored from the source, not written by the model. A cached item has `data_origin` `cached` and `retrieved_at` set to the original fetch.

### 5.2 Score

Present only on an opportunity. Never a bare number.

```json
{
  "value": 0,
  "band": "monitor",
  "weight_version": "v1",
  "factors": [
    { "key": "procurement_relevance", "points": 0, "max_points": 30 },
    { "key": "related_signal_strength", "points": 0, "max_points": 25 },
    { "key": "assessment_edtech_relevance", "points": 0, "max_points": 20 },
    { "key": "recency", "points": 0, "max_points": 15 },
    { "key": "source_reliability", "points": 0, "max_points": 10 }
  ],
  "explanation": null,
  "explanation_status": "unavailable"
}
```

`value` is the rules total. The five factors are always present and sum to `value`. `explanation`, when present, is `{ "text": "<prose>", "content_layer": "interpretation", "evidence_ids": ["<uuid>"] }` and `explanation_status` is `ready`. The prose must repeat `value`. If the model did not return a usable explanation, `explanation` is `null` and `explanation_status` is `unavailable`. The number is still returned.

`previous_value` is `null` or an integer when the score has changed. `scored_at` is a timestamp.

### 5.3 Signal summary and signal detail

Summary (lists and nested cards):

```json
{
  "signal_id": "<uuid>",
  "organization_id": "<uuid>",
  "organization_name": "<stored name>",
  "signal_type": "procurement",
  "state": "validated",
  "title": "<factual title>",
  "summary": "<what the source stated>",
  "summary_layer": "fact",
  "date": null,
  "date_status": "unavailable",
  "source_count": 1,
  "data_origin": "live"
}
```

Detail adds `rejection_reason` (`null` unless `state` is `rejected`), `opportunity_ids` (array, possibly empty), `ai_summary` (`null` or `{ "text", "content_layer": "interpretation", "evidence_ids" }`), and `evidence` (array of §5.1, one item per source reference). A merged cluster has `source_count` equal to `evidence.length`. A rejected signal still includes the evidence it had and a non-null `rejection_reason`.

### 5.4 Opportunity summary and detail

Summary:

```json
{
  "opportunity_id": "<uuid>",
  "organization_id": "<uuid>",
  "organization_name": "<stored name>",
  "organization_type": "university",
  "state_code": "<USPS code or null>",
  "score": {},
  "signal_count": 0,
  "updated_at": "<timestamp>",
  "data_origin": "live"
}
```

`score` on a summary is the full §5.2 object, not a lone integer.

Detail adds:

| Field | Shape |
|---|---|
| `signals` | Array of signal summaries that belong to this opportunity |
| `correlation` | `{ "text", "content_layer": "interpretation", "evidence_ids" }` |
| `recommended_action` | `null` or `{ "text", "content_layer": "recommended_action", "evidence_ids" }` |
| `evidence` | Array of §5.1 for every evidence item behind those signals |
| `label` | Always `potential_opportunity` |

### 5.5 Organization

```json
{
  "organization_id": "<uuid>",
  "name": "<stored name>",
  "organization_type": "k12_district",
  "state_code": "<USPS or null>",
  "website_url": "<official site or null>",
  "signal_count": 0,
  "opportunity_count": 0,
  "last_scanned_at": null,
  "data_origin": "live"
}
```

Detail adds `ipeds` and `last_scan`.

`ipeds` is `null` for K-12 and public-sector bodies, and `null` when the file was not loaded. When present:

```json
{
  "content_layer": "fact",
  "source_name": "NCES IPEDS",
  "source_url": "https://nces.ed.gov/ipeds/",
  "unit_id": "<string or null>",
  "collection_year": "<string or null>",
  "release": "final",
  "attributes": []
}
```

`release` is `final` or `provisional`. `attributes` is a list of `{ "key", "label", "value" }` taken from the loaded file. Keys are not invented beyond what that file's dictionary contains. IPEDS is never given a signal type.

`last_scan` is a scan summary (§5.6) or `null`.

### 5.6 Scan summary

```json
{
  "scan_id": "<uuid>",
  "organization_id": "<uuid>",
  "organization_name": "<stored name>",
  "status": "running",
  "stage": "collecting",
  "trigger": "manual",
  "started_at": "<timestamp>",
  "finished_at": null,
  "joined_existing": false,
  "data_origin": "live"
}
```

`trigger` is `manual` or `scheduled`. `stage` is `null` when the run has not started or has finished.

Detail adds `sources`, `changes`, and `batch_id` (`null` when the run was not part of Scan All).

```json
{
  "sources": [
    {
      "source_name": "SAM.gov",
      "status": "failed",
      "detail": "<short reason or null>"
    }
  ],
  "changes": {
    "signals_created": 0,
    "signals_updated": 0,
    "opportunities_created": 0,
    "opportunities_updated": 0,
    "score_changes": []
  }
}
```

`score_changes` items are `{ "opportunity_id", "previous_value", "value" }`. Counts are zero when `status` is `succeeded` and nothing new was found. That is success, not an error.

### 5.7 Advisor answer

```json
{
  "session_id": "<uuid>",
  "scope_type": "organization",
  "scope_id": "<uuid>",
  "advisor_status": "answered",
  "answer": {
    "text": "<prose with fact and interpretation marked in the text>",
    "segments": [
      {
        "text": "<sentence>",
        "content_layer": "fact",
        "evidence_ids": ["<uuid>"]
      }
    ]
  },
  "evidence": [],
  "data_origin": "live"
}
```

`segments` is the structured form of the four layers. A `fact` segment has at least one `evidence_id`. An `interpretation` segment may cite ids. `evidence` resolves those ids to §5.1 objects.

When `advisor_status` is `insufficient_evidence` or `out_of_scope`, `answer.segments` is empty and `answer.text` states that result. `evidence` is empty. HTTP status is still 200.

When `advisor_status` is `unavailable`, the model did not return a usable answer. `answer.text` says the Advisor is unavailable. HTTP status is 200.

---

## 6. Organizations

### 6.1 List and search

| | |
|---|---|
| Method / path | `GET /api/v1/organizations` |
| Auth | Bearer |
| Roles | Both |
| Pagination | §4 |

**Query**

| Parameter | Validation |
|---|---|
| `q` | Optional. 0 to 200 characters. Matches organization name. Empty is the same as omitted. Fewer than 2 characters returns `data: []` and `total: 0` without an error, so the global search box can stay quiet |
| `organization_type` | Optional. Repeatable. Each value must be an organization type |
| `state_code` | Optional. Repeatable. Two-letter USPS code |
| `has_opportunities` | Optional. `true` or `false` |
| `sort` | `name` or `recently_scanned`. Default `name` |
| `direction` | `asc` or `desc`. Default `asc` for `name`, `desc` for `recently_scanned` |

**200:** page of organization summaries (§5.5).

**Errors:** 400, 401, 403.

This is the only organization search. There is no `/search` route.

### 6.2 Detail

| | |
|---|---|
| Method / path | `GET /api/v1/organizations/{organization_id}` |
| Auth | Bearer |
| Roles | Both |

**200:** organization detail (§5.5).

**Errors:** 401, 403, 404 `NOT_FOUND` with `details.resource` `organization`.

Signals and opportunities for the organization are not inlined. The client calls §7.1 and §8.1 with `organization_id`.

---

## 7. Signals

### 7.1 List

| | |
|---|---|
| Method / path | `GET /api/v1/signals` |
| Auth | Bearer |
| Roles | Both |
| Pagination | §4 |

**Query**

| Parameter | Validation |
|---|---|
| `organization_id` | Optional UUID |
| `signal_type` | Optional. Repeatable enum |
| `state` | Optional. Repeatable enum. Default, when omitted: `validated` only. Pass `state=rejected` to inspect discards. Pass every state explicitly to see all |
| `date_from` | Optional `YYYY-MM-DD` |
| `date_to` | Optional `YYYY-MM-DD`. Must be on or after `date_from` |
| `q` | Optional. 0 to 200 characters. Title and summary |
| `sort` | `date` or `type`. Default `date` |
| `direction` | `asc` or `desc`. Default `desc` |

Signals with `date_status` `unavailable` sort after dated signals when `direction` is `desc`, and are not dropped by a date filter. A date filter applies only to signals that have a date. The response does not hide undated signals unless the client also sent a state or type filter that excludes them. If that rule is too broad for a UI date picker, the client sends `date_from` and understands undated rows remain. Documented so both sides implement the same rule.

**200:** page of signal summaries.

**Errors:** 400, 401, 403. Unknown `organization_id` is 200 with `total` 0, not 404. A bad UUID is 400.

### 7.2 Detail

| | |
|---|---|
| Method / path | `GET /api/v1/signals/{signal_id}` |
| Auth | Bearer |
| Roles | Both |

**200:** signal detail (§5.3).

**Errors:** 401, 403, 404.

No create, update, or delete. Users cannot correct a signal in the MVP.

---

## 8. Opportunities

### 8.1 List

| | |
|---|---|
| Method / path | `GET /api/v1/opportunities` |
| Auth | Bearer |
| Roles | Both |
| Pagination | §4 |

**Query**

| Parameter | Validation |
|---|---|
| `organization_id` | Optional UUID |
| `organization_type` | Optional. Repeatable |
| `state_code` | Optional. Repeatable USPS |
| `band` | Optional. Repeatable score band |
| `date_from` | Optional. Filters on `updated_at` date |
| `date_to` | Optional. On or after `date_from` |
| `sort` | `score` or `updated_at`. Default `score` |
| `direction` | `asc` or `desc`. Default `desc` |

**200:** page of opportunity summaries, each with a full score object.

**Errors:** 400, 401, 403.

### 8.2 Detail

| | |
|---|---|
| Method / path | `GET /api/v1/opportunities/{opportunity_id}` |
| Auth | Bearer |
| Roles | Both |

**200:** opportunity detail (§5.4).

**Errors:** 401, 403, 404.

No create or delete endpoint. Opportunities appear only after a scan applies the generation rule.

---

## 9. Scanning

### 9.1 Scan Now

| | |
|---|---|
| Method / path | `POST /api/v1/organizations/{organization_id}/scans` |
| Auth | Bearer |
| Roles | Both |
| Body | Empty object `{}` or no body |

**202:** scan detail (§5.6). `status` is `queued` or `running`.

If a scan for that organization is already `queued` or `running`, the response is **200** with that same scan and `joined_existing` true. The client attaches to it. This is not a 409.

**Errors:** 401, 403, 404 if the organization does not exist, 429 `SCAN_RATE_LIMITED` when the caller is starting scans faster than `FR-SCAN-06` allows.

**Validation:** `organization_id` must be a UUID of a tracked organization.

### 9.2 Scan All

| | |
|---|---|
| Method / path | `POST /api/v1/scans` |
| Auth | Bearer |
| Roles | Both |
| Body | `{ "scope": "all_tracked" }` |

Any other `scope` is 400. There is no body that accepts an arbitrary URL or an untracked name.

**202**

```json
{
  "batch_id": "<uuid>",
  "status": "running",
  "scan_ids": ["<uuid>"],
  "organization_count": 0
}
```

Each id is a scan for one tracked organization. Organizations that already have an active scan contribute that existing scan id. The batch does not start a second run for them.

**Errors:** 401, 403, 429 `SCAN_RATE_LIMITED`.

### 9.3 Get one scan

| | |
|---|---|
| Method / path | `GET /api/v1/scans/{scan_id}` |
| Auth | Bearer |
| Roles | Both |

**200:** scan detail. The client polls this about every 2 seconds while `status` is `queued` or `running`, and stops on a terminal status.

**Errors:** 401, 403, 404.

### 9.4 Get a Scan All batch

| | |
|---|---|
| Method / path | `GET /api/v1/scan-batches/{batch_id}` |
| Auth | Bearer |
| Roles | Both |

**200**

```json
{
  "batch_id": "<uuid>",
  "status": "running",
  "organization_count": 0,
  "completed_count": 0,
  "scans": []
}
```

`scans` is an array of scan summaries. `status` is `running` until every child is terminal, then `succeeded` if all succeeded, `partial` if any child is `partial` or `failed` while another succeeded, `failed` if all failed, `interrupted` if any child is `interrupted` and none are still running.

**Errors:** 401, 403, 404.

### 9.5 List scans

| | |
|---|---|
| Method / path | `GET /api/v1/scans` |
| Auth | Bearer |
| Roles | Both |
| Pagination | §4 |

**Query:** optional `organization_id` (UUID), optional `status` (repeatable scan status). Sort is fixed: `started_at` descending. No other sort.

**200:** page of scan summaries.

Used by the header scan indicator and the organization "last scanned" context. The latest row for the whole system is `offset=0&limit=1`.

---

## 10. Dashboard

| | |
|---|---|
| Method / path | `GET /api/v1/dashboard` |
| Auth | Bearer |
| Roles | Both |
| Query | None |
| Pagination | None. The lists inside are capped |

**200**

```json
{
  "generated_at": "<timestamp>",
  "data_origin": "live",
  "opportunities": {
    "total": 0,
    "by_band": { "high": 0, "medium": 0, "low": 0, "monitor": 0 },
    "new_since": "<timestamp>",
    "new_count": 0
  },
  "signals": {
    "validated_total": 0,
    "by_type": {
      "procurement": 0,
      "technology_initiative": 0,
      "leadership_change": 0,
      "funding_budget": 0,
      "strategic_announcement": 0,
      "competitor_vendor": 0,
      "contract_renewal": 0
    },
    "recent_window_days": 30,
    "recent_count": 0
  },
  "competitor_vendor": {
    "validated_total": 0,
    "new_in_window": 0
  },
  "scan_status": {
    "state": "never_scanned",
    "last_finished_at": null,
    "running": false,
    "last_status": null,
    "sources_failed": 0
  },
  "prioritized_opportunities": [],
  "recent_signals": [],
  "signal_volume": [],
  "ai_insights": []
}
```

| Field | Rule |
|---|---|
| `new_since` | Start of the window for `new_count`. Fixed at 7 days before `generated_at` |
| `scan_status.state` | `never_scanned`, `current`, `running`, `partial`, `failed` |
| `prioritized_opportunities` | At most 5 opportunity summaries, highest score first |
| `recent_signals` | At most 6 validated signal summaries, newest first |
| `signal_volume` | 30 items, one per day, oldest first: `{ "date", "count" }`. A day with none is `count` 0, not a missing point |
| `ai_insights` | Zero to three items: `{ "text", "content_layer": "interpretation", "evidence_ids", "evidence" }`. Empty array when there is nothing grounded to say. Never a fabricated insight |
| `data_origin` | `cached` if any included figure depends on cached evidence. Otherwise `live` |

All zeros and empty arrays are the honest empty dashboard. HTTP 200.

**Errors:** 401, 403, 500.

Drill-down is not a second dashboard route. The client opens §8.1 or §7.1 with the matching filter. Competitor totals match `signal_type=competitor_vendor`.

---

## 11. Evidence

Evidence is embedded on signal detail, opportunity detail, dashboard insights, and Advisor answers so a card can render in one response.

One extra read exists for a citation that only has an id:

| | |
|---|---|
| Method / path | `GET /api/v1/evidence/{evidence_id}` |
| Auth | Bearer |
| Roles | Both |

**200:** one §5.1 object.

**Errors:** 401, 403, 404.

No list-all-evidence endpoint. No upload.

---

## 12. AI Sales Advisor

### 12.1 Ask

| | |
|---|---|
| Method / path | `POST /api/v1/advisor/questions` |
| Auth | Bearer |
| Roles | Both |

**Body**

```json
{
  "scope_type": "organization",
  "scope_id": "<uuid>",
  "message": "<question>",
  "session_id": null
}
```

| Field | Validation |
|---|---|
| `scope_type` | `organization` or `opportunity` |
| `scope_id` | UUID of that resource. 404 if it does not exist |
| `message` | Required string, 1 to 2000 characters after trim. Empty is 400 |
| `session_id` | `null` to start a session. Otherwise a UUID of a session whose scope matches this request. A mismatch is 400 `VALIDATION_ERROR` |

**200:** §5.7. This includes insufficient evidence, out of scope, and unavailable. Those are not 4xx or 5xx.

The server keeps at most the last 4 turns on the session. The client still sends the new `message`. It does not send the transcript back.

**Errors:** 400, 401, 403, 404, 429 `ADVISOR_RATE_LIMITED`.

The Advisor does not create signals, opportunities, scans, or scores.

### 12.2 Get session

| | |
|---|---|
| Method / path | `GET /api/v1/advisor/sessions/{session_id}` |
| Auth | Bearer |
| Roles | Both |

**200**

```json
{
  "session_id": "<uuid>",
  "scope_type": "organization",
  "scope_id": "<uuid>",
  "turns": [
    {
      "role": "user",
      "text": "<message>",
      "created_at": "<timestamp>"
    },
    {
      "role": "advisor",
      "answer": {},
      "created_at": "<timestamp>"
    }
  ]
}
```

`turns` is oldest first, at most 8 items (4 user and 4 advisor). An advisor turn's `answer` is the §5.7 `answer` plus `advisor_status` and `evidence`.

**Errors:** 401, 403, 404.

There is no session list and no delete.

---

## 13. Search, filters, and sorting

Search and filters are query parameters on the list routes. They are collected here so the client has one table.

| UI need | Request |
|---|---|
| Global organization search | `GET /api/v1/organizations?q=` |
| Organizations by type, state, has opportunities | Same path, §6.1 |
| Signals by type, organization, date, state | `GET /api/v1/signals` §7.1 |
| Opportunities by band, type, state, date | `GET /api/v1/opportunities` §8.1 |
| Sort opportunities by score or recency | `sort=score` or `sort=updated_at` |
| Competitor/vendor list | `GET /api/v1/signals?signal_type=competitor_vendor` |

Repeated query keys are arrays: `signal_type=procurement&signal_type=funding_budget`.

Unknown query parameters are ignored. Known parameters with illegal values are 400. That split lets a stale client send an old flag without breaking, and still rejects a bad enum.

---

## 14. Validation summary

| Rule | Applies to |
|---|---|
| UUID path and query ids | All `/{id}` and `*_id` filters |
| Enums | Only the values in §1.2 |
| Dates | `YYYY-MM-DD` |
| Strings | Trimmed. Over the max length is 400 |
| Pagination | §4 |
| Advisor message | 1–2000 characters |
| Scan All body | Exactly `scope=all_tracked` |
| Extra JSON keys | Ignored on input. Not echoed |

The server never trusts a client-sent role, score, evidence URL, or organization name as authority.

---

## 15. What is not in this API

| Not provided | Why |
|---|---|
| Login, logout, password, token refresh | Clerk |
| Role assignment | A database row during the hackathon |
| Create or edit organization, signal, or opportunity | Read-only intelligence. Changes come from scans |
| Organization discovery from the open web | Out of MVP |
| CRM, email, or notification endpoints | Out of MVP |
| A free-form URL ingest endpoint | Collection is the scan pipeline and the source register |
| Portfolio-wide Advisor with no scope | `AI_RAG_DESIGN.md` §23 |

---

## 16. Contract changes

A change to a path, field, enum, or error code is edited in this document before either side codes it. The frontend does not read the backend to discover a field. The backend does not add a field the UI has not been told about.

`DATABASE_DESIGN.md` maps these names to columns when it is written. It does not rename them silently.

---

## Open questions

| # | Item | Status |
|---|---|---|
| C1 | Login on FastAPI | **Decided.** No. `GET /api/v1/me` only |
| C2 | Long-running scans | **Decided.** `202` plus poll `GET /api/v1/scans/{scan_id}` |
| C3 | Insufficient evidence | **Decided.** HTTP 200 and `advisor_status` `insufficient_evidence` |
| C4 | Second Scan Now | **Decided.** HTTP 200, same scan, `joined_existing` true |
| C5 | Undated signals and a date filter | **Decided in §7.1.** Undated signals stay in the list when a date range is set. Change this only by editing this contract |
