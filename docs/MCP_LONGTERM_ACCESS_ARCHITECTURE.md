# MCP long-term access architecture

The strategic decision about WHICH surfaces operators (Aaron),
ChatGPT chats, ChatGPT Agent runs, Deep Research runs, and
developers actually use to read / drive Lauburu state.

This is a **decision doc**, not a workflow rule. It captures
the canonical surfaces, their roles, and the migration path
away from the current Developer-Mode-only ChatGPT MCP setup
toward a stable, production-ready access architecture.

This is **doc only**. No app code. No Worker code change.
No EAS build.

## 0. The decision in one paragraph

The **Admin/Dev tab** in the mobile app is the **primary
phone/operator UI** for all live state and approval gates.
The **standard ChatGPT connector / API wrapper** is the
**long-term Agent / Deep Research / external-AI access path**
that does NOT require Developer Mode and works across
ChatGPT chat / Agent / Deep Research surfaces. The
**developer MCP** (the unified `/mcp/v2` namespaced tool
surface that today requires ChatGPT's Developer Mode toggle)
remains as **optional dev/debug tooling** — it is NOT the
required production workflow.

## 1. Three surfaces

| Surface | Role | Auth | Used by |
|---|---|---|---|
| **(A) Admin/Dev tab** in `apps/mobile/app/admin-dev.tsx` | **Primary phone UI** for state + approvals + alerts. The canonical operator surface. | Supabase JWT + email allowlist (per FS-019 / `MOBILE_NATIVE_CONTROL_CENTRE_SPEC.md` Tier 3). | Aaron (operator); Aaron's testers in admin-only pages. |
| **(B) Standard connector / API wrapper** | **Long-term Agent / Deep Research / external-AI access path.** A ChatGPT-compatible connector spec that survives plan-tier and Developer-Mode changes. | OAuth (preferred) OR API-key per ChatGPT's connector form. Public-safe by default; admin scopes via OAuth. | ChatGPT chat / Agent runs / Deep Research / future ChatGPT product surfaces / other AI clients (Claude.ai connectors, Anthropic API). |
| **(C) Developer MCP** | Optional dev/debug tooling — `/mcp/v2` JSON-RPC over Streamable HTTP, layered No Auth / Bearer admin. | Custom MCP via ChatGPT Developer Mode toggle today. | Claude Code / Codex laptop sessions; ChatGPT chat with Developer Mode ON; integration smoke tests. |

Each surface has a different role. **Surface A is what Aaron
uses on his phone day-to-day.** **Surface B is the path that
ships once we stop relying on ChatGPT's Developer Mode toggle.**
**Surface C is the laptop's debug surface.**

### 1.1 Why Admin/Dev tab is the primary UI

- Lives inside the app Aaron already uses — no separate web
  UI, no extra client.
- Survives ChatGPT product changes (Agent runtime gating, plan
  tier reshuffles) — the app does not depend on any external
  AI client's connector availability.
- Auth is Supabase JWT + email allowlist (FS-019); admin-token
  is never bundled into the mobile binary.
- Push notifications + approval gates (rules 19/20/21/22/23)
  surface here directly.
- Enforces rule 11 (MCP-first) for the operator just like for
  coders / agents.

### 1.2 Why standard connector / API wrapper is the long-term external path

- ChatGPT's **custom MCP** today requires Developer Mode
  (per `docs/AGENT_MCP_ACCESS.md` § 2 root cause candidates 1
  + 3 + 7). Developer Mode is a beta surface, not a stable
  production gate; it can be revoked, restricted to specific
  plans, or behave differently in Agent / Deep Research.
- A **standard connector** (built using ChatGPT's normal
  Connector / Action / GPT framework) does NOT require
  Developer Mode. It works in normal chat AND Agent runs AND
  Deep Research with the same connection.
- An **API wrapper** approach (OpenAPI spec for our Worker
  endpoints, optional OAuth) is the most portable: ChatGPT
  Custom GPTs, Claude.ai connectors, Anthropic API tool-use,
  and any future LLM client can consume it.

### 1.3 Why developer MCP stays as optional dev tooling

- The `/mcp/v2` JSON-RPC surface is genuinely useful for
  Claude Code and Codex on the laptop — they can call
  `project.update_work_status` etc. via Bearer-admin auth.
- It's also useful for ChatGPT chats where the operator has
  Developer Mode on and wants the rich 25-tool surface.
- But it's NOT load-bearing for the production workflow once
  surface A and B are in place. If ChatGPT removes Developer
  Mode tomorrow, the team workflow continues unaffected.

## 2. When Developer Mode can be turned off safely

**Developer Mode in ChatGPT is currently used for:**
1. Custom MCP connector inside ChatGPT chats (rich tool
   access for the operator).
2. Custom MCP in Agent / Deep Research (NOT working today
   per `docs/AGENT_MCP_ACCESS.md` — gating issue, not a
   Developer-Mode benefit).

**Aaron can safely turn Developer Mode OFF when ALL of the
following are true:**

| Criterion | Required state |
|---|---|
| (a) Admin/Dev tab parity | Admin/Dev tab exposes everything the operator currently uses Developer Mode + the `/mcp/v2` connector for: priority / blocker / lane status / build status / repo HEAD / agent_qa / handoff / approval gates / push toggles / writeback cadence. |
| (b) Approval gates landed | Rules 21 / 22 / 23 push wiring is shipped (FS-XXX from those specs). Aaron approves builds / deploys / migrations from Admin/Dev push, not from a ChatGPT chat tool call. |
| (c) Standard connector landed | Standard connector / API wrapper ships with read parity to the `/mcp/v2` core 25 tools (project / mobile / integrations / handoff / qa / release namespaces). |
| (d) Agent fallback path proven | Agent runs successfully with the workflow in `docs/AGENT_MCP_ACCESS.md` § 5 (chat does MCP-first read, packages state, hands to Agent) OR with the standard connector once that ships. Aaron has run at least one full Agent audit using the new path. |
| (e) Coder workflow continues without ChatGPT-side MCP | Claude Code + Codex on the laptop still have full access via Bearer-admin to `/mcp/v2`. ChatGPT Developer-Mode-MCP is no longer the only path. |
| (f) No active investigations gated on Developer Mode | All `CODEX-FIX-GRAPPLING-MCP-CHATGPT-CREATION-FAIL-01` and similar MCP-creation-fix prompts are resolved or the issue is acknowledged as ChatGPT-product-side and unfixable from our codebase. |

When (a)-(f) hold, Developer Mode can be turned off without
losing the operator workflow. Surface C (`/mcp/v2`) remains
available for laptop coders + occasional debug use.

If only (a) + (b) hold, Aaron can rely primarily on the
phone Admin/Dev tab while keeping Developer Mode on as a
backup. This is the **interim state** likely to apply for
several weeks while (c) + (d) ship.

## 3. Required Admin/Dev fields before Developer Mode is no longer needed

Today's Admin/Dev tab (per `apps/mobile/app/admin-dev.tsx`)
has substantial state surface but not yet full parity with
`/mcp/v2`. The following fields MUST be present (read +
write where applicable) before criterion (a) of § 2 holds.

### 3.1 Read surface

| Field | Source | Status today |
|---|---|---|
| Top priority + blocker + freshness | `project.get_current_state` | Shipped (admin-dev shows priority / blocker / freshness pill with relative age + colour cue) |
| Per-lane status (claude / codex / agent) | `project.get_current_state.agents[]` | Shipped (lane chips + dedicated Idle/working/blocked/needs-review tile) |
| Repo HEAD + branch + dirty count | `project.get_current_state.repo` | Shipped |
| Build status (Android versionCode + iOS buildNumber + Play / TestFlight tracks) | `mobile.get_build_status` | Shipped (build chips) |
| Agent QA result + release gate | `mobile.get_agent_qa_result` | Shipped (release-gate chip + iOS/Android boolean tile + reason) |
| Handoff (latest from each lane) | `handoff.get_latest` | Shipped (handoff card) |
| Integrations overview (provider counts) | `integrations.get_overview` | Shipped |
| Owner alerts toggle (rule 20 in-app banner) | local state | Shipped (banner toggle) |
| **Approval gate list (rule 21)** | local store `data/approval-gates/gates.json` + `useApprovalGatesStore` (UI shipped; server-side `project.list_approval_gates` admin tool still TODO) | **PARTIAL** — UI shipped (commit 87ebabc); server writeback + push fan-out TODO |
| **AI spend usage + gate list (rule 22)** | local `useSpendGatesStore` + `precheckJournalImport`/`precheckReadinessAnomaly`/`precheckHealthTrend` (UI shipped; server-side `project.get_ai_spend_usage` admin tool still TODO) | **PARTIAL** — UI + deterministic prechecks shipped (commit 228160c); server writeback TODO |
| **Research artifact cache (rule 23)** | local `useResearchJobsStore` (UI shipped with paste-result + reuseHash dedup + supersede; server-side `project.list_research_artifacts` admin tool still TODO) | **PARTIAL** — UI + cache lifecycle shipped (commit 11b8c75); server writeback TODO |
| **Operating rules count + ids (1..N)** | `project.get_operating_rules` | Shipped (rules count chip; current contract test asserts 23 rules) |
| **Action ledger backlog (rule 18)** | `project.list_priorities` (or dedicated ledger reader) | Shipped read-only; full detail TODO |

### 3.2 Write / action surface

| Action | Tool | Status today |
|---|---|---|
| Update lane status / next action / blocker | `project.update_work_status` | Shipped (admin-dev surfaces action; tool is on `/mcp/v2` core surface, admin-token-gated) |
| Submit priority suggestion | `project.submit_priority_suggestion` | Shipped |
| Toggle in-app banner | local | Shipped |
| **Approve / Defer / Cancel an approval gate (rule 21)** | local `useApprovalGatesStore.approve|defer|cancel|markCompleted`; new `project.update_approval_gate` admin tool TODO | **PARTIAL** — local-first writeback shipped (commit 87ebabc); on approve the store emits a ledger note Aaron pastes into `data/action-ledger/pending_actions.json` until the server route lands. Server `project.update_approval_gate` on `/mcp/v2/admin` still TODO |
| **Approve / Defer / Cancel an AI-spend gate + Export prompt (rule 22)** | local `useSpendGatesStore.approve|defer|cancel` + `exportSpendGatePrompt`; new `project.update_ai_spend_gate` admin tool TODO | **PARTIAL** — local writeback + paste-into-ChatGPT prompt-export shipped (commit 228160c). Server route TODO |
| **Create / Mark submitted / Mark complete / Cancel a research job + Copy prompt (rule 23)** | local `useResearchJobsStore.createJob|markSubmitted|markCompleted|cancel` + `exportResearchPrompt`; new `project.research_job_create` + `project.research_artifact_import` admin tools TODO | **PARTIAL** — local lifecycle + reuseHash dedup + supersede shipped (commit 11b8c75). Server routes TODO |
| Push permissions toggle | local + Expo Notifications | **TODO** (rule 20 push wiring) — blockers documented in `docs/APPROVAL_GATES_AND_PUSH.md` |
| Bridge:snapshot trigger (admin-dev "refresh writeback" button) | local invocation | Optional — coder-side cadence is canonical |

### 3.3 Acceptance criteria for surface A parity

A ↔ Developer-Mode-MCP parity holds when:
- All "Shipped" rows continue to render correctly.
- All "TODO" rows ship with their respective FS-XXX batches
  (FS-XXX rule 21 + rule 22 + rule 23 implementations).
- Operating-rules count chip stays in sync with the contract
  test (rules:test 1..N).
- Push-notification surface fires for all 3 gate types
  (rules 20 / 21 / 22 / 23) per their respective specs.
- The Admin/Dev tab tap-test flow Aaron uses today matches
  `docs/AGENT_MCP_ACCESS.md` § 5 fallback workflow when
  Agent needs the state.

## 4. Standard connector endpoint requirements

The "Surface B" path. What the public connector / API
wrapper must expose to be a credible long-term replacement
for the Developer-Mode MCP path.

### 4.1 Endpoint shape

- **OpenAPI spec** at a stable URL (e.g.
  `https://lauburu-mcp-preview.lauburu-aaron.workers.dev/openapi.json`
  → migrating to `https://mcp.lauburugrapplingmap.com/openapi.json`
  once Stage 5 of `docs/CLOUDFLARE_MIGRATION.md` lands).
- **REST/JSON over HTTPS** (not JSON-RPC) — this is what
  ChatGPT custom GPT actions, Custom Connectors, and most
  AI-platform tool-use clients consume.
- **Pagination + filtering** on list endpoints.
- **OAuth 2.0** for admin-scope endpoints (preferred over
  Bearer-token-in-form, which ChatGPT's connector form
  doesn't reliably forward — see `CHATGPT_CONNECTOR_SETUP.md`
  § 10.5).

### 4.2 Required public-safe endpoints (No Auth)

Mirror the `/mcp/v2` core 25 tools as REST:

| Endpoint | Returns |
|---|---|
| `GET /api/v1/state/current` | Equivalent of `project.get_current_state`. |
| `GET /api/v1/lanes` | Equivalent of `mobile.get_lane_overview`. |
| `GET /api/v1/builds` | Equivalent of `mobile.get_build_overview`. |
| `GET /api/v1/repo` | Equivalent of `mobile.get_repo_overview`. |
| `GET /api/v1/handoff/latest` | Equivalent of `handoff.get_latest`. |
| `GET /api/v1/integrations/overview` | Equivalent of `integrations.get_overview`. |
| `GET /api/v1/qa/latest` | Equivalent of `qa.get_latest_result`. |
| `GET /api/v1/release/gate` | Equivalent of `release.get_gate`. |
| `GET /api/v1/operating-rules` | Equivalent of `project.get_operating_rules`. |
| `GET /api/v1/priorities` | Equivalent of `project.list_priorities`. |

All redacted per `cloudflare-worker/src/data/CONNECTOR_SANITIZATION_RULES.md`.

### 4.3 Required admin-scope endpoints (OAuth)

Behind `Authorization: Bearer <oauth-access-token>` with
`admin` scope:

| Endpoint | Action |
|---|---|
| `POST /api/v1/state/work-status` | Equivalent of `project.update_work_status`. |
| `POST /api/v1/priorities/suggestions` | Equivalent of `project.submit_priority_suggestion`. |
| `POST /api/v1/approval-gates/{id}/action` | Equivalent of `project.update_approval_gate`. |
| `POST /api/v1/research-jobs` | Equivalent of `project.research_job_create`. |
| `POST /api/v1/research-jobs/{id}/import` | Equivalent of `project.research_artifact_import`. |
| `GET /api/v1/research-artifacts/lookup?reuseKey=...` | Equivalent of `project.research_artifact_lookup_by_reuseKey`. |

OAuth flow: standard PKCE; tokens issued by Worker after
verifying email-allowlist match against Aaron's account.
Token TTL ≤ 24h; refresh token TTL ≤ 30d. Tokens revocable
via Admin/Dev tab.

### 4.4 Connector packaging

For each AI client, package the OpenAPI spec as a connector:

- **ChatGPT Custom GPT / Action**: paste the OpenAPI JSON;
  ChatGPT generates the connector. Works in normal chat,
  Agent runs (where supported), Deep Research.
- **Claude.ai Custom Connector**: same OpenAPI; OAuth flow
  configured per Anthropic's connector docs.
- **Other clients**: the OpenAPI spec is portable.

This means adding a new AI client doesn't require app code
changes — only an OpenAPI registration step on the client
side.

### 4.5 What Surface B does NOT replace

- It does NOT replace the `/mcp/v2` JSON-RPC surface for
  laptop coders. Claude Code / Codex continue calling
  `/mcp/v2` directly with admin Bearer.
- It does NOT replace the Admin/Dev tab as the operator UI.
  Surface B is for Agent / Deep Research / external AI; the
  operator uses Surface A.
- It does NOT replace the in-app push surface. Push goes to
  Admin/Dev tab; Surface B is read/write for AI clients,
  not a notification surface.

## 5. Fallback workflow — Agent visually audits Admin/Dev

Until Surface B ships and Agent can call our API directly,
the fallback (per `docs/AGENT_MCP_ACCESS.md` § 5) is:

1. Aaron opens normal ChatGPT chat with Lauburu MCP enabled
   (Developer Mode ON).
2. Chat calls `project.get_current_state` and packages a
   structured state block.
3. Aaron pastes the state block into an Agent run.
4. Agent does device work using its built-in connectors.
5. Agent's output flows back to laptop coders.
6. Coders write results back via `/mcp/v2` admin tools.

**The new fallback once Surface A is feature-complete**
(criteria § 3 met):

1. Aaron opens the **Admin/Dev tab on his phone**.
2. Agent (via web / Browse mode) is asked to **visually
   audit the Admin/Dev tab screenshots** — Aaron screenshots
   the tab, drops the screenshots into Agent.
3. Agent reads the live state from the screenshots, applies
   its rule 11 / rule 22 / rule 23 logic, and proposes
   actions.
4. Aaron approves any required gates from the Admin/Dev
   tab's approval centre directly.

This fallback **does not depend on ChatGPT's Developer Mode
or custom MCP at all**. Surface A becomes the canonical
operator UI; Agent reads it visually until Surface B ships.

**The endgame** (Surface B shipped):

1. Agent runs call our standard connector / API wrapper
   directly.
2. Agent reads state, proposes actions, requests approval
   via the same approval gates.
3. Aaron approves from the Admin/Dev tab push notifications.
4. Agent never needs visual auditing — the connector is the
   same authoritative read path the app uses.

## 6. Migration phasing

Order of operations to retire Developer-Mode dependence:

### Phase 1 — current state (2026-05-09)

- Surface A (Admin/Dev tab): **substantially shipped**.
  - Read parity: priority / blocker / freshness with relative-age
    age cue, per-lane status, lane-status breakdown tile, repo
    HEAD, build status, release-gate boolean tile + reason,
    handoff card, integrations overview — all shipped.
  - Approval gate centre, AI-spend gate centre with deterministic
    prechecks + prompt export, research-job centre with
    reuseHash dedup + supersede + paste-result import — all
    shipped (commits 87ebabc, 228160c, 11b8c75).
  - Push notifications: **NOT shipped** (Apple capability +
    expo-notifications + backend route — see
    `docs/APPROVAL_GATES_AND_PUSH.md`). Banner-only today.
  - Server-side writeback for approval / spend / research gates:
    NOT shipped. Aaron pastes ledger notes manually until the
    server routes land.
- Surface B: NOT shipped.
- Surface C (`/mcp/v2`): shipped + working in normal chat
  (Developer Mode ON), broken in Agent / Deep Research.
  `/mcp/v2/admin` and `/mcp/v2/website` split shipped (commit
  630bf3f) so the core surface stays under ChatGPT's tool-picker
  cap. `project.ping` diagnostic shipped (commit 1081d65).
- Developer Mode: ON.

### Phase 2 — Surface A feature complete (when § 3 criteria hold)

- Push notifications shipped (rule 20 / 21 / 22 / 23 via
  Codex handoffs in their respective spec docs).
- Server-side approval-gate / spend-gate / research-job
  writeback routes shipped (`project.update_approval_gate`,
  `project.update_ai_spend_gate`,
  `project.research_job_create`, `project.research_artifact_import`
  on `/mcp/v2/admin`).
- Aaron uses Surface A for daily operator work. Surface C
  becomes "occasional debug".
- Developer Mode: still ON (provides fallback richness for
  one-off ChatGPT chat queries).

### Phase 3 — Surface B shipped (separate FS-XXX batch)

- OpenAPI spec at the Worker stable URL.
- OAuth 2.0 admin-scope flow.
- ChatGPT Custom GPT / Action connector registered (works
  in normal chat / Agent / Deep Research without Developer
  Mode).
- Other AI client connectors registered as needed.
- Developer Mode: can be turned OFF; Surface B replaces it
  for ChatGPT-side access.

### Phase 4 — Cloudflare DNS cutover (Stage 5 of CLOUDFLARE_MIGRATION)

- `mcp.lauburugrapplingmap.com` flips DNS to the production
  Cloudflare Worker.
- Surface B endpoints move from `*.workers.dev` to the
  custom domain.
- Surface C `/mcp/v2` remains for laptop coders.
- ChatGPT connectors re-pointed to the custom domain (each
  AI client requires re-registration with the new URL).

### Phase 5 — sunset Developer Mode references in docs

- Once Phase 4 holds, the chat-only Developer-Mode-MCP path
  is documented as "legacy" in
  `docs/CHATGPT_CONNECTOR_SETUP.md`. The canonical setup
  becomes Surface B (standard connector).
- `docs/AGENT_MCP_ACCESS.md` § 5 fallback workflow is
  retired (or kept as a "what to do if Surface B is down"
  emergency path).

## 7. Anti-rules

- **No silent surface deletion.** Removing surface A or B
  from the architecture requires explicit Aaron approval
  recorded in `docs/APP_DEVELOPMENTS.md`. Surface C may be
  deprecated later but never silently removed without coder
  workflow migration.
- **No bypassing Surface A for operator-facing decisions.**
  Aaron's approvals (rules 21 / 22 / 23) are recorded
  through Surface A's approval centre, never through
  Surface C tool calls. (Surface C admin tool calls remain
  available to Codex/Claude as automation, not to Aaron as
  a primary UI.)
- **No exposing admin tokens through Surface B.** OAuth
  flow only; never Bearer-token-in-form pattern (ChatGPT
  doesn't reliably forward auth headers — see § 4.1).
- **No private data in Surface B public-safe endpoints.**
  Same redaction surface as Surface C public tools.
- **No Surface B endpoints behind Developer Mode.** Surface
  B's value is precisely that it does NOT require
  Developer Mode.
- **No Surface A binary-bundled admin tokens.** Surface A
  uses Supabase JWT + email allowlist (FS-019). Admin
  tokens never live in the mobile app binary.

## 8. Cross-references

- `docs/MOBILE_NATIVE_CONTROL_CENTRE_SPEC.md` (FS-019) —
  the 3-tier auth model Surface A uses (No Auth public /
  Supabase JWT per-user / JWT + email allowlist admin).
- `docs/CONTROL_CENTRE_MVP_SPEC.md` — Snapshot schema +
  Worker composition for Surface A's read path.
- `docs/CHATGPT_CONNECTOR_SETUP.md` — Surface C custom-
  connector setup; § 10 failure modes.
- `docs/AGENT_MCP_ACCESS.md` — Agent-vs-MCP gap analysis;
  § 5 fallback workflow that Surface A makes obsolete once
  feature-complete.
- `docs/HUMAN_APPROVAL_GATE_SPEC.md` — rule 21 approval
  gates surfaced through Surface A.
- `docs/AI_SPEND_GATES_SPEC.md` — rule 22 AI-spend gates.
- `docs/DEEP_RESEARCH_OFFLOAD_SPEC.md` — rule 23 deep-
  research offload + artifact cache.
- `docs/CLOUDFLARE_MIGRATION.md` — Stage 5 DNS cutover for
  Surface B.
- `docs/UNIFIED_MCP_PLAN.md` — Worker auth model + the
  `/mcp/v2` namespacing that underlies Surface C and gets
  ported to Surface B.
- `docs/CONNECTOR_SECURITY_MODEL.md` — security model for
  the connector surfaces.
- `docs/PHONE_ONLY_AUTOMATION_PLAN.md` — Surface A operator
  workflow + manual Aaron steps.
- `docs/APPROVAL_GATES_AND_PUSH.md` — push setup blockers
  (Apple capability + `expo-notifications` + Expo push token
  + backend POST `/api/admin/notify-approval-gate`) and the
  manual ledger-writeback path Aaron uses today.
- `docs/MCP_CORE_AGENT_TROUBLESHOOTING.md` — diagnostic
  ladder for the "works in normal chat but not Agent"
  symptom; Surface B will eventually obsolete the workaround
  but the troubleshooting ladder remains useful for any
  future MCP transport regression.
