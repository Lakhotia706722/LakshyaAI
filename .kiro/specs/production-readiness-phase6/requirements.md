# Requirements Document

## Introduction

Phase 6 transforms LakshyaAI from a single-tenant MVP into a production-ready B2B SaaS platform. The changes span four concern areas: (1) multi-tenancy with strict org-level data isolation, (2) hardened authentication using short-lived tokens, email verification, password reset, rate limiting, and Google OAuth readiness, (3) security hardening covering secrets management, prompt injection prevention, file upload safety, HTTPS/HSTS/CORS, and per-org API rate limiting, and (4) DPDP Act compliance including consent records, data retention policies, and org-admin export/deletion endpoints.

The existing backend is FastAPI + SQLAlchemy (SQLite in dev, Postgres in prod) and the frontend is React/Vite. All existing tables — `companies`, `deals`, `deal_events`, `call_recordings`, `invoices`, `forecast_snapshots` — must be scoped to an `org_id`.

---

## Glossary

- **System**: The LakshyaAI backend API and its supporting services as a whole.
- **API**: The FastAPI backend application at `lakshya-ai/backend`.
- **Auth_Service**: The component responsible for authentication, token issuance, and session management (currently `app/routers/auth.py`).
- **Token_Store**: The database table (`refresh_tokens`) that persists hashed refresh tokens.
- **Organization**: A tenant record in the `organizations` table; the top-level isolation boundary.
- **Org_Member**: A user who belongs to an Organization, with a role of `owner`, `admin`, or `member` stored in `org_members`.
- **RBAC**: Role-Based Access Control enforced through the `org_members` table.
- **Query_Layer**: Every SQLAlchemy service function that reads or writes tenant data; must filter by `org_id` without exception.
- **Audit_Log**: The `audit_log` table recording create/update/delete actions on deals and companies.
- **AI_Prompt_Builder**: The component in `app/services/ai_extraction.py` that constructs prompts sent to the Claude API.
- **Prompt_Injection**: An attack where user-supplied text contains instructions intended to override or manipulate the AI_Prompt_Builder's intended behaviour.
- **File_Upload_Handler**: The component that accepts multipart file uploads (currently `app/routers/call_intelligence.py`).
- **Secrets_Manager**: An external service (AWS Secrets Manager or Doppler) that stores application secrets outside of `.env` files.
- **Rate_Limiter**: The middleware component that enforces request-per-window limits, backed by Redis.
- **DPDP_Act**: India's Digital Personal Data Protection Act 2023.
- **Consent_Record**: A row in the `consent_records` table documenting a data subject's consent for personal data processing.
- **Data_Retention_Policy**: Per-org configuration controlling how long raw personal data (call recordings, WhatsApp content) is retained before automatic deletion.
- **Access_Token**: A short-lived JWT (15-minute expiry) used to authenticate API requests.
- **Refresh_Token**: A long-lived opaque token (7-day expiry) stored hashed in the database, used to obtain new Access_Tokens.
- **SSO**: Single Sign-On; specifically Google OAuth 2.0 for this phase.
- **HSTS**: HTTP Strict Transport Security response header.
- **CORS**: Cross-Origin Resource Sharing; controls which origins may call the API.

---

## Requirements

---

### Requirement 1: Organization and Multi-Tenancy Data Model

**User Story:** As a platform operator, I want every tenant's data isolated at the database level, so that one customer can never read or modify another customer's records.

#### Acceptance Criteria

1. THE System SHALL create an `organizations` table with columns: `id` (primary key), `name` (non-null string), `plan_tier` (string), and `created_at` (timestamp).
2. THE System SHALL add a non-null `org_id` foreign key referencing `organizations.id` to the `companies`, `deals`, `deal_events`, `call_recordings`, `invoices`, and `forecast_snapshots` tables via Alembic migrations.
3. THE System SHALL create an `org_members` table with columns: `org_id` (FK → organizations), `user_id` (FK → users), `role` (enum: `owner` | `admin` | `member`), and `created_at` (timestamp), with a composite primary key on `(org_id, user_id)`.
4. THE System SHALL create an `audit_log` table with columns: `id`, `org_id`, `user_id`, `action` (string), `resource_type` (string), `resource_id` (integer), `timestamp` (datetime), and `ip_address` (string).
5. WHEN a user authenticates successfully, THE Auth_Service SHALL resolve the user's current `org_id` from `org_members` and embed it in the Access_Token payload.
6. WHEN a new user registers and no existing organization is provided, THE System SHALL create a new Organization record and assign the registering user the `owner` role in `org_members`.

---

### Requirement 2: Query-Layer Org Isolation

**User Story:** As a security engineer, I want every database query that touches tenant data to be filtered by `org_id`, so that cross-tenant data leaks are structurally impossible.

#### Acceptance Criteria

1. WHEN the Query_Layer executes any SELECT, INSERT, UPDATE, or DELETE on `companies`, `deals`, `deal_events`, `call_recordings`, `invoices`, or `forecast_snapshots`, THE Query_Layer SHALL apply an `org_id` filter equal to the authenticated user's `org_id`.
2. IF a request arrives without a valid Access_Token, THEN THE API SHALL return HTTP 401 before any Query_Layer function is invoked.
3. IF the Query_Layer receives a resource identifier that belongs to a different `org_id` than the authenticated user, THEN THE API SHALL return HTTP 404, not HTTP 403, to avoid leaking resource existence.
4. THE Query_Layer SHALL enforce `org_id` isolation at the service function level, not solely at the router level, so that future internal callers cannot bypass the check.

---

### Requirement 3: Role-Based Access Control (RBAC)

**User Story:** As an org admin, I want only members with sufficient roles to perform destructive or sensitive operations, so that I can control what each team member can do.

#### Acceptance Criteria

1. THE System SHALL define three roles: `owner`, `admin`, and `member`, with `owner` having a strict superset of `admin` permissions, and `admin` having a strict superset of `member` permissions.
2. WHEN a request to delete a company, deal, or any resource is received, THE API SHALL verify that the authenticated user's role is `admin` or `owner` before executing the deletion.
3. WHEN a request to export or delete all org data is received (DPDP endpoints), THE API SHALL verify that the authenticated user's role is `owner` before proceeding.
4. WHEN a request to invite or remove an org member is received, THE API SHALL verify that the authenticated user's role is `admin` or `owner`.
5. IF the authenticated user's role is insufficient for the requested operation, THEN THE API SHALL return HTTP 403.

---

### Requirement 4: Short-Lived Access Tokens and Refresh Token Flow

**User Story:** As a security-conscious operator, I want access tokens to expire quickly and be refreshable without re-login, so that stolen tokens have a limited window of exploitability.

#### Acceptance Criteria

1. THE Auth_Service SHALL issue Access_Tokens with a maximum lifetime of 15 minutes.
2. THE Auth_Service SHALL issue a Refresh_Token with a lifetime of 7 days upon successful login or registration.
3. THE Auth_Service SHALL store only the SHA-256 hash of each Refresh_Token in the Token_Store, never the plaintext value.
4. WHEN a client submits a valid Refresh_Token to the `/api/auth/refresh` endpoint, THE Auth_Service SHALL issue a new Access_Token and rotate the Refresh_Token (invalidate the old hash, store a new hash).
5. WHEN a client submits a Refresh_Token that does not match any row in the Token_Store, THE Auth_Service SHALL return HTTP 401.
6. WHEN a user explicitly logs out, THE Auth_Service SHALL delete the corresponding Refresh_Token row from the Token_Store, making the token irrevocable.
7. THE Auth_Service SHALL support revoking all Refresh_Tokens for a given user (e.g., "sign out of all devices") by deleting all Token_Store rows for that `user_id`.
8. THE Token_Store table SHALL include columns: `id`, `user_id` (FK → users), `token_hash` (string, indexed), `expires_at` (datetime), `created_at` (datetime).

---

### Requirement 5: Email Verification

**User Story:** As a platform operator, I want new accounts to verify their email address before accessing the system, so that I can prevent registration with disposable or fake addresses.

#### Acceptance Criteria

1. WHEN a new user registers, THE Auth_Service SHALL send a verification email containing a single-use token to the provided email address.
2. WHEN a user submits a valid, unexpired verification token to the `/api/auth/verify-email` endpoint, THE Auth_Service SHALL mark the user's account as `email_verified = true`.
3. WHILE a user's account has `email_verified = false`, THE Auth_Service SHALL return HTTP 403 with a clear message on any login attempt, directing the user to verify their email.
4. THE Auth_Service SHALL expire email verification tokens after 24 hours.
5. IF a user requests a resend of the verification email, THEN THE Auth_Service SHALL invalidate any previous unexpired verification token for that account before issuing a new one.

---

### Requirement 6: Password Reset Flow

**User Story:** As a user, I want to reset my password via email when I forget it, so that I can regain access to my account without contacting support.

#### Acceptance Criteria

1. WHEN a password reset request is submitted for a registered email, THE Auth_Service SHALL send a reset email containing a single-use token, regardless of whether the email exists, to prevent user enumeration.
2. THE Auth_Service SHALL expire password reset tokens after 1 hour.
3. WHEN a user submits a valid, unexpired reset token and a new password to the `/api/auth/reset-password` endpoint, THE Auth_Service SHALL update the user's `password_hash` and immediately invalidate the token.
4. IF a password reset token has already been used or has expired, THEN THE Auth_Service SHALL return HTTP 400 with a descriptive error.
5. WHEN a password is successfully reset, THE Auth_Service SHALL revoke all existing Refresh_Tokens for that user.

---

### Requirement 7: Auth Endpoint Rate Limiting

**User Story:** As a security engineer, I want login and registration endpoints to be rate-limited per IP address, so that brute-force and credential-stuffing attacks are mitigated.

#### Acceptance Criteria

1. THE Rate_Limiter SHALL enforce a limit of 5 requests per 15-minute sliding window per IP address on the `/api/auth/login` endpoint.
2. THE Rate_Limiter SHALL enforce a limit of 10 requests per hour per IP address on the `/api/auth/register` endpoint.
3. IF a request exceeds the applicable rate limit, THEN THE API SHALL return HTTP 429 with a `Retry-After` header indicating the number of seconds until the window resets.
4. THE Rate_Limiter SHALL use Redis as its backing store to maintain state across multiple API worker processes.
5. THE Rate_Limiter SHALL apply the same limits to the `/api/auth/forgot-password` endpoint to prevent email-based enumeration through timing.

---

### Requirement 8: Google OAuth SSO Readiness

**User Story:** As an enterprise customer, I want to sign in with my Google Workspace account, so that my team does not need to manage separate credentials.

#### Acceptance Criteria

1. THE System SHALL store a `provider` column (string, default `local`) and a nullable `password_hash` column on the `users` table, enabling the OAuth user record to omit a password.
2. WHERE Google OAuth is configured via environment variables, THE Auth_Service SHALL implement the `/api/auth/google` and `/api/auth/google/callback` endpoints following the OAuth 2.0 authorization code flow.
3. WHEN a Google OAuth callback is received with a valid authorization code, THE Auth_Service SHALL upsert a user record (match on email), set `provider = 'google'`, and issue a standard Access_Token and Refresh_Token pair.
4. WHERE Google OAuth is not configured, THE Auth_Service SHALL return HTTP 501 on the Google OAuth endpoints with a message indicating the feature is not enabled.
5. THE System SHALL NOT require `password_hash` to be non-null when `provider` is not `local`.

---

### Requirement 9: Secrets Management

**User Story:** As a platform operator, I want all application secrets stored in a dedicated secrets manager rather than in `.env` files, so that secrets are never committed to source control and can be rotated without redeployment.

#### Acceptance Criteria

1. THE System SHALL load secrets (API keys, database credentials, JWT secret, SMTP credentials) from AWS Secrets Manager or Doppler at application startup, not from `.env` files in production.
2. THE System SHALL fall back to environment variables only in the `development` environment, so that local development is unaffected.
3. IF the Secrets_Manager is unreachable at startup in a non-development environment, THEN THE System SHALL log a fatal error and refuse to start.
4. THE System SHALL never log secret values; log entries SHALL reference secrets by name only (e.g., `"ANTHROPIC_API_KEY"`, not the key value).
5. THE System SHALL provide a documented `.env.example` file listing every required secret name with placeholder values and a comment explaining each.

---

### Requirement 10: AI Prompt Injection Prevention

**User Story:** As a security engineer, I want user-supplied text that flows into AI prompts to be treated as untrusted data, never as instructions, so that a malicious WhatsApp message or call transcript cannot manipulate the Claude API calls.

#### Acceptance Criteria

1. THE AI_Prompt_Builder SHALL insert all user-supplied text into prompts exclusively within clearly delimited data sections (e.g., enclosed in XML-style tags such as `<conversation>…</conversation>` or `<transcript>…</transcript>`), separate from the system instructions.
2. THE AI_Prompt_Builder SHALL prepend a system-level instruction to every prompt stating that content within the data delimiters is untrusted user data and SHALL NOT be interpreted as instructions.
3. IF user-supplied text contains sequences that could be interpreted as prompt instructions (e.g., strings matching patterns like `"Ignore previous instructions"`, `"You are now"`, `"SYSTEM:"`, or `"[INST]"`), THEN THE AI_Prompt_Builder SHALL log a warning with the org_id and resource_id, and SHALL still process the request with the text treated as data, not instructions.
4. THE AI_Prompt_Builder SHALL NOT concatenate user-supplied text directly into the instruction portion of any prompt string.
5. THE System SHALL treat all text originating from WhatsApp exports, call transcripts, and deal event `raw_text` fields as untrusted content in prompt construction, regardless of the authenticated user's role.

---

### Requirement 11: File Upload Security

**User Story:** As a security engineer, I want uploaded files to be validated and stored safely, so that malicious uploads cannot compromise the server or consume unbounded resources.

#### Acceptance Criteria

1. THE File_Upload_Handler SHALL reject any uploaded file whose size exceeds 50 MB, returning HTTP 413.
2. THE File_Upload_Handler SHALL validate the uploaded file's MIME type by inspecting file magic bytes (not solely the `Content-Type` header), and SHALL reject files that are not audio formats (`audio/mpeg`, `audio/mp4`, `audio/wav`, `audio/ogg`, `audio/webm`), returning HTTP 415.
3. THE File_Upload_Handler SHALL store all accepted files in an S3-compatible object storage bucket, not on the local filesystem.
4. THE File_Upload_Handler SHALL generate a UUID-based object key for each upload, discarding the original filename to prevent path traversal.
5. IF object storage upload fails, THEN THE File_Upload_Handler SHALL return HTTP 502 and SHALL NOT save any file reference to the database.
6. WHERE ClamAV is available in the deployment environment, THE File_Upload_Handler SHALL scan uploaded files for malware before storing them and SHALL reject infected files with HTTP 422.

---

### Requirement 12: HTTPS, HSTS, and CORS Hardening

**User Story:** As a security engineer, I want all traffic encrypted in transit and browser-level protections active, so that the API is not reachable over plain HTTP and is not open to cross-origin abuse.

#### Acceptance Criteria

1. THE System SHALL respond to all HTTP requests with a redirect to HTTPS in production environments.
2. THE API SHALL include an `HSTS` header with `max-age=31536000; includeSubDomains` on all HTTPS responses in production.
3. THE API SHALL restrict the CORS `allow_origins` list to the exact frontend domain specified in the `FRONTEND_URL` environment variable, and SHALL NOT use a wildcard (`*`) or the broad Vercel preview regex in production.
4. THE API SHALL include `Referrer-Policy: strict-origin-when-cross-origin` and `X-Content-Type-Options: nosniff` headers on all responses.
5. THE API SHALL set the `Vary: Origin` header on all CORS-preflight responses.

---

### Requirement 13: Per-Org API Rate Limiting

**User Story:** As a platform operator, I want API usage limited per organization, so that a single customer's scripted requests cannot degrade service quality for all other tenants.

#### Acceptance Criteria

1. THE Rate_Limiter SHALL enforce a configurable per-org request limit, with a default of 1,000 requests per minute per Organization.
2. WHEN an Organization exceeds its per-org rate limit, THE API SHALL return HTTP 429 with a `Retry-After` header and a `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` response header set.
3. THE Rate_Limiter SHALL use a sliding window algorithm backed by Redis to calculate per-org usage.
4. THE Rate_Limiter SHALL apply per-org limits only to authenticated requests; unauthenticated requests SHALL be subject only to per-IP limits from Requirement 7.
5. THE API SHALL expose the rate limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`) on every authenticated response, not only on rate-limited responses.

---

### Requirement 14: Audit Logging

**User Story:** As an org admin, I want a tamper-evident log of all create, update, and delete actions on deals and companies, so that I can investigate suspicious activity.

#### Acceptance Criteria

1. WHEN a deal or company record is created, updated, or deleted, THE System SHALL write a row to the `audit_log` table containing: `org_id`, `user_id`, `action` (one of `create`, `update`, `delete`), `resource_type` (e.g., `deal`, `company`), `resource_id`, `timestamp` (UTC), and `ip_address` of the request.
2. THE System SHALL write audit log entries synchronously within the same database transaction as the mutation, so that an audit entry is never missing for a committed change.
3. THE System SHALL NOT delete audit log entries; the `audit_log` table SHALL have no DELETE permissions granted at the application layer.
4. WHEN an org admin requests the audit log via `GET /api/org/audit-log`, THE API SHALL return entries paginated by 50 per page, filterable by `resource_type`, `user_id`, and date range.
5. THE audit log endpoint SHALL be restricted to users with role `admin` or `owner`.

---

### Requirement 15: DPDP Act — Consent Records

**User Story:** As a data protection officer, I want a consent record created for every piece of personal data processed on a third party (deal contacts), so that the platform can demonstrate lawful basis for processing under the DPDP Act.

#### Acceptance Criteria

1. THE System SHALL create a `consent_records` table with columns: `id`, `org_id`, `data_subject_identifier` (string — hashed contact identifier), `data_type` (enum: `call_recording`, `whatsapp_content`, `contact_info`), `purpose` (string), `consent_given_at` (datetime), `consent_source` (string — e.g., `org_admin_assertion`), and `revoked_at` (nullable datetime).
2. WHEN a call recording is uploaded or a WhatsApp conversation is submitted for analysis, THE System SHALL require an associated `consent_record_id` or SHALL create a pending consent record linked to the processing event.
3. IF a consent record for the data subject is marked as revoked (`revoked_at` is not null), THEN THE System SHALL reject new processing requests for that data subject with HTTP 451 (Unavailable For Legal Reasons).
4. THE System SHALL provide a `POST /api/org/consent` endpoint for org admins to record consent for a data subject.
5. THE System SHALL provide a `GET /api/org/consent` endpoint for org admins to list all consent records for their organization.

---

### Requirement 16: Data Retention Policy

**User Story:** As an org admin, I want to configure how long raw personal data is retained before automatic deletion, so that the platform retains data only as long as necessary under the DPDP Act.

#### Acceptance Criteria

1. THE System SHALL add a `data_retention_days` column (integer, default 90) to the `organizations` table, representing the number of days raw call recordings are retained before automatic deletion.
2. THE System SHALL run a daily background job that deletes call recording files from object storage and sets `call_recordings.file_path` to null for any `CallRecording` whose `created_at` is older than the owning organization's `data_retention_days`.
3. THE System SHALL retain the `CallRecording` row and its `transcript` and `analysis_json` columns after file deletion; only the raw file SHALL be removed.
4. WHEN the retention job deletes a file, THE System SHALL write an `audit_log` entry with `action = 'auto_delete'`, `resource_type = 'call_recording'`, and the affected `resource_id`.
5. WHEN an org admin updates `data_retention_days` via `PATCH /api/org/settings`, THE System SHALL validate that the new value is between 1 and 3650 inclusive; IF the value is outside this range, THEN THE API SHALL return HTTP 422.

---

### Requirement 17: Data Export Endpoint

**User Story:** As an org admin, I want to export all my organization's data in a structured format, so that I can fulfill data portability obligations under the DPDP Act or migrate to another platform.

#### Acceptance Criteria

1. THE System SHALL provide a `GET /api/org/export` endpoint restricted to users with role `owner`.
2. WHEN an export is requested, THE System SHALL return a JSON document containing all records from `companies`, `deals`, `deal_events`, `call_recordings` (metadata only, not file contents), `invoices`, `forecast_snapshots`, `consent_records`, and `audit_log` that belong to the requesting organization.
3. THE System SHALL set the response `Content-Disposition: attachment; filename="org_export_{org_id}_{date}.json"` header.
4. THE System SHALL write an `audit_log` entry with `action = 'export'` and `resource_type = 'organization'` when an export is triggered.
5. IF the export payload exceeds 10 MB, THEN THE System SHALL generate the export asynchronously, write it to object storage, and return a pre-signed download URL instead of streaming the response inline.

---

### Requirement 18: Data Deletion Endpoint

**User Story:** As an org admin, I want to permanently delete all my organization's data on request, so that the platform can honor deletion requests as required by the DPDP Act.

#### Acceptance Criteria

1. THE System SHALL provide a `DELETE /api/org` endpoint restricted to users with role `owner`.
2. WHEN an org deletion is requested, THE API SHALL require the org owner to confirm by submitting their current password in the request body before proceeding.
3. WHEN confirmed, THE System SHALL delete all records in `companies`, `deals`, `deal_events`, `call_recordings`, `invoices`, `forecast_snapshots`, `consent_records`, `org_members`, and all associated files from object storage for the requesting organization.
4. THE System SHALL delete the `organizations` row last, after all dependent records are removed.
5. THE System SHALL write a final `audit_log` entry with `action = 'org_delete'` before the organization row is deleted, and SHALL retain this entry in a separate compliance-grade log store (e.g., a separate database table `compliance_audit_log` not subject to cascading deletion) for 7 years.
6. IF any step of the deletion fails, THEN THE System SHALL roll back all database changes and return HTTP 500 with a support reference code; partial deletion SHALL NOT be committed.

---

### Requirement 19: WhatsApp Chat Parser Round-Trip

**User Story:** As a developer, I want the WhatsApp export parser to be verifiably correct, so that intelligence extracted from chat exports is based on accurate message data.

#### Acceptance Criteria

1. THE System SHALL expose a `parse_whatsapp_export` function that parses WhatsApp export text into an ordered list of message objects, each with `date`, `time`, `sender`, and `message` fields.
2. THE System SHALL expose a `format_whatsapp_export` function (pretty-printer) that serialises a list of message objects back into WhatsApp export text format.
3. FOR ALL valid WhatsApp export strings, parsing then formatting then parsing SHALL produce a list of message objects equivalent to the first parse result (round-trip property).
4. WHEN a line in the WhatsApp export does not match the expected format, THE Parser SHALL attach the line as a continuation of the previous message's `message` field.
5. IF the WhatsApp export string is empty or contains no parseable messages, THEN THE Parser SHALL return an empty list without raising an exception.
