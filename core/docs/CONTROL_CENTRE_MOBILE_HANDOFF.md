# Control Centre — mobile wiring handoff (Codex)

The exact `/api/control_centre` response shape Codex needs to wire
into the iPhone Admin/Dev surface. This is the canonical source for
field names, types, null handling, and rendering rules. Anything
not documented here is out of scope for the mobile MVP.

Companion to:
- `docs/CONTROL_CENTRE_MVP_SPEC.md` (the parent spec)
- `docs/MCP_PHONE_CONTROL_CENTRE.md` (the live read paths)
- `docs/CHATGPT_CONNECTOR_SETUP.md` (separate; ChatGPT connector,
  not mobile)

Updated 2026-05-07.

## 1. Endpoint

```
GET https://lauburu-mcp-preview.lauburu-aaron.workers.dev/api/control_centre
Header: x-athlete-memory-token: <ATHLETE_MEMORY_API_TOKEN>
```

Mobile already wires `EXPO_PUBLIC_MCP_BASE_URL` and auto-appends
`/api`, so the existing `connector-status-client.ts` pattern works
unchanged. Add a sibling fetch:

```ts
const res = await fetch(`${baseUrl}/control_centre`, {
  headers: {
    Accept: 'application/json',
    'x-athlete-memory-token': process.env.EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN ?? '',
  },
});
```

403 → wrong/missing token. 404 → `EXPO_PUBLIC_MCP_BASE_URL` set
without the `/api` segment (mobile auto-appends, so this only
happens if Aaron explicitly ends the env value at `/api/`).

## 2. Finalized response shape

Live verified against Worker version `dc480b35` (Phase 2). The TS
shape lives in `cloudflare-worker/src/control-centre.ts`; this is
the same shape, restated for mobile consumption.

```ts
interface ControlCentreSnapshot {
  schemaVersion: 1;
  generatedAt: string;          // ISO Z
  updatedAt: string;            // ISO Z OR ISO +00:00 (Postgres)
  mcpConnectionStatus: 'connected' | 'stale' | 'fallback' | 'offline';
  freshnessWindowMs: number;    // 600000 (10 min)
  dataSource: 'supabase' | 'placeholder';

  priority: ControlCentreCard;       // never null
  blocker: ControlCentreCard | null; // null when nothing blocks
  nextAction: ControlCentreCard;     // never null

  lanes: ControlCentreLane[];

  buildDeploy: {
    android: ControlCentreBuildSide & { versionCode: number | null };
    ios:     ControlCentreBuildSide & { buildNumber: string | null };
  };

  repo: {
    branch: string | null;             // regex-filtered
    shortHead: string | null;          // 7-12 hex
    dirtyFileCount: number | null;
    updatedAt: string;
  };

  manualSteps: ControlCentreManualStep[]; // ≤10
  manualStepsCount: number;

  topBacklog: ControlCentreBacklogItem | null;

  suggestionCounts: {
    candidate: number;
    awaitingApproval: number;
  } | null;

  promptLibrary: ReadonlyArray<{ id: string; title: string; templateId: string }>;
  // Always 4 entries: claude / codex / chatgpt status / terminal-check.

  safety: {
    publicSafe: false;             // always false here
    privateFieldsWithheld: true;   // always true
    withheld: readonly string[];   // 8 categories enumerated
  };
}

interface ControlCentreCard {
  text: string;                   // ≤280 chars, redacted
  status: 'live' | 'repo-only' | 'tester-build' | 'blocked';
  updatedAt: string;
}

interface ControlCentreLane {
  laneId: 'claude' | 'codex' | 'claude_chat' | 'chatgpt' | 'cowork';
  status: 'idle' | 'working' | 'blocked' | 'needs_user' | 'needs_review' | 'done';
  oneLine: string;                // ≤140 chars, redacted
  lastSeenAt: string | null;      // ISO; null when never seen
  hasOpenPrompt: boolean;
}

interface ControlCentreBuildSide {
  status: 'live' | 'repo-only' | 'tester-build' | 'blocked';
  lastChange: string;             // ≤120 chars, server-composed prose
  updatedAt: string;
}

interface ControlCentreManualStep {
  id: string;                     // uuid; stable for marking-done in Phase 4
  text: string;                   // ≤200 chars, redacted
  category:
    | 'supabase' | 'cloudflare' | 'eas' | 'play_console'
    | 'app_store_connect' | 'github' | 'other';
  blocking: boolean;
  approvalRequired: boolean;
  approval: 'pending' | 'approved' | 'completed' | 'declined';
  createdAt: string;
  updatedAt: string;
}

interface ControlCentreBacklogItem {
  id: string;                     // uuid
  title: string;                  // ≤120 chars
  priority: number;               // 1..11 ladder, lower = higher priority
  status: 'live' | 'repo-only' | 'tester-build' | 'blocked' | 'done';
  type:
    | 'bug' | 'ux_issue' | 'feature_idea' | 'release_blocker'
    | 'health_data_issue' | 'ai_coaching_idea'
    | 'monetisation_payment_idea' | 'railway_backend_issue'
    | 'source_integration_issue';
  riskLevel: 'low' | 'medium' | 'high';
  needsBuild: boolean;
  updatedAt: string;
}
```

## 3. Field name confirmations (camelCase, not snake_case)

The Worker emits **camelCase** for every consumer-facing key —
even when the underlying Supabase column is `snake_case`. The
mapping happens in `buildControlCentreSnapshot`. Mobile MUST
read `manualStep.approvalRequired`, NOT `approval_required`;
`topBacklog.riskLevel`, NOT `risk_level`; `topBacklog.needsBuild`,
NOT `needs_build`.

Keys that may surprise:
- `manualStepsCount` is a top-level integer mirror of
  `manualSteps.length` — convenient for the section header
  ("Manual steps (3)") without iterating.
- `suggestionCounts` has TWO keys: `candidate` (open backlog
  rows) and `awaitingApproval` (manual steps with
  `approvalRequired: true` AND `approval: 'pending'`).
- `freshnessWindowMs` is the threshold the mobile client should
  use when its OWN cached snapshot ages — matches the server's
  `mcpConnectionStatus = 'stale'` rule.
- `safety.publicSafe` and `safety.privateFieldsWithheld` are
  literal booleans (`false` and `true` respectively); render
  them as constants, not as values to flip.

## 4. Null handling rules (read these before rendering)

| Field | Null possible? | Mobile rendering |
|---|---|---|
| `priority` | no — always populated | always render the card |
| `blocker` | yes | hide section when null |
| `nextAction` | no | always render the card |
| `lanes` | empty array possible | section: "no lane data yet" |
| `lanes[].lastSeenAt` | yes | render "—" or "never seen" |
| `buildDeploy.android.versionCode` | yes | "Android v?" when null |
| `buildDeploy.ios.buildNumber` | yes | "iOS Build ?" when null |
| `repo.branch` / `repo.shortHead` / `repo.dirtyFileCount` | each yes | hide each missing line |
| `manualSteps` | empty array possible | hide section when 0 |
| `topBacklog` | yes | render "no open items" placeholder when null |
| `suggestionCounts` | null only on read failure | "—" when null; numbers otherwise |

The Worker NEVER returns `undefined` for any documented field;
it always returns the documented type or `null`. If mobile sees
an undefined field, that's a Worker regression — surface a
"snapshot shape mismatch" toast and log the path.

## 5. Mobile rendering checklist (matches `CONTROL_CENTRE_MVP_SPEC.md` § 4)

Order top-to-bottom:

1. **Status banner** — `mcpConnectionStatus` chip + relative
   time (`updatedAt`). Color: green (connected) / amber (stale)
   / red (fallback / offline). Then priority card → blocker
   card (if non-null) → next action card.
2. **Lane cards** — one per `lanes[]` row, max 5. Show
   `laneId`, `status` chip, `oneLine`, "Xm ago" from
   `lastSeenAt`. Tap → no-op in MVP.
3. **Build / Deploy** — Android line + iOS line. Each: `status`
   chip + `lastChange` + relative time.
4. **Manual steps** — list `manualSteps[]`. Each row: `text`,
   `category` chip, `approval` state chip. If `blocking: true`
   add a left-edge red bar. If `approvalRequired: true` show
   "Aaron approval required" caption. Hide section when
   `manualStepsCount === 0`.
5. **Backlog preview** — `topBacklog`. Title + priority + type
   + status + risk. Link "open full backlog" → existing in-app
   backlog screen. When `topBacklog === null`, show
   "No open items".
6. **Prompt library** — render `promptLibrary[].title` as a
   list. Tap → resolve via existing
   `apps/mobile/src/services/prompt-templates.ts`
   `templateId` lookup. Worker DOES NOT return prompt bodies.
7. **Refresh button** — manual fetch. No background polling
   in MVP.

## 6. ISO timestamp parsing

Two formats both appear in this response and BOTH are valid
ISO-8601 UTC:

- `2026-05-07T12:34:56Z` — emitted by `new Date().toISOString()`
  in the Worker (e.g. `generatedAt`, `lanes[].lastSeenAt`).
- `2026-05-07T12:34:56.123456+00:00` — emitted by Postgres
  `timestamptz` columns (e.g. `manualSteps[].updatedAt`,
  `topBacklog.updatedAt`).

`new Date(ts)` parses both correctly. Don't string-compare
timestamps across rows; convert to numeric milliseconds first.

## 7. Caching + offline rules

- Cache the last successful snapshot in
  `expo-secure-store` (or wherever existing
  `connector-status-client.ts` already caches its other
  payloads). Keyed by base URL + token hash.
- On fetch failure, render the cached snapshot with
  `mcpConnectionStatus = 'offline'` (mobile-side override —
  the Worker NEVER returns 'offline', that's the mobile
  client's contribution).
- On 403, do NOT cache — render the inline "Token misconfigured"
  message described in `CONTROL_CENTRE_MVP_SPEC.md` § 4 status
  banner.
- Stale display: if the cached `updatedAt` is older than
  `freshnessWindowMs`, show the chip in amber and append
  "stale Xm ago".

## 8. Out of scope for the mobile MVP

- Writing back to the Worker (marking a manual step approved /
  completed). Phase 4 work, Lane 3.
- Pagination of `manualSteps` or backlog. Cap stays 10 + top-1.
- Polling. Refresh-on-tap is the contract.
- Surfacing the redacted Worker payload's `safety.withheld`
  array in the UI. Render the privacy state through the chip
  on the status banner; the array is for diagnostic curls.

## 9. Anti-rules

- Never render `priority.status` / `blocker.status` /
  `nextAction.status` text as the only signal — always pair the
  enum string with a coloured chip.
- Never compute `mcpConnectionStatus` mobile-side from
  individual updatedAt fields. Trust the server value EXCEPT
  for the 'offline' override on fetch failure.
- Never paste the admin token into any UI string. The token is
  read from env once and never displayed.
- Never display `topBacklog.id` or `manualSteps[].id` to the
  user. They're internal handles for the Phase-4 write API.

## 10. Worker contract guarantees (so Codex doesn't have to ask)

- Every documented field is either the typed value or `null` /
  empty array. No undefined.
- Length caps are enforced server-side; mobile can render
  without truncation logic.
- Every string field passes through the Worker's two-pass
  redactor at the response boundary. Mobile may still apply
  defense-in-depth string trimming for layout, but it does NOT
  need to redact tokens / paths / prompts — already done.
- Enum values are exhaustive as documented. If a future Worker
  build adds a new enum, the spec doc bumps `schemaVersion`
  first; mobile can refuse render on unknown `schemaVersion`.

## 11. Test from the laptop before shipping mobile

```sh
MCP_WORKER_URL=https://lauburu-mcp-preview.lauburu-aaron.workers.dev \
ATHLETE_MEMORY_TOKEN=$(grep '^EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN=' apps/mobile/.env.production | cut -d= -f2) \
npm run cc:test:live
```

12 assertion groups. Re-runs are cheap; the Worker is the
source of truth.
