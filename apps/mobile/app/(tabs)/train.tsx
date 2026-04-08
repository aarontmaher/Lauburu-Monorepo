import { useState, useMemo } from 'react';
import {
  StyleSheet,
  ScrollView,
  TextInput,
  Pressable,
  Alert,
  Keyboard,
} from 'react-native';
import { Text, View } from '@/components/Themed';
import { useTrainingStore } from '../../src/store/training-store';
import { useHealthStore } from '../../src/store/health-store';
import { useAuthStore } from '../../src/store/auth-store';
import type { SessionType, SessionIntensity, TrainingSession, ConditioningSubtype, ConditioningDetail, Modality, LiftingFocus } from '@lauburu/shared';
import { SESSION_TYPE_LABELS, INTENSITY_LABELS, TAG_OPTIONS, CONDITIONING_SUBTYPE_LABELS, MODALITY_LABELS, LIFTING_FOCUS_LABELS } from '@lauburu/shared';

const SESSION_TYPES: SessionType[] = ['class', 'sparring', 'drilling', 'wrestling', 'comp', 'open_mat', 'conditioning', 'other'];
const INTENSITIES: SessionIntensity[] = ['light', 'moderate', 'hard'];
const DURATION_PRESETS = [30, 45, 60, 90, 120];

const INTENSITY_COLORS: Record<string, string> = {
  light: '#4ade80',
  moderate: '#e8ff47',
  hard: '#ff6b6b',
};

function todayDate() {
  return new Date().toISOString().slice(0, 10);
}

function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

function formatDateLabel(date: string): string {
  const today = todayDate();
  if (date === today) return 'Today';
  if (date === daysAgo(1)) return 'Yesterday';
  const d = new Date(date + 'T12:00:00');
  return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
}

// ---------------------------------------------------------------------------
// Entry form
// ---------------------------------------------------------------------------

function EntryForm({
  editing,
  onDone,
}: {
  editing: TrainingSession | null;
  onDone: () => void;
}) {
  const addSession = useTrainingStore((s) => s.addSession);
  const editSession = useTrainingStore((s) => s.editSession);
  const syncData = useHealthStore((s) => s.syncData);
  const user = useAuthStore((s) => s.user);

  const [sessionType, setSessionType] = useState<SessionType>(editing?.type ?? 'class');
  const [intensity, setIntensity] = useState<SessionIntensity>(editing?.intensity ?? 'moderate');
  const [duration, setDuration] = useState(editing?.duration_min ?? 60);
  const [rounds, setRounds] = useState(editing?.rounds?.toString() ?? '');
  const [rpe, setRpe] = useState(editing?.rpe?.toString() ?? '');
  const [notes, setNotes] = useState(editing?.notes ?? '');
  const [selectedTags, setSelectedTags] = useState<string[]>(editing?.tags ?? ['no-gi']);

  // Conditioning state
  const [condSubtype, setCondSubtype] = useState<ConditioningSubtype>(
    editing?.conditioning?.subtype ?? 'hiit',
  );
  const [condModality, setCondModality] = useState<Modality>(
    editing?.conditioning?.modality ?? 'assault_bike',
  );
  const [workDur, setWorkDur] = useState(editing?.conditioning?.interval?.work_duration_s?.toString() ?? '30');
  const [restDur, setRestDur] = useState(editing?.conditioning?.interval?.rest_duration_s?.toString() ?? '30');
  const [intervalRounds, setIntervalRounds] = useState(editing?.conditioning?.interval?.rounds?.toString() ?? '10');
  const [liftFocus, setLiftFocus] = useState<LiftingFocus>(
    editing?.conditioning?.weight_training?.focus ?? 'full_body',
  );

  const isConditioning = sessionType === 'conditioning';
  const isInterval = isConditioning && ['hiit', 'intervals', 'sprint_intervals', 'circuit'].includes(condSubtype);
  const isWeightTraining = isConditioning && condSubtype === 'weight_training';
  const isRespiratory = isConditioning && ['respiratory_training', 'breathing_warmup', 'recovery_breathing'].includes(condSubtype);

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    );
  };

  const buildConditioning = (): ConditioningDetail | undefined => {
    if (!isConditioning) return undefined;
    const detail: ConditioningDetail = {
      subtype: condSubtype,
      modality: condModality,
    };
    if (isInterval) {
      detail.interval = {
        work_duration_s: parseInt(workDur, 10) || 30,
        rest_duration_s: parseInt(restDur, 10) || 30,
        rounds: parseInt(intervalRounds, 10) || 10,
      };
    }
    if (isWeightTraining) {
      detail.weight_training = { focus: liftFocus };
    }
    return detail;
  };

  const handleSubmit = () => {
    Keyboard.dismiss();
    const input = {
      date: editing?.date ?? todayDate(),
      type: sessionType,
      intensity,
      duration_min: duration,
      rounds: rounds ? parseInt(rounds, 10) : undefined,
      rpe: rpe ? parseInt(rpe, 10) : undefined,
      tags: selectedTags,
      notes,
      conditioning: buildConditioning(),
    };

    if (editing) {
      editSession(editing.id, input);
    } else {
      addSession(input);
    }

    if (user?.id) syncData(user.id);
    onDone();
  };

  return (
    <View style={styles.formSection}>
      {/* Type */}
      <View style={styles.section}>
        <Text style={styles.sectionLabel}>Type</Text>
        <View style={styles.pillRow}>
          {SESSION_TYPES.map((t) => (
            <Pressable
              key={t}
              style={[styles.pill, sessionType === t && styles.pillActive]}
              onPress={() => setSessionType(t)}>
              <Text style={[styles.pillText, sessionType === t && styles.pillTextActive]}>
                {SESSION_TYPE_LABELS[t]}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>

      {/* Conditioning subtype */}
      {isConditioning && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Conditioning Type</Text>
          <View style={styles.pillRow}>
            {(['hiit', 'intervals', 'sprint_intervals', 'steady_state', 'zone2', 'tempo',
              'weight_training', 'circuit', 'mobility', 'recovery_cardio',
              'respiratory_training', 'other'] as ConditioningSubtype[]).map((st) => (
              <Pressable
                key={st}
                style={[styles.pill, condSubtype === st && styles.pillActive]}
                onPress={() => setCondSubtype(st)}>
                <Text style={[styles.pillText, condSubtype === st && styles.pillTextActive]}>
                  {CONDITIONING_SUBTYPE_LABELS[st]}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>
      )}

      {/* Modality (for conditioning with equipment) */}
      {isConditioning && !isWeightTraining && !isRespiratory && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Modality</Text>
          <View style={styles.pillRow}>
            {(['assault_bike', 'rower', 'skierg', 'running', 'bike', 'bodyweight', 'kettlebell', 'other'] as Modality[]).map((m) => (
              <Pressable
                key={m}
                style={[styles.pill, condModality === m && styles.pillActive]}
                onPress={() => setCondModality(m)}>
                <Text style={[styles.pillText, condModality === m && styles.pillTextActive]}>
                  {MODALITY_LABELS[m]}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>
      )}

      {/* Interval detail */}
      {isInterval && (
        <View style={styles.rowInputs}>
          <View style={styles.halfInput}>
            <Text style={styles.sectionLabel}>Work (s)</Text>
            <TextInput
              style={styles.input}
              value={workDur}
              onChangeText={setWorkDur}
              keyboardType="number-pad"
              placeholder="30"
              placeholderTextColor="#666"
            />
          </View>
          <View style={styles.halfInput}>
            <Text style={styles.sectionLabel}>Rest (s)</Text>
            <TextInput
              style={styles.input}
              value={restDur}
              onChangeText={setRestDur}
              keyboardType="number-pad"
              placeholder="30"
              placeholderTextColor="#666"
            />
          </View>
          <View style={styles.halfInput}>
            <Text style={styles.sectionLabel}>Rounds</Text>
            <TextInput
              style={styles.input}
              value={intervalRounds}
              onChangeText={setIntervalRounds}
              keyboardType="number-pad"
              placeholder="10"
              placeholderTextColor="#666"
            />
          </View>
        </View>
      )}

      {/* Weight training focus */}
      {isWeightTraining && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Lifting Focus</Text>
          <View style={styles.pillRow}>
            {(['upper', 'lower', 'full_body', 'pull', 'push', 'posterior_chain', 'power', 'hypertrophy'] as LiftingFocus[]).map((f) => (
              <Pressable
                key={f}
                style={[styles.pill, liftFocus === f && styles.pillActive]}
                onPress={() => setLiftFocus(f)}>
                <Text style={[styles.pillText, liftFocus === f && styles.pillTextActive]}>
                  {LIFTING_FOCUS_LABELS[f]}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>
      )}

      {/* Intensity */}
      <View style={styles.section}>
        <Text style={styles.sectionLabel}>Intensity</Text>
        <View style={styles.pillRow}>
          {INTENSITIES.map((i) => (
            <Pressable
              key={i}
              style={[
                styles.pill,
                intensity === i && { borderColor: INTENSITY_COLORS[i], backgroundColor: INTENSITY_COLORS[i] + '15' },
              ]}
              onPress={() => setIntensity(i)}>
              <Text
                style={[
                  styles.pillText,
                  intensity === i && { color: INTENSITY_COLORS[i], fontWeight: '600' },
                ]}>
                {INTENSITY_LABELS[i]}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>

      {/* Duration */}
      <View style={styles.section}>
        <Text style={styles.sectionLabel}>Duration</Text>
        <View style={styles.pillRow}>
          {DURATION_PRESETS.map((d) => (
            <Pressable
              key={d}
              style={[styles.pill, duration === d && styles.pillActive]}
              onPress={() => setDuration(d)}>
              <Text style={[styles.pillText, duration === d && styles.pillTextActive]}>
                {d}min
              </Text>
            </Pressable>
          ))}
        </View>
      </View>

      {/* Tags */}
      <View style={styles.section}>
        <Text style={styles.sectionLabel}>Tags</Text>
        <View style={styles.pillRow}>
          {TAG_OPTIONS.map((tag) => (
            <Pressable
              key={tag}
              style={[styles.pill, selectedTags.includes(tag) && styles.pillActive]}
              onPress={() => toggleTag(tag)}>
              <Text style={[styles.pillText, selectedTags.includes(tag) && styles.pillTextActive]}>
                {tag}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>

      {/* Rounds + RPE */}
      <View style={styles.rowInputs}>
        <View style={styles.halfInput}>
          <Text style={styles.sectionLabel}>Rounds</Text>
          <TextInput
            style={styles.input}
            placeholder="—"
            placeholderTextColor="#666"
            value={rounds}
            onChangeText={setRounds}
            keyboardType="number-pad"
          />
        </View>
        <View style={styles.halfInput}>
          <Text style={styles.sectionLabel}>RPE (1-10)</Text>
          <TextInput
            style={styles.input}
            placeholder="—"
            placeholderTextColor="#666"
            value={rpe}
            onChangeText={setRpe}
            keyboardType="number-pad"
          />
        </View>
      </View>

      {/* Notes */}
      <View style={styles.section}>
        <Text style={styles.sectionLabel}>Notes</Text>
        <TextInput
          style={[styles.input, styles.textArea]}
          placeholder="Techniques worked, how it felt..."
          placeholderTextColor="#666"
          value={notes}
          onChangeText={setNotes}
          multiline
          textAlignVertical="top"
        />
      </View>

      {/* Submit */}
      <Pressable style={styles.submitButton} onPress={handleSubmit}>
        <Text style={styles.submitText}>
          {editing ? 'Save Changes' : 'Log Session'}
        </Text>
      </Pressable>

      {editing && (
        <Pressable style={styles.cancelButton} onPress={onDone}>
          <Text style={styles.cancelText}>Cancel</Text>
        </Pressable>
      )}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Session card
// ---------------------------------------------------------------------------

function SessionCard({
  session,
  onEdit,
  onDelete,
}: {
  session: TrainingSession;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const handleDelete = () => {
    Alert.alert(
      'Delete Session',
      `Delete ${SESSION_TYPE_LABELS[session.type]} on ${session.date}?`,
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Delete', style: 'destructive', onPress: onDelete },
      ],
    );
  };

  return (
    <View style={styles.sessionCard}>
      <View style={styles.sessionHeader}>
        <View>
          <Text style={styles.sessionType}>
            {SESSION_TYPE_LABELS[session.type]}
          </Text>
          <Text style={styles.sessionMeta}>
            {session.duration_min}min ·{' '}
            <Text style={{ color: INTENSITY_COLORS[session.intensity] }}>
              {session.intensity}
            </Text>
            {session.rounds ? ` · ${session.rounds} rounds` : ''}
            {session.rpe ? ` · RPE ${session.rpe}` : ''}
          </Text>
        </View>
        <View style={styles.sessionActions}>
          <Pressable onPress={onEdit} style={styles.actionBtn}>
            <Text style={styles.actionText}>Edit</Text>
          </Pressable>
          <Pressable onPress={handleDelete} style={styles.actionBtn}>
            <Text style={[styles.actionText, { color: '#ff6b6b' }]}>Delete</Text>
          </Pressable>
        </View>
      </View>
      {session.tags.length > 0 && (
        <Text style={styles.sessionTags}>{session.tags.join(' · ')}</Text>
      )}
      {session.notes ? (
        <Text style={styles.sessionNotes}>{session.notes}</Text>
      ) : null}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Main screen
// ---------------------------------------------------------------------------

export default function TrainScreen() {
  const sessions = useTrainingStore((s) => s.sessions);
  const removeSession = useTrainingStore((s) => s.removeSession);
  const syncData = useHealthStore((s) => s.syncData);
  const user = useAuthStore((s) => s.user);
  const [editingSession, setEditingSession] = useState<TrainingSession | null>(null);
  const [showForm, setShowForm] = useState(true);
  const [submitted, setSubmitted] = useState(false);

  // Group sessions by date (last 7 days)
  const groupedSessions = useMemo(() => {
    const sevenDaysAgo = daysAgo(7);
    const recent = sessions
      .filter((s) => s.date >= sevenDaysAgo)
      .sort((a, b) => b.date.localeCompare(a.date) || b.created_at.localeCompare(a.created_at));

    const groups: { date: string; label: string; sessions: TrainingSession[] }[] = [];
    let currentDate = '';
    for (const s of recent) {
      if (s.date !== currentDate) {
        currentDate = s.date;
        groups.push({ date: s.date, label: formatDateLabel(s.date), sessions: [] });
      }
      groups[groups.length - 1].sessions.push(s);
    }
    return groups;
  }, [sessions]);

  const handleFormDone = () => {
    setEditingSession(null);
    setShowForm(true);
    setSubmitted(true);
    setTimeout(() => setSubmitted(false), 3000);
  };

  const handleEdit = (session: TrainingSession) => {
    setEditingSession(session);
    setShowForm(true);
  };

  const handleDelete = (id: string) => {
    removeSession(id);
    if (user?.id) syncData(user.id);
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled">
      <Text style={styles.heading}>Log Training</Text>

      {submitted && !editingSession && (
        <View style={styles.successBanner}>
          <Text style={styles.successText}>Session logged — coaching updated</Text>
        </View>
      )}

      {/* Entry form */}
      {showForm && (
        <EntryForm
          editing={editingSession}
          onDone={handleFormDone}
        />
      )}

      {/* History */}
      {groupedSessions.length > 0 && (
        <View style={styles.historySection}>
          <Text style={styles.historyTitle}>Recent Sessions</Text>
          {groupedSessions.map((group) => (
            <View key={group.date} style={styles.dateGroup}>
              <Text style={styles.dateLabel}>{group.label}</Text>
              {group.sessions.map((s) => (
                <SessionCard
                  key={s.id}
                  session={s}
                  onEdit={() => handleEdit(s)}
                  onDelete={() => handleDelete(s.id)}
                />
              ))}
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 20, gap: 16, paddingBottom: 40 },
  heading: { fontSize: 24, fontWeight: '700' },

  formSection: { gap: 16 },
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

  rowInputs: { flexDirection: 'row', gap: 12 },
  halfInput: { flex: 1, gap: 8 },

  input: {
    borderWidth: 1,
    borderColor: '#333',
    borderRadius: 10,
    padding: 12,
    fontSize: 16,
    color: '#f0f0f0',
    backgroundColor: 'rgba(255,255,255,0.05)',
  },
  textArea: { minHeight: 80 },

  submitButton: {
    backgroundColor: '#e8ff47',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  submitText: { color: '#0a0a0a', fontSize: 17, fontWeight: '700' },

  cancelButton: {
    borderRadius: 12,
    padding: 14,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#666',
  },
  cancelText: { color: '#999', fontSize: 15 },

  successBanner: {
    backgroundColor: 'rgba(74,222,128,0.15)',
    borderWidth: 1,
    borderColor: '#4ade80',
    borderRadius: 10,
    padding: 12,
    alignItems: 'center',
  },
  successText: { color: '#4ade80', fontSize: 14, fontWeight: '600' },

  // History
  historySection: { gap: 12, marginTop: 8 },
  historyTitle: { fontSize: 18, fontWeight: '600' },
  dateGroup: { gap: 8 },
  dateLabel: { fontSize: 14, fontWeight: '600', opacity: 0.6 },

  // Session card
  sessionCard: {
    padding: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 6,
  },
  sessionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  sessionType: { fontSize: 15, fontWeight: '600' },
  sessionMeta: { fontSize: 13, opacity: 0.7, marginTop: 2 },
  sessionActions: { flexDirection: 'row', gap: 12 },
  actionBtn: { paddingVertical: 2, paddingHorizontal: 4 },
  actionText: { fontSize: 13, color: '#e8ff47' },
  sessionTags: { fontSize: 12, opacity: 0.5 },
  sessionNotes: { fontSize: 13, opacity: 0.6, lineHeight: 18 },
});
