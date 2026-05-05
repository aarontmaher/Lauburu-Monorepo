/**
 * Public athlete-memory routes — app-facing read endpoints.
 *
 * Reads from the canonical api-ai/ seeded state via FileApiAiStateStore
 * and the cache-first read orchestrator. Works in seed-mode: if today's
 * artifacts don't exist, falls back through the read chain (weekly →
 * stable memory → normalized → raw). Never pretends WHOOP-native fields
 * exist when source health says they're stale or missing.
 */
import { Router } from 'express';
import path from 'path';
import { FileApiAiStateStore } from '../athlete-memory/file-api-ai-state-store';
import { readAthleteState } from '../../../../packages/shared/src/backend/services/orchestrate/read-athlete-state';
import { createLiveWhoopReader } from '../sources/liveWhoopReader';
import { deriveHealthCheck } from '../../../../packages/shared/src/backend/services/health-check/derive-health-check';
import { SEED_SYLLABUS, SEED_TOUR, deriveSyllabusProgress } from '../../../../packages/shared/src/syllabus';
import type { AthleteAccountProfile } from '../../../../packages/shared/src/syllabus/account-profile.types';
import type { VideoAttachment, VideoAttachmentSummary } from '../../../../packages/shared/src/syllabus/video-attachment.types';
import { buildCoachAnswer } from '../../../../packages/shared/src/backend/services/coach/build-coach-answer';
import { computeLauburuReadiness } from '../../../../packages/shared/src/backend/services/readiness/lauburu-readiness';
import { computeGrapplerReadiness } from '../../../../packages/shared/src/backend/services/readiness/grappler-readiness';

const router = Router();
const store = new FileApiAiStateStore(
  path.resolve(__dirname, '../../../data/private-athlete-memory'),
);
const liveReader = createLiveWhoopReader(store);

/**
 * Decode a Supabase JWT without verifying the signature.
 * We extract the `sub` claim (user id) to bind requests to the user.
 *
 * Signature verification would require the Supabase JWT secret on the
 * backend. For now, we pair this extraction with the legacy shared token
 * check to prevent unauthenticated traffic, and use the `sub` claim as
 * the authoritative user identity. This gives ownership enforcement
 * while a full JWT verifier is added later.
 */
function extractSupabaseUserIdFromAuthHeader(authHeader: string | undefined): string | null {
  if (!authHeader) return null;
  const match = /^Bearer\s+(.+)$/.exec(authHeader);
  if (!match) return null;
  const token = match[1];
  const parts = token.split('.');
  if (parts.length !== 3) return null;
  try {
    // Base64url decode the payload
    const payloadB64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = payloadB64 + '='.repeat((4 - payloadB64.length % 4) % 4);
    const payload = JSON.parse(Buffer.from(padded, 'base64').toString('utf8'));
    if (typeof payload?.sub === 'string') return payload.sub;
    return null;
  } catch {
    return null;
  }
}

/**
 * App-facing athlete-memory auth guard.
 *
 * Requires:
 *   1. Shared `x-athlete-memory-token` (keeps unauth traffic off the route)
 *   2. `Authorization: Bearer <supabase-jwt>` identifying the caller
 *   3. Path `:athleteId` MUST match the Supabase JWT `sub` (user.id)
 *   4. `x-athlete-id` header MUST match the path param
 *
 * The shared token ALONE is no longer sufficient — every app-facing read
 * must carry an authenticated user JWT. This prevents the shared token
 * from being used to impersonate any athleteId.
 *
 * Operator routes live under /v1/internal/* with a separate `x-internal-token`
 * guard. Those are explicitly operator-only and not app-callable.
 *
 * Dev/test override: when NODE_ENV=test or ALLOW_SHARED_TOKEN_ONLY=1,
 * requests without a JWT are allowed through for test harnesses. Production
 * must never set these.
 */
function requirePrivateAthleteAccess(req: any, res: any, next: any) {
  const expectedToken = process.env.ATHLETE_MEMORY_API_TOKEN;
  if (!expectedToken) {
    res.status(503).json({
      error: 'Private athlete-memory route is disabled until ATHLETE_MEMORY_API_TOKEN is configured.',
    });
    return;
  }
  const presentedToken = req.header('x-athlete-memory-token');
  const claimedAthleteId = req.header('x-athlete-id');
  const pathAthleteId = req.params.athleteId;

  // 1. Shared token check
  if (presentedToken !== expectedToken || claimedAthleteId !== pathAthleteId) {
    res.status(403).json({ error: 'Forbidden athlete-memory access.' });
    return;
  }

  // 2. JWT required — except for explicit test/dev modes
  const supabaseUserId = extractSupabaseUserIdFromAuthHeader(req.header('authorization'));
  const allowSharedTokenOnly = process.env.ALLOW_SHARED_TOKEN_ONLY === '1'
    || process.env.NODE_ENV === 'test';

  if (!supabaseUserId) {
    if (!allowSharedTokenOnly) {
      res.status(401).json({
        error: 'Authentication required.',
        detail: 'App-facing athlete-memory routes require a Supabase Authorization Bearer token.',
      });
      return;
    }
    // Dev/test: fall through and use the path athleteId as identity.
  } else if (supabaseUserId !== pathAthleteId) {
    // 3. Ownership mismatch
    res.status(403).json({
      error: 'Athlete ownership mismatch.',
      detail: 'Authenticated user cannot access another user\'s athlete data.',
    });
    return;
  }

  (req as any).authenticatedUserId = supabaseUserId;
  next();
}

// GET /api/athlete-memory/:athleteId/latest
// Returns the cache-first resolved state with layer provenance.
// Works in seed-mode: stale daily artifacts are returned with
// honest confidence/layer metadata so the consumer knows the age.
router.get('/:athleteId/latest', requirePrivateAthleteAccess, async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const date = (req.query.date as string) ?? undefined;

    const result = await readAthleteState(
      { athleteId, date },
      store,
      liveReader,
    );

    // Build a consumer-friendly envelope with embedded capability summary.
    // Mobile reads this ONE response for both coaching context and capability truth.
    const today = date ?? new Date().toISOString().slice(0, 10);
    const sourceHealth = await store.getSourceHealth(athleteId, 'whoop');

    // Derive the canonical health-check inline — same logic, one call
    const healthCheck = deriveHealthCheck({
      athleteId,
      today,
      dailyArtifact: result.dailyArtifact,
      weeklyArtifact: result.weeklyArtifact,
      stableMemory: result.stableMemory,
      whoopHealth: sourceHealth,
    });

    res.status(200).json({
      ok: true,
      athleteId: result.athleteId,
      date: result.date,
      confidence: result.confidence,
      liveWhoopRead: result.liveWhoopRead,
      stillMissing: result.stillMissing,
      layersConsulted: result.layersConsulted,

      // Artifacts (may be null or stale — consumer checks dates)
      dailyArtifact: result.dailyArtifact,
      weeklyArtifact: result.weeklyArtifact,
      stableMemory: result.stableMemory,

      // Source health
      sourceHealth,

      // Seed/live capability truth — embedded so mobile needs ONE call
      seedMode: healthCheck.seedMode,
      provisionalUntilDirectWhoop: healthCheck.provisionalUntilDirectWhoop,
      seedCaveats: healthCheck.seedMode || healthCheck.provisionalUntilDirectWhoop
        ? [
            healthCheck.seedMode ? 'Daily artifact is from a previous date, not today.' : null,
            sourceHealth?.degradedReason ?? null,
            healthCheck.provisionalUntilDirectWhoop ? 'Artifacts derived from cached data, not live WHOOP.' : null,
          ].filter(Boolean)
        : [],

      // Compact capability summary — mobile uses this to gate coaching UI
      capability: {
        mode: healthCheck.mode,
        safeFor: healthCheck.safeFor,
        notSafeFor: healthCheck.notSafeFor,
        missingWhoopNativeFields: healthCheck.missingWhoopNativeFields,
        recommendedReadOrder: healthCheck.recommendedReadOrder,
      },
    });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to read athlete state.',
      detail: error instanceof Error ? error.message : 'unknown_error',
    });
  }
});

// GET /api/athlete-memory/:athleteId/weekly/latest
router.get('/:athleteId/weekly/latest', requirePrivateAthleteAccess, async (req: any, res: any) => {
  try {
    const weekly = await store.getLatestWeeklySynthesis(req.params.athleteId);
    if (!weekly) {
      res.status(404).json({ error: 'No weekly synthesis artifact found.' });
      return;
    }
    const sourceHealth = await store.getSourceHealth(req.params.athleteId, 'whoop');
    const isProvisional = sourceHealth?.upstreamStatus === 'degraded'
      || sourceHealth?.freshnessStatus === 'stale';
    res.status(200).json({
      ...weekly,
      seedMode: isProvisional,
      provisionalUntilDirectWhoop: isProvisional,
    });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to read latest weekly synthesis.',
      detail: error instanceof Error ? error.message : 'unknown_error',
    });
  }
});

// GET /api/athlete-memory/:athleteId/source-health
router.get('/:athleteId/source-health', requirePrivateAthleteAccess, async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const whoop = await store.getSourceHealth(athleteId, 'whoop');
    const appleHealth = await store.getSourceHealth(athleteId, 'apple_health');

    res.status(200).json({
      ok: true,
      athleteId,
      providers: {
        whoop: whoop ?? { status: 'not_configured' },
        apple_health: appleHealth ?? { status: 'not_configured' },
      },
    });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to read source health.',
      detail: error instanceof Error ? error.message : 'unknown_error',
    });
  }
});

// GET /api/athlete-memory/:athleteId/seeded-state
// Returns all supplementary seeded state (baseline, thresholds, patterns, block summary).
// Read-only. These are seed-time snapshots, not live-computed values.
router.get('/:athleteId/seeded-state', requirePrivateAthleteAccess, async (req: any, res: any) => {
  try {
    const seeded = await store.getSeededState(req.params.athleteId);
    res.status(200).json({ ok: true, athleteId: req.params.athleteId, ...seeded });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to read seeded state.',
      detail: error instanceof Error ? error.message : 'unknown_error',
    });
  }
});

// GET /api/athlete-memory/:athleteId/health-check
// Public canonical health/capability summary.
// Same derive-health-check logic as the internal route — one source of truth.
// Mobile uses this to decide what to display without reconstructing state.
router.get('/:athleteId/health-check', requirePrivateAthleteAccess, async (req: any, res: any) => {
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
      detail: error instanceof Error ? error.message : 'unknown_error',
    });
  }
});

// GET /api/athlete-memory/:athleteId/ai-context
// Unified AI context — everything the API AI layer needs in one call.
// Combines: orchestrated read + health check + baselines + normalized + source health.
// The AI MUST check capability.notSafeFor before generating readiness claims.
router.get('/:athleteId/ai-context', requirePrivateAthleteAccess, async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const today = (req.query.date as string) ?? new Date().toISOString().slice(0, 10);

    // Parallel fetch — all reads go through the canonical api-ai store
    const [readResult, whoopHealth, whoopDirectSrc, appleHealthSrc, cronometerSrc, healthConnectSrc, polarSrc, polarViaHcSrc, samsungViaHcSrc, seededState] = await Promise.all([
      readAthleteState({ athleteId, date: today }, store, liveReader),
      store.getSourceHealth(athleteId, 'whoop'),
      store.getSourceHealth(athleteId, 'whoop_direct'),
      store.getSourceHealth(athleteId, 'apple_health'),
      store.getSourceHealth(athleteId, 'cronometer'),
      store.getSourceHealth(athleteId, 'health_connect'),
      store.getSourceHealth(athleteId, 'polar'),
      store.getSourceHealth(athleteId, 'polar_via_health_connect'),
      store.getSourceHealth(athleteId, 'samsung_health_via_health_connect'),
      store.getSeededState(athleteId),
    ]);
    // Prefer whoop_direct over bridge/seed for capability derivation.
    // whoop_direct is the per-user OAuth path; whoop is the single-user bridge.
    const sourceHealth = whoopDirectSrc?.freshnessStatus === 'fresh' ? whoopDirectSrc : whoopHealth;

    // Get today's normalized (may already be in the read result, or fetch separately)
    let normalizedDay = readResult.normalizedDay
      ?? await store.getNormalizedDay(athleteId, today);

    // If no normalized day exists, try a live WHOOP fetch via bridge.
    // This populates seed data for athletes who haven't run the full
    // ingest pipeline but whose WHOOP MCP has data available.
    if (!normalizedDay) {
      try {
        const liveFetched = await liveReader.fetchAndNormalize(athleteId, today);
        if (liveFetched) normalizedDay = liveFetched;
      } catch { /* bridge unavailable — continue without */ }
    }

    // Derive capability
    const healthCheck = deriveHealthCheck({
      athleteId,
      today,
      dailyArtifact: readResult.dailyArtifact,
      weeklyArtifact: readResult.weeklyArtifact,
      stableMemory: readResult.stableMemory,
      whoopHealth: sourceHealth,
    });

    // Extract baselines from stable memory
    const baseline = readResult.stableMemory?.physiologyBaseline;

    res.status(200).json({
      ok: true,
      athleteId,
      date: today,

      seedMode: healthCheck.seedMode,
      provisionalUntilDirectWhoop: healthCheck.provisionalUntilDirectWhoop,
      seedCaveats: healthCheck.seedMode || healthCheck.provisionalUntilDirectWhoop
        ? [
            healthCheck.seedMode ? 'Daily artifact is from a previous date.' : null,
            sourceHealth?.degradedReason ?? null,
            healthCheck.provisionalUntilDirectWhoop ? 'Data from cached seed, not live WHOOP.' : null,
          ].filter(Boolean)
        : [],

      capability: {
        mode: healthCheck.mode,
        safeFor: healthCheck.safeFor,
        notSafeFor: healthCheck.notSafeFor,
        missingWhoopNativeFields: healthCheck.missingWhoopNativeFields,
        recommendedReadOrder: healthCheck.recommendedReadOrder,
      },

      sourceHealth,
      normalizedDay,
      dailyArtifact: readResult.dailyArtifact,
      weeklyArtifact: readResult.weeklyArtifact,

      baselines: baseline ? {
        recoveryBaseline: baseline.recoveryBaseline,
        hrvBaseline: baseline.hrvBaseline,
        restingHrBaseline: baseline.restingHrBaseline,
        sleepBaseline: baseline.sleepBaseline,
        strainBaseline: baseline.strainBaseline,
        dataWindowDays: baseline.dataWindowDays,
        computedAt: baseline.computedAt,
      } : null,

      blockSummary: readResult.stableMemory?.currentBlockSummary ?? null,

      // Nutrition from normalized day with provenance
      nutritionDailySummary: await (async () => {
        if (!normalizedDay) return null;
        const n = normalizedDay;
        const missing: string[] = [];
        if (n.nutritionCalories == null) missing.push('calories');
        if (n.nutritionProteinGrams == null) missing.push('protein');
        if (n.nutritionCarbGrams == null) missing.push('carbs');
        if (n.nutritionFatGrams == null) missing.push('fat');
        const hasNutrition = n.nutritionCalories != null || n.nutritionProteinGrams != null
          || n.nutritionCarbGrams != null || n.nutritionFatGrams != null;
        const provider = n.provider ?? 'unknown';
        // Read real provenance from raw nutrition record
        const rawNutr = await store.getRawNutrition(athleteId, today);
        const realSourceDeps = (rawNutr?.sourceDependencies as string[] | undefined);
        const realSourceState = (rawNutr?.sourceState as string | undefined);
        const sourceState = realSourceState
          ?? (provider === 'cronometer' ? 'live'
            : provider === 'ai_photo' ? 'estimated'
            : provider === 'mixed' ? 'mixed'
            : hasNutrition ? 'manual' : null);
        return {
          calories: n.nutritionCalories,
          proteinGrams: n.nutritionProteinGrams,
          carbGrams: n.nutritionCarbGrams,
          fatGrams: n.nutritionFatGrams,
          coverage: n.nutritionCoverage,
          missingFields: missing,
          sourceState,
          sourceDependencies: realSourceDeps ?? (hasNutrition ? [provider] : []),
          allConfirmed: (rawNutr?.confirmed as boolean | undefined) ?? true,
        };
      })(),

      confidence: readResult.confidence,

      // Multi-source health summary for all known providers
      multiSourceHealth: {
        whoop: whoopHealth ? { status: whoopHealth.freshnessStatus, upstream: whoopHealth.upstreamStatus, reason: whoopHealth.degradedReason, lastIngestAt: whoopHealth.lastSuccessfulIngestAt } : { status: 'not_connected', reason: null, lastIngestAt: null },
        whoop_direct: whoopDirectSrc ? { status: whoopDirectSrc.freshnessStatus, upstream: whoopDirectSrc.upstreamStatus, reason: whoopDirectSrc.degradedReason, lastIngestAt: whoopDirectSrc.lastSuccessfulIngestAt, domainsAvailable: Object.keys(whoopDirectSrc.coverageByDomain ?? {}) } : { status: 'not_connected', reason: 'Per-user WHOOP OAuth not connected.', lastIngestAt: null, domainsAvailable: [] },
        apple_health: appleHealthSrc ? { status: appleHealthSrc.freshnessStatus, upstream: appleHealthSrc.upstreamStatus, reason: appleHealthSrc.degradedReason, lastIngestAt: appleHealthSrc.lastSuccessfulIngestAt } : { status: 'not_connected', reason: null, lastIngestAt: null },
        health_connect: healthConnectSrc ? { status: healthConnectSrc.freshnessStatus, upstream: healthConnectSrc.upstreamStatus, reason: healthConnectSrc.degradedReason, lastIngestAt: healthConnectSrc.lastSuccessfulIngestAt } : { status: 'not_connected', reason: 'No Health Connect ingest yet.', lastIngestAt: null },
        cronometer: cronometerSrc ? { status: cronometerSrc.freshnessStatus, upstream: cronometerSrc.upstreamStatus, reason: cronometerSrc.degradedReason, lastIngestAt: cronometerSrc.lastSuccessfulIngestAt } : { status: 'not_connected', reason: 'No Cronometer source-health record.', lastIngestAt: null },
        polar: polarSrc ? { status: polarSrc.freshnessStatus, upstream: polarSrc.upstreamStatus, reason: polarSrc.degradedReason, lastIngestAt: polarSrc.lastSuccessfulIngestAt } : { status: 'not_connected', reason: 'Direct Polar adapter not yet live. Polar may still be available via Health Connect.', lastIngestAt: null },
        polar_via_health_connect: polarViaHcSrc
          ? {
              status: polarViaHcSrc.freshnessStatus,
              upstream: polarViaHcSrc.upstreamStatus,
              reason: polarViaHcSrc.degradedReason,
              lastIngestAt: polarViaHcSrc.lastSuccessfulIngestAt,
              sourceApp: polarViaHcSrc.degradedReason?.startsWith('sourceApp:')
                ? polarViaHcSrc.degradedReason.slice('sourceApp:'.length).trim()
                : 'Polar Flow',
              coverage: Object.keys(polarViaHcSrc.coverageByDomain ?? {}),
            }
          : { status: 'not_connected', reason: 'No Polar-origin records have arrived through Health Connect yet.', lastIngestAt: null, sourceApp: null, coverage: [] },
        samsung_health_via_health_connect: samsungViaHcSrc
          ? {
              status: samsungViaHcSrc.freshnessStatus,
              upstream: samsungViaHcSrc.upstreamStatus,
              reason: samsungViaHcSrc.degradedReason,
              lastIngestAt: samsungViaHcSrc.lastSuccessfulIngestAt,
              sourceApp: samsungViaHcSrc.degradedReason?.startsWith('sourceApp:')
                ? samsungViaHcSrc.degradedReason.slice('sourceApp:'.length).trim()
                : 'Samsung Health',
              coverage: Object.keys(samsungViaHcSrc.coverageByDomain ?? {}),
            }
          : { status: 'not_connected', reason: 'No Samsung Health records have arrived through Health Connect yet.', lastIngestAt: null, sourceApp: null, coverage: [] },
      },

      // Nutrition source state
      nutritionSources: [
        normalizedDay?.nutritionCalories != null ? normalizedDay.provider ?? 'unknown' : null,
        cronometerSrc?.freshnessStatus === 'fresh' ? 'cronometer' : null,
      ].filter((s): s is string => s != null),

      // Recent HIIT sessions from dedicated session store
      recentHIITWorkouts: await (async () => {
        try {
          const sessions = await store.getRecentSessionSummaries(athleteId, 3);
          if (sessions.length === 0) return null;
          return sessions.map((s: any) => ({
            id: s.sessionId ?? s.id,
            date: s.date,
            protocolFormat: s.protocolFormat ?? 'unknown',
            machineType: s.machineType ?? 'manual',
            totalSets: s.totalSets ?? 0,
            avgWatts: s.avgWatts ?? null,
            totalCalories: s.totalCalories ?? null,
            avgHr: s.avgHr ?? null,
          }));
        } catch { return null; }
      })(),

      // HIIT progress summary — compare two most recent sessions with same template
      hiitProgressSummary: await (async () => {
        try {
          const sessions = await store.getRecentSessionSummaries(athleteId, 10);
          if (sessions.length < 2) return null;
          // Find the most recent session with a template
          const latest = sessions.find((s: any) => s.templateId) as any;
          if (!latest?.templateId) return null;
          // Find the previous session with the same template
          const previous = sessions.find(
            (s: any) => s.templateId === latest.templateId && s.sessionId !== latest.sessionId,
          ) as any;
          if (!previous) return null;
          return {
            avgWattsDelta: latest.avgWatts != null && previous.avgWatts != null
              ? latest.avgWatts - previous.avgWatts : null,
            peakWattsDelta: latest.peakWatts != null && previous.peakWatts != null
              ? latest.peakWatts - previous.peakWatts : null,
            wattsDropOffPct: latest.wattsDropOffPct ?? null,
            hrDriftPct: latest.hrDriftPct ?? null,
          };
        } catch { return null; }
      })(),

      // Machine connection status — truthful, no faking
      machineConnectionStatus: {
        hasLiveConnection: false,
        primaryFallback: 'manual',
      },

      // Live readiness analysis — only populated when the current user
      // has a fresh whoop_direct source with recovery/HRV/strain.
      liveReadiness: await (async () => {
        try {
          const { analyseReadiness } = await import('../../../../packages/shared/src/backend/services/readiness/analyse-readiness');
          const whoopDirectFresh = whoopDirectSrc?.freshnessStatus === 'fresh'
            || whoopHealth?.freshnessStatus === 'fresh';
          return analyseReadiness({
            athleteId,
            date: today,
            normalizedDay,
            dailyArtifact: readResult.dailyArtifact ?? null,
            whoopDirectFresh,
          });
        } catch { return null; }
      })(),

      // Hub-first contextual readiness — the PRIMARY readiness model.
      // Always runs from Health Connect / Samsung / Polar / Apple Health
      // data. Produces useful training context even without direct WHOOP.
      contextualReadiness: await (async () => {
        try {
          const { analyseContextualReadiness } = await import('../../../../packages/shared/src/backend/services/readiness/analyse-contextual-readiness');
          const recentDays = await store.getNormalizedRecent(athleteId, 14);
          const hubSources: string[] = [];
          if (healthConnectSrc?.freshnessStatus === 'fresh') hubSources.push('Health Connect');
          if (samsungViaHcSrc?.freshnessStatus === 'fresh') hubSources.push('Samsung Health');
          if (polarViaHcSrc?.freshnessStatus === 'fresh') hubSources.push('Polar via HC');
          if (appleHealthSrc?.freshnessStatus === 'fresh') hubSources.push('Apple Health');
          const whoopDirectFresh = whoopDirectSrc?.freshnessStatus === 'fresh'
            || whoopHealth?.freshnessStatus === 'fresh';
          const hiitSessions = await store.getRecentSessionSummaries(athleteId, 10).catch(() => []);
          const last7 = new Date(Date.now() - 7 * 86_400_000).toISOString().slice(0, 10);
          const hiitLast7 = hiitSessions.filter((s: any) => s.date >= last7).length;
          const grapplingLast7 = recentDays.filter(d => d.date >= last7 && (d.grapplingSessionCount ?? 0) > 0)
            .reduce((sum, d) => sum + (d.grapplingSessionCount ?? 0), 0);
          const backlogStatus = await store.getBacklogStatus(athleteId).catch(() => null);
          return analyseContextualReadiness({
            athleteId,
            date: today,
            recentDays,
            today: normalizedDay,
            hubSources,
            hiitSessionsLast7Days: hiitLast7,
            grapplingSessionsLast7Days: grapplingLast7,
            nutritionLoggedToday: normalizedDay?.nutritionCalories != null,
            hasDirectWhoop: whoopDirectFresh,
            historyScope: (backlogStatus as any)?.historyScope ?? 'unknown',
          });
        } catch { return null; }
      })(),
    });
  } catch (error) {
    res.status(500).json({
      error: 'AI context fetch failed.',
      detail: error instanceof Error ? error.message : 'unknown_error',
    });
  }
});

// GET /api/athlete-memory/:athleteId/syllabus
// Returns the shared syllabus definition with athlete-scoped progress
// derived from existing reference-progress data. The syllabus itself
// is shared (non-personal). Progress is athlete-specific.
router.get('/:athleteId/syllabus', requirePrivateAthleteAccess, async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const belt = (req.query.belt as string) ?? 'white';

    // Find the requested belt in the seed syllabus
    const beltDef = SEED_SYLLABUS.belts.find((b) => b.belt === belt);
    if (!beltDef) {
      res.status(404).json({ error: `Belt '${belt}' not found in syllabus.` });
      return;
    }

    // The reference progress store is mobile-side. For the backend,
    // we can only derive progress if the mobile sends it. For now,
    // return the syllabus with empty progress — mobile will merge
    // its local progress client-side using deriveSyllabusProgress().
    res.status(200).json({
      ok: true,
      syllabus: {
        schemaVersion: SEED_SYLLABUS.schemaVersion,
        updatedAt: SEED_SYLLABUS.updatedAt,
        belt: beltDef,
      },
      progressDerivationAvailable: true,
      progressNote: 'Use deriveSyllabusProgress() client-side with your local reference-progress-store data.',
    });
  } catch (error) {
    res.status(500).json({
      error: 'Syllabus fetch failed.',
      detail: error instanceof Error ? error.message : 'unknown_error',
    });
  }
});

// POST /api/athlete-memory/:athleteId/syllabus/progress
// Accepts the athlete's reference progress map from mobile and returns
// a derived compact syllabus progress summary. The progress map stays
// on the mobile device — this route is stateless derivation only.
// Body: { belt?: string, progressMap: Record<string, 'none'|'drilling'|'learned'|'tracking'> }
router.post('/:athleteId/syllabus/progress', requirePrivateAthleteAccess, async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const belt = (req.body?.belt as string) ?? 'white';
    const progressMap = (req.body?.progressMap ?? {}) as Record<string, string>;

    const beltDef = SEED_SYLLABUS.belts.find((b) => b.belt === belt);
    if (!beltDef) {
      res.status(404).json({ error: `Belt '${belt}' not found in syllabus.` });
      return;
    }

    const progress = deriveSyllabusProgress(athleteId, beltDef, progressMap as any);

    // Build compact section-level counts for mobile display
    const sectionCounts: Record<string, { total: number; started: number; demonstrated: number }> = {};
    for (const item of progress.items) {
      const req = beltDef.requirements.find((r) => r.id === item.requirementId);
      const section = req?.sectionId ?? 'general';
      if (!sectionCounts[section]) sectionCounts[section] = { total: 0, started: 0, demonstrated: 0 };
      sectionCounts[section].total += 1;
      if (item.status !== 'not_started') sectionCounts[section].started += 1;
      if (item.status === 'demonstrated' || item.status === 'verified') sectionCounts[section].demonstrated += 1;
    }

    res.status(200).json({
      ok: true,
      athleteId,
      belt: progress.currentBelt,
      updatedAt: progress.updatedAt,

      // Compact summary — mobile's primary display source
      summary: progress.summary,

      // Per-section breakdown for mobile's section-level UI
      sectionCounts,

      // Full per-item progress if mobile wants detail view
      items: progress.items,

      // Honesty markers
      derivedFromReferenceProgress: true,
      progressConfidenceNote: 'Progress is derived from local reference-progress data. Demonstrated status means the technique is marked learned in the reference system, not formally assessed.',
      promotionReadinessNote: 'Syllabus progress counts do not imply belt readiness or promotion eligibility.',
    });
  } catch (error) {
    res.status(500).json({
      error: 'Syllabus progress derivation failed.',
      detail: error instanceof Error ? error.message : 'unknown_error',
    });
  }
});

// GET /api/athlete-memory/syllabus/all
// Returns the full shared syllabus (all belts) without athlete context.
// No auth required for the shared curriculum definition.
router.get('/syllabus/all', async (_req: any, res: any) => {
  res.status(200).json(SEED_SYLLABUS);
});

// GET /api/athlete-memory/tour
// Returns shared app tour content. No auth — shared content, not personal.
router.get('/tour', async (_req: any, res: any) => {
  res.status(200).json(SEED_TOUR);
});

// GET /api/athlete-memory/:athleteId/profile
// Compact athlete account profile with belt rank and syllabus summary.
// Belt defaults to 'white' / 'default' source until coach-verified.
router.get('/:athleteId/profile', requirePrivateAthleteAccess, async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const whiteBelt = SEED_SYLLABUS.belts.find((b) => b.belt === 'white');

    const profile: AthleteAccountProfile = {
      athleteId,
      beltRank: 'white',
      beltUpdatedAt: null,
      beltSource: 'default',
      syllabus: whiteBelt ? {
        trackingBelt: 'white',
        totalRequirements: whiteBelt.requirementCount,
        startedCount: 0,
        demonstratedCount: 0,
      } : null,
    };

    res.status(200).json({ ok: true, ...profile });
  } catch (error) {
    res.status(500).json({
      error: 'Profile fetch failed.',
      detail: error instanceof Error ? error.message : 'unknown_error',
    });
  }
});

// GET /api/athlete-memory/:athleteId/videos
// Returns video attachment state for syllabus requirements.
// Currently all techniques are 'not_attached' — video content
// lives on the hosted website, not in the mobile seed data.
// This endpoint is honest: it returns the real availability state,
// not inferred readiness from bare URLs.
router.get('/:athleteId/videos', requirePrivateAthleteAccess, async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const belt = (req.query.belt as string) ?? 'white';
    const beltDef = SEED_SYLLABUS.belts.find((b) => b.belt === belt);

    if (!beltDef) {
      res.status(404).json({ error: `Belt '${belt}' not found.` });
      return;
    }

    // Build truthful video attachment state — currently none attached in-app.
    // Videos live on the hosted 3D map. Fallback labels explain this honestly.
    const summaries: VideoAttachmentSummary[] = beltDef.requirements
      .filter((r) => r.type === 'technique')
      .map((r): VideoAttachmentSummary => ({
        targetId: r.id,
        availability: 'not_attached',
        provider: 'website_3d_map',
        title: r.label,
        playbackUrl: null,
        externalUrl: r.positionName
          ? `https://www.lauburugrapplingmap.com/#pos=${encodeURIComponent(r.positionName)}`
          : null,
        fallbackLabel: 'View in 3D map',
        fallbackReason: 'Video content is attached to positions in the hosted 3D map, not bundled in the mobile app.',
      }));

    res.status(200).json({
      ok: true,
      athleteId,
      belt,
      totalTechniques: summaries.length,
      attachedReady: 0,
      attachedUnavailable: 0,
      notAttached: summaries.length,
      items: summaries,
      note: 'Technique videos are served by the hosted 3D map. Mobile seed data does not include video attachments.',
    });
  } catch (error) {
    res.status(500).json({
      error: 'Video attachment fetch failed.',
      detail: error instanceof Error ? error.message : 'unknown_error',
    });
  }
});

// POST /api/athlete-memory/:athleteId/coach/ask
// Canonical Coach answer endpoint. Accepts a question, fetches ai-context
// internally, classifies the question, and returns a typed answer card.
// Mobile renders this directly without local answer composition.
router.post('/:athleteId/coach/ask', requirePrivateAthleteAccess, async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const { question, topic } = req.body as { question: string; topic?: string };

    if (!question?.trim()) {
      res.status(400).json({
        ok: false,
        domain: 'general',
        mode: 'seed_partial',
        questionClass: 'invalid_input',
        status: 'unsupported',
        answer: { short: 'No question provided.', why: 'A question is required.', nextStep: 'Type a question and try again.', missingnessNote: null },
        confidence: 'low',
        sourceDependencies: [],
        missingFields: ['question'],
        safetyFlags: [],
        upgradeHint: null,
      });
      return;
    }

    const today = new Date().toISOString().slice(0, 10);

    // Fetch canonical ai-context internally (same as /ai-context endpoint)
    const [readResult, sourceHealth, whoopDirectCoach, ahSrc, crSrc, hcSrc, polarSrc, polarViaHcSrcCoach, samsungViaHcSrcCoach] = await Promise.all([
      readAthleteState({ athleteId, date: today }, store, liveReader),
      store.getSourceHealth(athleteId, 'whoop'),
      store.getSourceHealth(athleteId, 'whoop_direct'),
      store.getSourceHealth(athleteId, 'apple_health'),
      store.getSourceHealth(athleteId, 'cronometer'),
      store.getSourceHealth(athleteId, 'health_connect'),
      store.getSourceHealth(athleteId, 'polar'),
      store.getSourceHealth(athleteId, 'polar_via_health_connect'),
      store.getSourceHealth(athleteId, 'samsung_health_via_health_connect'),
    ]);

    let normalizedDay = readResult.normalizedDay
      ?? await store.getNormalizedDay(athleteId, today);

    // Live WHOOP fallback for uninitialized athletes
    if (!normalizedDay) {
      try {
        const liveFetched = await liveReader.fetchAndNormalize(athleteId, today);
        if (liveFetched) normalizedDay = liveFetched;
      } catch { /* bridge unavailable */ }
    }

    const healthCheck = deriveHealthCheck({
      athleteId, today,
      dailyArtifact: readResult.dailyArtifact,
      weeklyArtifact: readResult.weeklyArtifact,
      stableMemory: readResult.stableMemory,
      whoopHealth: sourceHealth,
    });

    const baseline = readResult.stableMemory?.physiologyBaseline;
    const nutrMissing: string[] = [];
    if (normalizedDay) {
      if (normalizedDay.nutritionCalories == null) nutrMissing.push('calories');
      if (normalizedDay.nutritionProteinGrams == null) nutrMissing.push('protein');
      if (normalizedDay.nutritionCarbGrams == null) nutrMissing.push('carbs');
      if (normalizedDay.nutritionFatGrams == null) nutrMissing.push('fat');
    }

    // Build the ai-context shape for the answer builder
    const aiContext = {
      ok: true,
      athleteId,
      date: today,
      seedMode: healthCheck.seedMode,
      provisionalUntilDirectWhoop: healthCheck.provisionalUntilDirectWhoop,
      seedCaveats: [] as string[],
      capability: {
        mode: healthCheck.mode,
        safeFor: healthCheck.safeFor,
        notSafeFor: healthCheck.notSafeFor,
        missingWhoopNativeFields: healthCheck.missingWhoopNativeFields,
        recommendedReadOrder: healthCheck.recommendedReadOrder,
      },
      sourceHealth,
      normalizedDay,
      dailyArtifact: readResult.dailyArtifact,
      weeklyArtifact: readResult.weeklyArtifact,
      baselines: baseline ? {
        recoveryBaseline: baseline.recoveryBaseline,
        hrvBaseline: baseline.hrvBaseline,
        restingHrBaseline: baseline.restingHrBaseline,
        sleepBaseline: baseline.sleepBaseline,
        strainBaseline: baseline.strainBaseline,
        dataWindowDays: baseline.dataWindowDays,
        computedAt: baseline.computedAt,
      } : null,
      blockSummary: readResult.stableMemory?.currentBlockSummary ?? null,
      nutritionDailySummary: normalizedDay ? await (async () => {
        const hasNutrition = normalizedDay.nutritionCalories != null || normalizedDay.nutritionProteinGrams != null
          || normalizedDay.nutritionCarbGrams != null || normalizedDay.nutritionFatGrams != null;
        const provider = normalizedDay.provider ?? 'unknown';
        const rawNutr = await store.getRawNutrition(athleteId, today);
        const realSourceDeps = (rawNutr?.sourceDependencies as string[] | undefined);
        const realSourceState = (rawNutr?.sourceState as string | undefined);
        const nutrSourceState = realSourceState
          ?? (provider === 'cronometer' ? 'live'
            : provider === 'ai_photo' ? 'estimated'
            : provider === 'mixed' ? 'mixed'
            : hasNutrition ? 'manual' : null);
        return {
          calories: normalizedDay.nutritionCalories,
          proteinGrams: normalizedDay.nutritionProteinGrams,
          carbGrams: normalizedDay.nutritionCarbGrams,
          fatGrams: normalizedDay.nutritionFatGrams,
          coverage: normalizedDay.nutritionCoverage,
          missingFields: nutrMissing,
          sourceState: nutrSourceState,
          sourceDependencies: realSourceDeps ?? (hasNutrition ? [provider] : []),
          allConfirmed: (rawNutr?.confirmed as boolean | undefined) ?? true,
        };
      })() : null,
      nutritionSources: [
        normalizedDay?.nutritionCalories != null ? normalizedDay.provider ?? 'unknown' : null,
        crSrc?.freshnessStatus === 'fresh' ? 'cronometer' : null,
      ].filter((s): s is string => s != null),
      recentHIITWorkouts: await (async () => {
        try {
          const sessions = await store.getRecentSessionSummaries(athleteId, 3);
          if (sessions.length === 0) return null;
          return sessions.map((s: any) => ({
            id: s.sessionId ?? s.id,
            date: s.date,
            protocolFormat: s.protocolFormat ?? 'unknown',
            machineType: s.machineType ?? 'manual',
            totalSets: s.totalSets ?? 0,
            avgWatts: s.avgWatts ?? null,
            totalCalories: s.totalCalories ?? null,
            avgHr: s.avgHr ?? null,
          }));
        } catch { return null; }
      })(),
      hiitProgressSummary: await (async () => {
        try {
          const sessions = await store.getRecentSessionSummaries(athleteId, 10);
          if (sessions.length < 2) return null;
          const latest = sessions.find((s: any) => s.templateId) as any;
          if (!latest?.templateId) return null;
          const previous = sessions.find(
            (s: any) => s.templateId === latest.templateId && s.sessionId !== latest.sessionId,
          ) as any;
          if (!previous) return null;
          return {
            avgWattsDelta: latest.avgWatts != null && previous.avgWatts != null
              ? latest.avgWatts - previous.avgWatts : null,
            peakWattsDelta: latest.peakWatts != null && previous.peakWatts != null
              ? latest.peakWatts - previous.peakWatts : null,
            wattsDropOffPct: latest.wattsDropOffPct ?? null,
            hrDriftPct: latest.hrDriftPct ?? null,
          };
        } catch { return null; }
      })(),
      machineConnectionStatus: { hasLiveConnection: false, primaryFallback: 'manual' },
      confidence: readResult.confidence,
      multiSourceHealth: {
        whoop: sourceHealth ? { status: sourceHealth.freshnessStatus, upstream: sourceHealth.upstreamStatus, reason: sourceHealth.degradedReason, lastIngestAt: sourceHealth.lastSuccessfulIngestAt } : { status: 'not_connected', reason: null, lastIngestAt: null },
        apple_health: ahSrc ? { status: ahSrc.freshnessStatus, upstream: ahSrc.upstreamStatus, reason: ahSrc.degradedReason, lastIngestAt: ahSrc.lastSuccessfulIngestAt } : { status: 'not_connected', reason: null, lastIngestAt: null },
        health_connect: hcSrc ? { status: hcSrc.freshnessStatus, upstream: hcSrc.upstreamStatus, reason: hcSrc.degradedReason, lastIngestAt: hcSrc.lastSuccessfulIngestAt } : { status: 'not_connected', reason: 'No Health Connect ingest yet.', lastIngestAt: null },
        cronometer: crSrc ? { status: crSrc.freshnessStatus, upstream: crSrc.upstreamStatus, reason: crSrc.degradedReason, lastIngestAt: crSrc.lastSuccessfulIngestAt } : { status: 'not_connected', reason: 'No Cronometer source-health record.', lastIngestAt: null },
        polar: polarSrc ? { status: polarSrc.freshnessStatus, upstream: polarSrc.upstreamStatus, reason: polarSrc.degradedReason, lastIngestAt: polarSrc.lastSuccessfulIngestAt } : { status: 'not_connected', reason: 'Direct Polar adapter not yet live. Polar may still be available via Health Connect.', lastIngestAt: null },
        polar_via_health_connect: polarViaHcSrcCoach
          ? {
              status: polarViaHcSrcCoach.freshnessStatus,
              upstream: polarViaHcSrcCoach.upstreamStatus,
              reason: polarViaHcSrcCoach.degradedReason,
              lastIngestAt: polarViaHcSrcCoach.lastSuccessfulIngestAt,
              sourceApp: polarViaHcSrcCoach.degradedReason?.startsWith('sourceApp:')
                ? polarViaHcSrcCoach.degradedReason.slice('sourceApp:'.length).trim()
                : 'Polar Flow',
              coverage: Object.keys(polarViaHcSrcCoach.coverageByDomain ?? {}),
            }
          : { status: 'not_connected', reason: 'No Polar-origin records have arrived through Health Connect yet.', lastIngestAt: null, sourceApp: null, coverage: [] },
        samsung_health_via_health_connect: samsungViaHcSrcCoach
          ? {
              status: samsungViaHcSrcCoach.freshnessStatus,
              upstream: samsungViaHcSrcCoach.upstreamStatus,
              reason: samsungViaHcSrcCoach.degradedReason,
              lastIngestAt: samsungViaHcSrcCoach.lastSuccessfulIngestAt,
              sourceApp: 'Samsung Health',
              coverage: Object.keys(samsungViaHcSrcCoach.coverageByDomain ?? {}),
            }
          : { status: 'not_connected', reason: 'No Samsung Health records via Health Connect.', lastIngestAt: null, sourceApp: null, coverage: [] },
      },
      // First-run backlog summary — Coach reads this for "what have you
      // learned about me" style questions. Scoped to this athleteId.
      backlogSummary: await store.getLatestBacklogSummary(athleteId).catch(() => null),
    };

    // Inject Lauburu Readiness onto the AI context. Pure compute over
    // normalized metrics + acute/chronic load. Failure here is
    // swallowed — Coach falls back to its existing daily-artifact
    // path unchanged via the readinessFragment null-return path.
    try {
      // Lookback window: pull up to ~5 years (1825 d) of normalised
      // metrics so the AI can build long-term / all-time artifacts.
      // Daily-recommendation paths still emphasise the 7/30/90 windows
      // — this only widens what's *available* for trend questions.
      const lookback = await store.getNormalizedRecent(athleteId, 1825);
      const sortedAsc = [...(lookback ?? [])].sort((a: any, b: any) => String(a.date).localeCompare(String(b.date)));
      const todayRec = sortedAsc[sortedAsc.length - 1] ?? null;
      const baseline = todayRec ? sortedAsc.filter((r: any) => r.date < (todayRec as any).date) : [];
      const acuteVals = sortedAsc.slice(-7)
        .map((r: any) => r.dailyStrain)
        .filter((v: any) => typeof v === 'number' && Number.isFinite(v)) as number[];
      const chronicVals = baseline.slice(-28)
        .map((r: any) => r.dailyStrain)
        .filter((v: any) => typeof v === 'number' && Number.isFinite(v)) as number[];
      const acuteLoad = acuteVals.length > 0
        ? { sum: acuteVals.reduce((s, v) => s + v, 0), avg: acuteVals.reduce((s, v) => s + v, 0) / acuteVals.length, days: acuteVals.length }
        : null;
      const chronicLoad = chronicVals.length > 0
        ? { avg: chronicVals.reduce((s, v) => s + v, 0) / chronicVals.length, days: chronicVals.length }
        : null;
      let staleHours: number | null = null;
      if ((todayRec as any)?.updatedAt) {
        const ms = new Date((todayRec as any).updatedAt).getTime();
        if (Number.isFinite(ms)) staleHours = Math.max(0, (Date.now() - ms) / (1000 * 60 * 60));
      }
      (aiContext as any).lauburu_readiness = computeLauburuReadiness({
        today: todayRec as any,
        baseline: baseline as any,
        acuteLoad,
        chronicLoad,
        staleHours,
      });

      // Grappler Readiness — the app-owned multi-bucket score that
      // is the product number going forward. Wearable-native scores
      // (WHOOP recovery, day_strain, etc.) are carried unmodified
      // on `raw_source_scores` as supporting evidence, never primary.
      // grappling + subjective buckets stay null until session
      // intensity + check-in slider fields are extended (Batches B/C
      // of the Grappler Readiness plan). Failure here must NOT
      // break /coach/ask — wrap in try/catch.
      try {
        (aiContext as any).grappler_readiness = computeGrapplerReadiness({
          today: todayRec as any,
          baseline: baseline as any,
          acuteLoad,
          chronicLoad,
          staleHours,
          // latestCheckin + recentGrappling intentionally null —
          // populated when Batches B/C land. Bucket compute returns
          // `score: null` with `missing: [...]` so the UI can show
          // "Log a check-in" prompts without faking a number.
          latestCheckin: null,
          recentGrappling: null,
        });
      } catch { /* grappler-readiness compute failure must not break Coach */ }

      // Long-term trend bundle — same algorithm as the
      // /v1/internal/athletes/:athleteId/ai-health-context endpoint.
      // Lets buildCoachAnswer answer "what trends can you find" /
      // "analyse my long-term data" with real coverage figures
      // instead of falling through to "Limited context".
      function trendSummary(records: any[], windowDays: number) {
        const out: Record<string, any> = {};
        const slice = records.slice(-windowDays);
        const sources_seen = new Set<string>();
        for (const r of slice) {
          if (typeof r.provider === 'string' && r.provider.length > 0) sources_seen.add(r.provider);
          // Multi-source records carry per-domain provenance flags.
          if (Array.isArray(r.providerSources)) {
            for (const p of r.providerSources) if (typeof p === 'string') sources_seen.add(p);
          }
        }
        const map: Array<[string, (r: any) => number | null, boolean]> = [
          ['hrv_ms', (r) => r.hrvMs, true],
          ['rhr_bpm', (r) => r.restingHrBpm, false],
          ['sleep_hours', (r) => r.totalSleepHours, true],
          ['day_strain', (r) => r.dailyStrain, false],
          ['recovery_score', (r) => r.recoveryScore, true],
          ['steps', (r) => r.steps ?? null, true],
          ['active_calories', (r) => r.activeCalories ?? null, true],
          ['bodyweight_kg', (r) => r.bodyweightKg ?? null, true],
          ['nutrition_calories', (r) => r.nutritionCalories ?? null, true],
          ['nutrition_protein_g', (r) => r.nutritionProteinGrams ?? null, true],
        ];
        for (const [name, pick, higherBetter] of map) {
          const vs: number[] = [];
          for (const r of slice) {
            const v = pick(r);
            if (typeof v === 'number' && Number.isFinite(v)) vs.push(v);
          }
          if (vs.length === 0) {
            out[name] = {
              coverage_days: 0,
              coverage_pct: 0,
              direction: 'insufficient',
              confidence: 'insufficient',
              variability: 'insufficient',
              consistency: 'insufficient',
              spikes: 0,
            };
            continue;
          }
          const m = vs.reduce((s, v) => s + v, 0) / vs.length;
          const sd = Math.sqrt(vs.reduce((s, v) => s + (v - m) ** 2, 0) / vs.length);
          // Coefficient of variation for variability classification.
          // Sleep / RHR / HRV use absolute scales — we still report cov_pct.
          const cov_pct = m > 0 ? (sd / m) * 100 : 0;
          let variability: 'low' | 'medium' | 'high' | 'insufficient' = 'insufficient';
          if (vs.length >= 4) {
            variability = cov_pct < 8 ? 'low' : cov_pct < 18 ? 'medium' : 'high';
          }
          // Spikes: count of points more than 2 SD from mean.
          let spikes = 0;
          if (vs.length >= 7 && sd > 0) {
            for (const v of vs) if (Math.abs(v - m) / sd > 2) spikes += 1;
          }
          // Consistency: coverage_pct + variability => low/medium/high.
          let consistency: 'low' | 'medium' | 'high' = 'low';
          const cov_window_pct = (vs.length / windowDays) * 100;
          if (cov_window_pct >= 80 && variability !== 'high') consistency = 'high';
          else if (cov_window_pct >= 50 && variability !== 'high') consistency = 'medium';
          let direction: 'improving' | 'worsening' | 'flat' | 'insufficient' = 'insufficient';
          if (vs.length >= 7) {
            const third = Math.max(1, Math.floor(vs.length / 3));
            const oldM = vs.slice(0, third).reduce((s, v) => s + v, 0) / third;
            const newM = vs.slice(-third).reduce((s, v) => s + v, 0) / third;
            const delta = newM - oldM;
            if (sd > 0 && Math.abs(delta) / sd > 0.5) {
              direction = (higherBetter ? delta > 0 : delta < 0) ? 'improving' : 'worsening';
            } else direction = 'flat';
          }
          // Confidence is a roll-up: needs both coverage AND signal.
          let conf: 'high' | 'medium' | 'low' = 'low';
          if (vs.length >= 30 && variability !== 'high') conf = 'high';
          else if (vs.length >= 14) conf = 'medium';
          out[name] = {
            coverage_days: vs.length,
            coverage_pct: Math.round((vs.length / windowDays) * 100),
            direction,
            confidence: conf,
            variability,
            consistency,
            spikes,
            mean: Number(m.toFixed(2)),
            latest: Number(vs[vs.length - 1].toFixed(2)),
            cov_pct: Number(cov_pct.toFixed(1)),
          };
        }
        return { metrics: out, sources_used: Array.from(sources_seen) };
      }
      (aiContext as any).trends_short_7d   = trendSummary(sortedAsc, 7);
      (aiContext as any).trends_short_14d  = trendSummary(sortedAsc, 14);
      (aiContext as any).trends_medium_30d = trendSummary(sortedAsc, 30);
      (aiContext as any).trends_long_90d   = trendSummary(sortedAsc, 90);
      (aiContext as any).trends_long_180d  = trendSummary(sortedAsc, 180);
      (aiContext as any).trends_long_365d  = trendSummary(sortedAsc, 365);
      // All-available / all-time uses the entire normalised history we
      // can see (capped at 1825 d above). Coverage figures already
      // express "days with the metric"; this just stops capping by
      // window length.
      (aiContext as any).trends_all_time   = trendSummary(sortedAsc, sortedAsc.length || 1);
      (aiContext as any).data_coverage = {
        total_normalized_days: sortedAsc.length,
        first_date: sortedAsc[0]?.date ?? null,
        last_date: (todayRec as any)?.date ?? null,
        baseline_days: baseline.length,
      };

      // ── Long-term baseline summary ──────────────────────────────
      // Cheap stats over the 95-day window we already hold in memory.
      // Stable-memory baselines (physiologyBaseline) are READ-ONLY here
      // and are produced by the daily-refresh job. This summary is a
      // separate, recomputable artifact for AI context only.
      const longTermBaseline: Record<string, any> = {};
      const baselineMetrics: Array<[string, (r: any) => number | null]> = [
        ['hrv_ms', (r) => r.hrvMs ?? null],
        ['rhr_bpm', (r) => r.restingHrBpm ?? null],
        ['sleep_hours', (r) => r.totalSleepHours ?? null],
        ['day_strain', (r) => r.dailyStrain ?? null],
        ['recovery_score', (r) => r.recoveryScore ?? null],
        ['steps', (r) => r.steps ?? null],
        ['bodyweight_kg', (r) => r.bodyweightKg ?? null],
      ];
      for (const [name, pick] of baselineMetrics) {
        const vs: number[] = [];
        for (const r of sortedAsc) {
          const v = pick(r);
          if (typeof v === 'number' && Number.isFinite(v)) vs.push(v);
        }
        if (vs.length === 0) {
          longTermBaseline[name] = { count: 0 };
          continue;
        }
        const mean = vs.reduce((s, v) => s + v, 0) / vs.length;
        const sd = Math.sqrt(vs.reduce((s, v) => s + (v - mean) ** 2, 0) / vs.length);
        const sorted = [...vs].sort((a, b) => a - b);
        const p10 = sorted[Math.floor(sorted.length * 0.1)];
        const p50 = sorted[Math.floor(sorted.length * 0.5)];
        const p90 = sorted[Math.floor(sorted.length * 0.9)];
        longTermBaseline[name] = {
          count: vs.length,
          mean: Number(mean.toFixed(2)),
          sd: Number(sd.toFixed(2)),
          p10: Number(p10.toFixed(2)),
          p50: Number(p50.toFixed(2)),
          p90: Number(p90.toFixed(2)),
        };
      }
      (aiContext as any).long_term_baseline = longTermBaseline;

      // ── Memory promotion candidates ─────────────────────────────
      // Surface recurring patterns the user could promote into stable
      // memory after explicit review. Pure read; never mutates store.
      // Each candidate carries: metric, pattern, evidence_window,
      // source_coverage, confidence, why_it_matters, status.
      const candidates: Array<Record<string, any>> = [];
      const t30 = (aiContext as any).trends_medium_30d?.metrics ?? {};
      const t90 = (aiContext as any).trends_long_90d?.metrics ?? {};
      function pushCandidate(metric: string, pattern: string, win: '30d' | '90d', why: string) {
        const t = (win === '90d' ? t90 : t30)[metric];
        if (!t || t.confidence === 'insufficient' || t.coverage_days < (win === '90d' ? 30 : 14)) return;
        candidates.push({
          metric,
          pattern,
          evidence_window: win,
          coverage_days: t.coverage_days,
          coverage_pct: t.coverage_pct,
          confidence: t.confidence,
          variability: t.variability,
          consistency: t.consistency,
          source_coverage: (aiContext as any).trends_medium_30d?.sources_used ?? [],
          why_it_matters: why,
          status: 'pending_review',
        });
      }
      // Pattern: 30d HRV worsening with non-trivial coverage.
      if (t30?.hrv_ms?.direction === 'worsening' && t30?.hrv_ms?.confidence !== 'low') {
        pushCandidate('hrv_ms', '30d_worsening', '30d', 'A 30-day HRV downtrend usually precedes recovery debt; worth flagging if it persists.');
      }
      // Pattern: 30d RHR rising — same idea, opposite direction polarity.
      if (t30?.rhr_bpm?.direction === 'worsening' && t30?.rhr_bpm?.confidence !== 'low') {
        pushCandidate('rhr_bpm', '30d_rising_rhr', '30d', 'A persistent RHR rise alongside flat strain often signals accumulated fatigue or under-recovery.');
      }
      // Pattern: chronic sleep shortage.
      if (t30?.sleep_hours?.direction === 'worsening' || (t30?.sleep_hours?.mean != null && t30.sleep_hours.mean < 7)) {
        pushCandidate('sleep_hours', '30d_short_sleep', '30d', 'Average sleep below 7 h over 30 days correlates with HRV/RHR drift in your data.');
      }
      // Pattern: 90d bodyweight drift (either direction).
      if (t90?.bodyweight_kg && t90.bodyweight_kg.direction !== 'flat' && t90.bodyweight_kg.confidence === 'high') {
        pushCandidate('bodyweight_kg', `90d_bodyweight_${t90.bodyweight_kg.direction}`, '90d', 'A 90-day bodyweight trend is a stable signal worth confirming with the user.');
      }
      // Pattern: 90d strain trend (either direction, high-confidence only).
      if (t90?.day_strain && t90.day_strain.direction !== 'flat' && t90.day_strain.confidence === 'high') {
        pushCandidate('day_strain', `90d_strain_${t90.day_strain.direction}`, '90d', 'Sustained strain change over 90 days reflects a real training-load shift.');
      }
      (aiContext as any).memory_candidates = candidates;

      // ── Cost / context-size guard ───────────────────────────────
      // Caps already in place: getNormalizedRecent(95) bounds rows.
      // Surface a size summary so we can spot regressions in tests.
      try {
        const ctxBytes = Buffer.byteLength(JSON.stringify(aiContext));
        (aiContext as any).context_size = {
          rows_loaded: sortedAsc.length,
          baseline_days: baseline.length,
          ai_context_bytes: ctxBytes,
          ai_context_kb: Math.round(ctxBytes / 1024),
          memory_candidates_count: candidates.length,
        };
      } catch { /* sizing failure is non-fatal */ }
    } catch { /* readiness/trends compute failure must not break Coach */ }

    const answer = buildCoachAnswer(question, aiContext as any, topic);
    res.status(200).json(answer);
  } catch (error) {
    res.status(500).json({
      ok: false,
      domain: 'general',
      mode: 'seed_partial',
      questionClass: 'error',
      status: 'unsupported',
      answer: {
        short: 'Coach is temporarily unavailable.',
        why: error instanceof Error ? error.message : 'Unknown error.',
        nextStep: 'Try again in a moment.',
        missingnessNote: null,
      },
      confidence: 'low',
      sourceDependencies: [],
      missingFields: ['backend_error'],
      safetyFlags: ['backend_error'],
      upgradeHint: null,
    });
  }
});

// ── Admin / Dev Control Center status ──────────────────────────
// GET /api/athlete-memory/admin/status
//
// Read-only summary for the in-app Admin/Dev Control Center. Returns
// booleans / counts / public links only — no env values, no token
// strings, no PHI. Protected by `requireAdminToken` (token-only;
// the per-athlete JWT/ownership gate doesn't apply to admin routes).
//
// Workflow allowlist + dispatch endpoint live further down; the
// allowlist is the source of truth for what the app can trigger.
const ADMIN_WORKFLOW_ALLOWLIST = [
  'mobile-typecheck',
  'android-aab-build',
  'ios-testflight-build',
  'backend-smoke',
  'release-audit',
  'ota-diagnostic',
] as const;

function requireAdminToken(req: any, res: any, next: any) {
  const expected = process.env.ATHLETE_MEMORY_API_TOKEN;
  if (!expected) {
    res.status(503).json({ ok: false, error: 'Admin routes disabled until ATHLETE_MEMORY_API_TOKEN is configured.' });
    return;
  }
  if (req.header('x-athlete-memory-token') !== expected) {
    res.status(403).json({ ok: false, error: 'Forbidden admin access.' });
    return;
  }
  next();
}

router.get('/admin/status', requireAdminToken, async (_req: any, res: any) => {
  try {
    const blockers: string[] = [];
    const dispatchAvailable = !!process.env.GITHUB_DISPATCH_TOKEN && !!process.env.GITHUB_REPO;
    if (!process.env.GITHUB_DISPATCH_TOKEN) blockers.push('GITHUB_DISPATCH_TOKEN not set on backend; workflow triggers disabled.');
    if (!process.env.GITHUB_REPO) blockers.push('GITHUB_REPO not set on backend (e.g. "aarontmaher/lauburu-grappling-map").');
    res.status(200).json({
      ok: true,
      backendHealthy: true,
      aiHealthContextAvailable: true,
      githubDispatchAvailable: dispatchAvailable,
      workflowDispatchAvailable: dispatchAvailable,
      workflowAllowlist: ADMIN_WORKFLOW_ALLOWLIST,
      // Per-workflow availability — true when dispatch is wired AND
      // the workflow id is on the allowlist. Does NOT verify the
      // workflow file exists on the repo (that's a GitHub-side check
      // at dispatch time) and does NOT verify GitHub Actions secrets
      // (Play/TestFlight credentials live there, never on Railway).
      androidBuildWorkflowAvailable: dispatchAvailable && (ADMIN_WORKFLOW_ALLOWLIST as readonly string[]).includes('android-aab-build'),
      iosBuildWorkflowAvailable: dispatchAvailable && (ADMIN_WORKFLOW_ALLOWLIST as readonly string[]).includes('ios-testflight-build'),
      releaseAuditWorkflowAvailable: dispatchAvailable && (ADMIN_WORKFLOW_ALLOWLIST as readonly string[]).includes('release-audit'),
      // We never read GitHub Actions secret values — these flags are
      // unknown from the backend. The UI surfaces them as "unknown"
      // and tells the user to confirm the secret in GitHub.
      playUploadConfigured: null,
      testflightSubmitConfigured: null,
      // Group-assignment is now wired on the iOS side via
      // eas.json submit.production.ios.groups (default ["Team (Expo)"]).
      // Backend can't read eas.json from disk in production (no
      // working-tree mount), so this is a static `true` reflecting
      // the repo state at deploy time. Update if eas.json changes.
      testflightGroupAssignmentConfigured: true,
      // Android upload runs as DRAFT release (eas.json
      // submit.production.android.releaseStatus = 'draft') — Play
      // accepts the upload, but per-release Review/Start-rollout
      // remains a manual Play Console click until the listing is
      // fully filled and you opt in to COMPLETED status.
      androidPlayPromoteAutomatic: false,
      otaAvailable: false,
      otaBlocked: true,
      otaBlockerReason: 'Expo SDK 54 publishes are server-rejected. Use Play / TestFlight native updates.',
      links: {
        expoProject: 'https://expo.dev/accounts/aaronmaher/projects/lauburu-grappling-map',
        railwayDashboard: 'https://railway.com/project',
        playConsole: 'https://play.google.com/console',
        appStoreConnect: 'https://appstoreconnect.apple.com/',
        githubRepo: process.env.GITHUB_REPO ? `https://github.com/${process.env.GITHUB_REPO}` : null,
        githubActions: process.env.GITHUB_REPO ? `https://github.com/${process.env.GITHUB_REPO}/actions` : null,
      },
      blockers,
      generatedAt: new Date().toISOString(),
    });
  } catch (error) {
    res.status(500).json({ ok: false, error: error instanceof Error ? error.message : 'unknown' });
  }
});

// GET /api/athlete-memory/admin/work-status
//
// Connector-shaped read-only summary of the project's owner-side
// state. Designed to be the structured source of truth that
// ChatGPT / Claude / Codex connectors read via a single GET, with
// the same `requireAdminToken` gate as the rest of /admin.
//
// CONTRACT: response shape never includes env values, secret
// strings, raw athlete health rows, OAuth tokens, or per-tester
// PII. Field values are short, structured, and stable across
// deploys. New fields can be added at the end; existing fields
// never change meaning.
//
// See docs/CONNECTOR_BACKLOG_TOOLS_PLAN.md for the wider tool spec
// and docs/RAILWAY_CONNECTOR_TOOLS.md for the curl examples.
router.get('/admin/work-status', requireAdminToken, async (_req: any, res: any) => {
  try {
    const dispatchAvailable = !!process.env.GITHUB_DISPATCH_TOKEN && !!process.env.GITHUB_REPO;
    res.status(200).json({
      ok: true,
      generatedAt: new Date().toISOString(),
      // Owner-curated current-state strings. The mobile Admin/Dev
      // chips read the same values from
      // `apps/mobile/src/store/owner-workflow-store.ts` — backend
      // copy is the durable mirror so connectors don't need to
      // fetch the device. Updated by repo deploys for now;
      // POST /admin/work-status (write tool) lands in the second
      // wave per CONNECTOR_BACKLOG_TOOLS_PLAN.md.
      currentPriority:
        'Apple Health (iPhone) + Health Connect (Android) usable for daily testing. Free-tier gate removed; ships in v15 / Build 16.',
      currentBlocker:
        'None code-side. Awaiting tester-device confirmation that the un-gated primary health cards surface and connect cleanly.',
      nextAction:
        'Aaron + girlfriend install v15 / Build 16 → confirm Apple Health / Health Connect cards visible and connectable. Reply with metrics that surface and which say missing.',
      androidReleaseStatus: {
        testerLive: 'v14 (auto-promoted via run 25361589282)',
        autoPromote: 'proven',
        eaSubmitTrack: 'internal',
        releaseStatus: 'completed',
        latestDispatch: { runId: '25384901407', state: 'in_progress', versionCode: 15 },
      },
      iosReleaseStatus: {
        testerLive: 'Build 14 (TestFlight) / Build 15 processing',
        autoSubmit: 'live (TestFlight auto-group Team (Expo))',
        latestDispatch: { runId: '25384907135', state: 'in_progress', buildNumber: 16 },
        healthKitMacVisionWarningFix: 'shipped on Build 15',
      },
      healthSourceStatus: {
        appleHealth: 'live (iOS only) — primary card un-gated from free tier',
        healthConnect: 'live (Android only) — primary card un-gated from free tier',
        whoopDirect: 'planned — direct dev-portal app not registered yet; raw 404 surface fixed in commit a036fd5',
        polarDirect: 'planned — same upstream state',
        whoopCsv: 'live (historical backfill upload)',
        polarExport: 'live (historical backfill upload)',
        cronometer: 'scaffold (UI not wired)',
      },
      adminDevStatus: {
        ownerFabRule: 'live (FabsGate hides Feedback for owner email)',
        primaryActions: 'Build Android + upload, Build iOS + submit, Run typecheck, Run release audit',
        promptBridge: 'live (5 deterministic templates + tmux instructions)',
        backlogQuickCapture: 'live (local secure-storage; backend sync deferred)',
        workflowDispatchAvailable: dispatchAvailable,
        otaBlocked: true,
        otaBlockerReason: 'Expo SDK 54 publishes are server-rejected. Use Play / TestFlight native updates.',
      },
      feedbackSummary: {
        endpoint: '/api/feedback (public POST, admin-gated GET)',
        recentRouteAdminGated: true,
        attachmentsAdminGated: true,
        approxRecordCount: null, // future: count files in FEEDBACK_DIR
      },
      backlogSummary: {
        ownerLocalStore: 'apps/mobile/src/store/owner-backlog-store.ts (local secure-storage)',
        backendSync: 'deferred (see docs/CONNECTOR_BACKLOG_TOOLS_PLAN.md)',
      },
      manualSteps: [
        'Watch v15 + Build 16 to green; install on tester devices',
        'Confirm Apple Health (Aaron) + Health Connect (girlfriend) primary cards visible without member gate',
        'Reply with which metrics surface and which say missing',
      ],
      canDeleteFromNotes: [
        'Auto-update lane / Play Console listing pass / phone screenshots / releaseStatus flip / proof workflow / tester device verification — all DONE',
        'Why girlfriend cannot see Health Connect — root cause was the free-tier gate; fix on main',
      ],
      doNotDeleteYet: [
        'Verify v15 + Build 16 land on real devices and the un-gated Health cards surface',
        'Cautious early Grappler Readiness prototype (provisional label, low/medium/high confidence)',
        'Health Connect Play-Store-deep-link install hint when SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED',
        'Grappler Readiness Batches B/C/D',
        'Admin/Dev Railway MCP-style read-only bridge (this route is the first iteration)',
        'AI provider implementation — gated',
        'Public production release — out of scope until production listing pass is done',
      ],
      // Reserved future fields — connector tools will fill these
      // as they land. Listed in the response so connectors can
      // probe presence without retry loops.
      reserved: {
        priorityDraft: null,
        backlogReadRoute: '/api/athlete-memory/admin/backlog (TODO)',
        handoffReadRoute: '/api/athlete-memory/admin/handoff (TODO)',
        backlogWriteRoute: 'POST /api/athlete-memory/admin/backlog (TODO — second wave)',
      },
    });
  } catch (error) {
    res.status(500).json({ ok: false, error: error instanceof Error ? error.message : 'unknown' });
  }
});

// POST /api/athlete-memory/admin/workflows/:workflowId/dispatch
//
// Stub endpoint. Returns 503 until GITHUB_DISPATCH_TOKEN + GITHUB_REPO
// are configured on the backend. When configured, will POST to
// `https://api.github.com/repos/<owner>/<repo>/actions/workflows/<id>.yml/dispatches`
// with the bearer token. Workflow ID must be on the allowlist.
router.post('/admin/workflows/:workflowId/dispatch', requireAdminToken, async (req: any, res: any) => {
  const { workflowId } = req.params;
  const ref = (req.body?.ref as string | undefined) ?? 'main';
  if (!(ADMIN_WORKFLOW_ALLOWLIST as readonly string[]).includes(workflowId)) {
    res.status(400).json({ ok: false, error: 'Unknown workflow id.' });
    return;
  }
  const token = process.env.GITHUB_DISPATCH_TOKEN;
  const repo = process.env.GITHUB_REPO;
  if (!token || !repo) {
    res.status(503).json({
      ok: false,
      error: 'Workflow dispatch not configured on backend.',
      needs: ['GITHUB_DISPATCH_TOKEN', 'GITHUB_REPO'],
    });
    return;
  }
  try {
    const url = `https://api.github.com/repos/${repo}/actions/workflows/${encodeURIComponent(workflowId)}.yml/dispatches`;
    const resp = await fetch(url, {
      method: 'POST',
      headers: {
        'authorization': `Bearer ${token}`,
        'accept': 'application/vnd.github+json',
        'content-type': 'application/json',
        'x-github-api-version': '2022-11-28',
      },
      body: JSON.stringify({ ref, inputs: req.body?.inputs ?? {} }),
    });
    if (!resp.ok) {
      const text = await resp.text().catch(() => '');
      console.warn(`[admin-dispatch] workflow=${workflowId} ref=${ref} status=${resp.status}`);
      res.status(502).json({ ok: false, error: `GitHub dispatch failed (${resp.status})`, detail: text.slice(0, 500) });
      return;
    }
    // Audit line — token never logged. Repo is public knowledge.
    console.log(`[admin-dispatch] workflow=${workflowId} ref=${ref} repo=${repo} ok=true`);
    res.status(200).json({
      ok: true,
      workflowId,
      ref,
      dispatchedAt: new Date().toISOString(),
      actionsUrl: `https://github.com/${repo}/actions/workflows/${encodeURIComponent(workflowId)}.yml`,
    });
  } catch (error) {
    res.status(500).json({ ok: false, error: error instanceof Error ? error.message : 'unknown' });
  }
});

// ── Polar export historical training-context import ───────────
// POST /api/athlete-memory/:athleteId/polar-export/import
//
// Body: { sessions: PolarSession[] } (PolarSession shape from
// packages/shared/src/backend/services/polar/parse-polar-export).
//
// Storage: writes a JSON file per session under
//   athletes/<athleteId>/api-ai/polar_export_sessions/<startISO>.json
// keyed by ISO start time. Dedupe is by (athleteId, startTime, sport)
// — re-importing the same session is a no-op. Polar export is
// historical training context only — not a recovery / readiness
// signal. App-owned Lauburu Readiness remains product truth.
router.post('/:athleteId/polar-export/import', requirePrivateAthleteAccess, async (req: any, res: any) => {
  try {
    const { athleteId } = req.params;
    const sessions = Array.isArray(req.body?.sessions) ? req.body.sessions : [];
    if (sessions.length === 0) {
      res.status(400).json({ ok: false, error: 'No sessions in request body.' });
      return;
    }

    // Soft cap to prevent a single request from writing thousands of
    // files in one go. Real Polar exports are usually <200 sessions.
    if (sessions.length > 1000) {
      res.status(413).json({ ok: false, error: 'Too many sessions in one request (max 1000).' });
      return;
    }

    const seen = new Set<string>();
    let imported = 0;
    let deduped = 0;
    let skipped = 0;
    const errors: string[] = [];

    for (const raw of sessions) {
      try {
        const startTime = typeof raw?.startTime === 'string' ? raw.startTime : null;
        const sport = typeof raw?.sport === 'string' ? raw.sport : null;
        if (!startTime) { skipped += 1; continue; }
        const key = `${startTime}__${sport ?? 'unknown'}`;
        if (seen.has(key)) { deduped += 1; continue; }
        seen.add(key);
        // Dedupe vs. storage: best-effort idempotency. Filename keyed
        // by start time + sport — same session reimported is no-op.
        const safeKey = key.replace(/[^A-Za-z0-9._-]/g, '_');
        const path = `athletes/${athleteId}/api-ai/polar_export_sessions/${safeKey}.json`;
        const existing = await (store as any).readJson?.(path).catch(() => null);
        if (existing) { deduped += 1; continue; }
        const record = {
          ...raw,
          source: 'polar_export',
          ingestedAt: new Date().toISOString(),
          athleteId,
        };
        await (store as any).writeJson?.(path, record);
        imported += 1;
      } catch (e: any) {
        errors.push(e?.message ?? 'unknown');
      }
    }

    res.status(200).json({
      ok: true,
      imported,
      deduped,
      skipped,
      total_received: sessions.length,
      errors: errors.slice(0, 5),
      note: 'Polar export sessions stored as historical training context only. Recovery/Readiness still uses your other sources.',
    });
  } catch (error) {
    res.status(500).json({
      ok: false,
      error: 'Polar export import failed.',
      detail: error instanceof Error ? error.message : 'unknown',
    });
  }
});

export default router;
