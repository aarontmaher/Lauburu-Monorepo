/**
 * Pure mapper contract for push-driven approval-gate mutations.
 *
 * Locks the rules in
 * packages/shared/src/approval-gates/push.ts:
 *   - 3 known action ids (approve / deny / defer); anything else → null
 *   - empty / non-string actionId or gateId → null
 *   - case-insensitive match
 *   - approve / deny carry a fixed reason string
 *   - defer carries a deferUntil computed from `now()` + `deferHours`
 *     (default 24h)
 *   - APPROVAL_CATEGORY_IDENTIFIER is a stable identifier so the
 *     iOS notification category cannot drift silently
 */

import {
  APPROVAL_CATEGORY_IDENTIFIER,
  DEFAULT_NOTIFICATION_DEFER_HOURS,
  mapNotificationActionToGateMutation,
} from '../../packages/shared/src/approval-gates/push';

function assert(cond: unknown, label: string): asserts cond {
  if (!cond) {
    console.error(`✗ ${label}`);
    process.exit(1);
  }
}

const NOW = () => new Date('2026-05-09T12:00:00Z');

// ── Stable identifier ────────────────────────────────────────────────

assert(APPROVAL_CATEGORY_IDENTIFIER === 'lauburu_approval_gate_v1', 'APPROVAL_CATEGORY_IDENTIFIER stable');
assert(DEFAULT_NOTIFICATION_DEFER_HOURS === 24, 'DEFAULT_NOTIFICATION_DEFER_HOURS === 24');

// ── Happy paths ──────────────────────────────────────────────────────

const approve = mapNotificationActionToGateMutation('approve', 'gate-test', { now: NOW });
assert(approve !== null && approve.kind === 'approve', 'approve maps to kind=approve');
assert(approve!.gateId === 'gate-test', 'approve preserves gateId');
assert(approve!.reason === 'approved via push notification action', 'approve reason fixed');

const deny = mapNotificationActionToGateMutation('deny', 'gate-test', { now: NOW });
assert(deny !== null && deny.kind === 'deny', 'deny maps to kind=deny');
assert(deny!.reason === 'denied via push notification action', 'deny reason fixed');

const defer = mapNotificationActionToGateMutation('defer', 'gate-test', { now: NOW });
assert(defer !== null && defer.kind === 'defer', 'defer maps to kind=defer');
assert((defer as any).deferUntil === '2026-05-10T12:00:00.000Z', 'defer adds 24h to now() by default');
assert(defer!.reason === 'deferred via push notification action', 'defer reason fixed');

const deferCustom = mapNotificationActionToGateMutation('defer', 'gate-test', { now: NOW, deferHours: 4 });
assert((deferCustom as any).deferUntil === '2026-05-09T16:00:00.000Z', 'defer respects custom deferHours');

// ── Case-insensitive ────────────────────────────────────────────────

const upperApprove = mapNotificationActionToGateMutation('APPROVE', 'gate-test');
assert(upperApprove !== null && upperApprove.kind === 'approve', 'uppercase APPROVE accepted');

const mixedDeny = mapNotificationActionToGateMutation('Deny', 'gate-test');
assert(mixedDeny !== null && mixedDeny.kind === 'deny', 'mixed-case Deny accepted');

// ── Negative paths ──────────────────────────────────────────────────

assert(mapNotificationActionToGateMutation(null, 'gate-test') === null, 'null actionId → null');
assert(mapNotificationActionToGateMutation(undefined, 'gate-test') === null, 'undefined actionId → null');
assert(mapNotificationActionToGateMutation('', 'gate-test') === null, 'empty actionId → null');
assert(mapNotificationActionToGateMutation('approve', null) === null, 'null gateId → null');
assert(mapNotificationActionToGateMutation('approve', undefined) === null, 'undefined gateId → null');
assert(mapNotificationActionToGateMutation('approve', '') === null, 'empty gateId → null');
assert(mapNotificationActionToGateMutation('not-a-real-action', 'gate-test') === null, 'unknown actionId → null');
assert(mapNotificationActionToGateMutation('cancel', 'gate-test') === null, 'cancel actionId NOT mapped to deny (must be exact)');
// Whitespace is NOT trimmed — iOS will deliver exactly the
// identifier we registered, so any drift should surface
// immediately rather than be silently accepted.
assert(mapNotificationActionToGateMutation('approve ', 'gate-test') === null, 'trailing-space actionId rejected (no implicit trim)');
assert(mapNotificationActionToGateMutation(' approve', 'gate-test') === null, 'leading-space actionId rejected (no implicit trim)');

// ── deferHours guards ───────────────────────────────────────────────

const deferZero = mapNotificationActionToGateMutation('defer', 'gate-test', { now: NOW, deferHours: 0 });
assert((deferZero as any).deferUntil === '2026-05-10T12:00:00.000Z', 'deferHours <= 0 falls back to default 24h');

const deferNegative = mapNotificationActionToGateMutation('defer', 'gate-test', { now: NOW, deferHours: -5 });
assert((deferNegative as any).deferUntil === '2026-05-10T12:00:00.000Z', 'negative deferHours falls back to default');

console.log('push approval action mapping test passed.');
