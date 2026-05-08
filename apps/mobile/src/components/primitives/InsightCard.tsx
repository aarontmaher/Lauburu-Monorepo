import type { ReactNode } from 'react';
import { StyleSheet, View, Text } from 'react-native';
import { colors, elevation, radii, spacing, typography } from '../../theme';

/**
 * InsightCard — compact card used for a single Coach insight or
 * pattern hint. Pure presentation; the body MUST be sanitised
 * upstream (no medical advice, no causation language).
 *
 * The optional `accentTone` paints a 3-pixel left bar in the
 * matching tone colour; the bar is informational only and MUST
 * NOT exceed the height of the card.
 */
export interface InsightCardProps {
  title: string;
  body: string;
  accentColor?: string;
  trailing?: ReactNode;
}

export function InsightCard({ title, body, accentColor, trailing }: InsightCardProps) {
  return (
    <View style={[styles.card, accentColor ? { borderLeftColor: accentColor, borderLeftWidth: 3 } : null]}>
      <View style={styles.header}>
        <Text style={styles.title} numberOfLines={2}>{title}</Text>
        {trailing}
      </View>
      <Text style={styles.body} numberOfLines={5}>{body}</Text>
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
  header: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: spacing.sm },
  title: { ...typography.bodyEmphasis, color: colors.textPrimary, flex: 1 },
  body: { ...typography.body, color: colors.textSecondary },
});
