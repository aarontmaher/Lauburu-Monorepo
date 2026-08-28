/**
 * HealthConnectDebugCard — admin/dev panel that surfaces the
 * Android Health Connect handshake state so a tester can see WHAT
 * happened after tapping Connect, not just an opaque alert.
 *
 * Visible only on Android, only when caller has already gated on
 * `showSourceDiagnostics` (admin email or dev unlock). Reads:
 *   - SDK availability via HealthConnectService.getAvailabilityDetail()
 *   - Last permission_requested event from the audit-event-store
 *   - Per-metric granted state from useHealthStore.permissions
 *   - Last error string from useHealthStore.error
 *   - Static list of permissions Lauburu requests (HC_PERMISSIONS)
 *
 * Includes a secondary "Open Health Connect" troubleshooting button
 * so the tester can verify the OS-side state directly. The primary
 * Connect button on the source sheet still calls requestPermission;
 * this card never substitutes for it.
 */
import { useEffect, useMemo, useState } from 'react';
import { Platform, Pressable, StyleSheet } from 'react-native';
import { Text, View } from '@/components/Themed';
import { useHealthStore } from '../store/health-store';
import { useAuditEventStore } from '../store/audit-event-store';

type AvailabilityCode = 'available' | 'provider_update_required' | 'sdk_unavailable' | 'unknown';

const REQUESTED_PERMISSION_RECORD_TYPES: readonly string[] = [
  'RestingHeartRate',
  'HeartRateVariabilityRmssd',
  'Steps',
  'ActiveCaloriesBurned',
  'HeartRate',
  'SleepSession',
  'ExerciseSession',
];

const METRIC_LABELS: Record<string, string> = {
  resting_heart_rate: 'Resting HR',
  hrv: 'HRV',
  steps: 'Steps',
  active_calories: 'Active calories',
  heart_rate: 'Heart rate',
  sleep: 'Sleep',
  workouts: 'Workouts',
};

function formatRelative(iso: string | null): string {
  if (!iso) return 'never';
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return 'never';
  const ageMs = Date.now() - t;
  if (ageMs < 60_000) return 'just now';
  if (ageMs < 3_600_000) return `${Math.round(ageMs / 60_000)}m ago`;
  if (ageMs < 86_400_000) return `${Math.round(ageMs / 3_600_000)}h ago`;
  return `${Math.round(ageMs / 86_400_000)}d ago`;
}

export function HealthConnectDebugCard() {
  const [availability, setAvailability] = useState<{ code: AvailabilityCode; rawStatus: string | null } | null>(null);
  const permissions = useHealthStore((s) => s.permissions);
  const error = useHealthStore((s) => s.error);
  const auditEvents = useAuditEventStore((s) => s.events);

  useEffect(() => {
    if (Platform.OS !== 'android') return;
    let cancelled = false;
    (async () => {
      try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const mod = require('../services/health.android');
        const Ctor = mod?.HealthConnectService;
        if (typeof Ctor !== 'function') {
          if (!cancelled) setAvailability({ code: 'unknown', rawStatus: 'native_module_unavailable' });
          return;
        }
        const svc = new Ctor();
        if (typeof svc.getAvailabilityDetail !== 'function') {
          if (!cancelled) setAvailability({ code: 'unknown', rawStatus: 'method_missing' });
          return;
        }
        const detail = await svc.getAvailabilityDetail();
        if (!cancelled) setAvailability({ code: detail.code as AvailabilityCode, rawStatus: detail.rawStatus ?? null });
      } catch {
        if (!cancelled) setAvailability({ code: 'unknown', rawStatus: null });
      }
    })();
    return () => { cancelled = true; };
  }, [permissions]);

  const lastRequestedAt = useMemo(() => {
    for (const ev of auditEvents) {
      if (ev.sourceId === 'health_connect' && ev.eventType === 'permission_requested') return ev.createdAt;
    }
    return null;
  }, [auditEvents]);

  const lastGrantedAt = useMemo(() => {
    for (const ev of auditEvents) {
      if (ev.sourceId === 'health_connect' && ev.eventType === 'permission_granted') return ev.createdAt;
    }
    return null;
  }, [auditEvents]);

  const lastDeniedAt = useMemo(() => {
    for (const ev of auditEvents) {
      if (ev.sourceId === 'health_connect' && ev.eventType === 'permission_denied') return ev.createdAt;
    }
    return null;
  }, [auditEvents]);

  if (Platform.OS !== 'android') return null;

  const grantedMetrics = Object.entries(permissions?.permissions ?? {})
    .filter(([, status]) => status === 'authorized')
    .map(([metric]) => METRIC_LABELS[metric] ?? metric);
  const grantedLine = grantedMetrics.length > 0 ? grantedMetrics.join(', ') : 'none';

  const onOpenHealthConnect = async () => {
    try {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const mod = require('react-native-health-connect');
      if (typeof mod?.openHealthConnectSettings === 'function') {
        mod.openHealthConnectSettings();
        return;
      }
    } catch {
      // fall through to system settings
    }
    try {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const { Linking } = require('react-native');
      Linking.openSettings().catch(() => { /* no-op */ });
    } catch { /* ignore */ }
  };

  return (
    <View style={styles.card}>
      <Text style={styles.title}>Health Connect debug</Text>
      <Row label="HC available" value={availability ? `${availability.code}${availability.rawStatus ? ` (${availability.rawStatus})` : ''}` : '…'} />
      <Row label="Permission requested" value={`${lastRequestedAt ? formatRelative(lastRequestedAt) : 'never'}${lastGrantedAt ? ` · granted ${formatRelative(lastGrantedAt)}` : lastDeniedAt ? ` · denied ${formatRelative(lastDeniedAt)}` : ''}`} />
      <Row label="Requested permissions" value={`${REQUESTED_PERMISSION_RECORD_TYPES.length} read · ${REQUESTED_PERMISSION_RECORD_TYPES.join(', ')}`} />
      <Row label="Granted permissions" value={grantedLine} />
      <Row label="Last error" value={error ?? 'none'} />
      <Pressable style={styles.btn} onPress={onOpenHealthConnect} accessibilityRole="button" accessibilityLabel="Open Health Connect">
        <Text style={styles.btnText}>Open Health Connect</Text>
      </Pressable>
      <Text style={styles.hint}>
        First tap of Connect calls Health Connect&rsquo;s permission API directly. Use this troubleshooting button only if the OS prompt did not appear.
      </Text>
    </View>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    padding: 12,
    borderRadius: 12,
    backgroundColor: 'rgba(120,180,255,0.06)',
    borderWidth: 1,
    borderColor: 'rgba(120,180,255,0.2)',
    gap: 6,
    marginTop: 8,
  },
  title: { fontSize: 13, fontWeight: '700', color: '#9ec5ff' },
  row: { flexDirection: 'row', justifyContent: 'space-between', gap: 8 },
  rowLabel: { fontSize: 11, opacity: 0.7, flex: 0, minWidth: 130 },
  rowValue: { fontSize: 11, opacity: 0.95, flex: 1, textAlign: 'right' },
  btn: {
    marginTop: 6,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(120,180,255,0.15)',
    borderWidth: 1,
    borderColor: 'rgba(120,180,255,0.3)',
  },
  btnText: { fontSize: 12, fontWeight: '700', color: '#9ec5ff' },
  hint: { fontSize: 11, opacity: 0.6, marginTop: 4 },
});
