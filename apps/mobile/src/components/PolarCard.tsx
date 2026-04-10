/**
 * PolarCard — compact placeholder surface for a future Polar integration.
 *
 * No live data today. The card exists so:
 *   (1) the Health tab shows Polar as a first-class source category,
 *       not just a muted row at the bottom of the Data Sources list.
 *   (2) the user can see exactly which three paths Polar could land
 *       through, ranked by coverage.
 *   (3) future real-integration code has an obvious place to land —
 *       the store + card pattern already matches WhoopCard, so wiring
 *       AccessLink OAuth or BLE HR later is just a matter of filling
 *       in polar-store.fetchToday() and swapping this placeholder body
 *       for a live-metrics grid.
 *
 * Explicitly NOT:
 *   - a fake "connected" row that implies live data when there is none
 *   - a button that actually attempts OAuth today (the AccessLink flow
 *     needs a client ID + redirect URI provisioned in a Polar developer
 *     account, neither of which exist yet)
 *   - a sensor-scan button (BLE path needs the native module + prebuild)
 */
import { useEffect } from 'react';
import { StyleSheet } from 'react-native';
import { Text, View } from '@/components/Themed';
import { usePolarStore } from '../store/polar-store';

export function PolarCard() {
  const status = usePolarStore((s) => s.status);
  const fetchToday = usePolarStore((s) => s.fetchToday);

  useEffect(() => {
    // Fires the stub once on mount so the store state is consistent;
    // the stub always resolves to 'not_connected' today.
    if (status === 'idle') fetchToday();
  }, [status, fetchToday]);

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <View style={styles.titleBlock}>
          <Text style={styles.cardTitle}>Polar</Text>
          <Text style={styles.sourceLabel}>scaffolded · not connected</Text>
        </View>
      </View>

      <Text style={styles.bodyText}>
        Polar data today reaches the app only when the Polar Flow app is
        set to write into Apple Health / Health Connect — so it arrives as
        generic metrics without Polar's richer readiness fields. A direct
        Polar integration is reserved for a future batch.
      </Text>

      <View style={styles.pathsBlock}>
        <Text style={styles.pathsHeader}>Future paths</Text>
        <Text style={styles.pathItem}>
          •{' '}
          <Text style={styles.pathBold}>Polar AccessLink</Text> — OAuth2 REST API
          for daily summaries and Recovery Pro / Nightly Recharge. Biggest
          coverage, most work.
        </Text>
        <Text style={styles.pathItem}>
          • <Text style={styles.pathBold}>Polar Flow export</Text> — CSV import
          from flow.polar.com. No OAuth, simplest first path.
        </Text>
        <Text style={styles.pathItem}>
          • <Text style={styles.pathBold}>BLE chest strap</Text> — direct
          pairing to an H9/H10/Verity Sense for live HR during a session.
          Complementary to AccessLink.
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 10,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  titleBlock: { gap: 2 },
  cardTitle: { fontSize: 18, fontWeight: '600' },
  sourceLabel: {
    fontSize: 11,
    opacity: 0.4,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  bodyText: { fontSize: 13, opacity: 0.65, lineHeight: 18 },

  pathsBlock: {
    gap: 4,
    paddingTop: 6,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.06)',
  },
  pathsHeader: {
    fontSize: 11,
    opacity: 0.4,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  pathItem: { fontSize: 12, opacity: 0.6, lineHeight: 17 },
  pathBold: { fontWeight: '600', color: '#d4e157' },
});
