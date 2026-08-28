# Mobile Railway dependency audit

Updated 2026-05-06. Mobile-app view only; backend deployment state is
tracked separately by Claude/main-lane work.

## Summary

The mobile app still points production backend traffic at Railway via
`EXPO_PUBLIC_AI_BACKEND_URL` and `EXPO_PUBLIC_AI_PUBLIC_URL`. Android
Health Connect itself is on-device and does not require Railway to
request permissions or read local records, but durable ingest, Coach
context, Admin/Dev backend status, WHOOP/Polar direct flows, feedback,
and automation status still use the Railway-hosted API paths unless the
build env is explicitly changed.

## Classification

| Area | Current mobile dependency | Classification |
| --- | --- | --- |
| Android Health Connect permission sheet | `react-native-health-connect` / Android provider | app independent of Railway |
| Android Health Connect local sync | native Health Connect reads + local store | app independent of Railway until backend fan-out |
| Health Connect audit events | `audit-event-store` local secure storage | app independent of Railway |
| Save long-term health data | `durable-persist.ts` posts to internal ingest | still points to Railway through env |
| Admin/Dev backend status | `/v1/internal/.../ai-health-context` and `/api/athlete-memory/admin/status` | still points to Railway through env |
| Admin/Dev agent status | `/api/athlete-memory/admin/agent-status` | new backend route expected / still Railway today |
| Workflow dispatch buttons | `/api/athlete-memory/admin/workflows/:id/dispatch` | new backend route expected / still Railway today |
| WHOOP Direct | `/api/integrations/whoop/*` | tied to Railway OAuth/backend routes |
| Polar Direct | `/api/integrations/polar/*` | tied to Railway OAuth/backend routes |
| WHOOP bridge card | Supabase bridge plus Railway WHOOP MCP upstream | tied to Railway until bridge target migrates |
| Supabase mirror | Supabase auth/functions/client | app independent of Railway for mirror path |
| Cloudflare Worker | `EXPO_PUBLIC_MCP_BASE_URL` documented but unset | env-only / unknown until deployed |
| Grappler Readiness UI | docs/plans only for this lane | intentionally not shipped |

## Shutdown blockers

Before Railway shutdown, mobile needs a verified replacement for:

- `EXPO_PUBLIC_AI_BACKEND_URL` internal ingest and AI-context reads.
- `EXPO_PUBLIC_AI_PUBLIC_URL` athlete-memory, admin status, feedback,
  backlog, integration, and workflow-dispatch routes.
- WHOOP/Polar OAuth callback hosting and token storage.
- WHOOP MCP / bridge upstream if that path is still used.
- Feedback attachment persistence if still served from Railway
  filesystem.

Unknown without live backend/MCP access:

- Whether Cloudflare Worker preview has the full route parity for
  Admin/Dev status and health-source summary endpoints.
- Whether WHOOP/Polar token persistence has moved off Railway
  filesystem.
- Whether `/admin/health-source-status`, `/health-audit-summary`, or
  `/health-event` exist in production.
- Whether any tester build in the field points at a non-Railway env.
