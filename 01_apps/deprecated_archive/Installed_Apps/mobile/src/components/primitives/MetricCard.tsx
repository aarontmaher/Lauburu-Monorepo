import type { ReactNode } from 'react';
import { StyleSheet, View, Text } from 'react-native';
import { colors, elevation, radii, spacing, typography } from '../../theme';
import { SourceChip } from './SourceChip';
import type { TruthLabel } from './_helpers';

/**
 * MetricCard — large numeric metric with optional unit + trailing
 * source chip + delta. Pure presentation. Consumers feed only
 * sanitised values; this card never invents formatting.
 *
 * Anti-rule: caller MUST pass `value` as a fully-formatted string
 * (so number formatting / fallback to "—" stays in the upstream
 * service). The card itself does not do conditional formatting.
 */
export interface MetricCardProps {
  label: string;
  /** Pre-formatted main value, e.g. "62 bpm" or "—". */
  value: string;
  unit?: string;
  /** Optional secondary line, e.g. "vs 7-day avg 64 bpm". */
  subtext?: string;
  /** Source label per docs/HEALTH_CONNECTIVITY_TRUTH_SPEC.md § 3. */
  sourceState?: TruthLabel;
  /** Optional trailing slot (e.g. <ConfidenceBadge level="medium"/>). */
  trailing?: ReactNode;
}

export function MetricCard({ label, value, unit, subtext, sourceState, trailing }: MetricCardProps) {
  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.label} numberOfLines={1}>{label}</Text>
        {trailing}
      </View>
      <View style={styles.valueRow}>
        <Text style={styles.value} numberOfLines={1}>{value}</Text>
        {unit && <Text style={styles.unit}>{unit}</Text>}
      </View>
      {subtext && <Text style={styles.subtext} numberOfLines={2}>{subtext}</Text>}
      {sourceState && (
        <View style={styles.sourceRow}>
          <SourceChip state={sourceState} />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.bgCard,
    borderRadius: radii.lg,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    gap: spacing.xs,
    ...elevation.card,
  },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: spacing.sm },
  label: { ...typography.label, color: colors.textSecondary, flex: 1 },
  valueRow: { flexDirection: 'row', alignItems: 'baseline', gap: spacing.xs, marginTop: spacing.xs },
  value: { ...typography.display, color: colors.textPrimary, lineHeight: 36 },
  unit: { ...typography.body, color: colors.textSecondary },
  subtext: { ...typography.caption, color: colors.textMuted },
  sourceRow: { marginTop: spacing.xs, flexDirection: 'row' },
});
