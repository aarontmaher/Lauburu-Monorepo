import type { ReactNode } from 'react';
import { StyleSheet, View, Text } from 'react-native';
import { colors, spacing, typography } from '../../theme';
import { SourceChip } from './SourceChip';
import type { TruthLabel } from './_helpers';

/**
 * FactorRow — single-line readiness factor (e.g. sleep, load,
 * nutrition) with label + value + optional source state. Pure
 * presentation. Consumers MUST pass already-formatted values;
 * a missing value should be the literal string "—" so the row
 * never claims a number it does not have.
 */
export interface FactorRowProps {
  label: string;
  value: string;
  sourceState?: TruthLabel;
  trailing?: ReactNode;
}

export function FactorRow({ label, value, sourceState, trailing }: FactorRowProps) {
  return (
    <View style={styles.row}>
      <Text style={styles.label} numberOfLines={1}>{label}</Text>
      <View style={styles.valueWrap}>
        <Text style={styles.value} numberOfLines={1}>{value}</Text>
        {sourceState && <SourceChip state={sourceState} />}
        {trailing}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
    gap: spacing.sm,
  },
  label: { ...typography.body, color: colors.textPrimary, flexShrink: 1 },
  valueWrap: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  value: { ...typography.bodyEmphasis, color: colors.textPrimary },
});
