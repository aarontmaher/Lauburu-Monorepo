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
