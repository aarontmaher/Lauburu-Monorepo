/**
 * Sync Diagnostics — compact tester-facing card showing exactly what
 * the last Health Connect/Apple Health sync found. No tokens, no raw
 * health values — just record counts, provenance, and error state.
 */
import { useState } from 'react';
import { StyleSheet, Pressable, Platform } from 'react-native';
import { Text, View } from '@/components/Themed';
import { useHealthStore } from '../store/health-store';

export function SyncDiagnosticsCard() {
  const diag = useHealthStore((s) => s.lastSyncDiagnostics);
  const permissions = useHealthStore((s) => s.permissions);
  const historyAccess = useHealthStore((s) => s.historyAccess);
  const error = useHealthStore((s) => s.error);
  const [expanded, setExpanded] = useState(false);

  return (
    <View style={styles.card}>
      <Pressable onPress={() => setExpanded((v) => !v)} style={styles.header}>
        <Text style={styles.title}>Sync Diagnostics</Text>
        <Text style={styles.toggle}>{expanded ? 'Hide' : 'Show'}</Text>
      </Pressable>

      {expanded && (
        <View style={styles.body}>
          {/* Permissions */}
          <Text style={styles.label}>Permissions</Text>
          {permissions ? (
            <View style={styles.row}>
              <Text style={styles.mono}>available: {String(permissions.available)}</Text>
              {Object.entries(permissions.permissions).map(([key, val]) => (
                <Text key={key} style={[styles.mono, val === 'authorized' && styles.green]}>
                  {key}: {val}
                </Text>
              ))}
            </View>
          ) : (
            <Text style={styles.mono}>Not checked yet</Text>
          )}

          <Text style={styles.label}>History Access</Text>
          <Text style={styles.mono}>{historyAccess}</Text>

          {error && (
            <>
              <Text style={styles.label}>Last Error</Text>
              <Text style={[styles.mono, styles.red]}>{error}</Text>
            </>
          )}

          {diag ? (
            <>
              <Text style={styles.label}>Last Sync ({diag.timestamp.slice(0, 19).replace('T', ' ')})</Text>
              <Text style={styles.mono}>Window: last {diag.daysBack} days</Text>
              <Text style={styles.mono}>Normalized days: {diag.normalizedDays}</Text>
              <Text style={styles.mono}>Backend sync attempted: {String(diag.backendSyncAttempted)}</Text>
              {diag.error && <Text style={[styles.mono, styles.red]}>Error: {diag.error}</Text>}

              <Text style={styles.label}>Records Read</Text>
              {Object.entries(diag.recordCounts).map(([key, count]) => (
                <Text key={key} style={[styles.mono, count > 0 && styles.green]}>
                  {key}: {count}
                </Text>
              ))}

              <Text style={styles.label}>Source Provenance Detected</Text>
              {diag.provenanceDetected.length > 0 ? (
                diag.provenanceDetected.map((src, i) => (
                  <Text key={i} style={styles.mono}>{src}</Text>
                ))
              ) : (
                <Text style={styles.mono}>No source provenance found in records</Text>
              )}
            </>
          ) : (
            <Text style={styles.mono}>No sync has been performed yet.</Text>
          )}

          <Text style={styles.hint}>
            {Platform.OS === 'ios'
              ? 'If records are 0 across all types:\n'
                + '1. Open iOS Settings → Health → Data Access & Devices → Lauburu.\n'
                + '2. Tap "Turn On All" for the metrics you want (steps, HRV, resting heart rate, sleep, etc.).\n'
                + '3. Open iOS Health app → Browse → confirm recent entries exist.\n'
                + '4. Return here and tap Refresh.'
              : 'If records are 0 across all types:\n'
                + '1. Check Health Connect has data (open Health Connect app → Browse).\n'
                + '2. Samsung Health: Settings → Health Connect → App permissions → allow sharing.\n'
                + '3. Samsung Health: may need to open and let it sync before data appears in HC.\n'
                + '4. Try a wider sync window (backlog analysis uses 30-90 days).'}
          </Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { padding: 12, borderRadius: 10, backgroundColor: 'rgba(255,255,255,0.04)', gap: 4 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  title: { fontSize: 13, fontWeight: '600', opacity: 0.6 },
  toggle: { fontSize: 12, color: '#d4e157' },
  body: { gap: 4, marginTop: 6 },
  label: { fontSize: 11, fontWeight: '600', opacity: 0.5, textTransform: 'uppercase', marginTop: 6 },
  mono: { fontSize: 11, opacity: 0.7, fontFamily: 'SpaceMono' },
  green: { color: '#4ade80', opacity: 1 },
  red: { color: '#ff6b6b', opacity: 1 },
  row: { gap: 1 },
  hint: { fontSize: 11, opacity: 0.4, lineHeight: 16, marginTop: 8 },
});
