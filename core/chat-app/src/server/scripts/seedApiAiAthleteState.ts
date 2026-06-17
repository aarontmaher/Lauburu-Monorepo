import { promises as fs } from 'fs';
import path from 'path';
import type { DailyMetrics, AthleteMemoryRecord } from '@lauburu/shared';
import type { AthleteObservedPattern } from '../../../../packages/shared/src/athlete-memory/types';
import type { SourceHealthStatus } from '../../../../packages/shared/src/backend/contracts/freshness.types';
import type { DailyRefreshArtifact, WeeklySynthesisArtifact } from '../../../../packages/shared/src/backend/contracts/refresh-artifacts.types';
import type { NormalizedDailyMetrics } from '../../../../packages/shared/src/backend/contracts/normalized-daily.types';
import type { WhoopDailyMetricsRaw } from '../../../../packages/shared/src/backend/contracts/whoop-raw.types';
import type {
  SeededBaselineProfile,
  SeededBaselineThresholds,
  SeededCurrentBlockSummary,
  SeededRecurringPatternsCandidates,
} from '../../../../packages/shared/src/backend/contracts/seeded-athlete-state.types';
import {
  ingestWhoopBatch,
  type WhoopMcpDayPayload,
} from '../../../../packages/shared/src/backend/services/whoop/ingest-whoop';
import { normalizeWhoopBatch } from '../../../../packages/shared/src/backend/services/normalize/normalize-daily-metrics';
import { buildDailyRefreshArtifact } from '../../../../packages/shared/src/backend/services/refresh/build-daily-refresh';
import { buildWeeklySynthesisArtifact } from '../../../../packages/shared/src/backend/services/refresh/build-weekly-synthesis';

interface Manifest {
  athleteId: string;
  timezone: string;
}

interface SeedResult {
  athleteId: string;
  baseDir: string;
  latestDate: string;
  weekKey: string;
  missingSourceCaveats: string[];
  writtenPaths: string[];
}

function repoRoot() {
  const cwd = process.cwd();
  return cwd.endsWith(path.sep + 'chat-app')
    ? cwd
    : path.join(cwd, 'chat-app');
}

function athleteBaseDir(athleteId: string) {
  return path.join(repoRoot(), 'data', 'private-athlete-memory', athleteId);
}

function isoNow() {
  return new Date().toISOString();
}

function startOfWeek(date: string): string {
  const d = new Date(`${date}T00:00:00.000Z`);
  const day = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() - day + 1);
  return d.toISOString().slice(0, 10);
}

function enumerateDateRange(startDate: string, endDate: string): string[] {
  const dates: string[] = [];
  const cursor = new Date(`${startDate}T00:00:00.000Z`);
  const end = new Date(`${endDate}T00:00:00.000Z`);
  while (cursor <= end) {
    dates.push(cursor.toISOString().slice(0, 10));
    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }
  return dates;
}

async function readJson<T>(filePath: string): Promise<T> {
  const raw = await fs.readFile(filePath, 'utf8');
  return JSON.parse(raw) as T;
}

async function writeJson(filePath: string, value: unknown): Promise<void> {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

function toWhoopSeedPayloads(
  history: DailyMetrics[],
  timezone: string,
): WhoopMcpDayPayload[] {
  return history
    .filter((day) => day.provider === 'whoop')
    .map((day) => ({
      local_date: day.date,
      timezone,
      recovery_score: day.recovery_score ?? null,
      hrv_ms: day.hrv_ms ?? null,
      rhr_bpm: day.resting_hr ?? null,
      spo2_pct: day.spo2_pct ?? null,
      skin_temp_celsius: day.skin_temp_c ?? null,
      sleep_performance_pct: day.sleep_performance_pct ?? null,
      sleep_efficiency_pct: day.sleep_efficiency_pct ?? null,
      total_sleep_hours: day.sleep_hours ?? null,
      sws_hours: day.sws_hours ?? null,
      rem_hours: day.rem_hours ?? null,
      respiratory_rate: day.respiratory_rate ?? null,
      sleep_debt_hours: null,
      sleep_needed_baseline_hours: null,
      day_strain: day.daily_strain ?? null,
      day_kilojoules:
        day.active_calories != null ? Math.round(day.active_calories * 4.184) : null,
      day_avg_hr: null,
      day_max_hr: null,
      workout_count: day.workouts?.length ?? 0,
      workout_strain_total:
        day.workouts && day.workouts.length > 0
          ? day.workouts.reduce((sum, workout) => sum + (workout.strain ?? 0), 0)
          : null,
      workout_minutes_total:
        day.workouts && day.workouts.length > 0
          ? day.workouts.reduce((sum, workout) => sum + (workout.duration_min ?? 0), 0)
          : null,
      workout_details: (day.workouts ?? []).map((workout, index) => ({
        id: workout.source_id ?? `${day.date}-workout-${index + 1}`,
        sport_id: 0,
        sport_name: workout.sport_label ?? workout.type,
        strain: workout.strain ?? 0,
        avg_hr: workout.avg_hr ?? 0,
        max_hr: workout.max_hr ?? 0,
        kilojoules:
          workout.calories != null ? Math.round(workout.calories * 4.184) : 0,
        calories_kilocalories: workout.calories ?? null,
        start: workout.start_time ?? `${day.date}T00:00:00.000Z`,
        end:
          workout.end_time ??
          `${day.date}T${String(Math.min(workout.duration_min ?? 0, 23)).padStart(2, '0')}:00:00.000Z`,
        duration_min: workout.duration_min ?? 0,
        percent_recorded: null,
        hr_zones: [],
      })),
      source_updated_at: day.last_updated ?? undefined,
    }))
    .sort((a, b) => a.local_date.localeCompare(b.local_date));
}

function buildWhoopSourceHealth(
  athleteId: string,
  latestRaw: WhoopDailyMetricsRaw | null,
  missingSourceCaveats: string[],
): SourceHealthStatus {
  const now = isoNow();
  return {
    id: `source_health_whoop_${athleteId}`,
    schemaVersion: 1,
    createdAt: now,
    updatedAt: now,
    athleteId,
    provider: 'whoop',
    lastSuccessfulIngestAt: latestRaw?.sourceUpdatedAt ?? latestRaw?.updatedAt ?? null,
    lastFailedIngestAt: null,
    freshnessStatus: latestRaw ? 'stale' : 'missing',
    coverageByDomain: {
      recovery: {
        lastDate: latestRaw?.localDate ?? null,
        status: latestRaw?.recoveryScore != null ? 'stale' : 'missing',
      },
      sleep: {
        lastDate: latestRaw?.localDate ?? null,
        status: latestRaw?.totalSleepHours != null ? 'stale' : 'missing',
      },
      strain: {
        lastDate: latestRaw?.localDate ?? null,
        status: latestRaw?.dayStrain != null ? 'stale' : 'missing',
      },
      workouts: {
        lastDate: latestRaw?.localDate ?? null,
        status: latestRaw ? 'stale' : 'missing',
      },
    },
    upstreamStatus: latestRaw ? 'degraded' : 'unknown',
    degradedReason: latestRaw
      ? 'Seed pass includes WHOOP daily views through the latest cached day only; current-day live coverage is not seeded here.'
      : 'No WHOOP daily views were available in the repo seed inputs.',
  };
}

function buildAppleHealthSourceHealth(
  athleteId: string,
  missingSourceCaveats: string[],
): SourceHealthStatus {
  const now = isoNow();
  return {
    id: `source_health_apple_health_${athleteId}`,
    schemaVersion: 1,
    createdAt: now,
    updatedAt: now,
    athleteId,
    provider: 'apple_health',
    lastSuccessfulIngestAt: null,
    lastFailedIngestAt: null,
    freshnessStatus: 'missing',
    coverageByDomain: {
      recovery: { lastDate: null, status: 'missing' },
      sleep: { lastDate: null, status: 'missing' },
      activity: { lastDate: null, status: 'missing' },
      workouts: { lastDate: null, status: 'missing' },
    },
    upstreamStatus: 'unknown',
    degradedReason: missingSourceCaveats[0] ?? 'No Apple Health structured output is available in this seed pass.',
  };
}

function buildBaselineProfileSeed(
  athleteId: string,
  memory: AthleteMemoryRecord,
  missingSourceCaveats: string[],
): SeededBaselineProfile {
  return {
    athleteId,
    generatedAt: isoNow(),
    source: 'stable_memory_seed',
    baselineProfile: memory.physiologyBaseline,
    missingSourceCaveats,
  };
}

function buildBaselineThresholdsSeed(
  athleteId: string,
  memory: AthleteMemoryRecord,
  missingSourceCaveats: string[],
): SeededBaselineThresholds {
  return {
    athleteId,
    generatedAt: isoNow(),
    source: 'stable_memory_seed',
    thresholds: memory.physiologyBaseline.thresholds,
    basedOnComputedAt: memory.physiologyBaseline.computedAt,
    missingSourceCaveats,
  };
}

function buildRecurringPatternCandidatesSeed(
  athleteId: string,
  observedPatterns: AthleteObservedPattern[],
  weeklyArtifact: WeeklySynthesisArtifact,
  missingSourceCaveats: string[],
): SeededRecurringPatternsCandidates {
  const candidates = weeklyArtifact.promotionCandidates
    .filter((candidate) => candidate.targetDoc === 'recurring_patterns')
    .map((candidate, index) => ({
      key: `candidate_${index + 1}`,
      label: candidate.candidateStatement,
      observationCount: observedPatterns.find((pattern) =>
        candidate.candidateStatement.includes(pattern.key))?.observationCount ?? 0,
      confidence: candidate.evidenceStrength,
      evidenceWindow: candidate.evidenceWindow,
      eligibleForPromotion: candidate.eligible,
      caveats: [
        'Promotion candidate only; not auto-promoted into stable memory.',
      ],
    }));

  return {
    athleteId,
    generatedAt: isoNow(),
    source: 'weekly_synthesis_seed',
    candidates,
    observedPatternsSnapshot: observedPatterns,
    missingSourceCaveats,
  };
}

function buildCurrentBlockSummarySeed(
  athleteId: string,
  memory: AthleteMemoryRecord,
  latestDaily: DailyRefreshArtifact,
  latestWeekly: WeeklySynthesisArtifact,
  missingSourceCaveats: string[],
): SeededCurrentBlockSummary {
  return {
    athleteId,
    generatedAt: isoNow(),
    summary: memory.currentBlockSummary,
    confidence: latestWeekly.confidence,
    sourceDate: latestDaily.sourceDate,
    weekKey: `${latestWeekly.weekStart}__${latestWeekly.weekEnd}`,
    caveats: missingSourceCaveats,
  };
}

async function seedAthlete(athleteId: string): Promise<SeedResult> {
  const baseDir = athleteBaseDir(athleteId);
  const [manifest, metricsHistory, memory] = await Promise.all([
    readJson<Manifest>(path.join(baseDir, 'manifest.json')),
    readJson<DailyMetrics[]>(path.join(baseDir, 'metrics-history.json')),
    readJson<AthleteMemoryRecord>(path.join(baseDir, 'memory.json')),
  ]);

  const missingSourceCaveats = [
    'Apple Health structured output is not present in the repo seed inputs.',
  ];

  const whoopPayloads = toWhoopSeedPayloads(metricsHistory, manifest.timezone);
  const rawRecords = ingestWhoopBatch(whoopPayloads, athleteId);
  const normalizedRecords = normalizeWhoopBatch(rawRecords);

  const latestNormalized = normalizedRecords[normalizedRecords.length - 1];
  if (!latestNormalized) {
    throw new Error(`No normalized WHOOP records available for ${athleteId}`);
  }

  const recentDates = normalizedRecords.slice(-7).map((record) => record.date);
  const dailyArtifacts: DailyRefreshArtifact[] = [];
  for (const date of recentDates) {
    const today = normalizedRecords.find((record) => record.date === date);
    if (!today) continue;
    const recent3Days = normalizedRecords.filter(
      (record) => record.date <= date,
    ).slice(-3);
    dailyArtifacts.push(
      buildDailyRefreshArtifact({
        today,
        recent3Days,
        baseline: memory.physiologyBaseline,
      }),
    );
  }

  const latestDaily = dailyArtifacts[dailyArtifacts.length - 1];
  if (!latestDaily) {
    throw new Error(`No daily refresh artifacts could be built for ${athleteId}`);
  }

  const weekStart = startOfWeek(latestDaily.sourceDate);
  const weekEnd = latestDaily.sourceDate;
  const expectedWeekDates = enumerateDateRange(weekStart, weekEnd);
  const weekDailyArtifacts = expectedWeekDates
    .map((date) => dailyArtifacts.find((artifact) => artifact.sourceDate === date))
    .filter((artifact): artifact is DailyRefreshArtifact => artifact != null);

  const weeklyArtifact = buildWeeklySynthesisArtifact({
    athleteId,
    weekStart,
    weekEnd,
    dailyArtifacts: weekDailyArtifacts,
    baseline: memory.physiologyBaseline,
  });

  const baselineProfile = buildBaselineProfileSeed(
    athleteId,
    memory,
    missingSourceCaveats,
  );
  const baselineThresholds = buildBaselineThresholdsSeed(
    athleteId,
    memory,
    missingSourceCaveats,
  );
  const recurringPatternsCandidates = buildRecurringPatternCandidatesSeed(
    athleteId,
    memory.observedPatterns,
    weeklyArtifact,
    missingSourceCaveats,
  );
  const currentBlockSummary = buildCurrentBlockSummarySeed(
    athleteId,
    memory,
    latestDaily,
    weeklyArtifact,
    missingSourceCaveats,
  );
  const whoopHealth = buildWhoopSourceHealth(
    athleteId,
    rawRecords[rawRecords.length - 1] ?? null,
    missingSourceCaveats,
  );
  const appleHealth = buildAppleHealthSourceHealth(athleteId, missingSourceCaveats);

  const writeTargets: Array<[string, unknown]> = [];

  for (const record of rawRecords) {
    writeTargets.push([
      path.join(baseDir, 'api-ai', 'whoop_daily_metrics_raw', `${record.localDate}.json`),
      { ...record, seedMode: true, provisionalUntilDirectWhoop: true },
    ]);
  }
  writeTargets.push([
    path.join(baseDir, 'api-ai', 'whoop_daily_metrics_raw', 'latest.json'),
    { ...rawRecords[rawRecords.length - 1], seedMode: true, provisionalUntilDirectWhoop: true },
  ]);

  for (const record of normalizedRecords) {
    writeTargets.push([
      path.join(baseDir, 'api-ai', 'normalized_daily_metrics', `${record.date}.json`),
      { ...record, seedMode: true, provisionalUntilDirectWhoop: true },
    ]);
  }
  writeTargets.push([
    path.join(baseDir, 'api-ai', 'normalized_daily_metrics', 'latest.json'),
    { ...latestNormalized, seedMode: true, provisionalUntilDirectWhoop: true },
  ]);

  for (const artifact of dailyArtifacts) {
    writeTargets.push([
      path.join(baseDir, 'api-ai', 'daily_refresh_artifact', `${artifact.sourceDate}.json`),
      { ...artifact, seedMode: true, provisionalUntilDirectWhoop: true },
    ]);
  }
  writeTargets.push([
    path.join(baseDir, 'api-ai', 'daily_refresh_artifact', 'latest.json'),
    { ...latestDaily, seedMode: true, provisionalUntilDirectWhoop: true },
  ]);

  writeTargets.push([
    path.join(baseDir, 'api-ai', 'weekly_synthesis_artifact', `${weekStart}__${weekEnd}.json`),
    { ...weeklyArtifact, seedMode: true, provisionalUntilDirectWhoop: true },
  ]);
  writeTargets.push([
    path.join(baseDir, 'api-ai', 'weekly_synthesis_artifact', 'latest.json'),
    { ...weeklyArtifact, seedMode: true, provisionalUntilDirectWhoop: true },
  ]);

  writeTargets.push([
    path.join(baseDir, 'api-ai', 'baseline_profile.json'),
    baselineProfile,
  ]);
  writeTargets.push([
    path.join(baseDir, 'api-ai', 'baseline_thresholds.json'),
    baselineThresholds,
  ]);
  writeTargets.push([
    path.join(baseDir, 'api-ai', 'recurring_patterns_candidates.json'),
    recurringPatternsCandidates,
  ]);
  writeTargets.push([
    path.join(baseDir, 'api-ai', 'current_block_summary.json'),
    currentBlockSummary,
  ]);
  writeTargets.push([
    path.join(baseDir, 'api-ai', 'source_health_status', 'whoop.json'),
    whoopHealth,
  ]);
  writeTargets.push([
    path.join(baseDir, 'api-ai', 'source_health_status', 'apple_health.json'),
    appleHealth,
  ]);

  writeTargets.push([
    path.join(baseDir, 'api-ai', 'manifest.json'),
    {
      athleteId,
      generatedAt: isoNow(),
      latestDate: latestDaily.sourceDate,
      weekKey: `${weekStart}__${weekEnd}`,
      seedMode: true,
      seedExportedAt: isoNow(),
      provisionalUntilDirectWhoop: true,
      seedCaveats: [
        'Artifacts derived from cached metrics-history.json, not live WHOOP MCP.',
        'freshUntil timestamps reflect export-time validity, not live refresh.',
        ...missingSourceCaveats,
      ],
      writeTargets: writeTargets.map(([target]) => path.relative(baseDir, target)),
      missingSourceCaveats,
    },
  ]);

  await Promise.all(writeTargets.map(([filePath, value]) => writeJson(filePath, value)));

  return {
    athleteId,
    baseDir,
    latestDate: latestDaily.sourceDate,
    weekKey: `${weekStart}__${weekEnd}`,
    missingSourceCaveats,
    writtenPaths: writeTargets.map(([target]) => path.relative(baseDir, target)),
  };
}

async function main() {
  const athleteId = process.argv[2] ?? 'dev-athlete';
  const result = await seedAthlete(athleteId);
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
}

void main();
