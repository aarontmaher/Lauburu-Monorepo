/**
 * TrainMachineSection — the one place that owns machine capture.
 *
 * Product ownership decision: machine capture belongs in Train
 * (part of session execution), NOT Health (which owns Apple Health
 * / WHOOP / enrichment / source status).
 *
 * Behavior:
 *   - Render an honest planned-state note for normal users.
 *   - Do not expose pair/scan/live-read controls until Bluetooth
 *     capture is product-ready and tested.
 */
import { StyleSheet } from 'react-native';
import { Text, View } from '@/components/Themed';

export function TrainMachineSection() {
  return (
    <View style={styles.notLinkedCard}>
      <Text style={styles.notLinkedTitle}>Bluetooth heart-rate sensors planned</Text>
      <Text style={styles.notLinkedBody}>
        Manual session logging is the supported path today. Polar may appear
        through Apple Health or Health Connect; direct Bluetooth heart-rate
        capture will stay hidden until it is ready to test.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  notLinkedCard: {
    padding: 10,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
    gap: 4,
  },
  notLinkedTitle: { fontSize: 13, fontWeight: '700', opacity: 0.8 },
  notLinkedBody: { fontSize: 11, opacity: 0.6, lineHeight: 15 },
});
