/**
 * Athlete refresh scheduler — polls on an interval and runs the
 * ingest → normalize → daily refresh pipeline for each athlete
 * with autoRefresh.daily enabled.
 *
 * Uses the FileApiAiStateStore (api-ai/ directory) so writes
 * and reads use the same path the read orchestrator consumes.
 *
 * Does NOT mutate stable memory. Does NOT auto-promote.
 */
import { FileApiAiStateStore } from '../athlete-memory/file-api-ai-state-store';
import { FilePrivateAthleteMemoryRepository, type PrivateAthleteManifest } from '../athlete-memory/file-private-athlete-memory-repository';
import { createLiveWhoopReader } from '../sources/liveWhoopReader';
import { normalizeWhoopDay } from '../../../../packages/shared/src/backend/services/normalize/normalize-daily-metrics';
import { buildDailyRefreshArtifact } from '../../../../packages/shared/src/backend/services/refresh/build-daily-refresh';
import { buildWeeklySynthesisArtifact } from '../../../../packages/shared/src/backend/services/refresh/build-weekly-synthesis';
import type { AthletePhysiologyBaseline } from '../../../../packages/shared/src/athlete-memory/types';

function dateKeyInZone(date: Date, timeZone: string): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date);
}

function currentWeekStart(dateKey: string): string {
  const date = new Date(`${dateKey}T00:00:00.000Z`);
  const day = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() - day + 1);
  return date.toISOString().slice(0, 10);
}

function offsetDate(date: string, days: number): string {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export function startAthleteRefreshScheduler(
  legacyRepo: FilePrivateAthleteMemoryRepository,
  options?: {
    pollIntervalMs?: number;
    now?: () => Date;
    store?: FileApiAiStateStore;
  },
): NodeJS.Timeout {
  const pollIntervalMs = options?.pollIntervalMs ?? 15 * 60 * 1000;
  const now = options?.now ?? (() => new Date());
  // Use the api-ai store for reads and writes so the pipeline
  // output lands where the read orchestrator looks.
  const store = options?.store ?? new FileApiAiStateStore(legacyRepo['baseDir']);
  const liveReader = createLiveWhoopReader(store);

  const tick = async () => {
    const manifests = await legacyRepo.listAthletes();
    for (const manifest of manifests) {
      try {
        await runDailyIfNeeded(manifest, store, liveReader, now);
        await runWeeklyIfNeeded(manifest, store, now);
      } catch (err) {
        // Log but don't crash the scheduler
        console.error(`[scheduler] ${manifest.athleteId} error:`, err);
      }
    }
  };

  void tick();
  return setInterval(() => { void tick(); }, pollIntervalMs);
}

async function runDailyIfNeeded(
  manifest: PrivateAthleteManifest,
  store: FileApiAiStateStore,
  liveReader: ReturnType<typeof createLiveWhoopReader>,
  now: () => Date,
) {
  if (!manifest.autoRefresh.daily) return;

  const currentDateKey = dateKeyInZone(now(), manifest.timezone);
  const latestDaily = await store.getLatestDailyRefresh(manifest.athleteId);
  if (latestDaily && latestDaily.sourceDate >= currentDateKey) return; // already fresh

  // Try live WHOOP fetch for today
  const liveNorm = await liveReader.fetchAndNormalize(manifest.athleteId, currentDateKey);
  if (!liveNorm) return; // no data available yet

  // Get recent 3 days for rolling risk
  const threeDaysAgo = offsetDate(currentDateKey, -2);
  const recentNorm = await store.loadNormalizedRange(manifest.athleteId, threeDaysAgo, currentDateKey);

  // Get baseline from stable memory
  const memory = await store.getStableMemory(manifest.athleteId);
  if (!memory?.physiologyBaseline) return;

  const artifact = buildDailyRefreshArtifact({
    today: liveNorm,
    recent3Days: recentNorm.length > 0 ? recentNorm : [liveNorm],
    baseline: memory.physiologyBaseline as AthletePhysiologyBaseline,
  });

  await store.saveDailyRefresh(manifest.athleteId, artifact);
}

async function runWeeklyIfNeeded(
  manifest: PrivateAthleteManifest,
  store: FileApiAiStateStore,
  now: () => Date,
) {
  if (!manifest.autoRefresh.weekly) return;

  const currentDateKey = dateKeyInZone(now(), manifest.timezone);
  const weekStart = currentWeekStart(currentDateKey);
  const latestWeekly = await store.getLatestWeeklySynthesis(manifest.athleteId);
  if (latestWeekly && latestWeekly.weekStart >= weekStart) return; // already fresh

  const dailies = await store.listDailyRefreshes(manifest.athleteId, {
    startDate: weekStart,
    endDate: currentDateKey,
  });
  if (dailies.length === 0) return;

  const memory = await store.getStableMemory(manifest.athleteId);
  if (!memory?.physiologyBaseline) return;

  const synthesis = buildWeeklySynthesisArtifact({
    athleteId: manifest.athleteId,
    weekStart,
    weekEnd: currentDateKey,
    dailyArtifacts: dailies,
    baseline: memory.physiologyBaseline as AthletePhysiologyBaseline,
  });

  await store.saveWeeklySynthesis(manifest.athleteId, synthesis);
}
