import { StyleSheet, ScrollView, ActivityIndicator } from 'react-native';
import { Text, View } from '@/components/Themed';
import { useAuthStore } from '../../src/store/auth-store';
import { useProgress } from '../../src/hooks/useProgress';

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
      {isMember && <ProgressCard />}

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Health Summary</Text>
        <Text style={styles.cardBody}>
          {isMember
            ? 'Recovery score, HRV, sleep, and readiness will appear here once health providers are connected.'
            : 'Sign in to see your health data.'}
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Recent Activity</Text>
        <Text style={styles.cardBody}>
          {isMember
            ? 'Recent grappling sessions and success log entries will appear here.'
            : 'Sign in to see your activity.'}
        </Text>
      </View>
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
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingTop: 8,
  },
  stat: { alignItems: 'center', gap: 4 },
  statNumber: { fontSize: 28, fontWeight: '700', color: '#e8ff47' },
  statLabel: { fontSize: 13, opacity: 0.6 },
});
