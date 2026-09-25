# Data Sources

> **Status:** DRAFT — verified sources only
> **Version:** 0.3
> **Date:** 2026-09-23
> **Authoring order:** 3 of 9
> **Depends on:** `AGENTS.md` §6, `PRODUCT_PRD.md` §§6 and 25–26, `TECHNICAL_PRD.md` §§8 and 19
> **Primary author:** Developer 3 (AI/RAG/Data ingestion)

## Purpose of this document

The only register of sources the system may collect. A source that is not listed here is not collected (`FR-DATA-02`, `FR-DATA-06`).

Nothing in this document was taken from a third-party API guide. Where an official page is incomplete or contradicts itself, the gap is marked `NEEDS VERIFICATION` instead of being filled in.

No named organization website is listed yet. A website is added only after the checks in §5.2.

---

## 1. Rules

- Official API, then official public data file, then a validated official organization website.
- No third-party data providers. No news sites, no aggregators, no vendor blogs.
- Do not bypass authentication, robots rules, rate limits, paywalls, or CAPTCHAs (`FR-DATA-03`).
- Do not invent an endpoint, query parameter, or field that the official documentation does not list.
- Mock data is never a source. Cached fallback is a snapshot of content this register already allowed (`FR-FB-02`).
- IPEDS is reference data. It is not a signal (`FR-DATA-07`).

### Target data model

The primary purpose of the system is to monitor potential customer organizations in the U.S. education and EdTech market.

The MVP may track 10 U.S. education organizations as TARGET organizations. Store them as configurable database records. Do not hard-code them in application code. Additional organizations can be added later without changing the application architecture. Site selection and validation stay in §5.1 and §5.2. This count of 10 sits inside the 10–20 range already stated in §5.1.

**Decided 2026-09-23.** The build starts with two TARGET organizations. Add one only after a real SAM.gov notice or a validated page on that organization's own site is found. Add further organizations only after the signal-to-opportunity flow works for those two.

The system may also track a smaller number of EdTech and assessment companies as COMPETITOR organizations, for secondary competitive intelligence. They use the same approved sources in this document. A competitor company is not a new data provider.

| Organization type | Meaning |
|---|---|
| TARGET | Potential customer organization |
| COMPETITOR | Competitive intelligence |

TARGET organizations are the primary focus of opportunity detection. COMPETITOR signals must not automatically be treated as customer opportunities.

Organization type is a field on the organization record. §5.3 does not gain a new column for it.

### 1.1 Source priority

| Priority | Kind | Used now |
|---|---|---|
| 1 | Official APIs | SAM.gov Get Opportunities Public API and USAspending API v2 |
| 2 | Official public data | NCES IPEDS Data Center downloads |
| 3 | Official organization websites | Only after source validation (§5.2), one site at a time |
| 4 | Any other public source | Not approved. Do not add one in code |

### 1.2 How fresh the data is

| Class | Meaning in this product | Which approved source |
|---|---|---|
| Real-time | A push or continuous feed of events as they are published | None of the approved sources |
| Periodic | The publisher refreshes on a stated cycle. We poll on a schedule | SAM.gov active notices (daily). Organization websites (our schedule) |
| Historical | A record of past awards or spending, not a notice that something is opening now | USAspending |
| Reference / enrichment | Describes the institution. Not an event | NCES IPEDS |

SAM.gov is not treated as real-time. GSA states that active notices are updated daily and archived notices weekly.

### 1.3 Pre-RFP signals and actual procurement signals

Pre-RFP signals may come from:

- Official organization announcements
- Digital learning initiatives
- Assessment modernization initiatives
- Technology initiatives
- Strategic plans
- Funding and organizational signals
- Historical procurement context

These signals indicate potential future needs. They must not be presented as proof that an RFP will be issued.

Pre-RFP is a reading of signal types this document already allows, including `TECHNOLOGY_INITIATIVE`, `STRATEGIC_ANNOUNCEMENT`, `FUNDING_BUDGET`, `LEADERSHIP_CHANGE`, and `COMPETITOR_VENDOR`. It is not an eighth signal type.

Actual procurement signals may come from:

- SAM.gov procurement notices
- A procurement notice on a validated official organization website (§5), which is the only other procurement source already approved here

An actual procurement signal is a published notice. It is the existing `PROCUREMENT` type. It is not a prediction, and it is not a new signal category.

### 1.4 Product flow

```
TARGET ORGANIZATION
        ↓
Official public signals
        ↓
AI analyzes and classifies signals
        ↓
Combine with procurement/funding/history context
        ↓
Potential opportunity detected
        ↓
Sales team investigates / takes action
```

When an actual procurement notice exists:

```
SAM.gov / approved procurement source
        ↓
Published procurement notice
        ↓
Confirmed procurement signal
```

The confirmed procurement signal is still `PROCUREMENT`, with the evidence of the published notice. It does not by itself assert that a further RFP will be issued.

---

## 2. SAM.gov

| | |
|---|---|
| Source name | SAM.gov Contract Opportunities |
| Official site | https://sam.gov/opportunities |
| Official API documentation | https://open.gsa.gov/api/get-opportunities-public-api/ |
| Purpose | Federal contract opportunities: pre-solicitation, solicitation, award notices, justification notices, and related published procurement notices |
| Data class | Periodic. Active notices updated daily. Archived notices updated weekly |
| Signal types it can support | `PROCUREMENT`, `CONTRACT_RENEWAL` when the notice is an award or a follow-on to an award |
| Signal types it does not provide | Technology initiatives, leadership changes, strategic announcements, and competitor/vendor changes at a university or district. A federal notice names an agency and sometimes an awardee. It is not the institution's own news |
| Access method | Official API. Not HTML scraping of sam.gov |
| Reliability label | `official_api` (10 points). See §6 |

**Role.** SAM.gov provides published federal procurement notices. It is not a prediction engine. When a relevant notice exists, treat it as evidence of existing published procurement activity. Do not claim that SAM.gov predicts future RFPs.

### 2.1 API

GSA documents the Get Opportunities Public API, version v2.

| Item | What the official page says |
|---|---|
| Production base in the Version Control section | `https://api.sam.gov/opportunities/v2/search` |
| Production URL in Example 1 on the same page | `https://api.sam.gov/prod/opportunities/v2/search` |
| Alpha | `https://api-alpha.sam.gov/opportunities/v2/search` |

> NEEDS VERIFICATION — those two production paths are both printed on the GSA page. The collector uses one of them only after a keyed request shows which path returns `200`. Do not guess, and do not add any other SAM.gov API (entity, exclusions, or opportunities downloads) until that API is added here.

Authentication: a public API key is required. A registered user requests it from the Account Details page on SAM.gov. The key is passed as the `api_key` query parameter. Store it in `SAM_GOV_API_KEY`. Never put it in a user-facing URL, a log line, or the repository.

Required search parameters on that documented operation:

| Parameter | Rule from the GSA page |
|---|---|
| `api_key` | Required |
| `postedFrom` | Required. `MM/dd/yyyy`. The span to `postedTo` is at most one year |
| `postedTo` | Required. Same format and one-year span |
| `limit` | Optional. Maximum 1000. Default documented as 1 |
| `offset` | Optional. Page index. Default 0 |
| `ptype` | Optional. Values below |

Documented `ptype` values:

| Code | Meaning on the GSA page |
|---|---|
| `p` | Pre solicitation |
| `o` | Solicitation |
| `k` | Combined Synopsis/Solicitation |
| `r` | Sources Sought |
| `s` | Special Notice |
| `a` | Award Notice |
| `u` | Justification (J&A) |
| `i` | Intent to Bundle Requirements (DoD-Funded) |
| `g` | Sale of Surplus Property |

There is no documented `ptype` named sole source. Sole-source related material appears as Justification (`u`) and as sole-source set-aside codes on the same page (`8AN`, `HZS`, `SDVOSBS`, `WOSBSS`, `EDWOSBSS`, `VSS`). Those codes are filters, not a promise that a given notice exists.

`deptname` and `subtier` are marked deprecated on the v2 parameter table. Do not build the collector on them.

The response fields the product may keep, because the same page lists them: `noticeId`, `title`, `solicitationNumber`, `postedDate`, `type`, `baseType`, `active`, `naicsCode`, `classificationCode`, `fullParentPathName`, `fullParentPathCode`, `responseDeadLine` (the prose table spells one field `reponseDeadLine`), award number, amount, date, and awardee name when present, and `uiLink`. Descriptions are not inline. The `description` field is a link, and the page says the public API key must be appended to download it.

### 2.2 Expected data and evidence

Keep the notice id, title, procurement type, posted date, response deadline if present, agency path, NAICS, solicitation number, and award fields when the payload includes them. The verbatim evidence snippet is text returned by the API (title plus type, or the description body after a keyed download). The snippet is not written by the model.

Evidence URL:

- The keyed description link is a fetch URL for the server only. It is not the evidence URL.
- GSA states that `uiLink` sends a user without a contracting officer or contracting specialist role to a 404. Do not store `uiLink` as the public evidence link until that behavior is rechecked.
- The human entry point that is verified today is https://sam.gov/opportunities.

> NEEDS VERIFICATION — the public notice URL that opens the same `noticeId` without a login. Until that pattern is confirmed on sam.gov, the evidence record stores the notice id and https://sam.gov/opportunities, and says the deep link is not yet verified. Do not invent a `/opp/{id}` path.

### 2.3 Update frequency

Poll at most once a day for active notices, matching GSA's daily update statement. A poll uses a `postedFrom`/`postedTo` window of **at most 364 days** (SAM rejects an exact 365-day inclusive span as more than one year). Do not page the full history. Archived notices are out of the daily poll. They are weekly on SAM.gov's side and are not required for the MVP.

### 2.4 Rate limits

The API page says the daily request limit depends on federal, non-federal, or general role. It does not print the integers.

The SAM.gov System Account User Guide states these default limits. A public copy of that guide is https://www.state.gov/wp-content/uploads/2025/05/SAM-User-Guide.pdf.

| Account | Documented default |
|---|---|
| Non-federal individual, not associated with an entity | 10 requests every 24 hours |
| Non-federal individual associated with an entity | 1,000 requests every 24 hours |
| Federal individual | 1,000 requests every 24 hours |
| Non-federal system account | 1,000 requests every 24 hours |
| Federal system account | 10,000 requests every 24 hours |

> NEEDS VERIFICATION — the quota on the key this project actually receives. The figures above are the User Guide's defaults for account types. They are not this project's measured quota.
>
> **Decided 2026-09-23.** Until that quota is verified, the application itself stops at **10 requests per 24 hours**. That cap is an implementation safeguard. It is not SAM.gov's official quota. One search page is one request. A description download is another request. Do not backfill a year of pages under this cap.

On HTTP 429 or 403, stop that source for the run. Do not rotate keys, do not retry in a tight loop, and do not fall through to scraping sam.gov.

### 2.5 Limitations

- Federal notices only. A state university procurement portal will not be in this API.
- The API returns the latest active version of a notice, not every historical version. Older versions are under SAM.gov Data Services, which this document does not approve.
- Place of performance and agency name are not the same thing as "this notice is about the tracked university." Matching a notice to a tracked organization is our code, using names and identifiers we stored. A failed match means no signal, not a guessed link.
- Sale of surplus property (`g`) is not an education sales signal. Drop that `ptype` unless a later decision says otherwise.
- The description download can return "Description not found". Store the search record without a description snippet. Do not fabricate the body.

### 2.6 Failure behavior

If the key is missing, the quota is exhausted, or the host errors, the scan records SAM.gov as a failed source and continues with the other approved sources (`FR-SCAN-05`). Previously stored SAM.gov notices stay visible. Cached copies of those notices, if used for a demo, carry the cached flag and the original retrieval time (`FR-FB-03`). The cache is not a substitute that hides the failure (`FR-FB-04`).

### 2.7 Terms

Use the public API with a key issued to this project. Send an honest User-Agent (`HTTP_USER_AGENT`). Do not share the key. Do not republish the raw feed as a competing SAM.gov. Attribution on evidence is the source name SAM.gov plus the verified public URL.

---

## 3. USAspending.gov

| | |
|---|---|
| Source name | USAspending.gov |
| Official API | https://api.usaspending.gov/ |
| Official endpoint index | https://api.usaspending.gov/docs/endpoints |
| Human site | https://www.usaspending.gov |
| Purpose | Federal award and spending records, recipient identity, and agency context. Historical procurement context |
| Data class | Historical, refreshed on the publisher's load cycle. Not a solicitation feed |
| Signal types it can support | `FUNDING_BUDGET` when a federal award or grant to a tracked organization is in the result. `CONTRACT_RENEWAL` only as context that an award exists, with period fields the payload actually contains |
| Signal types it does not provide | Pre-solicitation, RFP, RFI, sources sought, leadership changes, technology initiatives, strategic announcements, and vendor-adoption announcements. An award recipient is not a "vendor change" signal by itself |
| Access method | Official API, version 2. The site says v1 is deprecated. Do not call v1 |
| Reliability label | `official_api` (10 points) for an award fact. It does not outrank a missing solicitation. An old award is weak on recency |

**Role.** USAspending is historical award, spending, and context data. It is not itself an RFP or a real-time opportunity feed.

### 3.1 API

The endpoint index states: "Endpoints do not currently require any authorization." No API key is documented. Do not invent one.

Only these documented v2 operations are approved for the MVP. Other rows on the index are not approved by being nearby.

| Endpoint | Method | Documented description | MVP use |
|---|---|---|---|
| `/api/v2/autocomplete/recipient/` | POST | Returns recipient names and UEI for the search text | Resolve a tracked organization's name to a recipient id. Ambiguous matches are not auto-selected |
| `/api/v2/search/spending_by_award/` | POST | Returns the fields of the filtered awards | List awards for a resolved recipient |
| `/api/v2/awards/<AWARD_ID>/` | GET | Returns details about a specific award | One award's detail page fields |
| `/api/v2/awards/last_updated/` | GET | Returns date of last update | Show how current the spending data is |

Request bodies for the POST operations are not copied here. At implementation, read the live page for that endpoint and send only fields it documents. Do not add a filter the page does not list.

Documented status codes on the index: `200` success, `400` malformed request, `500` server error.

### 3.2 Rate limits

The endpoint index does not publish a numeric rate limit.

A maintainer reply on the USAspending API issue tracker (19 August 2025, issue 4459) said most endpoints allow 1,000 requests in 300 seconds, and some endpoints are stricter. That is not the endpoint index.

> NEEDS VERIFICATION — treat 1,000 requests / 300 seconds as an unverified ceiling, not as permission to approach it. The MVP sends a handful of sequential calls per organization, backs off on connection resets and `500`s, and does not run bulk-download jobs.

### 3.3 Expected data and evidence

From a successful award detail or spending-by-award row, keep only fields present in that response: award id, recipient name, awarding agency, amounts, dates, and description text if the payload has them. Dates that are absent stay "unavailable".

The evidence URL is the public USAspending.gov page for that award only after the URL pattern is confirmed from a link the API or the human site returns.

> NEEDS VERIFICATION — do not invent `https://www.usaspending.gov/award/{id}`. If the response contains no public URL, the evidence URL is https://www.usaspending.gov and the award id is stored beside it until a deep link is verified.

### 3.4 Update frequency

At most once per day per tracked organization, and only for organizations that already resolved to a single recipient. This is context, not the scan's first request. SAM.gov and official websites take the request budget first.

### 3.5 Limitations

- Federal awards only. A district's local budget vote is not in USAspending.
- Recipient autocomplete can return several entities with similar names. The collector stores the candidates and does not pick one by fuzzy confidence from a model.
- Many universities and districts receive no recent federal award. Empty is a valid result.
- Award data lags the transaction. `last_updated` is shown with the fact so the user can see the lag.
- A grant or contract award is observed spending. It is not evidence that a new RFP will be issued.

### 3.6 Failure behavior

Same as §2.6. A USAspending failure does not block SAM.gov or website collection. No silent substitution.

### 3.7 Terms

The API root page describes the service as public access to federal spending data under the DATA Act, built by the U.S. Department of the Treasury. Use it for this internal sales-intelligence tool. Attribute USAspending.gov on every award fact. Do not strip agency or recipient names.

---

## 4. NCES IPEDS

| | |
|---|---|
| Source name | NCES IPEDS (Integrated Postsecondary Education Data System) |
| Official site | https://nces.ed.gov/ipeds/ |
| Use-the-data page | https://nces.ed.gov/IPEDS/use-the-data |
| Data Center | https://nces.ed.gov/ipeds/datacenter/ |
| Purpose | Identify and describe U.S. postsecondary institutions: name, UnitID, sector and characteristics, enrollment, and finance context |
| Data class | Reference / enrichment. Survey collections are annual. Not a signal feed |
| Signal types it can support | None |
| Signal types it does not provide | All seven. A finance figure from a survey year is not a funding announcement. A leadership title in a directory, if present, is not a leadership-change event unless a dated announcement says the person was appointed |
| Access method | Official data files from the IPEDS Data Center. Not an NCES REST API. No third-party IPEDS API |
| Reliability | Authoritative for the survey year it names. It does not receive signal reliability points, because it never becomes a signal |

**Role.** NCES IPEDS is reference and enrichment data about institutions. It is not an opportunity signal.

### 4.1 What is verified about access

The use-the-data page documents these tools: Look Up an Institution, Custom Data Files, Compare Institutions, and Complete Data Files. Complete Data Files are zipped CSV by survey and year. Custom Data Files are CSV (and statistical-package variants) for institutions and variables the user selects. The Data Center help text says institutions can be found by name or UnitID.

The Data Center distinguishes provisional and final release. For institution context, use a final release when both exist. If only a provisional year is available, store the release label with the figures. Do not present provisional numbers as the final survey.

Surveys named on the Data Center release table include Institutional Characteristics. The use-the-data page also points at enrollment and finance topics (revenues, student charges, financial aid). The MVP download is limited to identification, sector, state, enrollment, and a small finance set for the tracked postsecondary institutions.

> NEEDS VERIFICATION — the exact file name and column names for the collection year we download. Read the data dictionary that ships with that file. Do not hard-code a column that the dictionary does not contain.

There is no documented API key and no documented rate limit for these downloads. Download a file once, store it, and do not script the Data Center UI.

### 4.2 Who IPEDS covers

Postsecondary institutions. It does not cover K-12 districts or a state education agency as a district. Those organizations get identity from the tracked-organization list and from their own official website. An empty IPEDS panel for a district is correct, not a failed source (`FR-ORG-02`).

### 4.3 Update frequency

Once, when the tracked postsecondary list is chosen, and again only when NCES publishes a later final release we decide to load. Not on Scan Now. Not daily.

### 4.4 Evidence

IPEDS figures are shown in the reference band, labelled reference, with the survey name and year. They are not evidence items on a signal. The source URL is the IPEDS institution lookup or the data-file page that was actually used, once that URL is the one we downloaded from. Until a per-institution public URL is confirmed, cite https://nces.ed.gov/ipeds/ and the UnitID.

### 4.5 Failure behavior

If the file cannot be downloaded, organization profiles omit IPEDS and say reference data is unavailable. Signals and scores do not change.

### 4.6 Terms

IPEDS is a federal statistical data collection. Use the public files for institution context inside this tool. Do not imply NCES produced our opportunity scores. Keep the survey year next to every figure.

---

## 5. Official organization websites

| | |
|---|---|
| Source name | Official website of a tracked organization |
| Official URL | Not a shared URL. Each site is an entry added under §5.3 |
| Purpose | Leadership changes, technology initiatives, strategic announcements, vendor or platform announcements, and funding or budget news the institution itself publishes |
| Data class | Periodic collection of specific pages. The institution does not offer a real-time feed unless that feed is later verified and added |
| Signal types it can support | `LEADERSHIP_CHANGE`, `TECHNOLOGY_INITIATIVE`, `STRATEGIC_ANNOUNCEMENT`, `COMPETITOR_VENDOR`, `FUNDING_BUDGET` when the page states that event |
| Signal types it usually cannot support | Federal `PROCUREMENT` notices. A local procurement page can support `PROCUREMENT` or `CONTRACT_RENEWAL` only when that page is on the official site and the text is a notice, not a generic "doing business with us" page |
| Access method | HTTP GET of an allowlisted URL, then parse HTML. Playwright only if that specific page is documented here as requiring JavaScript |
| Reliability label | `official_website` (6 points) |

**Role.** Official organization websites are the primary source for pre-RFP institutional signals. Only validated public pages may be collected (§5.2). Do not assume every organization has the same page structure.

### 5.1 How a site is selected

The tracked set may grow to 10–20 U.S. education organizations, chosen because recent public material exists across more than one signal type (`PRODUCT_PRD.md` §6). Fame is not a reason. **Decided 2026-09-23:** start with two, and only after real evidence exists.

For each organization, the candidate site is the institution's own site: a university or college `.edu` site, a school district's official domain, or a state education agency's official government domain. The starting point is a link from IPEDS for a postsecondary institution, or from the agency's own published contact page for a district or state agency.

A news outlet, a foundation, a vendor, or a Wikipedia page is not the official site of a TARGET organization.

A COMPETITOR organization, when one is tracked, uses that company's own official site. The same §5.2 checks apply before any page is collected.

### 5.2 How a site is validated

All of these must be true before the URL is written into §5.3 and before any **content collector** runs:

1. The page loads without a login, a paywall, or a CAPTCHA.
2. The site identifies the organization by its official name.
3. `robots.txt` for that host does not disallow the specific path we will fetch.
4. The path is a bounded section (news, leadership, board, or technology), not the whole host and not a search-all crawl.
5. A human records the URL, the section, the signal types that section might hold, and the date checked — **or**, for MVP discovery-only Scan All (§5.2a), the backend records an equivalent validation result into `organization_sources`.

Until those five are recorded for **collection**, the URL is not an approved collection source in §5.3, except under the interim rule in §5.2b.

### 5.2a MVP discovery-only Scan All (interim)

**Does not replace §5.3 for content collection.** Full pipeline collection still requires §5.3 (or an explicit later decision).

For the interim demo slice:

1. Scan All / dashboard "Scan Now" loads every organization with `tracking_status = active`.
2. The backend fetches the official homepage and collects same-domain links (deterministic allowlist), plus any previously approved `organization_sources` URLs.
3. A configured LLM adapter may **select and classify** only from that allowlist. The LLM must not invent URLs.
4. The backend **must** validate each candidate: URL syntax, HTTP accessibility (safe redirects, with one retry on transient errors), final host on the official domain or subdomain, public access, and `robots.txt` for the path.
5. Only candidates that pass are stored as `organization_sources` with `status = approved`. Upsert is on `(organization_id, url)` — no duplicates. Previously approved URLs are not demoted to rejected on transient network errors.
6. The LLM is never the final authority. Invented or third-party URLs are dropped before validation.
7. Chunks, embeddings, and signals are **out of this slice**.

### 5.2b MVP page collection (interim)

**Decided 2026-09-24.** Until §5.3 is filled by hand, an approved `organization_sources` row is the collection allowlist for that organization. The same Scan collects those pages into `documents`:

1. The page HTML fetched during validation (§5.2a step 4) is the page that is stored. It is not fetched a second time in the same scan.
2. One approved page per organization may be the organization's own **news hub** (`page_category` `news`, for example `news.asu.edu` or `ucf.edu/news`). It is still an official page on the organization's domain. Third-party news sites stay forbidden (§1).
3. From a news hub, the scan also collects up to `SCAN_NEWS_ARTICLES_PER_HUB` article pages (default 5) that the hub itself links to, on the same host, in the order the hub lists them. Article URLs come only from the fetched hub HTML. Nothing else is followed. This is the "documented next-page link on the same host" in §5.4, not a crawl.
4. Every request follows §5.4: `robots.txt` first, at least five seconds between requests to the same host (longer if `crawl-delay` says so), the honest `HTTP_USER_AGENT`, same-domain redirects only. A 403 or 429 is recorded and not retried with another client or user agent. Different hosts run in parallel.
5. **Updated 2026-09-24.** Scan Now is user-triggered and fetches live pages every time (`SCAN_REFRESH_HOURS` default 0), so a demo always shows the site as it is now. Within one scan each page is still fetched once, the five-second host gap still applies, and only one scan per organization runs at a time. A scheduled scan, if built, sets `SCAN_REFRESH_HOURS` to 24 to keep the "one fetch per page per daily scan" rule; a page collected (or found unreadable) inside that window is then reused.
6. A page whose text only appears after JavaScript runs is recorded as not collectable (`extraction_status` `failed`). Playwright is not used for it.
7. `published_on` is set only when the page states a date (meta tags or structured data; the `<time>` tag on article pages). Otherwise it stays null. The scan never substitutes today's date.
8. Each organization and URL has one current document. An unchanged page changes nothing. A changed page replaces the stored text in place, so the database shows what the site says now (`DATABASE_DESIGN.md` §6). An older version is kept only when stored evidence points at it.
9. **Decided 2026-09-24.** Website collection does not insert rows into `sources`. That table holds only origins listed in this document (today `sam_gov`, `usaspending`, `ipeds`). The organization root URL is `organizations.website_url`. Approved pages are `organization_sources`. Website `documents` leave `source_id` null.

**Decided 2026-09-24 (Scan Now multi-source).** The same Scan All / Scan Now run collects website pages and SAM.gov notices in parallel. SAM.gov uses one shared search for the batch (plus at most a few documented `title` searches when an org matched nothing), under the application cap of 10 requests / 24 hours. Notices are matched to `organizations.name` locally; unmatched notices are not stored. Matched notices become `documents` with `source_id` = SAM.gov, `organization_id` set, and `external_id` = `noticeId`. Description downloads are out of this slice (each is another request). USAspending and IPEDS are not part of this parallel loop yet.

### 5.3 Approved website register

No organization website is approved yet.

| Organization | Official URL | Section | Signal types that section may hold | robots checked | Date checked |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

> **Decided 2026-09-23.** Start with two TARGET organizations, each added only after real evidence. §5.3 stays empty until a human validates each row. Collection code that fetches a URL not in this table, and not allowed by the interim rule in §5.2b, is a defect.

### 5.4 How a site is collected

- GET the allowlisted URL only. Do not follow links onto other hosts.
- One page, or a documented next-page link on the same host, per section. No site-wide crawl (`FR-DATA-04`).
- Read `robots.txt` first. If the path is disallowed, skip it and record the skip. Do not use a different user agent to get around the rule.
- Wait at least five seconds between requests to the same host. One fetch of each allowlisted page per daily scan, unless the site's `robots.txt` crawl-delay is longer. In that case use the longer delay.
- Identify the client with `HTTP_USER_AGENT`.
- If the page requires JavaScript to show the article text, do not scrape the empty shell. Either mark the section as not collectable for the MVP, or add one line here that Playwright is required for that URL and why. Playwright is not the default.
- Store the final URL after redirects, the status code, the retrieval time, and the raw HTML. The evidence snippet is taken from that HTML. The evidence URL is that final URL.

### 5.5 Limitations

- A marketing homepage with no dated announcement does not produce a signal (`PRODUCT_PRD.md` §9).
- Leadership bios with no appointment date can be reference context only. They are not a `LEADERSHIP_CHANGE` unless the page states a change and a date, or the date is stored as unavailable and the text still states an appointment. The extraction rules in `AI_RAG_DESIGN.md` still apply. The model does not invent the appointment.
- The same story on the institution site and in a federal notice is one clustered signal with two source references, not two opportunities.
- K-12 and state agencies will not have IPEDS rows. Their websites carry more of the identity burden. That does not relax the validation rules.

### 5.6 Failure behavior

A single host timeout or HTTP error fails that website section only. Other sections and other sources continue. The scan result names the URL and the status. Cached HTML from an earlier successful fetch may be shown only with the cached label and the original retrieval date.

### 5.7 Terms

Each site's terms and `robots.txt` govern that site. If terms forbid automated collection, the site is not added. There is no project-wide exemption.

---

## 6. Reliability

Signal reliability points used by scoring (`AI_RAG_DESIGN.md` §10) are only:

| Label | Points | Assigned to |
|---|---|---|
| `official_api` | 10 | SAM.gov Get Opportunities API. USAspending API |
| `official_website` | 6 | A website that passed §5.2 |
| `other_public` | 3 | Nothing. Reserved for a later approved source |

The group's source-reliability factor uses the highest label among the signals in the group. IPEDS is not in this table.

A high label does not make a stale fact recent. Recency is a separate factor.

---

## 7. Signal coverage

A cell marked "no" means the source must not be asked to produce that signal type.

| Signal type | SAM.gov | USAspending | IPEDS | Official website |
|---|---|---|---|---|
| Procurement | Yes, federal notices only | No | No | Only a procurement notice on that official site |
| Technology initiatives | No | No | No | Yes, when the page announces one |
| Leadership changes | No | No | No | Yes, when the page announces a change |
| Funding / budget | No, except an award amount on an award notice | Yes, federal awards and grants | No. Survey finance is reference | Yes, when the institution announces funding or a budget action |
| Strategic announcements | No | No | No | Yes |
| Competitor / vendor changes | No. An awardee name is an award fact, not a campus vendor adoption | No | No | Yes, when the institution announces a vendor or platform |
| Contract / renewal | Yes, when the notice is an award or justification | Context only, from award records that contain period fields | No | Only when the official page states a contract or renewal |

---

## 8. Collection frequency

| Source | MVP cadence | Stop condition |
|---|---|---|
| SAM.gov | At most once a day, one or a few search calls inside the key's daily quota | 429, 403, missing key, or the application safeguard of 10 requests per 24 hours |
| USAspending | At most once a day per resolved recipient, sequential | Repeated 500s or connection resets after one backoff |
| IPEDS | When the tracked postsecondary list is loaded, then on a new final release | Failed download. Profiles omit reference data |
| Official websites | At most once a day per allowlisted URL, with the delay in §5.4 | `robots.txt` disallow, non-200, or timeout |

Scheduled scans and Scan Now share this cadence and the same quota (`FR-SCAN-06`, `FR-SCHED-03`). Scan All does not give every organization its own SAM.gov query. SAM.gov is searched once per run, then matched to tracked organizations locally.

---

## 9. Evidence requirements

Every signal from these sources still follows `FR-EV-01`.

| Field | Rule |
|---|---|
| Source name | The name in this document, or the organization site name recorded in §5.3 |
| Source URL | A URL this document allows. Never a model-written URL. Never a URL that contains `SAM_GOV_API_KEY` |
| Date | `postedDate` or the award date when the payload has it. The page's stated date when the parser finds it. Otherwise unavailable |
| Snippet | Verbatim text from the API payload or the fetched page |
| Relationship | Why that snippet supports the signal. Interpretation, not a new fact |

If the deep link is still `NEEDS VERIFICATION`, the evidence shows the verified entry-point URL plus the source's own identifier (`noticeId`, award id, or UnitID). A missing deep link is not a reason to invent one.

---

## 10. Failure and fallback

| Failure | Behavior |
|---|---|
| One source fails | That source is named on the scan. Other approved sources continue |
| SAM.gov quota | Stop SAM.gov for the rest of that 24-hour window. Do not scrape the website instead |
| Empty result | Successful collection with no new signals |
| All sources fail | The scan is failed. Previously stored facts remain. Nothing is generated to fill the gap |
| Demo outage | Cached snapshots of earlier successful fetches for the demonstration organizations only, labelled with the original retrieval time |

The cache cannot contain an organization or a notice we never retrieved.

---

## 11. MVP source strategy

The smallest set that can still show the full workflow:

1. **SAM.gov Get Opportunities API** for federal procurement and award notices. This is the structured source. One daily search, matched locally to the tracked organizations. The application cap is 10 requests per 24 hours until the issued key's quota is verified (§2.4). That cap is not SAM.gov's official quota.
2. **Two official organization websites** for the first demo, each validated under §5.2 and written into §5.3. Leadership, technology, funding, and vendor signals come from those pages. SAM.gov stays the source for federal procurement notices. More sites, up to five, wait until the two-organization flow works.
3. **NCES IPEDS** for postsecondary identity and context only. One file load. Not part of Scan Now. **Deferred for the first demo.**
4. **USAspending** only for tracked organizations that resolve to one federal recipient. It adds historical award context. **Deferred for the first demo.**

That is the whole set. No fifth source.

A reliable demo organization is one that, on a checked day, has either a matching SAM.gov notice or a dated page on its own site, and preferably both, across more than one signal type. The names are chosen when §5.3 is filled. They are not chosen in advance here.

Order of implementation: confirm the SAM.gov production path, validate two organizations from real evidence, then run the signal-to-opportunity flow. Load IPEDS and add USAspending only after that first prototype works.

---

## Open questions

| # | Question | Status |
|---|---|---|
| D1 | Which SAM.gov production path is live, `/opportunities/v2/search` or `/prod/opportunities/v2/search`? | NEEDS VERIFICATION against a keyed request. Both appear on the GSA page |
| D2 | What daily quota does this project's API key have? | Official quota is unverified. The application caps itself at 10 requests / 24 hours until then. That cap is not SAM.gov's official quota |
| D3 | Public SAM.gov notice URL that works without a contracting role | NEEDS VERIFICATION. Do not invent the path |
| D4 | Public USAspending award URL | NEEDS VERIFICATION. Use the site root plus the award id until then |
| D5 | IPEDS file name and columns for the year we load | NEEDS VERIFICATION from that year's data dictionary |
| D6 | Which organizations, and which of their URLs pass §5.2? | **Decided 2026-09-23.** Start with two, only after real evidence. Names are not selected yet. §5.3 stays empty until each row is validated |
| D7 | USAspending numeric rate limit | Not in the official endpoint index. Do not build to the GitHub figure |
