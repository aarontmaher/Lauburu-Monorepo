import { StatusPill } from './StatusPill';
import { mapConfidenceToTone, type ConfidenceLevel } from './_helpers';

/**
 * ConfidenceBadge — surfaces the confidence level of a metric or
 * readiness reading. Anti-rule: a 'high' badge MUST NOT appear
 * alongside a `seed/provisional` source chip; the readiness
 * compute layer enforces this upstream.
 */
export interface ConfidenceBadgeProps {
  level: ConfidenceLevel;
  /** Optional label override. Default labels match the level. */
  label?: string;
}

const DEFAULT_LABELS: Record<ConfidenceLevel, string> = {
  high: 'high confidence',
  medium: 'medium confidence',
  low: 'low confidence',
  provisional: 'provisional',
  unknown: 'confidence unknown',
};

export function ConfidenceBadge({ level, label }: ConfidenceBadgeProps) {
  return (
    <StatusPill
      label={label ?? DEFAULT_LABELS[level]}
      tone={mapConfidenceToTone(level)}
    />
  );
}
