/**
 * Admin home widget context contract.
 *
 * Separate from the user widget adapter. This adapter is developer
 * MCP only, entitlement gated, and exposes summaries/counts without
 * secrets, raw logs, full prompts, or private worker text.
 */

import assert from 'node:assert/strict';
import { buildAdminHomeWidgetContext } from '../../apps/mobile/src/services/admin-home-widget-context';

{
  const blocked = buildAdminHomeWidgetContext({
    adminEntitled: false,
    generatedAt: '2026-05-09T08:00:00Z',
    mcp: { updatedAt: '2026-05-09T07:59:50Z', ageMs: 10_000, isStale: false, staleReason: 'fresh' },
    lanes: [],
    nextPromptTarget: 'codex',
    humanApprovalCount: 1,
    buildGateStatus: 'blocked',
    qaGateStatus: 'partial',
    overnightQueueCount: 2,
    auditQueueCount: 3,
  });
  assert.equal(blocked, null, 'admin widget must be hidden without admin entitlement');
}

{
  const widget = buildAdminHomeWidgetContext({
    adminEntitled: true,
    generatedAt: '2026-05-09T08:00:00Z',
    mcp: { updatedAt: '2026-05-09T07:59:50Z', ageMs: 10_000, isStale: false, staleReason: 'fresh' },
    lanes: [
      { id: 'claude', status: 'idle', heartbeatAgeMs: 8_000 },
      { id: 'codex', status: 'in_progress', heartbeatAgeMs: 12_000 },
      { id: 'cowork', status: 'blocked', heartbeatAgeMs: 20_000 },
    ],
    nextPromptTarget: 'codex',
    humanApprovalCount: 2,
    buildGateStatus: 'blocked',
    qaGateStatus: 'partial',
    overnightQueueCount: 4,
    auditQueueCount: 5,
  });

  assert.ok(widget);
  assert.equal(widget!.mode, 'admin');
  assert.equal(widget!.mcp.freshness, 'fresh');
  assert.equal(widget!.mcp.lastWritebackAgeMs, 10_000);
  assert.deepEqual(widget!.lanes.map((l) => `${l.id}:${l.state}`), ['claude:idle', 'codex:working', 'agent:blocked']);
  assert.equal(widget!.nextPromptTarget, 'codex');
  assert.equal(widget!.approvals.humanApprovalCount, 2);
  assert.equal(widget!.gates.build, 'blocked');
  assert.equal(widget!.gates.qa, 'partial');
  assert.equal(widget!.queues.overnightCount, 4);
  assert.equal(widget!.queues.auditCount, 5);
  assert.equal(widget!.deepLink, '/admin-dev');
  assert.equal(widget!.safety.developerMcpOnly, true);
  assert.equal(widget!.safety.includesSecrets, false);
  assert.equal(widget!.safety.includesRawLogs, false);
  assert.equal(widget!.safety.includesPromptText, false);
  assert.equal(widget!.safety.noInstalledBuildVerifiedClaim, true);
}

{
  const widget = buildAdminHomeWidgetContext({
    adminEntitled: true,
    generatedAt: '2026-05-09T08:00:00Z',
    mcp: {
      updatedAt: null,
      ageMs: null,
      isStale: true,
      staleReason: 'no_writeback_with_extra_private_detail_that_must_be_capped_because_widgets_are_small',
    },
    lanes: [{ id: 'claude', status: 'complete_waiting_approval', heartbeatAgeMs: -20 }],
    nextPromptTarget: 'full prompt: do secret thing',
    humanApprovalCount: -3,
    buildGateStatus: 'clear',
    qaGateStatus: 'ready_for_review',
    overnightQueueCount: 1.9,
    auditQueueCount: Number.NaN,
  });

  assert.ok(widget);
  assert.equal(widget!.mcp.freshness, 'missing');
  assert.ok((widget!.mcp.staleReason ?? '').length <= 64, 'stale reason is capped');
  assert.equal(widget!.lanes[0].state, 'needs_review');
  assert.equal(widget!.lanes[0].heartbeatAgeMs, null, 'negative heartbeat ages are not surfaced');
  assert.equal(widget!.nextPromptTarget, null, 'free-form prompt text must not become widget data');
  assert.equal(widget!.approvals.humanApprovalCount, 0);
  assert.equal(widget!.queues.overnightCount, 1);
  assert.equal(widget!.queues.auditCount, 0);
}

console.log('Admin home widget context contract test passed.');
