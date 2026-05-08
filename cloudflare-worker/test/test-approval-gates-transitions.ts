/**
 * Pure-state-machine contract for approval-gate transitions.
 *
 * Locks in the rules in packages/shared/src/approval-gates/index.ts:
 *   - construction refuses bad safeDefault values for the action type
 *   - construction refuses secret-shaped fields
 *   - approve / defer / cancel / complete only fire from valid statuses
 *   - expireIfDue is idempotent and only acts on pending/deferred past expiry
 *   - resolutionNote secret-shaped values are rejected at every transition
 *   - ledgerNote includes the gate id and resolver
 */

import {
  approveGate,
  cancelGate,
  completeGate,
  deferGate,
  expireIfDue,
  isActionable,
  looksLikeSecret,
  makeApprovalGate,
  type ApprovalGate,
} from '../../packages/shared/src/approval-gates';

function assert(cond: unknown, label: string): asserts cond {
  if (!cond) {
    console.error(`✗ ${label}`);
    process.exit(1);
  }
}

const T0 = '2026-05-09T00:00:00Z';
const T_FUTURE = '2026-05-15T00:00:00Z';
const T_DEFER = '2026-05-12T00:00:00Z';

function freshGate(overrides: Partial<Parameters<typeof makeApprovalGate>[0]> = {}): ApprovalGate {
  return makeApprovalGate({
    id: 'gate-test',
    title: 'Test gate',
    description: 'Approve to proceed with the test action.',
    priority: 'P1',
    actionType: 'eas_build',
    safeDefault: 'wait',
    createdAt: T0,
    expiresAt: T_FUTURE,
    ...overrides,
  });
}

// ── construction guards ──────────────────────────────────────────────

const okGate = freshGate();
assert(okGate.status === 'pending', 'fresh gate starts pending');
assert(okGate.resolvedAt === null && okGate.resolvedBy === null, 'fresh gate has no resolver');

let threw = false;
try { freshGate({ safeDefault: 'notify_only', actionType: 'eas_build' }); } catch { threw = true; }
assert(threw, 'eas_build refuses safeDefault notify_only');

threw = false;
try { freshGate({ safeDefault: 'rollback', actionType: 'eas_build' }); } catch { threw = true; }
assert(threw, 'eas_build refuses safeDefault rollback');

threw = false;
try { freshGate({ description: 'token: eyJabcdefghij.eyJklmnop.qrstuvwxyz' }); } catch { threw = true; }
assert(threw, 'description rejects JWT-shaped token');

threw = false;
try { freshGate({ title: 'hello sk-1234567890abcdef1234' }); } catch { threw = true; }
assert(threw, 'title rejects sk- secret');

threw = false;
try { freshGate({ actionPayload: 'gh_token=ghp_abcdefghijklmnopqrstuvwxyz12' }); } catch { threw = true; }
assert(threw, 'actionPayload rejects GitHub PAT');

threw = false;
try { freshGate({ expiresAt: T0 }); } catch { threw = true; }
assert(threw, 'expiresAt must be after createdAt');

// ── approve / defer / cancel transitions ─────────────────────────────

const now = () => new Date('2026-05-09T01:00:00Z');

const approveResult = approveGate(okGate, 'Aaron iPhone admin-dev', { now, note: 'Looks good.' });
assert(approveResult.ok, 'pending → approved succeeds');
assert(approveResult.next.status === 'approved', 'status becomes approved');
assert(approveResult.next.resolvedBy === 'Aaron iPhone admin-dev', 'resolvedBy recorded');
assert(approveResult.next.resolvedAt === '2026-05-09T01:00:00.000Z', 'resolvedAt recorded');
assert(approveResult.ledgerNote != null && approveResult.ledgerNote.includes('gate-test'), 'ledgerNote names the gate');

const reApprove = approveGate(approveResult.next, 'Aaron');
assert(!reApprove.ok, 'approved → approved blocked');

const deferResult = deferGate(okGate, 'Aaron iPhone admin-dev', T_DEFER, { now });
assert(deferResult.ok, 'pending → deferred succeeds');
assert(deferResult.next.status === 'deferred', 'status becomes deferred');
assert(deferResult.next.deferUntil === T_DEFER, 'deferUntil recorded');

const reApproveAfterDefer = approveGate(deferResult.next, 'Aaron iPhone admin-dev', { now });
assert(reApproveAfterDefer.ok, 'deferred → approved succeeds');

const deferAfterExpiryAttempt = deferGate(okGate, 'Aaron', T_FUTURE);
assert(!deferAfterExpiryAttempt.ok, 'deferUntil >= expiresAt rejected');

const deferWithBadDate = deferGate(okGate, 'Aaron', 'not-a-date');
assert(!deferWithBadDate.ok, 'unparseable deferUntil rejected');

const cancelResult = cancelGate(okGate, 'automation:cancel', { now });
assert(cancelResult.ok, 'pending → cancelled succeeds');
assert(cancelResult.next.status === 'cancelled', 'status becomes cancelled');

const reCancel = cancelGate(cancelResult.next, 'automation:cancel');
assert(!reCancel.ok, 'cancelled → cancelled blocked');

// ── note-secret guards on transitions ────────────────────────────────

const approveWithSecretNote = approveGate(okGate, 'Aaron', { note: 'token sk-abcdefghij1234567890' });
assert(!approveWithSecretNote.ok, 'approve refuses secret-shaped resolutionNote');

const deferWithSecretNote = deferGate(okGate, 'Aaron', T_DEFER, { note: 'jwt eyJabcdefghij12.eyJklmnopq.qrstuvwxyz' });
assert(!deferWithSecretNote.ok, 'defer refuses secret-shaped resolutionNote');

const cancelWithSecretNote = cancelGate(okGate, 'Aaron', { note: 'AKIAIOSFODNN7EXAMPLE' });
assert(!cancelWithSecretNote.ok, 'cancel refuses secret-shaped resolutionNote');

// ── completion path ──────────────────────────────────────────────────

const completeFromPending = completeGate(okGate, 'automation', { now });
assert(!completeFromPending.ok, 'cannot complete a gate that was never approved');

const completeFromApproved = completeGate(approveResult.next, 'automation', { now });
assert(completeFromApproved.ok, 'approved → completed succeeds');
assert(completeFromApproved.next.status === 'completed', 'status becomes completed');

const completeFromCompleted = completeGate(completeFromApproved.next, 'automation');
assert(!completeFromCompleted.ok, 'completed → completed blocked');

// ── expiry ───────────────────────────────────────────────────────────

const past = () => new Date('2026-06-01T00:00:00Z');
const expireResult = expireIfDue(okGate, { now: past });
assert(expireResult.ok, 'past expiresAt expires the gate');
assert(expireResult.next.status === 'expired', 'status becomes expired');
assert(expireResult.next.resolvedBy === 'system:expiry', 'resolvedBy === system:expiry');
assert(expireResult.next.resolutionNote != null && expireResult.next.resolutionNote.includes('safeDefault=wait'), 'resolutionNote records safeDefault');

const expireBeforeDue = expireIfDue(okGate, { now });
assert(!expireBeforeDue.ok, 'pre-expiry call is a no-op');

const expireOnApproved = expireIfDue(approveResult.next, { now: past });
assert(!expireOnApproved.ok, 'expireIfDue ignores already-resolved gates');

const expireIdempotent = expireIfDue(expireResult.next, { now: past });
assert(!expireIdempotent.ok, 'expireIfDue is idempotent — no double expiry');

// ── isActionable ─────────────────────────────────────────────────────

assert(isActionable(okGate), 'pending is actionable');
assert(!isActionable(approveResult.next), 'approved is not actionable');
assert(!isActionable(expireResult.next), 'expired is not actionable');

// Deferred + deferUntil in the past should be actionable again. Construct:
const deferredButOverdue: ApprovalGate = {
  ...freshGate(),
  status: 'deferred',
  deferUntil: '2025-01-01T00:00:00Z',
};
assert(isActionable(deferredButOverdue), 'deferred-but-overdue is actionable');

const deferredFuture: ApprovalGate = {
  ...freshGate(),
  status: 'deferred',
  deferUntil: '2099-01-01T00:00:00Z',
};
assert(!isActionable(deferredFuture), 'deferred + future deferUntil is not actionable');

// ── secret detection helper ──────────────────────────────────────────

assert(looksLikeSecret('eyJabcdefghij12.eyJklmnopq.qrstuvwxyz'), 'JWT detected');
assert(looksLikeSecret('sk-abcdefghij1234567890'), 'sk- detected');
assert(looksLikeSecret('ghp_abcdefghijklmnopqrstuvwxyz12'), 'ghp_ detected');
assert(looksLikeSecret('AKIAIOSFODNN7EXAMPLE'), 'AKIA detected');
assert(!looksLikeSecret('Approve Android v20 Play Internal upload'), 'normal copy passes');
assert(!looksLikeSecret('cd cloudflare-worker && npx wrangler deploy --env preview'), 'shell command passes');

console.log('approval-gates transitions test passed.');
