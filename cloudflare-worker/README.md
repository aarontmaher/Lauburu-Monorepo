# Lauburu MCP — Cloudflare Worker

Scaffold-only today. Production traffic still hits the Railway
backend at
`https://lauburu-ai-backend-production.up.railway.app`. See
`docs/CLOUDFLARE_MIGRATION.md` for the staged cutover plan.

## Quick start

```sh
cd cloudflare-worker
npm install                       # 61 packages, ~18s
npx wrangler login                # one-time, opens browser
echo 'ATHLETE_MEMORY_API_TOKEN="<paste-from-Railway-env>"' > .dev.vars
npm run dev                       # http://127.0.0.1:8787
```

In another terminal:

```sh
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/status
curl -H "x-athlete-memory-token: <paste>" \
  http://127.0.0.1:8787/mcp/health
curl -H "x-athlete-memory-token: <paste>" \
  http://127.0.0.1:8787/app-dev-centre/status
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
