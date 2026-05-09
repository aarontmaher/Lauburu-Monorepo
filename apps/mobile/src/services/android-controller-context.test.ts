import {
  buildAndroidControllerContext,
  ANDROID_CONTROLLER_NOTIFICATION_CATEGORIES,
  type AndroidControllerContextInput,
} from './android-controller-context';

function fail(message: string): never {
  throw new Error(message);
}

function assertEqual<T>(actual: T, expected: T, message: string): void {
  if (actual !== expected) {
    fail(`${message}: expected ${String(expected)}, got ${String(actual)}`);
  }
}

function baseInput(overrides: Partial<AndroidControllerContextInput> = {}): AndroidControllerContextInput {
  return {
    adminEntitled: true,
    platform: 'android',
    generatedAt: '2026-05-10T00:00:00Z',
    mcp: { updatedAt: '2026-05-10T00:00:00Z', ageMs: 1_000, isStale: false, staleReason: null },
    lanes: [
      { id: 'claude', status: 'idle', heartbeatAgeMs: 5_000 },
      { id: 'codex', status: 'working', heartbeatAgeMs: 1_000 },
    ],
    nextPromptTarget: 'claude',
    humanApprovalCount: 0,
    buildGateStatus: 'unknown',
    qaGateStatus: 'unknown',
    overnightQueueCount: 0,
    auditQueueCount: 0,
    healthConnect: { state: 'connected', lastSyncAt: '2026-05-10T00:00:00Z', availableMetrics: 4, missingMetrics: [] },
    latestEvidencePath: null,
    ...overrides,
  };
}

// 1. Non-android / non-admin returns null (admin gate).
assertEqual(buildAndroidControllerContext(baseInput({ adminEntitled: false })), null, 'non-admin → null');
assertEqual(buildAndroidControllerContext(baseInput({ platform: 'ios' })), null, 'iOS → null');

// 2. Fresh MCP maps to fresh.
{
  const ctx = buildAndroidControllerContext(baseInput());
  if (!ctx) fail('expected fresh context');
  assertEqual(ctx.mcp.freshness, 'fresh', 'fresh');
  assertEqual(ctx.platform, 'android', 'platform');
  assertEqual(ctx.mode, 'android_admin_controller', 'mode');
}

// 3. Stale → stale; missing updatedAt → missing.
{
  const stale = buildAndroidControllerContext(baseInput({
    mcp: { updatedAt: '2026-05-10T00:00:00Z', ageMs: 999_999, isStale: true, staleReason: 'too old' },
  }));
  if (!stale) fail('expected stale context');
  assertEqual(stale.mcp.freshness, 'stale', 'stale');
  assertEqual(stale.mcp.staleReason, 'too old', 'stale reason preserved');

  const missing = buildAndroidControllerContext(baseInput({
    mcp: { updatedAt: null, ageMs: null, isStale: false, staleReason: null },
  }));
  if (!missing) fail('expected missing context');
  assertEqual(missing.mcp.freshness, 'missing', 'missing freshness');
}

// 4. safety + auditRunner invariants — no live claims.
{
  const ctx = buildAndroidControllerContext(baseInput());
  if (!ctx) fail('expected ctx');
  assertEqual(ctx.safety.publicSafe, true, 'publicSafe');
  assertEqual(ctx.safety.includesSecrets, false, 'no secrets');
  assertEqual(ctx.safety.noReleaseActions, true, 'no release actions');
  assertEqual(ctx.safety.noInstalledBuildVerifiedClaim, true, 'no installed-build verified claim');
  assertEqual(ctx.auditRunner.simulatorOrMirrorEvidenceOnly, true, 'mirror-only evidence');
  assertEqual(ctx.auditRunner.canClearInstalledDeviceGate, false, 'cannot clear installed-device gate');
}

// 5. notification categories are exposed and stable.
{
  const ctx = buildAndroidControllerContext(baseInput());
  if (!ctx) fail('expected ctx');
  assertEqual(ctx.notifications.categories.length, ANDROID_CONTROLLER_NOTIFICATION_CATEGORIES.length, 'categories shape');
  for (const c of ANDROID_CONTROLLER_NOTIFICATION_CATEGORIES) {
    if (!ctx.notifications.categories.includes(c)) fail(`missing category ${c}`);
  }
}

// 6. lanes truncated to 8 entries; bad heartbeats normalised to null.
{
  const lanes = Array.from({ length: 12 }, (_, i) => ({
    id: `lane-${i}`,
    status: 'idle',
    heartbeatAgeMs: i % 2 === 0 ? -100 : 1_000,
  }));
  const ctx = buildAndroidControllerContext(baseInput({ lanes }));
  if (!ctx) fail('expected ctx');
  assertEqual(ctx.lanes.length, 8, 'lanes truncated');
  for (const lane of ctx.lanes) {
    if (lane.heartbeatAgeMs !== null && lane.heartbeatAgeMs < 0) fail('negative heartbeat must be null');
  }
}

// 7. count() clamps negatives / non-finite to 0.
{
  const ctx = buildAndroidControllerContext(baseInput({
    humanApprovalCount: -5,
    overnightQueueCount: Number.NaN,
    auditQueueCount: 1.7,
    healthConnect: { state: 'connected', lastSyncAt: null, availableMetrics: -1, missingMetrics: [] },
  }));
  if (!ctx) fail('expected ctx');
  assertEqual(ctx.approvals.humanApprovalCount, 0, 'negative approvals clamp to 0');
  assertEqual(ctx.queues.overnightCount, 0, 'NaN overnight clamps to 0');
  assertEqual(ctx.queues.auditCount, 1, 'fractional audit floors to 1');
  assertEqual(ctx.healthConnect.availableMetrics, 0, 'negative metrics clamps to 0');
}

console.log('android-controller-context: all assertions passed');
