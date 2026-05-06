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

## 11.5 Verified state (2026-05-06, after Wrangler 4 bump)

- `npm install` in `cloudflare-worker/` clean — 39 packages, 0
  vulnerabilities.
- `wrangler --version` reports `4.88.0` (bumped from `^3.50.0`
  in this batch's commit).
- `wrangler login` succeeded on Aaron's machine.
- `wrangler deploy --dry-run --env preview` succeeds with no
  warnings; bundle 5.19 KiB / gzip 1.71 KiB. No actual deploy
  attempted.
- `npm run dev` serves `http://127.0.0.1:8787`.
- `GET /health` → 200; `GET /status` → 200.
- Admin-gated routes return 403 without the header (correct
  fail-closed behaviour). Real-token verification pending: the
  `.dev.vars` may still carry the literal placeholder string
  `<paste-from-Railway-env>`. Substitute the real token from
  Railway env before expecting 200 from `/mcp/health`.
- `wrangler.toml` updated for Wrangler 4: top-level `[vars]`
  no longer auto-inherits, so `[env.preview.vars]` and
  `[env.production.vars]` blocks now redeclare `WORKER_MODE` +
  `RAILWAY_FALLBACK_URL` explicitly. Production env stays
  reserved (no deploy).
- Worker `tsc --noEmit` clean after a small `ConnectorMeta`
  ordering fix.

No production behaviour change. Mobile app and Railway
unchanged.

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

## 14. DNS / custom domain cutover steps (Stage 5 only)

Reserved for the final cutover. Do NOT run these until every
prior stage has been green for ≥1 month and Aaron has signed off
in a doc commit.

1. In Cloudflare dashboard → Workers → `lauburu-mcp-production` →
   **Triggers → Custom Domains** → add the domain you want the
   Worker to own (e.g. `mcp.lauburugrapplingmap.com` or a
   subpath of an existing zone).
2. Cloudflare automatically issues TLS via Universal SSL when
   the domain is on a Cloudflare zone. If the zone lives
   elsewhere, follow Cloudflare's guidance to add the zone first.
3. Update the mobile app `eas.json` env values for the next
   build:
   ```jsonc
   "env": {
     "EXPO_PUBLIC_AI_PUBLIC_URL": "https://mcp.lauburugrapplingmap.com/api/athlete-memory",
     "EXPO_PUBLIC_AI_BACKEND_URL": "https://mcp.lauburugrapplingmap.com/v1/internal"
   }
   ```
   (The Worker must be ready to serve the matching paths — Stage
   3 onwards covers the public surface; the legacy `/v1/internal/*`
   server-to-server routes stay on Railway and require their own
   migration plan, which is NOT in scope for the Worker.)
4. Cut a new mobile build via Admin/Dev → Primary actions.
5. Once the mobile cohort is fully on the new build AND the
   Worker has served traffic cleanly for ≥7 days, delete the
   Railway service (or pause billing).

## 15. Rollback plan (full)

Each stage is reversible by env-var change; nothing requires git
revert.

- **Stage 4 rollback** (mobile env switch caused issues): unset
  `EXPO_PUBLIC_MCP_BASE_URL` in EAS env, cut a new mobile build.
  Worker stays deployed but no app code calls it.
- **Stage 5 rollback** (custom domain cutover caused issues):
  point `EXPO_PUBLIC_AI_PUBLIC_URL` and `EXPO_PUBLIC_AI_BACKEND_URL`
  back at the Railway URL (`https://lauburu-ai-backend-production.up.railway.app`)
  in `eas.json`, cut a new mobile build. Railway service must
  not have been deleted yet (do NOT delete Railway until Stage
  5 has been green for ≥1 month per §14 step 5).
- **Custom domain rollback**: in Cloudflare dashboard → Workers
  → Triggers → Custom Domains → remove the domain. DNS
  propagation back to Railway is instant if Railway still owns
  the route.

## 16. Final Railway removal checklist

Only run AFTER §14 step 5 condition is satisfied (≥7 days of
clean Worker traffic on the production cohort).

- [ ] No mobile build in the field still points at the Railway
      URL — confirm via the EAS env on the latest released build
      and via the in-app Settings → About → Build/Version row.
- [ ] No external service / connector / user-facing URL still
      resolves to Railway. Check `dig +short
      lauburu-ai-backend-production.up.railway.app` from a
      neutral network.
- [ ] All audit roll-up routes that were planned for the Worker
      (per `IN_APP_AUDIT_SYSTEM.md` § Backend route contract) are
      live and Aaron has used them at least once.
- [ ] Railway env values for `ATHLETE_MEMORY_API_TOKEN` /
      `INTERNAL_API_TOKEN` / `INTEGRATION_STATE_SECRET` are
      either rotated to Cloudflare or scheduled for rotation
      post-removal.
- [ ] Railway service paused (NOT deleted yet) for 7 more days
      as a fallback window.
- [ ] After the additional 7-day fallback window, Railway service
      may be deleted. Doc-commit the deletion timestamp.

## 17. Supabase schema/env required for Stage 3 reads

Documented here so when Stage 3 lands, the env vars and table
names are unambiguous.

Required Cloudflare secrets (set per env via `wrangler secret put`):

- `SUPABASE_URL` — same value the Railway backend reads
  (`https://YOUR-PROJECT.supabase.co`).
- `SUPABASE_SERVICE_ROLE_KEY` — server-side key. NEVER bundle
  into the mobile app.

Tables / RPCs the Worker reads (read-only):

- `auth.users` (Supabase-managed) — only for the owner email
  match when admin-token auth is augmented with per-user JWT
  cross-check (Stage 5 nicety, not required for Stage 3).
- `normalized_daily_metrics` — read-only count + most-recent
  timestamp roll-ups for `/admin/health-source-status`. Per-user
  rows NEVER serialised to the wire (only aggregates).
- `source_connection_state` — count of active connections per
  source. Aggregates only.
- (Future) `audit_events` table — schema NOT yet defined; lands
  with the Stage 3 audit roll-up route per
  `IN_APP_AUDIT_SYSTEM.md`.

If any of the table names above are wrong, the Worker handler
keeps returning `supabaseConfigured: false` + `repo-only` —
fail-soft on schema mismatch, never invent data.
