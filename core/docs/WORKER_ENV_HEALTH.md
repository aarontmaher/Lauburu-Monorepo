# Worker environment health

This document tracks the MCP Worker deployment split without storing
secret values.

## Current finding

As of 2026-05-08T04:31Z, both the top-level and preview Workers read
Supabase fresh through `/mcp/v2`.

Verified markers on both endpoints:

- `source: "supabase"`
- `freshness.staleReason: "fresh"`
- `freshness.isStale: false`

The previous `env_missing` state is retained below as historical
context only.

## Historical finding

Preview MCP is the fresh shared-state surface:

- `https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/v2`
- `project.get_current_state` returns `source: "supabase"` and
  `freshness.staleReason: "fresh"`.
- Secret names present on `--env preview`: `ATHLETE_MEMORY_API_TOKEN`,
  `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.

The top-level Worker currently has only `ATHLETE_MEMORY_API_TOKEN`.
It does not have `SUPABASE_URL` or `SUPABASE_SERVICE_ROLE_KEY`, so
`project.get_current_state` correctly reports `source: "placeholder"`
and `freshness.staleReason: "env_missing"`.

This was not a code bug. It was an environment configuration gap.

## Safe manual fix

Aaron must paste the existing Supabase values into Wrangler without
printing them:

```bash
cd cloudflare-worker
npx wrangler secret put SUPABASE_URL
npx wrangler secret put SUPABASE_SERVICE_ROLE_KEY
npx wrangler deploy
```

Do not put these values in mobile, `EXPO_PUBLIC_*`, committed docs, or
shell commands with `--value`. Wrangler prompts for the value
interactively and stores it as a Cloudflare secret.

Afterward, verify with:

```bash
curl -sS https://lauburu-mcp.lauburu-aaron.workers.dev/mcp/v2 \
  -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"project.get_current_state","arguments":{}}}'
```

Expected safe marker:

- `source: "supabase"`
- `freshness.staleReason: "fresh"`
- `actionLedger.pendingCount` present

## What not to do

- Do not copy service-role secrets into `apps/mobile`.
- Do not add Supabase service-role values to EAS env.
- Do not expose secret values in MCP, logs, screenshots, docs, or chat.
- Do not weaken no-auth MCP write blocking.
