import { StyleSheet, View, Text } from 'react-native';
import { radii, spacing, typography } from '../../theme';
import { TONE_COLOURS, type Tone } from './_helpers';

/**
 * StatusPill — the base building block for SourceChip,
 * ConfidenceBadge, and any other pill-shaped status indicator.
 * Pure presentation; consumers map their domain enum to a
 * `Tone` via the helpers in `_helpers.ts`.
 */
export interface StatusPillProps {
  label: string;
  tone?: Tone;
  /** When true, render with a solid foreground bar dot — useful for live indicators. */
  dot?: boolean;
}

export function StatusPill({ label, tone = 'neutral', dot = false }: StatusPillProps) {
  const palette = TONE_COLOURS[tone];
  return (
    <View style={[styles.pill, { backgroundColor: palette.bg }]}>
      {dot && <View style={[styles.dot, { backgroundColor: palette.fg }]} />}
      <Text style={[styles.text, { color: palette.fg }]} numberOfLines={1}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: radii.pill,
    gap: 6,
    alignSelf: 'flex-start',
  },
  dot: { width: 6, height: 6, borderRadius: 3 },
  text: { ...typography.caption, fontWeight: '700' },
});
