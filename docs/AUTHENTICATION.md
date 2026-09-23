# Authentication and Authorization

> **Status:** DRAFT — awaiting approval
> **Version:** 0.2
> **Date:** 2026-09-23
> **Authoring order:** 5 of 9
> **Depends on:** `AGENTS.md`, `PRODUCT_PRD.md` §27, `TECHNICAL_PRD.md` §10 and AD-15
> **Primary author:** Developer 2 (backend verification and role store), Developer 1 (Clerk in the React app)

## Purpose of this document

Defines who authenticates the user, who authorizes them, how a Clerk identity becomes an
application role, and what the frontend and the API do when authentication or authorization fails.

**This document does not choose FastAPI-native authentication or Supabase Auth.** Both are
rejected. The approved split is:

| System | Question it answers | Owns |
|---|---|---|
| Clerk | Who is this user? | Sign-up, sign-in, sign-out, passwords, sessions, tokens, identity |
| FastAPI | What is this user allowed to do? | Token verification, role lookup, authorization on every protected route |
| Supabase PostgreSQL | What does the application know? | The role row and all other application data. Not credentials |

Endpoint paths, request bodies, and the shared error envelope's full catalogue belong to
`API_CONTRACT.md`. This document defines the authentication and authorization rules that contract
must follow. Table names belong to `DATABASE_DESIGN.md`; the fields below are required whatever
the table is called.

---

## 1. Authentication architecture

```
User
  ↓
React frontend
  ↓
Clerk sign-in
  ↓
Authenticated Clerk session
  ↓
Clerk session token
  ↓
FastAPI request  (Authorization: Bearer <token>)
  ↓
FastAPI verifies the Clerk token
  ↓
Identify the authenticated user  (Clerk user id)
  ↓
Load the application role from PostgreSQL
  ↓
Apply authorization rules
  ↓
API response
```

Two checks, in this order, on every protected request:

1. **Authentication** — the token is present, well-formed, signed by Clerk, and unexpired. Failure
   is `401`. The request never reaches role logic.
2. **Authorization** — the Clerk user id has exactly one application role, and that role is allowed
   to perform the operation. Failure is `403`.

The frontend repeats a weaker version of the first check so an anonymous visitor does not see the
application. That check is not a substitute for the backend. A client that skips the redirect and
calls the API directly is still rejected.

---

## 2. Clerk responsibilities

Clerk is the only authentication system.

| Responsibility | Clerk | This application |
|---|---|---|
| Sign up | Yes | No sign-up form of our own |
| Sign in | Yes | No sign-in form of our own |
| Sign out | Yes | The UI calls Clerk's sign-out, then clears client caches |
| Password storage and hashing | Yes | Never |
| Password reset | Yes | Never |
| Session creation, refresh, and expiry | Yes | Never |
| Session token issuance | Yes | The backend verifies tokens. It does not issue them |
| User identity (Clerk user id, email, name) | Yes, source of truth | Not copied into PostgreSQL for the MVP |
| Basic account management | Clerk Dashboard | No admin screens |

Login method for the MVP is email and password through Clerk. That satisfies `AGENTS.md` §11.
Social login, enterprise SSO, and custom password rules are out of scope (§15).

The React app uses Clerk's React SDK. The sign-in screen is Clerk's sign-in component on the
`/login` route from `UI_UX_DESIGN.md`. It is themed toward the navy and Inter tokens as far as
Clerk's appearance options allow. It does not sit inside the application sidebar or header.

---

## 3. FastAPI responsibilities

FastAPI does not authenticate. It verifies that Clerk already did, then authorizes.

| Responsibility | Rule |
|---|---|
| Verify the bearer token on every protected route | Shared dependency, not per-route custom code |
| Read the Clerk user id from the verified token | This is the only identity key the backend trusts |
| Load `SALES_REP` or `SALES_MANAGER` from PostgreSQL | Clerk metadata is not the role source |
| Reject missing, invalid, and expired tokens | `401`, before any database write |
| Reject an authenticated user with no usable role | `403` |
| Enforce the role on the operation | Even though both MVP roles currently share one permission set |
| Never accept a role, user id, or permission sent by the client as authority | The token proves identity. The database proves the role |

A user who is valid in Clerk and has no application role is denied (`TECHNICAL_PRD.md` §10).
Sign-up does not grant a role.

---

## 4. Authentication flow

**Sign in**

1. An unauthenticated visitor opens any application route and is redirected to `/login`.
2. Clerk presents email/password sign-in (or sign-up, which Clerk also owns).
3. On success, Clerk holds the session in the browser. The application does not write a session
   cookie of its own and does not store the token in `localStorage` itself. Clerk's SDK holds it.
4. The frontend API client requests a session token from Clerk and sends it as
   `Authorization: Bearer <token>` on every API call.
5. FastAPI verifies the token with the Clerk secret. Verification failure stops the request.

**While the session is active**

Clerk refreshes the session. The application does not implement a refresh endpoint. Each API call
carries a current token from the Clerk SDK. The backend is stateless: it does not keep a server
session.

**Sign out**

1. The user chooses sign out in the sidebar (`UI_UX_DESIGN.md` §23).
2. The frontend calls Clerk sign-out. Clerk invalidates the session.
3. The frontend clears the TanStack Query cache so the next user on that browser cannot see the
   previous user's data.
4. The frontend navigates to `/login`.
5. Any later request that still carries the old token fails verification and returns `401`.

There is no backend logout endpoint in the MVP. Logout is a Clerk session change plus a client
cache clear.

---

## 5. Authorization flow

After the token verifies:

1. Read the Clerk user id from the verified token.
2. Look up the application user row by that id.
3. If no row exists, return `403` with `USER_NOT_PROVISIONED`. Do not create a row automatically.
4. If the row exists but the role is missing or is not exactly `SALES_REP` or `SALES_MANAGER`,
   return `403` with `USER_WITHOUT_ROLE`.
5. If the operation's allowed roles do not include the stored role, return `403` with
   `INSUFFICIENT_PERMISSION`.
6. Otherwise run the operation. The role does not change which organizations, signals, or
   opportunities are returned (`FR-ROLE-04`).

Authorization is role-based, not record-based. There is no organization ownership check.

---

## 6. Role model

Exactly two roles. Codes are stored and compared as these strings. Display labels are for the UI
only.

| Code | UI label | MVP access |
|---|---|---|
| `SALES_REP` | Sales Representative | Every tracked organization, every MVP screen, Scan Now, Scan All, AI Sales Advisor |
| `SALES_MANAGER` | Sales Manager | The same set. No manager-only screen |

`FR-ROLE-01` — one role per user.
`FR-ROLE-03` — both roles see the same evidence.
`FR-ROLE-04` — queries are not filtered by the calling user.

### 6.1 How a Clerk user receives a role

MVP provisioning is manual. There is no admin UI, no invitation workflow, and no webhook.

1. Create the person in the Clerk Dashboard (or let them sign up through Clerk).
2. Insert one application user row: internal id, Clerk user id, role, `created_at`, `updated_at`.
3. Until that row exists with a valid role, the API returns `403` even though Clerk sign-in
   succeeded.

The team assigns the role in the database during the hackathon. The user cannot choose or change
their own role. Changing a role means updating that row. It does not mean editing Clerk.

Demo accounts follow the same path: one Clerk user with a `SALES_REP` row, one with a
`SALES_MANAGER` row, created before the demonstration. The email addresses are not written into
this repository.

### 6.2 Permission matrix

For the MVP the matrix is intentionally flat. The check still runs, so a later restricted
operation can be added without a new identity system.

| Operation | `SALES_REP` | `SALES_MANAGER` | No role |
|---|---|---|---|
| Call any protected MVP endpoint (read intelligence, Advisor, Scan Now, Scan All) | Allowed | Allowed | `403` |
| See every tracked organization | Allowed | Allowed | `403` |
| Assign or edit roles | No endpoint | No endpoint | No endpoint |
| Manage other users | No endpoint | No endpoint | No endpoint |

---

## 7. Frontend route protection

Clerk authentication state guards routes. This is a UX layer and a convenience barrier. It is not
the security boundary.

| Condition | What the user sees |
|---|---|
| No Clerk session | Redirect to `/login`. The application shell (sidebar, header, data) is not rendered |
| Clerk session, role not yet known | The shell may render a loading state. No intelligence data is shown until the current-user call succeeds |
| Clerk session, API returns `USER_NOT_PROVISIONED` or `USER_WITHOUT_ROLE` | A dedicated page: the account is signed in and has no application role. Offer sign out. Do not send them back to `/login` in a loop |
| Clerk session, API returns `401` | Treat the session as dead. Sign out of Clerk and redirect to `/login` |
| Clerk session and a valid role | The application. Both roles see the same routes (`UI_UX_DESIGN.md` §22) |

Protected routes are every route in `UI_UX_DESIGN.md` §22 except `/login`.

The API client attaches the Clerk session token to every request. Components do not read or store
the token. The sidebar shows the role label from the current-user response so the person knows
which role they hold. That label does not change the data on screen.

The current-user call is `GET /api/v1/me` in `API_CONTRACT.md` §2.1. The response includes
`user_id`, `clerk_user_id`, and `role`. The frontend does not invent another path.

---

## 8. Backend API protection

Every FastAPI endpoint that reads or writes application data requires a verified Clerk token.
That includes organizations, signals, opportunities, evidence, the Advisor, scans, and dashboard
metrics.

Unauthenticated exceptions, and the only ones:

| Endpoint class | Auth |
|---|---|
| Process health, if one is added for the host | Public. It returns no application data and no user data |
| Everything else | Protected |

There is no login endpoint on FastAPI. Login is Clerk.

Implementation rule: the role dependency is the default for routers. A public route is an explicit
exception that a reviewer can see. The reverse — remembering to add auth to each new route — is
not acceptable.

---

## 9. User and application data

Clerk is the source of truth for identity and credentials. PostgreSQL is the source of truth for
application data, including the role.

The application user row stores only:

| Field | Required | Notes |
|---|---|---|
| Internal id | Yes | Primary key used by our tables if a later feature must reference a user |
| Clerk user id | Yes | Unique. The join key from a verified token. Never a password, never an email |
| Application role | Yes, once provisioned | `SALES_REP` or `SALES_MANAGER` only |
| `created_at` | Yes | Audit |
| `updated_at` | Yes | Audit |

Not stored: password, password hash, session token, Clerk secret, refresh token, or a copy of the
Clerk profile. The frontend reads display name and email from the Clerk session when it needs them.

No row is created on first login. Automatic provisioning would let anyone who can sign up in Clerk
become a user of the product. The hackathon team inserts rows on purpose.

`DATABASE_DESIGN.md` names the table and the constraints. The unique Clerk user id and the closed
role set are required there.

---

## 10. Error handling

Auth failures use the error envelope from `TECHNICAL_PRD.md` §13:

```json
{ "error": { "code": "AUTH_EXPIRED", "message": "Sign in again.", "details": {} } }
```

`API_CONTRACT.md` §2 and §3 use these codes. They are not optional.

| Situation | HTTP | Code | Message intent |
|---|---|---|---|
| No `Authorization` header, or empty bearer token | 401 | `AUTH_MISSING` | Authentication is required |
| Token is malformed, unsigned, or not issued by this Clerk instance | 401 | `AUTH_INVALID` | Authentication failed |
| Token is expired | 401 | `AUTH_EXPIRED` | Sign in again |
| Token is valid and no application user row exists | 403 | `USER_NOT_PROVISIONED` | Signed in, no access granted yet |
| Token is valid, row exists, role is missing or not one of the two codes | 403 | `USER_WITHOUT_ROLE` | Signed in, no application role |
| Token is valid, role is valid, operation does not allow that role | 403 | `INSUFFICIENT_PERMISSION` | Authenticated, not allowed |

`401` means we do not know an authenticated user. `403` means we do, and they may not proceed.

Responses do not include stack traces, the Clerk secret, the raw token, or whether some other
user exists. `401` messages stay generic. `403` messages may say that this account has no role,
because the caller already proved who they are.

---

## 11. Security rules

| Rule | Requirement |
|---|---|
| Token verification | Every protected request. Signature, issuer, and expiry checked with Clerk. A decoded-but-unverified token is never trusted |
| Protected endpoints | Default-on, §8 |
| Clerk secret | `CLERK_SECRET_KEY` on the backend only. It never appears in frontend code, frontend env, logs, or the repository |
| Publishable key | `VITE_CLERK_PUBLISHABLE_KEY` is the only Clerk value in the frontend. It is publishable by Clerk's design. It is still not committed with a real value |
| Passwords | Never received by FastAPI. Never hashed by us. Never written to PostgreSQL |
| Custom password hashing | Not implemented |
| Authorization | Server-side after verification. The UI hiding a control is irrelevant (`FR-ROLE-02`) |
| Role source | PostgreSQL only. A role claim inside the token is ignored if it disagrees with the row |
| Session expiry | An expired token is `401 AUTH_EXPIRED`. The frontend returns the user to `/login`. There is no silent continuation |
| Logout | Clerk invalidates the session. The client cache is cleared. Old tokens fail verification |
| Unauthorized access | `403` as in §10. The body contains no intelligence data |
| Logging | Tokens and secrets are never logged (`TECHNICAL_PRD.md` §14) |
| Transport | HTTPS in the hosted environment |
| Brute force and password policy | Clerk's controls. We do not add a second limiter on a login route we do not have |
| CORS | The backend allowlist is the frontend origin only (`TECHNICAL_PRD.md` §16). It is not an auth mechanism |

A Clerk outage blocks sign-in and token verification. The API then returns `401`. It does not fall
back to a local password check.

---

## 12. Environment variables

Names match `TECHNICAL_PRD.md` §16. Values are never written in the repository. `.env.example`
holds placeholders only.

| Variable | Process | Required | Purpose |
|---|---|---|---|
| `VITE_CLERK_PUBLISHABLE_KEY` | Frontend, build-time | Yes | Clerk browser SDK. Safe to be public. Not a secret |
| `CLERK_SECRET_KEY` | Backend | Yes | Verifies session tokens. Secret |
| `CORS_ALLOWED_ORIGINS` | Backend | Yes | Frontend origin allowed to call the API |

No `JWT_SECRET`. The backend does not sign tokens.

The Clerk Dashboard must allow the frontend origin used in each environment. That setting lives in
Clerk, not in this repository.

---

## 13. Local development

Minimum configuration:

1. One shared Clerk **development** instance for the team, so Clerk user ids match the shared
   development database (`TECHNICAL_PRD.md` §26).
2. Frontend `.env`: `VITE_CLERK_PUBLISHABLE_KEY=<development publishable key>`.
3. Backend `.env`: `CLERK_SECRET_KEY=<development secret key>`.
4. Two application user rows in the shared database, one role each, using the Clerk user ids from
   that same development instance.

Each developer copies `.env.example` to an untracked `.env`. Keys are not pasted into source, into
`AGENTS.md`, or into chat that gets committed.

Local sign-in uses the same `/login` route as production. The backend rejects tokens from a
different Clerk instance than the one for `CLERK_SECRET_KEY`.

---

## 14. Production considerations

The demonstration environment uses a separate Clerk instance from development, with its own keys
in the host's environment configuration. Development keys are not reused.

| Topic | Requirement |
|---|---|
| Keys | Production `CLERK_SECRET_KEY` only on the backend host. Production publishable key only as the frontend build variable |
| Instances | Development and demo Clerk instances stay separate, matching the separate demo database |
| Users | Demo `SALES_REP` and `SALES_MANAGER` rows exist before the demonstration. No self-service role grant |
| HTTPS | Required. Clerk and the hosts provide it |
| Sign-in availability | If Clerk is unreachable, users cannot sign in and API calls fail closed with `401` |
| Secrets in logs and errors | Forbidden (§11) |

No extra auth infrastructure. No session store, no Redis, no auth microservice.

---

## 15. MVP scope

Required for the hackathon:

1. Login through Clerk.
2. Logout through Clerk, with the client cache cleared.
3. An authenticated Clerk session.
4. A Clerk user id available to FastAPI after verification.
5. The `SALES_REP` role.
6. The `SALES_MANAGER` role.
7. Protected frontend routes that redirect when signed out.
8. Protected FastAPI routes that reject missing or bad tokens.
9. Backend role authorization using the PostgreSQL role row.

Both roles can see all tracked organizations. No assignment filter.

---

## 16. Out of scope

These are not part of the hackathon. They must not be built because they are nearby.

| Excluded | Why it stays out |
|---|---|
| Enterprise SSO | Already out of MVP in `AGENTS.md` §13 |
| SCIM and directory sync | Identity-management scope |
| Multi-tenancy | One internal deployment |
| Organization-level permissions and assignment | `FR-ROLE-04` |
| An admin UI for users and roles | Roles are inserted in the database for the week |
| Invitation workflows | Create the user in the Clerk Dashboard, then insert the role row |
| Custom password management, hashing, or reset | Clerk owns passwords |
| Social-login customization | Email/password is enough |
| FastAPI-issued JWTs | Rejected |
| Supabase Auth and Row Level Security as the auth system | Rejected. AD-05 stands |
| Clerk webhooks to auto-provision users | Extra moving part. Manual rows are enough for 10–20 organizations and a handful of users |
| Storing the role in Clerk public metadata as the source of truth | The role would then live outside PostgreSQL. The database row is the source of truth |

---

## Open questions

| # | Question | Status |
|---|---|---|
| A1 | FastAPI-native auth or Supabase Auth? | **Decided.** Neither. Clerk authenticates. FastAPI authorizes. PostgreSQL stores the role |
| A2 | Where is the role stored? | **Decided.** Application user row in PostgreSQL, keyed by Clerk user id. Not in Clerk metadata |
| A3 | Does sign-up grant a role? | **Decided.** No. A Clerk account with no role row receives `403 USER_NOT_PROVISIONED` |
| A4 | Which email addresses are the two demo accounts? | Left out of the repository on purpose. Create them in the Clerk Dashboard before the demo |
| A5 | Current-user path and schema | **Decided.** `GET /api/v1/me` returns `user_id`, `clerk_user_id`, and `role` (`API_CONTRACT.md` §2.1). `GET /api/v1/health` is the only public route |
