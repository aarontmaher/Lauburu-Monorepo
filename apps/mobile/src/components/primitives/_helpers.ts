/**
 * Pure helpers shared by the design primitives.
 *
 * Kept separate from the React components so the contract can be
 * unit-tested without React Native. Anti-rule: helpers MUST NOT
 * import any react-native, expo, or other native module.
 */

import { colors } from '../../theme';

/**
 * Canonical six truth labels per
 * `docs/HEALTH_CONNECTIVITY_TRUTH_SPEC.md` § 3, plus two
 * additional UI-only states the prompt's redesign brief asked
 * for ('missing', 'stale'). Coders MUST NOT invent shorter or
 * longer phrasings; the SourceChip wraps these in a StatusPill.
 */
export const TRUTH_LABELS = [
  'live',
  'synced from hub',
  'imported summary',
  'seed/provisional',
  'setup required',
  'planned',
  'missing',
  'stale',
] as const;
export type TruthLabel = (typeof TRUTH_LABELS)[number];

export type Tone = 'fresh' | 'warning' | 'danger' | 'neutral' | 'info' | 'provisional';

export const TONE_COLOURS: Record<Tone, { fg: string; bg: string }> = {
  fresh: { fg: colors.toneFresh, bg: colors.accentSoft },
  warning: { fg: colors.toneStale, bg: colors.warningSoft },
  danger: { fg: colors.danger, bg: colors.dangerSoft },
  neutral: { fg: colors.toneMissing, bg: colors.neutralSoft },
  info: { fg: colors.toneSetupRequired, bg: colors.infoSoft },
  provisional: { fg: colors.toneProvisional, bg: colors.neutralSoft },
};

/** Map a TruthLabel to the StatusPill tone. */
export function mapTruthLabelToTone(label: TruthLabel | null | undefined): Tone {
  switch (label) {
    case 'live':
      return 'fresh';
    case 'synced from hub':
      return 'fresh';
    case 'imported summary':
      return 'info';
    case 'seed/provisional':
      return 'provisional';
    case 'setup required':
      return 'warning';
    case 'planned':
      return 'neutral';
    case 'stale':
      return 'warning';
    case 'missing':
      return 'neutral';
    default:
      return 'neutral';
  }
}

export type ConfidenceLevel = 'high' | 'medium' | 'low' | 'provisional' | 'unknown';

export function mapConfidenceToTone(level: ConfidenceLevel | null | undefined): Tone {
  switch (level) {
    case 'high':
      return 'fresh';
    case 'medium':
      return 'info';
    case 'low':
      return 'warning';
    case 'provisional':
      return 'provisional';
    default:
      return 'neutral';
  }
}

export type ReadinessBand = 'high' | 'medium' | 'low' | 'provisional';

/**
 * Canonical readiness band thresholds.
 *
 * - `null` / not-finite scores → 'provisional' (do NOT colour green).
 * - 0..33 → 'low'
 * - 34..66 → 'medium'
 * - 67..100 → 'high'
 *
 * Tied 1:1 to the colours in `theme.ts`; changing one without the
 * other breaks the contract test.
 */
export function readinessBandFromScore(score: number | null | undefined): ReadinessBand {
  if (typeof score !== 'number' || !Number.isFinite(score)) return 'provisional';
  if (score >= 67) return 'high';
  if (score >= 34) return 'medium';
  return 'low';
}

export function readinessBandColour(band: ReadinessBand): string {
  switch (band) {
    case 'high':
      return colors.readinessHigh;
    case 'medium':
      return colors.readinessMedium;
    case 'low':
      return colors.readinessLow;
    case 'provisional':
      return colors.readinessProvisional;
  }
}
