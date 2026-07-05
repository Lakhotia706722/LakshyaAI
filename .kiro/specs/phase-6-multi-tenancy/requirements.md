# Phase 6 — Multi-Tenancy, Auth, and Security Hardening
## Requirements

### Context

The MVP (Phases 0–5) is a single-tenant FastAPI + React application. Every authenticated
user currently sees all data in the database with no org-level isolation. Passwords are
hashed with raw SHA-256 (not bcrypt despite passlib being installed), JWTs have a 24-hour
lifetime with no refresh or revocation, there is no rate limiting, uploads are stored on
the local filesystem, and CORS is partially open. This phase closes all of those gaps
before a second customer can be onboarded.

Reference files:
- #[[file:backend/app/models.py]]
- #[[file:backend/app/routers/auth.py]]
- #[[file:backend/app/main.py]]
- #[[file:backend/app/db.py]]
- #[[file:backend/app/schemas.py]]
- #[[file:frontend/src/api/client.js]]
- #[[file:frontend/src/App.jsx]]

---

## REQ-1 — Organization Data Model

**REQ-1.1** Add an `organizations` table with columns: `id` (PK), `name` (string, not null),
`plan_tier` (string, default "free"), `created_at` (datetime).

**REQ-1.2** Add `org_id` (FK → organizations.id, not null, indexed) to every data-bearing
table: `companies`, `deals`, `deal_events`, `call_recordings`, `invoices`,
`forecast_snapshots`.

**REQ-1.3** Add an `org_members` table with columns: `id` (PK), `org_id` (FK), `user_id`
(FK), `role` (enum: `owner` / `admin` / `member`), `created_at` (datetime). A user may
belong to exactly one organization in the MVP. The first user to register an organization
is assigned the `owner` role automatically.

**REQ-1.4** Every service-layer query that reads or writes `companies`, `deals`,
`deal_events`, `call_recordings`, `invoices`, or `forecast_snapshots` **must** include a
`.filter(Model.org_id == current_org_id)` clause. No exceptions. This is the primary
data-isolation guarantee.

**REQ-1.5** All existing six router files (`deals.py`, `companies.py`,
`whatsapp_intelligence.py`, `call_intelligence.py`, `forecasting.py`, `auth.py`) must
derive `org_id` from the authenticated user's org membership and apply REQ-1.4 before
returning any data or writing any record.

---

## REQ-2 — User Model Changes

**REQ-2.1** Modify the `users` table:
- Add `is_email_verified` (boolean, default `False`)
- Add `email_verification_token` (string, nullable)
- Add `password_reset_token` (string, nullable)
- Add `password_reset_expires` (datetime, nullable)
- Add `provider` (string, nullable — values: `null` for email/password, `"google"` for
  OAuth later)
- Make `password_hash` nullable (required when provider is null, null when provider is
  not null)

**REQ-2.2** Remove the dead `pwd_context` references and unreachable code in `auth.py`.
Replace the current SHA-256 password hashing with `passlib[bcrypt]` (already in
`requirements.txt`). All new passwords must be hashed with bcrypt (cost factor 12 minimum).

**Security flag — needs sign-off:** Existing users in the database have SHA-256 hashes.
A migration path is needed: on next successful login with a correct SHA-256 password,
re-hash with bcrypt and update the record. After 90 days (or when convenient) the
SHA-256 fallback should be removed.

---

## REQ-3 — Authentication Flow Changes

**REQ-3.1 Short-lived access tokens + refresh tokens**
- Access tokens: 15-minute expiry, signed HS256 JWT, payload contains `user_id`, `org_id`,
  `role`.
- Refresh tokens: 7-day expiry, opaque random bytes (32 bytes, hex-encoded), stored
  **hashed** (SHA-256) in a new `refresh_tokens` table with columns `id`, `user_id`,
  `token_hash`, `expires_at`, `revoked` (boolean, default false), `created_at`.
- `POST /api/auth/refresh` accepts `{"refresh_token": "..."}` in the request body (not a
  cookie, for simplicity) and returns a new access token + new refresh token (token
  rotation).
- `POST /api/auth/logout` revokes the presented refresh token by setting `revoked = true`.

**REQ-3.2 Email verification on signup**
- On `POST /api/auth/register`, set `is_email_verified = False`, generate a 32-byte random
  URL-safe token, store it in `email_verification_token`, and send a verification email to
  the user.
- `GET /api/auth/verify-email?token=<token>` sets `is_email_verified = True` and clears
  the token field.
- Until the email is verified, the user may log in but a warning banner must be surfaced
  in the frontend. For MVP convenience, email-unverified users are not blocked from API
  access — just warned. (Blocking can be toggled via an env flag `REQUIRE_EMAIL_VERIFICATION`.)

**REQ-3.3 Password reset flow**
- `POST /api/auth/forgot-password` accepts `{"email": "..."}`, generates a 32-byte
  URL-safe reset token, stores it hashed in `password_reset_token` with a 1-hour expiry
  in `password_reset_expires`, and sends a reset email.
- `POST /api/auth/reset-password` accepts `{"token": "...", "new_password": "..."}`,
  validates the token (not expired, not already used), updates the password hash with
  bcrypt, and clears the reset token fields.
- Both endpoints must return the same generic success message whether or not the email
  exists (prevents email enumeration).

**REQ-3.4 Google OAuth stub**
- The `users` table already supports it via `provider` column (REQ-2.1).
- Add a `GOOGLE_OAUTH_ENABLED` feature flag (env var, default `false`). When false, the
  OAuth routes return HTTP 501 Not Implemented.
- When enabled: implement `GET /api/auth/google` (redirect to Google) and
  `GET /api/auth/google/callback` (exchange code, create/find user, issue tokens). Use
  `authlib` or `httpx` — do not add a new heavy OAuth library without confirming first.

**Security flag — needs sign-off:** The frontend currently stores the access token in
`localStorage`, which is vulnerable to XSS. Recommend moving to an `httpOnly` cookie for
the refresh token and keeping the access token in memory (React state). Confirm whether
to do this now or defer.

---

## REQ-4 — Rate Limiting on Auth Endpoints

**REQ-4.1** Add rate limiting to `POST /api/auth/login` and `POST /api/auth/register`:
maximum 5 attempts per IP per 15-minute window.

**REQ-4.2** Use Redis as the rate-limit store (add `redis` and `slowapi` to
`requirements.txt`). If Redis is unavailable at startup, log a warning and fall back to
an in-memory store (acceptable for single-instance dev; not for multi-instance prod).

**REQ-4.3** When the limit is exceeded, return HTTP 429 with a `Retry-After` header
indicating seconds until the window resets.

**REQ-4.4** Add `REDIS_URL` to `.env.example`. Document the Railway Redis add-on setup
in a comment in `.env.example`.

---

## REQ-5 — Role-Based Access Control (RBAC)

**REQ-5.1** Define three roles with the following permissions:

| Action | owner | admin | member |
|---|---|---|---|
| Read all org data | ✓ | ✓ | ✓ |
| Create/update companies, deals | ✓ | ✓ | ✓ |
| Delete companies, deals | ✓ | ✓ | ✗ |
| Invite/remove members | ✓ | ✓ | ✗ |
| Change org plan | ✓ | ✗ | ✗ |
| Export/delete org data | ✓ | ✗ | ✗ |

**REQ-5.2** Implement a `require_role(minimum_role)` dependency function that raises
HTTP 403 if the current user's role is insufficient.

**REQ-5.3** Apply `require_role` to all DELETE endpoints (require `admin`) and to the
data export/deletion endpoints from REQ-8 (require `owner`).

---

## REQ-6 — Audit Log

**REQ-6.1** Add an `audit_log` table: `id` (PK), `org_id` (FK), `user_id` (FK),
`action` (string — e.g. `"create"`, `"update"`, `"delete"`), `resource_type` (string —
e.g. `"deal"`, `"company"`), `resource_id` (integer), `diff_json` (JSON, nullable —
stores before/after for updates), `timestamp` (datetime), `ip_address` (string).

**REQ-6.2** Log all create, update, and delete operations on `deals` and `companies`.
Log all delete operations on `call_recordings` and `invoices`.

**REQ-6.3** The audit log is append-only. No route should update or delete audit log rows.

**REQ-6.4** Add `GET /api/audit-log` (owner/admin only) that returns paginated audit log
entries for the caller's org, with optional filters: `resource_type`, `user_id`,
`from_date`, `to_date`. Default page size 50.

---

## REQ-7 — Security Hardening

**REQ-7.1 CORS**
- Change the `allow_origins` list in `main.py` to only include explicitly configured
  origins from the `FRONTEND_URL` env var.
- Remove the catch-all `allow_origin_regex` for all `*.vercel.app` URLs. Replace with an
  explicit `ALLOWED_EXTRA_ORIGINS` env var (comma-separated) for preview URLs during dev.
- Add `HSTS` and `X-Content-Type-Options` response headers via middleware.

**REQ-7.2 Prompt injection prevention**
- In `ai_extraction.py` and `transcription.py`, all user-supplied text (WhatsApp chat
  content, call transcripts, deal notes) that is interpolated into AI prompts must be
  wrapped in a sanitisation step before insertion.
- The sanitisation must: (a) truncate to a max length (WhatsApp: 50 000 chars, transcripts:
  100 000 chars), (b) strip any occurrence of the strings `"<SYSTEM>"`, `"[INST]"`,
  `"###"` and similar prompt-boundary markers, (c) insert the user text between explicit
  delimiter tags (`<user_input>` / `</user_input>`) and the system prompt must instruct
  Claude to treat content between those tags as data, never as instructions.
- This must be implemented as a shared utility function `sanitize_for_prompt(text, max_len)`
  in a new file `backend/app/services/prompt_safety.py`.

**REQ-7.3 File upload hardening**
- Maximum upload size: 50 MB (audio files).
- Validate MIME type via file header magic bytes (use `python-magic` or `filetype` library),
  not just the `Content-Type` header. Reject anything that is not `audio/*`.
- Store uploaded files in S3-compatible object storage (AWS S3 or Cloudflare R2). Add
  `AWS_S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` (or
  equivalent R2 vars) to `.env.example`.
- The local `uploads/` directory fallback remains for local dev when S3 vars are not set.
- **Security flag — needs sign-off:** Moving to S3 changes the Whisper call from a local
  file path to a pre-signed URL or streamed bytes. Confirm approach before implementation.

**REQ-7.4 Per-org API rate limiting**
- Add a secondary rate limit of 1 000 API requests per org per hour across all
  non-auth endpoints. Return HTTP 429 when exceeded.
- This limit is stored in Redis (same instance as REQ-4.2).

**REQ-7.5 Secrets management**
- Add a `backend/app/config.py` using `pydantic-settings` `BaseSettings` that loads all
  configuration from environment variables with explicit types and validation (no silent
  fallback to insecure defaults in production).
- Add an `APP_ENV` env var (`development` / `production`). In `production`, startup must
  fail with a clear error if `JWT_SECRET` is the default placeholder value or is shorter
  than 32 characters.
- Document Doppler as the recommended secrets manager in `.env.example` with setup notes.
  Do not add Doppler as a code dependency — it is a CLI-level tool.

---

## REQ-8 — DPDP Act Compliance Basics

**REQ-8.1 Consent records**
- Add a `consent_records` table: `id`, `org_id`, `user_id`, `data_subject_identifier`
  (string — phone number or email of the third-party contact whose data is being
  processed), `consent_type` (enum: `call_recording`, `whatsapp_processing`),
  `consented_at` (datetime), `consent_source` (string — e.g. `"verbal_on_call"`,
  `"whatsapp_opt_in"`), `withdrawn_at` (datetime, nullable).
- When uploading a call recording or submitting WhatsApp chat text, the API must accept
  an optional `consent_record_id` parameter. If absent, a warning is logged but the
  request is not blocked (enforcement is deferred to a later phase after legal review).

**REQ-8.2 Data retention policy**
- Add `recording_retention_days` (integer, default 90) to the `organizations` table.
- Add a background job (can be a standalone script initially, not a full Celery setup)
  `backend/scripts/retention_cleanup.py` that deletes `call_recordings` rows (and their
  associated S3/local files) older than `org.recording_retention_days`.
- The raw `file_path`/S3 key is deleted; the `transcript` and `analysis_json` columns are
  retained unless the deal itself is deleted.

**REQ-8.3 Data export endpoint**
- `GET /api/org/export` (owner only) returns a JSON file download containing all org
  data: organizations record, all members, all companies, all deals with events, all
  call recordings (metadata only, not raw audio), all invoices, all forecast snapshots.
- The export must complete within 30 seconds for orgs with up to 10 000 records; for
  larger orgs, return a 202 Accepted and implement async export with a download link
  (defer async implementation — note it as a known limitation for now).

**REQ-8.4 Data deletion endpoint**
- `DELETE /api/org` (owner only) permanently deletes all data for the org: all rows in
  all tables with the org's `org_id`, all S3/local files, and the org record itself.
- This endpoint requires a confirmation body: `{"confirm": "DELETE <org_name>"}` to
  prevent accidental calls.
- This logs to the audit log (using the requesting user's ID) before deletion, then
  proceeds with deletion. This is the one audit log write that does not require the
  org to exist afterward.

---

## REQ-9 — Alembic Migration Discipline

**REQ-9.1** The current practice of `Base.metadata.create_all(bind=engine)` on every
startup is unsafe for production because it cannot alter existing tables or columns.
`create_all` must be removed from `main.py` startup for the production environment
(`APP_ENV == "production"`). In development it can remain for convenience.

**REQ-9.2** All schema changes in this phase must be delivered as numbered Alembic
migration files in `backend/alembic/versions/`. Each migration must have a functioning
`downgrade()` function.

**REQ-9.3** The `alembic/versions/` directory must be populated with at least two
migration files: one for all new tables (organizations, org_members, refresh_tokens,
audit_log, consent_records) and one for all column additions to existing tables.

---

## REQ-10 — Frontend Auth Updates

**REQ-10.1** The frontend `api/client.js` must be updated to handle token refresh:
when a request returns HTTP 401, attempt one silent refresh via
`POST /api/auth/refresh`, update the stored token, and retry the original request.
If the refresh also fails, redirect to `/login`.

**REQ-10.2** Add a signup page at `/register` that calls `POST /api/auth/register`.
After successful registration, show a "Check your email to verify your account" message.

**REQ-10.3** Add a forgot-password page at `/forgot-password` and a reset-password page
at `/reset-password?token=<token>` that call the corresponding endpoints from REQ-3.3.

**REQ-10.4** Show an email verification warning banner in the main layout when
`user.is_email_verified === false`.

**REQ-10.5** Show the logged-in user's organization name and role in the sidebar/header.

---

## Non-Requirements (explicitly out of scope for Phase 6)

- Celery / background job queue (deferred to Phase 7)
- Tally, WhatsApp BSP, diarization integrations (Phases 7–10)
- Full billing integration (Phase 12)
- Multi-org membership (one user in multiple orgs) — single org per user for now
- SSO with Google beyond the stub in REQ-3.4

---

## Acceptance Criteria

1. A user can register an org, verify their email, log in with bcrypt-hashed credentials,
   and receive a 15-minute access token + 7-day refresh token.
2. Two separate orgs cannot see each other's deals, companies, or any other data — verified
   by creating data in Org A and confirming it does not appear when authenticated as Org B.
3. Five failed login attempts from the same IP within 15 minutes result in HTTP 429.
4. All create/update/delete actions on deals and companies produce an audit log entry.
5. The org data export endpoint returns a complete JSON file for the org's data.
6. The org data deletion endpoint removes all traces of the org's data from the database.
7. Uploading a non-audio file to the call recording endpoint is rejected with HTTP 422.
8. The `sanitize_for_prompt` function strips prompt injection markers from user text.
9. All schema changes are delivered as Alembic migrations with working downgrade paths.
10. The frontend handles token expiry transparently (silent refresh) without logging the
    user out mid-session.
