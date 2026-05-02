# Admin / Dev Control Center — architecture plan

Hidden, admin-gated screen inside the Lauburu mobile app for managing
the build/release/AI workflow from a phone — without ever turning the
app into a remote shell.

## Hard rules

- The mobile app **reads** status and **opens** approved external URLs.
- The mobile app must **never** execute arbitrary shell, never call
  EAS / Railway / GitHub admin APIs directly, and never carry tokens
  for those systems at runtime.
- All workflow triggers go through a **signed backend proxy** that the
  app calls with the existing internal/admin auth, and the proxy in
  turn calls a small set of approved GitHub Actions
  `workflow_dispatch` endpoints with secrets that live only on the
  backend.
- All admin endpoints return booleans / counts / public URLs only —
  no env values, no token strings, no service-role keys, ever.
- Cross-user data is gated by k≥10 + explicit consent (not changed by
  this work; remains backlog).

## Stages

### Stage 1 — MVP (this batch, repo-only)

Implemented as `apps/mobile/app/admin-dev.tsx` + a hidden long-press
gate on Settings → About → Version (admin email allowlist).

Sections:

1. App build / runtime — version, Android versionCode / iOS build
   number, runtime version, channel, current update id, OTA blocked
   note.
2. Backend status — fetches the existing
   `/v1/internal/athletes/:id/ai-health-context` with the internal
   token already shipped to the EAS production env. Reads
   booleans/counts only. No token displayed.
3. Data / AI status — total normalised days, date range, sources
   connected count, readiness status, multi-window support.
4. Release / status links — Expo project, Expo builds, Expo updates,
   Railway dashboard, GitHub repo, GitHub Actions, Play Console, App
   Store Connect. All public URLs.
5. Prompt library — collapsible blocks of canonical Claude prompts;
   text is rendered inside selectable RNText so the OS native copy
   menu works without an extra native dep.
6. Status handoff template — collapsible compact `CHATGPT_STATUS_*`
   block.
7. Workflow triggers — placeholders only. Buttons are disabled with
   the copy *"Workflow trigger not connected yet."*

Entry point: Settings → About → Version row → long-press (≥800 ms)
when signed in as `aaron.t.maher@gmail.com`. Hidden for everyone else.

### Stage 2 — Read-only backend status endpoint

Add `GET /api/admin/status` in `chat-app/src/server/routes/`. Reuses
the existing `requirePrivateAthleteAccess` (`x-athlete-memory-token`)
or a stricter `x-admin-token`. Returns:

```jsonc
{
  "backendHealthy": true,
  "aiHealthContextAvailable": true,
  "normalizedDaysTotal": 95,
  "dateRange": { "first": "2026-01-27", "last": "2026-05-02" },
  "sourceCoverage": { "live": 3, "evidence_only": 2, "planned": 2 },
  "blockers": ["EAS Update SDK 54 publishes are server-rejected"],
  "generatedAt": "2026-05-02T00:00:00.000Z"
}
```

No env values. No token strings. No PHI. Aggregate counts and known
links only.

### Stage 3 — Workflow triggers via signed proxy

A small backend route, e.g.:

```
POST /api/admin/workflow/dispatch
Headers: x-admin-token
Body:    { "workflow": "eas-android-build" | "backend-deploy" | "release-audit",
           "ref": "main" }
```

Backend validates the token, validates the workflow name against an
allowlist, and calls
`POST https://api.github.com/repos/<owner>/<repo>/actions/workflows/<file>/dispatches`
with `Authorization: Bearer ${process.env.GITHUB_DISPATCH_TOKEN}` (a
fine-grained PAT with `actions:write` only, scoped to that one repo).
The mobile app never sees the GitHub token.

GitHub Actions workflows in `.github/workflows/`:

- `deploy-backend.yml` — typecheck `chat-app` + `packages/shared`,
  then `railway up` (uses `${{ secrets.RAILWAY_TOKEN }}`).
- `eas-android-build.yml` — `eas-cli build --platform android
  --profile production` (uses `${{ secrets.EXPO_TOKEN }}`).
- `release-audit.yml` — diff `app.json` versionCode/buildNumber, run
  manifest dump on the latest AAB artifact, post a status comment.

### Stage 4 — Codespaces / VPS option

Optional path for live editing from phone:

- GitHub Codespaces with the repo's existing Node version + a
  `.devcontainer/devcontainer.json` that pre-installs `eas-cli` and
  `railway` CLIs. Secrets via Codespaces secret store.
- Small VPS only if a long-running poller becomes necessary; not
  needed for the dispatch model above.

## Secrets — where they live

| Secret | Lives in | Used by | Never in |
|---|---|---|---|
| `RAILWAY_TOKEN` | GitHub Actions secrets | `deploy-backend.yml` | mobile, repo |
| `EXPO_TOKEN` | GitHub Actions secrets | `eas-android-build.yml` | mobile, repo |
| `GITHUB_DISPATCH_TOKEN` | Railway env | backend signed proxy | mobile, repo |
| `INTERNAL_API_TOKEN` | Railway env + EAS env | backend + mobile | repo |
| `ATHLETE_MEMORY_API_TOKEN` | Railway env + EAS env | backend + mobile | repo |
| Supabase service role | Railway env | backend mirrors | mobile, repo |

## What can be triggered from the app

After Stage 3 lands:

- Backend deploy (signed proxy → `deploy-backend.yml`).
- Android AAB build (signed proxy → `eas-android-build.yml`).
- Release audit (signed proxy → `release-audit.yml`).

What is **never** triggerable from the app:

- Arbitrary shell.
- Token rotation.
- Secrets read.
- Cross-user data access (separate consent + k-threshold path).
- Production database mutations.

## Mobile UI rules

- Stay in `app/admin-dev.tsx` (Stack route, not a tab).
- Long-press version row only — no marketing surface.
- Disabled trigger buttons until Stage 3 lands. Always say so in copy.
- Read-only by default. Any future write action requires a confirm
  step inside the app.
