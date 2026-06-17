/**
 * Backlog analysis orchestrator — runs the first-run "what I can tell
 * so far" pipeline for a single athlete within an explicit window,
 * using ONLY records belonging to that athlete.
 *
 * Wiring:
 *   caller → runBacklogAnalysis({ userId, athleteId, windowStart,
 *                                  windowEnd, sources?, dryRun? })
 *   service → reads normalized days + HIIT sessions + source-health
 *     for THIS athleteId only
 *   service → calls findTrendCandidates + buildBacklogCohortComparison
 *   service → optionally builds + persists daily artifacts for days
 *     missing them (unless dryRun)
 *   service → optionally builds + persists weekly synthesis artifacts
 *     for complete ISO weeks in-window (unless dryRun)
 *   service → returns a status row, a summary, and the trend
 *     candidates — never touches stable memory.
 *
 * The service takes an injected `BacklogStore` so tests can drive it
 * with fakes. Production wires this to the real FileApiAiStateStore.
 */

import type { NormalizedDailyMetrics } from '../../contracts/normalized-daily.types';
import type { DailyRefreshArtifact, WeeklySynthesisArtifact } from '../../contracts/refresh-artifacts.types';
import type { SourceHealthStatus } from '../../contracts/freshness.types';
import type { HIITWorkoutRecord } from '../../../types/hiit-workout';
import type {
  BacklogAnalysisStatusRecord,
  BacklogInitialSummary,
  BacklogSourceDiscovery,
  BacklogTrendCandidate,
  RunBacklogAnalysisInput,
  RunBacklogAnalysisResult,
} from '../../contracts/backlog-analysis.types';
import type { AthletePhysiologyBaseline } from '../../../athlete-memory/types';
import { findTrendCandidates } from './find-trend-candidates';
import { buildBacklogCohortComparison } from './build-cohort-comparison';

/**
 * Minimal store surface the backlog service needs. Production binds
 * this to the full athlete-memory store; tests can pass an in-memory
 * fake. All methods are athleteId-keyed — the surface intentionally
 * has no "all athletes" read to make accidental cross-user access
 * impossible by construction.
 */
export interface BacklogStore {
  getNormalizedDay(athleteId: string, date: string): Promise<NormalizedDailyMetrics | null>;
  listDailyRefreshes(
    athleteId: string,
    opts?: { startDate?: string; endDate?: string },
  ): Promise<DailyRefreshArtifact[]>;
  getLatestWeeklySynthesis(athleteId: string): Promise<WeeklySynthesisArtifact | null>;
  saveDailyRefresh(athleteId: string, artifact: DailyRefreshArtifact): Promise<void>;
  saveWeeklySynthesis(athleteId: string, artifact: WeeklySynthesisArtifact): Promise<void>;
  getSourceHealth(athleteId: string, provider: string): Promise<SourceHealthStatus | null>;
  listHiitSessions(
    athleteId: string,
    opts?: { startDate?: string; endDate?: string },
  ): Promise<HIITWorkoutRecord[]>;
  getBaseline(athleteId: string): Promise<AthletePhysiologyBaseline | null>;
  loadNormalizedRange(
    athleteId: string,
    startDate: string,
    endDate: string,
  ): Promise<NormalizedDailyMetrics[]>;
  saveBacklogStatus(athleteId: string, record: BacklogAnalysisStatusRecord): Promise<void>;
  saveBacklogSummary(athleteId: string, summary: BacklogInitialSummary): Promise<void>;
  saveBacklogTrendCandidates(athleteId: string, trends: BacklogTrendCandidate[]): Promise<void>;
}

/**
 * Builders are injected so the service doesn't take a hard build-time
 * dep on every pure-function pipeline file. Keeps the service layer
 * composable and keeps the trend-detection logic testable in
 * isolation.
 */
export interface BacklogBuilders {
  buildDailyRefreshArtifact: (input: {
    today: NormalizedDailyMetrics;
    recent3Days: NormalizedDailyMetrics[];
    baseline: AthletePhysiologyBaseline;
  }) => DailyRefreshArtifact;
  buildWeeklySynthesisArtifact: (input: {
    athleteId: string;
    weekStart: string;
    weekEnd: string;
    dailyArtifacts: DailyRefreshArtifact[];
    baseline: AthletePhysiologyBaseline;
  }) => WeeklySynthesisArtifact;
}

function dateList(start: string, end: string): string[] {
  const out: string[] = [];
  const s = new Date(start + 'T00:00:00Z').getTime();
  const e = new Date(end + 'T00:00:00Z').getTime();
  for (let t = s; t <= e; t += 86_400_000) {
    out.push(new Date(t).toISOString().slice(0, 10));
  }
  return out;
}

function addDaysIso(iso: string, delta: number): string {
  return new Date(new Date(iso + 'T00:00:00Z').getTime() + delta * 86_400_000)
    .toISOString()
    .slice(0, 10);
}

/**
 * ISO-week Monday (start) + Sunday (end) for the date. Returns both
 * as YYYY-MM-DD. Uses UTC to avoid DST boundary weirdness.
 */
function isoWeekBounds(dateIso: string): { start: string; end: string } {
  const d = new Date(dateIso + 'T00:00:00Z');
  const dow = d.getUTCDay(); // 0 (Sun) .. 6 (Sat)
  const mondayOffset = dow === 0 ? -6 : 1 - dow;
  const monday = addDaysIso(dateIso, mondayOffset);
  const sunday = addDaysIso(monday, 6);
  return { start: monday, end: sunday };
}

/**
 * Infer the BacklogSourceDiscovery[] from source-health rows that
 * exist for THIS athleteId. Never reads across athletes.
 */
export async function discoverAthleteSources(
  store: BacklogStore,
  athleteId: string,
): Promise<BacklogSourceDiscovery[]> {
  const provs = [
    'whoop',
    'apple_health',
    'health_connect',
    'polar_via_health_connect',
    'polar',
    'cronometer',
    'manual',
  ] as const;
  const rows = await Promise.all(provs.map((p) => store.getSourceHealth(athleteId, p)));
  const out: BacklogSourceDiscovery[] = [];
  provs.forEach((provider, i) => {
    const row = rows[i];
    if (!row) {
      out.push({
        source: provider,
        state: 'not_connected',
        sourceApp: null,
        domainsAvailable: [],
        reason: `No ${provider} source-health record found.`,
      });
      return;
    }
    const domains = Object.entries(row.coverageByDomain ?? {})
      .filter(([, v]) => (v as any)?.status === 'fresh' || (v as any)?.status === 'stale')
      .map(([k]) => k);
    let state: BacklogSourceDiscovery['state'];
    if (row.freshnessStatus === 'fresh') state = 'connected';
    else if (row.freshnessStatus === 'stale') state = 'stale';
    else if (row.freshnessStatus === 'expired') state = 'sync_needed';
    else if (domains.length > 0) state = 'partial';
    else state = 'not_connected';
    const sourceApp = provider === 'polar_via_health_connect' && row.degradedReason?.startsWith('sourceApp:')
      ? row.degradedReason.slice('sourceApp:'.length).trim()
      : null;
    out.push({
      source: provider,
      state,
      sourceApp,
      domainsAvailable: domains,
      reason: row.degradedReason,
    });
  });
  return out;
}

function summaryFromData(
  athleteId: string,
  normalizedDays: NormalizedDailyMetrics[],
  hiitSessions: HIITWorkoutRecord[],
  trends: BacklogTrendCandidate[],
  sourceDiscovery: BacklogSourceDiscovery[],
  hasDirectWhoopData: boolean,
): BacklogInitialSummary {
  const now = new Date().toISOString();

  const countBy = (predicate: (d: NormalizedDailyMetrics) => boolean) =>
    normalizedDays.filter(predicate).length;

  const earlyPatterns: string[] = [];
  for (const t of trends) {
    if (t.confidence !== 'low' || t.observationCount >= 3) {
      earlyPatterns.push(t.statement);
    }
  }
  if (earlyPatterns.length === 0) {
    earlyPatterns.push('No patterns have enough evidence yet — keep logging and sync more sources.');
  }

  const whatsMissing: string[] = [];
  for (const src of sourceDiscovery) {
    if (src.state === 'not_connected' || src.state === 'permission_required' || src.state === 'sync_needed' || src.state === 'unavailable') {
      whatsMissing.push(`${src.source}: ${src.state.replace('_', ' ')}${src.reason ? ` (${src.reason})` : ''}`);
    }
  }
  if (!hasDirectWhoopData) {
    whatsMissing.push('Direct WHOOP recovery/HRV/strain: not live — readiness clearance is blocked until these arrive.');
  }

  const safeNextSteps: string[] = [];
  const hcRow = sourceDiscovery.find((s) => s.source === 'health_connect');
  if (hcRow && hcRow.state !== 'connected') {
    safeNextSteps.push('Sync Health Connect on Android for sleep, workouts, and heart-rate context.');
  }
  const nutRow = sourceDiscovery.find((s) => s.source === 'cronometer');
  if (nutRow && nutRow.state !== 'connected') {
    safeNextSteps.push('Log food (manual or barcode is fine) to build nutrition context.');
  }
  if (hiitSessions.length < 3) {
    safeNextSteps.push('Log a few HIIT sessions so Coach can compare watts/HR across time.');
  }
  if (safeNextSteps.length === 0) {
    safeNextSteps.push('Keep logging. Coach will sharpen as more days arrive.');
  }

  const reviewableMemoryCandidateIds = trends.filter((t) => t.eligibleForMemoryProposal).map((t) => t.id);
  const comparison = buildBacklogCohortComparison(trends);

  const confidence: 'low' | 'medium' | 'high' =
    normalizedDays.length >= 21 && hiitSessions.length >= 4 ? 'medium' :
    normalizedDays.length >= 7 ? 'low' : 'low';

  return {
    id: `backlog_summary_${athleteId}_${now}`,
    athleteId,
    generatedAt: now,
    dataFound: {
      normalizedDays: normalizedDays.length,
      healthConnectDays: countBy((d) => d.provider === 'health_connect' || d.provider === 'mixed'),
      appleHealthDays: countBy((d) => d.provider === 'apple_health'),
      polarViaHealthConnectDays: countBy((d) => d.provider === 'polar_via_health_connect'),
      whoopDays: countBy((d) => typeof d.recoveryScore === 'number' || typeof d.hrvMs === 'number' || typeof d.dailyStrain === 'number'),
      cronometerDays: countBy((d) => typeof d.nutritionCalories === 'number' && d.provider === 'cronometer'),
      manualNutritionDays: countBy((d) => typeof d.nutritionCalories === 'number' && d.provider === 'manual'),
      hiitSessions: hiitSessions.length,
      grapplingSessions: normalizedDays.reduce((a, d) => a + (d.grapplingSessionCount ?? 0), 0),
    },
    earlyPatterns,
    whatsMissing,
    safeNextSteps,
    reviewableMemoryCandidateIds,
    comparison,
    confidence,
  };
}

/**
 * The main service. Always privacy-scoped to the single athleteId
 * passed in — every read that touches storage goes through the
 * BacklogStore which is athleteId-keyed on every method.
 */
export async function runBacklogAnalysis(
  input: RunBacklogAnalysisInput,
  store: BacklogStore,
  builders: BacklogBuilders | null,
): Promise<RunBacklogAnalysisResult> {
  const now = new Date().toISOString();
  const { userId, athleteId, windowStart, windowEnd, dryRun, historyScope } = input;

  // Discover what sources are usable for this athlete specifically.
  const sources = await discoverAthleteSources(store, athleteId);
  const sourcesIncluded = sources.filter((s) => s.state === 'connected' || s.state === 'partial' || s.state === 'stale').map((s) => s.source);
  const sourcesMissing = sources.filter((s) => s.state === 'not_connected' || s.state === 'permission_required' || s.state === 'sync_needed' || s.state === 'unavailable').map((s) => s.source);

  let normalizedDays: NormalizedDailyMetrics[] = [];
  try {
    normalizedDays = await store.loadNormalizedRange(athleteId, windowStart, windowEnd);
  } catch {
    normalizedDays = [];
  }

  let hiitSessions: HIITWorkoutRecord[] = [];
  try {
    hiitSessions = await store.listHiitSessions(athleteId, { startDate: windowStart, endDate: windowEnd });
  } catch {
    hiitSessions = [];
  }

  // hasDirectWhoopData gate — require direct WHOOP source-health fresh
  // AND normalized days containing at least one recoveryScore. Polar
  // via HC and generic HC never flip this gate.
  const whoopRow = await store.getSourceHealth(athleteId, 'whoop');
  const hasFreshWhoopSource = whoopRow?.freshnessStatus === 'fresh';
  const hasAnyRecoveryDay = normalizedDays.some((d) => typeof d.recoveryScore === 'number');
  const hasDirectWhoopData = hasFreshWhoopSource && hasAnyRecoveryDay;

  const hasGrapplingSessions = normalizedDays.some((d) => (d.grapplingSessionCount ?? 0) > 0);

  const trends = findTrendCandidates({
    athleteId,
    windowStart,
    windowEnd,
    normalizedDays,
    hiitSessions,
    hasDirectWhoopData,
    hasGrapplingSessions,
  });

  let dailyArtifactsCreated = 0;
  let weeklyArtifactsCreated = 0;

  // Build missing daily artifacts when requested (non-dry) and when a
  // baseline + builders are available. Without a baseline the daily
  // refresh builder cannot safely produce dayState/dayScore.
  const baseline = await store.getBaseline(athleteId);
  if (!dryRun && builders && baseline) {
    const existing = await store.listDailyRefreshes(athleteId, { startDate: windowStart, endDate: windowEnd });
    const existingByDate = new Set(existing.map((a) => a.sourceDate));
    const sorted = [...normalizedDays].sort((a, b) => a.date.localeCompare(b.date));
    const byDate = new Map(sorted.map((d) => [d.date, d] as const));

    for (const day of sorted) {
      if (existingByDate.has(day.date)) continue;
      // Build last-3-days context from in-memory sorted window.
      const idx = sorted.indexOf(day);
      const recent3Days: NormalizedDailyMetrics[] = [];
      for (let j = idx - 3; j < idx; j++) {
        if (j >= 0) recent3Days.push(sorted[j]);
      }
      try {
        const artifact = builders.buildDailyRefreshArtifact({
          today: day,
          recent3Days,
          baseline,
        });
        await store.saveDailyRefresh(athleteId, artifact);
        dailyArtifactsCreated += 1;
      } catch {
        // Per-day failure is not fatal — continue with the rest.
      }
    }

    // Weekly synthesis for every complete ISO week fully inside the window.
    const dates = dateList(windowStart, windowEnd);
    const weekKeys = new Set<string>();
    for (const d of dates) {
      const { start, end } = isoWeekBounds(d);
      if (start < windowStart || end > windowEnd) continue; // only complete weeks
      weekKeys.add(`${start}|${end}`);
    }

    // Re-read daily artifacts once the backfill has run, so weekly
    // synthesis can draw on freshly-built days.
    const allDailyArtifacts = await store.listDailyRefreshes(athleteId, { startDate: windowStart, endDate: windowEnd });
    const byArtifactDate = new Map(allDailyArtifacts.map((a) => [a.sourceDate, a]));
    for (const key of weekKeys) {
      const [weekStart, weekEnd] = key.split('|');
      const weekDates = dateList(weekStart, weekEnd);
      const dailyArtifacts = weekDates
        .map((dt) => byArtifactDate.get(dt))
        .filter((x): x is DailyRefreshArtifact => Boolean(x));
      if (dailyArtifacts.length === 0) continue;
      try {
        const artifact = builders.buildWeeklySynthesisArtifact({
          athleteId,
          weekStart,
          weekEnd,
          dailyArtifacts,
          baseline,
        });
        await store.saveWeeklySynthesis(athleteId, artifact);
        weeklyArtifactsCreated += 1;
      } catch {
        // Per-week failure is not fatal.
      }
    }
  }

  // Persist trend candidates first so the summary can reference them.
  if (!dryRun && trends.length > 0) {
    try {
      await store.saveBacklogTrendCandidates(athleteId, trends);
    } catch {
      // Non-fatal — summary still returns in memory.
    }
  }

  const summary = summaryFromData(athleteId, normalizedDays, hiitSessions, trends, sources, hasDirectWhoopData);

  let status: BacklogAnalysisStatusRecord['status'] = 'complete';
  if (normalizedDays.length === 0 && hiitSessions.length === 0) status = 'partial';
  if (sourcesMissing.length > sourcesIncluded.length && normalizedDays.length < 7) status = 'partial';

  const statusRecord: BacklogAnalysisStatusRecord = {
    userId,
    athleteId,
    status,
    consentGrantedAt: now,
    analysisStartedAt: now,
    analysisCompletedAt: now,
    windowStart,
    windowEnd,
    sourcesIncluded,
    sourcesMissing,
    recordsAnalysed: normalizedDays.length + hiitSessions.length,
    dailyArtifactsCreated,
    weeklyArtifactsCreated,
    patternCandidatesCreated: trends.length,
    memoryProposalsCreated: trends.filter((t) => t.eligibleForMemoryProposal).length,
    missingnessNote:
      normalizedDays.length === 0
        ? 'No normalized days in window — connect sources and sync, then re-run.'
        : dailyArtifactsCreated === 0 && !dryRun && !baseline
          ? 'No physiology baseline on file — daily artifacts could not be built. Baseline requires at least 3 normalized days with recovery fields.'
          : historyScope === 'limited_history'
            ? 'Health Connect history access is limited to ~30 days. Grant full history permission for deeper analysis.'
            : null,
    historyScope: historyScope ?? 'unknown',
    latestSummaryId: summary.id,
    createdAt: now,
    updatedAt: now,
  };

  if (!dryRun) {
    try {
      await store.saveBacklogStatus(athleteId, statusRecord);
    } catch {
      // Status save failures surface on the next status-read.
    }
    try {
      await store.saveBacklogSummary(athleteId, summary);
    } catch {
      // Non-fatal — summary still returned to caller in memory.
    }
  }

  return {
    status: statusRecord,
    summary,
    trendCandidates: trends,
  };
}
