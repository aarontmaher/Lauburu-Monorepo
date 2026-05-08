/**
 * Research-job lifecycle + reuseHash + cache-status contract.
 *
 * Locks in the rules in packages/shared/src/research-jobs/index.ts:
 *   - makeResearchJob refuses missing/secret-shaped topic and prompt
 *   - reuseHash is stable across same trigger + topic + scopeKeys
 *     order, and changes when any of those changes
 *   - markSubmitted / completeResearch / cancelJob status guards
 *   - reuseFromExisting requires reuseHash match + completed source
 *   - supersedeJob marks the older artifact superseded
 *   - refreshArtifactStatus flips valid → stale past freshnessWindow
 *   - exportResearchPrompt includes anti-rules and never the pasted result
 */

import {
  cancelJob,
  completeResearch,
  computeResearchReuseHash,
  exportResearchPrompt,
  makeResearchJob,
  markSubmitted,
  refreshArtifactStatus,
  reuseFromExisting,
  supersedeJob,
  type ResearchJob,
} from '../../packages/shared/src/research-jobs';

function assert(cond: unknown, label: string): asserts cond {
  if (!cond) {
    console.error(`✗ ${label}`);
    process.exit(1);
  }
}

const T0 = '2026-05-09T00:00:00Z';

function freshJob(overrides: Partial<Parameters<typeof makeResearchJob>[0]> = {}): ResearchJob {
  return makeResearchJob({
    id: 'research-test',
    triggerType: 'readiness_pattern',
    topic: 'Multi-day readiness drop after travel',
    prompt: 'Summarise published findings on multi-day readiness drops post-travel. Associations only; no clinical advice.',
    scopeKeys: ['readiness', 'travel', '72h'],
    createdAt: T0,
    ...overrides,
  });
}

// ── construction ─────────────────────────────────────────────────────

const job = freshJob();
assert(job.status === 'draft', 'fresh job is draft');
assert(job.reuseHash.length === 8, 'reuseHash is 8 hex chars');
assert(job.freshnessWindowDays === 30, 'default freshness window 30 days');
assert(job.scopeKeys.length === 3, 'scopeKeys preserved');
assert(job.staleAfter === null && job.completedAt === null, 'completion fields null on draft');

let threw = false;
try { freshJob({ topic: '' }); } catch { threw = true; }
assert(threw, 'empty topic refused');

threw = false;
try { freshJob({ prompt: '' }); } catch { threw = true; }
assert(threw, 'empty prompt refused');

threw = false;
try { freshJob({ topic: 'token sk-abcdefghij1234567890' }); } catch { threw = true; }
assert(threw, 'secret-shaped topic refused');

threw = false;
try { freshJob({ prompt: 'eyJabcdefghij12.eyJklmnopq.qrstuvwxyz secret prompt' }); } catch { threw = true; }
assert(threw, 'secret-shaped prompt refused');

// ── reuseHash determinism ────────────────────────────────────────────

const hashA = computeResearchReuseHash({ triggerType: 'readiness_pattern', topic: 'Multi-day readiness drop after travel', scopeKeys: ['72h', 'travel', 'readiness'] });
const hashB = computeResearchReuseHash({ triggerType: 'readiness_pattern', topic: 'Multi-day readiness drop after travel', scopeKeys: ['readiness', 'travel', '72h'] });
assert(hashA === hashB, 'reuseHash is order-insensitive on scopeKeys');

const hashC = computeResearchReuseHash({ triggerType: 'health_trend_narrative', topic: 'Multi-day readiness drop after travel', scopeKeys: ['readiness', 'travel', '72h'] });
assert(hashC !== hashA, 'changing triggerType changes hash');

const hashD = computeResearchReuseHash({ triggerType: 'readiness_pattern', topic: 'Multi-day readiness drop after travel', scopeKeys: ['readiness', 'travel', '24h'] });
assert(hashD !== hashA, 'changing scopeKeys changes hash');

// ── markSubmitted ────────────────────────────────────────────────────

const now = () => new Date('2026-05-09T01:00:00Z');
const submitted = markSubmitted(job, { now });
assert(submitted.ok && submitted.next.status === 'submitted', 'draft → submitted succeeds');
assert(submitted.next.submittedAt === '2026-05-09T01:00:00.000Z', 'submittedAt recorded');

const reSubmit = markSubmitted(submitted.next, { now });
assert(!reSubmit.ok, 'cannot mark submitted twice');

// ── completeResearch ─────────────────────────────────────────────────

const completed = completeResearch(submitted.next, {
  result: 'Across multiple reviews, multi-day readiness drops post-travel are associated with sleep-debt and parasympathetic withdrawal. No clinical recommendations are appropriate from this summary alone.',
  citations: ['https://example.org/review-1', 'https://example.org/review-2'],
  now,
});
assert(completed.ok && completed.next.status === 'completed', 'submitted → completed succeeds');
assert(completed.next.artifactStatus === 'valid', 'fresh artifact is valid');
assert(completed.next.completedAt === '2026-05-09T01:00:00.000Z', 'completedAt recorded');
assert(completed.next.staleAfter != null, 'staleAfter computed');
assert(completed.next.citations.length === 2, 'citations preserved');

const completeAgain = completeResearch(completed.next, { result: 'second result', now });
assert(!completeAgain.ok, 'cannot complete an already-completed job');

const completeWithSecret = completeResearch(submitted.next, {
  result: 'token sk-abcdefghij1234567890 leaked',
  now,
});
assert(!completeWithSecret.ok, 'completeResearch refuses secret-shaped result');

const completeFromDraft = completeResearch(job, { result: 'short answer', now });
assert(completeFromDraft.ok, 'completeResearch can run direct from draft');

// ── cancelJob ────────────────────────────────────────────────────────

const cancelled = cancelJob(job, { reason: 'Out of scope.' });
assert(cancelled.ok && cancelled.next.status === 'cancelled', 'draft → cancelled succeeds');
assert(cancelled.next.reuseNote === 'Out of scope.', 'cancel reason recorded');

const cancelCompleted = cancelJob(completed.next);
assert(!cancelCompleted.ok, 'cannot cancel completed job');

// ── reuseFromExisting ────────────────────────────────────────────────

const newDraft = makeResearchJob({
  id: 'research-test-2',
  triggerType: 'readiness_pattern',
  topic: 'Multi-day readiness drop after travel',
  prompt: 'Different phrasing of the same scope question.',
  scopeKeys: ['readiness', 'travel', '72h'],
  createdAt: '2026-05-09T02:00:00Z',
});
assert(newDraft.reuseHash === completed.next.reuseHash, 'newDraft hashes the same as completed');

const reused = reuseFromExisting(newDraft, completed.next);
assert(reused.ok && reused.next.status === 'reused', 'reuse succeeds');
assert(reused.next.result === completed.next.result, 'reused inherits result');
assert(reused.next.completedAt === completed.next.completedAt, 'reused inherits completedAt');

const reuseMismatch = reuseFromExisting(
  makeResearchJob({
    id: 'research-test-3',
    triggerType: 'health_trend_narrative',
    topic: 'Different topic',
    prompt: 'Different prompt.',
    scopeKeys: ['x'],
    createdAt: '2026-05-09T03:00:00Z',
  }),
  completed.next,
);
assert(!reuseMismatch.ok, 'reuse with mismatched hash refused');

const reuseNonCompleted = reuseFromExisting(newDraft, submitted.next);
assert(!reuseNonCompleted.ok, 'reuse from non-completed source refused');

// ── refreshArtifactStatus ────────────────────────────────────────────

const veryLater = () => new Date(new Date(completed.next.staleAfter ?? '').getTime() + 86_400_000);
const stale = refreshArtifactStatus(completed.next, { now: veryLater });
assert(stale.artifactStatus === 'stale', 'artifact flips to stale past staleAfter');

const refreshDraft = refreshArtifactStatus(job);
assert(refreshDraft === job, 'draft job passes through unchanged');

// ── supersedeJob ─────────────────────────────────────────────────────

const newer = completeResearch(
  makeResearchJob({
    id: 'research-test-newer',
    triggerType: 'readiness_pattern',
    topic: 'Multi-day readiness drop after travel',
    prompt: 'Updated prompt for the same scope.',
    scopeKeys: ['readiness', 'travel', '72h'],
    createdAt: '2026-06-01T00:00:00Z',
  }),
  { result: 'New canonical summary.', now: () => new Date('2026-06-01T01:00:00Z') },
);
assert(newer.ok, 'newer artifact completes');

const sup = supersedeJob(completed.next, newer.next);
assert(sup.ok, 'supersedeJob ok with matching hash');
assert(sup.older.supersededBy === newer.next.id, 'older.supersededBy set');
assert(sup.older.artifactStatus === 'superseded', 'older.artifactStatus = superseded');

const supSelf = supersedeJob(completed.next, completed.next);
assert(!supSelf.ok, 'cannot supersede self');

const supMismatch = supersedeJob(completed.next, makeResearchJob({
  id: 'research-test-other',
  triggerType: 'protocol_safety_check',
  topic: 'Different scope',
  prompt: 'Different prompt.',
  scopeKeys: [],
  createdAt: '2026-06-01T00:00:00Z',
}));
assert(!supMismatch.ok, 'supersede with hash mismatch refused');

// ── exportResearchPrompt ─────────────────────────────────────────────

const exported = exportResearchPrompt(completed.next);
assert(exported.includes(`reuseHash: ${completed.next.reuseHash}`), 'export shows reuseHash');
assert(exported.includes('Anti-rules'), 'export includes anti-rules block');
assert(!exported.includes(completed.next.result ?? '__no_result__'), 'export does NOT include the pasted result');

console.log('research-jobs lifecycle test passed.');
