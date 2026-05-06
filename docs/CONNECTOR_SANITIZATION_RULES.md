# Connector sanitization rules

The exact rules every writer (tmux bridge, owner-tap edit,
mobile-app audit-event push) must apply before a string lands
in any of the five connector state objects defined in
`docs/CHATGPT_CONNECTOR_STATE_CONTRACT.md`.

The reader (ChatGPT Connector, Claude MCP, Codex agent) sees
the post-sanitization payload only; it never has access to the
raw tmux pane or terminal log.

Companion to:
- `docs/CHATGPT_CONNECTOR_STATE_CONTRACT.md` (state contract)
- `docs/CONNECTOR_SECURITY_MODEL.md` (invariants 1–10)
- `chat-app/src/server/types/connector.ts` (TS interfaces)
- `chat-app/src/server/routes/athleteMemory.ts`
  `redactTokenLikeSubstrings()` (existing implementation,
  commit `b1b88ce`)

Updated 2026-05-06.

## Two-pass redactor — canonical implementation

The existing `redactTokenLikeSubstrings()` in `athleteMemory.ts`
is the single implementation. New surfaces import it; they MUST
NOT re-implement the regex set.

### Pass 1 — sentinel-tag labelled values that must survive

Some short hex / alphanumeric values are intentional context
(commit SHAs, version tags, build numbers in human-readable
sentences). Pass 1 finds labels of the form
`(?:^|[^A-Za-z0-9_])(?<label>[a-z_]+)\s*[:=]\s*(?<value>[A-Za-z0-9.\-_]+)`
and tags the value with a sentinel so Pass 2 won't match it.

Allowed labels (case-insensitive after lower-casing):

| Label | Example matched value |
|---|---|
| `commit` | `1234567` |
| `commit_hash` | `1234567890abcdef` |
| `sha` | `abc1234` |
| `head` | `dadde0e` |
| `ref` | `main` |
| `branch` | `release/v17` |
| `version` | `0.1.0` |
| `build` | `18` |
| `build_number` | `18` |
| `version_code` | `17` |
| `tag` | `v17.0.0` |
| `prompt_id` | `CLAUDE-...-01` |
| `lane` | `claude` |
| `run_id` | `25417977756` |
| `submission` | `94cee638-97b3-...` |
| `eas_build` | `b05edd9a-...` |
| `expo_build_id` | `b05edd9a-...` |

Snake_case label boundary uses `(?:^|[^A-Za-z0-9_])` instead of
`\b` because `\b` does not reset on `_`. This is the bug fixed
by commit `b1b88ce` and must not regress.

Sentinel form: `\u0000PRESERVE_<idx>\u0000`. Pass 2 ignores
`\u0000`-bounded substrings; the final replace step swaps
sentinels back to their original values.

### Pass 2 — regex strikes for token-shaped substrings

Run in the order below (first match wins per substring).
All replace with `<redacted>`.

| # | Pattern | Targets |
|---|---|---|
| 1 | `[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}` | UUIDs (placed first; most submission IDs are UUIDs which we surface intentionally only via labelled fields) |
| 2 | `eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+` | JWTs (Supabase access tokens, etc.) |
| 3 | `sk-[A-Za-z0-9_\-]{20,}` | OpenAI / Anthropic-style keys |
| 4 | `ghp_[A-Za-z0-9]{30,}` | GitHub personal-access tokens |
| 5 | `gho_[A-Za-z0-9]{30,}` | GitHub OAuth tokens |
| 6 | `ghs_[A-Za-z0-9]{30,}` | GitHub server tokens |
| 7 | `whsec_[A-Za-z0-9]{20,}` | Webhook signing secrets |
| 8 | `AKIA[0-9A-Z]{16}` | AWS access key IDs |
| 9 | `xox[abprs]-[A-Za-z0-9\-]{10,}` | Slack tokens |
| 10 | `(?<![A-Za-z0-9])[A-Fa-f0-9]{32,}(?![A-Za-z0-9])` | Generic hex 32+ (HMAC outputs, hex-encoded secrets) |
| 11 | `(?<![A-Za-z0-9+/=])[A-Za-z0-9+/=]{24,}(?![A-Za-z0-9+/=])` | Generic base64 24+ (catch-all for raw secrets) |

UUID rule: the catalogue (#1) covers Play submission IDs, EAS
build IDs, and TestFlight submission IDs. These are intentional
surface fields. To preserve them, **callers must put UUIDs in
labelled fields** (e.g. `eas_build_id: <uuid>` in the structured
payload), not in free-text strings. The redactor then sees the
labelled form and Pass 1 preserves it.

Free-text usage of a UUID (e.g. someone writing "the build was
1234abcd-5678-..." in a plain summary) gets redacted on
purpose — that's the desired behaviour.

## File-path masking rules

File paths are useful context but can leak directory structure
beyond the repo. Apply these rules before serializing any
`dirtyFiles[]`, `doNotTouch[]`, or in-summary path mention:

1. **Repo-relative only.** Strip everything up to and including
   the working-directory prefix (`/Users/aaronmaher/LauburuGrapplingMap-mobile/`).
   `/Users/aaronmaher/LauburuGrapplingMap-mobile/apps/mobile/app/_layout.tsx`
   → `apps/mobile/app/_layout.tsx`.
2. **No home expansions.** Reject any string starting with `/Users/`
   or `~` after step 1; replace with `<host_path>`.
3. **No build artefacts.** Drop entries under
   `node_modules/`, `.expo/`, `ios/build/`, `android/.gradle/`,
   `android/build/`, `android/app/build/`,
   `apps/mobile/ios/Pods/`. These are generated, not signal.
4. **No Cursor / IDE state paths.** Drop entries under
   `.cursor/`, `.vscode/`, `.idea/`.
5. **No secret-shaped filenames.** If the basename matches the
   regex `(?:\.env|\.env\.local|\.env\.production|secrets?\.json|google-services-key\.json|.*\.pem|.*\.p12|.*\.keystore)`,
   drop the entry entirely (don't even surface "redacted").
6. **No scratch dirs.** Drop entries under
   `data/private-athlete-memory/` (per-user disk store) and
   `data/agent-queue/` (planned). The bridge-driven
   `data/agent-status/<lane>.json` is allowed.

## Summary length cap

| Field | Cap | Rationale |
|---|---|---|
| `lastSummary` (CoderLaneRow) | 1200 chars | Matches `MARK_AGENT_DONE` summary cap. |
| `summary` (TerminalSummaryEntry) | 1200 chars | Same. |
| `verification` (TerminalSummaryEntry) | 240 chars | Matches existing audit field. |
| `nextAction` (TerminalSummaryEntry) | 240 chars | Same. |
| `lastCommitMessage` (WorkStatus) | 200 chars | Git subject convention. |
| `currentPriority` / `currentBlocker` / `nextAction` (WorkStatus) | 280 chars | Single-tweet sized; fits in-app card. |
| `manualSteps[]` (Handoff) | 200 chars per step, 10 steps max | Bounded checklist. |
| `safeToBuildReason` (Handoff) | 280 chars | Single sentence. |

Truncation rule: cut at a word boundary (last space before the
cap), append a single `…` character. Never cut mid-token-shaped
substring before redaction — redact first, then truncate.

## Lane-status detection from tmux output

The Stage 1 bridge (`scripts/bridge-snapshot-lanes.sh`, planned)
maps tmux pane state to a `LaneStatus` value using this
deterministic ladder. First match wins, top to bottom.

| Detected condition (in pane buffer) | Mapped status |
|---|---|
| Last line ends with a known shell prompt **and** previous 30 lines contain `BLOCKED:` / `BLOCKER:` / `cannot continue` / `please clarify` / `awaiting owner` | `blocked` |
| Last line ends with a known shell prompt **and** previous 30 lines contain `NEEDS_USER:` / `awaiting input` / `confirm before proceeding` | `needs_user` |
| Last line ends with a known shell prompt **and** previous 30 lines contain `NEEDS_REVIEW:` / `please review` / `awaiting audit` | `needs_review` |
| Last line ends with a known shell prompt **and** the most recent commit subject in the buffer matches `done\|complete\|landed\|merged` and `git status` shows clean | `done` |
| Process is producing output within the last 5s (pane mtime fresh, last line not a prompt) | `working` |
| Pane is silent ≥ 30s **and** last line is a known shell prompt | `idle` |
| Pane buffer is empty **or** unreadable | `idle` (NEVER fabricate working/done) |

Known shell prompts (configurable, defaults below):

```
\$\s*$
%\s*$
>\s*$
zsh:\s\S+#\s*$
```

Customisations land in `scripts/bridge-snapshot-lanes.sh` config
header, never in connector code.

The detector MUST NOT scrape `git status` itself — it should
read `git status --short --no-renames` separately and compare
against the lane's owned-paths heuristic per
`BACKLOG_AUTOMATION_SYSTEM.md` Lane 1/2/3 mapping. Mixing
"what the pane looks like" with "what the repo looks like" is
exactly the brittle signal that creates false `done`s.

## Owner-side controls

The owner can override any auto-detected lane status by typing
into the lane's tmux session a single line:

```
LANE_STATUS_OVERRIDE: blocked  reason="awaiting WHOOP screenshot"
```

The bridge picks up the override line, applies it to the next
snapshot, and clears it. Override lines are themselves passed
through Pass 1 + Pass 2 redaction before persisting.

## What the redactor MUST NOT do

- Strip commit SHAs that appear in labelled positions. Commit
  `b1b88ce` made this work; regressions break audit traceability.
- Drop the entire string when it can't decide. Always emit
  `<redacted>` in place; never emit empty.
- Run on bytes outside the structured payload — it is a string
  redactor, not a binary scrubber.
- Be re-implemented per route. One redactor; many callers.

## What the bridge MUST NOT do

- Capture stdin. The bridge reads pane output only.
- Persist raw pane buffers to disk. Only the post-redaction,
  post-truncation `lastSummary` lands in `data/agent-status/`.
- Send any data over WAN. localhost + Tailscale only.
- Execute any string from the pane. Lane-status overrides are
  parsed for two fixed fields (`blocked|working|idle|...` enum
  + an optional `reason` quoted string); anything else is
  ignored.
- Promote a lane to `done` based solely on a coder's claim. The
  detector requires both the pane-claim signal AND a clean
  `git status` for the owned paths.
