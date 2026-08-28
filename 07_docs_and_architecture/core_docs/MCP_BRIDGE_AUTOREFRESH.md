# MCP bridge auto-refresh

How terminal/tmux lane state stays within roughly 10–15s of MCP /
Admin/Dev. Three pieces:

1. **Heartbeat fields** on every per-lane row.
2. **Auto-snapshot loop** that watches tmux state and triggers
   the existing writer on transitions plus a periodic heartbeat.
3. **AdminDev drift warning** that surfaces when the heartbeat
   goes stale on the device side.

This is repo-side and free to run; no extra Supabase writes
beyond what `bridge-snapshot-lanes.sh` already does.

## 1. Heartbeat fields

Every lane row in
`data/agent-status/lanes/coder_lanes.json` (and the per-lane
`data/agent-status/lanes/<laneId>.json`) now carries:

| Field | Meaning |
|---|---|
| `lastSeenAt` | ISO timestamp; bumped on every snapshot regardless of state. Drives the freshness window. |
| `lastStateChangeAt` | ISO timestamp; bumped only when `status` changes. Carries forward across snapshots that don't change anything. |
| `source` | Provenance string. `tmux_bridge` for the canonical writer; can be overridden per snapshot. |

The pure helper `compute_state_change_at(prev_status,
current_status, prev_change_at, now)` lives in
`scripts/bridge_snapshot_classifier.py` so the same rule
applies in tests, the writer, and any future tooling.

## 2. Auto-snapshot loop

`scripts/bridge-watch.sh` is a long-running poll loop:

```
npm run bridge:watch
```

What it does on every tick (default 10 seconds):

1. Capture each tmux session's last 200 lines (lightweight; no
   subprocess fan-out beyond `tmux` + `git`).
2. Run the classifier to detect the current status per lane.
3. Compare to the last-known status cached in
   `data/agent-status/lanes/.bridge-watch-state.json`.
4. If any lane's status changed, run the full
   `bridge-snapshot-lanes.sh` writer (which writes to disk +
   upserts Supabase).
5. If `HEARTBEAT_INTERVAL` (60s by default) has elapsed since
   the last full snapshot, run the writer anyway as a
   heartbeat refresh so `lastSeenAt` stays fresh.
6. `MIN_WRITE_INTERVAL` (10s by default) debounces flapping
   panes so a stuck "thinking…" indicator can't burn writes.

Cost in a typical day: 30–60 writes (one per state change +
one per minute while terminals are quiet). Each write is the
same 4-row Supabase upsert the manual snapshot already does.

Flags / env:

```
POLL_INTERVAL=10           # seconds between ticks
HEARTBEAT_INTERVAL=60      # seconds between forced full snapshots
MIN_WRITE_INTERVAL=10      # seconds debounce after every write
./scripts/bridge-watch.sh --once       # run one tick + exit (CI / smoke)
./scripts/bridge-watch.sh --poll-interval=15
./scripts/bridge-watch.sh --heartbeat-interval=120
./scripts/bridge-watch.sh --min-write-interval=20
```

Stop with Ctrl-C. Trap-based shutdown.

Recommended invocation: keep a tmux pane named `bridge-watch`
running `npm run bridge:watch`. It survives restarts of the
laptop's other tmux sessions because it only reads them.

For prompt automation that should notice lane completion quickly,
run the MCP polling watcher at the same cadence:

```
npm run watcher:mcp -- --interval 10 --auto-refresh
```

The watcher accepts `--interval` down to 5 seconds; use 10 seconds
as the normal laptop-side setting to avoid unnecessary Worker
polling while still catching finished lanes quickly.

## 3. AdminDev drift warning

The mobile Admin/Dev tab now exposes a per-lane heartbeat
chip + an explicit "Lane drift suspected" warning when:

- `lastSeenAt` for any lane is older than 60 seconds, OR
- the MCP freshness signal flips to `no_writeback` /
  `env_missing`.

Both conditions surface the same exit-from-the-app
recommendation: start `npm run bridge:watch`, or run
`npm run bridge:snapshot` once.

Per-lane line format:

```
claude · idle · 12s
codex · working · stale 4m
```

`stale Xm` indicates the lane's `lastSeenAt` is past the
60-second drift threshold.

## 4. Live terminal markers

Coders and agents can update MCP **immediately** by emitting
structured single-line markers to their own stdout. The bridge's
parser (`parse_mcp_markers` in
`scripts/bridge_snapshot_classifier.py`) extracts the LAST
occurrence per marker name on every tick, sanitises every value
through the existing redactor, and attaches the result to the
lane row's `lastMarkers` field.

**Marker format** — one line per marker, name + colon + space +
value. Values are capped at 280 characters and redacted by the
existing two-pass `redactString` rules (JWT, sk-, ghp_, AKIA,
whsec_, sb_secret_).

| Marker | Purpose | Cap |
|---|---|---|
| `MCP_RESULT:` | What just shipped (commit / feature / patch) | 280 |
| `MCP_BLOCKER:` | What is blocking progress now (drives `currentBlocker`) | 280 |
| `MCP_COMMIT:` | Short SHA of the latest meaningful commit | 80 |
| `MCP_TESTS:` | Short test summary (e.g. "14/14 passed", "tsc EXIT=0") | 280 |
| `MCP_NEXT:` | What this lane is about to do next | 280 |
| `AGENT_QA_RESULT_JSON:` | One-shot JSON object — `status` / `gate` / `platform` digest only ride into MCP; the full JSON stays local | 6 KB raw |

Examples:

```
MCP_RESULT: shipped FS-020 import parser at commit 70cd98b
MCP_TESTS: 14/14 synthetic rows OK; tsc EXIT=0
MCP_COMMIT: 70cd98b
MCP_NEXT: bundle gate centres into v21 build after Aaron approval

AGENT_QA_RESULT_JSON: {"status": "pass", "gate": "release_gate", "platform": "android"}
```

`AGENT_QA_RESULT_JSON` may also span multiple lines starting with
the label and a trailing `{`:

```
AGENT_QA_RESULT_JSON:
{
  "status": "partial",
  "gate": "release_gate",
  "platform": "ios"
}
```

**marker_hash** is a deterministic FNV-1a 32-bit hex of the
non-JSON marker values + the QA-digest fields.
`bridge-watch.sh` compares the hash across ticks and fires a
fresh snapshot whenever it changes — that is how the bridge
gets to **10–15 seconds drift** for marker-driven updates,
ahead of the 60-second heartbeat refresh.

**Sanitization rules.** No raw pane text reaches Supabase. The
bridge stores only the parsed marker values (after redact +
truncate) and the small QA digest (status / gate / platform) —
never the full JSON, never the surrounding pane content. The
Worker re-redacts every marker string before exposing it on
`agents[].lastMarkers`.

**Anti-rules for emitters.** Aaron must NOT type markers by
hand; coders / agents emit them as part of structured output.
Markers MUST NOT carry secrets, raw user health values, or
file paths outside the repo. The two-pass redactor catches
known token shapes; emitters are still on the hook for not
including the values in the first place.

## 5. Anti-rules

- Auto-snapshot MUST NOT be confused with auto-deploy. The
  watch script only writes to the connector tables that the
  manual snapshot already writes; it never deploys the
  Worker, never starts an EAS build, never pushes to
  GitHub.
- The `source` field is informational only. Worker-side
  logic must not branch on it (Supabase RLS already enforces
  the write boundary).
- `data/agent-status/lanes/.bridge-watch-state.json` is
  gitignored — it's runtime state, not repo state.
- The heartbeat does NOT replace the existing freshness
  window in the Worker. `staleReason` still goes through
  `FRESHNESS_WINDOW_MS_V2` in `cloudflare-worker/src/mcp-v2.ts`;
  the heartbeat just means the underlying row updates more
  often.

## 6. Tests

- `scripts/test-bridge-snapshot-classifier.py` covers
  `compute_state_change_at` (carry-forward / transition /
  first-observation / empty-now rejection) and
  `heartbeat_envelope` (transition / carry-forward / custom
  source). Existing fixture tests still green.
- `cloudflare-worker/test/test-mcp-v2-chatgpt-compat.ts`
  continues to pass — the `lastStateChangeAt` + `source`
  fields ride alongside `lastSeenAt`, no breaking change to
  the public agent shape.
- Smoke: `bridge:watch --once` runs the writer, prints the
  reason ("first-tick / no prior state"), and persists the
  watch-state cache; subsequent ticks without state changes
  no-op until the heartbeat interval elapses.

## 7. Cross-references

- `docs/CONNECTOR_SUPABASE_SCHEMA.md` — connector tables the
  bridge writes to.
- `docs/CONNECTOR_SANITIZATION_RULES.md` — redaction rules
  the writer applies.
- `docs/MCP_LONGTERM_ACCESS_ARCHITECTURE.md` § 6 Phase 1 —
  freshness window context.
- `docs/ADMINDEV_INSTALLED_PROOF_GAP.md` § 1 P1 — MCP
  freshness proof tile P1; this commit makes the underlying
  signal stay live.
