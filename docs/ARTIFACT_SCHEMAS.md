# Persistent artifact schemas — single index

Every artifact schema this codebase uses, in one place, with the
test that locks each one. Goal: nothing important remains
terminal-only — every QA capture, gate, research result, or
notification mapping has a deterministic JSON shape that
downstream readers (Agent / Codex / Claude / a future Worker
route) can rely on.

This is a **doc-only** index. The schemas themselves live with
their owners. No app code, no Worker code change, no EAS build.

Status legend per row:
- **shipped** — schema and test already exist; cited test is
  green at HEAD.
- **partial** — schema exists; test missing or only covers
  happy paths.
- **planned** — referenced by a Codex handoff but not yet
  implemented.

## 1. Audit capture artifacts

| Artifact | captureMethod | captureTier | Owner | Test |
|---|---|---|---|---|
| Simulator/emulator screenshot bundle | n/a | `v1.5_human_driven_auto_capture` | `scripts/audit-screenshots-helpers.mjs` `buildManifest` | `cloudflare-worker/test/test-audit-screenshots-manifest.ts` — shipped |
| iPhone-Mirroring screenshot bundle | `iphone_mirroring` | (no tier marker; uses captureMethod) | `scripts/audit-screenshots-helpers.mjs` `buildIphoneMirroringManifest` | same file — shipped |
| scrcpy Android mirroring bundle | `scrcpy_android` | (no tier marker) | `scripts/audit-screenshots-helpers.mjs` `buildScrcpyAndroidManifest` | same file — shipped |
| Maestro YAML-flow auto-capture bundle | `maestro` | `v3_maestro_full_auto` | `scripts/audit-screenshots-helpers.mjs` `buildMaestroManifest` | same file — shipped |

Common envelope:

```json
{
  "schemaVersion": 1,
  "captureMethod": "iphone_mirroring|scrcpy_android|maestro" | undefined,
  "captureTier": "v1.5_human_driven_auto_capture|v3_maestro_full_auto" | undefined,
  "platform": "ios|android|unknown",
  "device": { "id": null, "name": null },
  "build": { "appVersion": null, "iosBuildNumber": null, "androidVersionCode": null, ... },
  "repo": { "branch": "main", "shortHead": "<7-12 hex>" },
  "capturedAt": "<ISO>",
  "screens": [...],   // simulator + iphone + scrcpy
  "captured": [...],  // maestro
  "failed": [...],    // maestro
  "skipped": [...],   // simulator
  "notes": "<string>" // iphone + scrcpy
}
```

Output dir convention: `artifacts/app-audit/<sub>/<isoTimestamp>/`
where `<sub>` is one of `simulator/`, `iphone-mirroring/`,
`android-scrcpy/`, `maestro/`. `artifacts/` is gitignored.

## 2. Approval-gate artifacts

| Artifact | Owner | Test |
|---|---|---|
| `ApprovalGate` (operator approval pause) | `packages/shared/src/approval-gates/index.ts` | `cloudflare-worker/test/test-approval-gates-transitions.ts` — shipped |
| `SpendGate` (AI cost-control gate) | `packages/shared/src/approval-gates/spend.ts` | `cloudflare-worker/test/test-spend-gates-and-prechecks.ts` — shipped |
| `PrecheckOutput` (deterministic AI bypass) | `packages/shared/src/approval-gates/spend-prechecks.ts` | same test — shipped |
| `ApprovalNotificationGateMutation` (push action mapper) | `packages/shared/src/approval-gates/push.ts` | `cloudflare-worker/test/test-push-approval-action-mapping.ts` — shipped |

Lifecycle: `pending → approved | deferred → expired | cancelled
| completed`. Every transition refuses secret-shaped text via
`looksLikeSecret`. Per-actionType safeDefault enforcement at
construction time.

Persisted gates live in:
- `data/approval-gates/gates.json` (repo state) — long-lived
  approval gates Aaron's workflow tracks.
- `apps/mobile/src/store/approval-gates-store.ts` (device
  state) — local-first device cache + recent ledger notes.
- `apps/mobile/src/store/spend-gates-store.ts` (device state)
  — same shape for AI spend gates.

## 3. Research-job artifacts

| Artifact | Owner | Test |
|---|---|---|
| `ResearchJob` (Deep Research offload) | `packages/shared/src/research-jobs/index.ts` | `cloudflare-worker/test/test-research-jobs.ts` — shipped |

Lifecycle: `draft → submitted → completed | cancelled |
reused`. `reuseHash` is a deterministic 32-bit FNV-1a hex of
`triggerType + topic + sorted scopeKeys`. Same hash short-
circuits a duplicate to `reused` carrying the cached artifact.
Newer completion supersedes older artifacts of the same hash.
`exportResearchPrompt` emits a paste-into-ChatGPT shorthand
that includes anti-rules and excludes the cached result.

Persisted in `apps/mobile/src/store/research-jobs-store.ts`
(device state). Server writeback (the eventual MCP tool
`project.list_research_jobs` on `/mcp/v2/admin`) is documented
as a follow-up.

## 4. QA gate / release-gate artifacts

| Artifact | Owner | Test |
|---|---|---|
| `AGENT_QA_RESULT_JSON` (Agent QA bundle) | `scripts/bridge-agent-qa.mjs` writer; consumed by `cloudflare-worker/src/mcp-v2.ts` `sanitizeQaResult` | `test-mcp-v2-chatgpt-compat.ts` (release gate shape) + `test-mcp-public-redaction.ts` — shipped |
| `connector_handoff.agentQaResult` (Worker projection) | `cloudflare-worker/src/mcp-v2.ts` | same — shipped |
| `release.get_gate` (public-safe release gate) | `cloudflare-worker/src/mcp-v2.ts` `buildReleaseGate` | `test-mcp-v2-chatgpt-compat.ts` — shipped |
| `admin_dev_installed_proof` (P1–P8 row map) | spec in `docs/ADMINDEV_INSTALLED_PROOF_GAP.md` § 3; recorded via `npm run bridge:agent-qa` | spec only — partial (recorder + UI live; cross-validation deferred) |

QA bundle envelope:

```json
{
  "status": "pass|fail|blocked|repo_only|partial",
  "gate": "release_gate|health_connectivity|grappling_readiness|native_control_centre|general",
  "platform": "android|ios|both|repo",
  "installedBuild": { "iosBuildNumber": null, "androidVersionCode": null, "appVersion": null, "channel": null, "track": null },
  "repo": { "branch": "main", "shortHead": "<7-12 hex>" },
  "results": { "<row>": "pass|fail|blocked|repo_only|partial|not_tested" },
  "releaseGate": { "newTestFlightAllowed": false, "newAndroidBuildAllowed": false, "reason": "<string>" },
  "requiredFixes": [ "<string>" ],
  "evidence": { "screenshotRefs": [ "<path>" ], "notes": "<string>" }
}
```

## 5. Bridge / heartbeat artifacts

| Artifact | Owner | Test |
|---|---|---|
| `coder_lanes` payload (incl. `lastSeenAt` / `lastStateChangeAt` / `source`) | `scripts/bridge-snapshot-lanes.sh` | `scripts/test-bridge-snapshot-classifier.py` (heartbeat helpers) + `chat-app/src/server/scripts/test-bridge-artifacts.ts` (schema) — shipped |
| `terminal_summary` payload | `scripts/bridge-snapshot-lanes.sh` (mark-agent-done ingest) | same chat-app schema test — shipped |
| `connector_handoff` payload | `scripts/bridge-snapshot-lanes.sh` | same — shipped |
| `connector_work_status` payload | `scripts/bridge-snapshot-lanes.sh` | same — shipped |
| `bridge-watch-state.json` (poll-loop cache) | `scripts/bridge-watch.sh` | runtime-only, gitignored |

Heartbeat fields per lane row:

```json
{
  "lastSeenAt": "<ISO>",
  "lastStateChangeAt": "<ISO>",
  "source": "tmux_bridge"
}
```

## 6. Action-ledger artifacts

| Artifact | Owner | Test |
|---|---|---|
| `pendingActions[]` rows | `data/action-ledger/pending_actions.json` | redaction surfaced by `cloudflare-worker/src/mcp-v2.ts` `buildPublicActionLedgerSummary`; covered by `test-mcp-public-redaction.ts` — shipped |

The action ledger remains the canonical durable store of
pending Aaron-approved work. Approval-gate stores emit ledger
notes (via `Copy last ledger note`) for manual paste into this
file until a server-side writeback route lands.

## 7. Public-MCP redaction artifacts

| Artifact | Owner | Test |
|---|---|---|
| `/mcp/public` 4-tool surface | `cloudflare-worker/src/mcp-public.ts` | `test-mcp-public-redaction.ts` — shipped |
| `/mcp/v2` core 9-tool surface | `cloudflare-worker/src/mcp-v2.ts` | `test-mcp-v2-chatgpt-compat.ts` — shipped |
| `/mcp/v2/admin` 17-tool admin surface | same | same test (cross-surface guard) — shipped |
| `/mcp/v2/website` 25-tool proxy | same | live test in `chat-app/src/server/scripts/test-mcp-v2-live.ts` — shipped |
| `/mcp/core` 6-tool legacy surface | `cloudflare-worker/src/mcp-core.ts` | `test-mcp-core-chatgpt-compat.ts` — shipped |

## 8. Verification matrix

To run ALL artifact contract tests in one pass:

```sh
cd cloudflare-worker
npx tsx test/test-audit-screenshots-manifest.ts
npx tsx test/test-approval-gates-transitions.ts
npx tsx test/test-spend-gates-and-prechecks.ts
npx tsx test/test-push-approval-action-mapping.ts
npx tsx test/test-research-jobs.ts
npx tsx test/test-mcp-v2-chatgpt-compat.ts
npx tsx test/test-mcp-public-redaction.ts
npx tsx test/test-mcp-core-chatgpt-compat.ts
npx tsx test/test-operating-rules.ts
npx tsx test/test-mcp-v2-work-status-write.ts

cd ..
python3 scripts/test-bridge-snapshot-classifier.py
npm run bridge:verify
```

Each test prints a one-line success message and exits 0 on
pass.

## 9. Anti-rules

- No artifact schema may carry **secret-shaped text**
  (looksLikeSecret patterns: JWT, sk-, ghp_, AKIA, whsec_,
  password, bearer). Every `make*` constructor and every
  transition refuses construction / mutation when input
  fields look secret-shaped.
- No artifact carries **raw user health values**. Audit
  screenshots may inadvertently capture them on-screen, in
  which case the privacy doc instructs Aaron to crop/blur
  before sharing externally; the screenshot-helper scripts
  refuse obvious-token filenames as a last-line guard.
- No artifact may be **silently committed** to the repo.
  `artifacts/` is gitignored; `data/agent-status/lanes/` is
  gitignored; runtime caches are gitignored.
- No artifact may be **auto-shared** to MCP / Slack /
  public surfaces without Aaron's explicit decision. Every
  helper that produces an artifact stops at the local
  filesystem; Aaron decides every share.
- No artifact may be **promoted past Aaron**. Even when
  a gate is approved, the underlying action does not run
  until the matching automation reads the ledger note (or
  the future server-side writeback lands).

## 10. Cross-references

Per artifact category:

- `docs/IN_APP_AUDIT_AUTOMATION_SPEC.md` — three-tier audit
  spec.
- `docs/AUDIT_SCREENSHOTS.md` — simulator/emulator driver.
- `docs/IPHONE_MIRRORING_QA_WORKFLOW.md` — iOS real-device
  capture.
- `docs/AUDIT_SCRCPY_ANDROID.md` — Android real-device
  capture.
- `apps/mobile/audit-flows/README.md` — Maestro flows.
- `docs/APPROVAL_GATES_AND_PUSH.md` — approval / spend gates
  + push setup blockers.
- `docs/MCP_BRIDGE_AUTOREFRESH.md` — heartbeat + auto-snapshot
  loop.
- `docs/ADMINDEV_INSTALLED_PROOF_GAP.md` — proof checklist
  P1–P8.
- `docs/MCP_LONGTERM_ACCESS_ARCHITECTURE.md` § 2 — Developer
  Mode off criteria.
- `docs/CHATGPT_CONNECTOR_SETUP.md` — ChatGPT connector
  setup.
- `docs/MCP_CORE_AGENT_TROUBLESHOOTING.md` — Agent diagnostic
  ladder.
