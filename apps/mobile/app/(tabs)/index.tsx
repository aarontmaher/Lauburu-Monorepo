import { useEffect } from 'react';
import { StyleSheet, ScrollView, ActivityIndicator } from 'react-native';
import { Text, View } from '@/components/Themed';
import { useAuthStore } from '../../src/store/auth-store';
import { useHealthStore } from '../../src/store/health-store';
import { useTrainingStore } from '../../src/store/training-store';
import { useWhoopStore } from '../../src/store/whoop-store';
import { useProgress } from '../../src/hooks/useProgress';
import type { ReadinessLevel } from '@lauburu/shared';
import { SESSION_TYPE_LABELS } from '@lauburu/shared';

const READINESS_COLORS: Record<ReadinessLevel, string> = {
  green: '#4ade80',
  yellow: '#d4e157',
  red: '#ff6b6b',
  grey: '#666',
};

function GuestBanner() {
  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Welcome to Lauburu</Text>
      <Text style={styles.cardBody}>
        Sign in on Settings to save your training data and get personalized coaching.
      </Text>
    </View>
  );
}

function WhoopHeadline() {
  const status = useWhoopStore((s) => s.status);
  const day = useWhoopStore((s) => s.day);
  const fetchToday = useWhoopStore((s) => s.fetchToday);

  useEffect(() => {
    if (status === 'idle') fetchToday();
  }, [status, fetchToday]);

  if (status !== 'ready' || !day || day.recovery_score == null) return null;

  const score = day.recovery_score;
  const color =
    score >= 67 ? '#4ade80' : score >= 34 ? '#d4e157' : '#ff6b6b';
  const label = score >= 67 ? 'Recovered' : score >= 34 ? 'Moderate' : 'Low';

  return (
    <View style={styles.whoopHeadline}>
      <View style={[styles.whoopDot, { backgroundColor: color }]} />
      <Text style={[styles.whoopLabel, { color }]}>
        WHOOP {score}% · {label}
      </Text>
      {day.daily_strain != null && (
        <Text style={styles.whoopMeta}>
          strain {day.daily_strain.toFixed(1)}
        </Text>
      )}
    </View>
  );
}

function ReadinessCard() {
  const insights = useHealthStore((s) => s.insights);
  const lastSyncAt = useHealthStore((s) => s.lastSyncAt);

  if (!insights || insights.readiness === 'grey') {
    return (
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Today's Readiness</Text>
        <Text style={styles.cardBody}>
          {lastSyncAt
            ? 'Sync more health data for personalized readiness.'
            : 'Connect Apple Health on the Health tab, then sync to see your training readiness.'}
        </Text>
      </View>
    );
  }

  const color = READINESS_COLORS[insights.readiness];

  return (
    <View style={styles.card}>
      <View style={styles.readinessRow}>
        <View style={[styles.readinessDot, { backgroundColor: color }]} />
        <Text style={[styles.readinessLabel, { color }]}>
          {insights.readiness_label}
        </Text>
      </View>
      <Text style={styles.cardBody}>{insights.recommendation.summary}</Text>
      {insights.key_metrics.length > 0 && (
        <View style={styles.metricsRow}>
          {insights.key_metrics.slice(0, 4).map((m, i) => (
            <View key={i} style={styles.metricItem}>
              <Text style={styles.metricValue}>{m.value}</Text>
              <Text style={styles.metricLabel}>{m.label}</Text>
            </View>
          ))}
        </View>
      )}
      {/* Key signals */}
      {(insights.positives.length > 0 || insights.concerns.length > 0) && (
        <View style={styles.signalsRow}>
          {insights.positives.slice(0, 2).map((p, i) => (
            <Text key={`p${i}`} style={styles.signalPositive}>✓ {p}</Text>
          ))}
          {insights.concerns.slice(0, 2).map((c, i) => (
            <Text key={`c${i}`} style={styles.signalConcern}>⚠ {c}</Text>
          ))}
        </View>
      )}
      {lastSyncAt && (
        <Text style={styles.syncNote}>
          Synced {new Date(lastSyncAt).toLocaleTimeString()}
        </Text>
      )}
    </View>
  );
}

function ProgressCard() {
  const { drilling, learned, loading, error } = useProgress();

  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Training Progress</Text>
      {loading ? (
        <ActivityIndicator size="small" color="#d4e157" />
      ) : error ? (
        <Text style={styles.cardError}>{error}</Text>
      ) : (
        <View style={styles.statsRow}>
          <View style={styles.stat}>
            <Text style={styles.statNumber}>{drilling}</Text>
            <Text style={styles.statLabel}>Drilling</Text>
          </View>
          <View style={styles.stat}>
            <Text style={styles.statNumber}>{learned}</Text>
            <Text style={styles.statLabel}>Learned</Text>
          </View>
          <View style={styles.stat}>
            <Text style={styles.statNumber}>{drilling + learned}</Text>
            <Text style={styles.statLabel}>Total</Text>
          </View>
        </View>
      )}
    </View>
  );
}

function RecentActivityCard() {
  const aiContext = useHealthStore((s) => s.aiContext);

  if (!aiContext || aiContext.recent_workouts.length === 0) {
    return (
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Recent Activity</Text>
        <Text style={styles.cardBody}>
          Recent workouts will appear here after syncing health data.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Recent Activity</Text>
      {aiContext.recent_workouts.slice(0, 5).map((w, i) => (
        <View key={i} style={styles.activityRow}>
          <View>
            <Text style={styles.activityName}>
              {w.name}
              {w.is_grappling ? ' 🥋' : ''}
            </Text>
            <Text style={styles.activityDate}>{w.date}</Text>
          </View>
          <Text style={styles.activityMeta}>
            {w.duration_min}min
            {w.calories ? ` · ${Math.round(w.calories)}cal` : ''}
          </Text>
        </View>
      ))}
    </View>
  );
}

function TrainingContextCard() {
  const coaching = useHealthStore((s) => s.coaching);
  const insights = useHealthStore((s) => s.insights);
  const sessions = useTrainingStore((s) => s.sessions);
  const todayStr = new Date().toISOString().slice(0, 10);
  const todaySessions = sessions.filter((s) => s.date === todayStr);

  if (!coaching && todaySessions.length === 0) return null;

  const hasCoaching = coaching && coaching.readiness.level !== 'grey';

  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Training Context</Text>

      {/* Plan status */}
      {hasCoaching && coaching.plan && coaching.plan.status !== 'no_plan' && (
        <Text style={styles.cardBody}>{coaching.plan.summary}</Text>
      )}

      {/* Load + grappling */}
      {hasCoaching && (
        <>
          <Text style={styles.cardBody}>{coaching.training_load.summary}</Text>
          {coaching.grappling.suggestion ? (
            <Text style={styles.suggestion}>{coaching.grappling.suggestion}</Text>
          ) : null}
        </>
      )}

      {/* Why this recommendation */}
      {insights && insights.recommendation.reasons.length > 0 && (
        <View style={styles.whySection}>
          <Text style={styles.whyLabel}>Why</Text>
          {insights.recommendation.reasons.slice(0, 3).map((r, i) => (
            <Text key={i} style={styles.whyItem}>• {r}</Text>
          ))}
        </View>
      )}

      {/* Today's sessions */}
      {todaySessions.length > 0 && (
        <View style={styles.todayBadge}>
          <Text style={styles.todayBadgeText}>
            Today: {todaySessions.map((s) => SESSION_TYPE_LABELS[s.type]).join(', ')}
          </Text>
        </View>
      )}
    </View>
  );
}

export default function HomeScreen() {
  const status = useAuthStore((s) => s.status);
  const user = useAuthStore((s) => s.user);
  const isMember = status === 'member';

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Text style={styles.title}>Lauburu Grappling Map</Text>
        <Text style={styles.subtitle}>
          {isMember ? `Signed in as ${user?.email}` : 'Your training companion'}
        </Text>
      </View>

      {!isMember && <GuestBanner />}

      {/* Readiness — the most important thing on Home */}
      {isMember && <ReadinessCard />}

      {/* Tiny backend-fed WHOOP headline — shown only when data is ready */}
      {isMember && <WhoopHeadline />}

      {isMember && <TrainingContextCard />}

      {isMember && <ProgressCard />}

      {isMember && <RecentActivityCard />}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 20, gap: 16 },
  header: { marginBottom: 8 },
  title: { fontSize: 28, fontWeight: '700' },
  subtitle: { fontSize: 16, opacity: 0.6, marginTop: 4 },
  card: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 8,
  },
  cardTitle: { fontSize: 18, fontWeight: '600' },
  cardBody: { fontSize: 14, opacity: 0.7, lineHeight: 20 },
  cardError: { fontSize: 14, color: '#ff6b6b' },

  // Readiness
  readinessRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  readinessDot: { width: 12, height: 12, borderRadius: 6 },
  readinessLabel: { fontSize: 20, fontWeight: '700' },
  metricsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingTop: 4,
  },
  metricItem: { alignItems: 'center', gap: 2 },
  metricValue: { fontSize: 16, fontWeight: '700', color: '#d4e157' },
  metricLabel: { fontSize: 10, opacity: 0.5 },
  signalsRow: { gap: 2, marginTop: 4 },
  signalPositive: { fontSize: 12, color: '#4ade80', opacity: 0.8 },
  signalConcern: { fontSize: 12, color: '#ff8a80', opacity: 0.8 },
  syncNote: { fontSize: 10, opacity: 0.3, marginTop: 4 },

  // Progress
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingTop: 8,
  },
  stat: { alignItems: 'center', gap: 4 },
  statNumber: { fontSize: 28, fontWeight: '700', color: '#d4e157' },
  statLabel: { fontSize: 13, opacity: 0.6 },

  // Activity
  activityRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 4,
  },
  activityName: { fontSize: 14 },
  activityDate: { fontSize: 11, opacity: 0.4 },
  activityMeta: { fontSize: 12, opacity: 0.5 },

  // Training context
  todayBadge: {
    backgroundColor: 'rgba(212,225,87,0.1)',
    borderRadius: 8,
    paddingVertical: 6,
    paddingHorizontal: 10,
    alignSelf: 'flex-start',
  },
  todayBadgeText: { fontSize: 12, color: '#d4e157', fontWeight: '600' },
  suggestion: { fontSize: 13, color: '#a8b84a', opacity: 0.9, lineHeight: 18 },
  whySection: { gap: 2, marginTop: 4, paddingTop: 6, borderTopWidth: 1, borderTopColor: 'rgba(255,255,255,0.06)' },
  whyLabel: { fontSize: 11, opacity: 0.4, textTransform: 'uppercase', letterSpacing: 0.5 },
  whyItem: { fontSize: 12, opacity: 0.6, lineHeight: 16 },

  // WHOOP headline
  whoopHeadline: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.03)',
  },
  whoopDot: { width: 10, height: 10, borderRadius: 5 },
  whoopLabel: { fontSize: 14, fontWeight: '600' },
  whoopMeta: { fontSize: 12, opacity: 0.5, marginLeft: 'auto' },
});
