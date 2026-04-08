import { StyleSheet, ScrollView, ActivityIndicator } from 'react-native';
import { Text, View } from '@/components/Themed';
import { useAuthStore } from '../../src/store/auth-store';
import { useHealthStore } from '../../src/store/health-store';
import { useProgress } from '../../src/hooks/useProgress';
import type { ReadinessLevel } from '@lauburu/shared';

const READINESS_COLORS: Record<ReadinessLevel, string> = {
  green: '#4ade80',
  yellow: '#e8ff47',
  red: '#ff6b6b',
  grey: '#666',
};

function GuestBanner() {
  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Welcome</Text>
      <Text style={styles.cardBody}>
        Sign in on the Settings tab to sync your training progress and health
        data.
      </Text>
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
          Connect a health source on the Health tab to see your training
          readiness.
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
        <ActivityIndicator size="small" color="#e8ff47" />
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
  metricValue: { fontSize: 16, fontWeight: '700', color: '#e8ff47' },
  metricLabel: { fontSize: 10, opacity: 0.5 },
  syncNote: { fontSize: 10, opacity: 0.3 },

  // Progress
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingTop: 8,
  },
  stat: { alignItems: 'center', gap: 4 },
  statNumber: { fontSize: 28, fontWeight: '700', color: '#e8ff47' },
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
});
