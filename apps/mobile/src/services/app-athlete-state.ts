/**
 * AppAthleteState — device-agnostic, app-owned normalized analysis
 * layer.
 *
 * THREE-LAYER SOURCE MODEL (roles, not rankings):
 *
 *   1. Apple Health (broad baseline / history)
 *      — HealthKit ingest of sleep, HRV, RHR, steps, workouts,
 *        calories, dietary data. Deep history when the user runs
 *        Enrich (up to 5 years). Drives longer baselines + filling
 *        gaps when WHOOP is unavailable.
 *
 *   2. WHOOP Direct (live / current state)
 *      — Live API cycle: today's recovery_score, HRV, RHR, strain,
 *        sleep. Authoritative for CURRENT proprietary scored state.
 *        Does NOT overwrite historical baselines the app derives
 *        from Apple Health — it adds today's scored signal on top.
 *
 *   3. WHOOP export / CSV (optional deeper enrichment)
 *      — User-imported CSV rows from WHOOP data export. Backend
 *        ingests these with source tag 'whoop_csv' so they augment
 *        the backend's longer-range recovery/sleep/workout view.
 *        Optional and additive — never required for normal sync.
 *
 * HOW THEY INTERACT:
 *   - Apple Health + WHOOP merged days power 7d and 30d baselines
 *     (HRV trend, RHR trend, sleep adequacy).
 *   - WHOOP Direct today wins for the TODAY reading of recovery +
 *     strain because it's the proprietary-scored current cycle.
 *   - Apple Health wins for DAYS WHOOP doesn't cover (e.g., user
 *     took the strap off, missed a cycle).
 *   - WHOOP CSV fills historical gaps the backend reasons over
 *     (trend-length, multi-month patterns); mobile surfaces the
 *     ingest status but doesn't independently recompute from CSV.
 *
 * Truth boundaries:
 *   - recent data is weighted more heavily than old data
 *   - confidence drops when inputs are incomplete
 *   - missingness is explicit (data_quality.missing)
 *   - source_roles is explicit (each signal tagged with which
 *     layer contributed — Apple Health, WHOOP Direct, merged)
 *   - nothing here fakes certainty
 */

import { Platform } from 'react-native';
import type { DailyMetrics, DerivedFeatures, TrainingSession } from '@lauburu/shared';

const NATIVE_HEALTH_LABEL = Platform.OS === 'ios' ? 'Apple Health' : 'Health Connect';
const NATIVE_HEALTH_SOURCE = Platform.OS === 'ios' ? 'apple_health' : 'health_connect';

export type Band = 'low' | 'mid' | 'high' | 'unknown';

export interface AppAthleteState {
  date: string; // local ISO date

  recovery_context: {
    band: Band;
    /** App-owned 0–100 composite. null when we lack enough signal. */
    score_0_100: number | null;
    /** Which inputs materially shaped this number, in order. */
    contributing_sources: Array<'whoop_recovery' | 'hrv_trend' | 'resting_hr_trend' | 'sleep_hours' | 'sleep_quality'>;
    /** Human-readable one-liner. Never a vendor-specific phrase. */
    note: string;
    /** Does this number include raw WHOOP recovery_score as an input? */
    uses_vendor_score: boolean;
  };

  load_context: {
    band: 'under' | 'at_target' | 'over' | 'unknown';
    sessions_7d: number;
    hard_sessions_3d: number;
    consecutive_hard_days: number;
    /** App-computed interpretation, NOT raw WHOOP strain. */
    note: string;
  };

  sleep_adequacy: {
    band: Band;
    hours_last_night: number | null;
    hours_7d_avg: number | null;
    note: string;
  };

  fueling_adequacy: {
    band: Band;
    calories_vs_target_pct: number | null;
    protein_vs_target_pct: number | null;
    gaps: Array<'calories' | 'protein' | 'water' | 'carbs' | 'fat' | 'fibre' | 'weight'>;
    note: string;
  };

  hydration_adequacy: {
    band: Band;
    water_ml_today: number | null;
    note: string;
  };

  acute_fatigue: {
    band: Band;
    /** App-level heuristic: hard sessions in last 72h + low recovery band. */
    note: string;
  };

  chronic_load_trend: {
    direction: 'rising' | 'stable' | 'falling' | 'unknown';
    note: string;
  };

  readiness_confidence: {
    level: 'low' | 'medium' | 'high';
    /** 0–1. Drops when inputs are missing or thin. */
    value: number;
    reasons_for_low: string[];
  };

  data_quality: {
    /** What high-value signals are currently missing. */
    missing: string[];
    /** Per-source freshness (hours since last update). null = never. */
    freshness_hours: {
      whoop: number | null;
      apple_health: number | null;
      native_health: number | null;
      nutrition: number | null;
      training: number | null;
    };
    /**
     * Per-signal history depth + the baseline window we chose for
     * each. Surfacing this lets Coach say "comparing today vs your
     * 60-day baseline" with confidence that the window is grounded
     * in this specific user's own history, not a global default.
     */
    history_depth: {
      hrv_days: number;
      rhr_days: number;
      sleep_days: number;
      sessions_total: number;
      baseline_window_days: number;
    };
  };

  /**
   * Three-layer source model — explicit roles so Coach / UI can
   * explain which source is contributing what, without ranking
   * them. All three can coexist; their roles differ.
   */
  source_roles: {
    /**
     * Platform-native broad baseline source. This is the preferred
     * cross-platform field for Coach context: iOS reports
     * `apple_health`, Android reports `health_connect`. The legacy
     * `apple_health` field below remains for older consumers.
     */
    native_health: {
      source: 'apple_health' | 'health_connect';
      label: 'Apple Health' | 'Health Connect';
      role: 'broad_baseline' | 'not_connected';
      days_with_data: number;
      covers_today: boolean;
      history_depth_days: number | null;
    };
    /** Legacy broad-baseline field retained for existing Coach readers. */
    apple_health: {
      role: 'broad_baseline' | 'not_connected';
      days_with_data: number;
      covers_today: boolean;
      history_depth_days: number | null;
    };
    whoop_direct: {
      role: 'live_current' | 'awaiting_cycle' | 'not_connected';
      has_today_cycle: boolean;
      latest_cycle_date: string | null;
    };
    whoop_csv: {
      role: 'deeper_enrichment' | 'not_imported';
      imported_rows: number | null;
      window_days: number | null;
    };
    /**
     * Polar evidence — either via Polar Flow writing to Health
     * Connect, or via the future Polar AccessLink OAuth path.
     * Both contribute training/HR/load evidence to the same
     * normalized layer; Coach can attribute training-load
     * contribution to Polar specifically when this flag is set.
     */
    polar: {
      role: 'training_evidence' | 'not_connected';
      via_health_connect: boolean;
      days_with_records: number | null;
    };
    /**
     * Samsung Health evidence — Android-only; surfaces when
     * Samsung Health writes its broad health metrics into Health
     * Connect. Treated as additional broad-baseline evidence
     * alongside Health Connect's own provider records.
     */
    samsung_health: {
      role: 'broad_baseline_via_hc' | 'not_connected';
      days_with_records: number | null;
    };
  };

  /**
   * Explicit seed/provisional marker for downstream consumers. The
   * readiness composite is app-owned — blended from Apple Health
   * baselines + optional WHOOP Direct + optional WHOOP CSV history +
   * training + nutrition. It is NOT the WHOOP native recovery score,
   * and while the backend is in seed mode it stays provisional.
   *
   * calibration_source is set to 'whoop_direct' when today's WHOOP
   * Direct cycle is present and scored — Coach / UI can mention
   * calibration is available. Set to null otherwise.
   */
  provisional: {
    seed_mode: true;
    score_kind: 'custom_readiness';
    calibration_source: 'whoop_direct' | null;
    primary_live_source: 'apple_health' | 'health_connect' | 'none';
  };
}

export interface BuildAppAthleteStateInputs {
  todayIsoDate: string;
  days: DailyMetrics[];
  features: DerivedFeatures | null;
  sessions: TrainingSession[];
  whoopDay: {
    recovery_score?: number | null;
    sleep_hours?: number | null;
    resting_hr?: number | null;
    daily_strain?: number | null;
    hrv_ms?: number | null;
    source_updated_at?: string | null;
    date?: string;
  } | null;
  whoopFetchedAt: string | null;
  nutritionToday: {
    calories_kcal?: number;
    protein_g?: number;
    carbs_g?: number;
    fat_g?: number;
    fibre_g?: number;
    water_ml?: number;
    body_weight_kg?: number;
    updated_at?: string;
  } | null;
  nutritionTargets: {
    calories_kcal?: number;
    protein_g?: number;
  } | null;
  /**
   * Last 14 days of confirmed nutrition (optional — older callers can
   * omit). Used to compute a rolling-average protein-per-kg + calories
   * baseline so the fueling band reflects a trend, not just today.
   */
  nutritionHistory?: Array<{
    date: string;
    calories_kcal?: number | null;
    protein_g?: number | null;
    body_weight_kg?: number | null;
  }> | null;
  healthLastSyncAt: string | null;
  /** WHOOP CSV enrichment state — optional third layer. When the
   *  backend ingest has CSV rows, pass the count + window so the
   *  source_roles block can surface it. */
  whoopCsv?: {
    imported: boolean;
    rowCount?: number | null;
    windowDays?: number | null;
  } | null;
  /** Live WHOOP fetch status from useWhoopStore. Treat 'loading'
   *  and 'ready' and 'error' (with prior day) as evidence the user
   *  has WHOOP connected — prevents "WHOOP not connected" from
   *  flashing on Home during the first-render fetch window. */
  whoopFetchStatus?: 'idle' | 'loading' | 'ready' | 'error' | null;
  /** Polar provenance — either via Polar Flow → Health Connect
   *  (Android) or via future Polar AccessLink OAuth. Either way it's training
   *  evidence; consumer just needs to know it exists. */
  polarPresence?: {
    detected: boolean;
    viaHealthConnect: boolean;
    daysWithRecords?: number | null;
  } | null;
  /** Samsung Health provenance — Android-only, via Health Connect. */
  samsungPresence?: {
    detected: boolean;
    daysWithRecords?: number | null;
  } | null;
}

function hoursSince(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return null;
  return Math.max(0, (Date.now() - t) / 3_600_000);
}

function pctOf(value: number | null | undefined, target: number | null | undefined): number | null {
  if (value == null || target == null || target <= 0) return null;
  return Math.round((value / target) * 100);
}

function bandFromPct(pct: number | null, goodMin = 80, goodMax = 120): Band {
  if (pct == null) return 'unknown';
  if (pct < 50) return 'low';
  if (pct < goodMin) return 'low';
  if (pct <= goodMax) return 'high';
  return 'mid';
}

/**
 * Compute an app-owned recovery composite. Vendor score is ONE input,
 * not the entire brain. We blend:
 *   - WHOOP recovery_score (when present): 0.4 weight
 *   - HRV trend (7d avg vs today) : 0.25 weight
 *   - Resting HR trend (inverse)  : 0.15 weight
 *   - Sleep hours vs ~7.5h target : 0.20 weight
 * When a signal is missing, its weight is redistributed proportionally
 * to the remaining signals, so a WHOOP-only user and a Apple-Health-
 * only user can both get a meaningful number on the same 0-100 scale.
 */
function computeRecoveryComposite(
  whoopRecoveryScore: number | null,
  hrvToday: number | null,
  hrv7dMean: number | null,
  restingHrToday: number | null,
  restingHr7dMean: number | null,
  sleepHours: number | null,
): { score: number | null; sources: Array<'whoop_recovery' | 'hrv_trend' | 'resting_hr_trend' | 'sleep_hours' | 'sleep_quality'>; usesVendor: boolean } {
  const signals: Array<{ name: 'whoop_recovery' | 'hrv_trend' | 'resting_hr_trend' | 'sleep_hours' | 'sleep_quality'; weight: number; value: number }> = [];

  if (typeof whoopRecoveryScore === 'number') {
    signals.push({ name: 'whoop_recovery', weight: 0.4, value: Math.max(0, Math.min(100, whoopRecoveryScore)) });
  }

  if (typeof hrvToday === 'number' && typeof hrv7dMean === 'number' && hrv7dMean > 0) {
    const delta = hrvToday - hrv7dMean;
    // +/- 20% from baseline → 0..100 mapped
    const ratio = delta / hrv7dMean;
    const val = Math.max(0, Math.min(100, 50 + ratio * 250));
    signals.push({ name: 'hrv_trend', weight: 0.25, value: val });
  }

  if (typeof restingHrToday === 'number' && typeof restingHr7dMean === 'number' && restingHr7dMean > 0) {
    // inverse: low RHR = good recovery
    const delta = restingHrToday - restingHr7dMean;
    const ratio = -delta / restingHr7dMean;
    const val = Math.max(0, Math.min(100, 50 + ratio * 500));
    signals.push({ name: 'resting_hr_trend', weight: 0.15, value: val });
  }

  if (typeof sleepHours === 'number') {
    // 7.5h = 80, cap 100 at 9h, 0 at 4h
    const v = sleepHours <= 4 ? 0 : sleepHours >= 9 ? 100 : Math.round(((sleepHours - 4) / 5) * 100);
    signals.push({ name: 'sleep_hours', weight: 0.2, value: v });
  }

  if (signals.length === 0) {
    return { score: null, sources: [], usesVendor: false };
  }

  const weightSum = signals.reduce((a, s) => a + s.weight, 0);
  const score = Math.round(signals.reduce((a, s) => a + s.value * (s.weight / weightSum), 0));
  return {
    score,
    sources: signals.map((s) => s.name),
    usesVendor: signals.some((s) => s.name === 'whoop_recovery'),
  };
}

function bandFromScore(score: number | null): Band {
  if (score == null) return 'unknown';
  if (score >= 67) return 'high';
  if (score >= 34) return 'mid';
  return 'low';
}

/**
 * Backlog-aware rolling baseline. Previously a 7d/30d toggle — now
 * scales with available history so a tester who uploads 90 days of
 * Apple Health / WHOOP export gets a materially stabler baseline than
 * someone on their first week.
 *
 *   depth ≥ 60 → 90d window
 *   depth ≥ 30 → 60d window
 *   depth ≥ 14 → 30d window
 *   depth ≥ 7  → 14d window
 *   depth < 7  → 7d window
 *
 * The window choice is the single biggest multiplier on Coach quality
 * for users with backlog. Privacy-safe: all computation is on the
 * current user's own `days[]` — no cross-user signal reaches this path.
 */
function pickBaselineWindow(depth: number): number {
  if (depth >= 60) return 90;
  if (depth >= 30) return 60;
  if (depth >= 14) return 30;
  if (depth >= 7) return 14;
  return 7;
}

function computeHrvBaseline(days: DailyMetrics[]): number | null {
  const depth = days.filter((d) => typeof d.hrv_ms === 'number').length;
  const window = pickBaselineWindow(depth);
  const vals = days
    .slice(-window)
    .map((d) => (d.hrv_ms ?? null) as number | null)
    .filter((v): v is number => typeof v === 'number');
  if (vals.length === 0) return null;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

function computeRhrBaseline(days: DailyMetrics[]): number | null {
  const depth = days.filter((d) => typeof d.resting_hr === 'number').length;
  const window = pickBaselineWindow(depth);
  const vals = days
    .slice(-window)
    .map((d) => (d.resting_hr ?? null) as number | null)
    .filter((v): v is number => typeof v === 'number');
  if (vals.length === 0) return null;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

function consecutiveHardDays(sessions: TrainingSession[], today: string): number {
  // Walk backwards from today-1; count consecutive days with a session
  // flagged as hard or tagged as HIIT/grappling.
  const set = new Set<string>();
  for (const s of sessions) {
    const hard = (s.intensity === 'hard') || /hiit|grap|sparring|hard/i.test(`${s.type} ${s.notes ?? ''}`);
    if (hard) set.add(s.date);
  }
  let count = 0;
  const cursor = new Date(today);
  for (let i = 0; i < 14; i += 1) {
    cursor.setDate(cursor.getDate() - 1);
    const key = cursor.toISOString().slice(0, 10);
    if (set.has(key)) count += 1; else break;
  }
  return count;
}

export function buildAppAthleteState(inputs: BuildAppAthleteStateInputs): AppAthleteState {
  const {
    todayIsoDate, days, sessions, whoopDay, whoopFetchedAt,
    nutritionToday, nutritionTargets, healthLastSyncAt,
  } = inputs;

  const todayMetrics = days.find((d) => d.date === todayIsoDate) ?? null;

  // "Most recent" fallback: when today's fields are null (WHOOP cycle
  // not scored yet, Apple Health hasn't synced today's metrics yet),
  // carry the most recent non-null value from the last 2 days so
  // Coach doesn't go silent just because it's morning. The recovery
  // note explicitly marks this as "carrying yesterday's signal".
  const mostRecentFrom = (pick: (d: DailyMetrics) => number | null | undefined): { value: number | null; dateLag: number } => {
    for (let lag = 0; lag < 3; lag += 1) {
      const d = new Date(todayIsoDate);
      d.setDate(d.getDate() - lag);
      const key = d.toISOString().slice(0, 10);
      const found = days.find((x) => x.date === key);
      if (found) {
        const v = pick(found);
        if (typeof v === 'number' && v > 0) return { value: v, dateLag: lag };
      }
    }
    return { value: null, dateLag: -1 };
  };

  const hrvHit = mostRecentFrom((d) => d.hrv_ms ?? null);
  const rhrHit = mostRecentFrom((d) => d.resting_hr ?? null);
  const sleepHit = mostRecentFrom((d) => d.sleep_hours ?? null);

  const hrv7d = computeHrvBaseline(days);
  const rhr7d = computeRhrBaseline(days);

  // Apple Health (HealthKit) gives broad history; WHOOP Direct gives
  // today's scored cycle. For sleep, prefer WHOOP when present and
  // scored; otherwise fall back to Apple Health's most recent.
  const sleepHoursToday = whoopDay?.sleep_hours ?? sleepHit.value;
  const hrvForBlend = hrvHit.value;
  const rhrForBlend = rhrHit.value;

  const recoveryBlend = computeRecoveryComposite(
    whoopDay?.recovery_score ?? null,
    hrvForBlend,
    hrv7d,
    rhrForBlend,
    rhr7d,
    sleepHoursToday,
  );

  const anyFallbackUsed = hrvHit.dateLag > 0 || rhrHit.dateLag > 0 || sleepHit.dateLag > 0;

  const recoveryBand = bandFromScore(recoveryBlend.score);
  const whoopAwaitingCycle = whoopDay != null && whoopDay.recovery_score == null && whoopDay.date === todayIsoDate;
  const recoveryNote = (() => {
    if (recoveryBlend.score == null) {
      if (whoopAwaitingCycle) {
        return `WHOOP awaiting today\u2019s cycle · ${NATIVE_HEALTH_LABEL} hasn\u2019t synced today\u2019s metrics yet. Using baselines from the merged record.`;
      }
      return `Not enough signal yet. Connect ${NATIVE_HEALTH_LABEL} or WHOOP for a real reading.`;
    }
    const fallbackSuffix = anyFallbackUsed ? ' (carrying yesterday\u2019s signal while today syncs)' : '';
    if (recoveryBand === 'high') return `Clear to train. Systems look recovered across the sources we have.${fallbackSuffix}`;
    if (recoveryBand === 'mid') return `Moderate recovery. Technique, drilling, or zone-2 likely better than a hard HIIT today.${fallbackSuffix}`;
    return `Low recovery signal across the sources we have. Easy day or rest likely better than a hard session.${fallbackSuffix}`;
  })();

  // Sessions in last 7 / 3 days
  const cutoff7 = new Date(todayIsoDate);
  cutoff7.setDate(cutoff7.getDate() - 7);
  const sessions7d = sessions.filter((s) => s.date > cutoff7.toISOString().slice(0, 10) && s.date <= todayIsoDate);
  const cutoff3 = new Date(todayIsoDate);
  cutoff3.setDate(cutoff3.getDate() - 3);
  // "Hard" classifier: explicit intensity=hard, OR a grappling-style
  // session (sparring / competition / live rolls). Grappling sparring
  // is systemically taxing even when the user labels intensity as
  // moderate, so treat it as hard for load-context purposes.
  const isHardish = (s: TrainingSession) =>
    (s.intensity === 'hard') ||
    /sparring|comp|competition|live|rolling|wrestle|hiit/i.test(`${s.type} ${(s as any).notes ?? ''}`);
  const hardSessions3d = sessions.filter(
    (s) => s.date > cutoff3.toISOString().slice(0, 10) && s.date <= todayIsoDate && isHardish(s),
  ).length;

  const loadBand: 'under' | 'at_target' | 'over' | 'unknown' =
    sessions7d.length === 0 ? 'unknown' :
    sessions7d.length >= 7 || hardSessions3d >= 3 ? 'over' :
    sessions7d.length >= 3 ? 'at_target' :
    'under';

  const loadNote = (() => {
    if (loadBand === 'over') return 'You\u2019ve stacked hard sessions recently. Consider pulling back intensity today.';
    if (loadBand === 'at_target') return 'Training frequency looks balanced.';
    if (loadBand === 'under') return 'Light week so far.';
    return 'Not enough session data yet.';
  })();

  const consecutiveHard = consecutiveHardDays(sessions, todayIsoDate);

  // Sleep adequacy
  const sleepHours7d = (() => {
    const vals = days.slice(-7)
      .map((d) => d.sleep_hours ?? null)
      .filter((v): v is number => typeof v === 'number');
    if (vals.length === 0) return null;
    return vals.reduce((a, b) => a + b, 0) / vals.length;
  })();
  const sleepBand: Band = sleepHoursToday == null ? 'unknown'
    : sleepHoursToday >= 7 ? 'high'
    : sleepHoursToday >= 5.5 ? 'mid'
    : 'low';
  const sleepNote = sleepHoursToday == null
    ? 'No sleep data yet today.'
    : sleepHoursToday < 6
      ? `Short sleep (${sleepHoursToday.toFixed(1)}h). Expect more fatigue tolerance than usual.`
      : `Sleep last night ~${sleepHoursToday.toFixed(1)}h${sleepHours7d ? ` (7d avg ${sleepHours7d.toFixed(1)}h)` : ''}.`;

  // Fueling adequacy
  const calPct = pctOf(nutritionToday?.calories_kcal, nutritionTargets?.calories_kcal);
  const proteinPct = pctOf(nutritionToday?.protein_g, nutritionTargets?.protein_g);
  const fuelGaps: Array<'calories' | 'protein' | 'water' | 'carbs' | 'fat' | 'fibre' | 'weight'> = [];
  if (!nutritionToday) {
    fuelGaps.push('calories', 'protein');
  } else {
    if (nutritionToday.calories_kcal == null) fuelGaps.push('calories');
    if (nutritionToday.protein_g == null) fuelGaps.push('protein');
    if (nutritionToday.carbs_g == null) fuelGaps.push('carbs');
    if (nutritionToday.fat_g == null) fuelGaps.push('fat');
    if (nutritionToday.fibre_g == null) fuelGaps.push('fibre');
    if (nutritionToday.water_ml == null) fuelGaps.push('water');
    if (nutritionToday.body_weight_kg == null) fuelGaps.push('weight');
  }

  // Protein per kg of bodyweight — the single most useful fueling
  // number for a strength/grappling athlete. 1.6 g/kg is the rough
  // lower bound for maintaining lean mass; 2.0+ g/kg is on the high
  // side but not excessive for hard training.
  const proteinPerKg =
    nutritionToday?.protein_g != null && nutritionToday?.body_weight_kg != null && nutritionToday.body_weight_kg > 0
      ? (nutritionToday.protein_g ?? 0) / nutritionToday.body_weight_kg
      : null;

  // Backlog-aware fueling baseline — 14d rolling averages computed
  // from this user's own confirmed history. Without this, the fueling
  // band only reflects TODAY, which means a user who logs 4 days out
  // of 5 still gets "unknown" on day 5 if they haven't logged yet,
  // and trend phrases like "you've been under-fueled this week" are
  // impossible. Privacy-safe: pure per-user computation on the
  // provided history array.
  const nutritionHistory = inputs.nutritionHistory ?? [];
  const last14Days = nutritionHistory.slice(-14);
  const avgOf = (pick: (r: any) => number | null | undefined): number | null => {
    const vals = last14Days
      .map((r) => pick(r))
      .filter((v): v is number => typeof v === 'number' && v > 0);
    if (vals.length === 0) return null;
    return vals.reduce((a, b) => a + b, 0) / vals.length;
  };
  const caloriesAvg14d = avgOf((r) => r.calories_kcal);
  const proteinAvg14d = avgOf((r) => r.protein_g);
  const weightLatest14d = (() => {
    for (let i = last14Days.length - 1; i >= 0; i -= 1) {
      const w = last14Days[i]?.body_weight_kg;
      if (typeof w === 'number' && w > 0) return w;
    }
    return null;
  })();
  const proteinPerKgAvg14d = (proteinAvg14d != null && weightLatest14d != null && weightLatest14d > 0)
    ? proteinAvg14d / weightLatest14d
    : null;

  const fuelBand: Band = (() => {
    if (!nutritionToday) return 'unknown';
    // If weight + protein are present, use protein-per-kg as the
    // primary signal — it's athlete-specific and doesn't depend on
    // targets being set.
    if (proteinPerKg != null) {
      if (proteinPerKg < 1.2) return 'low';
      if (proteinPerKg <= 2.2) return 'high';
      return 'mid';
    }
    // Otherwise fall back to % of target when targets exist
    if (calPct == null && proteinPct == null) return 'unknown';
    const pcts = [calPct, proteinPct].filter((v): v is number => typeof v === 'number');
    const avg = pcts.reduce((a, b) => a + b, 0) / pcts.length;
    if (avg < 60) return 'low';
    if (avg <= 110) return 'high';
    return 'mid';
  })();
  const fuelNote = (() => {
    if (!nutritionToday) {
      // If today is blank but recent history exists, say so — Coach
      // can then answer "what have you been fueling like" rather
      // than a flat "No fuel logged today."
      if (proteinPerKgAvg14d != null) {
        return `No fuel logged yet today. Your 14d avg is ${proteinPerKgAvg14d.toFixed(1)} g/kg protein.`;
      }
      return 'No fuel logged today.';
    }
    if (proteinPerKg != null) {
      const perKgStr = proteinPerKg.toFixed(1);
      const trendSuffix = proteinPerKgAvg14d != null && Math.abs(proteinPerKg - proteinPerKgAvg14d) >= 0.2
        ? ` vs ${proteinPerKgAvg14d.toFixed(1)} g/kg 14d avg`
        : '';
      if (fuelBand === 'low') return `Under-fueled on protein (${perKgStr} g/kg${trendSuffix}). Target ~1.6–2.0 g/kg for hard training.`;
      if (fuelBand === 'high') return `Protein ${perKgStr} g/kg${trendSuffix} — solid for training today.`;
      if (fuelBand === 'mid') return `High protein (${perKgStr} g/kg${trendSuffix}). Not harmful; consider easing if GI distress.`;
    }
    if (fuelBand === 'low') return 'Under-fueled relative to your targets.';
    if (fuelBand === 'high') return 'On target for fueling.';
    if (fuelBand === 'mid') return 'Over your targets today.';
    return 'Logged but no targets set — log body weight + protein for protein-per-kg guidance, or set calorie + protein targets.';
  })();

  // Hydration
  const hydrationBand: Band = nutritionToday?.water_ml == null ? 'unknown'
    : nutritionToday.water_ml >= 2000 ? 'high'
    : nutritionToday.water_ml >= 1000 ? 'mid'
    : 'low';
  const hydrationNote = nutritionToday?.water_ml == null
    ? 'No hydration logged today.'
    : `${Math.round(nutritionToday.water_ml)} ml logged.`;

  // Acute fatigue heuristic
  const acuteFatigueBand: Band = (() => {
    if (hardSessions3d >= 2 && recoveryBand === 'low') return 'high';
    if (hardSessions3d >= 2 || consecutiveHard >= 3) return 'mid';
    return 'low';
  })();
  const acuteFatigueNote = (() => {
    if (acuteFatigueBand === 'high') return 'Multiple hard sessions in 3d with low recovery. Acute fatigue is likely elevated.';
    if (acuteFatigueBand === 'mid') return `${hardSessions3d} hard session${hardSessions3d === 1 ? '' : 's'} in 3d; ${consecutiveHard} consecutive hard day${consecutiveHard === 1 ? '' : 's'}.`;
    return 'No stacked hard sessions detected.';
  })();

  // Chronic load trend — backlog-aware. Compares the last 7d count
  // against this user's own rolling 28d weekly average when 28d+ of
  // session history exists; falls back to the simple 7d-vs-prior-7d
  // diff when history is shallow. The longer baseline prevents a
  // noisy "rising/falling" flip every week once users have uploaded
  // a month or more of sessions.
  const todayT = new Date(todayIsoDate).getTime();
  const sessionsInWindow = (startDaysAgo: number, endDaysAgoExclusive: number) =>
    sessions.filter((s) => {
      const d = new Date(s.date).getTime();
      return d > todayT - startDaysAgo * 86400_000 && d <= todayT - endDaysAgoExclusive * 86400_000;
    }).length;
  const sessions28dCount = sessionsInWindow(28, 0);
  const sessionsPrev14d = sessionsInWindow(14, 7);
  const have28d = sessions28dCount > 0 && sessions.some((s) => {
    const d = new Date(s.date).getTime();
    return d <= todayT - 21 * 86400_000;
  });
  const weeklyAvg28d = sessions28dCount / 4;
  const chronicDir: 'rising' | 'stable' | 'falling' | 'unknown' = (() => {
    if (have28d) {
      const delta = sessions7d.length - weeklyAvg28d;
      if (delta >= 1.5) return 'rising';
      if (delta <= -1.5) return 'falling';
      if (sessions7d.length === 0 && weeklyAvg28d === 0) return 'unknown';
      return 'stable';
    }
    if (sessions7d.length === 0 && sessionsPrev14d === 0) return 'unknown';
    if (sessions7d.length > sessionsPrev14d + 1) return 'rising';
    if (sessions7d.length + 1 < sessionsPrev14d) return 'falling';
    return 'stable';
  })();
  const chronicNote = (() => {
    if (chronicDir === 'unknown') return 'Not enough history for a trend read.';
    if (have28d) {
      const avgLabel = weeklyAvg28d.toFixed(1);
      if (chronicDir === 'rising') return `Weekly sessions trending up vs your 4-week average (${avgLabel}/wk).`;
      if (chronicDir === 'falling') return `Weekly sessions trending down vs your 4-week average (${avgLabel}/wk).`;
      return `Weekly sessions holding near your 4-week average (${avgLabel}/wk).`;
    }
    if (chronicDir === 'rising') return 'Weekly session count is trending up.';
    if (chronicDir === 'falling') return 'Weekly session count is trending down.';
    return 'Weekly session count is holding steady.';
  })();

  // Readiness confidence
  const missing: string[] = [];
  const fWhoop = hoursSince(whoopDay?.source_updated_at ?? whoopFetchedAt);
  const fAH = hoursSince(healthLastSyncAt);
  const fNut = hoursSince(nutritionToday?.updated_at ?? null);
  const fTrain = hoursSince(sessions[0]?.date ? sessions[0].date + 'T12:00:00Z' : null);
  // Apple Health is "present" when days have been ingested at least
  // once — even if the last sync timestamp is stale, the normalized
  // daily metrics still power recovery/load/sleep. Only flag it as
  // missing if we've genuinely never pulled anything.
  const appleHealthHasData = days.length > 0;
  // WHOOP is "connected" if ANY of:
  //   - we have a WhoopDay record (pipe responded)
  //   - we have a fetch timestamp (attempted a fetch)
  //   - the store's fetch status is 'loading'/'ready'/'error' (an
  //     attempt is in-flight or completed at least once this session)
  // This prevents the first-render flash of "WHOOP not connected"
  // on Home before the initial /data/today fetch completes.
  const whoopFetchStatus = inputs.whoopFetchStatus ?? null;
  const whoopPipelineSeen = whoopFetchStatus === 'loading'
    || whoopFetchStatus === 'ready'
    || whoopFetchStatus === 'error';
  const whoopConnected = whoopDay != null || whoopFetchedAt != null || whoopPipelineSeen;
  if (!whoopConnected) missing.push('whoop');
  if (!appleHealthHasData && fAH == null) missing.push(Platform.OS === 'ios' ? 'apple_health' : 'health_connect');
  if (fNut == null) missing.push('nutrition');
  if (sessions7d.length === 0) missing.push('sessions_7d');

  // Backlog depth signals — let uploads materially lift confidence.
  const hrvHistoryDays = days.filter((d) => typeof d.hrv_ms === 'number').length;
  const rhrHistoryDays = days.filter((d) => typeof d.resting_hr === 'number').length;
  const sleepHistoryDays = days.filter((d) => typeof d.sleep_hours === 'number').length;
  const sessionsTotal = sessions.length;
  const depthBonus = (() => {
    // Each layer adds up to 0.05 at 90+ days, linearly scaled below.
    // Intentionally modest (max 0.20 total) so a fresh user with
    // today's WHOOP + AH still hits 'medium' without backlog, while
    // a tester with 90d history crosses into 'high'.
    const scaled = (n: number, cap: number) => Math.min(cap, (n / 90) * cap);
    return (
      scaled(hrvHistoryDays, 0.05)
      + scaled(rhrHistoryDays, 0.05)
      + scaled(sleepHistoryDays, 0.05)
      + scaled(sessionsTotal, 0.05)
    );
  })();

  const confidenceValue = (() => {
    let v = 0.2;
    // Credit WHOOP for being connected at all. The awaiting-cycle
    // state is normal, not a reason to tank confidence.
    if (whoopConnected) v += 0.25;
    else if (fWhoop != null && fWhoop < 24) v += 0.25;
    // Credit Apple Health for having data at all, not just a fresh
    // sync. A user who enriched history 2 days ago still has all
    // the signal the analysis needs.
    if (appleHealthHasData) v += 0.25;
    else if (fAH != null && fAH < 24) v += 0.25;
    if (sessions7d.length > 0) v += 0.15;
    if (nutritionToday) v += 0.15;
    v += depthBonus;
    return Math.max(0, Math.min(1, v));
  })();
  const confidenceLevel: 'low' | 'medium' | 'high' =
    confidenceValue >= 0.8 ? 'high' : confidenceValue >= 0.5 ? 'medium' : 'low';
  const reasonsForLow: string[] = [];
  if (confidenceLevel !== 'high') {
    if (!whoopConnected) reasonsForLow.push('WHOOP not connected');
    if (!appleHealthHasData && fAH == null) reasonsForLow.push(`${NATIVE_HEALTH_LABEL} not connected`);
    if (nutritionToday == null) reasonsForLow.push('No fuel logged today');
    if (sessions7d.length === 0) reasonsForLow.push('No recent training history');
  }

  return {
    date: todayIsoDate,
    recovery_context: {
      band: recoveryBand,
      score_0_100: recoveryBlend.score,
      contributing_sources: recoveryBlend.sources,
      note: recoveryNote,
      uses_vendor_score: recoveryBlend.usesVendor,
    },
    load_context: {
      band: loadBand,
      sessions_7d: sessions7d.length,
      hard_sessions_3d: hardSessions3d,
      consecutive_hard_days: consecutiveHard,
      note: loadNote,
    },
    sleep_adequacy: {
      band: sleepBand,
      hours_last_night: sleepHoursToday,
      hours_7d_avg: sleepHours7d,
      note: sleepNote,
    },
    fueling_adequacy: {
      band: fuelBand,
      calories_vs_target_pct: calPct,
      protein_vs_target_pct: proteinPct,
      gaps: fuelGaps,
      note: fuelNote,
    },
    hydration_adequacy: {
      band: hydrationBand,
      water_ml_today: nutritionToday?.water_ml ?? null,
      note: hydrationNote,
    },
    acute_fatigue: {
      band: acuteFatigueBand,
      note: acuteFatigueNote,
    },
    chronic_load_trend: {
      direction: chronicDir,
      note: chronicNote,
    },
    readiness_confidence: {
      level: confidenceLevel,
      value: Math.round(confidenceValue * 100) / 100,
      reasons_for_low: reasonsForLow,
    },
    data_quality: {
      missing,
      freshness_hours: {
        whoop: fWhoop,
        apple_health: fAH,
        native_health: fAH,
        nutrition: fNut,
        training: fTrain,
      },
      history_depth: {
        hrv_days: hrvHistoryDays,
        rhr_days: rhrHistoryDays,
        sleep_days: sleepHistoryDays,
        sessions_total: sessionsTotal,
        baseline_window_days: pickBaselineWindow(Math.max(hrvHistoryDays, rhrHistoryDays, sleepHistoryDays)),
      },
    },
    source_roles: {
      native_health: {
        source: NATIVE_HEALTH_SOURCE,
        label: NATIVE_HEALTH_LABEL,
        role: appleHealthHasData ? 'broad_baseline' : 'not_connected',
        days_with_data: days.length,
        covers_today: todayMetrics != null,
        history_depth_days: days.length > 0 ? days.length : null,
      },
      apple_health: {
        role: appleHealthHasData ? 'broad_baseline' : 'not_connected',
        days_with_data: days.length,
        covers_today: todayMetrics != null,
        history_depth_days: days.length > 0 ? days.length : null,
      },
      whoop_direct: {
        role: whoopDay?.recovery_score != null
          ? 'live_current'
          : (whoopDay != null && whoopDay.date != null)
            ? 'awaiting_cycle'
            : 'not_connected',
        has_today_cycle: whoopDay?.date === todayIsoDate,
        latest_cycle_date: whoopDay?.date ?? null,
      },
      whoop_csv: {
        role: inputs.whoopCsv?.imported ? 'deeper_enrichment' : 'not_imported',
        imported_rows: inputs.whoopCsv?.rowCount ?? null,
        window_days: inputs.whoopCsv?.windowDays ?? null,
      },
      polar: {
        role: inputs.polarPresence?.detected ? 'training_evidence' : 'not_connected',
        via_health_connect: !!inputs.polarPresence?.viaHealthConnect,
        days_with_records: inputs.polarPresence?.daysWithRecords ?? null,
      },
      samsung_health: {
        role: inputs.samsungPresence?.detected ? 'broad_baseline_via_hc' : 'not_connected',
        days_with_records: inputs.samsungPresence?.daysWithRecords ?? null,
      },
    },
    provisional: {
      seed_mode: true,
      score_kind: 'custom_readiness',
      calibration_source: whoopDay?.recovery_score != null ? 'whoop_direct' : null,
      primary_live_source: appleHealthHasData
        ? NATIVE_HEALTH_SOURCE
        : 'none',
    },
  };
}
