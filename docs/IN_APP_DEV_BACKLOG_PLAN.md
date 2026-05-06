# In-app Dev Backlog / Notepad — plan

Replaces Apple Notes as the structured source of truth for owner
backlog. Apple Notes is now a human scratchpad only; it is stale
for planning until an item is promoted into the repo-backed
roadmap/backlog or captured in Admin/Dev. The in-app Dev Backlog
is the **structured** state that ChatGPT, Claude, Codex, and the
connector tools read.

Companion to `FEEDBACK_PRIORITY_MODEL.md` (the priority ladder),
`CONNECTOR_BACKLOG_TOOLS_PLAN.md` (read/write tools spec),
`APP_DEVELOPMENTS.md` (the active priority list mirror), and
`RAILWAY_BACKEND_AUDIT.md` (route auth model).

Updated 2026-05-06.

## Why this exists

Aaron's current loop is: brain-dump in Apple Notes → triage by
hand → paste into ChatGPT → paste into Claude Code. Apple Notes
has no schema, no priority enum, no status field, no link to a
tester device or a specific build. Every paste re-formats by hand.

Goal: give the **structured** layer a real home — owner-only,
in-app, mobile-first — so the schema is stable and ChatGPT /
Claude / Codex can read+write the same items without any human
re-formatting.

Apple Notes is NOT replaced for free-form thinking. It stays as
the journal/scratchpad. It is not authoritative, not
machine-readable, and not a place to mark work done. The Dev
Backlog is for items that will move forward.

## Sections (Admin/Dev → Dev Backlog)

Already partially live as `Backlog · Quick capture` in Admin/Dev.
Plan for the next iteration:

1. **Current priority** — chip at top mirroring Now → Priority.
2. **Current blocker** — chip mirroring Now → Blocker.
3. **Next action** — chip mirroring Now → Next action.
4. **Active issues** — items with status in `new | triaged |
   accepted | in_progress`. Sorted by priority ladder.
5. **Tester feedback queue** — items where `source ===
   'tester_feedback'` AND `needsReview === true`. Owner-only;
   normal testers never see this section.
6. **Health / data-source priority** — items where `type ===
   'health_data_issue'` OR `type === 'source_integration_issue'`.
   Surfaced separately because they're rank-3 / rank-4 on the
   priority ladder for the current product phase (Apple Health +
   Health Connect testing).
7. **Admin/Dev workflow** — items where `type ===
   'release_blocker'` (rank 1) AND `category === 'release'`.
8. **Can archive** — `status === 'done' | 'tester_live'` items
   older than N days, plus `'archived'`.
9. **Do not delete yet** — items pinned by Aaron / awaiting one
   more verification step.
10. **Future / later** — `status === 'do_not_build_yet'` and
    type `feature_idea`, `monetisation_payment_idea`,
    `ai_coaching_idea`.
11. **Prompt drafts** — drafted but un-sent prompts (for the
    Prompt bridge, kept locally so re-opens don't lose them).
12. **Status handoff** — saved CHATGPT_STATUS blocks, most-recent
    on top.

Each section expand/collapse on mobile so the screen stays
compact.

## Backlog item shape (target)

Mostly already exists in `owner-backlog-store.ts`. Spec for the
next iteration extends fields. Current → target diff:

```ts
interface BacklogItem {
  id: string;                       // already present
  title: string;                    // already present
  details: string;                  // already present
  type: BacklogType;                // already present (extend enum)
  severity?: 'low' | 'medium' | 'high' | 'blocking';   // NEW
  priority: number;                 // already present (1–11 ladder)
  platform: 'ios' | 'android' | 'both';   // already present
  status: BacklogStatus;            // already present (extend enum)
  source: 'owner' | 'tester_feedback';     // EXTEND from 'owner' only
  sourceUserId?: string | null;     // NEW — null when anon
  appVersion?: string | null;       // NEW
  buildNumber?: string | null;      // NEW (versionCode on Android)
  screenshotUrl?: string | null;    // NEW
  createdAt: string;                // already present
  updatedAt?: string;               // NEW
  blockedBy?: string | null;        // NEW (free-text or another id)
  liveState?: 'live' | 'repo_only' | 'future' | 'blocked';  // NEW
  needsReview?: boolean;            // NEW (default true for
                                    //      auto-routed feedback)
  blocker?: string;                 // already present
}
```

### Type enum (extend)

Existing values stay; add the missing ones from this batch's spec:

- `bug`
- `ux` → rename for clarity to `ux_issue` (wire under both names
  for backward-compat for now)
- `feature` → `feature_idea`
- `release_blocker` (already present)
- `health_data` → `health_data_issue`
- `ai_coaching` → `ai_coaching_idea`
- `monetisation` → `monetisation_payment_idea`
- `railway_backend_issue` (NEW)
- `source_integration_issue` (NEW)

### Status enum (extend)

Already extended to match `FEEDBACK_PRIORITY_MODEL.md`:
`new | accepted | in_progress | repo_only | built | tester_live |
done | blocked | do_not_build_yet`. Add `triaged` (between `new`
and `accepted`) and `archived` (terminal-after-done).

## Tester-feedback auto-routing (server-side)

When `POST /api/feedback` accepts a tester submission, the same
record should also surface under the Dev Backlog UI as a
`source: 'tester_feedback'` item. Two implementation options:

### Option A — view, not duplicate (recommended)

Backend adds a derived view route (Phase 6 below) that returns
tester feedback records mapped to the backlog shape on read.
No double-write. The mobile UI fetches both:

- `GET /api/feedback/recent?includeArchived=false` (already
  admin-gated as of commit `4e567b7`).
- `GET /api/admin/backlog/local` (TODO — owner-backlog-store on
  device).

Render them in a single sorted list under "Tester feedback queue"
+ "Active issues". Source field disambiguates.

Advantage: no migration, no risk of drift between the two stores.

### Option B — copy on submit

`POST /api/feedback` writes the record AND creates a backlog row.
More work, more drift risk. Not preferred.

**Decision: Option A.** No code change for this batch beyond
documenting the contract. Implementation lands when the local
owner-backlog-store has the `screenshotUrl` + `appVersion` fields
above.

## Privacy boundary for tester feedback in Dev Backlog

- A tester's `userId` / `athleteId` shows on the backlog row only
  when `signed_in === true` on the original feedback record (the
  server already stamps this). Anonymous submissions render as
  "anon".
- Screenshot rendering uses `attachmentImageSource()` (already
  added in commit `4e567b7`) which sends the admin token in the
  `<Image>` source headers. Normal testers cannot reach
  `/api/feedback/attachments/:filename`.
- The Dev Backlog UI is gated by the same owner-email allowlist /
  dev-unlock as the rest of Admin/Dev. Normal testers see the
  Feedback FAB only — never the Dev Backlog.

## Approval gates for connector-driven edits

When the ChatGPT / Claude connector starts writing into the
backlog, certain actions need explicit owner approval. Spec'd in
detail in `CONNECTOR_BACKLOG_TOOLS_PLAN.md`. Summary:

- AI may freely create backlog items with `status: 'new'` +
  `needsReview: true`.
- AI may NOT change `currentPriority` directly — it can write a
  `priorityDraft` field instead, which the owner promotes via a
  one-tap "Accept" in Admin/Dev.
- AI may NOT archive items — only owner can move to `archived`.
- AI may NOT dispatch builds, change health/readiness user-facing
  copy, mark stable athlete memory, or invoke paid API features.
  All gated by an explicit human-tap.

## Out of scope for tonight

- Real local-store schema migration to add `screenshotUrl` /
  `appVersion` / `updatedAt`. The shape change is documented; the
  migration is a separate batch with explicit tests.
- The connector tools spec is in
  `CONNECTOR_BACKLOG_TOOLS_PLAN.md`; route implementation lands
  when the connector contract is reviewed.
- Apple Notes auto-import — not happening. Apple Notes is
  intentionally NOT machine-readable; importing it would just
  contaminate the structured backlog with brain-dump.
