/**
 * Reusable upgrade prompt shown when a feature requires a higher tier.
 * Non-disruptive — shows a clean card explaining the requirement.
 */
import { StyleSheet } from 'react-native';
import { Text, View } from '@/components/Themed';
import { useGate } from '../hooks/useGate';
import type { Capability } from '@lauburu/shared';

export function UpgradePrompt({ capability }: { capability: Capability }) {
  const { tierLabel, tierColor, capLabel, capDescription } = useGate(capability);

  return (
    <View style={styles.container}>
      <Text style={styles.icon}>🔒</Text>
      <Text style={styles.title}>{capLabel}</Text>
      <Text style={styles.description}>{capDescription}</Text>
      <Text style={[styles.tierBadge, { color: tierColor, borderColor: tierColor }]}>
        {tierLabel} plan
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 20,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.03)',
    alignItems: 'center',
    gap: 6,
  },
  icon: { fontSize: 24 },
  title: { fontSize: 16, fontWeight: '600' },
  description: { fontSize: 13, opacity: 0.6, textAlign: 'center' },
  tierBadge: {
    fontSize: 13,
    fontWeight: '600',
    borderWidth: 1,
    borderRadius: 12,
    paddingVertical: 4,
    paddingHorizontal: 12,
    marginTop: 4,
  },
});
