import { StyleSheet, View, Text } from 'react-native';
import { colors, spacing, typography } from '../../theme';
import { ConfidenceBadge } from './ConfidenceBadge';
import { readinessBandFromScore, readinessBandColour, type ConfidenceLevel } from './_helpers';

/**
 * ReadinessGauge — large central readiness number with a band
 * colour ring + an optional confidence badge.
 *
 * Implementation note: this is a static circular ring (no partial
 * fill) because `react-native-svg` is not installed. When it
 * lands, this component will be upgraded to a partial-arc fill
 * proportional to the score. Today the design rules:
 *
 *  - Provisional / null / non-finite scores show "—" centered.
 *  - The ring colour reflects the band only; the partial fill
 *    is omitted to avoid overclaiming precision.
 *  - The accent green ring is reserved for high-band readings
 *    with high or medium confidence. Provisional readings use
 *    the slate provisional tone.
 */
export interface ReadinessGaugeProps {
  /** 0..100 numeric readiness score. Null / undefined → provisional ring + "—". */
  score: number | null | undefined;
  confidence?: ConfidenceLevel;
  /** Diameter in pixels. Default 144 — sized for the Health tab top card. */
  size?: number;
}

export function ReadinessGauge({ score, confidence, size = 144 }: ReadinessGaugeProps) {
  const band = readinessBandFromScore(score);
  const ringColour = readinessBandColour(band);
  const display = typeof score === 'number' && Number.isFinite(score) ? `${Math.round(score)}` : '—';
  const ringWidth = Math.max(8, Math.round(size / 16));
  return (
    <View style={styles.wrap}>
      <View
        style={[
          styles.ring,
          {
            width: size,
            height: size,
            borderRadius: size / 2,
            borderWidth: ringWidth,
            borderColor: ringColour,
          },
        ]}>
        <Text style={[styles.score, { color: ringColour }]}>{display}</Text>
        <Text style={styles.label}>READINESS</Text>
      </View>
      {confidence && (
        <View style={styles.badgeRow}>
          <ConfidenceBadge level={confidence} />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', gap: spacing.sm },
  ring: {
    backgroundColor: colors.bgElevated,
    alignItems: 'center',
    justifyContent: 'center',
  },
  score: { ...typography.display, lineHeight: 38, marginTop: 4 },
  label: { ...typography.label, color: colors.textMuted, marginTop: 4 },
  badgeRow: { flexDirection: 'row' },
});
