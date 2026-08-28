# App developments — repo-backed roadmap

Single source of truth for the **active** roadmap Aaron carries
between the laptop terminal, ChatGPT chats, and the phone
Admin/Dev control centre. Apple Notes is now stale as a roadmap:
it is a human scratchpad only. Anything intended to drive work
must be promoted into this repo-backed roadmap / backlog flow.
The in-app Admin/Dev "Backlog" card mirrors this file. When the
file changes, the next paired build picks it up — no live-fetch
required yet (the long-term shape is the connector reading this
via the MCP route layer once Supabase is wired).

MCP-first operating rule: before any Claude / Codex / Agent /
ChatGPT task starts, check `get_work_status`,
`list_pending_suggestions`, `get_automation_state`, `get_handoff`,
then `/api/control_centre` if available. Report MCP state,
freshness/staleness, chosen next task, and whether fallback
terminal / control-centre state was needed. If MCP is stale, say
"MCP stale" and use latest terminal / control-centre state as
fallback.

Status language used below:

| Tag | Meaning |
|---|---|
| **live** | Running in production / a deployed component (Worker, last released mobile build, etc.). |
| **repo-only** | Code / docs are on `main` but not yet shipped via a tester build, deployment, or dashboard step. |
| **tester-build** | Will ship to testers when the next paired Android v18 / iOS Build 19 dispatch goes. **Per 2026-05-08 directive: this build is installed-device QA only — TestFlight tester group + Play Internal Testing track. NOT a public release.** Numbers stay at current `app.json` values (no bump) until Aaron approves the next paired build after Android Health Connect + Grappling Readiness v1 are finished and Agent-confirmed. The `production` EAS submit profile's `ios.groups: ["Team (Expo)"]` already routes to the TestFlight tester group, not App Store public. |
| **blocked** | Cannot move without a specific external action — Aaron's manual step, vendor processing window, or upstream dependency. |

Updated 2026-05-07.

## Active priority order

The MCP connector/control-centre path is **Priority 1** because
every other priority benefits from ChatGPT being able to read
Claude / Codex lane status without screenshots. The remaining
priorities keep their relative order below that app-control lane.

### 1. Screenshot-free MCP terminal bridge / control centre (Priority 1) — IN FLIGHT

ChatGPT and the mobile Admin/Dev surface should read Claude /
Codex lane status, build state, handoff, and recent terminal
summaries from one admin-token-gated read path — no Termius
screenshots, no manual paste, no raw terminal control.

Priority 1 has three inseparable pieces:

1. **ChatGPT-compatible MCP connector auth/read path** — the
   Worker exposes the MCP protocol and REST `/api/*` read routes,
   authenticated by the existing owner token.
2. **Screenshot-free terminal status** — the local bridge writes
   sanitized `coder_lanes`, `terminal_summary`, `handoff`, and
   `work_status` state without storing raw pane logs.
3. **App Admin/Dev status consumer** — the phone reads
   `EXPO_PUBLIC_MCP_BASE_URL` and renders owner-only status cards
   for Aaron.

| Component | Status |
|---|---|
| Cloudflare Worker (`lauburu-mcp-preview`) | **live** — `https://lauburu-mcp-preview.lauburu-aaron.workers.dev/` |
| Worker admin-token gate | **live** — every connector route 403s without `x-athlete-memory-token` |
| Worker routes (`/api/work_status`, `/api/coder_lanes`, `/api/build_status`, `/api/handoff`, `/api/terminal_summary`) | **live** — placeholder + `dataSource.schemaRequired` payload until Supabase wires |
| MCP protocol endpoint (`POST /mcp`) | **live** — ChatGPT-compatible tool calls for the same five read objects |
| Local tmux bridge (`scripts/bridge-snapshot-lanes.sh` / `npm run bridge:snapshot`) | **live** — writes 4 sanitised JSON artifacts to `data/agent-status/lanes/` |
| Bridge artifact schema test (`npm run bridge:verify`) | **live** |
| Live worker integration test (`npm run mcp:test:live`) | **live** — 11/11 assertions pass |
| Express parity routes in `chat-app` | **live in repo** (chat-app is parity reference, not deployed) |
| Supabase migration `0003_connector_status_tables.sql` | **repo-only** — committed at `955bfed`, awaiting manual apply |
| Worker `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` secrets | **blocked** on Aaron's `wrangler secret put` after the migration |
| Mobile Admin/Dev cards reading the Worker | **tester-build** — `EXPO_PUBLIC_MCP_BASE_URL=<worker>/api` env switch + next paired build |
| Bridge → Supabase upsert (`LaneStatusWritePayload` consumer) | **repo-only / planned** — schema exists; producer code not yet written |

**Done flag for Priority 1:** Aaron taps an Admin/Dev card on the
phone and sees the live Claude lane summary written by the local
bridge to Supabase, fetched by the Worker, returned to the app
through `EXPO_PUBLIC_MCP_BASE_URL`.

### 2. Health / Data Source reliability

Real-tester functionality for Aaron's iPhone (Apple Health) and
his girlfriend's Android (Health Connect) is the first health
source target. Two devices in active daily use must connect
cleanly, surface what's available, and stay honest about what's
missing. Manual check-ins + training logs are the fallback when a
source isn't connected.

Source-of-truth spec for every provider:
`docs/HEALTH_CONNECTIVITY_TRUTH_SPEC.md` — pulls
Apple Health / Health Connect / Polar via hub / WHOOP direct /
Polar direct / WHOOP export / Bluetooth HR / generic
conditioning / manual log into one matrix with the canonical
truth labels (`live` / `synced from hub` / `imported summary`
/ `seed/provisional` / `setup required` / `planned`), names
what's allowed to feed Grappler Readiness now vs later, and
specifies the proposed `connector_health_sources` MCP fields.

Hard guardrails (preserved):

- Apple Health is iOS-only; Health Connect is Android-only. No
  cross-platform claims.
- Missing data stays missing — never fabricated.
- No paid-tier gating for these two primary sources (already
  un-gated, commit `d4827ba`).
- WHOOP Direct and Polar Direct are not core Grappler Readiness
  sources. If historical CSV/export paths already exist, they are
  optional backfill/provisional evidence only. Bluetooth HR is
  Train-session data only, never readiness input.

Status: **live** for the existing primary cards in last paired
build. Next moves are tester-build verifications, then source
expansion in this order:

1. Android Health Connect reliability.
2. Apple Health stability.
3. Manual session logging and journal context.
4. WHOOP / Polar labels stay truthful as optional/backfill only.
5. Polar / Bluetooth truthfulness for non-readiness surfaces.
6. Optional FIT / TCX / CSV import later.

Optional import backlog stays secondary: ErgZone FIT / TCX / CSV
export import, Rogue / Concept2 Logbook indirect import, and
Strava / TrainingPeaks / Intervals.icu indirect import only when
the user already syncs there or provides a file export. Do **not**
build ErgZone or Rogue as primary dependencies or direct APIs.
These data-source lanes matter, but they do not outrank the
Apple Health / Health Connect daily testing path.

Generic conditioning import model:

- `sourceApp` — human-readable app label from Apple Health /
  Health Connect provenance when available.
- `sourceType` — `apple_health`, `health_connect`, `fit_file`,
  `tcx_file`, `csv_file`, or `manual`.
- `workoutType` — HIIT, rowing, ski erg, bike erg, assault bike,
  conditioning, or unknown.
- Timing — start time, end time, duration.
- Summary metrics — calories, distance, heart-rate summary when
  available.
- Intervals — present only when the source actually supplies
  structured interval splits; otherwise UI must say "Workout
  summary imported; interval splits not available."
- `provenanceLabel` — e.g. "ErgData via Health Connect"; never
  "Concept2 Direct", "ErgZone Direct", or "Rogue Direct" unless a
  verified direct integration exists.

### 3. UX / information architecture cleanup

Daily and frequent workflows live in the feature tabs where the
user naturally does that work. Rare settings, account state,
subscription, app version/build info, permissions, support,
diagnostics, and developer/admin controls live in Settings or
Admin/Dev.

Current rule:

- Health owns nutrition targets, source status, sync/storage
  actions, and health-source management.
- Train owns weekly schedule, training plans, and session
  logging.
- Settings is not a dumping ground. It should stay focused on
  account, subscription, version/build, notifications,
  permissions, support/feedback, and hidden Admin/Dev entry.

Status: **ongoing**. UX/IA stays after MCP bridge and
Health/Data Source reliability unless a tester-facing blocker is
urgent.

### 4. Cautious early Grappler Readiness prototype

Uses only available data (Apple Health / Health Connect + manual
check-ins + training logs) and clearly shows missingness. No
strong "you are ready" claims. Labelled provisional.

**Hard guardrail (preserved):** No Grappler Readiness UI ships
until Batches B / C / D land. Tonight's prototype work is
doc-only (`docs/GRAPPLER_READINESS_PROTOTYPE_PLAN.md`).

| Batch | What | Status |
|---|---|---|
| B | Extend `NextDayCheckin` sliders (soreness, mood, perceived fatigue) | repo-only / planned |
| C | Extend `TrainingSession` schema (gi/no-gi, drilling vs live, perceived intensity) | repo-only / planned |
| D | Bucket-ring UI on `AthleteStateStrip` (5 buckets with provenance) | repo-only / planned |

### 5. Admin/Dev workflow + Cloudflare / Supabase MCP bridge on the phone

The owner-workflow surface that lets Aaron manage everything from
the phone. Subsumes the previous "Railway read-only / MCP-style
bridge" priority. Railway is deprecated; Cloudflare Worker +
Supabase is the active replacement for connector/control-centre
state.

- Admin/Dev surface (Now / Android / iOS / OTA cards, Primary
  actions, Prompt bridge, Quick capture, Open shortcuts):
  **live**.
- Workflow buttons (typecheck, release audit, backend smoke,
  Android build + upload, iOS build + submit, OTA diagnostic):
  **live** — owner-tap only, never auto-dispatched.
- Mobile MCP endpoint switch (`EXPO_PUBLIC_MCP_BASE_URL`):
  **live in code** (commit `7e40763`); **tester-build** to
  flip on for testers.
- Cloudflare Worker: see Priority 1 above.

## Later backlog (not in the active top 5)

### 6. Paid AI API integration

Deferred until monetisation + usage caps + data readiness all
exist. Triggers documented in:

- `docs/AI_PROVIDER_STRATEGY.md`
- `docs/AI_MONETISATION_AND_USAGE_STRATEGY.md`

Hard guardrail: no paid AI API call until both trigger docs
explicitly say go. Status: **blocked** by design until then.

### 7. Public production release

Out of scope until the production listing pass is done (separate
from the now-complete Internal Testing pass). Status: **blocked**
on production listing pass.

### 8. Stage-5 local Mac / tmux bridge daemon

Phone taps a fixed allowlist of safe actions over Tailscale. Gate
is the eight hard rules in `docs/LOCAL_BRIDGE_WORKFLOW_PLAN.md`
Stage 5. Stage 1 (the read-only producer) is **live**; the
write-side daemon stays **repo-only / planned**.

## Hard guardrails (apply across every priority)

These don't move without an explicit doc commit. They are not a
priority — they are the floor below every priority.

- **Apple Health iOS-only, Health Connect Android-only.** No
  cross-platform fallback.
- **Missing data stays missing.** No fabricated zeros, no
  invented connections.
- **No Grappler Readiness UI yet.** Doc-only until Batches B / C
  / D ship.
- **No paid AI API.** Gated on the two strategy docs.
- **Build dispatch is owner-tap only.** Connector / bridge cannot
  trigger builds.
- **EAS build cost control.** Coders may say a feature or patch is
  `Implementation-complete, awaiting Agent functional confirmation`
  when code is committed, typecheck/tests pass, no obvious blockers
  remain, and expected behaviour is clearly described. They must not
  request, trigger, or recommend a new EAS/tester build yet. A new
  EAS build is allowed only after:
  1. Agent performs a functional audit of the completed change.
  2. Agent confirms the change is worthwhile to test on-device.
  3. The change is bundled with other meaningful mobile changes
     where possible.
  4. Typecheck/tests pass.
  5. Aaron explicitly approves the EAS build.
  Default is no EAS build, no tester build, no "quick build to
  check", no build for docs/backend/MCP-only changes, and no build
  for tiny copy/UI tweaks unless bundled. Use mobile typecheck,
  unit tests, local inspection, simulator/dev-client if already
  available, Admin/Dev MCP status, and Agent audit confirmation
  instead. Use status wording: `Implementation-complete, awaiting
  Agent functional confirmation`, `Agent-confirmed, ready for Aaron
  build approval`, `Aaron-approved for EAS build`, and
  `Built/tester-ready`. Do not call mobile work `fully complete`
  until Aaron has tested or approved it.
- **Clear steps; automate first.** When something is required,
  coders / agents must give Aaron clear step-by-step instructions,
  automate every safe part before asking him, and use Claude /
  Codex / Agent wherever possible. Aaron should only handle secrets,
  approvals, logins, 2FA, vendor dashboards, or safety-sensitive
  confirmations. Every output must split follow-up into `automated by
  coder/agent`, `manual Aaron step`, and `blocked until Aaron acts`.
  No EAS build unless Agent confirms worthwhile on-device testing
  and Aaron approves.
- **Admin/Dev gating preserved.** No tester sees admin surfaces
  or owner-only FABs.
- **No secrets / tokens in any committed file** — `.env*` are
  gitignored; bridge artifacts pass through the two-pass
  redactor; Worker / chat-app responses pass through the same
  redactor at the boundary.
- **Do not touch grappling.opml content** — off-limits.
- **Agent role boundary.** Agent work is app UX audit worker work
  only: observe screens, find clutter/regressions, and propose or
  patch small mobile UX fixes when explicitly assigned. Agent is
  not a backend deployer, not an MCP auth owner, not a Supabase
  operator, and not a build dispatcher.

## Top 7 priorities (the answer to "what's next")

Updated 2026-05-09 per Aaron's CLAUDE-FINAL-OVERNIGHT-PRODUCT-AUTOMATION-01
directive — extends the earlier 2026-05-09 Top-5 with
priorities 6 + 7. In order:

1. **Health Connect / Apple Health installed-device truth** —
   clear the active release gate by retesting the Health
   Connect → Connect crash repro on Android v20
   (`~/Downloads/lauburu-android-versionCode20-health-connect-debug-surface.aab`)
   AND auditing iOS TestFlight build 19 on Aaron's iPhone.
   Drives `agent_qa_result.json` from `partial` →
   `pass`. Canonical: `docs/INSTALLED_DEVICE_QA_RELEASE_GATE.md`.
   Per rule 9, all health/readiness claims stay
   `confidence: provisional` until this gate clears.
2. **Push approval notifications** — ship the rule 21 / 22 /
   23 push wiring so automation pauses ONLY for Aaron's
   Approve / Defer / Deny on the iPhone lock screen.
   Synthesis: `docs/PUSH_APPROVAL_AUTOMATION_SPEC.md`.
   Underlying handoffs in dependency order:
   `CODEX-FS-XXX-ALL-IDLE-PUSH-NOTIFICATION-01` →
   `CODEX-FS-XXX-HUMAN-APPROVAL-GATE-IMPL-01` →
   `CODEX-FS-XXX-AI-SPEND-GATES-IMPL-01` →
   `CODEX-FS-XXX-DEEP-RESEARCH-OFFLOAD-IMPL-01`. All staged,
   all approval-gated.
3. **Admin/Dev approval centre** — single in-app panel that
   surfaces every pending gate (release / EAS build / Worker
   deploy / AI spend / research / FS-XXX promotion / public
   release) plus deferred / approved / blocked recent
   decisions. Spec: `docs/HUMAN_APPROVAL_GATE_SPEC.md` § 4 +
   `docs/PUSH_APPROVAL_AUTOMATION_SPEC.md` § 4. Required
   fields tracked in
   `docs/MCP_LONGTERM_ACCESS_ARCHITECTURE.md` § 3 (criterion
   (a) of Developer-Mode-off).
4. **Screenshot / audit automation** — shipped this session
   in 4 commits: `fc8d7c3` (audit-screenshots script + v1.5
   capture tier), `da233c3` (in-app audit automation spec),
   `412dab2` (iPhone Mirroring helper + workflow doc),
   `1e5a1ad` (operator audit playbook). Next step: Aaron
   runs `npm run audit:screenshots` (simulator) and
   `npm run audit:iphone-mirroring` (real device via
   Continuity) to validate end-to-end. Canonical playbook:
   `docs/INSTALLED_DEVICE_AUDIT_PLAYBOOK.md`.
5. **Grappling Readiness core** — architecture/schema +
   gated UI work per `docs/GRAPPLER_READINESS_BUILD_PLAN.md`
   + `docs/GRAPPLER_READINESS_PROTOTYPE_PLAN.md`. No
   overclaiming, no user-facing readiness score until
   priority 1 (real-device truth) clears AND priorities 2 +
   3 (push approval centre) ship to gate any high-cost AI
   inference per rule 22.
6. **AI cost control / external AI offload** — ship the
   tier model + pay-as-you-go overflow + tester-stage
   external-AI offload + cached research artifact reuse
   defined in `docs/AI_SPEND_GATES_SPEC.md` § 4 +
   `docs/DEEP_RESEARCH_OFFLOAD_SPEC.md` +
   `docs/AI_ECONOMICS_TESTER_TO_PUBLIC_PLAN.md`. Goal: the
   cheapest AI that still satisfies the user's question
   gets used; expensive paths cache + Aaron-approve. Pairs
   with priority 2 (gate UX) + priority 7 (Forever Improve
   AI cost reduction quality bar).
7. **Forever Improve / product intelligence** — keep the 9
   permanent improvement categories (per the section below)
   in active rotation. Each status report includes a
   one-line freshness note for at least one category. Drift
   on a category for >7d surfaces as a candidate FS-XXX.
   Lifecycle: per `docs/FOREVER_IMPROVE_LIFECYCLE_SPEC.md` —
   8 states from `candidate` to `verified` (or `superseded`
   exit). Memory architecture per
   `docs/MCP_MEMORY_ARCHITECTURE_SPEC.md` provides the
   "nothing gets lost" persistence floor.

Items 8+ stay in the Later backlog above. The Permanent
Improvement Categories below are continuous quality bars
that span priorities 1–7 and beyond — not separate items.

## Permanent improvement categories (Forever Improve)

Standing categories — colloquially "Forever Improve" — that
span multiple priorities. These are NOT one-time goals that
"ship" and disappear. They are continuous quality bars the
Top 5 priorities and Later backlog must honour.

### Reward principle (applies to every category below)

Reward **genuine grappling growth, verified contribution,
consistency, and learning quality.** NEVER reward spam
engagement, meaningless app usage, raw activity counts, or
behaviours users could farm. Every gamification / mastery /
reputation surface MUST resist sybil attacks, rate-limit
gain, and weight verified evidence above passive activity.

Video, skill-mastery, and any AI-derived claim about ability
MUST use **proof + confidence + manual-review layers.** No
automatic mastery claims; no automatic skill-level promotions;
no automatic ranking. Claims start at the lowest confidence
tier and only rise after explicit proof / peer signoff / coach
signoff per rule 9 (provisional health/skill claims).

### Complete mobile-only admin/developer workflow

The end state where Aaron operates the project from his phone
without a laptop or Termius for normal day-to-day work. Pairs
with rule 12 (coders run all laptop commands), rule 14
(parallel priorities — Admin/Dev phone control centre is
priority (b)), and `docs/MCP_LONGTERM_ACCESS_ARCHITECTURE.md`
§ 3 (Surface A required fields).

Permanent quality bars:

- **No required laptop / Termius for normal operation.** Every
  workflow Aaron uses daily must be reachable from the phone
  Admin/Dev tab. Laptop tools (Claude Code, Codex, terminal)
  are for coders + occasional debug; never the only path for
  Aaron.
- **Admin/Dev tab as the canonical operator surface.** Status,
  approvals, build gates, automation state, MCP freshness,
  next actions all visible. The architecture doc § 3 lists
  the exact fields required for Surface A parity with the
  laptop `/mcp/v2` surface.
- **Simple, effective, efficient, low-friction.** Every panel
  earns its place. Ship density is fine; UI debt is not. If a
  card does not directly serve operator decisions, archive it.
- **Every manual step is challenged.** For each step Aaron
  performs by hand, ask: can a coder / agent automate this
  safely (rule 12 / rule 13)? If not, can it be approval-
  gated via push so the user only taps Approve / Defer (rule
  21 / 22 / 23)? If neither, the step must have an explicit,
  written justification in `docs/PHONE_ONLY_AUTOMATION_PLAN.md`
  § 5. "Aaron has always done it" is not a justification.

This category is **never marked complete** — it is reviewed
continuously. Status reports include a one-line freshness
note (e.g. "Mobile-only workflow: rule-12 cadence holding;
1 manual step under review") and surface any drift from the
quality bars.

Implementation milestones live across the Top 5 priorities
(specifically priorities 1 + 5) and the staged Codex handoff
prompts in:
- `docs/CONTROL_CENTRE_MVP_SPEC.md` § 10 (rule 20 push wiring).
- `docs/HUMAN_APPROVAL_GATE_SPEC.md` § 6 (rule 21 approval
  centre).
- `docs/AI_SPEND_GATES_SPEC.md` § 6 (rule 22 AI-spend gate).
- `docs/DEEP_RESEARCH_OFFLOAD_SPEC.md` § 7 (rule 23 deep-
  research offload + cache).
- `docs/MCP_LONGTERM_ACCESS_ARCHITECTURE.md` § 4 (Surface B
  standard connector for external-AI access without laptop).

When all of these land, criterion (a) of the architecture
doc § 2 ("Admin/Dev tab parity") holds and Developer Mode
can be turned off — completing the mobile-only workflow.

### Gamification / progression systems

Continuous quality bars for any future XP / streak / badge /
level / progression surface.

- **Reward verified mastery + consistency, never raw activity
  counts.** No "you logged in 7 days in a row" badges. No
  "you opened the app N times" XP. Streaks are tied to
  deliberate practice signals (drill rep counts, sparring
  rounds with logged outcomes, journal entries with non-empty
  content), never to passive opens.
- **Belt-aware progression.** Where progression surfaces
  reference belt level, they treat belt as **context** for
  expected technique scope, NEVER as automatic XP / mastery /
  rank within the app. Belt level is user-asserted (with
  optional coach signoff via the verified-mastery surface
  below) and revocable; belt promotion happens at a real-life
  academy, not in the app. The app may surface "techniques
  often tested at <belt>" or "drills your peers at <belt>
  also practice", but never claims to grant or test belt
  rank itself.
- **Technique-mastery progression.** Mastery / repetition /
  consistency tied to a specific technique node in the
  drill / position taxonomy (verified-mastery surface
  below). Never global "skill level" inflation.
- **Contribution / reputation as one of the progression
  inputs.** Reputation earned via the community-contribution
  surface below feeds into a user-visible profile; it does
  NOT confer in-app authority that overrides safety / privacy
  controls.
- **Anti-farm.** Cap dailies / weeklies that can be gamed.
  Rate-limit XP gain per session. Diminishing returns on
  repeat actions inside a window.
- **No medals from passive metrics alone.** Steps, watch-on-
  wrist time, raw heart-rate data, total app-usage minutes
  do NOT generate awards by themselves; they are inputs to
  context, not achievements.
- **Public leaderboards only after opt-in + calibration.** No
  default-on rankings; no surfacing of relative position to
  peers without explicit user consent recorded per FS-019
  auth model.
- **Privacy floor.** Rule 22 applies: nothing about gamification
  state is sent to external AI without per-call approval.

### Verified instructional mastery

Mastery claims (e.g. "I can hit X technique reliably") require
proof, NEVER auto-promotion.

- **Three confidence tiers.** `claim_only` (user said so;
  lowest) → `self_video_attached` (user uploaded clip;
  middle) → `verified_by_coach` or `verified_by_peers`
  (explicit signoff; highest). Tier display follows rule 9
  — `verified_by_coach` is the highest tier; no `mastered`
  or absolute claim language.
- **No automatic mastery awards.** Mastery is never inferred
  from session count, journal frequency, or AI scoring alone.
  An explicit human signoff (self-attested-with-evidence,
  peer, or coach) is required for each tier upgrade.
- **Tied to a drill / position / progression taxonomy.**
  Mastery rows reference a stable taxonomy id so claims are
  comparable + revocable per technique, not a vague global
  "skill level".
- **Revocability.** Coaches and the user themselves can
  downgrade or revoke a mastery claim. Audit trail preserved.

### AI video analysis

When AI is used to analyse uploaded video (technique
breakdown, sparring footage, drill review, competition
footage), the workflow honours rule 22 (AI spend gate) +
rule 23 (deep research offload + cache) + the
proof/confidence/manual-review layers above.

- **Footage classes.** Distinct schemas for: `competition`
  (full match, opponent identifiable, scoreline if any),
  `training_sparring` (round / partner / intensity), `drill`
  (technique focus + rep count), `instructional_reference`
  (third-party clip the user is studying — analysis only,
  no claims about the user's own ability).
- **Analysis tasks.** Three high-signal modes: **positional
  analysis** (classifying positions over time within a
  match / round), **mistake analysis** (flagging moments
  where a technique was attempted and failed, with a
  confidence label), **system analysis** (clustering the
  user's tendencies into a higher-level "what they tend to
  do" picture across many clips). All three are
  hypothesis-generating; none confer mastery automatically.
- **Vision-heavy → `expensive_ai` cost class** per rule 22.
  Each video analysis fires the AI-spend gate before
  inference. No silent vision processing.
- **Cache by `reuseKey`** per rule 23. Re-uploading the same
  clip (hash match) returns the cached annotations + cited
  artifact; no re-spend.
- **Output is annotated suggestions, never prescriptive
  coaching.** Rule 9 anti-rules apply: associations only,
  no "you should do X", no causation claims.
- **Coach review + confidence labels.** Each AI annotation
  carries a confidence tier: `ai_only_low_confidence` →
  `ai_only_medium_confidence` → `coach_reviewed` →
  `coach_signoff` (the highest tier surfaces only after a
  linked coach explicitly accepts the annotation per the
  Private coaching surface below). The UI MUST render the
  tier alongside any annotation.
- **Manual review layer required.** User (and the linked
  coach, if any) can accept / reject / correct each AI
  annotation before it counts as mastery evidence. Rejected
  annotations are logged but never surface as truth.
- **No auto-promotion.** AI-flagged "good rep" or "clean
  technique" output does NOT automatically lift mastery
  tier. It can be ATTACHED as evidence; the human signoff
  is still required.
- **Privacy floor.** Video stays per-user; never auto-shared
  with peers / coach / the cohort. Sharing requires explicit
  per-clip user action (per rule 22 sensitive-data opt-in).

### Community contribution / reputation

Reputation rewards verified contributions, never raw activity.

- **What earns reputation:** confirmed-correct technique
  annotations, peer reviews other users mark as helpful,
  community content that gets manual-moderation signoff,
  coach-verified mastery sign-offs given to peers.
- **What does NOT earn reputation:** post count, comment
  count, login streaks, video upload count, follower count.
- **Anti-sybil + rate-limit + manual moderation.** Reputation
  growth is throttled. Manual moderation surfaces flag spam
  patterns; reputation decays toward zero when behaviour
  shifts toward farming patterns.
- **Visible reputation is opt-in.** Default-private; surfacing
  to peers requires explicit user consent.
- **Reputation never gates safety.** A user with low / zero
  reputation still has full access to safety features (block,
  report, privacy controls, leaving the community).

### Private coaching workflows

Coach ↔ student is a per-pair RLS-gated relationship; never a
broadcast or one-way data drain. Designed first for Aaron's
own online + in-person privates; the same module is reusable
for other coaches once the per-pair contract is shipped.

- **Per-pair consent.** A coach reads a student's data ONLY
  with the student's explicit, time-bound, revocable consent
  recorded in a `coaching_relationships` row (Supabase RLS-
  gated by both `coach_user_id` and `student_user_id`).
- **Online + in-person private mode.** A `private_session`
  row captures: scheduled time, mode (`online` / `in_person`),
  technique focus (links to drill / position taxonomy),
  pre-session goals from the student, post-session signoff
  from the coach. Online sessions can attach a session
  recording; in-person sessions log a coach note + optional
  uploaded video that the coach films at the session.
- **Granular scope.** Consent is per-data-class (e.g. journal,
  health metrics, video, mastery claims) not all-or-nothing.
- **No silent broadcast.** Coaches do not get a "see all your
  students at a glance" surface unless each student opts in
  individually. Aggregate views over the coach's roster are
  count-only by default.
- **Sign-off-able feedback loop.** Coach feedback (verbal,
  written, video-annotated, post-session note) lands as
  evidence in the verified-mastery surface above when the
  student accepts it. Coach signoff is also the highest
  tier in the AI-video-analysis confidence ladder above.
- **Reusable module.** Once Aaron's coach-side flow is
  shipped + battle-tested, the same `coaching_relationships`
  + `private_session` schema is exposed to other coaches
  who want to use the app for their own students. The module
  is reusable, NOT cloned; per-coach customisation lands
  via settings, not separate code paths.
- **Priority access (points/reputation-based).** A coach
  may optionally enable a priority-access lane where
  students with higher reputation / verified consistency
  (per the Community-contribution surface above) get earlier
  booking slots — but the coach can also retain a fully
  manual booking flow. **Priority access is NEVER an
  automatic unlock** — students never gain access purely by
  hitting an XP threshold. The coach approves every booking;
  reputation only sorts the queue.
- **Inheritance.** Privacy floor (rule 22), AI-spend gate
  (rule 22), and deep-research-offload (rule 23) all apply
  to coach-side AI usage. The coach's API budget is the
  coach's, not the student's.
- **Termination.** Either party can revoke the relationship.
  Existing artifacts (cached signoffs, annotations) stay in
  the audit trail but new reads are blocked.

### Mobile-only coaching / admin operations

Extends the "Complete mobile-only admin/developer workflow"
category above to the coach role.

- **No required laptop for coach operations.** Coaches
  operate the per-pair surfaces from their phone:
  reviewing student journal entries, signing off on mastery
  claims, watching submitted clips, sending feedback.
- **Coach approval flows reuse rule 21 push wiring.** When a
  coach needs to approve a high-cost AI analysis (rule 22)
  or an artifact import (rule 23) on behalf of a student-
  shared clip, the gate fires on the coach's phone too.
- **Every manual coach step is challenged.** Same bar as
  the operator: automate (rule 12 / rule 13), approval-gate
  via push (rule 21), or document explicit justification.
- **Coach UI honours the same simple/effective/efficient/
  low-friction bar.** No coach surface earns its place by
  surfacing extra metrics; surfaces must directly serve
  coaching decisions.
- **Coach mobile path is independent of operator (Aaron)
  mobile path.** Coach is a separate role with its own auth
  scope (Supabase JWT + coach-allowlist or coach-grant flow).

### User feedback incentives

Reward users who help the app get better. Pairs tightly with
the community-contribution surface above but is scoped
specifically to product feedback.

- **Points for useful suggestions.** A user-submitted
  suggestion that passes triage (not duplicate, not spam,
  has a clear product point) earns a small base reward.
- **More points if implemented.** When a suggestion lands as
  an FS-XXX candidate that ships, the suggesting user(s)
  earn a larger reward + a one-line credit on the FS-XXX
  card (opt-out by default; user can opt out of public
  credit per submission).
- **Anti-spam / duplicate protection.** Each new suggestion
  is auto-checked against the open + recently-closed
  backlog for near-duplicates (text similarity threshold).
  Duplicates are merged into the original; the merging user
  earns no points but the suggestion stays in the audit
  trail.
- **Rate-limit + cooldown.** Hard cap on suggestions per
  user per day; cooldown after rejected suggestions to
  discourage spray-and-pray.
- **Contributor reputation.** Approved-suggestion + shipped
  suggestion counts feed into the community-contribution
  reputation surface. Contributor reputation is opt-in to
  surface publicly, same rules as community reputation.
- **Aaron's manual review.** Final triage / accept / reject
  decisions are Aaron's (or a delegated maintainer's) — no
  AI auto-acceptance. AI may pre-flag duplicates or
  low-quality submissions but never auto-rejects without
  human review.
- **No reward gaming.** Submitting variations of the same
  idea, splitting one suggestion into many, or copy-pasting
  another user's suggestion are detected and zero out the
  reward; repeat offenders lose contributor reputation.
- **Privacy.** Suggestions submitted privately stay private
  by default; public visibility (e.g. "voted on by N
  contributors") requires per-suggestion opt-in.

Schema sketch (Supabase, RLS-gated):

```ts
interface UserSuggestion {
  id: string;
  user_id: string;
  text: string;                  // ≤2000 chars
  category: 'gameplay' | 'health' | 'coaching' | 'admin' | 'other';
  status: 'pending_review' | 'duplicate_of' | 'accepted_backlog'
        | 'shipped' | 'rejected_with_reason';
  duplicateOfSuggestionId?: string;
  fsCandidateId?: string;
  rewardPointsAwarded: number;
  publicCreditOptIn: boolean;
  createdAt: string;
  updatedAt: string;
}
```

Maps to existing `connector_backlog_items` / FS-XXX flow
where appropriate.

### Evidence-driven technique evolution

The headline category — how grappling technique improvements
flow through the app from raw hypothesis to public
instructional content WITHOUT the app ever claiming
unverified technique effectiveness.

Suggestions for new techniques / variations / system
refinements travel through a state machine of progressively
stronger evidence before they appear as a public node on the
3D grappling map.

**State machine** (10 states):

```
suggested
   │
   ▼
approved_private  ──────────────► rejected
   │                                  │
   ▼                                  │
testing_live  ────────────────────►  │
   │                                  │
   ▼                                  │
evidence_accumulating  ─────► deprecated
   │                                  │
   ▼                                  │
validated                             │
   │                                  │
   ▼                                  │
instructional_ready ─────►  rejected  │
   │                                  │
   ▼                                  │
filmed                                │
   │                                  │
   ▼                                  │
published ─────────────► deprecated ◄─┘
```

| State | Meaning |
|---|---|
| `suggested` | An AI / user / coach proposed a new technique or refinement. Untested. No public surfacing. |
| `approved_private` | Aaron (or a delegated coach) reviewed the suggestion and accepted it for private testing. Hidden 3D-map node created (private to Aaron + collaborating coaches). |
| `testing_live` | The technique is being tested in live rolling / competition / drill. Footage uploaded against the hidden node. |
| `evidence_accumulating` | Multiple footage attempts logged. AI may surface pattern observations (associations only — never effectiveness claims). |
| `validated` | Enough evidence + coach review to consider the technique reliably reproducible. Still private. |
| `instructional_ready` | Aaron decides this is worth making an instructional for. Filming queued. |
| `filmed` | Instructional video filmed but not yet published. |
| `published` | Public node added to the 3D map; viewable by users (with opt-in tier gating per coaching/community surfaces above). |
| `rejected` | Suggestion deemed unworkable. Stays in audit trail; reusable as a "tried and rejected because X" data point. |
| `deprecated` | A previously-published or validated technique no longer holds (e.g. counter discovered in live testing). Surface flips from public-good to deprecated; the audit trail keeps the original + the deprecation reason. |

**Hard rules**:

- **AI must NOT claim unproven technique effectiveness.**
  Any AI output about a technique in `suggested` /
  `approved_private` / `testing_live` /
  `evidence_accumulating` MUST be phrased as hypothesis
  ("possible improvement", "candidate position", "observed
  in N attempts"), never as confirmed claim.
- **Hypothesis-until-validated.** No technique is asserted
  reliable until `validated` AND a coach signoff has been
  recorded.
- **Only `published` nodes are user-viewable.** Earlier
  states are private to Aaron + collaborating coaches.
  Other users never see in-progress experimental nodes
  unless explicitly invited.
- **Footage-backed transitions.** Promotion from
  `testing_live` → `evidence_accumulating` → `validated`
  requires uploaded footage proof + coach review per the
  AI-video-analysis confidence ladder above.
- **No app-claimed grappling authority.** The app surfaces
  evidence; humans (Aaron, coaches) make every promotion
  / rejection decision. AI may flag candidates, but every
  state transition past `suggested` requires human signoff.

**Spec home**: `docs/EVIDENCE_DRIVEN_TECHNIQUE_EVOLUTION_SPEC.md`
(canonical) — covers schema, state-machine transitions,
3D-map-node integration, Codex handoff for the backlog
surface.

When all of these categories' implementation milestones land,
the app's "Forever Improve" bar is materially honoured. Each
status report MUST include a one-line freshness note for at
least one of these categories ("Mobile-only workflow: rule-12
cadence holding"; "Verified mastery: 3 new tier-2 claims this
week"; etc.) and surface drift from the quality bars.

## Manual steps for Aaron (phone-first)

The only steps that genuinely need a human + browser. Everything
else is dispatchable from Admin/Dev.

1. **Apply the Supabase migration.** Open Supabase project
   `aarontmaher's Project` (`rejalrfmievikabgsakf`) → SQL Editor
   → paste `supabase/migrations/0003_connector_status_tables.sql`
   → Run. (Priority 1 unblocker.)
2. **Set the Worker secrets.** From the laptop:
   ```sh
   cd cloudflare-worker
   npx wrangler secret put SUPABASE_URL --name lauburu-mcp-preview
   # https://rejalrfmievikabgsakf.supabase.co
   npx wrangler secret put SUPABASE_SERVICE_ROLE_KEY --name lauburu-mcp-preview
   # service_role JWT from Supabase → Settings → API
   npx wrangler deploy --env preview
   ```
3. **Verify.** `npm run mcp:test:live` should still pass and
   `dataSource.source` should flip from `placeholder` to
   `supabase` on every route.
4. **Tester device install** — TestFlight / Play Store auto-update
   once notified — no action needed beyond accepting the prompt.

## What's NOT in this file

- Long-form architecture (lives in `docs/architecture/`).
- Specific code TODOs (tracked in code, not here).
- Per-batch task breakdowns (in conversation history; this file
  carries the cross-conversation roadmap only).
- The grappling.opml content (untouched, off-limits).
- Old build / submission post-mortems — moved to
  `docs/BACKLOG_AUTOMATION_SYSTEM.md` and the relevant per-build
  audit docs.
