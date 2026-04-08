import { useEffect } from 'react';
import {
  StyleSheet,
  ScrollView,
  Pressable,
  ActivityIndicator,
  Platform,
} from 'react-native';
import { Text, View } from '@/components/Themed';
import { useHealthStore } from '../../src/store/health-store';
import { useAuthStore } from '../../src/store/auth-store';
import type { HealthMetricType, PermissionStatus, DailyMetrics } from '@lauburu/shared';

// --- Permission status row ---

const STATUS_LABELS: Record<PermissionStatus, { text: string; color: string }> = {
  authorized: { text: 'Authorized', color: '#4ade80' },
  denied: { text: 'Denied', color: '#ff6b6b' },
  not_determined: { text: 'Not requested', color: '#e8ff47' },
  unavailable: { text: 'Unavailable', color: '#666' },
};

const METRIC_LABELS: Record<HealthMetricType, string> = {
  heart_rate: 'Heart Rate',
  resting_heart_rate: 'Resting Heart Rate',
  hrv: 'Heart Rate Variability',
  sleep: 'Sleep',
  steps: 'Steps',
  active_calories: 'Active Calories',
  workouts: 'Workouts',
};

function PermissionRow({
  metric,
  status,
}: {
  metric: HealthMetricType;
  status: PermissionStatus;
}) {
  const info = STATUS_LABELS[status];
  return (
    <View style={styles.permRow}>
      <Text style={styles.permLabel}>{METRIC_LABELS[metric]}</Text>
      <Text style={[styles.permStatus, { color: info.color }]}>{info.text}</Text>
    </View>
  );
}

// --- Today's metrics card ---

function TodayCard({ today }: { today: DailyMetrics }) {
  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Today — {today.date}</Text>
      <View style={styles.metricsGrid}>
        <MetricBox label="Resting HR" value={today.resting_hr} unit="bpm" />
        <MetricBox label="HRV" value={today.hrv_ms} unit="ms" />
        <MetricBox label="Sleep" value={today.sleep_hours} unit="hrs" />
        <MetricBox label="Steps" value={today.step_count} unit="" />
        <MetricBox label="Active Cal" value={today.active_calories} unit="kcal" />
        <MetricBox
          label="Strain"
          value={today.daily_strain}
          unit="/21"
        />
      </View>
      {today.workouts && today.workouts.length > 0 && (
        <View style={styles.workoutSection}>
          <Text style={styles.workoutHeader}>
            Workouts ({today.workouts.length})
          </Text>
          {today.workouts.map((w, i) => (
            <View key={i} style={styles.workoutRow}>
              <Text style={styles.workoutName}>
                {w.sport_label ?? w.type}
                {w.is_grappling ? ' 🥋' : ''}
              </Text>
              <Text style={styles.workoutMeta}>
                {w.duration_min}min
                {w.calories ? ` · ${w.calories}cal` : ''}
              </Text>
            </View>
          ))}
        </View>
      )}
    </View>
  );
}

function MetricBox({
  label,
  value,
  unit,
}: {
  label: string;
  value?: number;
  unit: string;
}) {
  return (
    <View style={styles.metricBox}>
      <Text style={styles.metricValue}>
        {value != null ? String(Math.round(value * 10) / 10) : '—'}
      </Text>
      <Text style={styles.metricUnit}>{unit}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
    </View>
  );
}

// --- Recent days list ---

function RecentDays({ days }: { days: DailyMetrics[] }) {
  const recent = days.slice(-7).reverse();
  if (recent.length === 0) return null;

  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Recent Days</Text>
      {recent.map((day) => (
        <View key={day.date} style={styles.dayRow}>
          <Text style={styles.dayDate}>{day.date}</Text>
          <Text style={styles.dayMetrics}>
            {day.resting_hr ? `${day.resting_hr}bpm` : '—'}
            {' · '}
            {day.sleep_hours ? `${Math.round(day.sleep_hours * 10) / 10}h sleep` : '—'}
            {' · '}
            {day.step_count ? `${day.step_count} steps` : '—'}
          </Text>
        </View>
      ))}
    </View>
  );
}

// --- Main screen ---

export default function HealthScreen() {
  const permissions = useHealthStore((s) => s.permissions);
  const syncing = useHealthStore((s) => s.syncing);
  const lastSyncAt = useHealthStore((s) => s.lastSyncAt);
  const today = useHealthStore((s) => s.today);
  const days = useHealthStore((s) => s.days);
  const error = useHealthStore((s) => s.error);
  const checkPermissions = useHealthStore((s) => s.checkPermissions);
  const requestPermissions = useHealthStore((s) => s.requestPermissions);
  const syncData = useHealthStore((s) => s.syncData);

  const authStatus = useAuthStore((s) => s.status);
  const user = useAuthStore((s) => s.user);

  // Check permissions on mount
  useEffect(() => {
    checkPermissions();
  }, [checkPermissions]);

  const platformName = Platform.OS === 'ios' ? 'Apple HealthKit' : 'Health Connect';
  const isAvailable = permissions?.available ?? false;
  const anyAuthorized = permissions
    ? Object.values(permissions.permissions).some((s) => s === 'authorized')
    : false;

  const handleConnect = async () => {
    const granted = await requestPermissions();
    if (granted && user?.id) {
      syncData(user.id);
    }
  };

  const handleSync = () => {
    if (user?.id) syncData(user.id);
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}>
      <Text style={styles.heading}>Health</Text>

      {/* Source info */}
      <View style={styles.card}>
        <View style={styles.cardHeaderRow}>
          <Text style={styles.cardTitle}>{platformName}</Text>
          <Text
            style={[
              styles.availBadge,
              { color: isAvailable ? '#4ade80' : '#ff6b6b' },
            ]}>
            {isAvailable ? 'Available' : 'Not Available'}
          </Text>
        </View>

        {!isAvailable && (
          <Text style={styles.unavailNote}>
            {Platform.OS === 'ios'
              ? 'HealthKit requires a real device or simulator with Health app. Run expo prebuild first.'
              : 'Health Connect requires Android 14+ or the Health Connect app from Play Store.'}
          </Text>
        )}

        {isAvailable && !anyAuthorized && (
          <Pressable style={styles.connectButton} onPress={handleConnect}>
            <Text style={styles.connectText}>Connect {platformName}</Text>
          </Pressable>
        )}

        {isAvailable && anyAuthorized && (
          <>
            <View style={styles.syncRow}>
              <Text style={styles.syncLabel}>
                Last sync:{' '}
                {lastSyncAt
                  ? new Date(lastSyncAt).toLocaleTimeString()
                  : 'Never'}
              </Text>
              <Pressable
                style={styles.syncButton}
                onPress={handleSync}
                disabled={syncing}>
                {syncing ? (
                  <ActivityIndicator size="small" color="#e8ff47" />
                ) : (
                  <Text style={styles.syncButtonText}>Sync Now</Text>
                )}
              </Pressable>
            </View>

            {authStatus !== 'member' && (
              <Text style={styles.guestWarning}>
                Sign in on Settings tab to save health data to your account.
              </Text>
            )}
          </>
        )}

        {error && <Text style={styles.errorText}>{error}</Text>}
      </View>

      {/* Permissions detail */}
      {permissions && isAvailable && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Permissions</Text>
          {(Object.entries(permissions.permissions) as [HealthMetricType, PermissionStatus][]).map(
            ([metric, status]) => (
              <PermissionRow key={metric} metric={metric} status={status} />
            ),
          )}
        </View>
      )}

      {/* Today's data */}
      {today && <TodayCard today={today} />}

      {/* Recent days */}
      {days.length > 0 && <RecentDays days={days} />}

      {/* Supported sources info */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Supported Sources</Text>
        <View style={styles.sourceList}>
          <SourceRow
            name="Apple HealthKit"
            status={Platform.OS === 'ios' ? 'supported' : 'ios_only'}
          />
          <SourceRow
            name="Health Connect"
            status={Platform.OS === 'android' ? 'supported' : 'android_only'}
          />
          <SourceRow name="WHOOP" status="via_backend" />
          <SourceRow name="Polar" status="via_backend" />
          <SourceRow name="Cronometer" status="coming_soon" />
        </View>
      </View>
    </ScrollView>
  );
}

function SourceRow({
  name,
  status,
}: {
  name: string;
  status: 'supported' | 'ios_only' | 'android_only' | 'via_backend' | 'coming_soon';
}) {
  const labels: Record<string, { text: string; color: string }> = {
    supported: { text: 'Native', color: '#4ade80' },
    ios_only: { text: 'iOS only', color: '#666' },
    android_only: { text: 'Android only', color: '#666' },
    via_backend: { text: 'Via website', color: '#e8ff47' },
    coming_soon: { text: 'Coming soon', color: '#666' },
  };
  const info = labels[status];
  return (
    <View style={styles.sourceRow}>
      <Text style={styles.sourceName}>{name}</Text>
      <Text style={[styles.sourceStatus, { color: info.color }]}>{info.text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 20, gap: 16, paddingBottom: 40 },
  heading: { fontSize: 24, fontWeight: '700' },

  card: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 10,
  },
  cardHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  cardTitle: { fontSize: 18, fontWeight: '600' },

  availBadge: { fontSize: 12, fontWeight: '700', letterSpacing: 0.5 },
  unavailNote: { fontSize: 13, opacity: 0.6, lineHeight: 18 },

  connectButton: {
    backgroundColor: '#e8ff47',
    borderRadius: 10,
    padding: 14,
    alignItems: 'center',
    marginTop: 4,
  },
  connectText: { color: '#0a0a0a', fontSize: 16, fontWeight: '600' },

  syncRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  syncLabel: { fontSize: 13, opacity: 0.6 },
  syncButton: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#e8ff47',
  },
  syncButtonText: { color: '#e8ff47', fontSize: 13, fontWeight: '600' },

  guestWarning: {
    fontSize: 12,
    color: '#e8ff47',
    opacity: 0.8,
  },

  errorText: { fontSize: 13, color: '#ff6b6b' },

  // Permissions
  permRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
  },
  permLabel: { fontSize: 14 },
  permStatus: { fontSize: 13, fontWeight: '600' },

  // Today's metrics
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  metricBox: {
    width: '30%',
    alignItems: 'center',
    gap: 2,
    paddingVertical: 8,
  },
  metricValue: { fontSize: 24, fontWeight: '700', color: '#e8ff47' },
  metricUnit: { fontSize: 11, opacity: 0.5 },
  metricLabel: { fontSize: 11, opacity: 0.6, textAlign: 'center' },

  // Workouts
  workoutSection: { gap: 6, marginTop: 4 },
  workoutHeader: { fontSize: 14, fontWeight: '600', opacity: 0.8 },
  workoutRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 6,
    backgroundColor: 'rgba(255,255,255,0.03)',
  },
  workoutName: { fontSize: 13 },
  workoutMeta: { fontSize: 12, opacity: 0.5 },

  // Recent days
  dayRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.04)',
  },
  dayDate: { fontSize: 13, fontWeight: '600' },
  dayMetrics: { fontSize: 12, opacity: 0.6 },

  // Sources
  sourceList: { gap: 6 },
  sourceRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
  },
  sourceName: { fontSize: 14 },
  sourceStatus: { fontSize: 13, fontWeight: '600' },
});
