/**
 * Lauburu mobile UI primitives — premium dark-theme building blocks.
 *
 * Import as:
 *   import { SourceChip, ConfidenceBadge, MetricCard, ... } from '@/src/components/primitives';
 *
 * See docs/UI_PRIMITIVES_INTEGRATION_GUIDE.md for slot-in instructions
 * per existing screen.
 */
export { StatusPill, type StatusPillProps } from './StatusPill';
export { SourceChip, type SourceChipProps } from './SourceChip';
export { ConfidenceBadge, type ConfidenceBadgeProps } from './ConfidenceBadge';
export { MetricCard, type MetricCardProps } from './MetricCard';
export { FactorRow, type FactorRowProps } from './FactorRow';
export { InsightCard, type InsightCardProps } from './InsightCard';
export { ReadinessGauge, type ReadinessGaugeProps } from './ReadinessGauge';
export { TrendSparkline, type TrendSparklineProps } from './TrendSparkline';

// Pure helpers (testable without React Native).
export {
  TRUTH_LABELS,
  TONE_COLOURS,
  mapTruthLabelToTone,
  mapConfidenceToTone,
  readinessBandFromScore,
  readinessBandColour,
  type TruthLabel,
  type Tone,
  type ConfidenceLevel,
  type ReadinessBand,
} from './_helpers';
