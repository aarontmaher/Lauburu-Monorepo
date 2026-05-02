# Admin / Release Automation Plan

Intent: turn the Lauburu mobile app into a phone-first release control
center, without ever turning it into a remote shell.

## What the app can safely do

- Read public/admin-protected status (build versions, backend health,
  AI coverage, OTA state, links).
- Copy canonical Claude / ChatGPT prompts to clipboard / system copy
  menu.
- Trigger a fixed allowlist of GitHub Actions `workflow_dispatch`
  endpoints through a signed backend proxy.
- View the most recent workflow run URLs and their status.
- Open Expo / Railway / GitHub / Play Console / App Store Connect.

## What the app must NEVER do

- Execute arbitrary shell commands.
- Hold or display tokens for EAS, Railway, GitHub, Apple, or Google.
- Bypass the workflow allowlist.
- Push to Supabase or rotate credentials.
- Expose admin endpoints publicly without `x-athlete-memory-token` (or
  a stricter `x-admin-token` once it exists).

## Secret model

| Secret | Lives in | Used by |
|---|---|---|
| `EXPO_TOKEN` | GitHub Actions secrets | EAS build/update workflows |
| `RAILWAY_TOKEN` | GitHub Actions secrets | backend deploy workflow |
| `GITHUB_DISPATCH_TOKEN` | Railway env | backend signed proxy → Actions |
| `INTERNAL_API_TOKEN` / `ATHLETE_MEMORY_API_TOKEN` | Railway env + EAS env | backend + mobile (already live) |
| Play Developer API service account JSON | GitHub Actions secret (`PLAY_SA_JSON`) | future Play upload step |
| Apple App Store Connect API key | GitHub Actions secrets (`APPLE_KEY_ID`, `APPLE_ISSUER_ID`, `APPLE_API_KEY`) | future TestFlight submit step |

The mobile app sees **none** of these directly.

## Workflow model

Mobile app → `POST /api/admin/workflows/:workflowId/dispatch`
(protected by `x-athlete-memory-token`) → backend validates workflow
ID against the allowlist → backend calls
`POST https://api.github.com/repos/<owner>/<repo>/actions/workflows/<file>/dispatches`
with `Authorization: Bearer ${GITHUB_DISPATCH_TOKEN}` (a fine-grained
PAT scoped to `actions:write` on the one repo).

Backend `GET /api/admin/workflows/runs` mirrors
`GET /actions/runs?per_page=10` so the app can render the last few
runs without ever holding the GitHub token.

## Required workflows

`.github/workflows/`:

- **mobile-typecheck.yml** — checkout → setup Node → install →
  `cd apps/mobile && npx tsc --noEmit`.
- **android-aab-build.yml** — typecheck → `npx eas-cli build --platform
  android --profile production --non-interactive` (via `EXPO_TOKEN`)
  → output build URL.
- **ios-testflight-build.yml** — typecheck → `npx eas-cli build
  --platform ios --profile production` → optional `eas submit` if the
  `submit` input is `true` and `APPLE_*` secrets are present.
- **backend-smoke.yml** — `curl` `/v1/internal/.../ai-health-context`
  with `x-internal-token` (server-side; `INTERNAL_API_TOKEN` is a
  GitHub Action secret) and report HTTP status; never echo the token.
- **release-audit.yml** — read `app.json` for current
  versionCode/buildNumber, list last 5 EAS builds for each platform,
  list latest Railway deploy URL, summarise blockers.
- **ota-diagnostic.yml** — read EAS branch/channel/runtime config and
  report; only attempt one publish if `publish` input is `true` and a
  reason is provided. Never blind-loop publishes.

All workflows: `workflow_dispatch` only (no `push` triggers in this
batch). Allowlist enforced server-side; GitHub side will accept
manual dispatch even if the proxy is bypassed, so secrets stay
GitHub-side and we monitor via the runs API.

## Safety gates

- Owner allowlist (admin email) on the mobile route.
- `x-athlete-memory-token` on backend endpoints; server-side
  allowlist of workflow IDs.
- Confirmation alert in the app before every trigger.
- Branch lock: workflows accept `ref: 'main'` only by default.
- No free-text command input.
- Audit log: every dispatch records `(user_email, workflow, timestamp,
  ref, run_id)`.
- Rate limit: backend rejects dispatch if last run for the same
  workflow started < 60 s ago.
- Dry-run: every workflow accepts a `dry_run: 'true'` input that
  short-circuits before the destructive step.

## Implementation status (this batch)

- ✅ `.github/workflows/*.yml` scaffolded (6 files).
- ✅ Plan doc (`docs/ADMIN_RELEASE_AUTOMATION_PLAN.md`).
- ✅ Backend `GET /api/admin/status` (read-only, protected) returning
  booleans/counts/links — no secrets.
- ⏳ `POST /api/admin/workflows/:workflowId/dispatch` — scaffold
  documented but **not implemented** until the repo is pushed to
  GitHub and a `GITHUB_DISPATCH_TOKEN` is set on Railway.
- ⏳ Mobile Quick-actions buttons remain disabled with copy "Connect
  GitHub Actions trigger backend first."

## Follow-up steps (not in this batch)

1. `gh repo create` (private) and push the local repo to GitHub.
2. Create a fine-grained PAT with `actions:write` and store it as
   `GITHUB_DISPATCH_TOKEN` on Railway production.
3. Create `EXPO_TOKEN` and `RAILWAY_TOKEN` as GitHub Actions secrets.
4. Implement `POST /api/admin/workflows/:workflowId/dispatch` and
   `GET /api/admin/workflows/runs` on the backend, deploy.
5. Enable the mobile Quick-actions buttons.
6. Optional: add Play Developer API service account JSON
   (`PLAY_SA_JSON`) for Internal Testing auto-upload, and Apple
   App Store Connect API key for `eas submit` automation.
