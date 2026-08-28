# Deep research offload + artifact cache — spec (operating rule 23)

When a request classifies as `deep_research_external` per
rule 22, the app generates a ready-to-run external-AI prompt
(default ChatGPT Deep Research), Aaron pastes it into the
external surface, and the result is imported back as a
cached artifact. Future requests with the same redacted
input hash reference the cached artifact rather than
re-running the research — same research never repeats while
a valid artifact exists.

This is **spec only**. No app code. No Worker code change.
No EAS build. Implementation is a Codex follow-up batch
gated on Aaron approval (per rule 7 + rule 13 + rule 21).

## 0. Relationship to existing rules

| Rule | Relationship |
|---|---|
| Rule 7 (EAS build cost control) | Rule 23 generalises the cost-gating principle from EAS to deep research. |
| Rule 9 (provisional health claims) | Imported research artifacts inherit `confidence: provisional` for any health-context claim. The import parser strips medical-advice / causation language. |
| Rule 11 (MCP-first) | Cache lookups go through MCP; the reuseKey check happens BEFORE any prompt is shown to Aaron. |
| Rule 18 (action ledger) | Research jobs + artifact imports + citations are recorded as ledger rows. |
| Rule 21 (Human-approval push gate) | Research jobs use rule 21's state machine + push wiring exactly. New gate states `running | imported | cached | stale` extend the rule 21 base states for the research-specific lifecycle. |
| Rule 22 (AI spend gate) | Rule 23 is the implementation of rule 22's `deep_research_external` cost class. The other 3 cost classes (free_deterministic, cheap_ai, expensive_ai) do NOT route through rule 23. |

## 1. Research job schema

```ts
interface ResearchJob {
  id: string;                           // uuid
  user_id: string;
  triggerType: 'complex_journal' | 'blood_test_pdf' | 'dexa_scan'
             | 'health_trend' | 'readiness_anomaly'
             | 'visual_app_audit' | 'athlete_memory_synthesis'
             | 'custom';
  triggerContext: string;               // ≤280 chars, redacted
  prompt: string;                       // the external-AI-ready prompt text
  promptModel: 'chatgpt_deep_research' | 'claude_extended_thinking' | 'gemini_deep_research' | 'custom';
  sourceDataSummary: string;            // redacted minimal context block sent to external AI
  reuseKey: string;                     // sha256 of triggerType + canonicalised sourceDataSummary
  status: 'waiting_for_approval'        // rule 21 base
        | 'approved'                    // rule 21 base
        | 'deferred'                    // rule 21 base
        | 'expired'                     // rule 21 base
        | 'blocked'                     // rule 21 base
        | 'running'                     // gate-specific: prompt copied, awaiting import
        | 'imported'                    // gate-specific: result pasted back, parsing
        | 'cached'                      // gate-specific: artifact stored + indexed
        | 'stale';                      // gate-specific: TTL expired
  approvedAt?: string;
  resultArtifactId?: string;            // → research_artifacts.id once imported
  expiresAt: string;                    // ISO; default now + 90d for health, +30d for app-state
  citationCount: number;                // how many times the cached artifact has been cited
  createdAt: string;
  updatedAt: string;
}
```

Separate `research_artifacts` table for the imported content
itself:

```ts
interface ResearchArtifact {
  id: string;
  user_id: string;
  research_job_id: string;
  reuseKey: string;                     // copied from job for fast lookup
  triggerType: ResearchJob['triggerType'];
  importedAt: string;
  rawText: string;                      // verbatim external-AI output, redacted of advice/causation
  parsedSummary: string;                // ≤500 char structured summary
  citations: Array<{ url: string; title: string }>;
  flagsStripped: string[];              // log of phrases removed at import (e.g. "you should", "this will help")
  expiresAt: string;
  citationCount: number;
}
```

Both tables are RLS-gated by `auth.uid() = user_id`. No
cross-user reads.

## 2. Trigger types

The 7 documented triggers + a `custom` escape hatch.

### 2.1 `complex_journal`

Aaron pastes / imports a journal block that the FS-020
parser flags as needing higher-level reasoning beyond
deterministic shape detection. Example: a multi-page note
with mixed peptide cycle history + symptom narrative + dose
changes that's too entangled for the parser to confidently
split into discrete events.

`sourceDataSummary` = redacted structural skeleton (term
count + date range + ambiguity count), NOT the raw text.

### 2.2 `blood_test_pdf`

Aaron uploads a blood test PDF (or pastes the values).
External AI is asked to summarise standard interpretation
context (general background only — not personalised medical
advice; rule 9). Imported result is stored as a cached
artifact tied to that test date.

`sourceDataSummary` = list of marker names + values + units +
reference range (no PII, no patient info); the original PDF
stays on-device.

### 2.3 `dexa_scan`

Body composition scan upload. External AI is asked for the
standard-context interpretation (lean mass / fat mass /
visceral fat trends) — provisional language only, no
medical advice.

`sourceDataSummary` = redacted scan values (no clinic name,
no patient id, no scan-image attachment unless Aaron explicitly
opts in via the `sensitiveDataIncluded` flag from rule 22 § 3.2).

### 2.4 `health_trend`

A new trend in HRV / RHR / sleep efficiency / training load.
Coach detects the trend deterministically; rule 23 routes
the explanation request to external research.

`sourceDataSummary` = trend direction + window + magnitude +
relevant journal events that overlap (redacted).

### 2.5 `readiness_anomaly`

Coach detects an unusual pattern (e.g. "metric X dropped 20%
without an obvious cause"). Rule 23 routes the explanation
request.

`sourceDataSummary` = anomaly window + delta + adjacent
journal events.

### 2.6 `visual_app_audit`

Large-scale visual audit of the app (multiple screenshots,
multi-screen flow). External AI does the visual analysis;
imported result is a structured findings list.

`sourceDataSummary` = screen names + screenshot count +
audit goal. The screenshots themselves go into the prompt
via the export-prompt copy path; Aaron drag-drops into the
external AI.

### 2.7 `athlete_memory_synthesis`

Long-form synthesis across months of data (training,
readiness, journal, nutrition). Always external — too long
for in-app inference.

`sourceDataSummary` = data window + lane counts + key
metrics-summarised.

### 2.8 `custom`

Escape hatch for triggers that don't fit the 7 above.
`triggerContext` is a freeform user-typed reason. Same
gate + cache mechanics apply.

## 3. Cache + reuse model

The core cost-saver. Rule 23's reason for existing.

### 3.1 reuseKey computation

```ts
function reuseKey(job: { triggerType: string; sourceDataSummary: string }): string {
  const canonical = canonicaliseForCache(job.sourceDataSummary);
  // canonicaliseForCache: lowercase, sort fields, trim whitespace,
  // replace ISO timestamps within ±1d, normalise number precision (3 sig figs).
  return sha256(`${job.triggerType}::${canonical}`);
}
```

The canonicalisation rules are deliberately tolerant — slight
input variations (different capitalisation, slightly different
date, rounding) hash to the same key. Aggressive enough to
maximise cache hits without conflating genuinely different
research questions.

### 3.2 Cache lookup order

1. Check `research_artifacts` for the user's own non-stale
   artifact with matching `reuseKey`. If found: cite + return,
   no gate, no spend.
2. (Future, not in MVP) check shared / cohort cache — only if
   the artifact opted into cross-user reuse (FS-020 § 9 model).
   Rule 23 MVP is per-user only.
3. If no cached artifact: proceed to gate (§ 4).

### 3.3 Stale handling

- Default TTL: 90 days for health-context triggers (`blood_test_pdf`,
  `dexa_scan`, `health_trend`, `readiness_anomaly`,
  `complex_journal`, `athlete_memory_synthesis`).
- Default TTL: 30 days for app-state triggers (`visual_app_audit`,
  most `custom`).
- TTL configurable per-user in settings.
- On TTL expiry: status flips `cached` → `stale`. Stale artifacts
  are NOT auto-purged (audit trail) but are NOT used for new
  citations. A new request with the same `reuseKey` creates a
  fresh job (no auto-rerun without Aaron approval).

### 3.4 Citation contract

Every future explanation that draws on a cached artifact MUST
include `cited_artifact_id` in its output and increment the
artifact's `citationCount`. The Admin/Dev approval centre
surfaces this so Aaron can see "this answer cited the 2026-04-15
DEXA research artifact" without re-deriving.

## 4. Approval gate flow + push UX

Reuses rule 21 state machine for the base states; adds 4
research-specific states (`running` / `imported` / `cached` /
`stale`).

### 4.1 Lifecycle

```
  cache check
    │
    ├─ HIT (non-stale) ─► cite cached artifact, no gate
    │
    └─ MISS or STALE ──► waiting_for_approval (push fires)
                              │
              ┌───────────────┼───────────────────┐
              │               │                   │
              ▼               ▼                   ▼
          approved         deferred             blocked
              │               │                   │
              ▼               │                   │
          running         (re-fire             (close)
              │           after deferred_until)
              │
              ▼
          imported    (Aaron pastes result back)
              │
              ▼
          cached      (artifact indexed + cite-able)
              │
              ▼
          stale       (after expiresAt; not auto-rerun)
```

### 4.2 Push payload (extends rule 21 + rule 22)

```ts
{
  title: `Deep research approval: ${triggerType}`,
  body: `${triggerContext} · External AI estimated cost: ${estimatedCostString} · Top priority: ${topPriorityContext}`,
  data: {
    gateId: string,
    gateState: 'waiting_for_approval',
    costClass: 'deep_research_external',
    triggerType: ResearchJob['triggerType'],
    reuseKey: string,
    estimatedCostString: string,
    promptModel: ResearchJob['promptModel'],
    promptSummary: string,            // ≤280 chars, redacted
    expiresAt: string,
    deepLink: 'lauburu://admin-dev/research/<gateId>',
  },
  actions: [
    { id: 'approve_in_app', title: 'Approve' },
    { id: 'defer',          title: 'Defer' },
    { id: 'copy_prompt',    title: 'Copy prompt' },
    { id: 'import_result',  title: 'Import result' },
  ],
}
```

`copy_prompt` action: opens the deep-link with the prompt
ready to copy (no re-fetch; Aaron taps once → prompt is on
clipboard, ready to paste into ChatGPT / Claude.ai).

`import_result` action: opens the deep-link with the import
modal pre-positioned. (Useful when Aaron has already run the
research externally and is returning to the app to paste the
result.)

## 5. Import-back contract

How Aaron's external research result gets back into the app.

### 5.1 Import modal

```
┌─ Import research result ─────────────────────────┐
│                                                  │
│ Trigger: blood_test_pdf · Job 8a3f...            │
│ Prompt: (was copied to clipboard 2h ago)         │
│                                                  │
│ Paste the external AI's response below:          │
│ ┌──────────────────────────────────────────────┐ │
│ │ <textarea — multiline>                       │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ [ Cancel ]   [ Import ]                          │
└──────────────────────────────────────────────────┘
```

### 5.2 Import parser pipeline

1. **Strip medical-advice / causation phrases.** Banned-phrase
   regex: "you should", "this will help", "is safe", "is
   dangerous", "stop taking", "increase your dose", "caused by",
   "causes", "is causing", "leads to". Every match is logged
   in `flagsStripped` and the offending line is reduced to
   the safer phrasing OR dropped entirely.
2. **Truncate / chunk if oversize.** Default cap: 32k chars per
   artifact; longer results are stored as multi-part.
3. **Extract citations.** Detect URL patterns + linked-text
   tuples; store in `citations[]`.
4. **Generate `parsedSummary`.** Pure deterministic — no LLM
   call (rule 22 cost class: `free_deterministic`). Algorithm:
   first paragraph + bullet list extraction + URL-stripped
   summary, capped at 500 chars.
5. **Verify reuseKey integrity.** Recompute `reuseKey` from the
   job's `sourceDataSummary`; confirm it matches the job row.
   This guards against a spoofed import targeted at a different
   reuseKey.
6. **Store + flip status.** Artifact written → status `cached`
   → push notification: "Research artifact cached: <triggerType>".

### 5.3 Confidence inheritance

Per rule 9, any health-context citation derived from the
cached artifact carries:
- `confidence: 'provisional'`
- `source: 'imported_external_ai_research'`
- `cited_artifact_id: <id>`
- `cited_artifact_imported_at: <timestamp>`
- `disclaimer: "General background only. Not medical advice. Associations only, not causation."`

The disclaimer is rendered alongside any UI surface that uses
the artifact.

## 6. Safety / privacy

**Hard rules.**

1. **Minimal redacted context only.** `sourceDataSummary` is
   structural / counts / ranges — never raw journal text, raw
   metric values with PII, or screenshots without explicit
   per-call opt-in.
2. **User approval before any sensitive data leaves the app.**
   Rule 22 privacy floor applies. Even on Approve, the prompt
   shown to Aaron lists exactly what will leave the device;
   Aaron sees the redaction before pasting.
3. **No medical advice in the imported result.** Banned-phrase
   regex strips at import; health-context artifacts carry
   provisional confidence + disclaimer.
4. **No causation claims.** "Associated with" / "co-occurred
   with" only. Banned: "caused by", "leads to", "is causing".
5. **No personal AI history exposure.** ChatGPT / Claude.ai
   history is the user's; this app does NOT crawl it back.
   The only path is Aaron's manual paste of the result.
6. **Artifact storage is per-user RLS-gated.** No cross-user
   reads in MVP. Cohort sharing is FS-020 § 9 territory.
7. **Imported content is logged but never auto-shared.** No
   broadcast to other users, MCP public surfaces, or the
   shared dictionary.

## 7. Codex handoff prompt — implementation

Stored as ready-to-paste. Aaron MUST explicitly approve dispatch
before this prompt goes to Codex.

```
PROMPT-ID: CODEX-FS-XXX-DEEP-RESEARCH-OFFLOAD-IMPL-01
TYPE: CODEX
LANE: Supabase research_jobs / research_artifacts schema +
      Worker MCP tools + mobile import modal + import parser

MCP-FIRST: call project.get_current_state. Bridge → Supabase
direct upsert is LIVE; bridge:snapshot for end-of-task cadence
per rule 12.

Reference (read first):
- docs/DEEP_RESEARCH_OFFLOAD_SPEC.md (this doc — canonical).
- docs/AI_SPEND_GATES_SPEC.md (rule 22 — deep_research_external
  cost class is the only path that triggers this).
- docs/HUMAN_APPROVAL_GATE_SPEC.md (rule 21 — state machine
  reused; new states running | imported | cached | stale
  extend the base set).
- docs/OPERATING_RULES.md § 23 (rule body).

GOAL
Wire the deep-research offload end-to-end:
- Supabase: research_jobs + research_artifacts tables, RLS
  by auth.uid().
- Worker: project.research_job_create + research_job_update +
  research_artifact_import + research_artifact_lookup_by_reuseKey
  MCP tools (admin token).
- Mobile: research-jobs panel in admin-dev (or user settings),
  4-button gate UI per rule 23 § 4.2.
- Mobile: import-result modal per § 5.1; banned-phrase parser
  per § 5.2.
- Mobile: cached-artifact citation surface — when a future
  request hits a cache match, show the citation chip.

SCOPE PHASE 1 (this prompt)
1. Supabase migration (additive): research_jobs +
   research_artifacts tables per § 1; indexes on (user_id,
   reuseKey) for fast lookup; RLS by auth.uid().
2. Worker: 4 MCP tools (admin token):
   - project.research_job_create(triggerType,
     triggerContext, sourceDataSummary, promptModel)
     → returns { jobId, reuseKey, cacheHit, cachedArtifactId? }.
   - project.research_job_update(jobId, action, reason?).
     Validates state transitions per § 4.1.
   - project.research_artifact_import(jobId, rawText)
     → applies the import parser pipeline (§ 5.2) and
     returns the artifact row.
   - project.research_artifact_lookup_by_reuseKey(reuseKey)
     → returns the latest non-stale artifact for the user
     OR null.
3. Mobile: deep-research approval centre panel + 4-button
   gate UI sharing the rule 21 push wiring.
4. Mobile: import-result modal with banned-phrase parser.
   Pure deterministic — no LLM call.
5. Mobile: citation chip rendered wherever a cached artifact
   is consumed.
6. Tests: banned-phrase parser strips every phrase in § 5.2.1;
   reuseKey hashing matches across mobile + Worker for
   identical inputs; cache lookup returns non-stale matches.

ANTI-RULES
- No payload PII in push or log surfaces.
- No raw sensitive data sent to any AI without per-call
  approval.
- Honour rule 11 (MCP-first): cache lookup is the FIRST
  step.
- Honour rule 21: state machine extension is additive — no
  silent base-state deletions.
- Honour rule 9: imported health-context artifacts carry
  confidence: provisional + disclaimer.
- No medical advice / no causation claims survive import.
- No EAS build dispatched from this prompt.
- No iOS-only or Android-only.

VERIFICATION
- cd apps/mobile && npx tsc --noEmit clean.
- cd cloudflare-worker && npx tsc --noEmit clean.
- npm run rules:test PASS (23 rules, doc parity).
- npm run mcp:test:public-redaction PASS.
- New contract test: banned-phrase parser strips every
  phrase listed in § 5.2.1; reuseKey hashing is
  deterministic + matches across mobile + Worker.
- Manual: simulate cache miss → gate fires → approve →
  copy prompt → paste external result → artifact cached.
- Manual: re-issue identical request → cache hit, no gate,
  citation chip rendered.

OUTPUT (small)
- Status: implementation-complete-awaiting-Agent-confirmation
  / partial / blocked
- Supabase migration name:
- New Worker tools:
- Existing files touched:
- New files added:
- Tests run:
- MCP / bridge writeback evidence:
- Open questions for Aaron / Agent confirmation:
- Recommendation for follow-up (FS-XXX next batch — e.g.
  cohort artifact sharing model under FS-020 § 9):
```

Approval-gated: do NOT dispatch this prompt without Aaron's
explicit approval per rule 7 + rule 13 + rule 21.

## 8. Anti-rules

- **No re-running cached research.** A non-stale artifact is
  the answer; the gate doesn't fire.
- **No silent stale-rerun.** Stale artifacts require a NEW
  approval gate to refresh.
- **No medical advice / causation claims surviving import.**
  Banned-phrase regex is non-negotiable.
- **No raw sensitive data without per-call approval.** Rule 22
  privacy floor.
- **No background research jobs.** Every research job is
  user-triggered or coach-triggered; never a silent crawl.
- **No public exposure of artifacts.** RLS-gated, per-user.
- **No artifact deletion without user action.** Stale ≠ deleted;
  audit trail preserved.
- **No cross-user attribution.** Artifacts are per-user;
  cohort sharing is FS-020 § 9 design-only territory until
  Aaron approves a separate batch.

## 9. Cross-references

- `docs/OPERATING_RULES.md` § 23 — canonical rule body.
- `docs/AI_SPEND_GATES_SPEC.md` — rule 22 cost classes;
  deep_research_external is the only entry to rule 23.
- `docs/HUMAN_APPROVAL_GATE_SPEC.md` — rule 21 state machine
  extended here.
- `docs/JOURNAL_IMPORT_NORMALIZE_INSIGHTS_SPEC.md` § 6 — the
  static research-snippets surface; rule 23 cached artifacts
  are user-private and DO NOT flow into the shared
  `journal-research-snippets.ts` file.
- `cloudflare-worker/src/data/CONNECTOR_SANITIZATION_RULES.md`
  — privacy floor for `sourceDataSummary` redaction.
- `docs/HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md` —
  confidence labels artifacts inherit per rule 9.
