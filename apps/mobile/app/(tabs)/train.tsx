import { useState } from 'react';
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
import type { SessionType, SessionIntensity } from '@lauburu/shared';
import { SESSION_TYPE_LABELS, INTENSITY_LABELS } from '@lauburu/shared';

const SESSION_TYPES: SessionType[] = ['class', 'sparring', 'drilling', 'comp', 'open_mat', 'other'];
const INTENSITIES: SessionIntensity[] = ['light', 'moderate', 'hard'];
const DURATION_PRESETS = [30, 45, 60, 90, 120];
const TAG_OPTIONS = ['gi', 'no-gi', 'positional', 'technique', 'comp-prep', 'flow'];

function todayDate() {
  return new Date().toISOString().slice(0, 10);
}

export default function TrainScreen() {
  const [sessionType, setSessionType] = useState<SessionType>('class');
  const [intensity, setIntensity] = useState<SessionIntensity>('moderate');
  const [duration, setDuration] = useState(60);
  const [rounds, setRounds] = useState('');
  const [rpe, setRpe] = useState('');
  const [notes, setNotes] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>(['no-gi']);
  const [submitted, setSubmitted] = useState(false);

  const addSession = useTrainingStore((s) => s.addSession);
  const sessions = useTrainingStore((s) => s.sessions);
  const syncData = useHealthStore((s) => s.syncData);
  const user = useAuthStore((s) => s.user);

  const todaySessions = sessions.filter((s) => s.date === todayDate());

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    );
  };

  const handleSubmit = () => {
    Keyboard.dismiss();

    const session = addSession({
      date: todayDate(),
      type: sessionType,
      intensity,
      duration_min: duration,
      rounds: rounds ? parseInt(rounds, 10) : undefined,
      rpe: rpe ? parseInt(rpe, 10) : undefined,
      tags: selectedTags,
      notes,
    });

    // Trigger health pipeline recomputation with the new session
    if (user?.id) {
      syncData(user.id);
    }

    setSubmitted(true);
    setNotes('');
    setRounds('');
    setRpe('');

    // Reset after a moment
    setTimeout(() => setSubmitted(false), 3000);
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled">
      <Text style={styles.heading}>Log Training</Text>

      {/* Success banner */}
      {submitted && (
        <View style={styles.successBanner}>
          <Text style={styles.successText}>Session logged — coaching updated</Text>
        </View>
      )}

      {/* Session type */}
      <View style={styles.section}>
        <Text style={styles.sectionLabel}>Type</Text>
        <View style={styles.pillRow}>
          {SESSION_TYPES.map((t) => (
            <Pressable
              key={t}
              style={[styles.pill, sessionType === t && styles.pillActive]}
              onPress={() => setSessionType(t)}>
              <Text
                style={[styles.pillText, sessionType === t && styles.pillTextActive]}>
                {SESSION_TYPE_LABELS[t]}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>

      {/* Intensity */}
      <View style={styles.section}>
        <Text style={styles.sectionLabel}>Intensity</Text>
        <View style={styles.pillRow}>
          {INTENSITIES.map((i) => {
            const colors: Record<string, string> = {
              light: '#4ade80',
              moderate: '#e8ff47',
              hard: '#ff6b6b',
            };
            return (
              <Pressable
                key={i}
                style={[
                  styles.pill,
                  intensity === i && { borderColor: colors[i], backgroundColor: colors[i] + '15' },
                ]}
                onPress={() => setIntensity(i)}>
                <Text
                  style={[
                    styles.pillText,
                    intensity === i && { color: colors[i], fontWeight: '600' },
                  ]}>
                  {INTENSITY_LABELS[i]}
                </Text>
              </Pressable>
            );
          })}
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
              <Text
                style={[styles.pillText, duration === d && styles.pillTextActive]}>
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
              style={[
                styles.pill,
                selectedTags.includes(tag) && styles.pillActive,
              ]}
              onPress={() => toggleTag(tag)}>
              <Text
                style={[
                  styles.pillText,
                  selectedTags.includes(tag) && styles.pillTextActive,
                ]}>
                {tag}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>

      {/* Rounds + RPE row */}
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
        <Text style={styles.submitText}>Log Session</Text>
      </Pressable>

      {/* Today's sessions */}
      {todaySessions.length > 0 && (
        <View style={styles.todaySection}>
          <Text style={styles.todayHeader}>Today's Sessions</Text>
          {todaySessions.map((s) => (
            <View key={s.id} style={styles.sessionCard}>
              <View style={styles.sessionRow}>
                <Text style={styles.sessionType}>
                  {SESSION_TYPE_LABELS[s.type]} · {s.duration_min}min · {s.intensity}
                </Text>
                {s.rpe && (
                  <Text style={styles.sessionRpe}>RPE {s.rpe}</Text>
                )}
              </View>
              {s.tags.length > 0 && (
                <Text style={styles.sessionTags}>{s.tags.join(', ')}</Text>
              )}
              {s.notes ? (
                <Text style={styles.sessionNotes}>{s.notes}</Text>
              ) : null}
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

  successBanner: {
    backgroundColor: 'rgba(74,222,128,0.15)',
    borderWidth: 1,
    borderColor: '#4ade80',
    borderRadius: 10,
    padding: 12,
    alignItems: 'center',
  },
  successText: { color: '#4ade80', fontSize: 14, fontWeight: '600' },

  todaySection: { gap: 8, marginTop: 8 },
  todayHeader: { fontSize: 16, fontWeight: '600' },
  sessionCard: {
    padding: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 4,
  },
  sessionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sessionType: { fontSize: 14, fontWeight: '600' },
  sessionRpe: { fontSize: 13, color: '#e8ff47' },
  sessionTags: { fontSize: 12, opacity: 0.5 },
  sessionNotes: { fontSize: 13, opacity: 0.7 },
});
