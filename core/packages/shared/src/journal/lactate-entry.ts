/**
 * FS-021 Phase 1 — manual lactate entry validator.
 *
 * Pure helper that validates a single manual lactate entry per
 * `docs/FS021_HEALTH_INPUTS_EXPANSION_SPEC.md` § 1. No UI wiring,
 * no storage — the spec explicitly says "documentation and test
 * scaffolding only until Aaron approves a focused implementation
 * batch."
 *
 * Safety floor (spec § Safety rules):
 *
 * - Lactate is training/performance context. The validator
 *   refuses notes that contain clinical / causal / advice
 *   language so the field cannot drift into "you are recovered"
 *   territory at the data layer.
 * - Confidence is the literal `'low' | 'medium' | 'high'`
 *   trio matching `JournalNotesConfidence`.
 * - All entries are user-scoped — the validator surfaces a
 *   `userId` field but does not infer one. Callers must supply
 *   it from the authenticated session; the validator does not
 *   default to a shared id.
 *
 * Non-goals: BLE pairing, CSV import, threshold inference,
 * device-specific protocol handling. Those are research-only per
 * spec § 1 phases 2 / 3.
 */

export type LactateConfidence = 'low' | 'medium' | 'high';

export type LactateTimingRelativeToTraining =
  | 'pre_training'
  | 'mid_training'
  | 'post_training'
  | 'recovery'
  | 'unknown';

export type LactateSource = 'manual' | 'csv_import';

export interface ManualLactateEntryInput {
  userId: string | null;
  /** ISO-8601 datetime. */
  dateTime: string;
  /** mmol/L; non-negative finite number, ≤ 30 (anything above is implausible). */
  mmolPerL: number;
  /** Free-form protocol description, ≤ 200 chars. */
  testProtocol: string | null;
  /** Stage / workload description, ≤ 200 chars. */
  stageOrWorkload: string | null;
  /** Heart rate (bpm); non-negative integer, ≤ 250. */
  heartRateBpm: number | null;
  /** RPE 0..10 (Borg CR-10) or 6..20 (Borg 6-20) — caller picks scale. */
  rpe: number | null;
  /** Coarse timing relative to training. */
  timingRelativeToTraining: LactateTimingRelativeToTraining;
  /** Source flag — manual or csv_import. */
  source: LactateSource;
  /** User confidence in the reading. */
  confidence: LactateConfidence;
  /** Free-form note ≤ 500 chars. Banned terms enforced below. */
  notes: string | null;
}

export interface ManualLactateEntryAccepted {
  ok: true;
  entry: ManualLactateEntryInput & {
    /** Echoes the spec copy guardrail so consumers can render it verbatim. */
    contextOnlyDisclaimer: string;
  };
  warnings: string[];
}

export interface ManualLactateEntryRejected {
  ok: false;
  reason: string;
  field?: keyof ManualLactateEntryInput;
}

export type ManualLactateEntryResult =
  | ManualLactateEntryAccepted
  | ManualLactateEntryRejected;

const CONTEXT_ONLY_DISCLAIMER =
  'Lactate is training context. It does not diagnose recovery, fatigue, fitness, or health status.';

/**
 * Banned patterns — hard floor against clinical / causal language
 * leaking into the notes field. Mirrors the spec's safety rules.
 */
const BANNED_NOTE_PATTERNS: ReadonlyArray<{ re: RegExp; reason: string }> = [
  { re: /\b(diagnos(?:e|es|is|tic)|clinical(?:ly)?|treats?|cures?)\b/i, reason: 'clinical language banned in lactate notes' },
  { re: /\b(this caused|caused by|because of (?:my )?lactate)\b/i, reason: 'causal language banned in lactate notes' },
  { re: /\b(you (?:are|were|will) (?:fit|unfit|recovered|fatigued|ready|not ready|safe|in danger))\b/i, reason: 'directive readiness language banned in lactate notes' },
  { re: /\b(skip training|skip your session|train harder today|push harder today)\b/i, reason: 'training-prescription language banned in lactate notes' },
];

const STR_FIELD_CAPS: Partial<Record<keyof ManualLactateEntryInput, number>> = {
  testProtocol: 200,
  stageOrWorkload: 200,
  notes: 500,
};

const TIMING_SET: ReadonlySet<LactateTimingRelativeToTraining> = new Set([
  'pre_training',
  'mid_training',
  'post_training',
  'recovery',
  'unknown',
]);

const SOURCE_SET: ReadonlySet<LactateSource> = new Set(['manual', 'csv_import']);
const CONFIDENCE_SET: ReadonlySet<LactateConfidence> = new Set(['low', 'medium', 'high']);

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

export function validateManualLactateEntry(
  input: unknown,
): ManualLactateEntryResult {
  if (!input || typeof input !== 'object') {
    return { ok: false, reason: 'entry must be an object' };
  }
  const e = input as Record<string, unknown>;

  // userId — caller supplies, validator does not default. null is
  // allowed so an offline draft can be staged before sign-in.
  if (e.userId !== null && typeof e.userId !== 'string') {
    return { ok: false, reason: 'userId must be a string or null', field: 'userId' };
  }
  if (typeof e.userId === 'string' && e.userId.trim().length === 0) {
    return { ok: false, reason: 'userId must not be the empty string', field: 'userId' };
  }

  // dateTime — must be parseable ISO-8601.
  if (typeof e.dateTime !== 'string' || !Number.isFinite(Date.parse(e.dateTime))) {
    return { ok: false, reason: 'dateTime must be an ISO-8601 string', field: 'dateTime' };
  }

  // mmolPerL — non-negative finite, < 30 (above is physiologically
  // implausible; reject as a typo).
  if (!isFiniteNumber(e.mmolPerL) || e.mmolPerL < 0 || e.mmolPerL > 30) {
    return { ok: false, reason: 'mmolPerL must be a finite number in [0, 30]', field: 'mmolPerL' };
  }

  // Optional string fields — null or string within cap.
  for (const field of ['testProtocol', 'stageOrWorkload', 'notes'] as const) {
    const value = e[field];
    const cap = STR_FIELD_CAPS[field] ?? Infinity;
    if (value !== null && typeof value !== 'string') {
      return { ok: false, reason: `${field} must be a string or null`, field };
    }
    if (typeof value === 'string' && value.length > cap) {
      return { ok: false, reason: `${field} must be ≤ ${cap} chars`, field };
    }
  }

  // Optional numeric fields.
  if (e.heartRateBpm !== null) {
    if (!isFiniteNumber(e.heartRateBpm) || !Number.isInteger(e.heartRateBpm) || e.heartRateBpm < 0 || e.heartRateBpm > 250) {
      return { ok: false, reason: 'heartRateBpm must be a non-negative integer ≤ 250 (or null)', field: 'heartRateBpm' };
    }
  }
  if (e.rpe !== null) {
    if (!isFiniteNumber(e.rpe) || e.rpe < 0 || e.rpe > 20) {
      return { ok: false, reason: 'rpe must be a number in [0, 20] (CR-10 or 6-20 Borg) or null', field: 'rpe' };
    }
  }

  // Enum fields.
  if (typeof e.timingRelativeToTraining !== 'string' || !TIMING_SET.has(e.timingRelativeToTraining as LactateTimingRelativeToTraining)) {
    return { ok: false, reason: `timingRelativeToTraining must be one of ${[...TIMING_SET].join('/')}`, field: 'timingRelativeToTraining' };
  }
  if (typeof e.source !== 'string' || !SOURCE_SET.has(e.source as LactateSource)) {
    return { ok: false, reason: `source must be one of ${[...SOURCE_SET].join('/')}`, field: 'source' };
  }
  if (typeof e.confidence !== 'string' || !CONFIDENCE_SET.has(e.confidence as LactateConfidence)) {
    return { ok: false, reason: `confidence must be one of ${[...CONFIDENCE_SET].join('/')}`, field: 'confidence' };
  }

  // Banned-pattern check on notes — hard reject so clinical /
  // causal / advice copy cannot leak into the data layer.
  if (typeof e.notes === 'string' && e.notes.length > 0) {
    for (const banned of BANNED_NOTE_PATTERNS) {
      if (banned.re.test(e.notes)) {
        return { ok: false, reason: banned.reason, field: 'notes' };
      }
    }
  }

  // Soft warnings — surfaced to the UI but do not block storage.
  const warnings: string[] = [];
  if (e.heartRateBpm == null) warnings.push('heartRateBpm missing — context-only without HR pairing.');
  if (e.testProtocol == null && e.stageOrWorkload == null) warnings.push('No protocol or stage recorded — protocol context will help future analysis.');
  if (e.confidence === 'low') warnings.push('User confidence is low — surface a confirm-before-using-in-aggregate gate.');

  return {
    ok: true,
    entry: {
      userId: (e.userId as string | null),
      dateTime: e.dateTime as string,
      mmolPerL: e.mmolPerL,
      testProtocol: (e.testProtocol as string | null) ?? null,
      stageOrWorkload: (e.stageOrWorkload as string | null) ?? null,
      heartRateBpm: (e.heartRateBpm as number | null) ?? null,
      rpe: (e.rpe as number | null) ?? null,
      timingRelativeToTraining: e.timingRelativeToTraining as LactateTimingRelativeToTraining,
      source: e.source as LactateSource,
      confidence: e.confidence as LactateConfidence,
      notes: (e.notes as string | null) ?? null,
      contextOnlyDisclaimer: CONTEXT_ONLY_DISCLAIMER,
    },
    warnings,
  };
}

export { CONTEXT_ONLY_DISCLAIMER as LACTATE_CONTEXT_ONLY_DISCLAIMER };
