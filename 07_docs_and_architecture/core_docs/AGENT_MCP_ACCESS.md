# ChatGPT Agent + Grappling Map MCP Core — access spec

The ChatGPT custom MCP connector documented in
`docs/CHATGPT_CONNECTOR_SETUP.md` works inside **normal ChatGPT
chats**. Aaron has observed that it does **NOT** work inside
**ChatGPT Agent** runs (Agent reports "MCP Core not callable"
and stops). This doc captures why, how to verify, what to do
right now, and what the ideal future state is.

This is doc-only. No app code. No Worker code change. No EAS
build.

## 1. Observed difference

| Surface | MCP Core callable? | Notes |
|---|---|---|
| Normal ChatGPT chat (with custom connector enabled) | YES | `project.get_current_state` etc resolve and return live state. Tools/list returns 25 tools (after the `/mcp/v2` website-proxy split — see `docs/CHATGPT_CONNECTOR_SETUP.md` § 8). |
| ChatGPT Agent run (same account, same connector enabled) | NO | Agent reports MCP Core not callable. Agent stops or falls back to its built-in connectors (Gmail / Drive / GitHub / Calendar). |
| Same chat, switched to Agent mid-session | UNKNOWN — needs Aaron verification | See § 3 verification matrix. |

The strict reading of operating rule 11 (MCP-first start) is
that an Agent unable to reach MCP Core MUST stop and surface
the unavailability, NOT fall back to memory or screenshots
unless Aaron explicitly approves a "fallback mode". The
observed behaviour ("Agent stops") is consistent with rule 11
honoured.

## 2. Root cause candidates

Numbered for reference in the verification matrix below. The
most likely explanation is (1) — Agent runs in a different tool
surface that doesn't inherit arbitrary custom MCP servers.

1. **Agent runtime uses a curated connector surface** — the
   ChatGPT Agent product (autonomous browsing / deep research)
   may only support a curated set of "official" connectors
   (Gmail, Drive, GitHub, Calendar, Linear, Slack, etc.) and
   not arbitrary custom MCP servers. Custom MCP ≠ Agent-eligible
   connector.
2. **Connector enablement is per-feature, not global** —
   even if "enabled" in Settings → Connectors, Agent may need
   a separate enablement step (e.g. selected in the Agent
   composer's connector picker).
3. **Custom MCP requires "publish" before Agent picks it up** —
   if the Lauburu MCP connector is in "Drafts" / Developer
   Mode, Agent may only see published connectors. Normal chat
   may be more permissive about Drafts.
4. **Old chat session tool-list snapshot** — if the connector
   was added AFTER the chat was opened, the chat sees the
   connector but Agent (forked from that chat) may not. Per
   `docs/CHATGPT_CONNECTOR_SETUP.md` § 10.2 (fresh chat
   required) — same root cause class, different surface.
5. **Tool-picker cap differs in Agent** — the ~30-tool picker
   cap in chat may be smaller or different in Agent. Even if
   MCP is enabled, the specific tools may be invisible to
   Agent.
6. **Auth-header forwarding gap** — Agent may not forward
   custom-connector headers. Our `/mcp/v2` is No Auth for the
   public-safe surface, so this shouldn't matter — but worth
   confirming.
7. **Plan-tier gating** — Agent on certain plan tiers may
   exclude custom MCP. (As of 2026-05, Plus / Pro / Team /
   Enterprise have differing custom-MCP eligibility.)
8. **Origin / referer header check on Worker** — unlikely
   here (our Worker doesn't gate on Origin), but ruling it
   out is cheap.
9. **OAuth requirement** — some "Agent-eligible" connectors
   are gated on OAuth flow rather than No Auth or Bearer.
   Custom MCP servers without OAuth might be filtered out.

## 3. Verification matrix

Aaron runs each row; record YES / NO in the result column. The
combination tells us which root cause is real.

| # | Setup | Tools listed in surface | MCP Core callable? | Inferred root cause |
|---|---|---|---|---|
| V1 | Fresh normal chat, Lauburu MCP enabled, no Agent | ≤30 of the 25 core | YES expected | Baseline (already known) |
| V2 | Fresh Agent run from settings, Lauburu MCP enabled, no chat first | — | TBD | If NO: confirms Agent runtime curated surface (cause 1) |
| V3 | Existing chat (V1) → switch to Agent within same session | — | TBD | If V1 worked + V3 fails: cause 1 or cause 4 |
| V4 | Fresh Agent run with **Developer Mode ON** in account settings | — | TBD | If V2 fails + V4 works: cause 3 (publish required) |
| V5 | Fresh Agent run with ONLY Lauburu MCP enabled (Gmail / Drive / GitHub disabled) | — | TBD | If V2 fails + V5 works: cause 5 (picker cap conflict) |
| V6 | Fresh Agent run, paste rule 11 prompt + ask "list connectors / tools you see" | reported list | observed | Diagnostic — what does Agent actually see? |
| V7 | Try to add a NEW connector inside Agent (if UI allows) | — | TBD | If only Agent-side connector add resolves Agent calls: cause 2 (per-feature enablement) |
| V8 | Curl the Worker from local laptop while Agent claims unavailable | 200 OK | YES | Confirms Worker is fine — issue is ChatGPT-side |

For each row Aaron records: **(date, ChatGPT plan, account, model used, connector list visible, MCP Core callable yes/no, tools/list count if any, freeform notes)**.

## 4. Exact Aaron steps

Run V1 → V8 in order. Skip rows where the prerequisite is impossible (e.g. V7 if Agent-side connector add UI doesn't exist on Aaron's plan tier).

### V1 — Baseline (normal chat)

1. Open chatgpt.com, `+` → New chat.
2. Settings → Connectors — confirm **Lauburu MCP (unified)** is enabled.
3. In the chat composer's connector picker, enable Lauburu MCP for this chat.
4. Send: "Use the `project.get_current_state` tool from Lauburu MCP."
5. Expected: ChatGPT calls the tool, returns a payload with `freshness`, `agents`, `repo` etc.
6. Record: V1 → YES (or note the failure mode).

### V2 — Fresh Agent (no chat first)

1. From chatgpt.com home → New Agent run (or wherever Agent UI is — Tasks / Run / Agent button).
2. Confirm Settings → Connectors still shows Lauburu MCP enabled.
3. In the Agent run, send the same first message: "Use the `project.get_current_state` tool from Lauburu MCP."
4. Expected: TBD. Record YES/NO.
5. If NO: copy Agent's exact "MCP Core not callable" error text (verbatim, redacting any PII).

### V3 — Mid-session switch to Agent

1. Continue from V1's chat.
2. Switch the chat to Agent mode mid-session (if your plan UI offers this).
3. Send: "Now using Agent mode, call `project.get_current_state` again."
4. Record YES/NO.

### V4 — Developer Mode

1. Settings → Personalization → Developer / Beta Features (location varies; may be account-level toggle).
2. Toggle Developer Mode ON.
3. Wait 30 seconds for ChatGPT to refresh available features.
4. Repeat V2.
5. Record YES/NO + note whether Developer Mode toggle is on the same level as Custom MCP gating.

### V5 — Lauburu MCP only

1. Settings → Connectors.
2. Disable Gmail / Drive / GitHub / Calendar / any other custom or built-in connector — leaving ONLY Lauburu MCP (unified).
3. Repeat V2 (fresh Agent run).
4. Record YES/NO.
5. Re-enable other connectors after the test.

### V6 — Diagnostic listing

1. Repeat V2 setup (fresh Agent, all connectors at normal state).
2. Send: "List every connector and every tool name you can currently see, grouped by connector. Do not call any tool — just list."
3. Record Agent's response verbatim. This tells us what Agent's tool-list snapshot actually contains.

### V7 — Add connector inside Agent UI

1. If the Agent run's composer has its own "Add connector" button (separate from chat-side Settings → Connectors), tap it and add the Lauburu MCP URL there.
2. Repeat the call.
3. Record whether Agent-side add resolves the issue.

### V8 — Worker reachability check (laptop)

1. From the laptop terminal:
   ```sh
   curl -sS -X POST -H 'Content-Type: application/json' \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"agent-probe","version":"1"}}}' \
     https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/v2
   ```
2. Confirm HTTP 200 + `serverInfo.name = "lauburu-mcp-unified"`.
3. If V8 returns 200 but Agent says MCP unavailable → confirmed: Worker is fine, issue is ChatGPT-side.

## 5. Recommended workflow now (until Agent supports custom MCP)

This is the immediate fallback per rule 11's "explicit Aaron-approved fallback mode" branch. It does NOT bypass MCP-first — it routes the MCP-first check through normal chat, then hands the live state to Agent as input.

1. **Normal ChatGPT chat does the MCP check.** Aaron opens a chat with Lauburu MCP enabled, pastes the rule 11 preamble (per `docs/CHATGPT_CONNECTOR_SETUP.md` § "MCP-first rule"), asks ChatGPT to call `project.get_current_state` and return a structured context block.
2. **ChatGPT packages the live state.** ChatGPT's response includes: priority, blocker, lane status (Claude / Codex idle / working / blocked), repo HEAD, freshness signal, agent_qa state, top backlog items.
3. **Aaron starts an Agent run** with that context block as the first message. Agent treats the context block as ground truth for "current project state". Agent does NOT need to call MCP itself — its starting state is the chat's MCP read.
4. **Agent does its device / screenshot / audit / vendor-console work** using its built-in connectors (Gmail / Drive / GitHub / Calendar / browsing).
5. **Agent's output lands as text / files** that Aaron then either:
   (a) pastes back into the chat for ChatGPT to summarise + flag follow-ups, OR
   (b) drops into the Claude Code laptop session for the coder to write back to MCP via `project.update_work_status` or `bridge:snapshot`.
6. **Coder writes the result back to MCP / bridge** so the action ledger has evidence. The audit findings should produce: agent_qa updates, action-ledger entries, FS-XXX candidates, or doc updates per rule 1 (audit → bundles).

This workflow is verbose but rule-11-compliant: every step still hard-gates on MCP-first via the chat lane.

### Minimum required Aaron action per Agent run

- Open or reuse a chat with Lauburu MCP enabled.
- Paste / dispatch the rule-11 preamble + `project.get_current_state` request.
- Copy the structured state block.
- Paste into the Agent run's first message.
- Agent runs. Aaron forwards Agent's output to the laptop (or asks Codex/Claude in another window to consume it).

## 6. Ideal future workflow (when Agent supports custom MCP)

When ChatGPT Agent supports custom MCP servers natively, the workflow collapses to:

1. **Agent calls MCP Core directly** as its first step. Same `project.get_current_state` / `mobile.get_*_overview` / `handoff.get_latest` / `qa.get_latest_result` surface.
2. **Agent enforces rule 11** before starting any audit / task / answer. If MCP is stale, Agent calls it out and falls back to local artefacts. If MCP is unavailable, Agent stops and surfaces clearly (per the rule 11 amendment in commit `734ab16`).
3. **Agent writes audit results back to MCP** if an admin token is configured for the run. Tools used:
   - `project.update_work_status` — flip lane to `working` / `needs_review` with an audit-result summary.
   - `project.submit_priority_suggestion` — surface FS-XXX candidates.
   - `qa.list_results` (read) — verify prior QA state before re-running.
4. **Full audit hard-gates on MCP availability.** No memory-based audits without explicit Aaron-approved fallback (rule 11 amendment).

The ideal future has Agent + chat + laptop all calling the same canonical MCP — the same single source of truth across surfaces.

## 7. Codex handoff (if Worker-side changes are needed)

Most likely there are NO Worker-side changes needed; this is a ChatGPT product gating issue. But the verification matrix in § 3 will tell us. If results suggest Worker-side adaptation, the candidate Codex prompts are:

- **If cause 9 (OAuth requirement) is real**: Worker needs to expose an OAuth flow at `/mcp/v2/oauth/*` (or similar). That's a meaningful Worker change — separate FS-XXX candidate.
- **If cause 8 (Origin header check) is real**: this codebase doesn't gate on Origin today; would need to be intentionally added IF Agent requires a specific Origin to be allow-listed.
- **If cause 5 (tool picker cap)**: continue the `/mcp/v2/lauburu` + `/mcp/v2/website` split already in the `CODEX-FIX-GRAPPLING-MCP-CHATGPT-CREATION-FAIL-01` queue.
- **If cause 1 / 7 (Agent runtime / plan tier excludes custom MCP)**: this is NOT fixable on our side. Workflow stays § 5 indefinitely until ChatGPT product changes.

No Codex handoff dispatched from this doc; verification results determine which (if any) becomes the next prompt.

## 8. Cross-references

- **`docs/MCP_LONGTERM_ACCESS_ARCHITECTURE.md`** — the
  long-term access architecture this gap-fix doc feeds into;
  Surface A (Admin/Dev tab) becomes the primary operator UI,
  Surface B (standard connector / API wrapper) replaces this
  fallback workflow once shipped.
- `docs/OPERATING_RULES.md` § rule 11 — MCP-first, including the unavailable-stop branch.
- `docs/CHATGPT_CONNECTOR_SETUP.md` — chat-side connector setup; § "MCP-first rule (operating rule 11)" callout; § 10 failure-mode quick reference.
- `docs/MCP_CANONICAL_STATE.md` — canonical MCP paths.
- `docs/UNIFIED_MCP_PLAN.md` — Worker auth model + namespacing.
- `docs/CLOUDFLARE_MIGRATION.md` — Stage 5 DNS cutover (custom domain → Cloudflare Worker), still pending.
- `docs/PHONE_ONLY_AUTOMATION_PLAN.md` § 5 — what stays manual on Aaron.

## 9. Anti-rules

- **No app code in this doc.** Implementation lives elsewhere.
- **No EAS build implications.** Mobile bundle is unaffected.
- **No public-write tools added to MCP.** All proposed Agent writes are admin-token-gated.
- **No public exposure of admin token.** Agent OAuth (if pursued) MUST be a separate flow; the existing No Auth surface stays public-safe.
- **No memory-based answer when MCP unavailable.** Rule 11 amendment hard-stops.
