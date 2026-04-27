/**
 * Internal-only backend job routes — /v1/internal/...
 *
 * These are NOT client-callable app routes. They are called by:
 *   - the scheduler (athleteRefreshScheduler.ts)
 *   - manual operator triggers
 *   - future cron/Cloud Scheduler
 *
 * Auth: requires INTERNAL_API_TOKEN header. If not configured,
 * all internal routes return 503.
 *
 * Pipeline:
 *   POST /v1/internal/ingest/whoop/daily
 *     → ingestWhoopBatch → saveRawDay per day
 *
 *   POST /v1/internal/normalize/daily-metrics
 *     → load raw days → normalizeWhoopBatch → saveNormalizedDay per day
 *
 *   POST /v1/internal/athletes/:athleteId/jobs/daily-refresh
 *     → load normalized + baseline → buildDailyRefreshArtifact → save
 *
 *   POST /v1/internal/athletes/:athleteId/jobs/weekly-synthesis
 *     → load daily artifacts + baseline → buildWeeklySynthesisArtifact → save
 *
 * Non-negotiable:
 *   - Normalized records stay interpretation-free
 *   - Daily refresh never mutates stable memory
 *   - Weekly synthesis never auto-promotes
 *   - All stored objects get ids, schema versions, timestamps
 */

import { Router } from 'express';
import path from 'path';
import { FileApiAiStateStore } from '../athlete-memory/file-api-ai-state-store';
import { ingestWhoopBatch, type WhoopMcpDayPayload } from '../../../../packages/shared/src/backend/services/whoop/ingest-whoop';
import { normalizeWhoopBatch } from '../../../../packages/shared/src/backend/services/normalize/normalize-daily-metrics';
import { buildDailyRefreshArtifact } from '../../../../packages/shared/src/backend/services/refresh/build-daily-refresh';
import { buildWeeklySynthesisArtifact } from '../../../../packages/shared/src/backend/services/refresh/build-weekly-synthesis';
import type { NormalizedDailyMetrics } from '../../../../packages/shared/src/backend/contracts/normalized-daily.types';
import type { DailyRefreshArtifact } from '../../../../packages/shared/src/backend/contracts/refresh-artifacts.types';
import type { AthletePhysiologyBaseline } from '../../../../packages/shared/src/athlete-memory/types';
import type { SourceHealthStatus } from '../../../../packages/shared/src/backend/contracts/freshness.types';
import { readAthleteState } from '../../../../packages/shared/src/backend/services/orchestrate/read-athlete-state';
import { createLiveWhoopReader } from '../sources/liveWhoopReader';
import { applyPromotion, type PromotionRequest } from '../../../../packages/shared/src/backend/services/promote/apply-promotion';
import { initializeAthlete } from '../../../../packages/shared/src/backend/services/initialize/initialize-athlete';
import { fetchWhoopRecent } from '../sources/liveWhoopReader';
import { deriveHealthCheck } from '../../../../packages/shared/src/backend/services/health-check/derive-health-check';
import { ingestNutritionDay, isNutritionIngestConfirmed, type NutritionIngestPayload } from '../../../../packages/shared/src/backend/services/nutrition/ingest-nutrition';
import { applyNutritionToNormalized } from '../../../../packages/shared/src/backend/services/nutrition/normalize-nutrition';
import type { NutritionDailyMetricsRaw } from '../../../../packages/shared/src/backend/contracts/nutrition-raw.types';
import { ingestHealthSourceDay, normalizeHealthSourceDay, type HealthSourceIngestPayload } from '../../../../packages/shared/src/backend/services/health-source/ingest-health-source';
import { buildMultiSourceHealth } from '../../../../packages/shared/src/backend/services/health-source/build-multi-source-health';
import { ingestAndNormalizeSessionLog } from '../../../../packages/shared/src/backend/services/session/ingest-session-log';
import type { SessionLogIngestPayload, NormalizedSessionSummary } from '../../../../packages/shared/src/backend/contracts/session-log.types';
import { DefaultCronometerAdapter, normalizeCronometerDaily } from '../../../../packages/shared/src/backend/services/cronometer/cronometer-adapter';
import { buildCronometerCoverage } from '../../../../packages/shared/src/backend/contracts/cronometer.types';
import { recordSourceConnectionState, type SourceName } from '../lib/sourceConnectionStateSink';

const router = Router();

const store = new FileApiAiStateStore(
  path.resolve(__dirname, '../../../data/private-athlete-memory'),
);

// ── Auth guard ────────────────────────────────────────────────

function requireInternalAuth(req: any, res: any, next: any) {
  const expected = process.env.INTERNAL_API_TOKEN;
  if (!expected) {
    res.status(503).json({ error: 'Internal routes disabled until INTERNAL_API_TOKEN is configured.' });
    return;
  }
  if (req.header('x-internal-token') !== expected) {
    res.status(403).json({ error: 'Forbidden.' });
    return;
  }
  next();
}

router.use(requireInternalAuth);

// ── 0. WHOOP sync trigger + status ──────────────────────────
// POST /v1/internal/whoop/trigger-sync
// Triggers a WHOOP MCP sync so today's data is available.
// Fire-and-forget on the MCP side — returns immediately after triggering.

const WHOOP_MCP_DIRECT = process.env.WHOOP_MCP_URL
  ?? 'https://whoop-mcp-production-032e.up.railway.app';

router.post('/whoop/trigger-sync', async (req: any, res: any) => {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    const mcpResp = await fetch(`${WHOOP_MCP_DIRECT}/diag/trigger-sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
    }).catch(() => null);
    clearTimeout(timer);

    if (mcpResp?.ok) {
      const body = await mcpResp.json().catch(() => ({}));
      res.status(200).json({
        ok: true,
        triggered: true,
        latestDate: (body as any).latest_local_date ?? null,
        note: 'Sync triggered. Full completion takes 2-3 minutes.',
      });
    } else {
      res.status(200).json({
        ok: true,
        triggered: false,
        note: 'Sync trigger sent but MCP did not confirm. Sync may still be running.',
      });
    }
  } catch (error) {
    res.status(500).json({
      ok: false,
      triggered: false,
      error: error instanceof Error ? error.message : 'unknown',
    });
  }
});

// GET /v1/internal/whoop/freshness
// Returns WHOOP source-health for an athlete, plus whether today's data exists.
router.get('/whoop/:athleteId/freshness', async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const today = new Date().toISOString().slice(0, 10);
    const sourceHealth = await store.getSourceHealth(athleteId, 'whoop');
    const normalizedToday = await store.getNormalizedDay(athleteId, today);
    const hasTodayRecovery = normalizedToday?.recoveryScore != null;
    const hasTodaySleep = normalizedToday?.totalSleepHours != null;
    const hasTodayStrain = normalizedToday?.dailyStrain != null;

    res.status(200).json({
      ok: true,
      athleteId,
      today,
      sourceHealth: sourceHealth ?? { status: 'not_connected' },
      todayAvailable: {
        recovery: hasTodayRecovery,
        sleep: hasTodaySleep,
        strain: hasTodayStrain,
        normalized: normalizedToday != null,
      },
      freshForLiveMode: hasTodayRecovery && hasTodaySleep,
    });
  } catch (error) {
    res.status(500).json({ error: 'Freshness check failed.', detail: error instanceof Error ? error.message : 'unknown' });
  }
});

// ── 1. Ingest raw WHOOP data ─────────────────────────────────
// POST /v1/internal/ingest/whoop/daily
// Body: { athleteId: string, days: WhoopMcpDayPayload[] }

router.post('/ingest/whoop/daily', async (req: any, res: any) => {
  try {
    const { athleteId, days } = req.body as {
      athleteId: string;
      days: WhoopMcpDayPayload[];
    };
    if (!athleteId || !Array.isArray(days) || days.length === 0) {
      res.status(400).json({ error: 'athleteId and non-empty days[] required.' });
      return;
    }

    const rawRecords = ingestWhoopBatch(days, athleteId);
    for (const record of rawRecords) {
      await store.saveRawDay(athleteId, record);
    }

    // Update source health after successful ingest
    const latestRaw = rawRecords[rawRecords.length - 1];
    const now = new Date().toISOString();
    await store.saveSourceHealth(athleteId, 'whoop', {
      id: `source_health_whoop_${athleteId}`,
      schemaVersion: 1,
      createdAt: now,
      updatedAt: now,
      athleteId,
      provider: 'whoop',
      lastSuccessfulIngestAt: now,
      lastFailedIngestAt: null,
      freshnessStatus: 'fresh',
      coverageByDomain: {
        recovery: { lastDate: latestRaw.localDate, status: latestRaw.recoveryScore != null ? 'fresh' : 'missing' },
        sleep: { lastDate: latestRaw.localDate, status: latestRaw.totalSleepHours != null ? 'fresh' : 'missing' },
        strain: { lastDate: latestRaw.localDate, status: latestRaw.dayStrain != null ? 'fresh' : 'missing' },
        workouts: { lastDate: latestRaw.localDate, status: latestRaw.workoutCount > 0 ? 'fresh' : 'stale' },
      },
      upstreamStatus: 'healthy',
      degradedReason: null,
    });

    void recordSourceConnectionState({
      userId: athleteId,
      source: 'whoop',
      status: 'connected',
      lastIngestedAt: now,
      lastSuccessAt: now,
      metadata: { lastDate: latestRaw.localDate, ingested: rawRecords.length },
    });

    res.status(200).json({
      ok: true,
      ingested: rawRecords.length,
      dates: rawRecords.map((r) => r.localDate),
    });
  } catch (error) {
    // Update source health on failure
    const { athleteId: aId } = (req.body ?? {}) as { athleteId?: string };
    if (aId) {
      const now = new Date().toISOString();
      const existing = await store.getSourceHealth(aId, 'whoop');
      await store.saveSourceHealth(aId, 'whoop', {
        id: `source_health_whoop_${aId}`,
        schemaVersion: 1,
        createdAt: existing?.createdAt ?? now,
        updatedAt: now,
        athleteId: aId,
        provider: 'whoop',
        lastSuccessfulIngestAt: existing?.lastSuccessfulIngestAt ?? null,
        lastFailedIngestAt: now,
        freshnessStatus: existing?.freshnessStatus ?? 'missing',
        coverageByDomain: existing?.coverageByDomain ?? {},
        upstreamStatus: 'degraded',
        degradedReason: error instanceof Error ? error.message : 'Ingest failed',
      });
      void recordSourceConnectionState({
        userId: aId,
        source: 'whoop',
        status: 'error',
        lastFailureAt: now,
        lastFailureReason: error instanceof Error ? error.message.slice(0, 200) : 'ingest_failed',
      });
    }
    res.status(500).json({
      error: 'Ingest failed.',
      detail: error instanceof Error ? error.message : 'unknown',
    });
  }
});

// ── 2. Normalize daily metrics ───────────────────────────────
// POST /v1/internal/normalize/daily-metrics
// Body: { athleteId: string, dates: string[] }
// Loads raw records for the given dates, normalizes, saves.

router.post('/normalize/daily-metrics', async (req: any, res: any) => {
  try {
    const { athleteId, dates } = req.body as {
      athleteId: string;
      dates: string[];
    };
    if (!athleteId || !Array.isArray(dates) || dates.length === 0) {
      res.status(400).json({ error: 'athleteId and non-empty dates[] required.' });
      return;
    }

    const rawRecords = [];
    for (const date of dates) {
      const raw = await store.getRawDay(athleteId, date);
      if (raw) rawRecords.push(raw);
    }

    if (rawRecords.length === 0) {
      res.status(404).json({ error: 'No raw records found for given dates.' });
      return;
    }

    // normalizeWhoopBatch expects WhoopDailyMetricsRaw[]
    const normalized = normalizeWhoopBatch(rawRecords as any);
    for (const record of normalized) {
      await store.saveNormalizedDay(athleteId, record);
    }

    res.status(200).json({
      ok: true,
      normalized: normalized.length,
      dates: normalized.map((r) => r.date),
      completeness: normalized.map((r) => r.completeness),
    });
  } catch (error) {
    res.status(500).json({
      error: 'Normalization failed.',
      detail: error instanceof Error ? error.message : 'unknown',
    });
  }
});

// ── 3. Daily refresh job ─────────────────────────────────────
// POST /v1/internal/athletes/:athleteId/jobs/daily-refresh
// Body: { date: string } (YYYY-MM-DD)
// Loads normalized record + recent 3 days + baseline → builds artifact → saves.

router.post('/athletes/:athleteId/jobs/daily-refresh', async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const { date } = req.body as { date: string };
    if (!date) {
      res.status(400).json({ error: 'date (YYYY-MM-DD) required in body.' });
      return;
    }

    // Load today's normalized record
    const todayNorm = await store.getNormalizedDay(athleteId, date) as NormalizedDailyMetrics | null;
    if (!todayNorm) {
      res.status(404).json({ error: `No normalized record for ${date}. Run normalize first.` });
      return;
    }

    // Load recent 3 days for rolling risk
    const threeDaysAgo = offsetDate(date, -2);
    const recentNorm = (await store.loadNormalizedRange(athleteId, threeDaysAgo, date)) as NormalizedDailyMetrics[];

    // Load baseline from stable memory
    const memory = await store.getStableMemory(athleteId);
    const baseline = memory?.physiologyBaseline;
    if (!baseline) {
      res.status(412).json({ error: 'No stable baseline found. Initialize athlete memory first.' });
      return;
    }

    const artifact = buildDailyRefreshArtifact({
      today: todayNorm,
      recent3Days: recentNorm.length > 0 ? recentNorm : [todayNorm],
      baseline: baseline as AthletePhysiologyBaseline,
    });

    await store.saveDailyRefresh(athleteId, artifact);

    res.status(200).json({
      ok: true,
      artifactId: artifact.id,
      sourceDate: artifact.sourceDate,
      dayState: artifact.dayState,
      confidence: artifact.confidence,
      rollingRiskLevel: artifact.rollingRiskLevel,
    });
  } catch (error) {
    res.status(500).json({
      error: 'Daily refresh failed.',
      detail: error instanceof Error ? error.message : 'unknown',
    });
  }
});

// ── 4. Weekly synthesis job ──────────────────────────────────
// POST /v1/internal/athletes/:athleteId/jobs/weekly-synthesis
// Body: { weekStart: string, weekEnd: string }
// Loads daily artifacts for the week + baseline → builds synthesis → saves.

router.post('/athletes/:athleteId/jobs/weekly-synthesis', async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const { weekStart, weekEnd } = req.body as { weekStart: string; weekEnd: string };
    if (!weekStart || !weekEnd) {
      res.status(400).json({ error: 'weekStart and weekEnd required in body.' });
      return;
    }

    // Load daily artifacts for the week
    const dailies = await store.listDailyRefreshes(athleteId, {
      startDate: weekStart,
      endDate: weekEnd,
    });

    if (dailies.length === 0) {
      res.status(404).json({ error: `No daily artifacts found for ${weekStart}–${weekEnd}. Run daily refresh first.` });
      return;
    }

    // Load baseline
    const memory = await store.getStableMemory(athleteId);
    const baseline = memory?.physiologyBaseline;
    if (!baseline) {
      res.status(412).json({ error: 'No stable baseline found.' });
      return;
    }

    const synthesis = buildWeeklySynthesisArtifact({
      athleteId,
      weekStart,
      weekEnd,
      dailyArtifacts: dailies,
      baseline: baseline as AthletePhysiologyBaseline,
    });

    await store.saveWeeklySynthesis(athleteId, synthesis);

    res.status(200).json({
      ok: true,
      artifactId: synthesis.id,
      weekStart: synthesis.weekStart,
      weekEnd: synthesis.weekEnd,
      dailyArtifactCount: synthesis.dailyArtifactCount,
      confidence: synthesis.confidence,
      dominantDriver: synthesis.dominantDriver,
      promotionCandidateCount: synthesis.promotionCandidates.length,
    });
  } catch (error) {
    res.status(500).json({
      error: 'Weekly synthesis failed.',
      detail: error instanceof Error ? error.message : 'unknown',
    });
  }
});

// ── Helper ───────────────────────────────────────────────────

function offsetDate(date: string, days: number): string {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

// ── 5. Full daily pipeline: ingest → normalize → refresh ─────
// POST /v1/internal/athletes/:athleteId/pipeline/daily
// Body: { date: string, days: WhoopMcpDayPayload[] }
// Chains all three steps so the scheduler makes one call per athlete.
// Fails explicitly at whichever step breaks. Does NOT mutate stable memory.

router.post('/athletes/:athleteId/pipeline/daily', async (req: any, res: any) => {
  const { athleteId } = req.params;
  const { date, days } = req.body as {
    date: string;
    days: WhoopMcpDayPayload[];
  };
  if (!date || !Array.isArray(days) || days.length === 0) {
    res.status(400).json({ error: 'date and non-empty days[] required.' });
    return;
  }

  const steps: Array<{ step: string; ok: boolean; detail?: unknown }> = [];

  try {
    // Step 1: Ingest raw
    const rawRecords = ingestWhoopBatch(days, athleteId);
    for (const record of rawRecords) {
      await store.saveRawDay(athleteId, record);
    }
    steps.push({ step: 'ingest', ok: true, detail: { count: rawRecords.length } });

    // Step 2: Normalize (interpretation-free)
    const normalized = normalizeWhoopBatch(rawRecords as any);
    for (const record of normalized) {
      await store.saveNormalizedDay(athleteId, record);
    }
    steps.push({ step: 'normalize', ok: true, detail: { count: normalized.length, completeness: normalized.map((r) => r.completeness) } });

    // Step 3: Daily refresh (athlete-relative interpretation)
    const todayNorm = normalized.find((n) => n.date === date);
    if (!todayNorm) {
      steps.push({ step: 'daily_refresh', ok: false, detail: `No normalized record for ${date}.` });
      res.status(200).json({ ok: false, steps, error: `Normalized data missing for ${date}.` });
      return;
    }

    const threeDaysAgo = offsetDate(date, -2);
    const recentNorm = normalized.filter((n) => n.date >= threeDaysAgo && n.date <= date);

    const memory = await store.getStableMemory(athleteId);
    const baseline = memory?.physiologyBaseline;
    if (!baseline) {
      steps.push({ step: 'daily_refresh', ok: false, detail: 'No stable baseline. Initialize athlete memory first.' });
      res.status(200).json({ ok: false, steps, error: 'Missing baseline.' });
      return;
    }

    const artifact = buildDailyRefreshArtifact({
      today: todayNorm,
      recent3Days: recentNorm.length > 0 ? recentNorm : [todayNorm],
      baseline: baseline as AthletePhysiologyBaseline,
    });

    await store.saveDailyRefresh(athleteId, artifact);
    steps.push({
      step: 'daily_refresh',
      ok: true,
      detail: {
        artifactId: artifact.id,
        dayState: artifact.dayState,
        confidence: artifact.confidence,
        rollingRiskLevel: artifact.rollingRiskLevel,
      },
    });

    res.status(200).json({ ok: true, steps });
  } catch (error) {
    steps.push({
      step: 'pipeline_error',
      ok: false,
      detail: error instanceof Error ? error.message : 'unknown',
    });
    res.status(500).json({ ok: false, steps });
  }
});

// ── 6. Read athlete state via orchestrator ───────────────────
// GET /v1/internal/athletes/:athleteId/read
// Query: ?date=YYYY-MM-DD&requiredFields=recovery,hrv&realtime=true
// Returns the full cache-first resolved state with layer provenance.

router.get('/athletes/:athleteId/read', async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const date = req.query.date as string | undefined;
    const requiredFields = req.query.requiredFields
      ? (req.query.requiredFields as string).split(',').map((s: string) => s.trim())
      : [];
    const userRequestedRealtime = req.query.realtime === 'true';

    const result = await readAthleteState(
      { athleteId, date, requiredFields, userRequestedRealtime },
      store,
      createLiveWhoopReader(store),
    );

    const sourceHealth = await store.getSourceHealth(athleteId, 'whoop');
    const isSeedMode = result.dailyArtifact?.sourceDate !== result.date;
    const isProvisional = sourceHealth?.upstreamStatus === 'degraded'
      || sourceHealth?.freshnessStatus === 'stale'
      || sourceHealth?.freshnessStatus === 'missing';

    res.status(200).json({
      ok: true,
      ...result,
      sourceHealth,
      seedMode: isSeedMode,
      provisionalUntilDirectWhoop: isProvisional,
      seedCaveats: isSeedMode || isProvisional
        ? [
            isSeedMode ? 'Daily artifact is from a previous date, not today.' : null,
            sourceHealth?.degradedReason ?? null,
            isProvisional ? 'Artifacts derived from cached seed data, not live WHOOP.' : null,
          ].filter(Boolean)
        : [],
    });
  } catch (error) {
    res.status(500).json({
      error: 'Read orchestration failed.',
      detail: error instanceof Error ? error.message : 'unknown',
    });
  }
});

// ── 7. Read promotion candidates from latest weekly synthesis ─
// GET /v1/internal/athletes/:athleteId/promotion-candidates
// Returns typed candidates that require explicit approval.

router.get('/athletes/:athleteId/promotion-candidates', async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const weekly = await store.getLatestWeeklySynthesis(athleteId);

    if (!weekly) {
      res.status(404).json({ error: 'No weekly synthesis artifact found.' });
      return;
    }

    res.status(200).json({
      ok: true,
      weekStart: weekly.weekStart,
      weekEnd: weekly.weekEnd,
      generatedAt: weekly.generatedAt,
      candidates: weekly.promotionCandidates,
      totalCandidates: weekly.promotionCandidates.length,
      eligibleCount: weekly.promotionCandidates.filter((c) => c.eligible).length,
      allRequireApproval: weekly.promotionCandidates.every((c) => c.approvalRequired),
    });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to read promotion candidates.',
      detail: error instanceof Error ? error.message : 'unknown',
    });
  }
});

// ── 8. Source health status ──────────────────────────────────
// GET /v1/internal/athletes/:athleteId/source-health/:provider

router.get('/athletes/:athleteId/source-health/:provider', async (req: any, res: any) => {
  try {
    const { athleteId, provider } = req.params;
    const health = await store.getSourceHealth(athleteId, provider);

    if (!health) {
      res.status(404).json({ error: `No source health for provider ${provider}.` });
      return;
    }

    res.status(200).json({ ok: true, ...health });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to read source health.',
      detail: error instanceof Error ? error.message : 'unknown',
    });
  }
});

// ── 9. Explicit promotion of weekly candidates into stable memory ─
// POST /v1/internal/athletes/:athleteId/promote
// Body: { candidateIndex: number, approvedBy: string }
// Reads the latest weekly synthesis, validates the candidate,
// applies the promotion to stable memory, persists.
// Daily/weekly refresh flows NEVER call this route.

router.post('/athletes/:athleteId/promote', async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const { candidateIndex, approvedBy } = req.body as {
      candidateIndex: number;
      approvedBy: string;
    };

    if (candidateIndex == null || !approvedBy) {
      res.status(400).json({ error: 'candidateIndex (number) and approvedBy (string) required.' });
      return;
    }

    // Load latest weekly to get the candidate
    const weekly = await store.getLatestWeeklySynthesis(athleteId);
    if (!weekly) {
      res.status(404).json({ error: 'No weekly synthesis artifact. Run weekly synthesis first.' });
      return;
    }

    const candidate = weekly.promotionCandidates[candidateIndex];
    if (!candidate) {
      res.status(404).json({
        error: `Candidate index ${candidateIndex} not found. Available: ${weekly.promotionCandidates.length} candidates.`,
      });
      return;
    }

    // Load current stable memory
    const currentMemory = await store.getStableMemory(athleteId);
    if (!currentMemory) {
      res.status(412).json({ error: 'No stable memory found. Initialize athlete memory first.' });
      return;
    }

    // Apply promotion (pure function — validates eligibility, returns result)
    const result = applyPromotion(
      { athleteId, candidateIndex, candidate, approvedBy },
      currentMemory,
    );

    // Only persist if actually promoted
    if (result.outcome === 'promoted' && result.updatedMemory) {
      await store.saveStableMemory(athleteId, result.updatedMemory);
    }

    const statusCode = result.outcome === 'promoted' ? 200 : 422;
    res.status(statusCode).json({
      ok: result.outcome === 'promoted',
      outcome: result.outcome,
      reason: result.reason,
      targetDoc: result.targetDoc,
      candidateStatement: result.candidateStatement,
    });
  } catch (error) {
    res.status(500).json({
      error: 'Promotion failed.',
      detail: error instanceof Error ? error.message : 'unknown',
    });
  }
});

// ── 10. Initialize new athlete from first-ingest data ────────
// POST /v1/internal/athletes/:athleteId/initialize
// Body: { timezone: string }
// Loads whatever normalized metrics exist for this athlete,
// computes initial baselines, creates blank stable memory.
// Does NOT require pre-existing seeded state.
// Does NOT auto-promote or create patterns/hypotheses.

router.post('/athletes/:athleteId/initialize', async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const { timezone } = req.body as { timezone?: string };
    if (!timezone) {
      res.status(400).json({ error: 'timezone required in body.' });
      return;
    }

    // Check if stable memory already exists (don't overwrite)
    const existing = await store.getStableMemory(athleteId);
    if (existing) {
      res.status(409).json({
        error: 'Athlete already initialized.',
        updatedAt: existing.updatedAt,
        dataWindowDays: existing.physiologyBaseline.dataWindowDays,
      });
      return;
    }

    // Load all available normalized metrics. Previously capped at
    // 90 days; lifted to 5 years so tester backlog uploads (Apple
    // Health 365d, WHOOP export up to 2y+) actually reach the
    // initialize/refresh pipeline. The store already de-dupes + the
    // per-day footprint is small.
    const normalized = await store.getNormalizedRecent(athleteId, 1825);

    const result = initializeAthlete({
      athleteId,
      history: normalized,
      timezone,
    });

    if (!result.ok) {
      res.status(412).json({
        error: 'Cannot initialize — no data available.',
        warnings: result.warnings,
      });
      return;
    }

    // Persist stable memory and manifest
    await store.saveStableMemory(athleteId, result.memory);

    res.status(200).json({
      ok: true,
      athleteId,
      confidence: result.confidence,
      dataWindowDays: result.dataWindowDays,
      baseline: {
        recovery: result.baseline.recoveryBaseline,
        hrv: result.baseline.hrvBaseline,
        restingHr: result.baseline.restingHrBaseline,
        sleep: result.baseline.sleepBaseline,
        strain: result.baseline.strainBaseline,
      },
      warnings: result.warnings,
    });
  } catch (error) {
    res.status(500).json({
      error: 'Initialization failed.',
      detail: error instanceof Error ? error.message : 'unknown',
    });
  }
});

// ── 11. Reingest from live WHOOP — upgrade from seed mode ────
// POST /v1/internal/athletes/:athleteId/reingest-from-whoop
// Body: { days?: number } (default 7)
// Fetches fresh WHOOP data via bridge, runs the full pipeline
// (ingest → normalize → daily refresh → weekly synthesis),
// updates source health. Does NOT touch stable memory.
// If WHOOP is unavailable, returns honest degraded result.

router.post('/athletes/:athleteId/reingest-from-whoop', async (req: any, res: any) => {
  const { athleteId } = req.params;
  const days = (req.body?.days as number) ?? 7;
  const steps: Array<{ step: string; ok: boolean; detail?: unknown }> = [];

  try {
    // Step 1: Fetch live WHOOP data
    const whoopDays = await fetchWhoopRecent(days);

    if (whoopDays.length === 0) {
      // WHOOP unavailable — update source health honestly and return
      const now = new Date().toISOString();
      const existingHealth = await store.getSourceHealth(athleteId, 'whoop');
      await store.saveSourceHealth(athleteId, 'whoop', {
        id: `source_health_whoop_${athleteId}`,
        schemaVersion: 1,
        createdAt: existingHealth?.createdAt ?? now,
        updatedAt: now,
        athleteId,
        provider: 'whoop',
        lastSuccessfulIngestAt: existingHealth?.lastSuccessfulIngestAt ?? null,
        lastFailedIngestAt: now,
        freshnessStatus: existingHealth?.freshnessStatus ?? 'missing',
        coverageByDomain: existingHealth?.coverageByDomain ?? {},
        upstreamStatus: 'degraded',
        degradedReason: 'Live WHOOP fetch returned no data. Bridge may be unavailable or auth expired.',
      });
      steps.push({ step: 'fetch_whoop', ok: false, detail: 'No WHOOP data returned.' });
      res.status(200).json({ ok: false, steps, seedMode: true, reason: 'WHOOP unavailable — seed mode preserved.' });
      return;
    }

    steps.push({ step: 'fetch_whoop', ok: true, detail: { days: whoopDays.length, dates: whoopDays.map((d) => d.local_date) } });

    // Step 2: Ingest raw
    const rawRecords = ingestWhoopBatch(whoopDays, athleteId);
    for (const record of rawRecords) {
      await store.saveRawDay(athleteId, record); // No seedMode marker — this is live data
    }
    steps.push({ step: 'ingest', ok: true, detail: { count: rawRecords.length } });

    // Step 3: Normalize
    const normalized = normalizeWhoopBatch(rawRecords as any);
    for (const record of normalized) {
      await store.saveNormalizedDay(athleteId, record); // No seedMode marker — live data
    }
    steps.push({ step: 'normalize', ok: true, detail: { count: normalized.length, completeness: normalized.map((r) => r.completeness) } });

    // Step 4: Rebuild daily artifacts for each day
    const memory = await store.getStableMemory(athleteId);
    if (!memory?.physiologyBaseline) {
      steps.push({ step: 'daily_refresh', ok: false, detail: 'No baseline — run initialize first.' });
      res.status(200).json({ ok: false, steps, seedMode: true, reason: 'Missing baseline.' });
      return;
    }

    const dailyArtifacts: DailyRefreshArtifact[] = [];
    for (const norm of normalized) {
      const threeDaysAgo = offsetDate(norm.date, -2);
      const recent = normalized.filter((n) => n.date >= threeDaysAgo && n.date <= norm.date);
      const artifact = buildDailyRefreshArtifact({
        today: norm,
        recent3Days: recent.length > 0 ? recent : [norm],
        baseline: memory.physiologyBaseline as AthletePhysiologyBaseline,
      });
      await store.saveDailyRefresh(athleteId, artifact); // No seedMode — live
      dailyArtifacts.push(artifact);
    }
    const latestDaily = dailyArtifacts[dailyArtifacts.length - 1];
    steps.push({ step: 'daily_refresh', ok: true, detail: { count: dailyArtifacts.length, latest: latestDaily?.sourceDate, dayState: latestDaily?.dayState } });

    // Step 5: Rebuild weekly synthesis if we have enough dailies
    if (dailyArtifacts.length >= 3) {
      const latestDate = dailyArtifacts[dailyArtifacts.length - 1].sourceDate;
      const weekStart = startOfWeek(latestDate);
      const weekDailies = dailyArtifacts.filter((a) => a.sourceDate >= weekStart);
      if (weekDailies.length >= 3) {
        const synthesis = buildWeeklySynthesisArtifact({
          athleteId,
          weekStart,
          weekEnd: latestDate,
          dailyArtifacts: weekDailies,
          baseline: memory.physiologyBaseline as AthletePhysiologyBaseline,
        });
        await store.saveWeeklySynthesis(athleteId, synthesis); // No seedMode — live
        steps.push({ step: 'weekly_synthesis', ok: true, detail: { weekStart, weekEnd: latestDate, dailyCount: weekDailies.length } });
      } else {
        steps.push({ step: 'weekly_synthesis', ok: false, detail: `Only ${weekDailies.length} dailies in current week — need 3+.` });
      }
    } else {
      steps.push({ step: 'weekly_synthesis', ok: false, detail: `Only ${dailyArtifacts.length} total dailies — need 3+.` });
    }

    // Step 6: Update source health to live/fresh
    const latestRaw = rawRecords[rawRecords.length - 1];
    const now = new Date().toISOString();
    await store.saveSourceHealth(athleteId, 'whoop', {
      id: `source_health_whoop_${athleteId}`,
      schemaVersion: 1,
      createdAt: now,
      updatedAt: now,
      athleteId,
      provider: 'whoop',
      lastSuccessfulIngestAt: now,
      lastFailedIngestAt: null,
      freshnessStatus: 'fresh',
      coverageByDomain: {
        recovery: { lastDate: latestRaw.localDate, status: latestRaw.recoveryScore != null ? 'fresh' : 'missing' },
        sleep: { lastDate: latestRaw.localDate, status: latestRaw.totalSleepHours != null ? 'fresh' : 'missing' },
        strain: { lastDate: latestRaw.localDate, status: latestRaw.dayStrain != null ? 'fresh' : 'missing' },
        workouts: { lastDate: latestRaw.localDate, status: latestRaw.workoutCount > 0 ? 'fresh' : 'stale' },
      },
      upstreamStatus: 'healthy',
      degradedReason: null,
    });
    steps.push({ step: 'source_health', ok: true, detail: { freshnessStatus: 'fresh', upstreamStatus: 'healthy' } });

    // The athlete is now live — seedMode is false for new artifacts
    res.status(200).json({
      ok: true,
      steps,
      seedMode: false,
      provisionalUntilDirectWhoop: false,
      transitionedToLive: true,
    });
  } catch (error) {
    steps.push({ step: 'pipeline_error', ok: false, detail: error instanceof Error ? error.message : 'unknown' });
    res.status(500).json({ ok: false, steps });
  }
});

// ── 12. Health check — one canonical system summary ──────────
// GET /v1/internal/athletes/:athleteId/health-check
// Returns seed/live mode, source coverage, artifact freshness,
// safe/not-safe guidance, and recommended read order in one call.
// Does NOT write or fetch anything — pure read derivation.

router.get('/athletes/:athleteId/health-check', async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const today = new Date().toISOString().slice(0, 10);

    const [dailyArtifact, weeklyArtifact, stableMemory, whoopHealth] = await Promise.all([
      store.getLatestDailyRefresh(athleteId),
      store.getLatestWeeklySynthesis(athleteId),
      store.getStableMemory(athleteId),
      store.getSourceHealth(athleteId, 'whoop'),
    ]);

    const check = deriveHealthCheck({
      athleteId,
      today,
      dailyArtifact,
      weeklyArtifact,
      stableMemory,
      whoopHealth,
    });

    res.status(200).json(check);
  } catch (error) {
    res.status(500).json({
      error: 'Health check failed.',
      detail: error instanceof Error ? error.message : 'unknown',
    });
  }
});

function startOfWeek(date: string): string {
  const d = new Date(`${date}T00:00:00Z`);
  const day = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() - day + 1);
  return d.toISOString().slice(0, 10);
}

// ── 13. Nutrition ingest + normalize ─────────────────────────
// POST /v1/internal/ingest/nutrition/daily
// Body: { athleteId: string, day: NutritionIngestPayload }
// Ingests raw nutrition, then merges into the existing normalized
// record for that date. If no normalized record exists, creates
// a minimal one with nutrition only.

router.post('/ingest/nutrition/daily', async (req: any, res: any) => {
  try {
    const { athleteId, day } = req.body as {
      athleteId: string;
      day: NutritionIngestPayload;
    };
    if (!athleteId || !day?.date) {
      res.status(400).json({ error: 'athleteId and day with date required.' });
      return;
    }

    // Step 1: Ingest raw nutrition (always store raw, even if unconfirmed)
    const rawNutrition = ingestNutritionDay(day, athleteId);
    // Save raw nutrition (reuse the store's generic write)
    await store.saveRawNutrition(athleteId, rawNutrition as any);

    // Gate: unconfirmed barcode/photo proposals are stored as raw evidence
    // but NEVER enter normalized nutrition.
    if (!isNutritionIngestConfirmed(day)) {
      res.status(200).json({
        ok: true,
        athleteId,
        date: day.date,
        stored: 'raw_only',
        reason: 'Unconfirmed nutrition proposal stored as evidence. Confirm to enter normalized nutrition.',
        confirmed: false,
      });
      return;
    }

    // Step 2: Load existing normalized for this date, or create minimal
    let normalized = await store.getNormalizedDay(athleteId, day.date);
    if (normalized) {
      // Merge nutrition into existing normalized record
      normalized = applyNutritionToNormalized(normalized, rawNutrition);
      await store.saveNormalizedDay(athleteId, normalized);
    } else {
      // No WHOOP data for this date — create nutrition-only normalized
      const now = new Date().toISOString();
      const nutritionOnly: NormalizedDailyMetrics = {
        id: `norm_nutr_${day.date}_${Date.now()}`,
        schemaVersion: 1,
        createdAt: now,
        updatedAt: now,
        derivationVersion: 'nutrition_only_v1',
        athleteId,
        date: day.date,
        recoveryScore: null,
        hrvMs: null,
        restingHrBpm: null,
        spo2Pct: null,
        skinTempCelsius: null,
        respiratoryRate: null,
        totalSleepHours: null,
        deepSleepHours: null,
        remSleepHours: null,
        lightSleepHours: null,
        awakeHours: null,
        sleepEfficiencyPct: null,
        sleepDebtHours: null,
        dailyStrain: null,
        activeCaloriesKcal: null,
        totalCaloriesKj: null,
        workoutCount: 0,
        workoutMinutesTotal: null,
        workoutStrainTotal: null,
        grapplingSessionCount: 0,
        workoutSportNames: [],
        nutritionCalories: rawNutrition.caloriesKcal,
        nutritionProteinGrams: rawNutrition.proteinGrams,
        nutritionCarbGrams: rawNutrition.carbGrams,
        nutritionFatGrams: rawNutrition.fatGrams,
        nutritionCoverage: computeNutritionCoverage(rawNutrition),
        presentFields: buildNutritionPresentFields(rawNutrition),
        missingFields: [],
        completeness: 'minimal',
        sourceAgeHours: null,
        sourceRecordIds: [rawNutrition.id],
        sourceRefs: [{ layer: 'raw', recordId: rawNutrition.id, fieldPath: null, date: day.date }],
        provider: rawNutrition.source,
      };
      await store.saveNormalizedDay(athleteId, nutritionOnly);
      normalized = nutritionOnly;
    }

    const nowNutr = new Date().toISOString();
    const nutritionSource: SourceName =
      rawNutrition.source === 'cronometer' ? 'cronometer' : 'manual';
    void recordSourceConnectionState({
      userId: athleteId,
      source: nutritionSource,
      status: 'connected',
      lastIngestedAt: nowNutr,
      lastSuccessAt: nowNutr,
      metadata: {
        lastDate: day.date,
        coverage: normalized.nutritionCoverage,
        provider: rawNutrition.source,
      },
    });

    res.status(200).json({
      ok: true,
      athleteId,
      date: day.date,
      confirmed: true,
      sourceState: rawNutrition.sourceState ?? 'manual',
      source: rawNutrition.source,
      nutritionCalories: normalized.nutritionCalories,
      nutritionProteinGrams: normalized.nutritionProteinGrams,
      nutritionCarbGrams: normalized.nutritionCarbGrams,
      nutritionFatGrams: normalized.nutritionFatGrams,
      nutritionCoverage: normalized.nutritionCoverage,
    });
  } catch (error) {
    const { athleteId: aId } = (req.body ?? {}) as { athleteId?: string };
    if (aId) {
      void recordSourceConnectionState({
        userId: aId,
        source: 'manual',
        status: 'error',
        lastFailureAt: new Date().toISOString(),
        lastFailureReason: error instanceof Error ? error.message.slice(0, 200) : 'nutrition_ingest_failed',
      });
    }
    res.status(500).json({
      error: 'Nutrition ingest failed.',
      detail: error instanceof Error ? error.message : 'unknown',
    });
  }
});

function computeNutritionCoverage(n: NutritionDailyMetricsRaw): 'full' | 'partial' | 'none' {
  const count = [n.caloriesKcal, n.proteinGrams, n.carbGrams, n.fatGrams].filter((v) => v != null).length;
  return count === 4 ? 'full' : count > 0 ? 'partial' : 'none';
}

function buildNutritionPresentFields(n: NutritionDailyMetricsRaw): string[] {
  const fields: string[] = [];
  if (n.caloriesKcal != null) fields.push('nutritionCalories');
  if (n.proteinGrams != null) fields.push('nutritionProteinGrams');
  if (n.carbGrams != null) fields.push('nutritionCarbGrams');
  if (n.fatGrams != null) fields.push('nutritionFatGrams');
  return fields;
}

// ── 14. Generic health source ingest (Apple Health, HC, manual) ──
// POST /v1/internal/ingest/health-source/daily
// Body: { athleteId, day: HealthSourceIngestPayload }
// Ingests, normalizes, merges with existing normalized record if present.
// Updates source health for the provider.

router.post('/ingest/health-source/daily', async (req: any, res: any) => {
  try {
    const { athleteId, day } = req.body as { athleteId: string; day: HealthSourceIngestPayload };
    if (!athleteId || !day?.date || !day?.provider) {
      res.status(400).json({ error: 'athleteId, day.date, and day.provider required.' });
      return;
    }

    const raw = ingestHealthSourceDay(day, athleteId);
    const normalized = normalizeHealthSourceDay(raw);

    // Merge with existing normalized (e.g. WHOOP data) if present
    const existing = await store.getNormalizedDay(athleteId, day.date);
    if (existing) {
      // Prefer non-null fields from the new source, keep existing for already-populated fields
      const merged: NormalizedDailyMetrics = {
        ...existing,
        recoveryScore: existing.recoveryScore ?? normalized.recoveryScore,
        hrvMs: existing.hrvMs ?? normalized.hrvMs,
        restingHrBpm: existing.restingHrBpm ?? normalized.restingHrBpm,
        totalSleepHours: existing.totalSleepHours ?? normalized.totalSleepHours,
        deepSleepHours: existing.deepSleepHours ?? normalized.deepSleepHours,
        remSleepHours: existing.remSleepHours ?? normalized.remSleepHours,
        activeCaloriesKcal: existing.activeCaloriesKcal ?? normalized.activeCaloriesKcal,
        dailyStrain: existing.dailyStrain ?? normalized.dailyStrain,
        workoutCount: Math.max(existing.workoutCount, normalized.workoutCount),
        grapplingSessionCount: Math.max(existing.grapplingSessionCount, normalized.grapplingSessionCount),
        updatedAt: new Date().toISOString(),
        sourceRecordIds: [...new Set([...existing.sourceRecordIds, ...normalized.sourceRecordIds])],
        sourceRefs: [...existing.sourceRefs, ...normalized.sourceRefs],
        provider: existing.provider === normalized.provider ? existing.provider : 'mixed' as any,
      };
      // Recompute completeness
      const present = Object.entries({
        recoveryScore: merged.recoveryScore, hrvMs: merged.hrvMs, restingHrBpm: merged.restingHrBpm,
        totalSleepHours: merged.totalSleepHours, deepSleepHours: merged.deepSleepHours,
        remSleepHours: merged.remSleepHours, activeCaloriesKcal: merged.activeCaloriesKcal,
        dailyStrain: merged.dailyStrain,
      }).filter(([, v]) => v != null).map(([k]) => k);
      merged.presentFields = present;
      merged.missingFields = ['recoveryScore','hrvMs','restingHrBpm','totalSleepHours','deepSleepHours','remSleepHours','activeCaloriesKcal','dailyStrain'].filter(f => !present.includes(f));
      merged.completeness = merged.missingFields.length === 0 ? 'complete' : present.length >= 4 ? 'partial' : 'minimal';
      await store.saveNormalizedDay(athleteId, merged);
    } else {
      await store.saveNormalizedDay(athleteId, normalized);
    }

    // Update source health for this provider. For polar_via_health_connect,
    // we trust the client-declared `domains_from_polar` list because only
    // the mobile side can see per-sample `dataOrigin`. For all other
    // providers, coverage is derived from non-null fields.
    const now = new Date().toISOString();
    const domains: Record<string, { lastDate: string | null; status: 'fresh' | 'stale' | 'expired' | 'missing' }> = {};
    const polarDomains = raw.provider === 'polar_via_health_connect' ? (raw.domainsFromPolar ?? []) : [];
    const markDomain = (name: string) => { domains[name] = { lastDate: raw.date, status: 'fresh' }; };

    if (raw.recoveryScore != null) markDomain('recovery');
    if (raw.totalSleepHours != null || polarDomains.includes('sleep')) markDomain('sleep');
    if (raw.dailyStrain != null) markDomain('strain');
    if (raw.hrvMs != null || polarDomains.includes('hrv')) markDomain('hrv');
    if (raw.restingHrBpm != null || polarDomains.includes('resting_hr')) markDomain('resting_hr');
    if (raw.workoutCount > 0 || polarDomains.includes('workouts')) markDomain('workouts');
    if (polarDomains.includes('workout_hr')) markDomain('workout_hr');
    if (polarDomains.includes('heart_rate_samples')) markDomain('heart_rate_samples');
    if (raw.stepCount != null && raw.stepCount > 0 || polarDomains.includes('steps')) markDomain('steps');
    if (raw.activeCaloriesKcal != null || polarDomains.includes('active_calories')) markDomain('active_calories');

    // Pack sourceApp into degradedReason as a provenance carrier. The
    // multi-source builder reads it for polar_via_health_connect only.
    const degradedReason = raw.provider === 'polar_via_health_connect' && raw.sourceApp
      ? `sourceApp:${raw.sourceApp}`
      : null;

    await store.saveSourceHealth(athleteId, raw.provider, {
      id: `source_health_${raw.provider}_${athleteId}`,
      schemaVersion: 1,
      createdAt: now,
      updatedAt: now,
      athleteId,
      provider: raw.provider,
      lastSuccessfulIngestAt: now,
      lastFailedIngestAt: null,
      freshnessStatus: Object.keys(domains).length > 0 ? 'fresh' : 'missing',
      coverageByDomain: domains,
      upstreamStatus: 'healthy',
      degradedReason,
    });

    // Map ingest provider → schema-allowed scs source slot.
    // For polar_via_health_connect we mirror BOTH `health_connect` (the
    // bridge) and `polar` (the underlying evidence source) so Coach
    // attribution can see Polar presence even when bridged through HC.
    const providerToSource: Record<string, SourceName> = {
      apple_health: 'apple_health',
      health_connect: 'health_connect',
      polar_via_health_connect: 'health_connect',
      samsung_health_via_health_connect: 'health_connect',
      samsung_health_direct: 'samsung',
      direct_polar: 'polar',
      polar: 'polar',
      manual: 'manual',
      cronometer: 'cronometer',
    };
    const primarySource = providerToSource[raw.provider];
    if (primarySource) {
      void recordSourceConnectionState({
        userId: athleteId,
        source: primarySource,
        status: Object.keys(domains).length > 0 ? 'connected' : 'partial',
        lastIngestedAt: now,
        lastSuccessAt: now,
        metadata: {
          lastDate: raw.date,
          provider: raw.provider,
          domains: Object.keys(domains),
          ...(raw.sourceApp ? { sourceApp: raw.sourceApp } : {}),
        },
      });
    }
    if (raw.provider === 'polar_via_health_connect') {
      void recordSourceConnectionState({
        userId: athleteId,
        source: 'polar',
        status: 'connected',
        lastIngestedAt: now,
        lastSuccessAt: now,
        metadata: {
          lastDate: raw.date,
          via: 'health_connect',
          domains: polarDomains,
          ...(raw.sourceApp ? { sourceApp: raw.sourceApp } : {}),
        },
      });
    }
    if (raw.provider === 'samsung_health_via_health_connect') {
      void recordSourceConnectionState({
        userId: athleteId,
        source: 'samsung',
        status: 'connected',
        lastIngestedAt: now,
        lastSuccessAt: now,
        metadata: { lastDate: raw.date, via: 'health_connect' },
      });
    }

    res.status(200).json({
      ok: true, athleteId, date: day.date, provider: raw.provider,
      domainsIngested: Object.keys(domains),
      merged: existing != null,
    });
  } catch (error) {
    const { athleteId: aId } = (req.body ?? {}) as { athleteId?: string };
    if (aId) {
      void recordSourceConnectionState({
        userId: aId,
        source: 'health_connect',
        status: 'error',
        lastFailureAt: new Date().toISOString(),
        lastFailureReason: error instanceof Error ? error.message.slice(0, 200) : 'health_source_ingest_failed',
      });
    }
    res.status(500).json({ error: 'Health source ingest failed.', detail: error instanceof Error ? error.message : 'unknown' });
  }
});

// ── 15. Multi-source health summary ──────────────────────────
// GET /v1/internal/athletes/:athleteId/source-health/all
// Returns one machine-readable status per known provider.

router.get('/athletes/:athleteId/source-health/all', async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const PROVIDERS = ['whoop', 'whoop_direct', 'apple_health', 'health_connect', 'polar_via_health_connect', 'samsung_health_via_health_connect', 'samsung_health_direct', 'direct_polar', 'cronometer', 'manual', 'polar', 'concept2_logbook', 'garmin'];
    const records: Record<string, any> = {};
    for (const p of PROVIDERS) {
      records[p] = await store.getSourceHealth(athleteId, p);
    }
    const summary = buildMultiSourceHealth(athleteId, records);
    res.status(200).json(summary);
  } catch (error) {
    res.status(500).json({ error: 'Multi-source health failed.', detail: error instanceof Error ? error.message : 'unknown' });
  }
});

// ── 16. AI meal photo proposal + confirmation ────────────────
// POST /v1/internal/nutrition/photo-proposal
// Stores a photo proposal. Status: proposed. Does NOT enter normalized.
// Body: { athleteId, proposal: AiPhotoProposal }

router.post('/nutrition/photo-proposal', async (req: any, res: any) => {
  try {
    const { athleteId, proposal } = req.body as {
      athleteId: string;
      proposal: { proposalId: string; photoRef: string; description: string;
        proposedCalories: number | null; proposedProteinG: number | null;
        proposedCarbG: number | null; proposedFatG: number | null;
        confidence: string; missingFields: string[]; };
    };
    if (!athleteId || !proposal?.proposalId) {
      res.status(400).json({ error: 'athleteId and proposal.proposalId required.' });
      return;
    }

    const record = {
      ...proposal,
      status: 'proposed' as const,
      athleteId,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      enteredNormalized: false,
    };

    await store.saveNutritionEvidence(athleteId, record);

    res.status(200).json({
      ok: true,
      athleteId,
      proposalId: proposal.proposalId,
      status: 'proposed',
      enteredNormalized: false,
      reason: 'Photo proposal stored. User must confirm or edit before it enters nutrition totals.',
    });
  } catch (error) {
    res.status(500).json({ error: 'Photo proposal failed.', detail: error instanceof Error ? error.message : 'unknown' });
  }
});

// POST /v1/internal/nutrition/photo-confirm
// Confirms or edits a photo proposal. Confirmed/edited enters normalized.
// Body: { athleteId, proposalId, action: 'user_confirmed'|'user_edited'|'rejected',
//         finalCalories?, finalProteinG?, finalCarbG?, finalFatG? }

router.post('/nutrition/photo-confirm', async (req: any, res: any) => {
  try {
    const { athleteId, proposalId, action, finalCalories, finalProteinG, finalCarbG, finalFatG } = req.body as {
      athleteId: string; proposalId: string;
      action: 'user_confirmed' | 'user_edited' | 'rejected';
      finalCalories?: number | null; finalProteinG?: number | null;
      finalCarbG?: number | null; finalFatG?: number | null;
    };
    if (!athleteId || !proposalId || !action) {
      res.status(400).json({ error: 'athleteId, proposalId, and action required.' });
      return;
    }

    // Load existing proposal
    const existing = await store.getNutritionEvidence(athleteId, proposalId);
    if (!existing) {
      res.status(404).json({ error: 'Proposal not found.' });
      return;
    }

    // Update status
    const updated = {
      ...existing,
      status: action,
      updatedAt: new Date().toISOString(),
      ...(action !== 'rejected' ? {
        finalCalories: finalCalories ?? (existing as any).proposedCalories,
        finalProteinG: finalProteinG ?? (existing as any).proposedProteinG,
        finalCarbG: finalCarbG ?? (existing as any).proposedCarbG,
        finalFatG: finalFatG ?? (existing as any).proposedFatG,
      } : {}),
      enteredNormalized: action !== 'rejected',
    };
    await store.saveNutritionEvidence(athleteId, updated);

    // If confirmed/edited, ingest into normalized nutrition
    if (action === 'user_confirmed' || action === 'user_edited') {
      const sourceState = action === 'user_edited' ? 'mixed' : 'estimated';
      const date = (existing as any).date ?? new Date().toISOString().slice(0, 10);
      const rawNutrition = ingestNutritionDay({
        date,
        source: 'ai_photo',
        sourceState,
        confirmed: true,
        calories_kcal: updated.finalCalories as any,
        protein_g: updated.finalProteinG as any,
        carbs_g: updated.finalCarbG as any,
        fat_g: updated.finalFatG as any,
      }, athleteId);

      // Save raw
      await store.saveRawNutrition(athleteId, rawNutrition as any);

      // Merge into normalized
      let normalized = await store.getNormalizedDay(athleteId, date);
      if (normalized) {
        normalized = applyNutritionToNormalized(normalized, rawNutrition);
        await store.saveNormalizedDay(athleteId, normalized);
      } else {
        const now = new Date().toISOString();
        const nutritionOnly: NormalizedDailyMetrics = {
          id: `norm_photo_${date}_${Date.now()}`,
          schemaVersion: 1, createdAt: now, updatedAt: now,
          derivationVersion: 'photo_confirmed_v1', athleteId, date,
          recoveryScore: null, hrvMs: null, restingHrBpm: null,
          spo2Pct: null, skinTempCelsius: null, respiratoryRate: null,
          totalSleepHours: null, deepSleepHours: null, remSleepHours: null,
          lightSleepHours: null, awakeHours: null, sleepEfficiencyPct: null,
          sleepDebtHours: null, dailyStrain: null, activeCaloriesKcal: null,
          totalCaloriesKj: null, workoutCount: 0, workoutMinutesTotal: null,
          workoutStrainTotal: null, grapplingSessionCount: 0, workoutSportNames: [],
          nutritionCalories: rawNutrition.caloriesKcal,
          nutritionProteinGrams: rawNutrition.proteinGrams,
          nutritionCarbGrams: rawNutrition.carbGrams,
          nutritionFatGrams: rawNutrition.fatGrams,
          nutritionCoverage: computeNutritionCoverage(rawNutrition),
          presentFields: buildNutritionPresentFields(rawNutrition),
          missingFields: [], completeness: 'minimal', sourceAgeHours: null,
          sourceRecordIds: [rawNutrition.id],
          sourceRefs: [{ layer: 'raw', recordId: rawNutrition.id, fieldPath: null, date }],
          provider: 'ai_photo',
        };
        await store.saveNormalizedDay(athleteId, nutritionOnly);
      }
    }

    res.status(200).json({
      ok: true,
      athleteId,
      proposalId,
      status: action,
      enteredNormalized: action !== 'rejected',
    });
  } catch (error) {
    res.status(500).json({ error: 'Photo confirmation failed.', detail: error instanceof Error ? error.message : 'unknown' });
  }
});

// ── 17. Cronometer connection check + sync ────────────────────
// GET /v1/internal/cronometer/:athleteId/status
// Returns current Cronometer connection status.

const cronometerAdapter = new DefaultCronometerAdapter();

router.get('/cronometer/:athleteId/status', async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const connState = await cronometerAdapter.checkConnection();

    // Also return the stored source-health record if one exists
    const sourceHealth = await store.getSourceHealth(athleteId, 'cronometer');

    res.status(200).json({
      ok: true,
      athleteId,
      connection: connState,
      sourceHealth: sourceHealth ?? { status: 'not_connected', reason: 'No Cronometer source-health record.' },
    });
  } catch (error) {
    res.status(500).json({ error: 'Cronometer status check failed.', detail: error instanceof Error ? error.message : 'unknown' });
  }
});

// POST /v1/internal/cronometer/:athleteId/sync
// Attempts to sync today's (or specified date's) Cronometer nutrition.
// If not connected, returns truthful blocked status.
// If connected, fetches, normalizes, writes source-health + normalized.

router.post('/cronometer/:athleteId/sync', async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const { date } = req.body as { date?: string };
    const targetDate = date ?? new Date().toISOString().slice(0, 10);

    // Check connection first
    const connState = await cronometerAdapter.checkConnection();
    if (connState.status !== 'connected') {
      // Write honest source-health record
      const now = new Date().toISOString();
      await store.saveSourceHealth(athleteId, 'cronometer', {
        id: `source_health_cronometer_${athleteId}`,
        schemaVersion: 1,
        createdAt: now,
        updatedAt: now,
        athleteId,
        provider: 'cronometer',
        lastSuccessfulIngestAt: null,
        lastFailedIngestAt: now,
        freshnessStatus: 'missing',
        coverageByDomain: {},
        upstreamStatus: connState.status === 'unavailable' ? 'down' : 'unknown',
        degradedReason: `${connState.status}: ${connState.reason ?? 'No details.'}`,
      } as any);

      res.status(200).json({
        ok: false,
        athleteId,
        date: targetDate,
        status: connState.status,
        reason: connState.reason,
        actionRequired: connState.actionRequired,
        hasCredentials: connState.hasCredentials,
      });
      return;
    }

    // Attempt fetch
    const rawData = await cronometerAdapter.fetchDaily(targetDate);
    if (!rawData) {
      res.status(200).json({
        ok: false,
        athleteId,
        date: targetDate,
        status: 'unavailable',
        reason: 'Cronometer returned no data for this date.',
      });
      return;
    }

    // Normalize and ingest
    const normalized = normalizeCronometerDaily(rawData);
    const rawNutrition = ingestNutritionDay(normalized, athleteId);

    // Save raw
    await store.saveRawNutrition(athleteId, rawNutrition as any);

    // Merge into normalized day
    let normalizedDay = await store.getNormalizedDay(athleteId, targetDate);
    if (normalizedDay) {
      normalizedDay = applyNutritionToNormalized(normalizedDay, rawNutrition);
      // If day already has manual/barcode data, mark as mixed
      if (normalizedDay.provider !== 'cronometer') {
        (normalizedDay as any).provider = 'mixed';
      }
      await store.saveNormalizedDay(athleteId, normalizedDay);
    } else {
      const now = new Date().toISOString();
      const nutritionOnly: NormalizedDailyMetrics = {
        id: `norm_cron_${targetDate}_${Date.now()}`,
        schemaVersion: 1, createdAt: now, updatedAt: now,
        derivationVersion: 'cronometer_v1', athleteId, date: targetDate,
        recoveryScore: null, hrvMs: null, restingHrBpm: null,
        spo2Pct: null, skinTempCelsius: null, respiratoryRate: null,
        totalSleepHours: null, deepSleepHours: null, remSleepHours: null,
        lightSleepHours: null, awakeHours: null, sleepEfficiencyPct: null,
        sleepDebtHours: null, dailyStrain: null, activeCaloriesKcal: null,
        totalCaloriesKj: null, workoutCount: 0, workoutMinutesTotal: null,
        workoutStrainTotal: null, grapplingSessionCount: 0, workoutSportNames: [],
        nutritionCalories: rawNutrition.caloriesKcal,
        nutritionProteinGrams: rawNutrition.proteinGrams,
        nutritionCarbGrams: rawNutrition.carbGrams,
        nutritionFatGrams: rawNutrition.fatGrams,
        nutritionCoverage: computeNutritionCoverage(rawNutrition),
        presentFields: buildNutritionPresentFields(rawNutrition),
        missingFields: [], completeness: 'minimal', sourceAgeHours: null,
        sourceRecordIds: [rawNutrition.id],
        sourceRefs: [{ layer: 'raw', recordId: rawNutrition.id, fieldPath: null, date: targetDate }],
        provider: 'cronometer',
      };
      await store.saveNormalizedDay(athleteId, nutritionOnly);
    }

    // Write fresh source-health record
    const now = new Date().toISOString();
    const coverage = buildCronometerCoverage(rawData);
    const coverageByDomain: Record<string, { lastDate: string | null; status: 'fresh' | 'stale' | 'expired' | 'missing' }> = {};
    for (const c of coverage) {
      coverageByDomain[c.domain] = { lastDate: c.available ? targetDate : null, status: c.available ? 'fresh' : 'missing' };
    }
    await store.saveSourceHealth(athleteId, 'cronometer', {
      id: `source_health_cronometer_${athleteId}`,
      schemaVersion: 1,
      createdAt: now,
      updatedAt: now,
      athleteId,
      provider: 'cronometer',
      lastSuccessfulIngestAt: now,
      lastFailedIngestAt: null,
      freshnessStatus: 'fresh',
      coverageByDomain,
      upstreamStatus: 'healthy',
      degradedReason: null,
    } as any);

    res.status(200).json({
      ok: true,
      athleteId,
      date: targetDate,
      status: 'connected',
      coverage: coverage.filter((c) => c.available).map((c) => c.domain),
      missingFields: rawData.missingFields,
      nutritionCalories: rawNutrition.caloriesKcal,
      nutritionProteinGrams: rawNutrition.proteinGrams,
    });
  } catch (error) {
    res.status(500).json({ error: 'Cronometer sync failed.', detail: error instanceof Error ? error.message : 'unknown' });
  }
});

// ── 18. Session log ingest (HIIT workouts) ───────────────────
// POST /v1/internal/ingest/session-log
// Body: { athleteId: string, session: SessionLogIngestPayload }
// Ingests raw session + produces normalized summary.
// Supports manual HIIT now, machine-sync later.

router.post('/ingest/session-log', async (req: any, res: any) => {
  try {
    const { athleteId, session } = req.body as {
      athleteId: string;
      session: SessionLogIngestPayload;
    };
    if (!athleteId || !session?.sessionId || !session?.date) {
      res.status(400).json({ error: 'athleteId, session.sessionId, and session.date required.' });
      return;
    }

    // Ensure athleteId is consistent
    const payload: SessionLogIngestPayload = { ...session, athleteId };
    const { raw, normalized } = ingestAndNormalizeSessionLog(payload);

    // Store raw session in dedicated session_raw/ directory
    await store.saveRawSession(athleteId, raw as any);

    // Store normalized summary via dedicated session index
    await store.saveSessionSummary(athleteId, normalized as any);

    const nowSess = new Date().toISOString();
    void recordSourceConnectionState({
      userId: athleteId,
      source: 'hiit',
      status: 'connected',
      lastIngestedAt: nowSess,
      lastSuccessAt: nowSess,
      metadata: {
        lastDate: session.date,
        sessionId: session.sessionId,
        templateId: session.templateId ?? null,
        machineConnected: normalized.machineConnected,
        machineType: session.machineType,
        machineProvider: session.machineProvider,
      },
    });

    res.status(200).json({
      ok: true,
      athleteId,
      date: session.date,
      sessionId: session.sessionId,
      templateId: session.templateId,
      normalized: {
        totalSets: normalized.totalSets,
        workSets: normalized.workSets,
        avgWatts: normalized.avgWatts,
        avgHr: normalized.avgHr,
        wattsDropOffPct: normalized.wattsDropOffPct,
        hrDriftPct: normalized.hrDriftPct,
        avgHrRecoveryBpm: normalized.avgHrRecoveryBpm,
        machineConnected: normalized.machineConnected,
        missingFields: normalized.missingFields,
      },
    });
  } catch (error) {
    const { athleteId: aId } = (req.body ?? {}) as { athleteId?: string };
    if (aId) {
      void recordSourceConnectionState({
        userId: aId,
        source: 'hiit',
        status: 'error',
        lastFailureAt: new Date().toISOString(),
        lastFailureReason: error instanceof Error ? error.message.slice(0, 200) : 'session_log_ingest_failed',
      });
    }
    res.status(500).json({
      error: 'Session log ingest failed.',
      detail: error instanceof Error ? error.message : 'unknown',
    });
  }
});

export default router;
