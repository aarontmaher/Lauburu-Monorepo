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
import { computeLauburuReadiness } from '../../../../packages/shared/src/backend/services/readiness/lauburu-readiness';
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
import { mirrorNormalizedDay } from '../lib/normalizedMetricsSink';
import { mirrorRawSourceEvent } from '../lib/rawSourceEventsSink';

const router = Router();

const store = new FileApiAiStateStore(
  path.resolve(__dirname, '../../../data/private-athlete-memory'),
);

/**
 * Save normalized day to Railway primary AND fire-and-forget mirror
 * the same row to Supabase `normalized_daily_metrics`. Railway primary
 * is the source of truth; the mirror is redundant cross-stack
 * visibility (web/exports/future read paths). Mirror failures are
 * never propagated — primary writes are unaffected.
 *
 * Centralizing the call here means every existing
 * `store.saveNormalizedDay(...)` call site becomes a single line via
 * search-replace, with no behavior change beyond the added mirror.
 */
async function saveAndMirrorNormalized(athleteId: string, record: NormalizedDailyMetrics): Promise<void> {
  // Primary: Railway file storage (source of truth).
  await store.saveNormalizedDay(athleteId, record);
  // Mirror: Supabase normalized_daily_metrics (redundancy, fire-and-forget).
  void mirrorNormalizedDay(athleteId, record);
}

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
      // Mirror raw evidence to Supabase raw_source_events.
      // Idempotent on (user_id, source, source_record_id,
      // source_record_type) — re-ingesting same cycle updates the
      // payload_hash + ingested_at, no duplicate row.
      void mirrorRawSourceEvent({
        userId: athleteId,
        source: 'whoop',
        sourceRecordId: String((record as any).cycleId ?? record.localDate),
        sourceRecordType: 'whoop_daily',
        localDate: record.localDate,
        startedAt: (record as any).cycleStart ?? null,
        endedAt: (record as any).cycleEnd ?? null,
        payload: record,
        provenance: { ingest_route: '/ingest/whoop/daily' },
      });
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
      await saveAndMirrorNormalized(athleteId, record);
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
      await saveAndMirrorNormalized(athleteId,record);
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

// ── Trends — windowed rolling stats over normalized daily metrics ──
// GET /v1/internal/athletes/:athleteId/trends?windowDays=N
//
// Returns per-metric rolling stats over the most recent N days for
// HRV, RHR, sleep hours, day strain, sleep debt. Pure compute over
// `store.getNormalizedRecent`. Per-user only (athleteId in path; the
// internal-token middleware gates access). Includes coverage % +
// confidence + trend direction so a UI can surface "improving /
// worsening / flat / insufficient data" without server-side state.
// ── AI health-context bundle ──
// GET /v1/internal/athletes/:athleteId/ai-health-context
//
// Aggregates the structured pieces an AI/Coach surface needs:
//   - sources_connected[] (with last_sync_at + status)
//   - last_sync_at (most recent across sources)
//   - data_coverage (counts + window dates)
//   - readiness (score + status + confidence + training_bias + factors)
//   - trends_short (7d) + trends_medium (30d) + trends_long (90d)
//   - missing_data caveats (composed from readiness + trends)
//   - recent_session_count (last 30 d)
//
// Pure read — no writes. Per-user only (athleteId path scoped).
// Stamps `not_medical_advice: true` + `experimental: true` so any
// downstream consumer sees the safety contract.
// ── Auto-sync plan ──
// GET /v1/internal/athletes/:athleteId/auto-sync/plan
//
// Read-only orchestrator: tells mobile/app-open which sources are
// eligible for foreground sync, which are in cooldown, which need
// permission/reconnect, and which are client-driven (Apple Health /
// HC) vs server-driven (WHOOP Direct OAuth).
//
// Cooldown: 6h since last successful ingest. Manual Sync Now buttons
// in the app should bypass cooldown (the mobile UI controls that —
// this endpoint never executes a sync, only plans it). Failed syncs
// use a shorter 30-min retry cooldown so a transient network error
// doesn't lock out a tester for 6h.
//
// Per-user only. Auth-gated by the existing internal-token middleware.
// No writes from this endpoint — pure read of source_connection_state
// + source_health files.
router.get('/athletes/:athleteId/auto-sync/plan', async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const COOLDOWN_OK_MS = 6 * 60 * 60 * 1000;        // 6h after success
    const COOLDOWN_FAIL_MS = 30 * 60 * 1000;          // 30m after failure
    const now = Date.now();

    // Source kinds: client-driven means the mobile reads native data
    // and POSTs to /ingest/health-source/daily; server-driven means
    // chat-app pulls via OAuth (WHOOP Direct).
    const KNOWN_SOURCES: Array<{ name: string; kind: 'client_driven' | 'server_driven' | 'manual_only' }> = [
      { name: 'apple_health',                       kind: 'client_driven' },
      { name: 'health_connect',                     kind: 'client_driven' },
      { name: 'samsung_health_via_health_connect',  kind: 'client_driven' },
      { name: 'polar_via_health_connect',           kind: 'client_driven' },
      { name: 'whoop',                              kind: 'server_driven' },
      { name: 'polar',                              kind: 'server_driven' },
      { name: 'whoop_csv',                          kind: 'manual_only' },
      { name: 'cronometer',                         kind: 'server_driven' },
    ];

    const plan: Array<{
      source: string;
      kind: 'client_driven' | 'server_driven' | 'manual_only';
      action: 'sync_now' | 'cooldown' | 'permission_needed' | 'reconnect_needed' | 'not_connected' | 'manual_only_user_action' | 'unavailable';
      reason: string;
      last_success_at: string | null;
      last_failure_at: string | null;
      next_eligible_auto_sync_at: string | null;
      cooldown_remaining_seconds: number | null;
    }> = [];

    for (const { name, kind } of KNOWN_SOURCES) {
      const sh: any = await store.getSourceHealth(athleteId, name).catch(() => null);
      const lastOk = sh?.lastSuccessfulIngestAt ? new Date(sh.lastSuccessfulIngestAt).getTime() : null;
      const lastFail = sh?.lastFailedIngestAt ? new Date(sh.lastFailedIngestAt).getTime() : null;
      const upstream = sh?.upstreamStatus ?? null;
      const degraded = sh?.degradedReason ?? null;

      // Manual-only sources never auto-sync — surface honest state.
      if (kind === 'manual_only') {
        plan.push({
          source: name,
          kind,
          action: 'manual_only_user_action',
          reason: name === 'whoop_csv'
            ? 'WHOOP CSV/zip imports require user file paste/upload — auto-sync cannot pull new files.'
            : 'Manual entry only.',
          last_success_at: sh?.lastSuccessfulIngestAt ?? null,
          last_failure_at: sh?.lastFailedIngestAt ?? null,
          next_eligible_auto_sync_at: null,
          cooldown_remaining_seconds: null,
        });
        continue;
      }

      // No prior connection at all → not_connected.
      if (!sh || (!lastOk && !lastFail)) {
        plan.push({
          source: name,
          kind,
          action: 'not_connected',
          reason: kind === 'client_driven'
            ? `${name} not connected on this device yet — open the Health tab to connect.`
            : `${name} OAuth not connected — visit the Connect screen to authorise.`,
          last_success_at: null,
          last_failure_at: null,
          next_eligible_auto_sync_at: null,
          cooldown_remaining_seconds: null,
        });
        continue;
      }

      // Token/permission failure shape (heuristic on degradedReason).
      if (degraded && /unauthor|token|expired|reconnect/i.test(String(degraded))) {
        plan.push({
          source: name,
          kind,
          action: 'reconnect_needed',
          reason: `Reconnect required: ${String(degraded).slice(0, 120)}`,
          last_success_at: sh?.lastSuccessfulIngestAt ?? null,
          last_failure_at: sh?.lastFailedIngestAt ?? null,
          next_eligible_auto_sync_at: null,
          cooldown_remaining_seconds: null,
        });
        continue;
      }
      if (degraded && /permission/i.test(String(degraded))) {
        plan.push({
          source: name,
          kind,
          action: 'permission_needed',
          reason: `Permission missing: ${String(degraded).slice(0, 120)}`,
          last_success_at: sh?.lastSuccessfulIngestAt ?? null,
          last_failure_at: sh?.lastFailedIngestAt ?? null,
          next_eligible_auto_sync_at: null,
          cooldown_remaining_seconds: null,
        });
        continue;
      }

      // Cooldown calculation.
      const sinceOk = lastOk != null ? now - lastOk : Infinity;
      const sinceFail = lastFail != null ? now - lastFail : Infinity;
      const okCooldownLeft = Math.max(0, COOLDOWN_OK_MS - sinceOk);
      const failCooldownLeft = Math.max(0, COOLDOWN_FAIL_MS - sinceFail);
      const cooldownRemaining = Math.max(okCooldownLeft, failCooldownLeft);

      if (cooldownRemaining > 0) {
        plan.push({
          source: name,
          kind,
          action: 'cooldown',
          reason: failCooldownLeft > okCooldownLeft
            ? `In failure-retry cooldown (${Math.round(failCooldownLeft / 1000)}s remaining).`
            : `Recently synced; next auto-sync allowed in ${Math.round(cooldownRemaining / 1000)}s. Manual Sync Now bypasses.`,
          last_success_at: sh?.lastSuccessfulIngestAt ?? null,
          last_failure_at: sh?.lastFailedIngestAt ?? null,
          next_eligible_auto_sync_at: new Date(now + cooldownRemaining).toISOString(),
          cooldown_remaining_seconds: Math.round(cooldownRemaining / 1000),
        });
        continue;
      }

      // Eligible for auto-sync.
      plan.push({
        source: name,
        kind,
        action: 'sync_now',
        reason: kind === 'client_driven'
          ? `Eligible for client-driven foreground sync. Mobile should call its native ${name} reader and POST to /v1/internal/ingest/health-source/daily.`
          : `Eligible for server-driven OAuth sync. Backend would trigger ${name}'s pull route.`,
        last_success_at: sh?.lastSuccessfulIngestAt ?? null,
        last_failure_at: sh?.lastFailedIngestAt ?? null,
        next_eligible_auto_sync_at: new Date(now + COOLDOWN_OK_MS).toISOString(),
        cooldown_remaining_seconds: 0,
      });
    }

    // Aggregate health flags so a UI can render at-a-glance.
    const eligibleCount = plan.filter((p) => p.action === 'sync_now').length;
    const cooldownCount = plan.filter((p) => p.action === 'cooldown').length;
    const reconnectCount = plan.filter((p) => p.action === 'reconnect_needed').length;
    const permCount = plan.filter((p) => p.action === 'permission_needed').length;
    const notConnectedCount = plan.filter((p) => p.action === 'not_connected').length;
    const lastAnyOk = plan.map((p) => p.last_success_at).filter((v): v is string => !!v).sort().pop() ?? null;

    res.status(200).json({
      athleteId,
      computed_at: new Date().toISOString(),
      cooldown_policy: {
        success_cooldown_hours: 6,
        failure_retry_cooldown_minutes: 30,
        manual_sync_bypasses_cooldown: true,
      },
      summary: {
        eligible_for_auto_sync: eligibleCount,
        in_cooldown: cooldownCount,
        reconnect_required: reconnectCount,
        permission_required: permCount,
        not_connected: notConnectedCount,
        most_recent_sync_at: lastAnyOk,
      },
      plan,
      not_medical_advice: true,
      experimental: true,
    });
  } catch (error) {
    res.status(500).json({
      error: 'Auto-sync plan compute failed.',
      detail: error instanceof Error ? error.message : 'unknown',
    });
  }
});

router.get('/athletes/:athleteId/ai-health-context', async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    // 90 days is the longest window we expose for an AI context bundle.
    // Anything older lives in athlete_memory / weekly artifacts.
    const last90 = await store.getNormalizedRecent(athleteId, 95);
    const sortedAsc = [...(last90 ?? [])].sort((a: any, b: any) => String(a.date).localeCompare(String(b.date)));
    const today = sortedAsc[sortedAsc.length - 1] ?? null;
    const baseline = today ? sortedAsc.filter((r: any) => r.date < (today as any).date) : sortedAsc;
    // Readiness — same compute as the dedicated endpoint.
    const last7 = sortedAsc.slice(-7);
    const acuteVals: number[] = [];
    for (const r of last7) {
      const v = (r as any).dailyStrain;
      if (typeof v === 'number' && Number.isFinite(v)) acuteVals.push(v);
    }
    const acuteLoad = acuteVals.length > 0
      ? { sum: acuteVals.reduce((s, v) => s + v, 0), avg: acuteVals.reduce((s, v) => s + v, 0) / acuteVals.length, days: acuteVals.length }
      : null;
    const last28 = baseline.slice(-28);
    const chronicVals: number[] = [];
    for (const r of last28) {
      const v = (r as any).dailyStrain;
      if (typeof v === 'number' && Number.isFinite(v)) chronicVals.push(v);
    }
    const chronicLoad = chronicVals.length > 0
      ? { avg: chronicVals.reduce((s, v) => s + v, 0) / chronicVals.length, days: chronicVals.length }
      : null;
    let staleHours: number | null = null;
    if ((today as any)?.updatedAt) {
      const ms = new Date((today as any).updatedAt).getTime();
      if (Number.isFinite(ms)) staleHours = Math.max(0, (Date.now() - ms) / (1000 * 60 * 60));
    }
    const readiness = computeLauburuReadiness({
      today: today as any,
      baseline: baseline as any,
      acuteLoad,
      chronicLoad,
      staleHours,
    });
    // Trend windows — reduced to compact summaries (direction +
    // confidence + coverage_pct only) so the AI prompt stays small.
    function trendSummary(records: any[], windowDays: number) {
      const out: Record<string, any> = {};
      const slice = records.slice(-windowDays);
      const map: Array<[string, (r: any) => number | null, boolean]> = [
        ['hrv_ms', (r) => r.hrvMs, true],
        ['rhr_bpm', (r) => r.restingHrBpm, false],
        ['sleep_hours', (r) => r.totalSleepHours, true],
        ['day_strain', (r) => r.dailyStrain, false],
        ['recovery_score', (r) => r.recoveryScore, true],
      ];
      for (const [name, pick, higherBetter] of map) {
        const vs: number[] = [];
        for (const r of slice) { const v = pick(r); if (typeof v === 'number' && Number.isFinite(v)) vs.push(v); }
        if (vs.length === 0) { out[name] = { coverage_days: 0, direction: 'insufficient', confidence: 'insufficient' }; continue; }
        const m = vs.reduce((s, v) => s + v, 0) / vs.length;
        const sd = Math.sqrt(vs.reduce((s, v) => s + (v - m) ** 2, 0) / vs.length);
        let direction: 'improving' | 'worsening' | 'flat' | 'insufficient' = 'insufficient';
        if (vs.length >= 7) {
          const third = Math.floor(vs.length / 3);
          const oldM = vs.slice(0, third).reduce((s, v) => s + v, 0) / third;
          const newM = vs.slice(-third).reduce((s, v) => s + v, 0) / third;
          const delta = newM - oldM;
          if (sd > 0 && Math.abs(delta) / sd > 0.5) {
            direction = (higherBetter ? delta > 0 : delta < 0) ? 'improving' : 'worsening';
          } else direction = 'flat';
        }
        const conf = vs.length >= 30 ? 'high' : vs.length >= 7 ? 'medium' : 'low';
        out[name] = {
          coverage_days: vs.length,
          coverage_pct: Math.round((vs.length / windowDays) * 100),
          direction,
          confidence: conf,
          mean: Number(m.toFixed(2)),
          latest: Number((vs[vs.length - 1]).toFixed(2)),
        };
      }
      return out;
    }
    // Sources connected — read source_health files for each known
    // provider, return a compact list with last_sync_at + status.
    const PROVIDERS = ['whoop', 'apple_health', 'health_connect', 'polar_via_health_connect',
      'samsung_health_via_health_connect', 'samsung_health_direct', 'direct_polar', 'cronometer', 'polar', 'concept2_logbook'];
    const sources: Array<{ provider: string; status: string; last_sync_at: string | null; coverage_domains: string[] }> = [];
    for (const p of PROVIDERS) {
      const sh: any = await store.getSourceHealth(athleteId, p);
      if (sh) {
        sources.push({
          provider: p,
          status: String(sh.freshnessStatus ?? sh.upstreamStatus ?? 'unknown'),
          last_sync_at: sh.lastSuccessfulIngestAt ?? null,
          coverage_domains: Object.keys(sh.coverageByDomain ?? {}).filter((k) => (sh.coverageByDomain[k]?.status === 'fresh' || sh.coverageByDomain[k]?.status === 'stale')),
        });
      }
    }
    const lastSyncAt = sources
      .map((s) => s.last_sync_at)
      .filter((v): v is string => !!v)
      .sort()
      .pop() ?? null;
    res.status(200).json({
      athleteId,
      computed_at: new Date().toISOString(),
      not_medical_advice: true,
      experimental: true,
      data_coverage: {
        total_normalized_days: sortedAsc.length,
        first_date: sortedAsc[0]?.date ?? null,
        last_date: today ? (today as any).date : null,
        baseline_days: baseline.length,
      },
      sources_connected: sources,
      last_sync_at: lastSyncAt,
      readiness,
      trends_short_7d: trendSummary(sortedAsc, 7),
      trends_medium_30d: trendSummary(sortedAsc, 30),
      trends_long_90d: trendSummary(sortedAsc, 90),
    });
  } catch (error) {
    res.status(500).json({
      error: 'AI health context compute failed.',
      detail: error instanceof Error ? error.message : 'unknown',
    });
  }
});

// ── Lauburu Readiness — custom grappling-aware readiness score ──
// GET /v1/internal/athletes/:athleteId/readiness?date=YYYY-MM-DD
//
// Pure compute over normalized metrics + acute/chronic load. Returns
// a 0-100 score, status, confidence, training-bias, top contributing
// factors, missing-data list, caveats, plain-English explanation.
// NOT MEDICAL ADVICE — `not_medical_advice: true` flag on every
// response. Conservative; surfaces low-confidence + insufficient_data
// states explicitly.
router.get('/athletes/:athleteId/readiness', async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const requestedDate = (req.query.date as string | undefined) ?? new Date().toISOString().slice(0, 10);
    // Pull last 35 days so we have today + 28-day baseline + a small
    // pad for missing days. The compute module trims itself.
    const window = await store.getNormalizedRecent(athleteId, 35);
    if (!Array.isArray(window) || window.length === 0) {
      const out = computeLauburuReadiness({ today: null, baseline: [] });
      res.status(200).json({ athleteId, date: requestedDate, ...out });
      return;
    }
    // Sort ascending so today is the last entry.
    const sorted = [...window].sort((a: any, b: any) => String(a.date).localeCompare(String(b.date)));
    // Find today (or the requested date) and split baseline = everything before it.
    const todayIdx = sorted.findIndex((r: any) => r.date === requestedDate);
    const today = todayIdx >= 0 ? (sorted[todayIdx] as any) : (sorted[sorted.length - 1] as any);
    const baseline = sorted.filter((r: any) => r.date !== today.date && r.date < today.date);
    // Acute load: last 7 days of strain ending today (inclusive).
    const acuteSlice = sorted.filter((r: any) => r.date <= today.date).slice(-7);
    const acuteVals: number[] = [];
    for (const r of acuteSlice) {
      const v = (r as any).dailyStrain;
      if (typeof v === 'number' && Number.isFinite(v)) acuteVals.push(v);
    }
    const acuteLoad = acuteVals.length > 0
      ? { sum: acuteVals.reduce((s, v) => s + v, 0), avg: acuteVals.reduce((s, v) => s + v, 0) / acuteVals.length, days: acuteVals.length }
      : null;
    // Chronic load: last 28 days of strain (incl baseline) excluding today.
    const chronicSlice = baseline.slice(-28);
    const chronicVals: number[] = [];
    for (const r of chronicSlice) {
      const v = (r as any).dailyStrain;
      if (typeof v === 'number' && Number.isFinite(v)) chronicVals.push(v);
    }
    const chronicLoad = chronicVals.length > 0
      ? { avg: chronicVals.reduce((s, v) => s + v, 0) / chronicVals.length, days: chronicVals.length }
      : null;
    // Stale hours: derive from today.updatedAt if available.
    let staleHours: number | null = null;
    if (today?.updatedAt) {
      const updated = new Date(today.updatedAt).getTime();
      if (Number.isFinite(updated)) {
        staleHours = Math.max(0, (Date.now() - updated) / (1000 * 60 * 60));
      }
    }
    const result = computeLauburuReadiness({
      today,
      baseline,
      acuteLoad,
      chronicLoad,
      staleHours,
    });
    res.status(200).json({ athleteId, date: today.date, ...result });
  } catch (error) {
    res.status(500).json({
      error: 'Readiness compute failed.',
      detail: error instanceof Error ? error.message : 'unknown',
    });
  }
});

router.get('/athletes/:athleteId/trends', async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const windowDaysRaw = Number(req.query.windowDays ?? 30);
    const windowDays = Number.isFinite(windowDaysRaw)
      ? Math.max(7, Math.min(1825, Math.floor(windowDaysRaw)))
      : 30;
    const records = await store.getNormalizedRecent(athleteId, windowDays);
    const out: any = { athleteId, windowDays, recordCount: records.length, metrics: {} };
    if (records.length === 0) {
      res.status(200).json(out);
      return;
    }
    // Sort ascending so trend-direction comparisons are oldest→newest.
    records.sort((a: any, b: any) => String(a.date).localeCompare(String(b.date)));
    const metricMap: Array<[string, (r: any) => number | null]> = [
      ['hrv_ms', (r) => r.hrvMs],
      ['rhr_bpm', (r) => r.restingHrBpm],
      ['sleep_hours', (r) => r.totalSleepHours],
      ['day_strain', (r) => r.dailyStrain],
      ['sleep_debt_hours', (r) => r.sleepDebtHours],
      ['recovery_score', (r) => r.recoveryScore],
      ['active_kcal', (r) => r.activeCaloriesKcal],
      ['sleep_efficiency_pct', (r) => r.sleepEfficiencyPct],
    ];
    for (const [name, pick] of metricMap) {
      const values: number[] = [];
      for (const r of records) {
        const v = pick(r);
        if (typeof v === 'number' && Number.isFinite(v)) values.push(v);
      }
      if (values.length === 0) {
        out.metrics[name] = { coverage_days: 0, confidence: 'insufficient', direction: 'insufficient' };
        continue;
      }
      const sorted = [...values].sort((a, b) => a - b);
      const mean = values.reduce((s, v) => s + v, 0) / values.length;
      const variance = values.reduce((s, v) => s + (v - mean) ** 2, 0) / values.length;
      const stdev = Math.sqrt(variance);
      const p = (q: number) => sorted[Math.min(sorted.length - 1, Math.max(0, Math.floor(q * (sorted.length - 1))))];
      // Trend direction: compare first-third mean vs last-third mean,
      // require effect size > 0.5 stdev to count as a real shift.
      let direction: 'improving' | 'worsening' | 'flat' | 'insufficient' = 'insufficient';
      if (values.length >= 7) {
        const third = Math.floor(values.length / 3);
        const oldMean = values.slice(0, third).reduce((s, v) => s + v, 0) / third;
        const newMean = values.slice(-third).reduce((s, v) => s + v, 0) / third;
        const delta = newMean - oldMean;
        const sig = stdev > 0 && Math.abs(delta) / stdev > 0.5;
        if (!sig) direction = 'flat';
        // Higher = better for HRV / sleep_hours / sleep_efficiency / recovery_score / active_kcal.
        // Lower = better for RHR / day_strain / sleep_debt.
        else {
          const higherIsBetter = ['hrv_ms', 'sleep_hours', 'sleep_efficiency_pct', 'recovery_score', 'active_kcal'].includes(name);
          if (higherIsBetter) direction = delta > 0 ? 'improving' : 'worsening';
          else direction = delta < 0 ? 'improving' : 'worsening';
        }
      }
      // Confidence: low if <7 days coverage, medium 7-29, high ≥30.
      const confidence = values.length >= 30 ? 'high' : values.length >= 7 ? 'medium' : 'low';
      // Latest-vs-baseline z (using window mean+stdev as baseline).
      const latest = values[values.length - 1];
      const z = stdev > 0 ? (latest - mean) / stdev : 0;
      out.metrics[name] = {
        coverage_days: values.length,
        coverage_pct: Math.round((values.length / windowDays) * 100),
        mean: Number(mean.toFixed(2)),
        stdev: Number(stdev.toFixed(2)),
        min: sorted[0],
        max: sorted[sorted.length - 1],
        p25: p(0.25),
        p75: p(0.75),
        latest: Number(latest.toFixed(2)),
        latest_z: Number(z.toFixed(2)),
        direction,
        confidence,
      };
    }
    out.firstDate = records[0].date;
    out.lastDate = records[records.length - 1].date;
    res.status(200).json(out);
  } catch (error) {
    res.status(500).json({
      error: 'Trends compute failed.',
      detail: error instanceof Error ? error.message : 'unknown',
    });
  }
});

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
      await saveAndMirrorNormalized(athleteId,record); // No seedMode marker — live data
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
      await saveAndMirrorNormalized(athleteId,normalized);
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
      await saveAndMirrorNormalized(athleteId,nutritionOnly);
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

    // Mirror raw evidence (Apple Health / Health Connect / Samsung /
    // Polar-via-HC etc.) to Supabase. Source-tag from `raw.provider`,
    // record-type qualifies the per-day record. Same fire-and-forget
    // contract as elsewhere — primary Railway store is unaffected.
    void mirrorRawSourceEvent({
      userId: athleteId,
      source: raw.provider,
      sourceRecordId: String((raw as any).id ?? `${raw.provider}_${raw.date}`),
      sourceRecordType: 'health_source_daily',
      localDate: raw.date,
      payload: raw,
      provenance: {
        ingest_route: '/ingest/health-source/daily',
        source_app: (raw as any).sourceApp ?? null,
        domains_from_polar: (raw as any).domainsFromPolar ?? null,
      },
    });

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
      await saveAndMirrorNormalized(athleteId,merged);
    } else {
      await saveAndMirrorNormalized(athleteId,normalized);
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
        await saveAndMirrorNormalized(athleteId,normalized);
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
        await saveAndMirrorNormalized(athleteId,nutritionOnly);
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
      await saveAndMirrorNormalized(athleteId,normalizedDay);
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
      await saveAndMirrorNormalized(athleteId,nutritionOnly);
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
