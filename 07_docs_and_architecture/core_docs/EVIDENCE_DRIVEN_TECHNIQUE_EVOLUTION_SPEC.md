# Evidence-driven technique evolution — spec

How proposals for new grappling techniques, variations, or
system refinements flow through the app from **raw hypothesis**
to **public instructional content** without the app ever
claiming unverified technique effectiveness. Every state
transition past `suggested` requires explicit human signoff
(Aaron and/or a collaborating coach). AI flags candidates and
observes patterns — it never asserts effectiveness.

This is **spec only**. No app code. No Worker code change.
No EAS build. Implementation is a Codex follow-up batch
gated on Aaron approval per rule 7 + rule 13 + rule 21.

## 0. Relationship to existing rules + Forever Improve categories

| Pairs with | Why |
|---|---|
| Rule 9 (provisional health/skill claims) | Technique state tier maps directly to rule 9's confidence ladder. `validated` is `medium` confidence at most until live-rolled across opponents; `published` instructional content honours the rule-9 hedge language ("works often when…", never "always works"). |
| Rule 18 (action ledger) | Each state transition is recorded as a ledger row with `actorId`, `reason`, evidence references. |
| Rule 21 (approval gate) | `approved_private` / `instructional_ready` / `published` transitions are approval gates that surface to Aaron's phone via push. |
| Rule 22 (AI spend gate) | AI hypothesis generation and AI video analysis on candidate techniques use the AI-spend ladder; vision-heavy footage analysis is `expensive_ai`. |
| Rule 23 (deep research offload + cache) | Per-technique research artifacts (e.g. "what does external AI say about this position?") cache by `reuseKey` so the same research never re-runs. |
| Forever Improve § AI video analysis | Confidence ladder + manual review layers govern how footage promotes a candidate. |
| Forever Improve § Verified instructional mastery | A `published` technique node feeds the per-user mastery taxonomy with a stable id. |
| Forever Improve § Private coaching | Coach signoff is the highest evidence tier for state transitions. |
| Forever Improve § User feedback incentives | A `suggested` proposal authored by a non-coach user earns reward points if it reaches `validated` (per the user-feedback contributor reputation surface). |

## 1. State machine

```
                        suggested
                           │
              ┌────────────┼────────────┐
              ▼                         ▼
        approved_private          rejected
              │                         ▲
              ▼                         │
         testing_live ──────────────────┤
              │                         │
              ▼                         │
     evidence_accumulating ──────────► deprecated
              │                         ▲
              ▼                         │
          validated ────────────────────┤
              │                         │
              ▼                         │
      instructional_ready ──► rejected ─┤
              │                         │
              ▼                         │
            filmed                      │
              │                         │
              ▼                         │
          published ────► deprecated ◄──┘
```

Forward transitions all require explicit human signoff
(Aaron or a collaborating coach). Backward transitions
(rejection / deprecation) preserve the full audit trail —
the candidate is never deleted.

| State | Meaning | Transition rule | Visibility |
|---|---|---|---|
| `suggested` | AI / user / coach proposed a new technique or refinement. Untested. | Created via `project.technique_propose` (any user). | Private to author + Aaron. |
| `approved_private` | Aaron (or delegated coach) accepted for private testing. Hidden 3D-map node created. | Aaron-or-coach signoff per rule 21 gate. | Private to Aaron + collaborating coaches only. |
| `testing_live` | Technique being tested in live rolling / competition / drill. Footage starts uploading against the hidden node. | Aaron flips state when first footage is attached. | Same as approved_private. |
| `evidence_accumulating` | Multiple footage attempts logged (default ≥3 distinct sessions). AI may surface pattern observations — associations only, never effectiveness claims. | Auto-flips when footage threshold met; manually flipable earlier. | Same as approved_private. |
| `validated` | Enough evidence + coach review to consider reliably reproducible across opponents / contexts. | Coach signoff required. Default minimum bar: ≥10 successful executions across ≥3 different opponents. | Same as approved_private. |
| `instructional_ready` | Aaron decides this is worth filming. Filming queued. | Aaron-only signoff per rule 21 gate. | Private. |
| `filmed` | Instructional filmed but not yet published. | Aaron flips after filming + edit. | Private. |
| `published` | Public node added to the 3D map. Viewable per user / coaching / community visibility settings. | Aaron-only signoff per rule 21 gate (publishing is a public-release equivalent — rule 7 cost-control framing applies). | Public (subject to community-tier opt-in). |
| `rejected` | Suggestion deemed unworkable. Stays in audit trail. | Anyone in approval chain can reject; reason mandatory. | Private to participants. |
| `deprecated` | A previously-validated or published technique no longer holds (e.g. counter discovered). | Aaron-or-coach signoff; deprecation reason mandatory. | Public flip (if previously published) — the public node carries a deprecated banner with reason. |

## 2. Schema

### 2.1 `technique_candidates`

```sql
create table public.technique_candidates (
  id uuid primary key default gen_random_uuid(),
  proposed_by uuid not null references auth.users(id) on delete set null,
  proposer_role text not null check (proposer_role in ('user','coach','aaron','ai')),
  proposed_at timestamptz not null default now(),
  source_type text not null,                -- 'manual' | 'ai_pattern' | 'video_observation' | 'cohort_signal'
  technique_name text not null,             -- short canonical name
  technique_summary text not null,          -- ≤2000 chars
  position_taxonomy_id text,                -- nullable; links into the 3D map taxonomy when a parent position exists
  variant_of_technique_id uuid references public.technique_candidates(id),  -- self-FK if this refines another candidate
  state text not null check (state in (
    'suggested','approved_private','testing_live','evidence_accumulating',
    'validated','instructional_ready','filmed','published','rejected','deprecated'
  )) default 'suggested',
  state_history jsonb not null default '[]'::jsonb,  -- append-only list of {state, by, at, reason}
  evidence_count integer not null default 0,         -- count of attached evidence rows
  successful_evidence_count integer not null default 0,
  coach_signoff_count integer not null default 0,
  hidden_map_node_id uuid,                  -- nullable; set when approved_private creates a hidden node
  public_map_node_id uuid,                  -- nullable; set when published creates the public node
  publish_at timestamptz,
  deprecate_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.technique_candidates enable row level security;
-- RLS: rows visible to proposer + Aaron + collaborating coaches via coaching_relationships;
-- public reads only when state = 'published' AND public_map_node_id is set.
```

### 2.2 `technique_evidence`

```sql
create table public.technique_evidence (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid not null references public.technique_candidates(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  evidence_type text not null check (evidence_type in (
    'training_drill','training_sparring','competition','coach_signoff','user_signoff','ai_observation'
  )),
  outcome text check (outcome in ('success','partial','failure','inconclusive')),
  footage_class text check (footage_class in ('competition','training_sparring','drill','instructional_reference')),
  video_artifact_id uuid,                   -- → research_artifacts (rule 23) when video analysed
  ai_observation_text text,                 -- ≤500 chars; hypothesis language only, no effectiveness claims
  coach_signoff_user_id uuid references auth.users(id),
  notes text,
  recorded_at timestamptz not null default now()
);

alter table public.technique_evidence enable row level security;
-- RLS: same visibility as parent candidate; private until candidate.state = 'published'.
```

### 2.3 `technique_state_transitions` (audit ledger)

```sql
create table public.technique_state_transitions (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid not null references public.technique_candidates(id) on delete cascade,
  from_state text,
  to_state text not null,
  by_user_id uuid references auth.users(id) on delete set null,
  by_role text not null check (by_role in ('user','coach','aaron','system')),
  reason text not null,
  evidence_refs uuid[] not null default array[]::uuid[],
  transitioned_at timestamptz not null default now()
);

alter table public.technique_state_transitions enable row level security;
-- Append-only; no updates.
```

## 3. Hard rules

1. **AI must NOT claim unproven technique effectiveness.** AI
   output for any state in {`suggested`, `approved_private`,
   `testing_live`, `evidence_accumulating`} MUST use
   hypothesis language: "possible improvement", "observed in
   N attempts", "candidate position". NEVER: "this technique
   works", "this beats X", "use this against Y".
2. **Hypothesis until `validated`.** No technique is asserted
   reliable until state ≥ `validated` AND a coach signoff is
   recorded.
3. **Only `published` is user-viewable.** Earlier states stay
   private to the author + Aaron + collaborating coaches.
   Other users see them only with explicit per-candidate
   invite (a future opt-in for cohort beta-testing).
4. **Footage-backed transitions.** Promotion from
   `testing_live` → `evidence_accumulating` → `validated`
   requires uploaded footage proof per the AI-video-analysis
   confidence ladder (Forever Improve § AI video analysis).
5. **No app-claimed grappling authority.** The app surfaces
   evidence; humans (Aaron, coaches) make every promotion /
   rejection decision. Every state transition past
   `suggested` requires human signoff. AI never auto-promotes.
6. **No silent deprecation.** A previously-published technique
   that's deprecated MUST surface a banner on the public node
   with the deprecation reason. The original instructional
   stays viewable in the audit trail for honesty.
7. **Reuses rule 23 cache for per-technique research.** When
   external AI is asked about a technique (mechanism, history,
   counters), the result is cached as a research artifact and
   cited; same research never re-runs.
8. **Privacy floor (rule 22).** Footage stays per-user;
   sharing with coaches requires explicit consent. AI analysis
   over footage uses the AI-spend gate.

## 4. Approval-gate integration (rule 21)

Three of the state transitions are explicit approval gates
that surface to Aaron's phone via push:

| Transition | Gate type | Push payload |
|---|---|---|
| `suggested` → `approved_private` | Aaron-only | "Approve technique candidate: <name>" + summary + hypothesis source. Defer = stays in `suggested`. |
| `validated` → `instructional_ready` | Aaron-only | "Ready to film: <name>" + evidence summary + coach-signoff count. Defer = stays in `validated`. |
| `filmed` → `published` | Aaron-only | "Publish technique node: <name>" + public-visibility audit (rule 7-equivalent for public release). Defer = stays in `filmed`. |

The remaining transitions (`approved_private` → `testing_live`,
`testing_live` → `evidence_accumulating`, `evidence_accumulating`
→ `validated`, `instructional_ready` → `filmed`, any →
`rejected` / `deprecated`) write to the ledger but do NOT
require push gates because they happen during routine training
+ filming work where Aaron is already engaged.

## 5. 3D-map-node integration

The app's existing 3D grappling map (FS-XXX, separate doc)
gets two new node types:

- **Hidden node** (state `approved_private` through
  `instructional_ready`): visible only to Aaron + linked
  coaches. Carries a `state_pill` showing the current
  candidate state. NOT linked from public map exploration.
- **Public node** (state `published`): visible per the user /
  coaching / community visibility settings. Carries the
  filmed instructional + linked evidence (counts only;
  raw evidence stays private). When deprecated, the public
  node renders the deprecation banner and a link to the
  successor candidate (if Aaron designated one).

Map taxonomy stability: `position_taxonomy_id` on a candidate
is the link into the existing taxonomy. A new candidate can
either attach to an existing position or propose a brand-new
position node (which itself goes through the same state
machine).

## 6. AI hypothesis sources (state `suggested`)

How candidates are first proposed.

- **AI pattern observation.** When AI video analysis
  (Forever Improve § AI video analysis) detects a recurring
  pattern across multiple clips that doesn't map to an
  existing taxonomy node, it MAY auto-propose a new
  candidate with `proposer_role: 'ai'`,
  `source_type: 'ai_pattern'`. Aaron sees the proposal in
  the candidates inbox. AI never advances state past
  `suggested`.
- **User suggestion.** User-typed proposal in the app.
  `proposer_role: 'user'`, `source_type: 'manual'`. Earns
  user-feedback-incentives reward if reaches `validated`.
- **Coach suggestion.** Coach-typed proposal during a
  private session. `proposer_role: 'coach'`,
  `source_type: 'manual'`.
- **Aaron suggestion.** Aaron's own proposal during training
  / drilling / journaling.
- **Cohort signal** (future). When N opted-in users
  spontaneously try a similar variation in their own
  training, the cohort surface flags it as a candidate.
  Default OFF until aggregate-cohort thresholds (FS-020 § 9)
  are wired.

## 7. Codex handoff prompt — implementation

Stored as ready-to-paste. Aaron MUST explicitly approve
dispatch before this prompt goes to Codex.

```
PROMPT-ID: CODEX-FS-XXX-EVIDENCE-DRIVEN-TECHNIQUE-EVOLUTION-IMPL-01
TYPE: CODEX
LANE: Supabase technique_candidates / technique_evidence /
      technique_state_transitions schema + Worker MCP tools
      + mobile candidates inbox + integration with rule 21
      approval gate

MCP-FIRST: call project.get_current_state. Bridge → Supabase
direct upsert is LIVE; bridge:snapshot for end-of-task cadence
per rule 12.

Reference (read first):
- docs/EVIDENCE_DRIVEN_TECHNIQUE_EVOLUTION_SPEC.md (this
  doc — canonical).
- docs/HUMAN_APPROVAL_GATE_SPEC.md (rule 21 — gate state
  machine reused for the 3 push-gated transitions).
- docs/AI_SPEND_GATES_SPEC.md (rule 22 — vision-heavy
  analysis uses the AI-spend gate).
- docs/DEEP_RESEARCH_OFFLOAD_SPEC.md (rule 23 — per-
  technique research artifacts cache here).
- docs/APP_DEVELOPMENTS.md § Forever Improve.

GOAL
Wire the technique-evolution backlog end-to-end:
- Supabase: 3 new tables per § 2 of the spec, RLS-gated.
- Worker: project.technique_propose / technique_state_advance
  / technique_evidence_attach / technique_signoff MCP
  tools (admin token for Aaron's transitions; per-pair
  RLS for coach signoffs; user-only for own proposals).
- Mobile: candidates inbox panel in admin-dev (Aaron's
  approval queue) + per-candidate detail view + evidence
  upload modal.

SCOPE PHASE 1 (this prompt)
1. Supabase migration (additive): 3 tables per § 2; indexes
   on (proposed_by), (state), (variant_of_technique_id);
   RLS policies per the inline comments; CHECK constraints
   on state + role enums.
2. Worker: project.technique_propose (any-auth, user-scoped) →
   creates candidate in 'suggested'.
   project.technique_state_advance(candidateId, toState,
   reason, evidenceRefs?) (admin or per-pair coach token) →
   validates transition + writes ledger row + emits rule 21
   gate where required.
   project.technique_evidence_attach(candidateId, evidence)
   → appends to technique_evidence + updates evidence_count
   on parent candidate.
   project.technique_signoff(candidateId, evidenceRefs)
   (per-pair coach token only) → records coach_signoff +
   may auto-flip evidence_accumulating → validated when
   thresholds met.
3. Mobile: admin-dev candidates inbox panel — list pending
   proposals + each row's state + actions (Approve / Defer
   / Reject for the 3 gated transitions).
4. Mobile: per-candidate detail view — state history,
   evidence list, hidden-map-node link if assigned, footage
   playback (links to existing video module).
5. Mobile: evidence upload modal — captures evidence_type +
   outcome + footage_class + optional video upload (gated
   by rule 22 if AI analysis is requested).

ANTI-RULES
- AI MUST NOT advance state past 'suggested'. Hard
  enforcement at the Worker tool layer: project.technique_state_advance
  rejects calls where caller_role = 'ai'.
- No effectiveness claims in any AI-generated text. Worker
  output sanitiser strips banned phrases: "this works",
  "use this against", "is effective", "guaranteed to",
  "always wins". Logs stripped phrases.
- No public visibility for non-published candidates. RLS
  enforces; a contract test confirms no public-safe tool
  ever exposes a non-published candidate's name or
  summary.
- No silent deprecation of public nodes. A deprecation that
  affects a published technique MUST set deprecate_reason
  and surface the banner.
- No EAS build dispatched from this prompt; build approval
  follows Aaron's separate gate per rule 7.
- No iOS-only or Android-only — both platforms required for
  parity (rule 14).

VERIFICATION
- cd apps/mobile && npx tsc --noEmit clean.
- cd cloudflare-worker && npx tsc --noEmit clean.
- npm run rules:test PASS (23 rules — count unchanged; this
  spec did not add a new rule).
- npm run mcp:test:public-redaction PASS — public-safe
  surface MUST NOT include any non-published candidate
  data; new contract test asserts this.
- New banned-phrase contract test for AI output sanitiser.
- Manual: simulate suggested → approved_private gate;
  confirm push fires (rule 21) + Aaron approves on phone.
- Manual: attach 3 evidence rows; confirm
  evidence_count auto-updates; confirm auto-flip from
  testing_live → evidence_accumulating triggers.
- Manual: simulate AI proposal source; confirm state stays
  'suggested' with no auto-advance.

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
  3D-map-node integration, cohort-signal proposal source):
```

Approval-gated: do NOT dispatch this prompt without Aaron's
explicit approval per rule 7 + rule 13 + rule 21.

## 8. Anti-rules

- **No AI effectiveness claims.** Banned by sanitiser at
  output layer.
- **No state advancement by AI.** Hard rejection at Worker
  tool.
- **No public surfacing of non-published candidates.** RLS
  + redaction-test enforced.
- **No silent deprecation.** Deprecation banner mandatory.
- **No claim that the app teaches grappling.** The app
  surfaces evidence + connects students with coaches; it
  does NOT replace coaching.
- **No raw evidence leakage.** Public published nodes show
  evidence COUNTS only; raw clips / coach notes / outcome
  details stay private to the candidate's collaborators
  unless the user explicitly opts in to share.
- **No reward for proposal volume alone.** The user-feedback-
  incentives surface awards points only for proposals that
  reach `validated` — never for raw count.
- **No taxonomy contamination from rejected candidates.** A
  rejected candidate's `position_taxonomy_id` link does not
  pollute the public taxonomy. Only `published` nodes feed
  the taxonomy.

## 9. Cross-references

- `docs/APP_DEVELOPMENTS.md` § Forever Improve — list of
  permanent improvement categories this spec serves.
- `docs/OPERATING_RULES.md` § 9 (provisional health/skill
  claims) / § 18 (action ledger) / § 21 (approval gate) /
  § 22 (AI spend) / § 23 (deep research cache).
- `docs/HUMAN_APPROVAL_GATE_SPEC.md` — rule 21 state machine.
- `docs/AI_SPEND_GATES_SPEC.md` — rule 22 cost classes for
  vision analysis on candidate footage.
- `docs/DEEP_RESEARCH_OFFLOAD_SPEC.md` — rule 23 cache for
  per-technique research artifacts.
- `docs/JOURNAL_IMPORT_NORMALIZE_INSIGHTS_SPEC.md` § 6 — the
  research-snippets surface; technique research follows
  the same general-background pattern.
