# Athlete memory + style evolution spec

How long-form patterns of an individual athlete's training,
competition, technique evolution, and observed tendencies
get captured + analysed without the app overclaiming or
making causal assertions.

This is **doc only**. No app code. No EAS build.

## 0. Relationship to existing rules + specs

Athlete memory + style evolution are the **highest-context**
surfaces in the app — they look at months of journal entries,
training, competition footage, and technique outcomes. They
inherit the strictest rules:

| Rule / Spec | What it gives this surface |
|---|---|
| Rule 9 (provisional health/skill claims) | Hedge language only; no "you should X". |
| Rule 22 (AI spend gate) | Long-context analysis = `expensive_ai`; gate fires per pass. |
| Rule 23 (deep research offload + cache) | Per-athlete style synthesis is `athlete_memory_synthesis` triggerType; cached by reuseKey. |
| `docs/EVIDENCE_DRIVEN_TECHNIQUE_EVOLUTION_SPEC.md` | Hypothesis-only language for any technique-effectiveness inference; only `published` techniques may be cited authoritatively. |
| `docs/JOURNAL_IMPORT_NORMALIZE_INSIGHTS_SPEC.md` § 6 + § 8 | Pattern engine + research-snippets surface that this layer queries. |
| `docs/MCP_MEMORY_ARCHITECTURE_SPEC.md` | `kind: 'memory'` + `kind: 'audit'` artifacts the surface ingests. |
| Forever Improve § AI video analysis | Confidence ladder this surface inherits for video-derived observations. |
| Forever Improve § Verified instructional mastery | Per-technique mastery the style-evolution surface aggregates over. |

## 1. Athlete memory — what it is

A per-user, RLS-gated, opt-in body of curated artifacts
spanning their training history, competition results,
technique mastery state, journal patterns, and AI-derived
observations (all hedged per rule 9).

### 1.1 Components

| Component | Source | Visibility |
|---|---|---|
| **Training timeline** | `journal_events` (FS-018) + manual logs | per-user |
| **Competition results** | manual entry + competition footage analysis (Forever Improve § AI video analysis) | per-user |
| **Technique mastery state** | `technique_candidates` per `EVIDENCE_DRIVEN_TECHNIQUE_EVOLUTION_SPEC` + verified-mastery layer | per-user |
| **Journal pattern observations** | `metric_effect_windows` + `journal_dose_periods` (FS-018) | per-user |
| **Coach signoffs received** | `coaching_relationships` + `private_session` (FS-XXX coaching) | per-user |
| **AI synthesis cache** | rule 23 research artifacts with `triggerType: 'athlete_memory_synthesis'` | per-user |
| **Saved instructional references** | published technique nodes the athlete bookmarked | per-user |

No cross-user reads in MVP. Cohort aggregates (FS-020 § 9
territory) are explicitly out of scope here.

### 1.2 Schema

```ts
interface AthleteMemorySnapshot {
  user_id: string;
  generatedAt: string;
  windowStart: string;                  // ISO; default 90d back
  windowEnd: string;                    // ISO; default now
  trainingTimeline: Array<{ date: string; sessions: number; totalMinutes: number; highIntensity: boolean }>;
  competitionResults: Array<{ event: string; date: string; outcome: string; footage_artifact_id?: string }>;
  techniqueMasteryState: Array<{ technique_id: string; tier: 'claim_only' | 'self_video_attached' | 'verified_by_coach' | 'verified_by_peers'; lastReviewedAt: string }>;
  journalPatterns: Array<{ pattern_id: string; window: 'same_day' | 'next_day' | 'rolling_3' | 'rolling_7'; confidence: 'provisional' | 'low' | 'medium'; description: string }>;
  coachSignoffs: Array<{ coach_user_id: string; technique_id: string; signedAt: string; confidence: 'high' }>;
  aiSynthesisRefs: Array<{ artifact_id: string; reuseKey: string; citationCount: number }>;
  savedInstructionals: Array<{ technique_id: string; bookmarkedAt: string }>;
}
```

A snapshot is generated on demand (Aaron taps "View athlete
memory" in admin-dev / personal-profile surface) — never on
a background schedule (rule 22: long-context = expensive).

## 2. Style evolution — what it is

Higher-level pattern analysis OVER the athlete memory
snapshot. Asks questions like "how has this athlete's style
changed over 90 days" — strictly hypothesis language, never
authoritative.

### 2.1 What style evolution does NOT do

- Never claims "you've gotten better at X" or "your guard
  has improved" — those are objective claims requiring
  external evidence (competition results signoff).
- Never compares the athlete to a population baseline
  (rule 9 / FS-018 § 8.3 baseline-is-user's-own).
- Never auto-promotes a technique to the user's "favourite
  positions" without explicit user signoff.
- Never publishes the analysis to anyone except the athlete
  + their consenting coach (per FS-XXX coaching).

### 2.2 What style evolution does

| Question | Answer pattern (rule 9 honoured) |
|---|---|
| "What positions am I attempting most?" | Counts only — frequency table from training timeline + journal events. NO inference about whether the athlete is "good" at them. |
| "What positions did I succeed in last 30 days?" | Outcome breakdown from journal `outcome` fields (success / partial / failure / inconclusive). Hedge: "Recorded as success in N of M attempts; outcome labelling is user-reported." |
| "What's changed since 90 days ago?" | Frequency delta + outcome delta with explicit confidence ladder. Hedge: "Provisional — 47 observations across 90 days." |
| "What does my style look like?" | NEVER answered as a definitive claim. Surfaced as: "Frequent positions across last 90 days: [list]. Frequent successful exits: [list]. Coach review: [coach summary if signed off]." Aaron decides if this matches his self-perception. |
| "How does my game compare to <famous grappler>?" | NOT in scope. The app does NOT do peer comparison. External research (rule 23) optional but redirected to Aaron via export-prompt. |

### 2.3 Style evolution analysis pipeline

1. **Build athlete memory snapshot** (§ 1.2 — pure
   deterministic over per-user data).
2. **Classify request**: what kind of question is being
   asked? Free-deterministic / cheap_ai / expensive_ai
   per rule 22.
3. **Cache check**: if the answer is cacheable (per rule
   23), check `research_artifacts` with `reuseKey =
   sha256('athlete_style_evolution::' + user_id +
   '::' + canonicalised_window + '::' + question_hash)`.
4. **Approval gate** (rule 22): if `expensive_ai`, fire
   gate per `PUSH_APPROVAL_AUTOMATION_SPEC`.
5. **Run analysis** (deterministic OR LLM per cost class).
   Output structured: per-position counts + per-outcome
   deltas + confidence ladder + hedge phrases.
6. **Store as memory artifact** per
   `MCP_MEMORY_ARCHITECTURE_SPEC` `kind: 'memory'`,
   `topic: 'athlete_style_evolution'`,
   `confidence: 'low'` default (bumps with multiple runs
   converging).
7. **Surface in admin-dev** with explicit disclaimer:
   "Provisional. Associations only. Not a coaching
   recommendation."

### 2.4 Output format

UI mockup:

```
┌─ Style evolution — last 90 days ───────────────────┐
│                                                    │
│ Provisional · 142 training events · 8 competition  │
│ events · 2 coach signoffs.                         │
│                                                    │
│ Frequent positions:                                │
│   • Half guard (top)        47 attempts · 28 success
│   • Closed guard (bottom)   34 attempts · 12 success
│   • Mount (top)             29 attempts · 19 success
│   • Side control (bottom)   22 attempts · ?         │
│                                                    │
│ Δ vs prior 90 days:                                │
│   • Half guard top frequency +18% (low confidence) │
│   • Closed guard bottom -23% (low confidence)      │
│                                                    │
│ Coach review (last signoff 14 days ago):           │
│   "Half guard top sweeps look stronger; back-take  │
│   exits still need work" — Coach Alex.             │
│                                                    │
│ Not a coaching recommendation. Associations only.  │
│ Discuss with your coach for actionable feedback.   │
│ [ Save snapshot ]   [ Export to coach (with consent) ]
└────────────────────────────────────────────────────┘
```

Anti-claim phrases enforced at the renderer:
- NEVER: "You're getting better at X" / "Your style is X" /
  "You should focus on X" / "X is your weakness".
- ALWAYS: "Recorded as", "associated with", "frequency",
  "user-reported", "provisional", "discuss with your
  coach".

## 3. AI video analysis integration

Per Forever Improve § AI video analysis. Style evolution
consumes the AI-flagged annotations (with their confidence
tier) but never elevates them past the tier set by the
human review:

- `ai_only_low_confidence` annotations contribute to
  position counts but not to outcome claims.
- `ai_only_medium_confidence` annotations contribute to
  count + tentative outcome.
- `coach_reviewed` annotations contribute to outcome.
- `coach_signoff` annotations are quoted directly with
  attribution.

## 4. Privacy + safety floor

1. **Athlete memory is per-user RLS-gated.** No cross-user
   reads.
2. **Coach reads** require explicit per-pair consent per
   FS-XXX private coaching (`coaching_relationships`).
3. **Aaron can revoke** at any time; existing coach copies
   stay in the audit trail but new reads are blocked.
4. **AI analysis** uses minimal redacted context per rule 22
   privacy floor; raw journal text and identifiable
   competition footage are NOT sent to external AI without
   per-call approval.
5. **Cohort aggregation** is FS-020 § 9 territory; out of
   scope here.
6. **External-AI exports** (rule 23 deep research) for
   athlete-memory-synthesis MUST have `containsRealUserData:
   true` flag set; the operator must redact before pasting.

## 5. Codex handoff prompt — implementation

```
PROMPT-ID: CODEX-FS-XXX-ATHLETE-MEMORY-STYLE-EVOLUTION-IMPL-01
TYPE: CODEX
LANE: Supabase athlete_memory_snapshots view + Worker
      synthesis tool + admin-dev / personal-profile UI

MCP-FIRST: call project.get_current_state.

Reference (read first):
- docs/ATHLETE_MEMORY_AND_STYLE_EVOLUTION_SPEC.md (this doc).
- docs/EVIDENCE_DRIVEN_TECHNIQUE_EVOLUTION_SPEC.md (technique
  layer this aggregates).
- docs/JOURNAL_IMPORT_NORMALIZE_INSIGHTS_SPEC.md (FS-020
  pattern engine this consumes).
- docs/AI_SPEND_GATES_SPEC.md (rule 22 cost class).
- docs/DEEP_RESEARCH_OFFLOAD_SPEC.md (rule 23 cache).
- docs/MCP_MEMORY_ARCHITECTURE_SPEC.md (artifact schemas).

GOAL
Wire athlete memory + style evolution:
- Supabase: athlete_memory_snapshots view (or table) per
  § 1.2. Aggregates over journal_events + journal_items +
  technique_candidates + technique_evidence +
  metric_effect_windows + coaching signoffs +
  research_artifacts.
- Worker: project.athlete_memory_snapshot(window?) +
  project.style_evolution_run(window?, question?). Latter
  fires rule 22 cost gate when expensive_ai classified.
- Mobile: personal-profile surface (admin-dev for now;
  user-facing later) showing the snapshot + style evolution
  with hedge phrases.

SCOPE PHASE 1 (this prompt)
1. Supabase view (READ-only): athlete_memory_snapshot_v1
   joining the source tables.
2. Worker tools per goal.
3. Mobile UI: admin-dev panel rendering the snapshot with
   anti-claim renderer (banned-phrase enforcer at output
   layer).
4. AI spend integration: style_evolution_run fires
   classify_ai_call (rule 22) before any LLM pass.
5. Cache integration: reuseKey computed per § 2.3.
6. Banned-phrase contract test: snapshot renderer NEVER
   emits "you should" / "you're getting better" / etc.

ANTI-RULES
- Never claim "your style is X" or "you've improved".
- Never compare to other athletes.
- No cross-user reads (RLS enforced).
- AI analysis uses redacted minimal context only.
- No EAS build dispatched.

VERIFICATION
- Schema test: snapshot view returns deterministic shape.
- Banned-phrase test: every UI surface stripped of
  forbidden phrases.
- Manual: synthetic 90d data → snapshot → style evolution
  run with cost-class assertion.

OUTPUT (small)
- Status:
- Supabase view name:
- New Worker tools:
- Existing files touched:
- New files added:
- Tests run:
- MCP / bridge writeback evidence:
- Open questions:
- Recommendation for follow-up:
```

Approval-gated.

## 6. Anti-rules

- **No "your style is X" claims.** Hedge language only.
- **No cross-athlete comparison.** No leaderboards in this
  surface; cohort is separate.
- **No silent AI elevation.** Confidence ladder enforced at
  renderer.
- **No raw footage to external AI without approval.**
  Rule 22 privacy floor.
- **No coach broadcast.** Per-pair consent only.
- **No "verified" claim** about style without explicit
  Aaron-on-device confirmation (rule 9).

## 7. Cross-references

- `docs/EVIDENCE_DRIVEN_TECHNIQUE_EVOLUTION_SPEC.md` —
  technique state machine this aggregates.
- `docs/JOURNAL_IMPORT_NORMALIZE_INSIGHTS_SPEC.md` —
  pattern engine + § 8 windowed analysis this consumes.
- `docs/AI_SPEND_GATES_SPEC.md` — rule 22 cost classes.
- `docs/DEEP_RESEARCH_OFFLOAD_SPEC.md` — rule 23 cache.
- `docs/MCP_MEMORY_ARCHITECTURE_SPEC.md` — artifact schemas
  this writes into.
- `docs/APP_DEVELOPMENTS.md` § Forever Improve §§ AI video
  analysis / Verified instructional mastery / Private
  coaching — paired surfaces.
- `docs/OPERATING_RULES.md` § 9 / § 18 / § 22 / § 23.
