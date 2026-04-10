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
import { useTierStore } from '../../src/store/tier-store';
import { isExpoGo } from '../../src/services/expo-detect';
import { WhoopCard } from '../../src/components/WhoopCard';
import type { HealthMetricType, PermissionStatus, DailyMetrics, DerivedFeatures, CoachingResponse } from '@lauburu/shared';
import type { HealthFlag } from '@lauburu/shared';

// --- Permission status row ---

const STATUS_LABELS: Record<PermissionStatus, { text: string; color: string }> = {
  authorized: { text: 'Authorized', color: '#4ade80' },
  denied: { text: 'Denied', color: '#ff6b6b' },
  not_determined: { text: 'Not requested', color: '#d4e157' },
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

// --- Coaching card (structured training guidance) ---

function CoachingCard({ coaching }: { coaching: CoachingResponse }) {
  const statusColors: Record<string, string> = {
    recovered: '#4ade80',
    recovering: '#d4e157',
    fatigued: '#ff6b6b',
    unknown: '#666',
    good: '#4ade80',
    adequate: '#d4e157',
    poor: '#ff6b6b',
    balanced: '#4ade80',
    high: '#d4e157',
    low: '#999',
    overreaching: '#ff6b6b',
  };

  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Training Coaching</Text>

      {/* Today's recommendation */}
      <View style={styles.coachSection}>
        <Text style={styles.coachSectionLabel}>Today</Text>
        <Text style={styles.coachDetail}>{coaching.today_recommendation.detail}</Text>
      </View>

      {/* Recovery + Sleep + Load row */}
      <View style={styles.coachStatusRow}>
        <View style={styles.coachStatusItem}>
          <Text style={[styles.coachStatusValue, { color: statusColors[coaching.recovery.status] }]}>
            {coaching.recovery.status}
          </Text>
          <Text style={styles.coachStatusLabel}>Recovery</Text>
        </View>
        <View style={styles.coachStatusItem}>
          <Text style={[styles.coachStatusValue, { color: statusColors[coaching.sleep.status] }]}>
            {coaching.sleep.status}
          </Text>
          <Text style={styles.coachStatusLabel}>Sleep</Text>
        </View>
        <View style={styles.coachStatusItem}>
          <Text style={[styles.coachStatusValue, { color: statusColors[coaching.training_load.status] }]}>
            {coaching.training_load.status}
          </Text>
          <Text style={styles.coachStatusLabel}>Load</Text>
        </View>
      </View>

      {/* Grappling guidance */}
      <View style={styles.coachSection}>
        <Text style={styles.coachSectionLabel}>Grappling</Text>
        <Text style={styles.coachBody}>{coaching.grappling.summary}</Text>
        <Text style={styles.coachSuggestion}>{coaching.grappling.suggestion}</Text>
      </View>

      {/* Plan status */}
      {coaching.plan && coaching.plan.status !== 'no_plan' && (
        <View style={styles.coachSection}>
          <Text style={styles.coachSectionLabel}>Schedule</Text>
          <Text style={styles.coachBody}>{coaching.plan.summary}</Text>
        </View>
      )}

      {/* Recovery actions */}
      {coaching.recovery.actions.length > 0 && (
        <View style={styles.coachSection}>
          <Text style={styles.coachSectionLabel}>Recovery Actions</Text>
          {coaching.recovery.actions.map((a, i) => (
            <Text key={i} style={styles.coachAction}>• {a}</Text>
          ))}
        </View>
      )}

      {/* Preference effects */}
      {coaching.preference_effects && coaching.preference_effects.length > 0 && (
        <View style={styles.coachPrefs}>
          {coaching.preference_effects.map((e, i) => (
            <Text key={i} style={styles.coachPrefText}>⚙ {e}</Text>
          ))}
        </View>
      )}

      {/* Confidence */}
      <Text style={styles.coachConfidence}>
        Confidence: {coaching.confidence.level} — {coaching.confidence.note}
      </Text>
    </View>
  );
}

// --- Insights card (main training guidance) ---

import type { TrainingInsight, ReadinessLevel } from '@lauburu/shared';

const READINESS_COLORS: Record<ReadinessLevel, string> = {
  green: '#4ade80',
  yellow: '#d4e157',
  red: '#ff6b6b',
  grey: '#666',
};

function InsightsCard({ insights }: { insights: TrainingInsight }) {
  const color = READINESS_COLORS[insights.readiness];
  const statusColors: Record<string, string> = {
    good: '#4ade80',
    caution: '#d4e157',
    warning: '#ff6b6b',
    neutral: '#999',
  };

  return (
    <View style={styles.card}>
      {/* Readiness header */}
      <View style={styles.readinessHeader}>
        <View style={[styles.readinessDot, { backgroundColor: color }]} />
        <View style={styles.readinessText}>
          <Text style={[styles.readinessLabel, { color }]}>
            {insights.readiness_label}
          </Text>
          <Text style={styles.readinessSummary}>
            {insights.recommendation.summary}
          </Text>
        </View>
      </View>

      {/* Key metrics row */}
      {insights.key_metrics.length > 0 && (
        <View style={styles.keyMetricsRow}>
          {insights.key_metrics.map((m, i) => (
            <View key={i} style={styles.keyMetric}>
              <Text style={[styles.keyMetricValue, { color: statusColors[m.status] }]}>
                {m.value}
              </Text>
              <Text style={styles.keyMetricLabel}>{m.label}</Text>
            </View>
          ))}
        </View>
      )}

      {/* Reasons */}
      {insights.recommendation.reasons.length > 0 && (
        <View style={styles.reasonsList}>
          {insights.recommendation.reasons.map((r, i) => (
            <Text key={i} style={styles.reasonText}>• {r}</Text>
          ))}
        </View>
      )}

      {/* Positives */}
      {insights.positives.length > 0 && (
        <View style={styles.reasonsList}>
          {insights.positives.map((p, i) => (
            <Text key={i} style={[styles.reasonText, { color: '#4ade80' }]}>
              ✓ {p}
            </Text>
          ))}
        </View>
      )}

      {/* Concerns */}
      {insights.concerns.length > 0 && (
        <View style={styles.reasonsList}>
          {insights.concerns.map((c, i) => (
            <Text key={i} style={[styles.reasonText, { color: '#ff6b6b' }]}>
              ⚠ {c}
            </Text>
          ))}
        </View>
      )}

      {/* Data note */}
      <Text style={styles.dataNoteText}>{insights.data_note}</Text>
    </View>
  );
}

// --- Flags card ---

function FlagsCard({ flags }: { flags: HealthFlag[] }) {
  if (flags.length === 0) return null;
  const colors: Record<string, string> = {
    warning: '#ff6b6b',
    info: '#d4e157',
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
  increasing: '#d4e157',
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
  const canPersist = useTierStore((s) => s.can)('backend_persistence');

  if (authStatus !== 'member') return null;

  if (!canPersist) {
    return (
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Cloud Sync</Text>
        <Text style={styles.gateText}>
          Save health data to your account with the Starter plan.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.card}>
      <View style={styles.cardHeaderRow}>
        <Text style={styles.cardTitle}>Backend Sync</Text>
        <Pressable
          style={styles.syncButton}
          onPress={persistToBackend}
          disabled={persisting}>
          {persisting ? (
            <ActivityIndicator size="small" color="#d4e157" />
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

// --- Expo Go notice ---

function ExpoGoNotice() {
  return (
    <View style={styles.expoGoCard}>
      <Text style={styles.expoGoTitle}>Expo Go Mode</Text>
      <Text style={styles.expoGoBody}>
        Native health sync (HealthKit / Health Connect) requires a development
        build. Manual training logging, coaching, and check-ins work here.
      </Text>
      <Text style={styles.expoGoCommand}>
        npx expo prebuild --clean{'\n'}npx expo run:ios
      </Text>
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
  const insights = useHealthStore((s) => s.insights);
  const coaching = useHealthStore((s) => s.coaching);
  const error = useHealthStore((s) => s.error);
  const checkPermissions = useHealthStore((s) => s.checkPermissions);
  const requestPermissions = useHealthStore((s) => s.requestPermissions);
  const syncData = useHealthStore((s) => s.syncData);

  const authStatus = useAuthStore((s) => s.status);
  const user = useAuthStore((s) => s.user);

  const inExpoGo = isExpoGo();

  // Only check permissions in native builds — getHealthService crashes in Expo Go
  useEffect(() => {
    if (!inExpoGo) {
      checkPermissions();
    }
  }, [checkPermissions, inExpoGo]);

  const platformName = Platform.OS === 'ios' ? 'Apple HealthKit' : 'Health Connect';
  const isAvailable = inExpoGo ? false : (permissions?.available ?? false);
  const anyAuthorized = inExpoGo
    ? false
    : permissions
      ? Object.values(permissions.permissions).some((s) => s === 'authorized')
      : false;

  const handleConnect = async () => {
    if (inExpoGo) return;
    const granted = await requestPermissions();
    if (granted && user?.id) {
      syncData(user.id);
    }
  };

  const handleSync = () => {
    if (inExpoGo) return;
    if (user?.id) syncData(user.id);
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}>
      <Text style={styles.heading}>Health</Text>

      {isExpoGo() && <ExpoGoNotice />}

      {/* Source info */}
      <View style={styles.card}>
        <View style={styles.cardHeaderRow}>
          <Text style={styles.cardTitle}>{platformName}</Text>
          <Text
            style={[
              styles.availBadge,
              { color: isAvailable ? '#4ade80' : '#888' },
            ]}>
            {isAvailable ? 'Available' : 'Not set up'}
          </Text>
        </View>

        {!isAvailable && !inExpoGo && (
          <Text style={styles.unavailNote}>
            {Platform.OS === 'ios'
              ? "On-device Apple Health isn't connected here. Open the iOS Health app and grant Lauburu the metrics you want to sync."
              : "Health Connect isn't connected here. Requires Android 14+ or the Health Connect app."}
          </Text>
        )}

        {isAvailable && !anyAuthorized && (
          <>
            <Text style={styles.connectNote}>
              Connect to read heart rate, HRV, sleep, steps, calories, and workouts.
            </Text>
            <Pressable style={styles.connectButton} onPress={handleConnect}>
              <Text style={styles.connectText}>Connect {platformName}</Text>
            </Pressable>
          </>
        )}

        {isAvailable && anyAuthorized && (
          <>
            <View style={styles.syncRow}>
              <View>
                <Text style={styles.syncLabel}>
                  {syncing
                    ? 'Syncing health data...'
                    : lastSyncAt
                      ? `Last sync: ${new Date(lastSyncAt).toLocaleTimeString()}`
                      : 'Not synced yet'}
                </Text>
                {days.length > 0 && !syncing && (
                  <Text style={styles.syncDayCount}>
                    {days.length} day{days.length !== 1 ? 's' : ''} of data
                  </Text>
                )}
              </View>
              <Pressable
                style={[styles.syncButton, syncing && { opacity: 0.5 }]}
                onPress={handleSync}
                disabled={syncing}>
                {syncing ? (
                  <ActivityIndicator size="small" color="#d4e157" />
                ) : (
                  <Text style={styles.syncButtonText}>
                    {lastSyncAt ? 'Refresh' : 'Sync Now'}
                  </Text>
                )}
              </Pressable>
            </View>

            {days.length === 0 && !syncing && lastSyncAt && (
              <Text style={styles.noDataNote}>
                No health data found. Add sample data in the Health app, then sync again.
              </Text>
            )}

            {authStatus !== 'member' && (
              <Text style={styles.guestWarning}>
                Sign in to save health data to your account.
              </Text>
            )}
          </>
        )}

        {/* Only show the error line for genuine runtime errors. The
            "Health service unavailable" placeholder is already conveyed
            by the red Not Available badge + the explanatory note above,
            so duplicating it as a red error line reads like a crash. */}
        {error && error !== 'Health service unavailable' && (
          <Text style={styles.errorText}>{error}</Text>
        )}
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

      {/* Training insights — main guidance card */}
      {insights && <InsightsCard insights={insights} />}

      {/* Structured coaching */}
      {coaching && coaching.readiness.level !== 'grey' && (
        <CoachingCard coaching={coaching} />
      )}

      {/* Flags */}
      {flags.length > 0 && <FlagsCard flags={flags} />}

      {/* Today's data */}
      {today && <TodayCard today={today} />}

      {/* WHOOP — backend-fed, independent of on-device HealthKit */}
      <WhoopCard />

      {/* 7-day trends */}
      {features && <TrendsCard features={features} />}

      {/* Backend persistence */}
      <BackendSyncCard />

      {/* Recent days */}
      {days.length > 0 && <RecentDays days={days} />}

      {/* Data sources — summary of where Lauburu pulls signal from.
          WHOOP has its own live card above, so it only appears here as a
          pointer row. Apple Health status mirrors the card above. */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Data Sources</Text>
        <View style={styles.sourceList}>
          <SourceRow
            name="Apple Health"
            status={Platform.OS === 'ios'
              ? anyAuthorized ? 'connected' : isAvailable ? 'available' : 'not_set_up'
              : 'ios_only'}
          />
          <SourceRow name="WHOOP" status="live_backend" />
          <SourceRow name="Polar" status="via_backend" />
          <SourceRow name="ErgZone" status="coming_soon" />
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
  authorized_no_data: { text: 'Connected — no data yet', color: '#d4e157' },
  not_connected: { text: 'Not connected', color: '#999' },
  unavailable: { text: 'Not available', color: '#666' },
  denied: { text: 'Denied', color: '#ff6b6b' },
  via_website: { text: 'Via website sync', color: '#d4e157' },
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
  status: string;
}) {
  const labels: Record<string, { text: string; color: string }> = {
    connected: { text: 'Connected', color: '#4ade80' },
    available: { text: 'Available', color: '#a8b84a' },
    not_available: { text: 'Not available', color: '#666' },
    not_set_up: { text: 'Not set up', color: '#888' },
    supported: { text: 'Native', color: '#4ade80' },
    ios_only: { text: 'iOS only', color: '#555' },
    android_only: { text: 'Android only', color: '#555' },
    via_backend: { text: 'Via website sync', color: '#a8b84a' },
    live_backend: { text: 'Live · backend', color: '#4ade80' },
    coming_soon: { text: 'Coming soon', color: '#555' },
  };
  const info = labels[status] ?? { text: status, color: '#666' };
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
    backgroundColor: '#d4e157',
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
    borderColor: '#d4e157',
  },
  syncButtonText: { color: '#d4e157', fontSize: 13, fontWeight: '600' },

  guestWarning: {
    fontSize: 12,
    color: '#d4e157',
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
  metricValue: { fontSize: 24, fontWeight: '700', color: '#d4e157' },
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

  // Insights
  readinessHeader: { flexDirection: 'row', gap: 12, alignItems: 'flex-start' },
  readinessDot: { width: 14, height: 14, borderRadius: 7, marginTop: 3 },
  readinessText: { flex: 1, gap: 4 },
  readinessLabel: { fontSize: 18, fontWeight: '700' },
  readinessSummary: { fontSize: 14, opacity: 0.8, lineHeight: 20 },
  keyMetricsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: 8,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.06)',
    marginTop: 4,
  },
  keyMetric: { alignItems: 'center', gap: 2 },
  keyMetricValue: { fontSize: 18, fontWeight: '700' },
  keyMetricLabel: { fontSize: 11, opacity: 0.5 },
  reasonsList: { gap: 3, marginTop: 2 },
  reasonText: { fontSize: 13, opacity: 0.8, lineHeight: 18 },
  dataNoteText: { fontSize: 11, opacity: 0.35, marginTop: 6 },

  // Coaching
  coachSection: { gap: 4 },
  coachSectionLabel: {
    fontSize: 12,
    fontWeight: '600',
    textTransform: 'uppercase' as const,
    opacity: 0.5,
    letterSpacing: 0.5,
  },
  coachDetail: { fontSize: 14, opacity: 0.85, lineHeight: 20 },
  coachBody: { fontSize: 13, opacity: 0.7 },
  coachSuggestion: { fontSize: 13, color: '#d4e157', opacity: 0.9 },
  coachStatusRow: {
    flexDirection: 'row' as const,
    justifyContent: 'space-around' as const,
    paddingVertical: 8,
  },
  coachStatusItem: { alignItems: 'center' as const, gap: 2 },
  coachStatusValue: { fontSize: 14, fontWeight: '700', textTransform: 'capitalize' as const },
  coachStatusLabel: { fontSize: 10, opacity: 0.5 },
  coachAction: { fontSize: 13, opacity: 0.7, lineHeight: 18 },
  coachPrefs: { gap: 2, marginTop: 4 },
  coachPrefText: { fontSize: 11, color: '#d4e157', opacity: 0.6 },
  coachConfidence: { fontSize: 10, opacity: 0.3, marginTop: 6 },
  gateText: { fontSize: 13, opacity: 0.5, lineHeight: 18 },
  connectNote: { fontSize: 13, opacity: 0.6, lineHeight: 18 },
  syncDayCount: { fontSize: 11, opacity: 0.4, marginTop: 2 },
  noDataNote: { fontSize: 13, opacity: 0.5, lineHeight: 18, fontStyle: 'italic' },

  // Expo Go
  expoGoCard: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: 'rgba(212,225,87,0.08)',
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.2)',
    gap: 8,
  },
  expoGoTitle: { fontSize: 16, fontWeight: '600', color: '#d4e157' },
  expoGoBody: { fontSize: 13, opacity: 0.7, lineHeight: 18 },
  expoGoCommand: {
    fontSize: 11,
    fontFamily: 'SpaceMono',
    opacity: 0.5,
    backgroundColor: 'rgba(0,0,0,0.3)',
    padding: 8,
    borderRadius: 6,
    overflow: 'hidden',
  },

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
