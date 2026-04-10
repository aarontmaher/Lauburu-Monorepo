/**
 * WhoopCard — mobile surface for the backend-fed WHOOP day record.
 *
 * This is the mobile app's first real backend-health surface. WHOOP is NOT
 * ingested on-device (no OAuth, no tokens in the app). All data flows from
 * the Railway WHOOP MCP through the Supabase whoop-bridge to this card.
 *
 * Honest state handling:
 *   idle / loading → spinner
 *   error          → red note + retry
 *   ready, no day  → "no data yet"
 *   ready, stale   → amber warning with relative source age
 *   ready, fresh   → full readiness grid
 *
 * "Stale" here means: source_updated_at is more than STALE_SOURCE_HOURS ago.
 * A day row can be present (recovery + sleep) while today's workout has not
 * yet landed — we surface that honestly rather than claim "all synced".
 */
import { useEffect } from 'react';
import { StyleSheet, Pressable, ActivityIndicator } from 'react-native';
import { Text, View } from '@/components/Themed';
import { useWhoopStore, type WhoopDay } from '../store/whoop-store';

const STALE_SOURCE_HOURS = 6;

function readinessColor(score: number | null): string {
  if (score == null) return '#666';
  if (score >= 67) return '#4ade80'; // green
  if (score >= 34) return '#d4e157'; // yellow
  return '#ff6b6b'; // red
}

function readinessLabel(score: number | null): string {
  if (score == null) return 'No data';
  if (score >= 67) return 'Recovered';
  if (score >= 34) return 'Moderate';
  return 'Low';
}

function formatRelative(iso: string | null): string {
  if (!iso) return 'unknown';
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return 'unknown';
  const diffMs = Date.now() - then;
  const mins = Math.round(diffMs / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

function isSourceStale(day: WhoopDay): boolean {
  if (!day.source_updated_at) return true;
  const t = new Date(day.source_updated_at).getTime();
  if (Number.isNaN(t)) return true;
  return Date.now() - t > STALE_SOURCE_HOURS * 60 * 60 * 1000;
}

function isToday(date: string): boolean {
  const today = new Date().toISOString().slice(0, 10);
  return date === today;
}

function MetricBox({
  label,
  value,
  unit,
}: {
  label: string;
  value: number | string | null;
  unit?: string;
}) {
  const display = value == null || value === '' ? '—' : String(value);
  return (
    <View style={styles.metricBox}>
      <Text style={styles.metricValue}>
        {display}
        {unit && value != null ? <Text style={styles.metricUnit}>{unit}</Text> : null}
      </Text>
      <Text style={styles.metricLabel}>{label}</Text>
    </View>
  );
}

export function WhoopCard() {
  const status = useWhoopStore((s) => s.status);
  const day = useWhoopStore((s) => s.day);
  const fetchedAt = useWhoopStore((s) => s.fetchedAt);
  const error = useWhoopStore((s) => s.error);
  const fetchToday = useWhoopStore((s) => s.fetchToday);

  useEffect(() => {
    // Fetch on mount if nothing yet. No auto-refresh interval in this batch;
    // explicit Refresh button keeps the surface predictable.
    if (status === 'idle') {
      fetchToday();
    }
  }, [status, fetchToday]);

  const isLoading = status === 'loading';
  const isReady = status === 'ready' && day != null;
  const isError = status === 'error';
  const stale = isReady && day ? isSourceStale(day) : false;
  const workoutCount = day?.workouts?.length ?? 0;
  const missingWorkoutToday =
    isReady && day && isToday(day.date) && workoutCount === 0;

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <View style={styles.titleBlock}>
          <Text style={styles.cardTitle}>WHOOP</Text>
          <Text style={styles.sourceLabel}>Backend-fed · read-only</Text>
        </View>
        <Pressable
          onPress={fetchToday}
          disabled={isLoading}
          style={[styles.refreshBtn, isLoading && { opacity: 0.5 }]}
          hitSlop={8}>
          {isLoading ? (
            <ActivityIndicator size="small" color="#d4e157" />
          ) : (
            <Text style={styles.refreshText}>Refresh</Text>
          )}
        </Pressable>
      </View>

      {/* Error state */}
      {isError && (
        <View style={styles.noticeRow}>
          <View style={[styles.statusDot, { backgroundColor: '#ff6b6b' }]} />
          <Text style={styles.noticeError}>
            {error ?? 'WHOOP fetch failed'}
          </Text>
        </View>
      )}

      {/* Idle / first-load state */}
      {!isReady && !isError && !isLoading && (
        <Text style={styles.cardBody}>Waiting to fetch backend WHOOP data…</Text>
      )}

      {/* Loading with no prior data */}
      {isLoading && !day && (
        <Text style={styles.cardBody}>Fetching latest WHOOP day…</Text>
      )}

      {/* Ready state */}
      {isReady && day && (
        <>
          {/* Headline readiness */}
          <View style={styles.readinessRow}>
            <View
              style={[
                styles.readinessDot,
                { backgroundColor: readinessColor(day.recovery_score) },
              ]}
            />
            <Text
              style={[
                styles.readinessLabel,
                { color: readinessColor(day.recovery_score) },
              ]}>
              {day.recovery_score != null
                ? `${day.recovery_score}%`
                : '—'}{' '}
              {readinessLabel(day.recovery_score)}
            </Text>
            <Text style={styles.readinessDate}>{day.date}</Text>
          </View>

          {/* Key metrics grid */}
          <View style={styles.metricsGrid}>
            <MetricBox label="HRV" value={day.hrv_ms} unit="ms" />
            <MetricBox label="Resting HR" value={day.resting_hr} unit="bpm" />
            <MetricBox label="Sleep" value={day.sleep_hours} unit="h" />
            <MetricBox
              label="Sleep perf"
              value={day.sleep_performance_pct}
              unit="%"
            />
            <MetricBox
              label="Strain"
              value={day.daily_strain}
              unit="/21"
            />
            <MetricBox label="Workouts" value={workoutCount} />
          </View>

          {/* Honest freshness + gap notices */}
          <View style={styles.footerRow}>
            <Text style={styles.freshnessText}>
              Source updated {formatRelative(day.source_updated_at)}
              {fetchedAt ? ` · fetched ${formatRelative(fetchedAt)}` : ''}
            </Text>
          </View>

          {stale && (
            <View style={styles.noticeRow}>
              <View style={[styles.statusDot, { backgroundColor: '#d4e157' }]} />
              <Text style={styles.noticeWarn}>
                Source is stale (&gt;{STALE_SOURCE_HOURS}h). Backend tail-poll
                runs every 15 min — try Refresh in a moment.
              </Text>
            </View>
          )}

          {missingWorkoutToday && !stale && (
            <View style={styles.noticeRow}>
              <View style={[styles.statusDot, { backgroundColor: '#d4e157' }]} />
              <Text style={styles.noticeWarn}>
                Recovery and sleep are here, but today's workout hasn't reached
                the backend yet. Ends and uploads from the WHOOP strap surface
                on the next sync tick.
              </Text>
            </View>
          )}
        </>
      )}
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
  cardBody: { fontSize: 13, opacity: 0.6, lineHeight: 18 },

  refreshBtn: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#d4e157',
  },
  refreshText: { color: '#d4e157', fontSize: 13, fontWeight: '600' },

  readinessRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    flexWrap: 'wrap',
  },
  readinessDot: { width: 12, height: 12, borderRadius: 6 },
  readinessLabel: { fontSize: 18, fontWeight: '700' },
  readinessDate: { fontSize: 12, opacity: 0.4, marginLeft: 'auto' },

  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 4,
  },
  metricBox: {
    minWidth: '30%',
    flexGrow: 1,
    padding: 10,
    borderRadius: 8,
    backgroundColor: 'rgba(255,255,255,0.03)',
    gap: 2,
  },
  metricValue: { fontSize: 16, fontWeight: '700', color: '#d4e157' },
  metricUnit: { fontSize: 11, opacity: 0.5, fontWeight: '500' },
  metricLabel: { fontSize: 11, opacity: 0.5 },

  footerRow: { marginTop: 2 },
  freshnessText: { fontSize: 11, opacity: 0.4 },

  noticeRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    paddingVertical: 8,
    paddingHorizontal: 10,
    borderRadius: 8,
    backgroundColor: 'rgba(212,225,87,0.06)',
  },
  statusDot: { width: 8, height: 8, borderRadius: 4, marginTop: 5 },
  noticeWarn: { fontSize: 12, color: '#d4e157', flex: 1, lineHeight: 16 },
  noticeError: { fontSize: 12, color: '#ff6b6b', flex: 1, lineHeight: 16 },
});
