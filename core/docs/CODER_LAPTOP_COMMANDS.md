# Coder laptop commands — the full list

The single doc listing every command that runs on Aaron's
laptop. **Coders run all of these. Aaron runs none of them.**
Updated 2026-05-07 against
`CLAUDE-PHONE-ONLY-AUTOMATION-PLAN-01`.

If a workflow needs a laptop command that isn't in this list,
the workflow is wrong. Either the command joins this list
(via doc commit) or the workflow becomes phone-only.

## 0. Anti-rules

- **No "Aaron, run X locally and paste the output" prompts.**
  If a coder asks Aaron to run a laptop command, that's a
  workflow bug. Coder fixes it.
- **No "Aaron, can you check if the test passes" prompts.**
  Coder runs the test, reads the output, reports.
- **No surprise `wrangler deploy`.** Deploys are bundled per
  rule 7; Aaron must have approved the bundle before deploy
  fires.
- **No `git push --force` without explicit Aaron approval.**
  Force pushes can overwrite upstream work; same rule applies
  to `git reset --hard` and any branch deletion.
- **No commands that require interactive input / TTY.** Every
  command in this list runs non-interactively. If a tool prompts
  (e.g. `git rebase -i`), the coder uses a non-interactive
  alternative or scripts the inputs.

## 1. End-of-task cadence (rule 12)

After every meaningful unit of work (commit landed, doc batch
shipped, test sweep complete), the coder MUST run **at least
one** of:

```bash
# preferred — covers all four canonical-store tables in one go
npm run bridge:snapshot
```

OR equivalent Supabase MCP `execute_sql` writes when the
laptop bridge isn't reachable from the session (e.g. Claude
session running off a remote shell).

OR a single-table refresh via `/mcp/v2`:

```bash
# light refresh — single agent's status
TOKEN="$(grep ATHLETE_MEMORY_API_TOKEN cloudflare-worker/.dev.vars | cut -d= -f2)"
curl -sS -X POST \
  -H "x-athlete-memory-token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"project.update_work_status","arguments":{"agent":"claude","status":"<status>","task":"<task>","summary":"<≤140 char>","branch":"main","commit":"<sha>"}}}' \
  https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/v2
```

Reading `staleReason: 'no_writeback'` from
`project.get_current_state` after a coder claims to have
finished work is a workflow bug; coder re-runs the cadence.

## 2. Bridge & MCP

| Command | What it does | When to run |
|---|---|---|
| `npm run bridge:snapshot` | Capture both tmux panes, sanitise, upsert to all four `connector_*` tables. | End of every meaningful task; before reporting completion. |
| `npm run bridge:verify` | Validate that the bridge artefacts are well-formed and Supabase target is reachable. | After bridge / connector schema / Supabase env changes; when MCP looks stale and § 1 doesn't fix it. |
| `npm run mcp:test:public-redaction` | Asserts public-safe MCP outputs carry no admin fields. | Whenever `cloudflare-worker/src/mcp-public.ts` or `mcp-v2.ts` redaction logic changes. |
| `npm run mcp:test:v2-live` | End-to-end live `/mcp/v2` shape test. | Spot-check live shape; before any Worker deploy. |
| `npm run mcp:test:live` | Legacy `/mcp/public` live test. | When `/mcp/public` shape changes. |
| `npm run cc:test:live` | `/api/control_centre` admin route test. | When `/api/control_centre` shape changes. |
| `npm run rules:test` | Operating-rules contract test (count + ids + doc/code parity). | When `OPERATING_RULES.md` or `cloudflare-worker/src/operating-rules.ts` changes. |

## 3. Worker code

| Command | What it does | When to run |
|---|---|---|
| `cd cloudflare-worker && npx tsc --noEmit` | Worker typecheck. | Before any worker code commit. |
| `cd cloudflare-worker && wrangler deploy` | Push the Worker to production. | When worker code changes AND Aaron approved the bundle (rule 7) AND tests/typecheck pass. **Never on speculative changes.** |
| `cd cloudflare-worker && wrangler tail` | Live log stream from the deployed Worker. | Debugging a live route; Codex / Claude only, never Aaron. |
| `cd cloudflare-worker && wrangler secret put <NAME>` | Rotate / set a Worker secret. | When a vendor secret needs rotation AND Aaron has pasted the new value into the active session. |

`wrangler deploy` defaults are good. No `--name`, no
`--env`, no `--keep-vars` overrides unless documented
elsewhere with a reason.

## 4. Mobile app

| Command | What it does | When to run |
|---|---|---|
| `cd apps/mobile && npx tsc --noEmit` | Mobile typecheck. | Before any mobile code commit. |
| `cd apps/mobile && npm run lint` (if defined) | Lint / formatter run. | Before any mobile code commit if the script exists. |
| `cd apps/mobile && npm run test` (if defined) | Unit tests. | Before any meaningful logic commit. |
| `cd apps/mobile && npx expo start` | Local dev server for emulator / simulator. | **Dev-loop only.** Coder uses for local verification; never produces a release artefact. |

**No `eas build`** in this list. EAS builds run only when
Aaron has explicitly approved per rule 7. The exact command
when the time comes lives in `docs/IOS_TESTFLIGHT_AUTOMATION_SETUP.md`
and `docs/PLAY_SUBMIT_SETUP.md`; coder runs it from the
laptop on Aaron's phone-tap approval.

## 5. Git

| Command | What it does | When to run |
|---|---|---|
| `git status --short` | Check working-tree state. | Whenever choosing what to stage. |
| `git diff [HEAD]` | Inspect changes. | Before every commit. |
| `git add <specific paths>` | Stage specific files. | Before commit. **Never `git add .` or `git add -A`** — it can pick up secrets / `.env` files. |
| `git commit -m "..."` | Land work. | When the bundle is complete. Use a HEREDOC for multi-line messages. |
| `git push origin main` | Publish. | After commit; default scope `main`. |
| `git log --oneline -n 10` | Recent commits. | Diagnostic. |
| `git fetch && git status` | Check upstream state. | Before push if you suspect parallel work. |

Forbidden by default (require explicit Aaron approval):
- `git push --force` (any variant)
- `git reset --hard <other-branch>`
- `git branch -D <branch>`
- `git checkout -- <path>` (discards working changes)
- `git rebase -i` (interactive; use non-interactive alternatives)
- `git config --global` (touches user config)
- `git commit --amend` to a published commit (rewrite history)

## 6. Supabase / DB

The Supabase MCP is the canonical writer for one-off rows.
Direct `psql` / migration runs:

| Command | What it does | When to run |
|---|---|---|
| Supabase MCP `execute_sql` | Run a one-off SQL statement against the project. | Bridge writeback when `bridge:snapshot` isn't usable; refreshing canonical-store rows; small data fixes. |
| `cd supabase && supabase migration up` (if local CLI is configured) | Apply pending migrations to a local Supabase. | Local development only. **Never against production from this laptop without Aaron's go-ahead.** |
| `cd supabase && supabase db reset` | Wipe and re-seed local DB. | Local development only. **Forbidden against production.** |

Production migrations land via `apply_migration` Supabase MCP
tool **only** when:
- The migration SQL is reviewed in a PR or doc commit.
- Aaron has explicitly approved.
- The change is non-destructive (no DROP TABLE / DROP COLUMN
  on rows that have data).

## 7. Health / WHOOP / Polar / 3rd-party vendor commands

Any vendor-console step (WHOOP developer console, Polar
AccessLink dashboard, Apple App Store Connect, Google Play
Console) runs **either** on Aaron's iPhone via the vendor
web app, **or** in a coder session with Aaron-pasted
credentials that go directly into `wrangler secret put` and
never into a doc / commit / log.

**No coder pastes vendor credentials into the repo.** No
exception.

## 8. When something goes wrong

| Symptom | Coder action (not Aaron's) |
|---|---|
| `bridge:snapshot` errors | Read the error; if env-missing, list which env vars are missing; if Supabase reachable but write rejected, run `bridge:verify`; document the fix in `docs/MCP_CANONICAL_STATE.md`. Never ask Aaron to "check Supabase". |
| Worker deploy fails | Read `wrangler` output; fix the underlying cause (missing secret, schema mismatch, bundle size); re-run the local typecheck before retrying. Never ask Aaron to "check Cloudflare". |
| `tsc --noEmit` errors | Read the type errors; fix at root; re-run; commit. Never `// @ts-ignore` to "make it pass". |
| Live test fails | Diff the response shape against the test expectations; fix the worker if shape is wrong; fix the test if the shape change is intentional + documented. |
| Pre-commit hook fails | Read the hook output; fix the underlying issue (lint, format, secret-scan); re-stage; new commit. **Never `--no-verify`.** |
| `git push` rejected | Run `git fetch`, `git status`; rebase or merge upstream; re-push. **Never `--force`.** |
| MCP shows `staleReason: 'no_writeback'` | Run § 1 cadence; check Supabase connectivity. |

## 9. Cross-references

- `docs/PHONE_ONLY_AUTOMATION_PLAN.md` — the workflow these
  commands serve.
- `docs/OPERATING_RULES.md` — rule 12 (this doc's parent
  rule).
- `docs/MCP_CANONICAL_STATE.md` — when commands intersect with
  MCP state.
- `docs/UNIFIED_MCP_PLAN.md` § 15 — the write/read contract.
- `docs/IOS_TESTFLIGHT_AUTOMATION_SETUP.md` /
  `docs/PLAY_SUBMIT_SETUP.md` — EAS build commands (gated by
  rule 7).
- `docs/CONNECTOR_SECURITY_MODEL.md` — secret hygiene that
  every command in this list must respect.
