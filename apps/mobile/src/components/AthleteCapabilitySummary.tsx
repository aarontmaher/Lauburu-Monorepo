import { StyleSheet } from 'react-native';
import { Text, View } from '@/components/Themed';
import {
  getAthleteCapabilitySummary,
  type AthleteCapabilityMode,
} from '../services/athlete-capability-display';

export function AthleteCapabilitySummary({
  mode,
  detail,
  showNote = true,
}: {
  mode: AthleteCapabilityMode;
  detail?: string | null;
  showNote?: boolean;
}) {
  const summary = getAthleteCapabilitySummary(mode);
  return (
    <View style={styles.wrap}>
      <View style={[styles.badge, { borderColor: summary.borderColor }]}>
        <Text style={[styles.badgeText, { color: summary.color }]}>{summary.badge}</Text>
      </View>
      {showNote && (
        <Text style={styles.note}>{detail ?? summary.note}</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 6 },
  badge: {
    alignSelf: 'flex-start',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
    borderWidth: 1,
    backgroundColor: 'rgba(255,255,255,0.04)',
  },
  badgeText: {
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },
  note: {
    fontSize: 11,
    opacity: 0.62,
    lineHeight: 16,
  },
});
