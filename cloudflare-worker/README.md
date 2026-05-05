# Lauburu MCP — Cloudflare Worker

Scaffold-only today. Production traffic still hits the Railway
backend at
`https://lauburu-ai-backend-production.up.railway.app`. See
`docs/CLOUDFLARE_MIGRATION.md` for the staged cutover plan.

Verified locally (2026-05-06):

- `wrangler login` succeeded.
- `wrangler` is on v4.88.0; `npm install` clean (0 vulns).
- `wrangler deploy --dry-run --env preview` succeeded; bundle
  5.19 KiB / gzip 1.71 KiB. No deploy attempted.
- `npm run dev` serves `http://127.0.0.1:8787`.
- `GET /health` returns 200; `GET /status` returns 200; admin
  routes return 403 without the header.
- `.dev.vars` may still hold the literal placeholder string
  `<paste-from-Railway-env>` — replace with the real token from
  Railway env before admin routes can return 200.

## Quick start

```sh
cd cloudflare-worker
npm install                       # 39 packages on Wrangler 4
npx wrangler login                # one-time, opens browser

# IMPORTANT: substitute the placeholder with the real token from
# Railway env (do NOT commit the file — already gitignored).
# The literal string below is just a marker; replace it with the
# value of ATHLETE_MEMORY_API_TOKEN from Railway dashboard.
echo 'ATHLETE_MEMORY_API_TOKEN="REPLACE_WITH_REAL_TOKEN_FROM_RAILWAY"' > .dev.vars

npm run dev                       # http://127.0.0.1:8787
```

In another terminal (set `ATHLETE_MEMORY_TOKEN` in your shell
once so the curl examples don't carry the literal token):

```sh
# Public probes (no auth) — should always return 200
curl -sS http://127.0.0.1:8787/health
curl -sS http://127.0.0.1:8787/status

# Admin-gated probes — replace the placeholder env var with the
# real Railway token in your shell before running.
export ATHLETE_MEMORY_TOKEN="REPLACE_WITH_REAL_TOKEN_FROM_RAILWAY"

curl -sS -H "x-athlete-memory-token: $ATHLETE_MEMORY_TOKEN" \
  http://127.0.0.1:8787/mcp/health

curl -sS -H "x-athlete-memory-token: $ATHLETE_MEMORY_TOKEN" \
  http://127.0.0.1:8787/app-dev-centre/status

# Negative checks
curl -sS -i http://127.0.0.1:8787/mcp/health | head -1
# → HTTP/1.1 403 Forbidden

curl -sS -i -H "x-athlete-memory-token: not-the-real-token" \
  http://127.0.0.1:8787/mcp/health | head -1
# → HTTP/1.1 403 Forbidden
```

Without the header: `403 Forbidden admin access.`. Without
`ATHLETE_MEMORY_API_TOKEN` set on the Worker: `403 Admin token
not configured` (fail-closed by design).

## Deploy preview

```sh
npx wrangler secret put ATHLETE_MEMORY_API_TOKEN --env preview
npm run deploy:preview
```

Output: `https://lauburu-mcp-preview.<your-subdomain>.workers.dev`.
Run the same curl checks above against that URL.

## Files

- `wrangler.toml` — Worker config (preview + production envs;
  production reserved, do not deploy until cutover signed off).
- `src/worker.ts` — handler. 7 GET endpoints; admin-token gated
  reads fail closed.
- `tsconfig.json` — ES2022 + Bundler resolution + workers-types.
- `package.json` — `dev` / `deploy:preview` / `typecheck` scripts.
- `.gitignore` — `node_modules`, `.dev.vars`, `.wrangler`, `dist`.
- `.dev.vars` (NOT committed) — local-only secrets for
  `wrangler dev`.

## Endpoints

| Method | Path | Auth |
|---|---|---|
| GET | `/health` | public |
| GET | `/status` | public |
| GET | `/mcp/health` | admin token |
| GET | `/app-dev-centre/status` | admin token |
| GET | `/handoff` | admin token |
| GET | `/automation-state` | admin token |
| GET | `/pending-suggestions` | admin token |

All admin-gated routes return `mode: 'repo-only'` metadata until
Supabase is wired (Stage 3 per
`docs/CLOUDFLARE_MIGRATION.md`).
