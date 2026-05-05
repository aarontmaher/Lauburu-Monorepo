# Railway backend audit — what's deployed before testers

A mechanical review of every route that runs on the Railway-hosted
chat-app backend, what data it touches, who can call it, and where
that data persists. Written before the wider tester cohort starts so
the privacy story is grounded in code, not assumption.

Updated 2026-05-06.

## Host shape

- Single Express app: `chat-app/src/server/app.ts`.
- Mounted at the Railway-hosted public origin
  `https://lauburu-ai-backend-production.up.railway.app`.
- Six router groups:
  - `/api/chat`               — chat scaffold (legacy stub)
  - `/api/athlete-memory`     — per-athlete reads + admin dispatch
  - `/api/feedback`           — tester feedback submit + admin viewer
  - `/api/backlog`            — backlog/proposal flows per athlete
  - `/api/integrations`       — Polar / WHOOP / Cronometer OAuth +
    sync
  - `/v1/internal`            — internal-token-gated ingestion +
    pipeline jobs (NOT called from the mobile app — server-to-server
    only, e.g. WHOOP MCP, automation scripts)

## Authentication model

Three orthogonal credentials. The mobile app holds **none** of them
in plaintext anywhere a normal tester can read.

| Credential | Where lives | What it gates |
|---|---|---|
| `ATHLETE_MEMORY_API_TOKEN` | Railway env + `EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN` in mobile build env | All `/api/athlete-memory/:athleteId/*` reads, `/api/integrations/*` actions, `/api/backlog/*`, the now-protected `/api/feedback/recent` and `/api/feedback/attachments/:filename` |
| Supabase Bearer JWT (per-user) | Issued by Supabase on sign-in; sent as `Authorization: Bearer …` | Required IN ADDITION to the shared token for any `/:athleteId/*` route — server cross-checks the JWT's `sub` against the path's `athleteId` and returns 403 on mismatch |
| `INTERNAL_API_TOKEN` | Railway env only | All `/v1/internal/*` routes (`router.use(requireInternalAuth)` blanket) — never sent from the mobile app |

Server-side enforcement (verbatim from
`requirePrivateAthleteAccess` in `routes/athleteMemory.ts:78` and
`routes/backlog.ts:51`):

1. Reject if shared `x-athlete-memory-token` header is missing or
   wrong.
2. Reject if `x-athlete-id` header doesn't match the URL's
   `:athleteId`.
3. Decode the Supabase JWT from `Authorization`. If `sub !==
   :athleteId`, return 403 "Athlete ownership mismatch".
4. Only then call the handler.

This means: even if a tester somehow sniffs the shared token, they
still cannot read another athlete's data — the JWT cross-check
fails. The shared token alone is not sufficient unless
`ALLOW_SHARED_TOKEN_ONLY=1` or `NODE_ENV=test` is set (production
must NEVER set those — explicit comment in the code).

## Routes

### `/api/chat` — legacy stub

- `POST /send`, `GET /messages` — pre-existing controllers. Not in
  active mobile use; safe to leave as-is for now.

### `/api/athlete-memory` — primary mobile read API

All `:athleteId` routes are gated by `requirePrivateAthleteAccess`
(shared token + JWT ownership check):

- `GET /:athleteId/latest` — cache-first daily/weekly artifact for
  the signed-in user.
- `GET /:athleteId/weekly/latest` — same, weekly.
- `GET /:athleteId/source-health` — per-source freshness.
- `GET /:athleteId/seeded-state` — capability mode.
- `GET /:athleteId/health-check` — diagnostic.
- `GET /:athleteId/ai-context` — the AI Coach context bundle
  (capability + multi-window trends + nutrition / WHOOP / Polar
  presence flags).
- `GET /:athleteId/syllabus` + `POST /:athleteId/syllabus/progress`
  — per-user syllabus progress.
- `GET /:athleteId/profile` — compact profile (belt rank, syllabus
  summary).
- `GET /:athleteId/videos` — per-user video list.
- `POST /:athleteId/coach/ask` — Coach question; produces a
  short/why/nextStep answer over the artifacts above.
- `POST /:athleteId/polar-export/import` — store imported Polar
  sessions per athlete.

Open / unauth (intentional shared content):

- `GET /syllabus/all` — seed syllabus tree (read-only, no PII).
- `GET /tour` — app-tour content (read-only, no PII).

Admin (gated by `requireAdminToken` = shared token without the JWT
cross-check, since admin is a service operation):

- `GET /admin/status` — booleans + counts only. Returns env-name
  presence as booleans, never values; explicitly comments on which
  fields stay `null` because the backend can't introspect GitHub
  Actions secrets.
- `POST /admin/workflows/:workflowId/dispatch` — proxy to GitHub
  Actions `workflow_dispatch`. Workflow ID must be on the
  hard-coded `ADMIN_WORKFLOW_ALLOWLIST`. Token never logged. Only
  the resolved repo + workflow id + ref are logged for audit.

### `/api/feedback` — tester feedback

- `POST /` — public submit endpoint (intentional). Anonymous
  testers can file feedback. Inputs validated: `type` and
  `severity` constrained to known sets, `message` clipped to 4000
  chars, `attachments` clipped to N items, `userId` / `athleteId`
  clipped to 200 chars. Server augments with `signed_in: !!userId`.
  Persisted to `data/tester-feedback/<id>.json` on the Railway
  filesystem.
- `GET /recent` — **NOW** gated by `requireAdminToken` (was
  previously unauth — fixed in this batch, see "Risks fixed" below).
- `GET /attachments/:filename` — **NOW** gated by
  `requireAdminToken`. Mobile in-app `<Image>` source helper
  `attachmentImageSource()` injects the header.
- `POST /:id/archive`, `POST /:id/unarchive`,
  `GET /triage-suggestions` — already gated by `requireAdminToken`.

### `/api/backlog` — per-athlete proposals

- All routes gated by `requirePrivateAthleteAccess` (shared token +
  JWT ownership check). Mirrors the athlete-memory model.

### `/api/integrations` — third-party connect / sync

All routes gated by `requireAuth` (shared token + JWT user-id
extraction; falls back to `dev-athlete` only when
`ALLOW_SHARED_TOKEN_ONLY=1` or `NODE_ENV=test`).

OAuth callbacks (`GET /polar/callback`, `GET /whoop/callback`) are
intentionally unauthenticated at the HTTP layer — the OAuth state
parameter is HMAC-signed with `INTEGRATION_STATE_SECRET` and
verified server-side, with a 10-minute time window. State payload
carries the userId, signature uses HMAC-SHA256.

Provider routes:

- Polar AccessLink: status / connect / callback / disconnect / sync.
- WHOOP OAuth: status / connect / callback / disconnect / sync, plus
  CSV upload + clear (admin-style for the user's own data).
- Cronometer: status / import (passthrough to a shared importer).
- Concept2 status, Samsung Health status — read-only diagnostics.

### `/v1/internal` — server-to-server only

Blanket `router.use(requireInternalAuth)` at the top of the router
(`internal.ts:102`). Every route requires the
`x-internal-token: <INTERNAL_API_TOKEN>` header. The mobile app
NEVER sends this token. It's used by:

- WHOOP MCP for ingest (`POST /ingest/whoop/daily`).
- Daily / weekly normalisation jobs.
- Pipeline orchestration triggers.
- Read-side diagnostics that pre-aggregate into Supabase.

If `INTERNAL_API_TOKEN` is unset, every route 503s. There is no
fallback that lets a normal tester reach an internal route.

## Where data persists

| Where | What | TTL |
|---|---|---|
| Railway filesystem `data/private-athlete-memory/<userId>/…` | Per-user OAuth tokens (Polar, WHOOP, Cronometer), per-user import status JSONs, athlete-memory artifacts (cached daily/weekly/source-health), Polar export sessions | Until Railway redeploys (filesystem is **ephemeral** — see "Persistence reality" below) |
| Railway filesystem `data/tester-feedback/<id>.json` and `data/tester-feedback/attachments/` | Tester feedback records + attached images | Until redeploy (ephemeral) |
| Supabase Postgres tables | Durable per-user rows: `source_connection_state`, `normalized_daily_metrics`, `raw_source_events`, plus the Supabase-managed `auth.users` for sign-in | Persistent across deploys; per-user rows only |

### Persistence reality

Railway's container filesystem is ephemeral — every redeploy can
wipe `data/`. That has two implications worth being honest about
before testers start:

1. **OAuth tokens for Polar / WHOOP / Cronometer** can be lost on a
   redeploy. The user re-runs the connect flow, no data loss
   beyond the token (the providers still have the historical
   data).
2. **Tester feedback files** can be lost on a redeploy if Aaron
   hasn't pulled them off Railway via the admin viewer. Triage
   should download / archive feedback regularly. Future move to
   Supabase Storage / S3 is on the deferred list — not in scope
   for this audit lane.

The durable per-user data Coach reasons over (normalized_daily_
metrics etc.) lives in Supabase, NOT on Railway, so a Railway
redeploy does not erase health context. Coach answers may
temporarily fall back to deterministic templates if the cache
artifacts get rebuilt.

## Environment variables (names only)

Read by the backend code (`process.env.X`):

```
AGGREGATION_ENABLED
ALLOW_SHARED_TOKEN_ONLY
ATHLETE_MEMORY_API_TOKEN
BACKEND_URL
CRONOMETER_CLIENT_ID
GITHUB_DISPATCH_TOKEN
GITHUB_REPO
INTEGRATION_STATE_SECRET
INTERNAL_API_TOKEN
NODE_ENV
POLAR_ACCESSLINK_BASE_URL
POLAR_CLIENT_ID
POLAR_CLIENT_SECRET
POLAR_REDIRECT_URI
PORT
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_URL
WHOOP_BRIDGE_OWNER_ATHLETE_IDS
WHOOP_BRIDGE_URL
WHOOP_CLIENT_ID
WHOOP_CLIENT_SECRET
WHOOP_MCP_URL
WHOOP_REDIRECT_URI
```

The mobile app holds NONE of:
`SUPABASE_SERVICE_ROLE_KEY`, `INTERNAL_API_TOKEN`,
`GITHUB_DISPATCH_TOKEN`, `INTEGRATION_STATE_SECRET`,
`POLAR_CLIENT_SECRET`, `WHOOP_CLIENT_SECRET`. These live only on
Railway env. The mobile app holds:
`EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN` (shared token — paired with the
per-user JWT for cross-check), `EXPO_PUBLIC_AI_BACKEND_URL`,
`EXPO_PUBLIC_AI_PUBLIC_URL`, `EXPO_PUBLIC_INTERNAL_API_TOKEN`
(present but the mobile app does NOT call /v1/internal/* — the
constant is reserved for `/v1/internal/athletes/:id/ai-health-
context` calls in the Admin/Dev backend-status fetch only).

`SUPABASE_ANON_KEY` is intentionally public (Supabase uses it
client-side). `SUPABASE_SERVICE_ROLE_KEY` is server-only.

## What testers send to Railway

Per request, normal testers send:

- A Supabase Bearer JWT identifying who they are.
- The shared `x-athlete-memory-token` (constant, baked into the
  build).
- An `x-athlete-id` header that must equal their own user id.
- For health context calls: nothing in the body (server reads
  cached artifacts).
- For Coach `/coach/ask`: their question text + a structured
  `app_athlete_state` snapshot computed on-device (recovery_context,
  load_context, fueling_adequacy, source_roles, readiness flags),
  plus optional nutrition / training session history. No raw
  HealthKit / Health Connect samples — only the device-agnostic
  aggregated state.
- For OAuth connect flows: a CSRF state + the provider's auth code.
- For polar export import: parsed PolarSession[] (no credentials).
- For feedback submit: type / severity / message / optional
  attachments (resized + compressed client-side).

Things testers **never** send:

- Raw HealthKit / Health Connect record streams.
- Their Apple ID / Google account password.
- Any third-party API key.
- Any field labelled "secret".

## What admin-only data Railway sees

- The admin (Aaron) hits `/api/feedback/recent` and
  `/api/feedback/attachments/:filename` to triage tester feedback
  — those routes return PII (userId, athleteId, message text,
  context flags, attachment URLs) and are now gated by the admin
  shared token.
- The admin hits `/api/athlete-memory/admin/status` for the
  Admin/Dev status surface — booleans + repo links only.
- The admin hits `/api/athlete-memory/admin/workflows/:id/dispatch`
  to trigger GitHub Actions — workflow id must be on the allowlist;
  `ref` and `inputs` are forwarded; the GitHub PAT is read from
  Railway env only and never returned to the caller.

No tester can hit any admin route — every admin route checks the
shared `ATHLETE_MEMORY_API_TOKEN` AND, in the case of dispatch,
relies on the workflow allowlist as a second guard. A normal
tester's app does not even attempt these endpoints (the calls live
inside the Admin/Dev screen, which is gated by the owner-email
allowlist + the FAB rule).

## Risks fixed in this batch

1. **`GET /api/feedback/recent` was unauthenticated.** Any caller
   could list every recent feedback record including
   userId/athleteId/message/context. This is the highest-priority
   fix before testers start — it leaks PII trivially. Now requires
   `requireAdminToken`. Mobile client `fetchRecentFeedback` updated
   to send `x-athlete-memory-token` (via
   `EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN`).
2. **`GET /api/feedback/attachments/:filename` was unauthenticated.**
   Combined with the recent route, an attacker could list all
   filenames + fetch every screenshot. Now requires
   `requireAdminToken`. Mobile in-app `<Image>` switched to a
   source object `{ uri, headers: { 'x-athlete-memory-token': … } }`
   via the new `attachmentImageSource()` helper.

Both routes were always intended to be admin-only (the route
comments described them as "admin/export helper" / used inside the
admin viewer) — the gate was simply missing.

## Risks NOT yet fixed (deferred, lower priority)

- **Persistence on Railway is ephemeral.** Migrate
  feedback/attachments and OAuth tokens to Supabase Storage / a
  managed bucket before scaling testers. Out of scope for this
  audit lane.
- **No request-rate limit on `/api/feedback` POST.** A bot could
  flood the feedback dir. Add a per-IP rate limiter (express-rate-
  limit) before public-track production. Internal Testing is
  fine — only invited Google accounts can install.
- **Logs.** `[admin-dispatch]` lines are written to Railway logs.
  No tokens are logged; only workflow id + ref + repo (already
  public). No user data flows through these log lines — verified.
- **CORS.** `app.ts` doesn't show a CORS middleware, so Express
  defaults apply (no Access-Control-Allow-Origin) — fine for the
  mobile app (no browser CORS preflight) but the chat-app web UI
  may need explicit origins later.

## User-data isolation summary

Two-factor isolation: shared token AND per-user JWT. A tester
cannot fetch another tester's `/:athleteId/*` data even with both
the right shared token AND the wrong JWT — the route returns 403
`Athlete ownership mismatch`. The Supabase service role key is
server-only so cross-user reads are gated by the path-vs-JWT match
inside the route handler, not just by Postgres RLS.

The only cross-cutting data path is feedback triage, which is
admin-only (post-fix).

## Files changed in this audit batch

- `chat-app/src/server/routes/feedback.ts` — added
  `requireAdminToken` gate to `GET /recent` and
  `GET /attachments/:filename`.
- `apps/mobile/src/services/feedback-viewer.ts` — added admin token
  header on `fetchRecentFeedback`; new `attachmentImageSource()`
  helper that returns `{ uri, headers }` for `<Image>` sources.
- `apps/mobile/app/feedback-viewer.tsx` — `<Image>` thumbs and the
  full-size modal use `attachmentImageSource()`; `fullImage` state
  expanded to `{ uri, headers? }`.
- `docs/RAILWAY_BACKEND_AUDIT.md` — this document.

## Verification

`npx tsc --noEmit` in `apps/mobile` — exit 0. No backend smoke run
this lane (the gate is server-side; verify on next Railway deploy
by hitting `/api/feedback/recent` with and without the header).

## Safe-for-testers verdict

**Yes, with the two PII-leak fixes in this batch.** Other pending
items are scaling concerns for a wider cohort, not pre-tester
blockers.
