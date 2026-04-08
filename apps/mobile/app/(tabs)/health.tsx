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
import type { HealthMetricType, PermissionStatus, DailyMetrics, DerivedFeatures } from '@lauburu/shared';
import type { HealthFlag } from '@lauburu/shared';

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
              <View>
                <Text style={styles.workoutName}>
                  {w.sport_label ?? w.type}
                  {w.is_grappling ? ' 🥋' : ''}
                </Text>
                {w.source ? (
                  <Text style={styles.workoutSource}>{w.source}</Text>
                ) : null}
              </View>
              <View style={styles.workoutMetaCol}>
                <Text style={styles.workoutMeta}>
                  {w.duration_min}min
                  {w.calories ? ` · ${Math.round(w.calories)}cal` : ''}
                </Text>
                {(w.avg_hr || w.distance_m) ? (
                  <Text style={styles.workoutMeta}>
                    {w.avg_hr ? `${Math.round(w.avg_hr)}bpm avg` : ''}
                    {w.avg_hr && w.distance_m ? ' · ' : ''}
                    {w.distance_m ? `${(w.distance_m / 1000).toFixed(1)}km` : ''}
                  </Text>
                ) : null}
              </View>
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

// --- Flags card ---

function FlagsCard({ flags }: { flags: HealthFlag[] }) {
  if (flags.length === 0) return null;
  const colors: Record<string, string> = {
    warning: '#ff6b6b',
    info: '#e8ff47',
    positive: '#4ade80',
  };
  const icons: Record<string, string> = {
    warning: '⚠',
    info: 'ℹ',
    positive: '✓',
  };
  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Flags</Text>
      {flags.map((f, i) => (
        <Text key={i} style={[styles.flagText, { color: colors[f.type] }]}>
          {icons[f.type]} {f.label}
        </Text>
      ))}
    </View>
  );
}

// --- Trends card ---

const TREND_ARROWS: Record<string, string> = {
  improving: '↑',
  declining: '↓',
  stable: '→',
  increasing: '↑',
  decreasing: '↓',
};
const TREND_COLORS: Record<string, string> = {
  improving: '#4ade80',
  declining: '#ff6b6b',
  stable: '#999',
  increasing: '#e8ff47',
  decreasing: '#4ade80', // decreasing strain is good
};

function TrendsCard({ features }: { features: DerivedFeatures }) {
  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>7-Day Trends</Text>
      <View style={styles.trendsGrid}>
        <TrendItem
          label="Recovery"
          trend={features.recovery_trend}
          value={features.last_7d_recovery_mean}
          unit="%"
        />
        <TrendItem
          label="Strain"
          trend={features.strain_trend}
          value={features.last_7d_strain_mean}
          unit=""
        />
        <TrendItem
          label="HRV"
          trend={features.baseline_hrv_mean != null ? 'stable' : 'stable'}
          value={features.baseline_hrv_mean}
          unit="ms"
        />
        <TrendItem
          label="Sleep"
          trend={features.baseline_sleep_mean != null ? 'stable' : 'stable'}
          value={features.baseline_sleep_mean}
          unit="h"
        />
      </View>
      <View style={styles.trendMeta}>
        <Text style={styles.trendMetaText}>
          {features.workouts} workouts · {features.grappling_sessions} grappling
        </Text>
        <Text style={styles.trendMetaText}>
          Sources: {features.provenance.join(', ') || 'none'}
        </Text>
      </View>
    </View>
  );
}

function TrendItem({
  label,
  trend,
  value,
  unit,
}: {
  label: string;
  trend: string;
  value: number | null;
  unit: string;
}) {
  const arrow = TREND_ARROWS[trend] ?? '→';
  const color = TREND_COLORS[trend] ?? '#999';
  return (
    <View style={styles.trendItem}>
      <Text style={styles.trendLabel}>{label}</Text>
      <Text style={[styles.trendValue, { color }]}>
        {value != null ? `${Math.round(value * 10) / 10}${unit}` : '—'}
        {' '}
        {arrow}
      </Text>
    </View>
  );
}

// --- Backend sync card ---

function BackendSyncCard() {
  const persisting = useHealthStore((s) => s.persisting);
  const lastPersistedAt = useHealthStore((s) => s.lastPersistedAt);
  const lastPersistResult = useHealthStore((s) => s.lastPersistResult);
  const persistToBackend = useHealthStore((s) => s.persistToBackend);
  const authStatus = useAuthStore((s) => s.status);

  if (authStatus !== 'member') return null;

  return (
    <View style={styles.card}>
      <View style={styles.cardHeaderRow}>
        <Text style={styles.cardTitle}>Backend Sync</Text>
        <Pressable
          style={styles.syncButton}
          onPress={persistToBackend}
          disabled={persisting}>
          {persisting ? (
            <ActivityIndicator size="small" color="#e8ff47" />
          ) : (
            <Text style={styles.syncButtonText}>Save to Account</Text>
          )}
        </Pressable>
      </View>
      {lastPersistedAt && (
        <Text style={styles.syncTimestamp}>
          Last saved: {new Date(lastPersistedAt).toLocaleString()}
          {lastPersistResult
            ? ` · ${lastPersistResult.recordCount} days (${lastPersistResult.dateRange})`
            : ''}
        </Text>
      )}
      {!lastPersistedAt && (
        <Text style={styles.syncTimestamp}>
          Not yet saved to your account. Tap to persist.
        </Text>
      )}
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
  const features = useHealthStore((s) => s.features);
  const flags = useHealthStore((s) => s.flags);
  const error = useHealthStore((s) => s.error);
  const checkPermissions = useHealthStore((s) => s.checkPermissions);
  const requestPermissions = useHealthStore((s) => s.requestPermissions);
  const syncData = useHealthStore((s) => s.syncData);

  const authStatus = useAuthStore((s) => s.status);
  const user = useAuthStore((s) => s.user);

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

      {/* Flags */}
      {flags.length > 0 && <FlagsCard flags={flags} />}

      {/* Today's data */}
      {today && <TodayCard today={today} />}

      {/* 7-day trends */}
      {features && <TrendsCard features={features} />}

      {/* Backend persistence */}
      <BackendSyncCard />

      {/* Recent days */}
      {days.length > 0 && <RecentDays days={days} />}

      {/* Sync status summary */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Data Status</Text>
        <StatusRow
          label={platformName}
          status={
            !isAvailable
              ? 'unavailable'
              : !anyAuthorized
                ? 'not_connected'
                : days.length > 0
                  ? 'live'
                  : 'authorized_no_data'
          }
        />
        <StatusRow label="WHOOP" status="via_website" />
        <StatusRow label="Polar" status="via_website" />
        <StatusRow label="ErgZone" status="future" />
        <StatusRow label="Cronometer" status="future" />
        {lastSyncAt && (
          <Text style={styles.syncTimestamp}>
            Last sync: {new Date(lastSyncAt).toLocaleString()}
          </Text>
        )}
      </View>

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

type DataStatus =
  | 'live'
  | 'authorized_no_data'
  | 'not_connected'
  | 'unavailable'
  | 'denied'
  | 'via_website'
  | 'future';

const DATA_STATUS_LABELS: Record<DataStatus, { text: string; color: string }> = {
  live: { text: 'Live', color: '#4ade80' },
  authorized_no_data: { text: 'Connected — no data yet', color: '#e8ff47' },
  not_connected: { text: 'Not connected', color: '#999' },
  unavailable: { text: 'Not available', color: '#666' },
  denied: { text: 'Denied', color: '#ff6b6b' },
  via_website: { text: 'Via website sync', color: '#e8ff47' },
  future: { text: 'Coming soon', color: '#555' },
};

function StatusRow({ label, status }: { label: string; status: DataStatus }) {
  const info = DATA_STATUS_LABELS[status];
  return (
    <View style={styles.sourceRow}>
      <Text style={styles.sourceName}>{label}</Text>
      <View style={styles.statusDotRow}>
        <View style={[styles.statusDotSmall, { backgroundColor: info.color }]} />
        <Text style={[styles.sourceStatus, { color: info.color }]}>{info.text}</Text>
      </View>
    </View>
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
  workoutSource: { fontSize: 10, opacity: 0.35, marginTop: 1 },
  workoutMetaCol: { alignItems: 'flex-end' as const, gap: 1 },
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
  statusDotRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  statusDotSmall: { width: 6, height: 6, borderRadius: 3 },
  syncTimestamp: { fontSize: 11, opacity: 0.4, marginTop: 4 },

  // Flags
  flagText: { fontSize: 13, lineHeight: 18 },

  // Trends
  trendsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  trendItem: { width: '45%', gap: 2 },
  trendLabel: { fontSize: 12, opacity: 0.6 },
  trendValue: { fontSize: 16, fontWeight: '600' },
  trendMeta: { marginTop: 8, gap: 2 },
  trendMetaText: { fontSize: 11, opacity: 0.4 },
});
