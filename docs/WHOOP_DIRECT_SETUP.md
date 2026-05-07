# WHOOP Direct — Per-User OAuth Setup

Backend is ready. Only blocker: three env vars on Railway + a WHOOP developer app with the right redirect URI.

No Aaron-WHOOP fallback for other users — each user links their own WHOOP account, and tokens are scoped by Supabase `userId`.

## What to register on WHOOP

1. Go to https://developer.whoop.com/ → apply for API access (usually approved within a day).
2. Create an **OAuth Application** with these settings:
   - **Name:** Lauburu Grappling Map
   - **Redirect URI** *(must match exactly — one line, no spaces):*
     ```
     https://lauburu-ai-backend-production.up.railway.app/api/integrations/whoop/callback
     ```
   - **Scopes:** `read:recovery read:cycles read:sleep read:workout read:profile read:body_measurement`
3. Note the Client ID and Client Secret.

## What to set on Railway

Project: `lauburu-ai-backend` → Environment: `production` → Variables.

Set three variables:

| Name | Value |
| --- | --- |
| `WHOOP_CLIENT_ID` | *(from WHOOP developer dashboard)* |
| `WHOOP_CLIENT_SECRET` | *(from WHOOP developer dashboard)* |
| `WHOOP_REDIRECT_URI` | `https://lauburu-ai-backend-production.up.railway.app/api/integrations/whoop/callback` |

Trigger a redeploy after saving (Railway auto-redeploys on env change).

## How to verify end-to-end

1. In the mobile app, open **Health** → **WHOOP Direct** card.
2. Status pill should change from `Setup required` to `Not connected`.
3. Tap **Connect WHOOP** → Safari opens WHOOP auth page → sign in → approve → returns to backend → "WHOOP connected" confirmation page → return to Lauburu.
4. Back on the WHOOP Direct card, tap **Sync now**.
5. Status pill flips to `Connected`; the WHOOP card at the top of Health shows today's recovery, HRV, resting HR, strain, sleep.
6. Ask Coach: "Is WHOOP connected?" → should reference WHOOP as a direct source.
7. Ask Coach: "Can you assess readiness today?" → direct-readiness path unlocks because the current user's WHOOP fields are fresh.

## Security invariants (do not change)

- Tokens are stored per-user at `data/private-athlete-memory/<userId>/integrations/whoop_token.json`. No shared storage.
- OAuth `state` is HMAC-signed with `INTEGRATION_STATE_SECRET` and expires in 10 minutes — cross-user callback abuse impossible.
- `requireAuth` middleware enforces Supabase JWT → `userId` extraction. No way for user B to read user A's WHOOP token.
- Readiness unlock is gated on **the current user's** fresh WHOOP record — stale/missing direct WHOOP = downgraded to contextual only.
- Apple Health, Health Connect, Samsung Health remain **contextual only**. They never unlock direct readiness.

## If connect fails

- **Callback error 403 "Invalid or expired OAuth state"** → user took longer than 10 min between tap Connect and approval. Tap Connect again, complete quickly.
- **Callback error 502 "WHOOP token exchange failed"** → redirect URI mismatch between Railway env and WHOOP developer console. They must match byte-for-byte.
- **Status stays `config_missing` after env set** → env var not picked up by Railway worker. Force a redeploy from the Railway dashboard.

## Observability

- `GET /api/integrations/whoop/status` (authed) — shows the current user's status.
- Normalized daily metrics land under `data/private-athlete-memory/<userId>/ai_state/normalized_days/` with `provider: whoop_direct` or `mixed`.
- Raw WHOOP payloads land under `data/private-athlete-memory/<userId>/integrations/whoop_data/`.

## Migration plan — Railway → Cloudflare Worker

Updated 2026-05-07 against `CLAUDE-MCP-UNIFICATION-SPEC-04`.

The Railway backend is being deprecated. The WHOOP OAuth
callback + token storage moves to the Cloudflare Worker
already serving `/mcp/v2` and `/api/control_centre`. This is
FS-008 in `docs/FEEDBACK_SUGGESTIONS.md`. **Status: BLOCKED on
Aaron approval.** Until approved, this plan is
documentation-only; no code lands.

### M.1 Target architecture

| Concern | Today (Railway) | After migration (Cloudflare) |
|---|---|---|
| OAuth callback URL | `https://lauburu-ai-backend-production.up.railway.app/api/integrations/whoop/callback` | `https://lauburu-mcp-preview.lauburu-aaron.workers.dev/api/integrations/whoop/callback` (or a custom domain if Aaron prefers) |
| Client ID / secret storage | Railway env vars | `wrangler secret put WHOOP_CLIENT_ID` + `WHOOP_CLIENT_SECRET` |
| State HMAC secret | `INTEGRATION_STATE_SECRET` Railway env | `wrangler secret put INTEGRATION_STATE_SECRET` |
| User token storage | filesystem `data/private-athlete-memory/<userId>/integrations/whoop_token.json` | Supabase row in new `whoop_tokens` table, encrypted at rest, RLS-gated by `auth.uid() = user_id` |
| Token refresh job | Railway cron | Cloudflare Worker scheduled trigger (`cron: "*/30 * * * *"`) |
| Status read | `GET /api/integrations/whoop/status` Railway | `GET /api/integrations/whoop/status` Cloudflare (same path, same JSON shape — mobile app does not change) |
| Webhook receiver | Railway `POST /api/integrations/whoop/webhook` | Cloudflare `POST /api/integrations/whoop/webhook` (same shape) |

### M.2 Migration steps (in order; each step is a separate gate)

1. **Aaron approval (FS-008).** Required before step 2.
2. **Supabase migration** — new `whoop_tokens` table:
   ```sql
   create table public.whoop_tokens (
     user_id uuid primary key references auth.users(id) on delete cascade,
     access_token text not null,         -- encrypted via pgcrypto
     refresh_token text not null,        -- encrypted via pgcrypto
     scope text not null,
     expires_at timestamptz not null,
     created_at timestamptz not null default now(),
     updated_at timestamptz not null default now()
   );
   alter table public.whoop_tokens enable row level security;
   create policy whoop_tokens_self_read on public.whoop_tokens
     for select using (auth.uid() = user_id);
   create policy whoop_tokens_self_write on public.whoop_tokens
     for insert with check (auth.uid() = user_id);
   create policy whoop_tokens_self_update on public.whoop_tokens
     for update using (auth.uid() = user_id);
   ```
   Tokens encrypted with `pgcrypto` against a key stored in
   `wrangler secret put WHOOP_TOKEN_ENC_KEY`. Plaintext access
   tokens never leave the Worker.
3. **Worker route**: add `POST /api/integrations/whoop/callback`
   to `cloudflare-worker/src/worker.ts`. Mirrors the Railway
   handler: validate HMAC `state`, exchange code → tokens,
   encrypt + upsert into `whoop_tokens`. No log line includes
   the raw token.
4. **WHOOP developer-console update** (Aaron's hands): change
   the redirect URI to the new Cloudflare URL. Old URI stays
   listed for the cutover window.
5. **Token refresh job**: Cloudflare scheduled worker fires
   every 30 min, refreshes tokens whose `expires_at` is within
   2 hours, swaps in the new pair atomically.
6. **Cutover window**: both Railway + Cloudflare callbacks live
   for 7 days. New users land on Cloudflare; existing users
   keep their Railway-issued tokens until next refresh moves
   them to Supabase. After 7 days clean, Railway WHOOP routes
   are deleted.
7. **Truth-label promotion**: see § M.3.

### M.3 Truth-label progression during the migration

| Phase | Truth label | Confidence ceiling |
|---|---|---|
| Pre-migration (today) | `setup required` | NOT eligible for direct readiness |
| Day 0 — migration ships | `seed/provisional` | `confidence: low` |
| Day 1–7 post-migration | `seed/provisional` | `confidence: low` only |
| Day 7+ if all four conditions hold | `live` | `confidence: medium` (never `high` until Aaron-approved doc commit) |

The four conditions for `seed/provisional` → `live` (also at
`HEALTH_NUTRITION_READINESS_AUDIT.md` § 1.4.d):
1. ≥7 calendar days of clean token flow (no auth drops, no
   rate-limit errors, no shape mismatches in webhook).
2. At least one daily reading per day for recovery + sleep +
   strain.
3. Aaron's tester-device confirmation that the readings match
   his subjective experience.
4. Explicit `approved_done` line in
   `docs/FEEDBACK_SUGGESTIONS.md` against FS-008.

### M.4 Rollback

If anything in steps 3–6 misbehaves:
- Worker route can be removed in a single redeploy; existing
  `whoop_tokens` rows are kept (cheap to re-use).
- Railway WHOOP routes stay live during the 7-day window
  precisely so rollback is one config flip on the WHOOP
  developer console.
- `whoop_tokens` table stays around as a Supabase artefact
  even on rollback — no destructive drop.

### M.5 Anti-rules

- **Do not paste the WHOOP client secret into any commit, log,
  doc, or app UI.** It enters the Worker only via
  `wrangler secret put`.
- **Do not rotate the redirect URI without Aaron**. Even
  during the cutover, the WHOOP developer console must list
  the new URI before any user-facing connect button points at
  it.
- **Do not move the truth label to `live`** before § M.3
  conditions hold. The 7-day window exists specifically to
  catch issues that only surface after sustained token use.
- **Do not promote per-user readings to `confidence: high`**
  via this migration. That ceiling is reserved.
