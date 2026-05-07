# Mobile native control-centre — TestFlight-safe automation spec

The doc that makes Lauburu's MCP control-centre + safe automation
controls reachable from the **installed iPhone TestFlight app** (and
the equivalent Play Internal Android build), without shipping any
admin token / Supabase service-role key / MCP shared secret in the
app bundle. Updated 2026-05-08 against the
NATIVE-IPHONE-TESTFLIGHT-AUTOMATION-CONTROLS top-priority directive.

This is **spec only**. No mobile UI implementation, no Worker code
change, no migration applies. Implementation lands per FS-019
(registered below) gated by Aaron approval per rule 7.

## 0. The "Don't repeat WhatsApp Web" framing

Aaron's existing local Expo dev path works because `EXPO_PUBLIC_*`
env vars from `.env.local` are loaded into the JS bundle Metro
serves — including `EXPO_PUBLIC_MCP_BASE_URL` and (until this spec
ships) `EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN`. Same JS bundle in a
TestFlight / Play Internal install means the same baked-in env
vars are extractable from the installed IPA / APK by anyone with
basic reverse-engineering. **Any secret in `EXPO_PUBLIC_*` is
public.**

The current state:
1. The MCP shared admin token is **already in
   `apps/mobile/.env.production`** and would ship into the next
   EAS production / TestFlight build. (`.env.production` is
   gitignored, so the secret isn't in repo history; but it IS in
   the working tree and bakes into the bundle on build.)
2. The next safe action — independent of this spec — is to
   **rotate the admin token** since it has been visible in this
   session's Bash output and possibly chat history. This is
   Aaron's manual step listed below. Do NOT defer this on the
   spec.

## 1. Threat model

What we are protecting:

| Asset | Damage if leaked |
|---|---|
| `ATHLETE_MEMORY_API_TOKEN` (Worker shared admin bearer) | full read of every admin tool / `/api/control_centre`; ability to write `project.update_work_status` for any agent; ability to read full handoff / build / coder lane payloads |
| `SUPABASE_SERVICE_ROLE_KEY` | bypasses every RLS policy in the Supabase project; full read/write of every user's journal / health / training data; full destructive access to connector_* tables |
| WHOOP / Polar / vendor secrets | per-vendor account compromise; cross-user data flow if anything is shared |
| Aaron's Apple ID / Google Play / Cloudflare creds | full account compromise; out-of-scope for this spec but listed for completeness |

What is acceptable to expose to a TestFlight binary:

| Asset | Damage if leaked |
|---|---|
| `EXPO_PUBLIC_MCP_BASE_URL` | the URL of a public-safe MCP endpoint that already serves `tools/list` to any No-Auth caller; **safe to ship** |
| Public Supabase anon key | per-user RLS still applies; anon key only allows public-policy rows; **safe to ship** by Supabase design |
| Public-safe tool names + their schemas | already returned by `tools/list` from any caller; **safe to ship** |

## 2. Three-tier access surface

Every MCP / `/api/*` consumer the mobile app talks to falls into
one of three tiers. The tier determines auth, the auth
determines what data is visible.

### Tier 1 — Public-safe MCP tools (No Auth, ship freely)

What the mobile app calls today (and may call from TestFlight
unchanged):

- `project.get_current_state` — composed priority/blocker/next
  + per-lane sanitised summary + freshness signal
- `project.get_overview` — cross-project aggregates
- `project.get_work_status` — sanitised work status
- `project.list_priorities` — top backlog item only
- `project.get_operating_rules` — the 14 rules
- `mobile.get_lane_overview` / `mobile.get_build_overview` /
  `mobile.get_repo_overview` — counts/aggregates only
- `handoff.get_latest` — composed handoff feed
- `integrations.get_overview` — per-platform exposure flags

These are the **default** mobile-control-centre reads. Live /
stale / fallback labels render directly from the `freshness`
envelope these tools return (per
`docs/HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md` § 1.1 format
adapted for MCP context: "MCP fresh", "MCP stale (24 min ago)",
"MCP unreachable").

**TestFlight requirement**: `EXPO_PUBLIC_MCP_BASE_URL` must be in
`eas.json` under the production / preview build profiles' `env`
section. Today it is missing — see § 5.

### Tier 2 — Per-user authenticated reads (Supabase JWT, ship-safe)

The user signs in to the Lauburu app (existing flow via
`apps/mobile/src/store/auth-store.ts` → Supabase Auth). The
Supabase session JWT is then sent on each MCP call as
`Authorization: Bearer <supabase-session-jwt>`. The Worker
validates the JWT against Supabase's JWKS and returns whatever
data RLS policies allow for that user.

What this unlocks per user (without shipping any shared token):

- Per-user journal items / events / dose periods / metric-effect
  windows (FS-018 schema; RLS already enforces `auth.uid() =
  user_id`).
- Per-user nutrition / health-source rows.
- Per-user prompt-job approval records (proposed below in § 4).

What this does NOT unlock:

- Cross-user reads.
- The shared admin-only feeds (see Tier 3).

### Tier 3 — Admin-equivalent reads (JWT + email allowlist)

Aaron's specific need: see Claude / Codex lane state, build
status, control-centre snapshot from the iPhone app. Today this
is gated behind the shared `ATHLETE_MEMORY_API_TOKEN`. **The fix
is to gate it behind Aaron's authenticated identity instead.**

Architecture:

1. App sends `Authorization: Bearer <supabase-session-jwt>`.
2. Worker validates the JWT (signature + not expired + matches
   Supabase project audience).
3. Worker extracts the user's email from the JWT claims.
4. Worker matches against the existing `isAdminEmail`
   allowlist (currently used in `apps/mobile/app/admin-dev.tsx`
   and Settings — same hardcoded source of truth).
5. If allowlisted, Worker returns admin-equivalent reads:
   `mobile.get_control_centre`, `mobile.get_coder_lanes`,
   `mobile.get_work_status` (full payload), etc.
6. If not allowlisted, Worker returns the same `adminGateError`
   it returns today for missing-token requests.

**Critical**: the email allowlist becomes the single source of
truth for "admin" across mobile + Worker. The mobile app's
existing `isAdminEmail` check then matches the Worker's check
exactly. Adding / removing an admin is a **doc-and-code commit**
to the allowlist constant in both places (paired update, contract
test like operating-rules), never a runtime DB row that someone
could insert into.

**Important constraint**: this auth path replaces the shared-
token admin gate for the mobile app surface. It does NOT replace
laptop-side admin reads (curl from terminal during dev) — those
still use `x-athlete-memory-token` because Aaron's terminal isn't
signed in to Supabase. Both paths coexist.

## 3. Live / stale / fallback labelling

Required user-visible chip on every MCP-bound card in the native
control-centre, mirroring
`docs/HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md` § 1 format:

| Source state | Chip text |
|---|---|
| `freshness.staleReason: 'fresh'` and tool returned data | **live** |
| `freshness.staleReason: 'no_writeback'` (row > 10 min old) | **stale (last update {n} min ago)** |
| `freshness.staleReason: 'env_missing'` | **MCP not configured** |
| Network error / Worker unreachable | **MCP offline — last known: {n} min ago** |
| User not signed in (Tier 2 / Tier 3 attempted) | **sign in to see this** |
| Email not allowlisted (Tier 3 attempted) | **(card hidden — viewer not admin)** |

Every chip shows the relative timestamp. Empty caches surface
"MCP offline — no cache" rather than blank rows. Anti-rule: never
show numeric data without a freshness chip.

## 4. Safe write actions — small allowlist

Mobile native control-centre supports a **strictly bounded** set
of write actions. Each is per-user-scoped, idempotent, and
reversible. All ride the JWT auth path; **no write action ever
uses the shared admin token from the app**.

| Action | What it writes | Auth | Notes |
|---|---|---|---|
| **Approve FS-XXX** | inserts a row into `connector_backlog_approvals` (`(actor_email, fs_id, approved_at)`) — the Worker reads this on `project.list_priorities` to mark the candidate `(approved by Aaron at …)` | JWT + email allowlist | rule 5 / rule 7 — Aaron's tap from phone replaces the manual `FEEDBACK_SUGGESTIONS.md` line; coder watches the row and lands the doc commit |
| **Defer FS-XXX** | inserts a row into the same table with `status: 'deferred'` | JWT + email allowlist | reversible — re-approve flips status back to `approved` |
| **Approve EAS build (rule 7)** | sets `connector_build_approvals` row keyed by current build batch | JWT + email allowlist | rule 7 — replaces the laptop-side manual approval; coder dispatch script watches the row |
| **Mark health-source `approved_done`** | journal-style row in `connector_health_source_promotions` | JWT + email allowlist + must reference the FS-XXX it promotes | rule 8 — Aaron's "I tested this on my phone" confirmation flows here |
| **Promote suggestion to backlog** (FS-XXX intake) | inserts a row in `connector_backlog_intake` with `(actor_user_id, title, details, source: 'mobile')` | JWT (any signed-in user) | available to non-admins; intake-only; Aaron / Agent reviews before promotion |
| **Acknowledge a manual step** | flips `connector_manual_steps.row.acknowledged_at` for a step assigned to the current user | JWT + step ownership match | per-user; never cross-user |

What is **NEVER** in the mobile native control-centre allowlist:

- `wrangler deploy` (Worker / production deploys)
- `git push --force` / `git reset --hard` / branch deletion
- EAS build dispatch (rule 7 — Aaron approves the build, the
  laptop-side coder runs the actual build command per
  `docs/CODER_LAPTOP_COMMANDS.md` § 4)
- Any direct Supabase migration apply
- Any MCP write tool that touches non-Aaron user data
- Any vendor-secret rotation (rule 12 § 5 — Aaron-only)
- Token rotation
- Health-source truth-label promotions without a paired Agent
  audit

The phone is a **decision surface, not an execution surface**.
Approvals flow phone → Supabase row → coder script picks up the
row and runs the laptop command. The phone never directly
triggers a destructive operation.

## 5. EAS build env strategy

`eas.json` profiles (`development`, `preview`, `production`)
must be updated to include the public MCP env. Service-role and
admin-token vars must NOT be added.

### 5.1 Add to every build profile's `env` section

```json
{
  "build": {
    "preview": {
      "env": {
        "EXPO_PUBLIC_MCP_BASE_URL": "https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/v2",
        "EXPO_PUBLIC_AI_BACKEND_URL": "...",
        "EXPO_PUBLIC_AI_PUBLIC_URL": "...",
        "EXPO_PUBLIC_ATHLETE_ID": "dev-athlete",
        "EXPO_PUBLIC_WHOOP_BRIDGE_OWNER_IDS": "..."
      }
    },
    "production": {
      "env": {
        "EXPO_PUBLIC_MCP_BASE_URL": "https://lauburu-mcp.lauburu-aaron.workers.dev/mcp/v2",
        "...": "..."
      }
    }
  }
}
```

The production env points at the prod-environment Worker URL
(`lauburu-mcp.lauburu-aaron.workers.dev` per the deploy that
landed earlier this session, version `6fa09079-7cc5-4014-9db3-c06263900b07`).
Preview builds point at `lauburu-mcp-preview.lauburu-aaron.workers.dev`.

### 5.2 Remove from every build profile's `env` section

The current production `.env.production` ships
`EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN`. After this spec ships:

- The token MUST NOT appear in any `eas.json` `env` block.
- The token MUST NOT appear in any `.env.*` file that the build
  pipeline reads.
- The token MUST be rotated in Supabase / Worker before the next
  EAS build.
- The mobile app's admin-dev surface stops sending the token; it
  sends the Supabase JWT instead.

### 5.3 Migration sequence

1. Aaron rotates the existing `ATHLETE_MEMORY_API_TOKEN` (rule
   12 § 5 — Aaron-only step). New token goes into the Worker
   only via `wrangler secret put ATHLETE_MEMORY_API_TOKEN --env
   preview` and `--env production`.
2. Coder removes `EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN` from
   `apps/mobile/.env.production` + `.env.local` (Aaron deletes
   the local file's line; coder removes any code path that
   reads it).
3. Coder updates `eas.json` per § 5.1.
4. Coder ships the JWT-validation route in the Worker per § 6.
5. Coder updates `mcp-v2-client.ts` to send the Supabase JWT
   instead of the static token.
6. Tester build dispatched (Aaron approval per rule 7).
7. Aaron tests on TestFlight.

Each step is its own commit / its own approval gate.

## 6. Worker JWT validation — implementation outline

Outline only; full code in the FS-019 implementation batch.

### 6.1 New auth helper

`cloudflare-worker/src/supabase-jwt.ts` (NEW):

- `validateSupabaseJwt(jwt: string, env: Env): Promise<{ ok: true, userId: string, email: string } | { ok: false, reason: string }>`
- Verifies signature against Supabase project JWKS (URL is
  `<SUPABASE_URL>/auth/v1/.well-known/jwks.json`). JWKS is
  cached for 1 hour in Worker memory.
- Validates `iss` matches `<SUPABASE_URL>/auth/v1`, `aud` is
  `'authenticated'`, `exp > now()`.
- Returns `userId` (UUID) + `email` claims for the caller.

### 6.2 New helper

`cloudflare-worker/src/admin-allowlist.ts` (NEW):

```ts
export const ADMIN_EMAILS: readonly string[] = [
  // Single source of truth — mirrors apps/mobile's isAdminEmail
  // hardcoded list. Editing this constant requires a paired edit
  // to apps/mobile/src/services/admin-allowlist.ts in the same
  // commit; contract test asserts the two stay in sync.
];

export function isAdminEmail(email: string | null | undefined): boolean {
  if (!email) return false;
  return ADMIN_EMAILS.includes(email.toLowerCase());
}
```

### 6.3 Updated tokenAuthorised in mcp-v2.ts

Existing `tokenAuthorised(request, env)` keeps the shared-bearer
path for laptop curl. New parallel
`async function userAdminAuthorised(request, env): Promise<{
  ok: boolean; email?: string; userId?: string; reason?: string;
}>` validates the Supabase JWT and the email allowlist.

Admin tool dispatch becomes:

```ts
if (tool.auth === 'admin') {
  // Path A: laptop / curl with shared token
  if (tokenAuthorised(request, env)) { /* allow */ }
  // Path B: mobile app with Supabase JWT + admin-allowlisted email
  else if ((await userAdminAuthorised(request, env)).ok) { /* allow */ }
  else return adminGateError();
}
```

### 6.4 Contract test

`cloudflare-worker/test/test-admin-allowlist.ts` (NEW):

- Asserts `ADMIN_EMAILS.length` is small (≤5).
- Asserts the same emails appear in
  `apps/mobile/src/services/admin-allowlist.ts` (read via
  fs.readFileSync at test time).
- Drift between the two surfaces fails the contract test (rule
  similar to operating-rules drift detection).

## 7. Admin gating in the mobile app

Existing `isAdminEmail(user.email)` check in
`apps/mobile/app/admin-dev.tsx` already gates the screen. After
this spec ships:

1. The same allowlist constant is exported from
   `apps/mobile/src/services/admin-allowlist.ts` (NEW; mirrors
   the Worker constant).
2. `mcp-v2-client.ts` reads `useAuthStore` for the current
   Supabase session and attaches `Authorization: Bearer <jwt>`
   on every Tier-2 / Tier-3 request.
3. If the user signs out, every cached MCP read disappears from
   the UI; the chip flips to "sign in to see this".
4. If the user is signed in but not allowlisted, Tier-3 cards
   are hidden (not rendered with a "blocked" state — that
   leaks the existence of admin surfaces). Tier-1 + Tier-2
   surfaces remain available.

## 8. FS candidate

| Field | Value |
|---|---|
| FS ID | FS-019 |
| Title | Native iPhone TestFlight automation: per-user JWT MCP auth + email allowlist + EAS env strategy + safe-write allowlist |
| Status | candidate, awaiting Aaron approval |
| Lane | 3 (DB schema + Worker auth + secret rotation + mobile UI) |
| Spec home | `docs/MOBILE_NATIVE_CONTROL_CENTRE_SPEC.md` (this doc) |
| Roadmap rank | top priority — supersedes P1+P2 mobile home work for the duration of this spec's implementation per Aaron's directive |

Sub-batches (each its own commit):

- **B-19a (Aaron-only, no code)**: rotate
  `ATHLETE_MEMORY_API_TOKEN` via `wrangler secret put` in
  preview + production envs. Update local `.env.local` /
  `.env.production` to remove the public-bundled copy.
- **B-19b**: Worker — `supabase-jwt.ts` + `admin-allowlist.ts` +
  contract test + dual-auth path in `mcp-v2.ts`.
- **B-19c**: Mobile — `admin-allowlist.ts` mirror + `mcp-v2-client.ts`
  JWT attach + remove static-token reads. NO UI redesign.
- **B-19d**: `eas.json` env updates per § 5.1 / § 5.2.
- **B-19e**: New `connector_backlog_approvals` table (Supabase
  migration; RLS-gated by `auth.uid() = actor_user_id` for
  inserts; admin-allowlist-gated for reads).
- **B-19f**: Mobile UI — wire approve / defer FS-XXX taps in
  Admin/Dev surface using the new write tools. Per § 4
  allowlist only.
- **B-19g**: Tester build (Aaron approves per rule 7).

## 9. Codex handoff

Drop-in for the next batch when Aaron approves FS-019. Single
prompt covers B-19b + B-19c so worker auth + mobile client land
together; the rest follow once that pair is Agent-confirmed.

```
PROMPT-ID: CODEX-FS019-NATIVE-MCP-JWT-AUTH-01
TYPE: CODEX
LANE: Worker auth + mobile client (FS-019 B-19b + B-19c)

MCP-FIRST: call project.get_current_state. Bridge → Supabase
direct upsert is live; bridge:snapshot for end-of-task cadence
per rule 12.

Reference docs (read first):
- docs/MOBILE_NATIVE_CONTROL_CENTRE_SPEC.md (this doc) —
  threat model + three-tier surface + auth model.
- docs/UNIFIED_MCP_PLAN.md § 15 — write/read contract; the
  new JWT path adds an alternate admin auth, NOT a new write
  surface.
- docs/CODER_LAPTOP_COMMANDS.md — curl-from-terminal stays on
  the shared-bearer path.

Phase 1 scope (this batch): B-19b + B-19c paired commits.

B-19b — Worker:
1. cloudflare-worker/src/supabase-jwt.ts (NEW) — see § 6.1.
2. cloudflare-worker/src/admin-allowlist.ts (NEW) — see § 6.2.
3. cloudflare-worker/src/mcp-v2.ts — add userAdminAuthorised
   path; admin tool dispatch tries shared-token first, JWT
   second, returns adminGateError if both fail.
4. cloudflare-worker/test/test-admin-allowlist.ts (NEW) —
   contract test asserting ≤5 emails + drift detection vs
   apps/mobile mirror.
5. NO change to existing tools' shapes. Public-safe tools
   stay No-Auth.

B-19c — Mobile:
1. apps/mobile/src/services/admin-allowlist.ts (NEW) —
   mirrors the Worker constant.
2. apps/mobile/src/services/mcp-v2-client.ts (UPDATE) —
   attach Authorization: Bearer <supabase-session-jwt> on
   every Tier-2 / Tier-3 call. Read JWT from useAuthStore.
3. Remove all reads of EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN from
   the mobile codebase.
4. NO React UI redesign in this batch. Existing admin-dev.tsx
   keeps its layout; only the network layer changes.

Anti-rules (verbatim):
- No EAS build.
- No app version/build bump.
- No new write tools (B-19e/f land separately).
- No exposing the new path in public-safe tools.
- No removing the shared-bearer path (laptop curl still
  needs it).
- Don't ship until B-19a (Aaron's token rotation) is
  confirmed.

Status report opens with:
- rule-12 three-field block
- rule-13 three-section split
- rule-14 parallel-priority freshness notes

Output:
- changed files (worker + mobile only; NO eas.json / migrations)
- four-status compliance per FS-019
- recommendation for B-19d (eas.json) + B-19e (approvals
  table) timing
- explicit no-EAS-build statement
- commit SHA
```

## 10. Anti-rules (umbrella)

- **No `EXPO_PUBLIC_*` secrets.** The "public" prefix is the
  contract: anything under it ships in plaintext to every
  installed binary. Admin tokens, service-role keys, and vendor
  secrets MUST live behind `EXPO_PUBLIC_*` is forbidden.
- **No JWT in JS bundle.** The Supabase session JWT lives at
  runtime per signed-in user; it is NOT baked in. The Worker
  must validate every request.
- **No backdoor / admin-override.** No "if email matches
  Aaron's, skip JWT validation" path. The JWT MUST be valid AND
  the email MUST match the allowlist for Tier-3 access.
- **No silent rule edits to ADMIN_EMAILS.** Adding a new
  allowlisted email is a paired commit (Worker + mobile +
  contract test) reviewed by Aaron; never a runtime DB row.
- **No write actions outside the § 4 allowlist.** A new safe
  action requires a doc commit + Aaron approval per rule 7.
- **No exposing the existence of admin surfaces to non-admins.**
  Tier-3 cards are absent (not "blocked") for non-allowlisted
  signed-in users.
- **No rotation deferral.** The existing
  `ATHLETE_MEMORY_API_TOKEN` is exposed as of this session.
  Rotate it before any further EAS build — even if FS-019
  takes weeks.
- **No tearing down the laptop curl path.** Admin curl from
  Aaron's laptop continues to use `x-athlete-memory-token`;
  removing that breaks rule 12 cadence + bridge:snapshot
  fallback.

## 11. Cross-references

- `docs/UNIFIED_MCP_PLAN.md` § 15 — write/read contract; this
  spec's Tier-3 path is an alternate admin auth, not a new
  write surface.
- `docs/CODER_LAPTOP_COMMANDS.md` — laptop curl path stays
  shared-bearer.
- `docs/PHONE_ONLY_AUTOMATION_PLAN.md` § 5 — Aaron's seven
  irreducible manual steps; § 4 of this spec specifies which
  of those Aaron can now do FROM HIS PHONE via TestFlight.
- `docs/HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md` § 1 —
  freshness label format reused for live/stale/fallback chip
  in the mobile control-centre.
- `docs/CHATGPT_CONNECTOR_SETUP.md` — ChatGPT connector path
  unchanged; ChatGPT continues to use the public `/mcp/v2`
  surface (Tier 1 only); admin reads from chat are not in
  scope for this spec.
- `docs/MCP_PHONE_CONTROL_CENTRE.md` — phone-side runbook;
  this spec is the architectural design that
  MCP_PHONE_CONTROL_CENTRE references for the auth model.
- `docs/CONNECTOR_SECURITY_MODEL.md` — invariants this spec
  honours.
- `docs/FEEDBACK_SUGGESTIONS.md` FS-019 (registered by this
  commit).
