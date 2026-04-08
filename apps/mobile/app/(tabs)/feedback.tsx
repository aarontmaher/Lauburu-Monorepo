import { useState } from 'react';
import {
  StyleSheet,
  ScrollView,
  Pressable,
  TextInput,
  Alert,
  Keyboard,
} from 'react-native';
import { Text, View } from '@/components/Themed';
import { useFeedbackStore } from '../../src/store/feedback-store';
import { useHealthStore } from '../../src/store/health-store';
import { useTrainingStore } from '../../src/store/training-store';
import { useAuthStore } from '../../src/store/auth-store';
import { SESSION_TYPE_LABELS } from '@lauburu/shared';

function todayDate() {
  return new Date().toISOString().slice(0, 10);
}

function yesterdayDate() {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
}

// ---------------------------------------------------------------------------
// Rating row — reusable 1-5 selector
// ---------------------------------------------------------------------------

function RatingRow({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <View style={styles.ratingRow}>
      <Text style={styles.ratingLabel}>{label}</Text>
      <View style={styles.ratingDots}>
        {[1, 2, 3, 4, 5].map((n) => (
          <Pressable key={n} onPress={() => onChange(n)} style={styles.ratingDotBtn}>
            <View
              style={[
                styles.ratingDot,
                n <= value && styles.ratingDotActive,
              ]}
            />
            <Text style={[styles.ratingNum, n <= value && styles.ratingNumActive]}>
              {n}
            </Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Pill selector
// ---------------------------------------------------------------------------

function PillSelect<T extends string>({
  options,
  labels,
  value,
  onChange,
}: {
  options: T[];
  labels: Record<T, string>;
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <View style={styles.pillRow}>
      {options.map((opt) => (
        <Pressable
          key={opt}
          style={[styles.pill, value === opt && styles.pillActive]}
          onPress={() => onChange(opt)}>
          <Text style={[styles.pillText, value === opt && styles.pillTextActive]}>
            {labels[opt]}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}

// ---------------------------------------------------------------------------
// 1. Recommendation feedback
// ---------------------------------------------------------------------------

function RecommendationFeedbackCard() {
  const coaching = useHealthStore((s) => s.coaching);
  const addFeedback = useFeedbackStore((s) => s.addRecommendationFeedback);
  const existing = useFeedbackStore((s) => s.getFeedbackForDate(todayDate()));

  const [followed, setFollowed] = useState<'yes' | 'partly' | 'no'>('yes');
  const [accuracy, setAccuracy] = useState(3);
  const [usefulness, setUsefulness] = useState(3);
  const [saved, setSaved] = useState(!!existing);

  if (!coaching || coaching.readiness.level === 'grey') return null;

  const handleSave = () => {
    addFeedback({
      date: todayDate(),
      readiness_shown: coaching.readiness.level,
      recommendation_shown: coaching.today_recommendation.action,
      followed,
      accuracy,
      usefulness,
    });
    setSaved(true);
  };

  if (saved) {
    return (
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Recommendation Feedback</Text>
        <Text style={styles.savedText}>Saved for today</Text>
      </View>
    );
  }

  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Recommendation Feedback</Text>
      <Text style={styles.cardSubtitle}>
        Today's recommendation: {coaching.readiness.headline}
      </Text>

      <View style={styles.section}>
        <Text style={styles.sectionLabel}>Did you follow it?</Text>
        <PillSelect
          options={['yes', 'partly', 'no'] as const}
          labels={{ yes: 'Yes', partly: 'Partly', no: 'No' }}
          value={followed}
          onChange={setFollowed}
        />
      </View>

      <RatingRow label="Accuracy" value={accuracy} onChange={setAccuracy} />
      <RatingRow label="Usefulness" value={usefulness} onChange={setUsefulness} />

      <Pressable style={styles.saveButton} onPress={handleSave}>
        <Text style={styles.saveText}>Save Feedback</Text>
      </Pressable>
    </View>
  );
}

// ---------------------------------------------------------------------------
// 2. Session outcome
// ---------------------------------------------------------------------------

function SessionOutcomeCard() {
  const sessions = useTrainingStore((s) => s.sessions);
  const addOutcome = useFeedbackStore((s) => s.addSessionOutcome);
  const getOutcome = useFeedbackStore((s) => s.getOutcomeForSession);

  const todaySessions = sessions.filter((s) => s.date === todayDate());
  const latestSession = todaySessions[todaySessions.length - 1];

  const [feel, setFeel] = useState<'too_hard' | 'right' | 'too_easy'>('right');
  const [performance, setPerformance] = useState(3);
  const [soreness, setSoreness] = useState(2);
  const [fatigue, setFatigue] = useState(2);
  const [confidence, setConfidence] = useState(3);
  const [notes, setNotes] = useState('');
  const [saved, setSaved] = useState(false);

  if (!latestSession) return null;

  const existing = getOutcome(latestSession.id);
  if (existing || saved) {
    return (
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Session Outcome</Text>
        <Text style={styles.savedText}>
          Recorded for {SESSION_TYPE_LABELS[latestSession.type]}
        </Text>
      </View>
    );
  }

  const handleSave = () => {
    Keyboard.dismiss();
    addOutcome({
      session_ref: latestSession.id,
      date: todayDate(),
      difficulty_feel: feel,
      performance,
      soreness,
      fatigue,
      confidence,
      notes,
    });
    setSaved(true);
  };

  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Session Outcome</Text>
      <Text style={styles.cardSubtitle}>
        {SESSION_TYPE_LABELS[latestSession.type]} · {latestSession.duration_min}min
      </Text>

      <View style={styles.section}>
        <Text style={styles.sectionLabel}>How did it feel?</Text>
        <PillSelect
          options={['too_hard', 'right', 'too_easy'] as const}
          labels={{ too_hard: 'Too Hard', right: 'Right', too_easy: 'Too Easy' }}
          value={feel}
          onChange={setFeel}
        />
      </View>

      <RatingRow label="Performance" value={performance} onChange={setPerformance} />
      <RatingRow label="Soreness" value={soreness} onChange={setSoreness} />
      <RatingRow label="Fatigue" value={fatigue} onChange={setFatigue} />
      <RatingRow label="Confidence" value={confidence} onChange={setConfidence} />

      <TextInput
        style={styles.input}
        placeholder="Notes (optional)"
        placeholderTextColor="#666"
        value={notes}
        onChangeText={setNotes}
      />

      <Pressable style={styles.saveButton} onPress={handleSave}>
        <Text style={styles.saveText}>Save Outcome</Text>
      </Pressable>
    </View>
  );
}

// ---------------------------------------------------------------------------
// 3. Next-day check-in
// ---------------------------------------------------------------------------

function NextDayCheckinCard() {
  const sessions = useTrainingStore((s) => s.sessions);
  const addCheckin = useFeedbackStore((s) => s.addNextDayCheckin);
  const getCheckin = useFeedbackStore((s) => s.getCheckinForDate);

  const yesterday = yesterdayDate();
  const yesterdaySessions = sessions.filter((s) => s.date === yesterday);

  const [recoveryFeel, setRecoveryFeel] = useState<'better' | 'same' | 'worse'>('same');
  const [recAccuracy, setRecAccuracy] = useState<'right' | 'wrong' | 'mixed'>('right');
  const [injuryFlag, setInjuryFlag] = useState(false);
  const [injuryNotes, setInjuryNotes] = useState('');
  const [saved, setSaved] = useState(false);

  if (yesterdaySessions.length === 0) return null;

  const existing = getCheckin(yesterday);
  if (existing || saved) {
    return (
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Next-Day Check-in</Text>
        <Text style={styles.savedText}>Recorded for yesterday</Text>
      </View>
    );
  }

  const handleSave = () => {
    Keyboard.dismiss();
    addCheckin({
      training_date: yesterday,
      recovery_feel: recoveryFeel,
      recommendation_accuracy: recAccuracy,
      injury_flag: injuryFlag,
      injury_notes: injuryNotes,
    });
    setSaved(true);
  };

  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Next-Day Check-in</Text>
      <Text style={styles.cardSubtitle}>
        How are you after yesterday's training?
      </Text>

      <View style={styles.section}>
        <Text style={styles.sectionLabel}>Recovery</Text>
        <PillSelect
          options={['better', 'same', 'worse'] as const}
          labels={{ better: 'Better than expected', same: 'As expected', worse: 'Worse' }}
          value={recoveryFeel}
          onChange={setRecoveryFeel}
        />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionLabel}>Was the recommendation right?</Text>
        <PillSelect
          options={['right', 'wrong', 'mixed'] as const}
          labels={{ right: 'Right', wrong: 'Wrong', mixed: 'Mixed' }}
          value={recAccuracy}
          onChange={setRecAccuracy}
        />
      </View>

      <Pressable
        style={[styles.pill, injuryFlag && styles.pillDanger]}
        onPress={() => setInjuryFlag(!injuryFlag)}>
        <Text style={[styles.pillText, injuryFlag && styles.pillDangerText]}>
          {injuryFlag ? 'Injury / Warning flagged' : 'No injury or warning'}
        </Text>
      </Pressable>

      {injuryFlag && (
        <TextInput
          style={styles.input}
          placeholder="Describe injury / warning"
          placeholderTextColor="#666"
          value={injuryNotes}
          onChangeText={setInjuryNotes}
        />
      )}

      <Pressable style={styles.saveButton} onPress={handleSave}>
        <Text style={styles.saveText}>Save Check-in</Text>
      </Pressable>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Sync status + review
// ---------------------------------------------------------------------------

function SyncCard() {
  const syncStatus = useFeedbackStore((s) => s.syncStatus);
  const lastSyncAt = useFeedbackStore((s) => s.lastSyncAt);
  const lastSyncError = useFeedbackStore((s) => s.lastSyncError);
  const examples = useFeedbackStore((s) => s.examples);
  const syncToBackend = useFeedbackStore((s) => s.syncToBackend);
  const authStatus = useAuthStore((s) => s.status);

  const statusColors: Record<string, string> = {
    idle: '#999',
    syncing: '#e8ff47',
    synced: '#4ade80',
    failed: '#ff6b6b',
  };

  return (
    <View style={styles.card}>
      <View style={styles.syncRow}>
        <View>
          <Text style={styles.cardTitle}>Training Data</Text>
          <Text style={styles.cardSubtitle}>
            {examples.length} example{examples.length !== 1 ? 's' : ''} assembled
          </Text>
        </View>
        {authStatus === 'member' && (
          <Pressable
            style={styles.syncBtn}
            onPress={syncToBackend}
            disabled={syncStatus === 'syncing' || examples.length === 0}>
            <Text style={styles.syncBtnText}>
              {syncStatus === 'syncing' ? 'Syncing...' : 'Sync'}
            </Text>
          </Pressable>
        )}
      </View>
      <View style={styles.statusRow}>
        <View style={[styles.statusDot, { backgroundColor: statusColors[syncStatus] }]} />
        <Text style={[styles.statusText, { color: statusColors[syncStatus] }]}>
          {syncStatus === 'idle' && 'Not synced yet'}
          {syncStatus === 'syncing' && 'Syncing...'}
          {syncStatus === 'synced' && `Synced ${lastSyncAt ? new Date(lastSyncAt).toLocaleTimeString() : ''}`}
          {syncStatus === 'failed' && (lastSyncError ?? 'Sync failed')}
        </Text>
      </View>
      {authStatus !== 'member' && (
        <Text style={styles.guestNote}>Sign in to sync training data to your account.</Text>
      )}
    </View>
  );
}

function RecentExamplesCard() {
  const examples = useFeedbackStore((s) => s.examples);
  const recent = examples.slice(-5).reverse();

  if (recent.length === 0) return null;

  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Recent Examples</Text>
      {recent.map((ex) => (
        <View key={ex.date} style={styles.exampleRow}>
          <Text style={styles.exampleDate}>{ex.date}</Text>
          <View style={styles.exampleBadges}>
            {ex.health_inputs.sleep_hours != null && (
              <Text style={styles.badge}>sleep</Text>
            )}
            {ex.behavior.session_type && (
              <Text style={styles.badge}>{ex.behavior.session_type}</Text>
            )}
            {ex.feedback && (
              <Text style={styles.badge}>rated</Text>
            )}
            {ex.same_day_outcome && (
              <Text style={styles.badge}>outcome</Text>
            )}
            {ex.next_day_outcome && (
              <Text style={styles.badge}>next-day</Text>
            )}
          </View>
          <Text style={styles.exampleReadiness}>
            {ex.recommendation.readiness}
          </Text>
        </View>
      ))}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Main screen
// ---------------------------------------------------------------------------

export default function FeedbackScreen() {
  const feedbackCount = useFeedbackStore((s) => s.recommendations.length);
  const outcomeCount = useFeedbackStore((s) => s.outcomes.length);
  const checkinCount = useFeedbackStore((s) => s.checkins.length);

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled">
      <Text style={styles.heading}>Daily Check-in</Text>
      <Text style={styles.subtitle}>
        {feedbackCount + outcomeCount + checkinCount} entries captured
      </Text>

      <SyncCard />
      <NextDayCheckinCard />
      <RecommendationFeedbackCard />
      <SessionOutcomeCard />
      <RecentExamplesCard />

      <View style={styles.infoCard}>
        <Text style={styles.infoTitle}>Why this matters</Text>
        <Text style={styles.infoBody}>
          Your feedback trains the coaching system to be more accurate for you
          personally. Every data point improves future recommendations.
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 20, gap: 16, paddingBottom: 40 },
  heading: { fontSize: 24, fontWeight: '700' },
  subtitle: { fontSize: 14, opacity: 0.5 },

  card: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 12,
  },
  cardTitle: { fontSize: 18, fontWeight: '600' },
  cardSubtitle: { fontSize: 13, opacity: 0.6 },
  savedText: { fontSize: 14, color: '#4ade80' },

  section: { gap: 8 },
  sectionLabel: {
    fontSize: 13,
    fontWeight: '600',
    textTransform: 'uppercase',
    opacity: 0.5,
    letterSpacing: 0.5,
  },

  pillRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  pill: {
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#444',
  },
  pillActive: {
    borderColor: '#e8ff47',
    backgroundColor: 'rgba(232,255,71,0.1)',
  },
  pillText: { fontSize: 14, color: '#999' },
  pillTextActive: { color: '#e8ff47', fontWeight: '600' },
  pillDanger: {
    borderColor: '#ff6b6b',
    backgroundColor: 'rgba(255,107,107,0.1)',
  },
  pillDangerText: { color: '#ff6b6b', fontWeight: '600' },

  ratingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  ratingLabel: { fontSize: 14, flex: 1 },
  ratingDots: { flexDirection: 'row', gap: 8 },
  ratingDotBtn: { alignItems: 'center', gap: 2 },
  ratingDot: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#444',
  },
  ratingDotActive: {
    backgroundColor: '#e8ff47',
    borderColor: '#e8ff47',
  },
  ratingNum: { fontSize: 10, opacity: 0.4 },
  ratingNumActive: { opacity: 0.8, color: '#e8ff47' },

  input: {
    borderWidth: 1,
    borderColor: '#333',
    borderRadius: 10,
    padding: 12,
    fontSize: 14,
    color: '#f0f0f0',
    backgroundColor: 'rgba(255,255,255,0.05)',
  },

  saveButton: {
    backgroundColor: '#e8ff47',
    borderRadius: 10,
    padding: 14,
    alignItems: 'center',
  },
  saveText: { color: '#0a0a0a', fontSize: 15, fontWeight: '600' },

  infoCard: {
    padding: 14,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.03)',
    gap: 6,
  },
  infoTitle: { fontSize: 14, fontWeight: '600', opacity: 0.6 },
  infoBody: { fontSize: 13, opacity: 0.4, lineHeight: 18 },

  // Sync card
  syncRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  syncBtn: {
    paddingVertical: 6,
    paddingHorizontal: 14,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e8ff47',
  },
  syncBtnText: { color: '#e8ff47', fontSize: 13, fontWeight: '600' },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 4 },
  statusDot: { width: 8, height: 8, borderRadius: 4 },
  statusText: { fontSize: 12 },
  guestNote: { fontSize: 12, color: '#e8ff47', opacity: 0.7 },

  // Recent examples
  exampleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.04)',
  },
  exampleDate: { fontSize: 13, fontWeight: '600', width: 80 },
  exampleBadges: { flexDirection: 'row', flexWrap: 'wrap', gap: 4, flex: 1 },
  badge: {
    fontSize: 10,
    color: '#e8ff47',
    backgroundColor: 'rgba(232,255,71,0.1)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    overflow: 'hidden',
  },
  exampleReadiness: { fontSize: 12, opacity: 0.5, width: 50, textAlign: 'right' },
});
