import { StyleSheet, ScrollView, ActivityIndicator, Pressable } from 'react-native';
import { Text, View } from '@/components/Themed';
import { useWorkStatus } from '../../src/hooks/useWorkStatus';
import { usePromptJobs } from '../../src/hooks/usePromptJobs';
import type { AgentWorkStatus, PromptJob } from '@lauburu/shared';

// --- Agent status card ---

const STATUS_COLORS: Record<string, string> = {
  active: '#4ade80',
  idle: '#666',
  blocked: '#ff6b6b',
  working: '#e8ff47',
};

function AgentCard({ name, agent }: { name: string; agent: AgentWorkStatus }) {
  const dotColor = STATUS_COLORS[agent.status] ?? STATUS_COLORS.idle;
  return (
    <View style={styles.agentCard}>
      <View style={styles.agentHeader}>
        <View style={[styles.statusDot, { backgroundColor: dotColor }]} />
        <Text style={styles.agentName}>{name}</Text>
        <Text style={styles.agentStatus}>{agent.status}</Text>
      </View>
      {agent.task ? (
        <Text style={styles.agentTask} numberOfLines={2}>
          {agent.task}
        </Text>
      ) : null}
      {agent.branch ? (
        <Text style={styles.agentMeta}>
          {agent.branch}
          {agent.last_commit ? ` · ${agent.last_commit.slice(0, 7)}` : ''}
        </Text>
      ) : null}
    </View>
  );
}

function AgentSection() {
  const { data, loading, error, refresh } = useWorkStatus();

  if (loading) {
    return (
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Agent Status</Text>
        <ActivityIndicator size="small" color="#e8ff47" />
      </View>
    );
  }

  if (error || !data) {
    return (
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Agent Status</Text>
        <Text style={styles.cardError}>{error ?? 'No data'}</Text>
        <Pressable style={styles.retryButton} onPress={refresh}>
          <Text style={styles.retryText}>Retry</Text>
        </Pressable>
      </View>
    );
  }

  const agentEntries = Object.entries(data.agents);

  return (
    <View style={styles.card}>
      <View style={styles.cardHeaderRow}>
        <Text style={styles.cardTitle}>Agent Status</Text>
        <Text style={styles.liveIndicator}>LIVE</Text>
      </View>
      {agentEntries.map(([name, agent]) => (
        <AgentCard key={name} name={name} agent={agent} />
      ))}
    </View>
  );
}

// --- Prompt jobs ---

function JobRow({ job }: { job: PromptJob }) {
  const statusColors: Record<string, string> = {
    pending: '#e8ff47',
    claimed: '#4ade80',
    completed: '#666',
    failed: '#ff6b6b',
    cancelled: '#666',
  };
  return (
    <View style={styles.jobRow}>
      <View style={styles.jobHeader}>
        <Text
          style={[styles.jobStatus, { color: statusColors[job.status] ?? '#666' }]}>
          {job.status}
        </Text>
        {job.target_agent ? (
          <Text style={styles.jobAgent}>{job.target_agent}</Text>
        ) : null}
      </View>
      <Text style={styles.jobPrompt} numberOfLines={2}>
        {job.prompt}
      </Text>
    </View>
  );
}

function PromptJobsSection() {
  const { jobs, pending, loading, error, refresh } = usePromptJobs();

  if (loading) {
    return (
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Prompt Jobs</Text>
        <ActivityIndicator size="small" color="#e8ff47" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Prompt Jobs</Text>
        <Text style={styles.cardError}>{error}</Text>
        <Pressable style={styles.retryButton} onPress={refresh}>
          <Text style={styles.retryText}>Retry</Text>
        </Pressable>
      </View>
    );
  }

  const recentJobs = jobs.slice(0, 10);

  return (
    <View style={styles.card}>
      <View style={styles.cardHeaderRow}>
        <Text style={styles.cardTitle}>Prompt Jobs</Text>
        <Text style={styles.badge}>{pending.length} pending</Text>
      </View>
      {recentJobs.length === 0 ? (
        <Text style={styles.emptyText}>No prompt jobs</Text>
      ) : (
        recentJobs.map((job) => <JobRow key={job.id} job={job} />)
      )}
    </View>
  );
}

// --- Main screen ---

export default function ControlScreen() {
  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}>
      <Text style={styles.heading}>Control Centre Lite</Text>
      <Text style={styles.description}>
        Live agent activity and pending work.
      </Text>

      <AgentSection />
      <PromptJobsSection />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 20, gap: 16, paddingBottom: 40 },
  heading: { fontSize: 24, fontWeight: '700' },
  description: { fontSize: 14, opacity: 0.7, lineHeight: 20, marginBottom: 4 },

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
  cardError: { fontSize: 14, color: '#ff6b6b' },
  emptyText: { fontSize: 14, opacity: 0.5 },

  liveIndicator: {
    fontSize: 11,
    fontWeight: '700',
    color: '#4ade80',
    letterSpacing: 1,
  },
  badge: {
    fontSize: 12,
    color: '#e8ff47',
    fontWeight: '600',
  },

  // Agent cards
  agentCard: {
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.06)',
    borderRadius: 8,
    padding: 10,
    gap: 4,
  },
  agentHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  agentName: {
    fontSize: 14,
    fontWeight: '600',
    flex: 1,
  },
  agentStatus: {
    fontSize: 12,
    opacity: 0.5,
  },
  agentTask: {
    fontSize: 13,
    opacity: 0.7,
    paddingLeft: 16,
  },
  agentMeta: {
    fontSize: 11,
    opacity: 0.4,
    paddingLeft: 16,
    fontFamily: 'SpaceMono',
  },

  // Prompt job rows
  jobRow: {
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.06)',
    borderRadius: 8,
    padding: 10,
    gap: 4,
  },
  jobHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  jobStatus: {
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  jobAgent: {
    fontSize: 12,
    opacity: 0.5,
  },
  jobPrompt: {
    fontSize: 13,
    opacity: 0.7,
    lineHeight: 18,
  },

  retryButton: {
    alignSelf: 'flex-start',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#e8ff47',
  },
  retryText: {
    color: '#e8ff47',
    fontSize: 13,
    fontWeight: '600',
  },
});
