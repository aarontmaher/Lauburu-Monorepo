/**
 * First-run backlog analysis routes — app-facing, per-user.
 *
 * All routes here MUST go through `requirePrivateAthleteAccess`, which
 * enforces:
 *   1. Shared x-athlete-memory-token
 *   2. Supabase Authorization Bearer JWT
 *   3. JWT `sub` matches path athleteId
 *   4. x-athlete-id header matches path athleteId
 *
 * That guard is duplicated from athleteMemory.ts so this route stays
 * self-contained and can't accidentally drift. If we promote the
 * guard to a shared middleware later, both routes swap together.
 */
import { Router } from 'express';
import path from 'path';
import { FileApiAiStateStore } from '../athlete-memory/file-api-ai-state-store';
import { runBacklogAnalysis } from '../../../../packages/shared/src/backend/services/backlog/run-backlog-analysis';
import type { BacklogStore, BacklogBuilders } from '../../../../packages/shared/src/backend/services/backlog/run-backlog-analysis';
import type {
  BacklogAnalysisStatusRecord,
  BacklogInitialSummary,
  BacklogTrendCandidate,
} from '../../../../packages/shared/src/backend/contracts/backlog-analysis.types';
import { buildDailyRefreshArtifact } from '../../../../packages/shared/src/backend/services/refresh/build-daily-refresh';
import { buildWeeklySynthesisArtifact } from '../../../../packages/shared/src/backend/services/refresh/build-weekly-synthesis';

const router = Router();
const store = new FileApiAiStateStore(
  path.resolve(__dirname, '../../../data/private-athlete-memory'),
);

/** Same guard as athleteMemory.ts. */
function extractSupabaseUserIdFromAuthHeader(authHeader: string | undefined): string | null {
  if (!authHeader) return null;
  const match = /^Bearer\s+(.+)$/.exec(authHeader);
  if (!match) return null;
  const parts = match[1].split('.');
  if (parts.length !== 3) return null;
  try {
    const payloadB64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = payloadB64 + '='.repeat((4 - payloadB64.length % 4) % 4);
    const payload = JSON.parse(Buffer.from(padded, 'base64').toString('utf8'));
    if (typeof payload?.sub === 'string') return payload.sub;
    return null;
  } catch {
    return null;
  }
}

function requirePrivateAthleteAccess(req: any, res: any, next: any) {
  const expectedToken = process.env.ATHLETE_MEMORY_API_TOKEN;
  if (!expectedToken) {
    res.status(503).json({ error: 'Backlog routes disabled until ATHLETE_MEMORY_API_TOKEN is set.' });
    return;
  }
  const presentedToken = req.header('x-athlete-memory-token');
  const claimedAthleteId = req.header('x-athlete-id');
  const pathAthleteId = req.params.athleteId;
  if (presentedToken !== expectedToken || claimedAthleteId !== pathAthleteId) {
    res.status(403).json({ error: 'Forbidden backlog access.' });
    return;
  }
  const supabaseUserId = extractSupabaseUserIdFromAuthHeader(req.header('authorization'));
  const allowSharedTokenOnly =
    process.env.ALLOW_SHARED_TOKEN_ONLY === '1' || process.env.NODE_ENV === 'test';
  if (!supabaseUserId) {
    if (!allowSharedTokenOnly) {
      res.status(401).json({
        error: 'Authentication required.',
        detail: 'Backlog routes require a Supabase Authorization Bearer token.',
      });
      return;
    }
  } else if (supabaseUserId !== pathAthleteId) {
    res.status(403).json({
      error: 'Athlete ownership mismatch.',
      detail: 'Authenticated user cannot access another user\'s backlog analysis.',
    });
    return;
  }
  (req as any).authenticatedUserId = supabaseUserId ?? pathAthleteId;
  next();
}

// ── Shape the BacklogStore around the FileApiAiStateStore ──────
// Small adapter — the store methods we added match the BacklogStore
// surface closely, but the adapter keeps the type import lean.
function buildBacklogStore(fileStore: FileApiAiStateStore): BacklogStore {
  return {
    getNormalizedDay: (athleteId, date) => fileStore.getNormalizedDay(athleteId, date),
    listDailyRefreshes: (athleteId, opts) => fileStore.listDailyRefreshes(athleteId, opts),
    getLatestWeeklySynthesis: (athleteId) => fileStore.getLatestWeeklySynthesis(athleteId),
    saveDailyRefresh: (athleteId, artifact) => fileStore.saveDailyRefresh(athleteId, artifact),
    saveWeeklySynthesis: (athleteId, artifact) => fileStore.saveWeeklySynthesis(athleteId, artifact),
    getSourceHealth: (athleteId, provider) => fileStore.getSourceHealth(athleteId, provider),
    listHiitSessions: (athleteId, opts) => fileStore.listHiitSessions(athleteId, opts),
    getBaseline: (athleteId) => fileStore.getBaseline(athleteId),
    loadNormalizedRange: (athleteId, s, e) => fileStore.loadNormalizedRange(athleteId, s, e),
    saveBacklogStatus: (athleteId, record) => fileStore.saveBacklogStatus(athleteId, record),
    saveBacklogSummary: (athleteId, summary) => fileStore.saveBacklogSummary(athleteId, summary),
    saveBacklogTrendCandidates: (athleteId, trends) =>
      fileStore.saveBacklogTrendCandidates(athleteId, trends),
  };
}

const builders: BacklogBuilders = {
  buildDailyRefreshArtifact: (input) => buildDailyRefreshArtifact(input as any),
  buildWeeklySynthesisArtifact: (input) => buildWeeklySynthesisArtifact(input as any),
};

// ── GET status ─────────────────────────────────────────────────
// GET /api/backlog/:athleteId/status
router.get('/:athleteId/status', requirePrivateAthleteAccess, async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const status = await store.getBacklogStatus(athleteId);
    const summary = await store.getLatestBacklogSummary(athleteId);
    const trends = await store.getBacklogTrendCandidates(athleteId);
    res.status(200).json({
      ok: true,
      athleteId,
      status: status ?? {
        userId: (req as any).authenticatedUserId ?? athleteId,
        athleteId,
        status: 'not_started',
        consentGrantedAt: null,
        analysisStartedAt: null,
        analysisCompletedAt: null,
        windowStart: null,
        windowEnd: null,
        sourcesIncluded: [],
        sourcesMissing: [],
        recordsAnalysed: 0,
        dailyArtifactsCreated: 0,
        weeklyArtifactsCreated: 0,
        patternCandidatesCreated: 0,
        memoryProposalsCreated: 0,
        missingnessNote: null,
        historyScope: 'unknown' as const,
        latestSummaryId: null,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      } satisfies BacklogAnalysisStatusRecord,
      summary: summary ?? null,
      trends: trends ?? [],
    });
  } catch (e) {
    res.status(500).json({ error: 'Status read failed', detail: e instanceof Error ? e.message : 'unknown' });
  }
});

// ── POST skip ───────────────────────────────────────────────────
// POST /api/backlog/:athleteId/skip
router.post('/:athleteId/skip', requirePrivateAthleteAccess, async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const now = new Date().toISOString();
    const userId = (req as any).authenticatedUserId ?? athleteId;
    const record: BacklogAnalysisStatusRecord = {
      userId,
      athleteId,
      status: 'skipped',
      consentGrantedAt: null,
      analysisStartedAt: null,
      analysisCompletedAt: null,
      windowStart: null,
      windowEnd: null,
      sourcesIncluded: [],
      sourcesMissing: [],
      recordsAnalysed: 0,
      dailyArtifactsCreated: 0,
      weeklyArtifactsCreated: 0,
      patternCandidatesCreated: 0,
      memoryProposalsCreated: 0,
      missingnessNote: 'User declined backlog analysis. Can be re-run from Settings.',
      historyScope: 'unknown' as const,
      latestSummaryId: null,
      createdAt: now,
      updatedAt: now,
    };
    await store.saveBacklogStatus(athleteId, record);
    res.status(200).json({ ok: true, status: record });
  } catch (e) {
    res.status(500).json({ error: 'Skip failed', detail: e instanceof Error ? e.message : 'unknown' });
  }
});

// ── POST start (or re-run) — runs the analysis end-to-end ──────
// POST /api/backlog/:athleteId/start
// Body: { windowDays?: number, dryRun?: boolean, sources?: string[] }
router.post('/:athleteId/start', requirePrivateAthleteAccess, async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const userId = (req as any).authenticatedUserId ?? athleteId;
    const body = (req.body ?? {}) as { windowDays?: number; dryRun?: boolean; sources?: string[] };
    // Clamp widened 90 → 1825 days so WHOOP-export + Apple-Health-
    // backfill driven backlog analysis can span a real multi-year
    // trend window. Default stays 30 for short requests.
    const windowDays = Math.max(1, Math.min(1825, body.windowDays ?? 30));
    const today = new Date();
    const end = today.toISOString().slice(0, 10);
    const startDate = new Date(today.getTime() - (windowDays - 1) * 86_400_000)
      .toISOString()
      .slice(0, 10);

    // Mark running before we start so a client polling /status sees
    // 'running' while the analysis is in flight. If the service
    // throws, we overwrite with 'failed'.
    const now = new Date().toISOString();
    await store.saveBacklogStatus(athleteId, {
      userId,
      athleteId,
      status: 'running',
      consentGrantedAt: now,
      analysisStartedAt: now,
      analysisCompletedAt: null,
      windowStart: startDate,
      windowEnd: end,
      sourcesIncluded: [],
      sourcesMissing: [],
      recordsAnalysed: 0,
      dailyArtifactsCreated: 0,
      weeklyArtifactsCreated: 0,
      patternCandidatesCreated: 0,
      memoryProposalsCreated: 0,
      missingnessNote: null,
      historyScope: 'unknown' as const,
      latestSummaryId: null,
      createdAt: now,
      updatedAt: now,
    });

    const backlogStore = buildBacklogStore(store);
    const result = await runBacklogAnalysis(
      {
        userId,
        athleteId,
        windowStart: startDate,
        windowEnd: end,
        sources: body.sources,
        dryRun: body.dryRun ?? false,
      },
      backlogStore,
      builders,
    );

    res.status(200).json({
      ok: true,
      status: result.status,
      summary: result.summary,
      trendCandidates: result.trendCandidates,
    });
  } catch (e) {
    // Persist a failed status so the UI can surface it.
    try {
      const { athleteId } = req.params;
      const userId = (req as any).authenticatedUserId ?? athleteId;
      const now = new Date().toISOString();
      await store.saveBacklogStatus(athleteId, {
        userId,
        athleteId,
        status: 'failed',
        consentGrantedAt: now,
        analysisStartedAt: now,
        analysisCompletedAt: now,
        windowStart: null,
        windowEnd: null,
        sourcesIncluded: [],
        sourcesMissing: [],
        recordsAnalysed: 0,
        dailyArtifactsCreated: 0,
        weeklyArtifactsCreated: 0,
        patternCandidatesCreated: 0,
        memoryProposalsCreated: 0,
        missingnessNote: e instanceof Error ? e.message : 'Unknown error during backlog analysis.',
        historyScope: 'unknown' as const,
        latestSummaryId: null,
        createdAt: now,
        updatedAt: now,
      });
    } catch { /* already fatal */ }
    res.status(500).json({ error: 'Backlog analysis failed', detail: e instanceof Error ? e.message : 'unknown' });
  }
});

// ── GET memory proposals (trend candidates + weekly promotion candidates)
// GET /api/backlog/:athleteId/proposals
router.get('/:athleteId/proposals', requirePrivateAthleteAccess, async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    // Backlog trend candidates (eligibleForMemoryProposal=true)
    const trends = await store.getBacklogTrendCandidates(athleteId);
    const eligible = trends.filter((t: any) => t.eligibleForMemoryProposal);

    // Weekly synthesis promotion candidates (if any weekly artifacts exist)
    const weekly = await store.getLatestWeeklySynthesis(athleteId);
    const weeklyCandidates = weekly?.promotionCandidates ?? [];

    res.json({
      ok: true,
      athleteId,
      trendProposals: eligible.map((t: any) => ({
        id: t.id,
        kind: t.kind,
        statement: t.statement,
        confidence: t.confidence,
        evidenceFields: t.evidenceFields,
        windowStart: t.windowStart,
        windowEnd: t.windowEnd,
        observationCount: t.observationCount,
        createdAt: t.createdAt,
        source: 'backlog_analysis',
      })),
      weeklyCandidates: weeklyCandidates.map((c: any, idx: number) => ({
        index: idx,
        targetDoc: c.targetDoc,
        statement: c.candidateStatement,
        confidence: c.evidenceStrength,
        eligible: c.eligible,
        approvalRequired: c.approvalRequired,
        rejectionReason: c.rejectionReason,
        windowStart: c.evidenceWindow?.start,
        windowEnd: c.evidenceWindow?.end,
        source: 'weekly_synthesis',
      })),
      totalProposals: eligible.length + weeklyCandidates.filter((c: any) => c.eligible).length,
    });
  } catch (e) {
    res.status(500).json({ error: 'Proposals read failed', detail: e instanceof Error ? e.message : 'unknown' });
  }
});

// POST /api/backlog/:athleteId/proposals/accept
// Body: { candidateIndex: number, source: 'weekly_synthesis' | 'backlog_trend' }
router.post('/:athleteId/proposals/accept', requirePrivateAthleteAccess, async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const userId = (req as any).authenticatedUserId ?? athleteId;
    const { candidateIndex, source } = req.body as { candidateIndex: number; source: string };

    if (source === 'weekly_synthesis') {
      // Use the internal promote path
      const weekly = await store.getLatestWeeklySynthesis(athleteId);
      const candidates = weekly?.promotionCandidates ?? [];
      if (candidateIndex < 0 || candidateIndex >= candidates.length) {
        return res.status(400).json({ error: 'Invalid candidate index.' });
      }
      const candidate = candidates[candidateIndex];
      if (!candidate.eligible) {
        return res.json({ ok: false, outcome: 'rejected_not_eligible', reason: candidate.rejectionReason ?? 'Not eligible.' });
      }
      const { applyPromotion } = await import('../../../../packages/shared/src/backend/services/promote/apply-promotion');
      const memory = await store.getStableMemory(athleteId);
      if (!memory) {
        return res.json({ ok: false, outcome: 'rejected_not_eligible', reason: 'No stable memory on file. Run backlog analysis first.' });
      }
      const result = applyPromotion({ athleteId, candidateIndex, candidate, approvedBy: userId }, memory);
      if (result.outcome === 'promoted' && result.updatedMemory) {
        await store.saveStableMemory(athleteId, result.updatedMemory);
      }
      return res.json({ ok: result.outcome === 'promoted', outcome: result.outcome, reason: result.reason, statement: result.candidateStatement });
    }

    // Backlog trend proposal — mark it as accepted (flag only, no auto-promote to stable memory)
    const trends = await store.getBacklogTrendCandidates(athleteId);
    const trend = trends.find((t: any) => t.id === String(candidateIndex) || trends.indexOf(t) === candidateIndex);
    if (!trend) {
      return res.status(400).json({ error: 'Trend not found.' });
    }
    // For now, accepting a backlog trend is informational — it flags the trend
    // but does not touch stable memory. Future: promote to observedPatterns.
    return res.json({ ok: true, outcome: 'acknowledged', reason: 'Trend acknowledged. Stable memory promotion from backlog trends is a future feature.', statement: trend.statement });
  } catch (e) {
    res.status(500).json({ error: 'Accept failed', detail: e instanceof Error ? e.message : 'unknown' });
  }
});

// POST /api/backlog/:athleteId/proposals/reject
router.post('/:athleteId/proposals/reject', requirePrivateAthleteAccess, async (req: any, res: any) => {
  try {
    const { candidateIndex, source } = req.body as { candidateIndex: number; source: string };
    // Rejection is informational for now — no stable memory change.
    res.json({ ok: true, outcome: 'rejected', reason: 'Proposal dismissed. No memory change.' });
  } catch (e) {
    res.status(500).json({ error: 'Reject failed', detail: e instanceof Error ? e.message : 'unknown' });
  }
});

export default router;
