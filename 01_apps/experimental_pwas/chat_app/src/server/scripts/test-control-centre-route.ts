export {}; // make this file a module so its top-level helpers don't collide
            // with assert / isIsoZ in sibling test scripts under tsc.

/**
 * Live integration test for GET /api/control_centre.
 *
 * Asserts:
 *   - 403 without admin token.
 *   - 200 with admin token, body matches the ControlCentreSnapshot
 *     contract documented in docs/CONTROL_CENTRE_MVP_SPEC.md.
 *   - Status discriminators are correctly enumerated.
 *   - Safety flags publicSafe=false, privateFieldsWithheld=true.
 *   - No dangerous patterns appear in the response body
 *     (JWT / sk- / ghp_ / whsec_ / AKIA / EAS UUIDs / GitHub run
 *     IDs / repo paths / SCREAMING-KEBAB-CASE prompt IDs).
 *
 * Skip-mode when env unset (matches test-mcp-worker-live.ts pattern):
 *   MCP_WORKER_URL=… ATHLETE_MEMORY_TOKEN=… \
 *     npx tsx src/server/scripts/test-control-centre-route.ts
 */

const STATUS_LABELS = ['live', 'repo-only', 'tester-build', 'blocked'] as const;
type StatusLabel = (typeof STATUS_LABELS)[number];

const MCP_CONNECTION_STATUSES = ['connected', 'stale', 'fallback', 'offline'] as const;
type McpConnectionStatus = (typeof MCP_CONNECTION_STATUSES)[number];

const LANE_IDS = ['claude', 'codex', 'claude_chat', 'chatgpt', 'cowork'] as const;
const LANE_STATUSES = ['idle', 'working', 'blocked', 'needs_user', 'needs_review', 'done'] as const;

const DANGEROUS_PATTERNS: ReadonlyArray<{ name: string; pattern: RegExp }> = [
  { name: 'JWT', pattern: /eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}/ },
  { name: 'sk- key', pattern: /\bsk-[A-Za-z0-9_-]{16,}\b/ },
  { name: 'ghp_ token', pattern: /\bghp_[A-Za-z0-9]{20,}\b/ },
  { name: 'whsec_', pattern: /\bwhsec_[A-Za-z0-9]{20,}\b/ },
  { name: 'AKIA', pattern: /\bAKIA[0-9A-Z]{16}\b/ },
  { name: 'xox slack', pattern: /\bxox[abposr]-[A-Za-z0-9-]{20,}/ },
  // EAS / Play / TestFlight UUIDs by *field name*, not raw UUID.
  // Row-PK UUIDs (manualSteps[].id, topBacklog.id) are intentional and
  // mobile-readable. The dangerous ones are upstream submission /
  // build IDs whose key names should never appear in this response.
  { name: 'easBuildId field', pattern: /"easBuildId"\s*:/ },
  { name: 'playSubmissionId field', pattern: /"playSubmissionId"\s*:/ },
  { name: 'testflightSubmissionId field', pattern: /"testflightSubmissionId"\s*:/ },
  { name: 'githubRunId field', pattern: /"githubRunId"\s*:/ },
  // GitHub run IDs (10+ digit numeric, surrounded by JSON-string quotes
  // OR comma/space). Catches the same value if it ever leaks into a
  // free-text field.
  { name: 'GitHub run id (numeric)', pattern: /\b\d{10,}\b/ },
  // Prompt IDs follow SCREAMING-KEBAB-CASE-NN; admin-token-gated route
  // is allowed to surface them in upstream payloads, but Control Centre
  // explicitly drops them, so this MUST NOT match.
  { name: 'prompt id', pattern: /\b[A-Z]{2,}(?:-[A-Z0-9]+){2,}-\d{2}\b/ },
];

function assert(cond: unknown, label: string): asserts cond {
  if (!cond) throw new Error(`assertion failed: ${label}`);
}

function isIsoZ(s: unknown): s is string {
  // Accept both ISO-8601 UTC forms — Worker emits 'Z', Postgres emits '+00:00'.
  return typeof s === 'string'
    && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$/.test(s);
}

async function main(): Promise<void> {
  const baseUrl = (process.env.MCP_WORKER_URL ?? '').replace(/\/+$/, '');
  const token = process.env.ATHLETE_MEMORY_TOKEN ?? '';
  if (!baseUrl || !token) {
    console.log('skipping control_centre live test — set MCP_WORKER_URL and ATHLETE_MEMORY_TOKEN.');
    return;
  }

  // 1. Unauth → 403.
  const unauth = await fetch(`${baseUrl}/api/control_centre`);
  assert(unauth.status === 403, `unauth → expected 403, got ${unauth.status}`);
  console.log('✓ /api/control_centre unauth → 403');

  // 2. Auth → 200 + valid schema.
  const res = await fetch(`${baseUrl}/api/control_centre`, {
    headers: { 'x-athlete-memory-token': token },
  });
  assert(res.status === 200, `auth → expected 200, got ${res.status}`);
  const rawBody = await res.text();

  // 3. Dangerous-pattern grep on the raw body.
  for (const { name, pattern } of DANGEROUS_PATTERNS) {
    const match = rawBody.match(pattern);
    if (match) {
      throw new Error(`/api/control_centre leaked ${name}: ${match[0].slice(0, 80)}`);
    }
  }
  console.log(`✓ /api/control_centre clean of all ${DANGEROUS_PATTERNS.length} dangerous patterns`);

  const body = JSON.parse(rawBody) as Record<string, unknown>;

  assert(body.schemaVersion === 1, 'schemaVersion === 1');
  assert(isIsoZ(body.generatedAt), 'generatedAt iso');
  assert(isIsoZ(body.updatedAt), 'updatedAt iso');
  assert(
    typeof body.mcpConnectionStatus === 'string' &&
      (MCP_CONNECTION_STATUSES as readonly string[]).includes(body.mcpConnectionStatus),
    'mcpConnectionStatus enum',
  );
  assert(typeof body.freshnessWindowMs === 'number' && body.freshnessWindowMs > 0, 'freshnessWindowMs');
  assert(body.dataSource === 'supabase' || body.dataSource === 'placeholder', 'dataSource enum');
  console.log(`✓ schema scaffold (dataSource=${body.dataSource}, mcpConnectionStatus=${body.mcpConnectionStatus})`);

  // 4. Cards.
  const card = (v: unknown, label: string) => {
    const c = v as { text?: unknown; status?: unknown; updatedAt?: unknown };
    assert(typeof c.text === 'string' && c.text.length > 0 && c.text.length <= 280, `${label} text`);
    assert(typeof c.status === 'string' && (STATUS_LABELS as readonly string[]).includes(c.status), `${label} status`);
    assert(isIsoZ(c.updatedAt), `${label} updatedAt`);
  };
  card(body.priority, 'priority');
  if (body.blocker !== null) card(body.blocker, 'blocker');
  card(body.nextAction, 'nextAction');
  console.log('✓ priority / blocker / nextAction cards');

  // 5. Lanes.
  const lanes = body.lanes as Array<Record<string, unknown>>;
  assert(Array.isArray(lanes), 'lanes array');
  for (const l of lanes) {
    assert(typeof l.laneId === 'string' && (LANE_IDS as readonly string[]).includes(l.laneId), 'lane id enum');
    assert(typeof l.status === 'string' && (LANE_STATUSES as readonly string[]).includes(l.status), 'lane status enum');
    assert(typeof l.oneLine === 'string' && l.oneLine.length <= 140, 'lane oneLine cap');
    assert(l.lastSeenAt === null || isIsoZ(l.lastSeenAt), 'lane lastSeenAt');
    assert(typeof l.hasOpenPrompt === 'boolean', 'lane hasOpenPrompt boolean');
  }
  console.log(`✓ lanes (${lanes.length})`);

  // 6. Build deploy.
  const bd = body.buildDeploy as { android: Record<string, unknown>; ios: Record<string, unknown> };
  assert(typeof bd === 'object', 'buildDeploy object');
  assert((STATUS_LABELS as readonly string[]).includes(bd.android.status as string), 'android status enum');
  assert((STATUS_LABELS as readonly string[]).includes(bd.ios.status as string), 'ios status enum');
  assert(typeof bd.android.lastChange === 'string' && (bd.android.lastChange as string).length <= 120, 'android lastChange cap');
  assert(typeof bd.ios.lastChange === 'string' && (bd.ios.lastChange as string).length <= 120, 'ios lastChange cap');
  console.log(`✓ buildDeploy (android=${bd.android.status}, ios=${bd.ios.status})`);

  // 7. Repo.
  const repo = body.repo as { branch: unknown; shortHead: unknown; dirtyFileCount: unknown; updatedAt: unknown };
  assert(repo !== null && typeof repo === 'object', 'repo object');
  assert(repo.branch === null || (typeof repo.branch === 'string' && /^[A-Za-z0-9._\-/]{1,80}$/.test(repo.branch)), 'repo branch');
  assert(repo.shortHead === null || (typeof repo.shortHead === 'string' && /^[0-9a-f]{7,12}$/.test(repo.shortHead)), 'repo shortHead');
  assert(repo.dirtyFileCount === null || typeof repo.dirtyFileCount === 'number', 'repo dirtyFileCount');
  assert(isIsoZ(repo.updatedAt), 'repo updatedAt');
  console.log(`✓ repo (branch=${repo.branch}, shortHead=${repo.shortHead})`);

  // 8. Manual steps — rich shape (Phase 2 connector_manual_steps).
  const STEP_CATEGORIES = [
    'supabase', 'cloudflare', 'eas', 'play_console',
    'app_store_connect', 'github', 'other',
  ];
  const STEP_APPROVALS = ['pending', 'approved', 'completed', 'declined'];
  const steps = body.manualSteps as Array<Record<string, unknown>>;
  assert(Array.isArray(steps), 'manualSteps array');
  assert(steps.length <= 10, 'manualSteps cap 10');
  for (const s of steps) {
    assert(typeof s.id === 'string' && (s.id as string).length > 0, 'step id');
    assert(typeof s.text === 'string' && (s.text as string).length <= 200, 'step text cap');
    assert(typeof s.category === 'string' && STEP_CATEGORIES.includes(s.category as string), 'step category enum');
    assert(typeof s.blocking === 'boolean', 'step blocking boolean');
    assert(typeof s.approvalRequired === 'boolean', 'step approvalRequired boolean');
    assert(typeof s.approval === 'string' && STEP_APPROVALS.includes(s.approval as string), 'step approval enum');
    assert(isIsoZ(s.createdAt), 'step createdAt');
    assert(isIsoZ(s.updatedAt), 'step updatedAt');
  }
  assert(typeof body.manualStepsCount === 'number', 'manualStepsCount number');
  console.log(`✓ manualSteps (${steps.length}) with rich shape`);

  // 9. topBacklog (Phase 2 connector_backlog_items).
  if (body.topBacklog !== null) {
    const BACKLOG_STATUSES = ['live', 'repo-only', 'tester-build', 'blocked', 'done'];
    const BACKLOG_TYPES = [
      'bug', 'ux_issue', 'feature_idea', 'release_blocker',
      'health_data_issue', 'ai_coaching_idea',
      'monetisation_payment_idea', 'railway_backend_issue',
      'source_integration_issue',
    ];
    const BACKLOG_RISKS = ['low', 'medium', 'high'];
    const tb = body.topBacklog as Record<string, unknown>;
    assert(typeof tb.id === 'string' && (tb.id as string).length > 0, 'topBacklog id');
    assert(typeof tb.title === 'string' && (tb.title as string).length <= 120, 'topBacklog title cap');
    assert(typeof tb.priority === 'number' && Number.isInteger(tb.priority) && (tb.priority as number) >= 1 && (tb.priority as number) <= 11, 'topBacklog priority 1..11');
    assert(typeof tb.status === 'string' && BACKLOG_STATUSES.includes(tb.status as string), 'topBacklog status enum');
    assert(typeof tb.type === 'string' && BACKLOG_TYPES.includes(tb.type as string), 'topBacklog type enum');
    assert(typeof tb.riskLevel === 'string' && BACKLOG_RISKS.includes(tb.riskLevel as string), 'topBacklog riskLevel enum');
    assert(typeof tb.needsBuild === 'boolean', 'topBacklog needsBuild boolean');
    assert(isIsoZ(tb.updatedAt), 'topBacklog updatedAt');
  }
  console.log(`✓ topBacklog (${body.topBacklog === null ? 'null' : 'populated'})`);

  // 10. suggestionCounts (Phase 2 — null only on read failure now).
  if (body.suggestionCounts !== null) {
    const sc = body.suggestionCounts as { candidate: unknown; awaitingApproval: unknown };
    assert(typeof sc.candidate === 'number' && (sc.candidate as number) >= 0, 'suggestionCounts.candidate');
    assert(typeof sc.awaitingApproval === 'number' && (sc.awaitingApproval as number) >= 0, 'suggestionCounts.awaitingApproval');
  }
  console.log(`✓ suggestionCounts (${body.suggestionCounts === null ? 'null' : `${(body.suggestionCounts as {candidate:number;awaitingApproval:number}).candidate}c/${(body.suggestionCounts as {candidate:number;awaitingApproval:number}).awaitingApproval}a`})`);

  // 10. Prompt library.
  const promptLib = body.promptLibrary as Array<Record<string, unknown>>;
  assert(Array.isArray(promptLib) && promptLib.length === 4, 'promptLibrary length 4');
  for (const p of promptLib) {
    assert(typeof p.title === 'string' && (p.title as string).length <= 80, 'prompt title cap');
  }
  console.log('✓ promptLibrary (4 entries)');

  // 11. Safety.
  const safety = body.safety as { publicSafe: unknown; privateFieldsWithheld: unknown; withheld: unknown };
  assert(safety.publicSafe === false, 'safety.publicSafe === false');
  assert(safety.privateFieldsWithheld === true, 'safety.privateFieldsWithheld === true');
  assert(Array.isArray(safety.withheld) && (safety.withheld as unknown[]).length > 0, 'safety.withheld populated');
  console.log(`✓ safety (publicSafe=false, privateFieldsWithheld=true, ${(safety.withheld as unknown[]).length} categories)`);

  console.log('Control Centre route tests passed.');
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : String(err));
  process.exitCode = 1;
});
