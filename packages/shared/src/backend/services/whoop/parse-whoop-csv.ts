/**
 * Pure parser for WHOOP user-data CSV exports.
 *
 * The CSVs come from the user-initiated export in the WHOOP app
 * (Settings → Your Data → Export Data). We only parse the two files
 * with highest ROI for our AI baselines + trend analysis today:
 *
 *   recoveries.csv   → daily recovery, HRV, resting HR, SpO2,
 *                      respiratory rate, skin temp
 *   sleeps.csv       → per-sleep total/REM/deep/light/awake hours,
 *                      sleep efficiency, sleep performance
 *
 * The parser is header-detection driven so minor column renames in
 * future WHOOP exports don't break ingest — we look up by (normalized)
 * header name, not by column index. Headers WHOOP has shipped over
 * time include both "Cycle end time" and "Cycle End Time", both
 * "Recovery score %" and "Recovery Score %", etc. Normalisation
 * lowercases + strips non-alphanumerics so all variants resolve to
 * the same key.
 *
 * No side-effects. No DB access. Takes CSV text in, returns
 * `WhoopCsvParsed` out. Callers (ingest-whoop-csv.ts or a future
 * folder-watch worker) are responsible for dedup + persistence.
 */

export interface WhoopCsvRecoveryRow {
  /** Local date the cycle ended (YYYY-MM-DD). Derived from
   *  "Cycle end time" normalised to the device's local tz. */
  date: string;
  /** 0–100 recovery score, or null when not scored. */
  recoveryScore: number | null;
  hrvMs: number | null;
  restingHrBpm: number | null;
  spo2Pct: number | null;
  respiratoryRate: number | null;
  skinTempCelsius: number | null;
}

export interface WhoopCsvSleepRow {
  /** Local date the sleep block ended (YYYY-MM-DD). */
  date: string;
  totalSleepHours: number | null;
  remSleepHours: number | null;
  deepSleepHours: number | null;
  lightSleepHours: number | null;
  awakeHours: number | null;
  sleepEfficiencyPct: number | null;
  sleepPerformancePct: number | null;
  sleepConsistencyPct: number | null;
}

export interface WhoopCsvWorkoutRow {
  /** Local date the workout ended. */
  date: string;
  sportName: string | null;
  durationMin: number | null;
  strainScore: number | null;
  avgHr: number | null;
  maxHr: number | null;
  kilojoules: number | null;
  calories: number | null;
}

export interface WhoopCsvCycleRow {
  /** Local date the cycle ended. */
  date: string;
  dailyStrain: number | null;
  kilojoules: number | null;
  avgHr: number | null;
  maxHr: number | null;
}

/** Detected file type — returned by classifyCsvContent. */
export type WhoopCsvFileKind = 'recoveries' | 'sleeps' | 'workouts' | 'cycles' | 'journal' | 'unknown';

export interface WhoopCsvParsed {
  recoveries: WhoopCsvRecoveryRow[];
  sleeps: WhoopCsvSleepRow[];
  workouts: WhoopCsvWorkoutRow[];
  cycles: WhoopCsvCycleRow[];
  /** Per-file classification result for the UI result Alert. */
  filesDetected: Array<{
    name: string;
    kind: WhoopCsvFileKind;
    rowCount: number;
  }>;
  /** Files we could not classify and did not parse. */
  filesSkipped: Array<{ name: string; reason: string }>;
  /** Dates present across all parsed files, for window summary. */
  windowStart: string | null;
  windowEnd: string | null;
  /** Non-fatal warnings (unknown columns, unparseable rows). */
  warnings: string[];
}

/**
 * Normalise a header name so minor WHOOP renames don't break lookup.
 * Lowercase + strip anything that isn't a-z/0-9.
 */
function normKey(header: string): string {
  return (header ?? '').toLowerCase().replace(/[^a-z0-9]+/g, '');
}

/** Minimal CSV splitter that handles quoted fields + escaped quotes.
 *  WHOOP exports don't embed newlines in cells in the files we care
 *  about, so a line-based loop is enough; no multi-line cell support. */
function parseCsvLine(line: string): string[] {
  const out: string[] = [];
  let cur = '';
  let inQuote = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (inQuote) {
      if (c === '"') {
        if (line[i + 1] === '"') { cur += '"'; i++; } else { inQuote = false; }
      } else {
        cur += c;
      }
    } else {
      if (c === '"') inQuote = true;
      else if (c === ',') { out.push(cur); cur = ''; }
      else cur += c;
    }
  }
  out.push(cur);
  return out.map((s) => s.trim());
}

function parseNumberOrNull(raw: string | undefined): number | null {
  if (raw == null) return null;
  const s = String(raw).trim();
  if (s === '' || s === '--' || s.toLowerCase() === 'n/a') return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

function parseDateOrNull(raw: string | undefined): string | null {
  if (raw == null) return null;
  const s = String(raw).trim();
  if (!s) return null;
  // WHOOP exports use ISO-ish timestamps: "2024-03-15T22:41:08.000Z"
  // or "2024-03-15 22:41:08". Take the date-only prefix (first 10
  // chars when the input looks like YYYY-MM-DD...).
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 10);
  // Fall back to Date parse for anything else (including US-format
  // spans) — only accept if the date is finite.
  const d = new Date(s);
  if (!Number.isFinite(d.getTime())) return null;
  return d.toISOString().slice(0, 10);
}

function minutesToHours(minutes: number | null): number | null {
  if (minutes == null) return null;
  return Math.round((minutes / 60) * 100) / 100;
}

/**
 * Parse a recoveries.csv buffer. Uses normalized header lookup so
 * variant export formats all resolve.
 */
export function parseRecoveriesCsv(text: string, warnings: string[] = []): WhoopCsvRecoveryRow[] {
  const lines = text.split(/\r?\n/).filter((l) => l.length > 0);
  if (lines.length < 2) return [];
  const headers = parseCsvLine(lines[0]).map(normKey);
  const col = (keys: string[]): number => {
    for (const k of keys) {
      const i = headers.indexOf(k);
      if (i >= 0) return i;
    }
    return -1;
  };
  const iEnd = col(['cycleendtime', 'cycleend', 'endtime', 'recoveryend', 'recoveryendtime', 'cyclestarttime']);
  const iScore = col(['recoveryscore', 'recoveryscorepct', 'recoveryscorepercent', 'recoveryscorepercentage', 'recovery']);
  const iHrv = col(['hrvms', 'hrv', 'heartratevariabilityms', 'heartratevariability', 'hrvrmssdms']);
  const iRhr = col(['restingheartrate', 'restinghr', 'restingheartratebpm', 'rhrbpm']);
  const iSpo2 = col(['bloodoxygen', 'bloodoxygenpercent', 'spo2', 'spo2pct', 'spo2percent']);
  const iResp = col(['respiratoryrate', 'respirationrate', 'respiratoryratebrpm']);
  const iSkin = col(['skintempcelsius', 'skintemperature', 'skintempc', 'skintempcelcius']);
  if (iEnd < 0) {
    warnings.push(`recoveries.csv: no time column found; first headers were: ${headers.slice(0, 10).join(', ')}`);
    return [];
  }
  const out: WhoopCsvRecoveryRow[] = [];
  for (let i = 1; i < lines.length; i++) {
    const parts = parseCsvLine(lines[i]);
    const date = parseDateOrNull(parts[iEnd]);
    if (!date) continue;
    out.push({
      date,
      recoveryScore: iScore >= 0 ? parseNumberOrNull(parts[iScore]) : null,
      hrvMs: iHrv >= 0 ? parseNumberOrNull(parts[iHrv]) : null,
      restingHrBpm: iRhr >= 0 ? parseNumberOrNull(parts[iRhr]) : null,
      spo2Pct: iSpo2 >= 0 ? parseNumberOrNull(parts[iSpo2]) : null,
      respiratoryRate: iResp >= 0 ? parseNumberOrNull(parts[iResp]) : null,
      skinTempCelsius: iSkin >= 0 ? parseNumberOrNull(parts[iSkin]) : null,
    });
  }
  return out;
}

/** Parse sleeps.csv. WHOOP exports durations in minutes; we convert
 *  to hours so the shape matches normalized-day fields. */
export function parseSleepsCsv(text: string, warnings: string[] = []): WhoopCsvSleepRow[] {
  const lines = text.split(/\r?\n/).filter((l) => l.length > 0);
  if (lines.length < 2) return [];
  const headers = parseCsvLine(lines[0]).map(normKey);
  const col = (keys: string[]): number => {
    for (const k of keys) {
      const i = headers.indexOf(k);
      if (i >= 0) return i;
    }
    return -1;
  };
  const iEnd = col(['wakeontime', 'wakeuptime', 'cycleendtime', 'endtime']);
  const iTotal = col(['asleepduration', 'asleepdurationmin', 'totalsleepmin', 'asleephours']);
  const iRem = col(['remsleepduration', 'remsleepdurationmin', 'remsleepmin']);
  const iDeep = col(['deepslowwavesleepduration', 'deepsleepduration', 'deepsleepmin']);
  const iLight = col(['lightsleepduration', 'lightsleepmin']);
  const iAwake = col(['awakeduration', 'awakedurationmin', 'awakemin']);
  const iEff = col(['sleepefficiency', 'sleepefficiencypercent', 'sleepefficiencypct']);
  const iPerf = col(['sleepperformance', 'sleepperformancepercent', 'sleepperformancepct']);
  const iCons = col(['sleepconsistency', 'sleepconsistencypercent', 'sleepconsistencypct']);
  if (iEnd < 0) {
    warnings.push('sleeps.csv: no wake/end time column found; skipping file');
    return [];
  }
  const out: WhoopCsvSleepRow[] = [];
  for (let i = 1; i < lines.length; i++) {
    const parts = parseCsvLine(lines[i]);
    const date = parseDateOrNull(parts[iEnd]);
    if (!date) continue;
    out.push({
      date,
      totalSleepHours: minutesToHours(iTotal >= 0 ? parseNumberOrNull(parts[iTotal]) : null),
      remSleepHours: minutesToHours(iRem >= 0 ? parseNumberOrNull(parts[iRem]) : null),
      deepSleepHours: minutesToHours(iDeep >= 0 ? parseNumberOrNull(parts[iDeep]) : null),
      lightSleepHours: minutesToHours(iLight >= 0 ? parseNumberOrNull(parts[iLight]) : null),
      awakeHours: minutesToHours(iAwake >= 0 ? parseNumberOrNull(parts[iAwake]) : null),
      sleepEfficiencyPct: iEff >= 0 ? parseNumberOrNull(parts[iEff]) : null,
      sleepPerformancePct: iPerf >= 0 ? parseNumberOrNull(parts[iPerf]) : null,
      sleepConsistencyPct: iCons >= 0 ? parseNumberOrNull(parts[iCons]) : null,
    });
  }
  return out;
}

export function parseWorkoutsCsv(text: string, warnings: string[] = []): WhoopCsvWorkoutRow[] {
  const lines = text.split(/\r?\n/).filter((l) => l.length > 0);
  if (lines.length < 2) return [];
  const headers = parseCsvLine(lines[0]).map(normKey);
  const col = (keys: string[]): number => {
    for (const k of keys) { const i = headers.indexOf(k); if (i >= 0) return i; }
    return -1;
  };
  // Each candidate list is normKey'd ('a-z0-9' only). WHOOP's export
  // schema has shipped column names "Workout end time" → workoutendtime,
  // "Cycle end time" → cycleendtime, "Activity name" → activityname,
  // etc. Order: prefer workout-specific, fall back to cycle/end-time,
  // finally legacy 'activity*' names.
  const iEnd = col(['workoutendtime', 'workoutend', 'endtime', 'cycleendtime', 'activityend', 'activityendtime']);
  const iSport = col(['activityname', 'sportname', 'workouttype', 'sport']);
  const iDur = col(['durationmin', 'duration', 'workoutduration', 'workoutdurationmin']);
  const iStrain = col(['activitystrain', 'strain', 'strainscore', 'workoutstrain']);
  const iAvgHr = col(['averagehrbpm', 'averagehr', 'avgheartrate', 'avghr', 'avgheartratebpm']);
  const iMaxHr = col(['maxhrbpm', 'maxhr', 'maxheartrate', 'maxheartratebpm']);
  const iKj = col(['energyburnedkj', 'kilojoules', 'kjburned']);
  const iCal = col(['energyburnedcal', 'energyburnedcalories', 'calories', 'caloriesburned']);
  if (iEnd < 0) {
    warnings.push(`workouts.csv: no end-time column found; first headers were: ${headers.slice(0, 10).join(', ')}`);
    return [];
  }
  const out: WhoopCsvWorkoutRow[] = [];
  for (let i = 1; i < lines.length; i++) {
    const parts = parseCsvLine(lines[i]);
    const date = parseDateOrNull(parts[iEnd]);
    if (!date) continue;
    out.push({
      date,
      sportName: iSport >= 0 ? (parts[iSport] || null) : null,
      durationMin: iDur >= 0 ? parseNumberOrNull(parts[iDur]) : null,
      strainScore: iStrain >= 0 ? parseNumberOrNull(parts[iStrain]) : null,
      avgHr: iAvgHr >= 0 ? parseNumberOrNull(parts[iAvgHr]) : null,
      maxHr: iMaxHr >= 0 ? parseNumberOrNull(parts[iMaxHr]) : null,
      kilojoules: iKj >= 0 ? parseNumberOrNull(parts[iKj]) : null,
      calories: iCal >= 0 ? parseNumberOrNull(parts[iCal]) : null,
    });
  }
  return out;
}

export function parseCyclesCsv(text: string, warnings: string[] = []): WhoopCsvCycleRow[] {
  const lines = text.split(/\r?\n/).filter((l) => l.length > 0);
  if (lines.length < 2) return [];
  const headers = parseCsvLine(lines[0]).map(normKey);
  const col = (keys: string[]): number => {
    for (const k of keys) { const i = headers.indexOf(k); if (i >= 0) return i; }
    return -1;
  };
  const iEnd = col(['cycleendtime', 'cycleend', 'endtime']);
  const iStrain = col(['daystrain', 'dailystrain', 'strain']);
  const iKj = col(['energyburnedkj', 'kilojoules']);
  const iAvgHr = col(['averagehr', 'avghr', 'avgheartrate']);
  const iMaxHr = col(['maxhr', 'maxheartrate']);
  if (iEnd < 0) { warnings.push('cycles.csv: no Cycle end time column found; skipping'); return []; }
  const out: WhoopCsvCycleRow[] = [];
  for (let i = 1; i < lines.length; i++) {
    const parts = parseCsvLine(lines[i]);
    const date = parseDateOrNull(parts[iEnd]);
    if (!date) continue;
    out.push({
      date,
      dailyStrain: iStrain >= 0 ? parseNumberOrNull(parts[iStrain]) : null,
      kilojoules: iKj >= 0 ? parseNumberOrNull(parts[iKj]) : null,
      avgHr: iAvgHr >= 0 ? parseNumberOrNull(parts[iAvgHr]) : null,
      maxHr: iMaxHr >= 0 ? parseNumberOrNull(parts[iMaxHr]) : null,
    });
  }
  return out;
}

/**
 * Classify a CSV blob by inspecting filename hints AND the header
 * row. Filename wins if it clearly names a known type; otherwise
 * we fall back to header-signature matching so the user can paste
 * raw content without filename ceremony.
 *
 * Header-signature lookup order matters: we check the most specific
 * sentinels first (sleeps' `asleepduration`, workouts' `activitystrain`)
 * before generic ones (`cyclestarttime` lives in every WHOOP file, so
 * it can only act as a tiebreaker after no specific match was found).
 */
export function classifyCsvContent(name: string | null, text: string): WhoopCsvFileKind {
  const base = (name ?? '').toLowerCase().split('/').pop() ?? '';
  if (base.includes('recover')) return 'recoveries';
  if (base.includes('sleep')) return 'sleeps';
  if (base.includes('workout') || base.includes('activity')) return 'workouts';
  if (base.includes('cycle') || base.includes('physiological')) return 'cycles';
  if (base.includes('journal')) return 'journal';
  // Header signature fallback. Iterate in specificity order so a file
  // with both 'cyclestarttime' AND 'recoveryscore' is recoveries, not
  // cycles.
  const firstLine = text.split(/\r?\n/, 1)[0] ?? '';
  const headerKeys = parseCsvLine(firstLine).map(normKey);
  const has = (k: string) => headerKeys.includes(k);
  // Recoveries — recovery-score column or HRV/RHR pair without strain.
  if (has('recoveryscore') || has('recoveryscorepct') || has('recoveryscorepercent') || has('recoveryscorepercentage')) return 'recoveries';
  if ((has('hrvms') || has('heartratevariabilityms') || has('heartratevariability')) && (has('restingheartrate') || has('restinghr') || has('restingheartratebpm'))) return 'recoveries';
  // Sleeps — distinct sleep-stage durations.
  if (has('asleepduration') || has('remsleepduration') || has('sleepperformance') || has('lightsleepduration') || has('deepslowwavesleepduration') || has('deepsleepduration') || has('sleepefficiency') || has('sleepefficiencypercent')) return 'sleeps';
  // Workouts — per-activity records.
  if (has('activitystrain') || has('activityname') || has('workouttype') || has('workoutstarttime') || has('workoutendtime') || (has('sport') && has('strain')) || (has('hrzone1') && has('hrzone2'))) return 'workouts';
  // Cycles — daily strain.
  if (has('daystrain') || has('dailystrain')) return 'cycles';
  if (has('journalentry') || has('journalquestion')) return 'journal';
  return 'unknown';
}

/**
 * Entry point for ingest — takes a `{ filename: text }` map, auto-
 * classifies each file by filename + header, parses supported types,
 * and returns a summary for the UI. Unknown files are reported
 * without aborting.
 */
export function parseWhoopCsvBundle(files: Record<string, string>): WhoopCsvParsed {
  const warnings: string[] = [];
  let recoveries: WhoopCsvRecoveryRow[] = [];
  let sleeps: WhoopCsvSleepRow[] = [];
  let workouts: WhoopCsvWorkoutRow[] = [];
  let cycles: WhoopCsvCycleRow[] = [];
  const filesDetected: Array<{ name: string; kind: WhoopCsvFileKind; rowCount: number }> = [];
  const filesSkipped: Array<{ name: string; reason: string }> = [];
  for (const [name, text] of Object.entries(files)) {
    const kind = classifyCsvContent(name, text);
    let rowCount = 0;
    if (kind === 'recoveries') {
      const rows = parseRecoveriesCsv(text, warnings);
      recoveries = recoveries.concat(rows);
      rowCount = rows.length;
    } else if (kind === 'sleeps') {
      const rows = parseSleepsCsv(text, warnings);
      sleeps = sleeps.concat(rows);
      rowCount = rows.length;
    } else if (kind === 'workouts') {
      const rows = parseWorkoutsCsv(text, warnings);
      workouts = workouts.concat(rows);
      rowCount = rows.length;
    } else if (kind === 'cycles') {
      const rows = parseCyclesCsv(text, warnings);
      cycles = cycles.concat(rows);
      rowCount = rows.length;
    } else if (kind === 'journal') {
      filesSkipped.push({ name, reason: 'Journal entries not yet parsed (coming soon)' });
      filesDetected.push({ name, kind, rowCount: 0 });
      continue;
    } else {
      // Surface the first 10 normalized headers so users can see why
      // classification failed (and we can patch the classifier without
      // another guessing round). We log normalized keys rather than
      // raw cell content — no PII, just the column names.
      const firstLine = text.split(/\r?\n/, 1)[0] ?? '';
      const headerSample = parseCsvLine(firstLine).map(normKey).slice(0, 10).join(', ');
      filesSkipped.push({
        name,
        reason: headerSample
          ? `Unrecognised WHOOP CSV shape. Headers: ${headerSample}`
          : 'Unrecognised WHOOP CSV shape (empty file)',
      });
      continue;
    }
    filesDetected.push({ name, kind, rowCount });
  }
  // Dedup by date across sources.
  const recByDate = new Map<string, WhoopCsvRecoveryRow>();
  for (const r of recoveries) if (!recByDate.has(r.date)) recByDate.set(r.date, r);
  const slpByDate = new Map<string, WhoopCsvSleepRow>();
  for (const s of sleeps) if (!slpByDate.has(s.date)) slpByDate.set(s.date, s);
  const cycByDate = new Map<string, WhoopCsvCycleRow>();
  for (const c of cycles) if (!cycByDate.has(c.date)) cycByDate.set(c.date, c);
  // Workouts are per-event, not per-date; keep duplicates out on
  // (date + sportName + durationMin) signature to avoid re-uploading
  // the same export creating ghost sessions.
  const wkKey = (w: WhoopCsvWorkoutRow) => `${w.date}|${w.sportName ?? '?'}|${w.durationMin ?? '?'}`;
  const wkSeen = new Set<string>();
  const dedupedWk: WhoopCsvWorkoutRow[] = [];
  for (const w of workouts) { const k = wkKey(w); if (!wkSeen.has(k)) { wkSeen.add(k); dedupedWk.push(w); } }
  const dedupedRec = Array.from(recByDate.values()).sort((a, b) => a.date.localeCompare(b.date));
  const dedupedSlp = Array.from(slpByDate.values()).sort((a, b) => a.date.localeCompare(b.date));
  const dedupedCyc = Array.from(cycByDate.values()).sort((a, b) => a.date.localeCompare(b.date));
  const allDates = [...recByDate.keys(), ...slpByDate.keys(), ...cycByDate.keys(), ...dedupedWk.map((w) => w.date)].sort();
  const windowStart = allDates[0] ?? null;
  const windowEnd = allDates[allDates.length - 1] ?? null;
  return {
    recoveries: dedupedRec,
    sleeps: dedupedSlp,
    workouts: dedupedWk,
    cycles: dedupedCyc,
    filesDetected,
    filesSkipped,
    windowStart,
    windowEnd,
    warnings,
  };
}
