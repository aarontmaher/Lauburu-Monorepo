/**
 * WHOOP CSV ingest — deep historical enrichment path.
 *
 * Runs alongside `ingest-whoop.ts` (live API). CSV rows are written
 * under a *separate* `derivationVersion: 'whoop_csv_v1'` so API rows
 * are never overwritten by older CSV rows. Merge at read time picks
 * the right source per field age.
 *
 * Smart incremental ingest:
 *   - Caller computes file hash (SHA-256) and passes it in.
 *   - If the hash matches a prior import, the function returns
 *     `{ rowsNew: 0, skippedReason: 'duplicate-upload' }` without
 *     touching the store.
 *   - Per-date dedup: if a normalised day with `whoop_csv_v1` already
 *     exists and the new row has no new non-null fields, skip it.
 *     Otherwise merge — existing non-null values are preserved
 *     (so re-uploading a smaller CSV window can never delete data).
 *
 * No provider auto-sync. CSV is manual-upload only. If/when a folder-
 * watch worker arrives it calls `ingestWhoopCsvForAthlete(...)` with
 * the same shape and the smart-incremental logic handles it.
 */

import type { WhoopCsvParsed } from './parse-whoop-csv';

/**
 * Shape of a single normalized-day row we write. Loose on purpose —
 * the real type lives in the app's athlete-memory store and varies
 * slightly across schema versions; we only need the subset we set.
 */
export interface NormalizedDayPatch {
  id: string;
  schemaVersion: number;
  createdAt: string;
  updatedAt: string;
  derivationVersion: 'whoop_csv_v1';
  athleteId: string;
  date: string;
  recoveryScore: number | null;
  hrvMs: number | null;
  restingHrBpm: number | null;
  spo2Pct: number | null;
  respiratoryRate: number | null;
  skinTempCelsius: number | null;
  totalSleepHours: number | null;
  remSleepHours: number | null;
  deepSleepHours: number | null;
  lightSleepHours: number | null;
  awakeHours: number | null;
  sleepEfficiencyPct: number | null;
  sleepPerformancePct: number | null;
  dailyStrain: number | null;
  kilojoules: number | null;
  workoutCount: number | null;
  workoutMinutesTotal: number | null;
  workoutSports: string[] | null;
  provider: 'whoop_csv';
  sourceRefs: Array<{ layer: string; recordId: string; fieldPath: string | null; date: string }>;
}

export interface WhoopCsvSourceHealth {
  id: string;
  schemaVersion: number;
  updatedAt: string;
  athleteId: string;
  provider: 'whoop_csv';
  /** ISO timestamps of the last successful + last attempted imports. */
  lastImportAt: string | null;
  lastAttemptAt: string | null;
  /** Distinct file-content hashes imported so far. Used for dedup. */
  importedFileHashes: string[];
  /** Earliest date across all imports (persists across uploads). */
  earliestDate: string | null;
  /** Latest date across all imports. */
  latestDate: string | null;
  /** Sum of rows ingested (new + updated) across all imports. */
  totalRowsIngested: number;
  /** Rows ingested in the most recent import. 0 when duplicate. */
  lastImportRowsNew: number;
  /** Most recent import's window. */
  lastImportWindowStart: string | null;
  lastImportWindowEnd: string | null;
  /** Domains we've filled from CSV so the UI can tell the user
   *  what types of metrics they're getting out of the export. */
  domainsFilled: string[];
  /** Non-fatal warnings from the latest import. */
  lastWarnings: string[];
  /** Human-friendly note the mobile UI can surface. */
  note?: string;
}

export interface IngestRunResult {
  rowsConsidered: number;
  rowsNew: number;
  rowsSkippedDuplicate: number;
  domainsFilled: string[];
  windowStart: string | null;
  windowEnd: string | null;
  warnings: string[];
  skippedReason?: 'duplicate-upload';
}

/**
 * Store adapter interface. The server wires it to the existing
 * FileApiAiStateStore. Keeping the shape narrow means this module
 * stays unit-testable without dragging the whole store in.
 */
export interface CsvIngestStore {
  getNormalizedDay(athleteId: string, date: string, derivationVersion: string): Promise<Partial<NormalizedDayPatch> | null>;
  saveNormalizedDay(athleteId: string, day: NormalizedDayPatch): Promise<void>;
  getSourceHealth(athleteId: string, provider: 'whoop_csv'): Promise<WhoopCsvSourceHealth | null>;
  saveSourceHealth(athleteId: string, provider: 'whoop_csv', sh: WhoopCsvSourceHealth): Promise<void>;
}

function mergeFields(existing: Partial<NormalizedDayPatch> | null, incoming: Partial<NormalizedDayPatch>): Partial<NormalizedDayPatch> {
  if (!existing) return incoming;
  const preserved: Partial<NormalizedDayPatch> = { ...incoming };
  (Object.keys(incoming) as Array<keyof NormalizedDayPatch>).forEach((k) => {
    // Preserve existing non-null values — re-uploading a smaller CSV
    // should never erase richer historical rows.
    if ((existing as any)[k] != null && (incoming as any)[k] == null) {
      (preserved as any)[k] = (existing as any)[k];
    }
  });
  return preserved;
}

/**
 * Ingest a parsed CSV bundle for an athlete. Hash-dedup + per-date
 * merge. Idempotent: re-running with the same file does nothing
 * (returns `skippedReason: 'duplicate-upload'`).
 */
export async function ingestWhoopCsvForAthlete(params: {
  athleteId: string;
  fileHash: string;
  parsed: WhoopCsvParsed;
  store: CsvIngestStore;
  now?: string;
}): Promise<IngestRunResult> {
  const { athleteId, fileHash, parsed, store } = params;
  const now = params.now ?? new Date().toISOString();
  const existingSh = await store.getSourceHealth(athleteId, 'whoop_csv');

  // Duplicate-file short-circuit.
  if (existingSh && existingSh.importedFileHashes.includes(fileHash)) {
    const updated: WhoopCsvSourceHealth = {
      ...existingSh,
      lastAttemptAt: now,
      lastImportRowsNew: 0,
      lastWarnings: ['Same file already imported — nothing to do.'],
    };
    await store.saveSourceHealth(athleteId, 'whoop_csv', updated);
    return {
      rowsConsidered: 0,
      rowsNew: 0,
      rowsSkippedDuplicate: parsed.recoveries.length + parsed.sleeps.length,
      domainsFilled: existingSh.domainsFilled,
      windowStart: existingSh.earliestDate,
      windowEnd: existingSh.latestDate,
      warnings: ['Same file already imported — nothing to do.'],
      skippedReason: 'duplicate-upload',
    };
  }

  // Build per-date row patches from the parsed CSV bundle.
  const byDate = new Map<string, Partial<NormalizedDayPatch>>();
  for (const r of parsed.recoveries) {
    const base = byDate.get(r.date) ?? {};
    byDate.set(r.date, {
      ...base,
      date: r.date,
      recoveryScore: r.recoveryScore,
      hrvMs: r.hrvMs,
      restingHrBpm: r.restingHrBpm,
      spo2Pct: r.spo2Pct,
      respiratoryRate: r.respiratoryRate,
      skinTempCelsius: r.skinTempCelsius,
    });
  }
  for (const s of parsed.sleeps) {
    const base = byDate.get(s.date) ?? {};
    byDate.set(s.date, {
      ...base,
      date: s.date,
      totalSleepHours: s.totalSleepHours,
      remSleepHours: s.remSleepHours,
      deepSleepHours: s.deepSleepHours,
      lightSleepHours: s.lightSleepHours,
      awakeHours: s.awakeHours,
      sleepEfficiencyPct: s.sleepEfficiencyPct,
      sleepPerformancePct: s.sleepPerformancePct,
    });
  }
  for (const c of parsed.cycles) {
    const base = byDate.get(c.date) ?? {};
    byDate.set(c.date, {
      ...base,
      date: c.date,
      dailyStrain: c.dailyStrain,
      kilojoules: c.kilojoules,
    });
  }
  // Workouts: aggregate per-date summary (count, total minutes, sports).
  const workoutAgg = new Map<string, { count: number; minutes: number; sports: Set<string> }>();
  for (const w of parsed.workouts) {
    const cur = workoutAgg.get(w.date) ?? { count: 0, minutes: 0, sports: new Set<string>() };
    cur.count += 1;
    if (w.durationMin != null) cur.minutes += w.durationMin;
    if (w.sportName) cur.sports.add(w.sportName);
    workoutAgg.set(w.date, cur);
  }
  for (const [date, agg] of workoutAgg) {
    const base = byDate.get(date) ?? {};
    byDate.set(date, {
      ...base,
      date,
      workoutCount: agg.count,
      workoutMinutesTotal: Math.round(agg.minutes),
      workoutSports: Array.from(agg.sports),
    });
  }

  let rowsNew = 0;
  let rowsSkipped = 0;
  const domainsFilled = new Set<string>(existingSh?.domainsFilled ?? []);
  for (const [date, patch] of byDate) {
    const existing = await store.getNormalizedDay(athleteId, date, 'whoop_csv_v1');
    const merged = mergeFields(existing ?? null, patch) as NormalizedDayPatch;
    // Skip when the merge produces identical non-null fields to what's
    // already stored — avoids rewriting the file with no changes.
    const identical = existing && (Object.keys(merged) as Array<keyof NormalizedDayPatch>).every(
      (k) => (existing as any)[k] === (merged as any)[k],
    );
    if (identical) { rowsSkipped += 1; continue; }
    const full: NormalizedDayPatch = {
      id: existing?.id ?? `norm_whoop_csv_${date}_${Date.now()}`,
      schemaVersion: 1,
      createdAt: (existing as any)?.createdAt ?? now,
      updatedAt: now,
      derivationVersion: 'whoop_csv_v1',
      athleteId,
      date,
      recoveryScore: merged.recoveryScore ?? null,
      hrvMs: merged.hrvMs ?? null,
      restingHrBpm: merged.restingHrBpm ?? null,
      spo2Pct: merged.spo2Pct ?? null,
      respiratoryRate: merged.respiratoryRate ?? null,
      skinTempCelsius: merged.skinTempCelsius ?? null,
      totalSleepHours: merged.totalSleepHours ?? null,
      remSleepHours: merged.remSleepHours ?? null,
      deepSleepHours: merged.deepSleepHours ?? null,
      lightSleepHours: merged.lightSleepHours ?? null,
      awakeHours: merged.awakeHours ?? null,
      sleepEfficiencyPct: merged.sleepEfficiencyPct ?? null,
      sleepPerformancePct: merged.sleepPerformancePct ?? null,
      dailyStrain: merged.dailyStrain ?? null,
      kilojoules: merged.kilojoules ?? null,
      workoutCount: merged.workoutCount ?? null,
      workoutMinutesTotal: merged.workoutMinutesTotal ?? null,
      workoutSports: merged.workoutSports ?? null,
      provider: 'whoop_csv',
      sourceRefs: [
        { layer: 'csv_export', recordId: `whoop_csv_${fileHash.slice(0, 12)}`, fieldPath: null, date },
      ],
    };
    await store.saveNormalizedDay(athleteId, full);
    rowsNew += 1;
    if (full.recoveryScore != null) domainsFilled.add('recovery');
    if (full.hrvMs != null) domainsFilled.add('hrv');
    if (full.restingHrBpm != null) domainsFilled.add('resting_hr');
    if (full.totalSleepHours != null) domainsFilled.add('sleep');
    if (full.remSleepHours != null || full.deepSleepHours != null) domainsFilled.add('sleep_stage_detail');
    if (full.respiratoryRate != null) domainsFilled.add('respiratory_rate');
    if (full.skinTempCelsius != null) domainsFilled.add('skin_temp');
    if (full.spo2Pct != null) domainsFilled.add('spo2');
    if (full.dailyStrain != null) domainsFilled.add('strain');
    if (full.workoutCount != null) domainsFilled.add('workouts');
  }

  // Roll the window across all imports.
  const earliestDate = ((): string | null => {
    const candidates = [existingSh?.earliestDate, parsed.windowStart].filter((x): x is string => !!x);
    return candidates.length > 0 ? candidates.sort()[0] : null;
  })();
  const latestDate = ((): string | null => {
    const candidates = [existingSh?.latestDate, parsed.windowEnd].filter((x): x is string => !!x);
    return candidates.length > 0 ? candidates.sort()[candidates.length - 1] : null;
  })();

  const nextSh: WhoopCsvSourceHealth = {
    id: existingSh?.id ?? `source_health_whoop_csv_${athleteId}`,
    schemaVersion: 1,
    updatedAt: now,
    athleteId,
    provider: 'whoop_csv',
    lastImportAt: now,
    lastAttemptAt: now,
    importedFileHashes: Array.from(new Set([...(existingSh?.importedFileHashes ?? []), fileHash])),
    earliestDate,
    latestDate,
    totalRowsIngested: (existingSh?.totalRowsIngested ?? 0) + rowsNew,
    lastImportRowsNew: rowsNew,
    lastImportWindowStart: parsed.windowStart,
    lastImportWindowEnd: parsed.windowEnd,
    domainsFilled: Array.from(domainsFilled),
    lastWarnings: parsed.warnings,
    note: 'WHOOP CSV is manual-upload only — there is no automatic export source. Re-upload the latest WHOOP export to append new historical days.',
  };
  await store.saveSourceHealth(athleteId, 'whoop_csv', nextSh);

  return {
    rowsConsidered: byDate.size,
    rowsNew,
    rowsSkippedDuplicate: rowsSkipped,
    domainsFilled: Array.from(domainsFilled),
    windowStart: parsed.windowStart,
    windowEnd: parsed.windowEnd,
    warnings: parsed.warnings,
  };
}
