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
import { ATHLETE_CAPABILITY_COPY } from '../services/athlete-capability-display';
import { AthleteCapabilitySummary } from './AthleteCapabilitySummary';

const STALE_SOURCE_HOURS = 6;

function readinessColor(score: number | null): string {
  if (score == null) return '#666';
  if (score >= 67) return '#4ade80'; // green
  if (score >= 34) return '#d4e157'; // yellow
  return '#ff6b6b'; // red
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

/**
 * Returns:
 *   'unknown' — no freshness timestamp in the payload at all
 *   'stale'   — timestamp is older than STALE_SOURCE_HOURS
 *   'fresh'   — timestamp is within the stale window
 */
function sourceFreshness(day: WhoopDay): 'unknown' | 'stale' | 'fresh' {
  if (!day.source_updated_at) return 'unknown';
  const t = new Date(day.source_updated_at).getTime();
  if (Number.isNaN(t)) return 'unknown';
  const age = Date.now() - t;
  return age > STALE_SOURCE_HOURS * 60 * 60 * 1000 ? 'stale' : 'fresh';
}

function isToday(date: string): boolean {
  const today = new Date().toISOString().slice(0, 10);
  return date === today;
}

/**
 * Format a WHOOP numeric metric sensibly:
 *   - integers rendered as integers (no trailing .0)
 *   - `decimals` (default 1) for floats
 *   - null/undefined/NaN → em-dash
 */
function formatNumber(
  value: number | string | null | undefined,
  decimals = 1,
): string {
  if (value == null || value === '') return '—';
  const n = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(n)) return '—';
  if (Number.isInteger(n)) return String(n);
  return n.toFixed(decimals);
}

function MetricBox({
  label,
  value,
  unit,
}: {
  label: string;
  value: string;
  unit?: string;
}) {
  const hasValue = value !== '—';
  return (
    <View style={styles.metricBox}>
      <Text style={styles.metricValue}>
        {value}
        {unit && hasValue ? <Text style={styles.metricUnit}>{unit}</Text> : null}
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
  const hasDay = day != null;
  const isReady = status === 'ready' && hasDay;
  const isError = status === 'error';
  const freshness = hasDay && day ? sourceFreshness(day) : 'unknown';
  const workoutCount = day?.workouts?.length ?? 0;
  const latestDayIsToday = hasDay && day ? isToday(day.date) : false;

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <View style={styles.titleBlock}>
          <Text style={styles.cardTitle}>WHOOP reference</Text>
          <Text style={styles.sourceLabel}>Optional calibration source — not required</Text>
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
          <Text selectable style={styles.noticeError}>
            {error ?? 'WHOOP fetch failed'}
          </Text>
          {hasDay && day && (
            <Text style={styles.noticeStale}>
              Using last available reference data ({day.date}). Readiness keeps working from Apple Health, training, and imported history.
            </Text>
          )}
        </View>
      )}

      {/* Idle / first-load state — never use generic "waiting for
          backend" copy that can read as a stuck failure. Frame the
          card explicitly as optional reference, with custom readiness
          as the working primary. */}
      {!isReady && !isError && !isLoading && (
        <>
          <Text style={styles.cardBody}>Optional WHOOP reference — not required.</Text>
          <Text style={[styles.cardBody, { fontSize: 11, opacity: 0.55 }]}>
            Readiness is your primary score, derived from Apple Health, training, nutrition, and imported WHOOP history. Tap Refresh to attempt a WHOOP calibration pull.
          </Text>
        </>
      )}
      {/* Persistent error state — make the optional/fallback framing
          explicit so a non-allowlisted account doesn't read the empty
          card as "the app is broken". Custom readiness keeps running. */}
      {isError && (
        <Text style={[styles.cardBody, { fontSize: 11, opacity: 0.55, marginTop: -4 }]}>
          WHOOP Direct unavailable — using your readiness from Apple Health, training, and imported history.
        </Text>
      )}

      {/* Loading with no prior data */}
      {isLoading && !day && (
        <Text style={styles.cardBody}>Fetching latest WHOOP day…</Text>
      )}

      {/* Loading with cached data */}
      {isLoading && hasDay && day && (
        <View style={styles.noticeRow}>
          <View style={[styles.statusDot, { backgroundColor: '#d4e157' }]} />
          <Text style={styles.noticeWarn}>
            Checking backend. Showing last available WHOOP record for {day.date}.
          </Text>
        </View>
      )}

      {/* Any available day */}
      {hasDay && day && (
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
              recovery score
            </Text>
            <Text style={styles.readinessDate}>{day.date}</Text>
          </View>

          {/* Only badge as "seed-backed / provisional" when recovery_score
              is missing. When the score is present, this IS a live
              scored cycle from the WHOOP API — no need to hedge. */}
          {day.recovery_score == null && (
            <AthleteCapabilitySummary
              mode="missing_whoop_native"
              detail="Recovery score not in this cycle yet. WHOOP will score it after your next sleep."
            />
          )}

          {/* Key metrics grid */}
          <View style={styles.metricsGrid}>
            <MetricBox label="HRV" value={formatNumber(day.hrv_ms, 1)} unit=" ms" />
            <MetricBox
              label="Resting HR"
              value={formatNumber(day.resting_hr, 0)}
              unit=" bpm"
            />
            <MetricBox label="Sleep" value={formatNumber(day.sleep_hours, 1)} unit=" h" />
            <MetricBox
              label="Sleep perf"
              value={formatNumber(day.sleep_performance_pct, 0)}
              unit="%"
            />
            <MetricBox
              label="Day strain"
              value={formatNumber(day.daily_strain, 1)}
            />
            <MetricBox label="Workouts" value={String(workoutCount)} />
          </View>

          {/* Per-domain missingness line — makes "partial" actionable
              by naming exactly which domains the bridge returned null
              for. Testers can see at a glance whether it's a cycle-
              not-scored-yet case (normal, time-of-day) vs a genuine
              fetch/mapping gap. Hidden when everything is present. */}
          {(() => {
            const missing: string[] = [];
            if (day.recovery_score == null) missing.push('recovery');
            if (day.hrv_ms == null) missing.push('HRV');
            if (day.resting_hr == null) missing.push('RHR');
            if (day.sleep_hours == null) missing.push('sleep');
            if (workoutCount === 0) missing.push('workouts');
            if (missing.length === 0) return null;
            const allMissing = missing.length >= 4;
            return (
              <Text style={[styles.freshnessText, { color: allMissing ? '#ff6b6b' : '#d4e157' }]}>
                {allMissing
                  ? `Missing ${missing.join(', ')} — likely WHOOP bridge isn\u2019t linked to this account. Check EXPO_PUBLIC_WHOOP_BRIDGE_OWNER_IDS contains your user.id.`
                  : `Missing: ${missing.join(', ')}. WHOOP scores these after your next sleep / workout sync.`}
              </Text>
            );
          })()}

          {/* Honest freshness line — labels a scored cycle as "cycle"
              when recovery_score is present (live WHOOP Direct), else
              falls back to "snapshot" wording for raw payload-only
              states. "Seed" was the old seed-only era — dropped now
              that WHOOP Direct API is live. */}
          <View style={styles.footerRow}>
            <Text style={styles.freshnessText}>
              {(() => {
                const label = day.recovery_score != null ? 'cycle' : 'snapshot';
                if (isToday(day.date)) {
                  if (day.source_updated_at) return `Today\u2019s ${label} · updated ${formatRelative(day.source_updated_at)}`;
                  if (fetchedAt) return `Today\u2019s ${label} · fetched ${formatRelative(fetchedAt)}`;
                  return `Today\u2019s ${label}`;
                }
                if (day.source_updated_at) return `${day.date} ${label} · updated ${formatRelative(day.source_updated_at)}`;
                return `${day.date} ${label}`;
              })()}
            </Text>
          </View>

          {freshness === 'stale' && (
            <View style={styles.noticeRow}>
              <View style={[styles.statusDot, { backgroundColor: '#d4e157' }]} />
              <Text style={styles.noticeWarn}>
                WHOOP snapshot is more than {STALE_SOURCE_HOURS} hours old. Tap Refresh to re-pull from WHOOP.
              </Text>
            </View>
          )}

          {!latestDayIsToday && (
            <View style={styles.noticeRow}>
              <View style={[styles.statusDot, { backgroundColor: '#d4e157' }]} />
              <Text style={styles.noticeWarn}>
                Awaiting today’s cycle. Latest scored cycle is {day.date}. WHOOP scores the new cycle after your next sleep.
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
  noticeStale: { fontSize: 11, color: '#999', marginTop: 2 },
  noticeMuted: { fontSize: 12, color: '#999', flex: 1, lineHeight: 16 },
});
