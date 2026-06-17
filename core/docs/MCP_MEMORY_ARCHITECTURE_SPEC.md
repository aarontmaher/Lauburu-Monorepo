# MCP memory architecture spec

The structured-ingestion + artifact-schema + stale/superseded/
confidence model that turns MCP into the project's persistent
"nothing gets lost" memory. Operationalises rule 18 ("terminal
state is evidence, not memory") by giving every kind of
discoverable thing a typed home in MCP.

This is **doc only**. No app code. No EAS build.

## 0. Why this exists

Today's connector_* tables (`connector_work_status`,
`connector_coder_lanes`, `connector_handoff`,
`connector_terminal_summary`, `connector_backlog_items`)
capture lane status + handoff + ledger but do NOT have
typed homes for:

- Terminal discoveries (e.g. "the Health Connect debug card
  shows X for build Y").
- Audit findings (per
  `docs/INSTALLED_DEVICE_AUDIT_PLAYBOOK.md` § 5 rubric).
- Strategy ideas (e.g. "we should add scrcpy for Android
  audits").
- Workflow pain points (e.g. "git race condition between
  parallel coder lanes").
- Automation opportunities (e.g. "this manual Aaron step
  could be a push gate").
- Reusable research artifacts (per rule 23 — already typed,
  but standalone schema).

This spec defines four artifact schemas that share a common
core (id, kind, confidence, status, supersededBy) +
auto-ingestion rules so terminal discoveries flow into MCP
without manual transcription.

## 1. Common artifact core

Every memory artifact (regardless of kind) carries:

```ts
interface MemoryArtifactCore {
  id: string;                          // uuid
  kind: 'memory' | 'audit' | 'research' | 'strategy' | 'pain' | 'automation_opportunity';
  user_id: string | null;              // null for project-scoped, set for per-user
  scope: 'project' | 'per_user' | 'cohort_aggregate';
  title: string;                        // ≤140 chars
  body: string;                         // ≤2000 chars
  source: 'terminal' | 'audit' | 'manual_user' | 'manual_coder'
        | 'manual_agent' | 'ai_classifier' | 'mcp_writeback' | 'imported';
  proposedBy: 'aaron' | 'claude' | 'codex' | 'agent' | 'user' | 'ai';
  status: 'active' | 'superseded' | 'stale' | 'void';
  supersededBy: string | null;         // → another artifact id
  voidReason: string | null;
  confidence: 'provisional' | 'low' | 'medium' | 'high' | 'verified';
  staleAt: string | null;              // ISO; when this becomes stale
  createdAt: string;
  updatedAt: string;
  refs: Array<{ type: 'commit' | 'doc' | 'fs_candidate' | 'gate' | 'ledger_row'; value: string }>;
}
```

Confidence ladder rules (rule 9 honoured for any health/skill
claim; otherwise:):
- `provisional`: just observed; not validated.
- `low`: corroborated by one additional source.
- `medium`: corroborated by ≥2 sources OR repeated observation.
- `high`: explicit human signoff (Aaron / coach / agent QA).
- `verified`: shipped + Agent-confirmed + Aaron-tested-on-device.

Stale rules:
- Memory / strategy / automation_opportunity: default
  `staleAt = createdAt + 90d` (config per kind).
- Audit: `staleAt = createdAt + (default audit cycle interval)`
  per gate type (Gate A: 30d; Gate C: 90d; Gate F: per-build).
- Research: per `docs/DEEP_RESEARCH_OFFLOAD_SPEC.md` § 3.3
  (90d health / 30d app-state).
- Pain: stays active until resolved or superseded; no auto-stale.

## 2. Per-kind extensions

### 2.1 `memory` — strategy ideas, observations, decisions

Generic project knowledge that doesn't fit elsewhere. Added
when terminal output reveals something worth keeping.

Extensions:
```ts
interface MemoryArtifact extends MemoryArtifactCore {
  kind: 'memory';
  topic: string;                        // free-form tag
  decisionOrObservation: 'decision' | 'observation' | 'idea';
  alternatives_considered?: string[];   // for decisions
  cross_links?: string[];               // → other artifact ids
}
```

Examples (would be ingested):
- "Aaron prefers iPhone Mirroring over screen-record for
  non-OS-prompt audits because no AirDrop step needed."
  (`decisionOrObservation: 'decision'`).
- "Maestro flow files are easier to maintain than Detox
  test suites for our use case."
  (`decisionOrObservation: 'idea'`, eventual upgrade to
  `decision` once acted on).

### 2.2 `audit` — installed-device + simulator audit findings

Auto-ingested from `agent_qa_result.json` writes (rule 12
cadence) + manually added per
`docs/INSTALLED_DEVICE_AUDIT_PLAYBOOK.md` § 5 interpretation.

Extensions:
```ts
interface AuditArtifact extends MemoryArtifactCore {
  kind: 'audit';
  gateType: 'release_gate' | 'fs_xxx_functional' | 'forever_improve_drift'
          | 'health_connect_crash_retest' | 'ios_testflight_install'
          | 'pre_eas_sanity' | 'admin_dev_proof_checklist';
  platform: 'ios' | 'android' | 'both';
  installedBuild: { iosBuildNumber: string | null; androidVersionCode: number | null };
  result: 'pass' | 'partial' | 'fail';
  failingChecks: string[];              // rubric items that failed (per playbook § 5)
  screenshotRefs: string[];             // path-only; never URLs
  bundleRef: string | null;             // → audit-bundle-*.zip path
  agentReviewSummary: string | null;    // ≤500 chars; from Agent QA
  fsCandidatesProposed: string[];       // rule 1 (audit → bundles)
}
```

### 2.3 `research` — reusable external-AI research artifacts

Per rule 23 / `docs/DEEP_RESEARCH_OFFLOAD_SPEC.md`. Already
fully spec'd; included here for cross-kind consistency.

Extensions:
```ts
interface ResearchArtifact extends MemoryArtifactCore {
  kind: 'research';
  triggerType: ResearchJob['triggerType'];
  reuseKey: string;
  rawText: string;
  parsedSummary: string;
  citations: Array<{ url: string; title: string }>;
  flagsStripped: string[];
  citationCount: number;
  expiresAt: string;
}
```

(Mirror of the schema in `DEEP_RESEARCH_OFFLOAD_SPEC.md` § 1
for completeness; the canonical schema lives there.)

### 2.4 `strategy` — explicit strategic decisions

A subtype of `memory` with extra structure for plan-level
decisions Aaron makes.

Extensions:
```ts
interface StrategyArtifact extends MemoryArtifactCore {
  kind: 'strategy';
  scope_horizon: 'this_week' | 'this_month' | 'this_quarter' | 'long_term';
  alternatives_considered: string[];
  decision_rationale: string;            // ≤2000 chars
  related_priorities: number[];          // → connector_work_status.topPriorities[].rank
  reversibility: 'easy' | 'hard' | 'irreversible';
  safety_implications: string | null;
}
```

### 2.5 `pain` — workflow / process pain points

When terminal output reveals a recurring friction (e.g. the
git race condition Aaron + coders hit twice this session),
record it as a pain artifact so it surfaces a follow-up.

Extensions:
```ts
interface PainArtifact extends MemoryArtifactCore {
  kind: 'pain';
  severity: 'minor' | 'moderate' | 'severe';
  recurrenceCount: number;               // increments on re-observation
  workaround: string | null;
  proposed_fix: string | null;           // → automation_opportunity if cheap fix exists
  fs_candidate: string | null;
}
```

Example (already ingested as `process-2026-05-09T01:55-git-race-condition`):
- Severity: moderate.
- Recurrence: 2 (will increment if observed again).
- Workaround: stash-before-commit.
- Proposed fix: file-lock or per-lane staging area.
- FS candidate: pending classification.

### 2.6 `automation_opportunity`

Identified manual Aaron step that could become an automated
flow OR a push-approval gate. Surfaces from rule 13's
"every manual step is challenged" Forever Improve quality
bar.

Extensions:
```ts
interface AutomationOpportunityArtifact extends MemoryArtifactCore {
  kind: 'automation_opportunity';
  current_manual_step: string;
  proposed_automation: 'coder_can_run' | 'approval_gate' | 'fully_automatic';
  rule_reference: 'rule_12' | 'rule_13' | 'rule_21' | 'rule_22' | 'rule_23';
  estimated_friction_saved: 'minutes_per_week' | 'hours_per_week' | 'one_time_only';
  fs_candidate: string | null;
}
```

## 3. Automatic structured ingestion

Rule 18 says "terminal state is evidence, not memory." This
section defines HOW terminal discoveries flow into the
typed memory system without manual transcription.

### 3.1 Ingestion sources

| Source | Trigger | Default kind |
|---|---|---|
| `bridge:snapshot` writes | Each cadence per rule 12 | None directly; the snapshot is itself a connector_terminal_summary row, not a memory artifact. Memory artifacts are derived. |
| Coder commit message | `git commit` lands | `memory` if commit message contains a "Process note:" or "Strategic note:" section. Pre-commit hook (future) auto-extracts. |
| Audit run | `npm run bridge:agent-qa` writes `agent_qa_result.json` | `audit` artifact auto-created with `gateType`, `result`, `screenshotRefs`. |
| Coder report (Bash output to terminal) | Terminal scrollback contains a flagged line (e.g. starts with `MEMORY:` / `PAIN:` / `AUTOMATION:` / `STRATEGY:`). | Per the prefix. |
| Aaron message in chat | Aaron explicitly says "remember that ..." OR "the pain is ..." | `memory` / `pain` / `strategy` per parse. |
| AI classifier (future) | Background process scans recent terminal output for un-ingested signals. | Heuristic; flagged for human review. |

### 3.2 Ingestion contract

The auto-ingestion path:

1. Source produces a candidate signal (a structured write OR a flagged terminal line).
2. Signal goes to `connector_memory_ingestion_queue` (new
   table; future Codex handoff) with raw text + source +
   suggested kind.
3. Aaron OR a coder reviews the queue (admin-dev Memory
   panel). For each: accept (creates artifact), edit + accept
   (refined), or reject (queue row marked `rejected`).
4. Accepted rows materialise as full memory artifacts in
   the typed table per § 2.
5. Artifact gets a confidence score: `provisional` by default;
   bumps when multiple sources confirm.

No silent ingestion: every artifact has a human or
deterministic-classifier acceptance event recorded in
`createdAt` + `proposedBy`.

### 3.3 Cross-kind references

Memory artifacts cross-link via `refs[]`:

```ts
{ type: 'commit', value: '630d4ad' }
{ type: 'doc', value: 'docs/MCP_MEMORY_ARCHITECTURE_SPEC.md' }
{ type: 'fs_candidate', value: 'FS-XXX' }
{ type: 'gate', value: 'gate-uuid-from-rule-21' }
{ type: 'ledger_row', value: 'audit-2026-05-09T01:51-...' }
```

This makes the memory graph navigable: an audit artifact
references its commit + screenshots + bundle + gate + any
research that informed it.

## 4. Stale + superseded + confidence rules

### 4.1 Stale

Auto-flips status from `active` → `stale` when `staleAt`
elapses. Stale artifacts:
- Stay readable in the audit trail.
- Are NOT cited in new explanations (only `active` artifacts
  are).
- May be refreshed by re-observation (creates a new
  artifact + supersedes the stale one).
- Per default TTLs in § 1.

### 4.2 Superseded

When a new artifact replaces an old one:
- New artifact is created.
- Old artifact's `status` flips to `superseded`.
- Old `supersededBy` is set to the new artifact's id.
- New artifact's `refs[]` includes a back-link.
- Both stay in the audit trail.

Superseding is asymmetric — old becomes inactive immediately;
new starts at `confidence: provisional` unless Aaron
elevates.

### 4.3 Confidence elevation

| From | To | Trigger |
|---|---|---|
| `provisional` | `low` | One additional source corroborates (different terminal observation, same conclusion). |
| `low` | `medium` | ≥2 additional sources OR repeated observation across ≥7d. |
| `medium` | `high` | Explicit human signoff (Aaron / coach / agent QA). |
| `high` | `verified` | Shipped + Agent-confirmed + Aaron-tested-on-device (matches rule 8 four-status sequence end state). |

For `audit` artifacts: confidence maps directly from
agent_qa.status:
- `partial` → `low` confidence.
- `pass` → `high` confidence (or `verified` for full Gate A
  pass).
- `fail` → `provisional` confidence + immediate FS-XXX
  candidate.

Per rule 9: any health/skill claim NEVER reaches `verified`
without explicit Aaron-on-device confirmation.

## 5. Privacy + redaction

- All `per_user` scope artifacts are RLS-gated by `auth.uid()`.
- `project` scope artifacts visible to admin-token only,
  unless explicitly marked public-safe.
- `cohort_aggregate` scope artifacts (future) follow
  FS-020 § 9 anonymisation thresholds.
- Body text auto-redacted on ingestion: token patterns
  hard-blocked (`sb_secret_`, `eyJ` JWT-shape, etc.); PII
  patterns (email / phone / address) flagged for review.
- Public-safe MCP surfaces show counts + truncated titles;
  full body via admin-token only.

## 6. Codex handoff prompt — implementation

```
PROMPT-ID: CODEX-FS-XXX-MCP-MEMORY-ARCHITECTURE-IMPL-01
TYPE: CODEX
LANE: Supabase memory tables + ingestion queue + Worker
      tools + admin-dev memory panel

MCP-FIRST: call project.get_current_state.

Reference (read first):
- docs/MCP_MEMORY_ARCHITECTURE_SPEC.md (this doc — canonical).
- docs/OPERATING_RULES.md § 18 (action ledger which this
  extends).
- docs/DEEP_RESEARCH_OFFLOAD_SPEC.md (research artifact
  schema reused).
- docs/HUMAN_APPROVAL_GATE_SPEC.md (rule 21 — gate-typed
  artifacts cross-link here).
- docs/FOREVER_IMPROVE_LIFECYCLE_SPEC.md (lifecycle states
  the audit-artifact maps into).
- cloudflare-worker/src/data/CONNECTOR_SANITIZATION_RULES.md
  (privacy floor).

GOAL
Wire the typed memory system:
- Supabase: memory_artifacts table per § 1 + per-kind
  view tables per § 2 + memory_ingestion_queue table per § 3.
- Worker: project.memory_ingest (any user, queues) +
  project.memory_accept (admin or per-role) +
  project.memory_supersede + project.memory_list (filtered
  by kind / scope / status).
- Mobile: admin-dev Memory panel with per-kind filters +
  ingestion-queue review surface.
- Auto-ingestion hooks:
  - bridge:agent-qa wrapper auto-creates audit artifact.
  - git pre-commit hook (opt-in) extracts MEMORY: / PAIN: /
    AUTOMATION: / STRATEGY: prefixed lines from commit
    messages.

SCOPE PHASE 1 (this prompt)
1. Supabase migration: memory_artifacts table + per-kind
   typed views + memory_ingestion_queue. RLS by scope +
   auth.uid().
2. Worker tools per goal.
3. Mobile admin-dev panel + ingestion-queue review.
4. Auto-ingestion: bridge:agent-qa wrapper updated to also
   create an audit artifact.
5. Contract test: schema lock + redaction patterns.

ANTI-RULES
- No silent ingestion; every artifact has a proposedBy +
  human-or-deterministic acceptance.
- No deletion (status: void instead of delete).
- No PII / token leaks (auto-redaction enforced).
- No EAS build dispatched.

VERIFICATION
- Schema lock test PASS.
- npm run rules:test PASS (23 rules unchanged).
- npm run mcp:test:public-redaction PASS.
- Manual: simulate audit run → audit artifact auto-created
  with screenshotRefs.
- Manual: simulate "MEMORY: ..." line in commit message →
  ingestion-queue row.

OUTPUT (small)
- Status:
- Supabase migration name:
- New Worker tools:
- Existing files touched:
- New files added:
- Tests run:
- MCP / bridge writeback evidence:
- Open questions:
- Recommendation for follow-up:
```

Approval-gated.

## 7. Anti-rules

- **No untyped writes to memory.** Every artifact has a
  `kind` + per-kind extensions.
- **No silent confidence elevation.** Each ladder step
  requires a defined trigger.
- **No deletion.** Stale / superseded / void are the exits.
- **No cross-user leakage.** Per-user RLS-gated; cohort
  aggregates require thresholds.
- **No PII / token escape.** Auto-redaction at ingestion.
- **No "verified" without Aaron-on-device** for any
  health/skill claim (rule 9).

## 8. Cross-references

- **`docs/ARTIFACT_SCHEMAS.md`** (Codex `fe7f93d`) — top-level
  **index** of every persistent artifact schema in this
  codebase. This doc is ONE of the indexed specs (memory /
  audit / strategy / pain / automation_opportunity schemas).
- `docs/OPERATING_RULES.md` § 9 (provisional) / § 11
  (MCP-first) / § 18 (action ledger).
- `docs/FOREVER_IMPROVE_LIFECYCLE_SPEC.md` — lifecycle
  states audit-artifact maps into.
- `docs/HUMAN_APPROVAL_GATE_SPEC.md` — rule 21 gates
  cross-link via `refs[]`.
- `docs/AI_SPEND_GATES_SPEC.md` — rule 22 spend events
  cross-link.
- `docs/DEEP_RESEARCH_OFFLOAD_SPEC.md` — canonical research
  schema this references.
- `docs/INSTALLED_DEVICE_AUDIT_PLAYBOOK.md` — gateType
  enum + AGENT_QA recording feeds audit artifacts.
- `cloudflare-worker/src/data/CONNECTOR_SANITIZATION_RULES.md`
  — auto-redaction patterns.
