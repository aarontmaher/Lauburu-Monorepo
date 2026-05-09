import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

import {
  ANDROID_CONTROLLER_NOTIFICATION_CATEGORIES,
  buildAndroidControllerContext,
} from '../../apps/mobile/src/services/android-controller-context';

const ROOT = path.resolve(new URL('../..', import.meta.url).pathname);
const ADMIN_DEV = fs.readFileSync(path.join(ROOT, 'apps/mobile/app/admin-dev.tsx'), 'utf8');
const PUSH = fs.readFileSync(path.join(ROOT, 'apps/mobile/src/services/push-approval-notifications.ts'), 'utf8');

assert.deepEqual(
  ANDROID_CONTROLLER_NOTIFICATION_CATEGORIES,
  ['idle_lane', 'approval_needed', 'audit_complete', 'mcp_stale', 'build_blocked'],
  'controller notification categories',
);

const blocked = buildAndroidControllerContext({
  adminEntitled: false,
  platform: 'android',
  generatedAt: '2026-05-09T10:00:00Z',
  mcp: { updatedAt: null, ageMs: null, isStale: true, staleReason: 'no_writeback' },
  lanes: [],
  nextPromptTarget: null,
  humanApprovalCount: 0,
  buildGateStatus: 'blocked',
  qaGateStatus: 'partial',
  overnightQueueCount: 0,
  auditQueueCount: 0,
  healthConnect: { state: 'unknown', lastSyncAt: null, availableMetrics: 0, missingMetrics: [] },
  latestEvidencePath: null,
});
assert.equal(blocked, null, 'controller context hidden without admin entitlement');

const widget = buildAndroidControllerContext({
  adminEntitled: true,
  platform: 'android',
  generatedAt: '2026-05-09T10:00:00Z',
  mcp: { updatedAt: '2026-05-09T09:59:30Z', ageMs: 30_000, isStale: false, staleReason: 'fresh' },
  lanes: [
    { id: 'codex', status: 'working', heartbeatAgeMs: 12_000 },
    { id: 'claude', status: 'idle', heartbeatAgeMs: 70_000, terminalDisagreement: true },
  ],
  nextPromptTarget: 'claude',
  humanApprovalCount: 2,
  buildGateStatus: 'blocked',
  qaGateStatus: 'partial',
  overnightQueueCount: 3,
  auditQueueCount: 1,
  healthConnect: {
    state: 'not_registered',
    lastSyncAt: null,
    availableMetrics: 0,
    missingMetrics: ['hrv', 'sleep', 'steps'],
  },
  latestEvidencePath: 'audit-artifacts/android/20260509-100000/samsung-audit.mp4',
});

assert.ok(widget, 'controller context built');
assert.equal(widget!.mode, 'android_admin_controller');
assert.equal(widget!.mcp.freshness, 'fresh');
assert.equal(widget!.lanes[1].terminalDisagreement, true);
assert.equal(widget!.healthConnect.state, 'not_registered');
assert.equal(widget!.auditRunner.canClearInstalledDeviceGate, false);
assert.equal(widget!.safety.noReleaseActions, true);
assert.equal(widget!.safety.noInstalledBuildVerifiedClaim, true);
assert.ok(widget!.auditRunner.videoCommand.includes('scrcpy --record'), 'video capture command');
assert.ok(widget!.auditRunner.screenshotCommand.includes('adb exec-out screencap'), 'screenshot command');

for (const marker of [
  'Samsung controller home',
  'Audit Runner controls',
  'Human Approval Queue entry point',
  'Health Connect',
  'Copy start audit command',
  'Copy video capture command',
]) {
  assert.ok(ADMIN_DEV.includes(marker), `Admin/Dev missing ${marker}`);
}

assert.ok(PUSH.includes('registerAndroidControllerCategories'), 'push scaffold registers controller categories');
for (const category of ANDROID_CONTROLLER_NOTIFICATION_CATEGORIES) {
  assert.ok(PUSH.includes(category), `push scaffold missing ${category}`);
}

console.log('Android controller context contract test passed.');
