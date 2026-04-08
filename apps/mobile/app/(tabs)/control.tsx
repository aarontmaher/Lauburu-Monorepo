import { StyleSheet, ScrollView } from 'react-native';
import { Text, View } from '@/components/Themed';

export default function ControlScreen() {
  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}>
      <Text style={styles.heading}>Control Centre Lite</Text>
      <Text style={styles.description}>
        Monitor agent activity and pending work from your phone.
      </Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Agent Status</Text>
        <Text style={styles.cardBody}>
          Live work status for copilot, claude_code, codex, chatgpt, and
          claude_chat will appear here.
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Prompt Jobs</Text>
        <Text style={styles.cardBody}>
          Pending, claimed, and completed prompt jobs will be listed here.
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Pending Suggestions</Text>
        <Text style={styles.cardBody}>
          Suggestions awaiting review will appear here for quick
          approve/reject actions.
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 20, gap: 16 },
  heading: { fontSize: 24, fontWeight: '700' },
  description: { fontSize: 14, opacity: 0.7, lineHeight: 20, marginBottom: 4 },
  card: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 8,
  },
  cardTitle: { fontSize: 18, fontWeight: '600' },
  cardBody: { fontSize: 14, opacity: 0.7, lineHeight: 20 },
});
