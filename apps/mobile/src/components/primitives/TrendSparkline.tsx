import { StyleSheet, View } from 'react-native';
import { colors, radii, spacing } from '../../theme';

/**
 * TrendSparkline — minimal bar-style sparkline that renders a
 * fixed-height row of bars proportional to the values. Uses
 * stock React Native Views; no SVG required.
 *
 * Anti-rule: values MUST be already-sanitised numbers. Null /
 * undefined entries render as a faint placeholder bar at 10%
 * height so missing data is visible, not invisible.
 */
export interface TrendSparklineProps {
  /** Series of values; null = missing day. */
  values: ReadonlyArray<number | null | undefined>;
  /** Height of the sparkline row. Default 28. */
  height?: number;
  /** Bar tone — overrides the accent green default. */
  color?: string;
  /** Color used for null / undefined entries. Default: subtle grey. */
  missingColor?: string;
}

const PLACEHOLDER_RATIO = 0.1;

function sanitise(values: TrendSparklineProps['values']): Array<number | null> {
  return values.map((v) => (typeof v === 'number' && Number.isFinite(v) ? v : null));
}

function maxOf(values: Array<number | null>): number {
  let max = 0;
  for (const v of values) {
    if (v != null && v > max) max = v;
  }
  return max;
}

export function TrendSparkline({ values, height = 28, color, missingColor }: TrendSparklineProps) {
  const safe = sanitise(values);
  const max = maxOf(safe);
  const barColor = color ?? colors.accent;
  const phantomColor = missingColor ?? colors.borderEmphasis;
  return (
    <View style={[styles.row, { height }]}>
      {safe.map((v, idx) => {
        const ratio = v == null ? PLACEHOLDER_RATIO : max > 0 ? Math.max(PLACEHOLDER_RATIO, v / max) : PLACEHOLDER_RATIO;
        const isMissing = v == null;
        return (
          <View
            key={`spark-${idx}`}
            style={[
              styles.bar,
              {
                height: Math.max(2, Math.round(height * ratio)),
                backgroundColor: isMissing ? phantomColor : barColor,
                opacity: isMissing ? 0.5 : 1,
              },
            ]}
          />
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 2,
    paddingHorizontal: spacing.xs,
  },
  bar: { flex: 1, borderRadius: radii.sm, minWidth: 2 },
});
