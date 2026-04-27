/**
 * Readiness analysis layer — produces a structured readiness context
 * for a single athlete + single day.
 *
 * HARD GATE: this layer only activates when the athlete has DIRECT
 * user-owned WHOOP recovery/HRV/strain fields fresh for the given
 * day. Health Connect, Polar-via-HC, Polar direct, and nutrition
 * contribute as contextual support but NEVER unlock the readiness
 * output on their own.
 *
 * Output NEVER includes:
 *   - medical claims
 *   - injury prediction
 *   - absolute "must train" or "must rest" directives
 *
 * Output ALWAYS includes:
 *   - explicit confidence + missingness
 *   - source fields that grounded the interpretation
 *   - guardrail notes
 */

import type { NormalizedDailyMetrics } from '../../contracts/normalized-daily.types';
import type { DailyRefreshArtifact } from '../../contracts/refresh-artifacts.types';

export type ReadinessLevel = 'green' | 'yellow' | 'red' | 'blocked';
export type ReadinessMode = 'live' | 'seed' | 'unavailable';

export interface ReadinessAnalysisInput {
  athleteId: string;
  date: string;
  /** Today's normalized record — must contain WHOOP recovery fields. */
  normalizedDay: NormalizedDailyMetrics | null;
  /** Latest daily artifact — provides dayState and session gate. */
  dailyArtifact: DailyRefreshArtifact | null;
  /** Whether the WHOOP source is direct + fresh for THIS athlete. */
  whoopDirectFresh: boolean;
  /** Support context (not used for gating, only for richer output). */
  supportContext?: {
    hiitSessionCountLast7Days?: number;
    grapplingSessionCountLast7Days?: number;
    nutritionCaloriesToday?: number | null;
    nutritionProteinToday?: number | null;
    healthConnectSleepHours?: number | null;
    polarViaHcWorkoutCount?: number | null;
  };
}

export interface ReadinessAnalysisResult {
  athleteId: string;
  date: string;
  mode: ReadinessMode;
  level: ReadinessLevel;
  confidence: 'low' | 'medium' | 'high';

  /** Interpretation — human-readable, always cautious. */
  interpretation: string;
  /** Support context that strengthened or weakened confidence. */
  contextUsed: string[];
  /** What's missing that would improve this output. */
  missingness: string[];
  /** Sources that directly contributed to the level decision. */
  sourceFields: string[];

  /** Raw numbers surfaced for mobile display (null if unavailable). */
  metrics: {
    recoveryScore: number | null;
    hrvMs: number | null;
    restingHrBpm: number | null;
    dailyStrain: number | null;
    sleepHours: number | null;
  };

  /** Guardrail disclaimers — always non-empty. */
  guardrails: string[];
}

const GUARDRAILS = [
  'This is coaching context, not medical advice.',
  'Readiness interpretation is based on one day; multi-day trends are more reliable.',
  'Acute illness, injury, or medication can affect these metrics independently of training load.',
];

export function analyseReadiness(input: ReadinessAnalysisInput): ReadinessAnalysisResult {
  const { athleteId, date, normalizedDay, dailyArtifact, whoopDirectFresh, supportContext } = input;

  // ── Hard gate: no live readiness without direct WHOOP ──────
  if (!whoopDirectFresh || !normalizedDay) {
    return {
      athleteId,
      date,
      mode: whoopDirectFresh ? 'seed' : 'unavailable',
      level: 'blocked',
      confidence: 'low',
      interpretation: !whoopDirectFresh
        ? 'Readiness analysis requires fresh direct WHOOP recovery, HRV, and strain for your account. These fields are not live.'
        : 'No normalized data for today.',
      contextUsed: [],
      missingness: [
        !whoopDirectFresh ? 'direct_whoop_recovery_fields' : null,
        !normalizedDay ? 'normalized_day' : null,
      ].filter(Boolean) as string[],
      sourceFields: [],
      metrics: { recoveryScore: null, hrvMs: null, restingHrBpm: null, dailyStrain: null, sleepHours: null },
      guardrails: GUARDRAILS,
    };
  }

  const recovery = normalizedDay.recoveryScore;
  const hrv = normalizedDay.hrvMs;
  const strain = normalizedDay.dailyStrain;
  const sleep = normalizedDay.totalSleepHours;
  const rhr = normalizedDay.restingHrBpm;

  // Must have at least recovery + one more field for meaningful readiness.
  if (recovery == null) {
    return {
      athleteId, date, mode: 'seed', level: 'blocked', confidence: 'low',
      interpretation: 'Recovery score is missing from today\'s WHOOP data. Readiness cannot be determined without it.',
      contextUsed: [], missingness: ['recoveryScore'], sourceFields: [],
      metrics: { recoveryScore: null, hrvMs: hrv ?? null, restingHrBpm: rhr ?? null, dailyStrain: strain ?? null, sleepHours: sleep ?? null },
      guardrails: GUARDRAILS,
    };
  }

  // ── Derive level from artifact dayState if available, else from recovery ──
  let level: ReadinessLevel;
  if (dailyArtifact) {
    level = dailyArtifact.dayState as ReadinessLevel;
  } else {
    level = recovery >= 67 ? 'green' : recovery >= 34 ? 'yellow' : 'red';
  }

  const sourceFields = ['recoveryScore'];
  if (hrv != null) sourceFields.push('hrvMs');
  if (strain != null) sourceFields.push('dailyStrain');
  if (sleep != null) sourceFields.push('totalSleepHours');
  if (rhr != null) sourceFields.push('restingHrBpm');

  const confidence = sourceFields.length >= 4 ? 'high' : sourceFields.length >= 2 ? 'medium' : 'low';

  const contextUsed: string[] = [];
  const missingness: string[] = [];

  if (hrv == null) missingness.push('hrvMs');
  if (strain == null) missingness.push('dailyStrain');
  if (sleep == null) missingness.push('totalSleepHours');

  // Support context (enriches interpretation, never changes level).
  const sc = supportContext;
  if (sc?.hiitSessionCountLast7Days != null && sc.hiitSessionCountLast7Days >= 3) {
    contextUsed.push(`${sc.hiitSessionCountLast7Days} HIIT sessions in last 7 days (high load context).`);
  }
  if (sc?.grapplingSessionCountLast7Days != null && sc.grapplingSessionCountLast7Days >= 3) {
    contextUsed.push(`${sc.grapplingSessionCountLast7Days} grappling sessions in last 7 days.`);
  }
  if (sc?.nutritionCaloriesToday != null) {
    contextUsed.push(`Nutrition today: ${sc.nutritionCaloriesToday} kcal${sc.nutritionProteinToday != null ? `, ${sc.nutritionProteinToday}g protein` : ''}.`);
  }
  if (sc?.healthConnectSleepHours != null) {
    contextUsed.push(`Health Connect sleep: ${sc.healthConnectSleepHours.toFixed(1)}h (corroborates WHOOP sleep).`);
  }

  const interpretationParts = [
    `WHOOP recovery: ${recovery}% (${level}).`,
    hrv != null ? `HRV: ${hrv.toFixed(0)} ms.` : null,
    strain != null ? `Yesterday's strain: ${strain.toFixed(1)}.` : null,
    sleep != null ? `Sleep: ${sleep.toFixed(1)}h.` : null,
    level === 'green' ? 'Indicators support higher training load today.' : null,
    level === 'yellow' ? 'Moderate recovery — a lighter or skill-focused session may be appropriate.' : null,
    level === 'red' ? 'Low recovery — consider active rest or light mobility.' : null,
  ].filter(Boolean) as string[];

  return {
    athleteId,
    date,
    mode: 'live',
    level,
    confidence,
    interpretation: interpretationParts.join(' '),
    contextUsed,
    missingness,
    sourceFields,
    metrics: {
      recoveryScore: recovery,
      hrvMs: hrv ?? null,
      restingHrBpm: rhr ?? null,
      dailyStrain: strain ?? null,
      sleepHours: sleep ?? null,
    },
    guardrails: GUARDRAILS,
  };
}
