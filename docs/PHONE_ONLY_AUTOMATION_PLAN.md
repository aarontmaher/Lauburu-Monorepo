# Phone-only automation plan

The single doc that describes how Aaron runs Lauburu development
from his iPhone only. Updated 2026-05-07 against
`CLAUDE-PHONE-ONLY-AUTOMATION-PLAN-01`.

This is **spec + workflow doc**. No EAS build, no app
version/build bump, no mobile UI changes from this commit.
Implementation references existing tools that already ship.

## 0. The promise

Aaron approves from iPhone. Coders (Claude / Codex) run every
laptop command. MCP stores live status. Agent audits. Mobile
Admin/Dev displays the result. The only times Aaron touches a
laptop are the explicit "manual Aaron steps" in § 5.

## 1. Roles

| Role | Surface | Reads | Writes | Authorises |
|---|---|---|---|---|
| **Aaron (phone-only)** | iPhone Admin/Dev tab + iMessage / ChatGPT | live MCP state via the public connector + admin/dev cards | approval taps only | EAS builds, FS-XXX promotions, secret pastes |
| **Claude Code** | laptop tmux pane `lauburu` | full repo + Supabase MCP `execute_sql` + `/mcp/v2` admin tools | docs, code, MCP rows via `project.update_work_status` or Supabase MCP, `bridge:snapshot`, git commits/pushes, `wrangler deploy` (when authorised) | nothing — proposes, never approves |
| **Codex** | laptop tmux pane `codex-lauburu` | same as Claude in its own lane | same as Claude in its own lane (no overlap with Claude's in-flight files) | nothing |
| **Agent (functional auditor)** | spawned via existing audit prompt templates | Codex / Claude commit + repo state | comment on FS-XXX status (`Agent-confirmed` / `not confirmed`) | nothing — confirms or declines |
| **MCP / control-centre** | `/mcp/v2` + `/api/control_centre` | the canonical store | bridge writes via `bridge:snapshot` or `project.update_work_status` | nothing — surfaces only |
| **Mobile Admin/Dev** | iPhone Admin tab | `/api/control_centre` (admin token) | tap approvals → bridge action queue (planned, see § 6) | mediates Aaron's approvals |

## 2. The phone-only workflow loop

```
Aaron opens the Lauburu app → Admin/Dev tab.
  ↓ reads live MCP state (priority, lanes, blockers, build state)
  ↓
Aaron sees a coder is "Agent-confirmed, ready for Aaron approval".
  ↓ taps Approve in Admin/Dev (or types "approve FS-008" in ChatGPT)
  ↓
Approval lands in the canonical store via Supabase write.
  ↓
Coder (Claude / Codex) detects the approval on next bridge poll
  or when picked up by the next prompt.
  ↓
Coder executes the laptop work — code, tests, bridge:snapshot,
git commit, git push, wrangler deploy if needed.
  ↓
Coder calls project.update_work_status (writeback) to flip lane
to "implementation-complete-awaiting-agent-confirmation".
  ↓
Agent runs functional audit; updates lane to "Agent-confirmed".
  ↓
Aaron sees the green "Agent-confirmed" chip in Admin/Dev.
  ↓
If on-device verification is needed, Aaron opens the next tester
build (already on TestFlight / Play Internal).
  ↓
Aaron approves "Built/tester-ready" → loop restarts on next batch.
```

The loop closes without Aaron touching a terminal, copy-pasting a
SHA, or screenshotting tmux. He reads, taps, types in ChatGPT.

## 3. MCP writeback — current status

### 3.1 What exists today

The writeback path is **fully implemented**, just not always
invoked:

- `cloudflare-worker/src/mcp-v2.ts` exposes
  `project.update_work_status` (admin-token gated). Sanitises
  text, redacts secrets, maps the four-status build-readiness
  ladder to the canonical lane enum, upserts to
  `connector_work_status` + `connector_coder_lanes`. Compatibility
  alias `update_work_status` covers consumers that assume the
  unprefixed name.
- `scripts/bridge-snapshot-lanes.sh` (`npm run bridge:snapshot`)
  reads the two tmux panes (`lauburu` Claude + `codex-lauburu`
  Codex), sanitises per
  `docs/CONNECTOR_SANITIZATION_RULES.md`, and upserts to
  `connector_work_status`, `connector_coder_lanes`,
  `connector_handoff`, and `connector_terminal_summary` directly
  via Supabase REST (service-role key in env).
- `cloudflare-worker/test/test-mcp-v2-work-status-write.ts` locks
  in the contract: unauthenticated calls fail soft, secret-shaped
  text is redacted before storage, and the
  implementation-complete label maps to `needs_review`.
- The Supabase MCP (`mcp__claude_ai_Supabase__execute_sql`)
  available in Claude / Codex sessions writes the same rows when
  the bridge isn't run.

### 3.2 Why MCP often shows `staleReason: 'no_writeback'`

The freshness window is 10 min. After 10 min of no Supabase
write, `project.get_current_state.freshness.staleReason` flips to
`no_writeback`. This is **not** a code defect; it is an
**operational cadence gap**: nobody is running `bridge:snapshot`
or `project.update_work_status` between commits, so the row's
`generated_at` ages past the window.

### 3.3 The fix: cadence, not code

Rule 12 (see `docs/OPERATING_RULES.md`) makes the cadence
explicit. After every meaningful unit of coder work, the coder
MUST refresh the canonical store via:

1. `npm run bridge:snapshot` (preferred — covers all four tables
   in one command; safe to run at any time), OR
2. Supabase MCP `execute_sql` against the relevant rows (when
   the bridge environment isn't accessible from the session,
   e.g. ChatGPT-side coding), OR
3. `tools/call name="project.update_work_status"` against
   `/mcp/v2` with an admin token (when only a single agent's
   status needs flipping; lighter than a full snapshot).

End-of-task is non-negotiable. Mid-task refreshes during long
runs are encouraged but optional.

### 3.4 What stays manual for Aaron (writeback)

Nothing. Aaron is never the writer. If the bridge is broken or
the Supabase MCP is unavailable mid-session, the coder
**investigates and fixes** (rule 11 fallback) rather than
asking Aaron to refresh.

## 4. Coder laptop commands — the full list

Codified in `docs/CODER_LAPTOP_COMMANDS.md`. Summary:

| Concern | Command | Who runs it | When |
|---|---|---|---|
| Refresh MCP / control-centre | `npm run bridge:snapshot` | coder (laptop) | end of every meaningful task |
| Verify bridge health | `npm run bridge:verify` | coder (laptop) | when Aaron reports MCP looks stale and the cadence in § 3.3 doesn't fix it |
| Worker typecheck | `cd cloudflare-worker && npx tsc --noEmit` | coder (laptop) | before any worker commit |
| Worker deploy | `cd cloudflare-worker && wrangler deploy` | coder (laptop) | when worker code changes AND Aaron has approved the deploy AND the change is bundled per rule 7 |
| Run rules contract test | `npm run rules:test` | coder (laptop) | when `OPERATING_RULES.md` or `cloudflare-worker/src/operating-rules.ts` changes |
| Run public-redaction test | `npm run mcp:test:public-redaction` | coder (laptop) | when `cloudflare-worker/src/mcp-public.ts` or `mcp-v2.ts` redaction logic changes |
| Run live MCP test | `npm run mcp:test:v2-live` (or `mcp:test:live`) | coder (laptop) | spot-check `/mcp/v2` end-to-end |
| Run control-centre live test | `npm run cc:test:live` | coder (laptop) | when `/api/control_centre` shape changes |
| Mobile typecheck | `cd apps/mobile && npx tsc --noEmit` | coder (laptop) | before any mobile commit |
| Git commit | `git add <specific files> && git commit -m "..."` | coder (laptop) | when work is ready to land |
| Git push | `git push origin main` | coder (laptop) | after commit, default scope `main` |

Aaron does not run any of these. If Aaron is asked to "verify
locally" something a coder could verify, that's a workflow bug.
Coder fixes the workflow.

## 5. Remaining manual Aaron steps

These are the irreducible steps. Each is on Aaron's iPhone or in
ChatGPT, never on a laptop.

| # | Step | Where | Why irreducible |
|---|---|---|---|
| 1 | **Approve / defer FS-XXX candidates** (e.g. FS-008 WHOOP migration) | Admin/Dev tap or ChatGPT typed "approve FS-008" | rule 5 + rule 7: only Aaron approves promotions / EAS builds |
| 2 | **Approve EAS builds** | Admin/Dev tap "Approve build" | rule 7: default is no build |
| 3 | **Tester-device verification** | iPhone (TestFlight) / Android (Play Internal) | rule 8: only Aaron-tested-on-device qualifies as fully done |
| 4 | **Type WHOOP / Polar / 3rd-party secrets** when a vendor migration ships | a private connector path TBD; today, Aaron pastes once into a one-off coder session that runs `wrangler secret put` immediately | rule 7 + WHOOP migration § M.5: secrets never in commits / docs / app UI |
| 5 | **Two-factor / vendor-console steps Aaron alone can do** (WHOOP redirect URI update, App Store / Play Console publish flips) | the vendor's web console on iPhone | vendor-side ownership |
| 6 | **Decide between two coder-proposed alternatives** when the doc isn't decisive | text reply in ChatGPT or "decision" tap in Admin/Dev | judgement calls only Aaron makes |
| 7 | **Confirm "I tested it on my phone and the readings match my subjective experience"** for health-source promotion | Admin/Dev "approved_done" tap or ChatGPT typed confirmation | rule 9 + audit doc § 1.4.d: never auto-promoted |

Anti-rule: **a coder proposes; Aaron approves**. Coders never
auto-approve their own work. Coders never edit
`docs/FEEDBACK_SUGGESTIONS.md` to add an `approved_done` line —
that line comes from Aaron.

## 6. Admin/Dev requirements for the phone control centre

See `docs/MCP_PHONE_CONTROL_CENTRE.md` § "Phone control-centre
Admin/Dev requirements" for the surface contract.

In short, the iPhone Admin/Dev tab needs:

- **Live MCP read** — `project.get_current_state` first call,
  `/api/control_centre` for full detail (admin token already in
  the device).
- **Freshness chip** — visible at the top: green if
  `staleReason: 'fresh'`, amber if `'no_writeback'`, red if
  `'env_missing'`. Tapping the chip explains the meaning.
- **Per-lane tile** — Claude + Codex side by side with status
  chip + last-seen timestamp + one-line summary.
- **Approval queue** — list of items in
  "Agent-confirmed, ready for Aaron approval" status, each with
  a tap-to-approve button.
- **Build queue** — items in "Aaron-approved for EAS build" with
  a tap-to-trigger-build button (gated; planned, depends on the
  bridge action queue at § 7).
- **Pending FS-XXX** — list of candidates needing Aaron approval
  / defer.
- **Manual steps** — § 5 list of "things only Aaron can do",
  highlighted when relevant.

## 7. Bridge action queue (planned, not in this commit)

Tap-to-trigger from phone executing on laptop is Stage 5 of
`docs/LOCAL_BRIDGE_WORKFLOW_PLAN.md`. Today's loop relies on the
coder polling for Aaron's approval (in the next prompt) rather
than a phone-side trigger. The action queue stays planned-only
until:

1. Tailscale daemon ships on the laptop with biometric-auth
   reachability from phone.
2. Each action is in `docs/LOCAL_BRIDGE_COMMAND_ALLOWLIST.md`
   with explicit input / effect / rejection criteria.
3. Aaron explicitly approves the bridge daemon enabling.

Until then, the workflow at § 2 is what runs. Coders ask the
next prompt; Aaron approves in the next prompt; loop continues.

## 8. Anti-rules

- **No coder-side EAS build dispatch without Aaron approval.**
  Rule 7. The bridge action queue MUST refuse builds without an
  explicit approval row from Aaron.
- **No phone-side `wrangler deploy` ever.** Worker deploys are
  laptop-only because they require local secrets the phone never
  sees.
- **No phone-side `git push --force` ever.** Force pushes
  require explicit Aaron approval per the harness rules; they
  are not in the bridge allowlist.
- **No "fully done" without Aaron + tester device.** Rule 8.
  Coders MUST use the four-status sequence
  (Implementation-complete → Agent-confirmed → Aaron-approved →
  Built/tester-ready).
- **No silent rule promotions.** Rule 12 was added via this
  doc + a paired commit per the operating-rules edit policy.
  Future rule additions follow the same paired-edit gate.

## 9. Cross-references

- `docs/OPERATING_RULES.md` — the 12 rules; rule 12 makes
  laptop-command discipline explicit.
- `docs/CODER_LAPTOP_COMMANDS.md` — full command list with
  cadence.
- `docs/MCP_PHONE_CONTROL_CENTRE.md` — phone connector setup +
  Admin/Dev surface requirements.
- `docs/MCP_CANONICAL_STATE.md` § "Tool inventory" — the
  public/admin tool split + write tool location.
- `docs/UNIFIED_MCP_PLAN.md` § 15 — write/read contract +
  auth model.
- `docs/LOCAL_BRIDGE_WORKFLOW_PLAN.md` — the bridge daemon /
  action queue plan.
- `docs/LOCAL_BRIDGE_COMMAND_ALLOWLIST.md` — currently allowed
  bridge actions.
- `docs/BACKLOG_AUTOMATION_SYSTEM.md` § "EAS build cost
  control rule" — the cost gate that closes the loop.
