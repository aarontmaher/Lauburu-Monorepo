# Cloudflare migration — runbook

How the Lauburu MCP / app-dev-centre layer moves off Railway
dependency onto Cloudflare Workers + Supabase, without breaking
the current mobile app, the in-app Admin/Dev surface, the
website, or any deployed behaviour.

Companion to `RAILWAY_BACKEND_AUDIT.md` (current routes inventory),
`RAILWAY_CONNECTOR_TOOLS.md` (connector curl examples),
`CONNECTOR_SECURITY_MODEL.md` (invariants), and
`GRAPPLINGMAP_MCP_BRIDGE_PLAN.md` (5-stage build-out).

Updated 2026-05-06.

## 1. Why move

Railway billing requires a credit card; Aaron has a debit card.
The blocker is operational, not architectural. Cloudflare Workers
have a generous free tier and accept debit-only billing for paid
plans when usage grows. Moving the public MCP / app-dev-centre
control layer to Workers keeps the project shippable without a
Railway billing dependency.

The mobile app, the existing Express backend, the website, and
the connector tools all keep working on Railway during the
migration — Cloudflare deployment is additive, not a swap.

## 2. What stays on Supabase

- Auth (`auth.users`, JWT issuance).
- Durable per-user health rows (`normalized_daily_metrics`,
  `raw_source_events`, `source_connection_state`).
- Future connector-write tables (backlog, audit roll-ups,
  handoff blocks).

Supabase is the database / auth / state layer regardless of
where the control surface lives.

## 3. What Cloudflare Worker owns (target end state)

- Public MCP / app-dev-centre HTTP surface — the shape currently
  served by `/api/athlete-memory/admin/*` on Railway.
- Connector read tools (`get_work_status`, `get_release_status`,
  `get_health_source_status`, `get_handoff`,
  `get_health_audit_summary`, `get_pending_suggestions`).
- Owner-token-gated reads against Supabase.

Out of scope for the Worker:

- WHOOP / Polar OAuth flow (legacy /api/integrations/* — stays
  on Railway because OAuth callbacks anchor to specific URLs
  registered with each provider; rotating those is a separate
  operational task).
- Server-to-server `/v1/internal/*` ingest (also stays on
  Railway / WHOOP MCP; never reachable from the Worker).
- Build dispatch (`/admin/workflows/:id/dispatch`) — stays on
  Railway. The Worker explicitly does NOT relay build dispatches.

## 4. What Railway still owns until cutover

Everything in `chat-app/src/server/`. Mobile app keeps pointing
at Railway for both AI_INTERNAL_BASE + AI_PUBLIC_BASE until the
Worker verification is complete and the owner explicitly flips
the env values. Do NOT delete Railway config.

## 5. Local dev commands

```sh
# Worker scaffold lives in `cloudflare-worker/`
cd cloudflare-worker

# First-time setup (run once)
npm install
npx wrangler login   # opens browser; required for any deploy

# Run the Worker locally on http://127.0.0.1:8787
npm run dev

# Probe (no auth required for /health and /status)
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/status

# Probe admin-gated endpoints (need ATHLETE_MEMORY_API_TOKEN
# loaded into a `.dev.vars` file or via `wrangler secret put`)
curl -H "x-athlete-memory-token: $ATHLETE_MEMORY_API_TOKEN" \
  http://127.0.0.1:8787/mcp/health
```

## 6. Required Cloudflare setup steps (one-time)

1. Sign in / create a Cloudflare account.
2. Enable Workers & Pages.
3. `npx wrangler login` from `cloudflare-worker/`.
4. Set per-environment secrets:
   ```sh
   npx wrangler secret put ATHLETE_MEMORY_API_TOKEN --env preview
   # (paste the same value used on Railway env)
   ```
5. (Optional, for Stage 2) Set Supabase credentials:
   ```sh
   npx wrangler secret put SUPABASE_URL --env preview
   npx wrangler secret put SUPABASE_SERVICE_ROLE_KEY --env preview
   ```

Until step 5 is done, the Worker returns
`status: 'repo-only'` for routes that would otherwise read from
Supabase. That's by design — the scaffold is honest about its
state.

## 7. Required env vars

| Name | Where | Purpose |
|---|---|---|
| `ATHLETE_MEMORY_API_TOKEN` | Cloudflare secret (preview env) | Same shared token used by mobile + Railway; gates admin reads on the Worker |
| `SUPABASE_URL` | Cloudflare secret (preview env) | Supabase REST base, set when Stage 2 lands |
| `SUPABASE_SERVICE_ROLE_KEY` | Cloudflare secret (preview env) | Supabase server-side key, set when Stage 2 lands |
| `RAILWAY_FALLBACK_URL` | wrangler.toml `[vars]` | Public reference URL the Worker can echo for clients that need to hit Railway during overlap |
| `WORKER_MODE` | wrangler.toml `[vars]` | "preview" / "production" — surfaces in `/status` |
| `EXPO_PUBLIC_MCP_BASE_URL` | Mobile build env (NOT set yet) | Future switch in `apps/mobile/src/services/ai-backend-config.ts` to point a specific Admin/Dev "MCP probe" at the Worker without flipping the whole app off Railway |

## 8. How to test locally

```sh
cd cloudflare-worker
npm install
echo 'ATHLETE_MEMORY_API_TOKEN="dev-test-token"' > .dev.vars
npm run dev

# In another terminal:
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/status
curl -H "x-athlete-memory-token: dev-test-token" \
  http://127.0.0.1:8787/mcp/health
curl -H "x-athlete-memory-token: dev-test-token" \
  http://127.0.0.1:8787/app-dev-centre/status
```

Expected:

- `/health` and `/status` return 200 with `mode: 'preview'`.
- `/mcp/health` returns 200 with `mcp.status: 'repo-only'` until
  Supabase is wired.
- `/app-dev-centre/status` similarly returns repo-only metadata.
- Without the header → 403 `Forbidden admin access.`
- Without `ATHLETE_MEMORY_API_TOKEN` set → 403 `Admin token not
  configured` (so a misconfigured deployment fails closed, not
  open).

## 9. How to deploy preview

```sh
cd cloudflare-worker
npm run deploy:preview
```

Output: `*.workers.dev` URL. Use it in the verification curl
checks above to confirm the public-host shape matches local.

## 10. How to update the mobile app env (only after verification)

Do NOT set `EXPO_PUBLIC_MCP_BASE_URL` in production builds until:

1. Preview deploy verified by the curl checks above.
2. The Admin/Dev surface in the mobile app has been updated to
   gracefully handle both URLs (separate batch).
3. Owner explicitly approves the cutover via doc commit.

When ready, set in `eas.json` env / EAS env:

```jsonc
"env": {
  "EXPO_PUBLIC_MCP_BASE_URL": "https://lauburu-mcp-preview.YOUR_SUBDOMAIN.workers.dev"
}
```

The mobile `ai-backend-config.ts` now exports `MCP_BASE_URL` and
`MCP_BACKEND_CONFIGURED` — feature code can opt into the Worker
URL for specific calls without flipping the whole AI_PUBLIC_BASE.

## 11. Rollback plan

Cloudflare deployment is purely additive. To roll back:

1. Unset `EXPO_PUBLIC_MCP_BASE_URL` in the next mobile build.
2. (Optional) `npx wrangler delete` the Worker preview.

Railway routes never depended on the Worker; nothing breaks.

## 12. Live now vs repo-only

| Component | Status |
|---|---|
| Cloudflare Worker scaffold (`cloudflare-worker/`) | repo-only |
| `wrangler.toml` config | repo-only |
| Local dev command | runs from repo (no deploy needed) |
| Worker preview deploy | not deployed |
| Supabase reads from Worker | not wired |
| Mobile app pointing at Worker | not enabled (env var unset) |
| Railway backend (`chat-app/`) | LIVE — unchanged |
| Mobile app pointing at Railway | LIVE — unchanged |
| `EXPO_PUBLIC_MCP_BASE_URL` switch in `ai-backend-config.ts` | LIVE on `main` (env var unset, default `null`) |

All production traffic continues to hit Railway. The Worker is a
parallel scaffold, not a replacement.

## 13. Stages of cutover

| Stage | What | Trigger |
|---|---|---|
| Stage 0 — scaffold | Worker code + wrangler config + this doc | DONE this batch |
| Stage 1 — local dev | `wrangler dev` works against the scaffold | DONE this batch |
| Stage 2 — preview deploy | `*.workers.dev` URL responds to the public + admin endpoints | when Aaron has Cloudflare account + login |
| Stage 3 — Supabase reads | Worker reads owner-state from Supabase via the service-role key | after Stage 2 verified |
| Stage 4 — mobile env switch | `EXPO_PUBLIC_MCP_BASE_URL` set in EAS env; mobile Admin/Dev MCP probe hits the Worker | after Stage 3 has 1+ week of green polling |
| Stage 5 — full cutover | `AI_PUBLIC_BASE` flips to the Worker URL; Railway public endpoints turn off | after Stage 4 has 1+ month of green; explicit owner approval per doc commit |

Stage 5 is intentionally far away — the migration is staged so
each step is reversible by env-var unset, not git revert.
