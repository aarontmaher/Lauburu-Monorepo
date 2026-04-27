/**
 * Privacy-safe cohort/reference comparison for backlog analysis.
 *
 * Today this function ONLY emits `curated_reference` comparisons or
 * `none`. The `anonymous_cohort` comparison type is reserved — the
 * code path exists in the contract so future anonymized-aggregate
 * layers can be slotted in behind a privacy review, but this builder
 * intentionally refuses to return it.
 *
 * Forbidden by construction:
 *   - reading another athlete's private memory or artifacts
 *   - pulling any other user's trend candidates, raw records, or
 *     derived normalized/artifact data into this comparison
 *   - claiming "other athletes like you" statements that could only
 *     have come from identifiable records
 *
 * The curated reference ranges are static, general training knowledge
 * (e.g. adult sleep duration 7–9 hours) or conservative training
 * heuristics (e.g. ≥2 conditioning sessions per week as a low bar).
 * No individual athlete informs these numbers.
 */

import type {
  BacklogCohortComparison,
  BacklogTrendCandidate,
} from '../../contracts/backlog-analysis.types';

interface CuratedRule {
  low: number | null;
  high: number | null;
  label: string;
  basis: string;
}

const CURATED_REFERENCES: Partial<Record<BacklogTrendCandidate['kind'], CuratedRule>> = {
  sleep_consistency: {
    low: 7,
    high: 9,
    label: '7–9 hours',
    basis: 'General adult sleep duration reference range.',
  },
  training_frequency: {
    low: 3,
    high: 6,
    label: '3–6 sessions/week',
    basis: 'Typical conditioning volume for recreationally active adults.',
  },
  nutrition_protein_coverage: {
    low: 1.6,
    high: 2.2,
    label: '1.6–2.2 g/kg body weight',
    basis: 'General range for resistance-training adults; calibrated to body weight.',
  },
  hiit_frequency: {
    low: 1,
    high: 3,
    label: '1–3 sessions/week',
    basis: 'Conservative HIIT volume for athletes also training skill sports.',
  },
};

function extractNumber(statement: string): number | null {
  const match = statement.match(/([\d.]+)/);
  if (!match) return null;
  const n = Number(match[1]);
  return Number.isFinite(n) ? n : null;
}

/**
 * Build a cohort comparison for a single trend candidate. Many trends
 * don't have a meaningful general reference (e.g. grappling frequency,
 * HRV drift) — those return `comparisonType: 'none'` honestly.
 */
export function buildCohortComparisonForTrend(
  trend: BacklogTrendCandidate,
): BacklogCohortComparison {
  // Anonymous cohort never available from this builder.
  const rule = CURATED_REFERENCES[trend.kind];
  if (!rule) {
    return {
      comparisonType: 'none',
      cohortAvailable: false,
      cohortId: null,
      privacyLevel: 'aggregate_only',
      statement: 'No general reference range available for this pattern; comparison omitted.',
      confidenceImpact: 'none',
      missingnessNote: null,
    };
  }

  const value = extractNumber(trend.statement);
  if (value == null) {
    return {
      comparisonType: 'curated_reference',
      cohortAvailable: false,
      cohortId: null,
      privacyLevel: 'aggregate_only',
      statement: `General reference: ${rule.label}. ${rule.basis}`,
      confidenceImpact: 'none',
      missingnessNote: 'Could not parse a numeric value from the observed trend to compare.',
    };
  }

  const withinLow = rule.low == null || value >= rule.low;
  const withinHigh = rule.high == null || value <= rule.high;
  const within = withinLow && withinHigh;

  return {
    comparisonType: 'curated_reference',
    cohortAvailable: false,
    cohortId: null,
    privacyLevel: 'aggregate_only',
    statement: within
      ? `Within the general reference range of ${rule.label}. ${rule.basis}`
      : `Outside the general reference range of ${rule.label}. ${rule.basis}`,
    confidenceImpact: within ? 'raises' : 'lowers',
    missingnessNote: trend.confidence === 'low'
      ? 'Your own history is still short, so the comparison is indicative only.'
      : null,
  };
}

/**
 * Build a single summary-level cohort comparison that represents the
 * whole backlog run. Picks the strongest eligible trend that has a
 * curated reference; otherwise honestly reports `none`.
 */
export function buildBacklogCohortComparison(
  trends: BacklogTrendCandidate[],
): BacklogCohortComparison {
  const referenced = trends
    .map((t) => ({ trend: t, rule: CURATED_REFERENCES[t.kind] }))
    .filter((x): x is { trend: BacklogTrendCandidate; rule: CuratedRule } => Boolean(x.rule));

  if (referenced.length === 0) {
    return {
      comparisonType: 'none',
      cohortAvailable: false,
      cohortId: null,
      privacyLevel: 'aggregate_only',
      statement: 'No curated reference comparisons available for the trends detected so far.',
      confidenceImpact: 'none',
      missingnessNote: 'Cohort/aggregate comparison layer is not live yet; only curated training knowledge is used.',
    };
  }

  // Prefer highest-confidence, largest-observation trend.
  const bestTrend = referenced
    .slice()
    .sort((a, b) => {
      const rank = (c: 'low' | 'medium' | 'high') => (c === 'high' ? 2 : c === 'medium' ? 1 : 0);
      const byConf = rank(b.trend.confidence) - rank(a.trend.confidence);
      if (byConf !== 0) return byConf;
      return b.trend.observationCount - a.trend.observationCount;
    })[0];

  return buildCohortComparisonForTrend(bestTrend.trend);
}
