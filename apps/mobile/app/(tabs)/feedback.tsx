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
import {
  useDailyJournalStore,
  type CustomJournalAction,
  type CustomJournalCategory,
  type CustomJournalItem,
  type TrainingIntent,
} from '../../src/store/daily-journal-store';
import { SESSION_TYPE_LABELS } from '@lauburu/shared';
import { ATHLETE_CAPABILITY_COPY } from '../../src/services/athlete-capability-display';

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

const TRAINING_INTENT_LABELS: Record<TrainingIntent, string> = {
  push: 'Push',
  normal: 'Normal',
  technique: 'Technique',
  light: 'Light',
  rest: 'Rest',
};

const JOURNAL_CATEGORY_LABELS: Record<CustomJournalCategory, string> = {
  supplement: 'Supplement',
  medication: 'Medication',
  nutrition: 'Nutrition',
  recovery: 'Recovery',
  training: 'Training',
  sleep: 'Sleep',
  symptom: 'Symptom',
  other: 'Other',
};

const JOURNAL_ACTION_LABELS: Record<CustomJournalAction, string> = {
  start: 'Start',
  stop: 'Stop',
  dose_change: 'Dose change',
  break_start: 'Break start',
  break_end: 'Break end',
  one_off: 'One-off use',
  symptom_note: 'Symptom note',
  custom_note: 'Custom note',
};

function formatJournalDose(item: Pick<CustomJournalItem, 'dose' | 'unit' | 'frequencyTiming'>): string {
  const dose = [item.dose, item.unit].filter(Boolean).join(' ');
  return [dose, item.frequencyTiming].filter(Boolean).join(' · ') || 'No dose/timing set';
}

// ---------------------------------------------------------------------------
// 0. Daily journal — subjective readiness context
// ---------------------------------------------------------------------------

function DailyJournalCard() {
  const existing = useDailyJournalStore((s) => s.getEntryForDate(todayDate()));
  const upsertEntry = useDailyJournalStore((s) => s.upsertEntry);
  const [date, setDate] = useState(existing?.date ?? todayDate());
  const [sleepQuality, setSleepQuality] = useState(existing?.sleepQuality ?? 3);
  const [soreness, setSoreness] = useState(existing?.soreness ?? 3);
  const [fatigue, setFatigue] = useState(existing?.fatigue ?? 3);
  const [stress, setStress] = useState(existing?.stress ?? 3);
  const [trainingIntent, setTrainingIntent] = useState<TrainingIntent>(existing?.trainingIntent ?? 'normal');
  const [injuryPainNotes, setInjuryPainNotes] = useState(existing?.injuryPainNotes ?? '');
  const [medicationSupplementNotes, setMedicationSupplementNotes] = useState(existing?.medicationSupplementNotes ?? '');
  const [notes, setNotes] = useState(existing?.notes ?? '');
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    Keyboard.dismiss();
    const trimmedDate = date.trim();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(trimmedDate)) {
      Alert.alert('Daily journal', 'Use YYYY-MM-DD for the date.');
      return;
    }
    upsertEntry({
      date: trimmedDate,
      sleepQuality,
      soreness,
      fatigue,
      stress,
      trainingIntent,
      injuryPainNotes,
      medicationSupplementNotes,
      notes,
    });
    setSaved(true);
  };

  return (
    <View style={styles.card}>
      <View style={styles.cardHeaderRow}>
        <View>
          <Text style={styles.cardTitle}>Daily journal</Text>
          <Text style={styles.cardSubtitle}>Subjective context for provisional readiness</Text>
        </View>
        {(existing || saved) && <Text style={styles.savedText}>Saved</Text>}
      </View>

      <Text style={styles.noteText}>
        This is your self-report, not medical data. Pain or medication notes stay as context.
      </Text>

      <TextInput
        style={styles.input}
        placeholder="YYYY-MM-DD"
        placeholderTextColor="#666"
        value={date}
        onChangeText={setDate}
        autoCapitalize="none"
      />

      <RatingRow label="Sleep quality" value={sleepQuality} onChange={setSleepQuality} />
      <RatingRow label="Soreness" value={soreness} onChange={setSoreness} />
      <RatingRow label="Fatigue" value={fatigue} onChange={setFatigue} />
      <RatingRow label="Stress" value={stress} onChange={setStress} />

      <View style={styles.section}>
        <Text style={styles.sectionLabel}>Training intent</Text>
        <PillSelect
          options={['push', 'normal', 'technique', 'light', 'rest'] as const}
          labels={TRAINING_INTENT_LABELS}
          value={trainingIntent}
          onChange={setTrainingIntent}
        />
      </View>

      <TextInput
        style={styles.input}
        placeholder="Injury / pain notes (optional)"
        placeholderTextColor="#666"
        value={injuryPainNotes}
        onChangeText={setInjuryPainNotes}
      />
      <TextInput
        style={styles.input}
        placeholder="Medication / supplement notes (optional)"
        placeholderTextColor="#666"
        value={medicationSupplementNotes}
        onChangeText={setMedicationSupplementNotes}
      />
      <TextInput
        style={[styles.input, styles.multilineInput]}
        placeholder="Free text notes (optional)"
        placeholderTextColor="#666"
        value={notes}
        onChangeText={setNotes}
        multiline
      />

      <Pressable style={styles.saveButton} onPress={handleSave}>
        <Text style={styles.saveText}>{existing || saved ? 'Update Journal' : 'Save Journal'}</Text>
      </Pressable>
    </View>
  );
}

function CustomJournalTimelineCard() {
  const customItems = useDailyJournalStore((s) => s.customItems);
  const activeItems = useDailyJournalStore((s) => s.getActiveCustomItems());
  const stoppedItems = useDailyJournalStore((s) => s.getStoppedCustomItems());
  const recentEvents = useDailyJournalStore((s) => s.getRecentJournalEvents(8));
  const addCustomItem = useDailyJournalStore((s) => s.addCustomItem);
  const addJournalEvent = useDailyJournalStore((s) => s.addJournalEvent);
  const stopCustomItem = useDailyJournalStore((s) => s.stopCustomItem);

  const [name, setName] = useState('');
  const [category, setCategory] = useState<CustomJournalCategory>('supplement');
  const [customCategory, setCustomCategory] = useState('');
  const [dose, setDose] = useState('');
  const [unit, setUnit] = useState('');
  const [frequencyTiming, setFrequencyTiming] = useState('');
  const [startDate, setStartDate] = useState(todayDate());
  const [stopDate, setStopDate] = useState('');
  const [itemNotes, setItemNotes] = useState('');

  const [eventAction, setEventAction] = useState<CustomJournalAction>('dose_change');
  const [eventItemId, setEventItemId] = useState<string>('');
  const [eventDate, setEventDate] = useState(todayDate());
  const [eventDose, setEventDose] = useState('');
  const [eventUnit, setEventUnit] = useState('');
  const [eventNotes, setEventNotes] = useState('');
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  const handleAddItem = () => {
    Keyboard.dismiss();
    if (!name.trim()) {
      Alert.alert('Journal item', 'Add a name first.');
      return;
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(startDate.trim())) {
      Alert.alert('Journal item', 'Use YYYY-MM-DD for the start date.');
      return;
    }
    if (stopDate.trim() && !/^\d{4}-\d{2}-\d{2}$/.test(stopDate.trim())) {
      Alert.alert('Journal item', 'Use YYYY-MM-DD for the stop date.');
      return;
    }
    addCustomItem({
      name,
      category,
      customCategory,
      dose,
      unit,
      frequencyTiming,
      startDate,
      stopDate,
      notes: itemNotes,
    });
    setSavedMessage('Item added');
    setName('');
    setCustomCategory('');
    setDose('');
    setUnit('');
    setFrequencyTiming('');
    setStopDate('');
    setItemNotes('');
  };

  const handleAddEvent = () => {
    Keyboard.dismiss();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(eventDate.trim())) {
      Alert.alert('Journal event', 'Use YYYY-MM-DD for the event date.');
      return;
    }
    if (!eventItemId && !eventNotes.trim()) {
      Alert.alert('Journal event', 'Choose an item or add a note.');
      return;
    }
    const item = customItems.find((candidate) => candidate.id === eventItemId);
    addJournalEvent({
      itemId: item?.id ?? null,
      itemName: item?.name,
      action: eventAction,
      date: eventDate,
      dose: eventDose,
      unit: eventUnit,
      notes: eventNotes,
    });
    setSavedMessage('Event added');
    setEventDose('');
    setEventUnit('');
    setEventNotes('');
  };

  return (
    <View style={styles.card}>
      <View style={styles.cardHeaderRow}>
        <View>
          <Text style={styles.cardTitle}>Custom journal timeline</Text>
          <Text style={styles.cardSubtitle}>Track things that may affect readiness</Text>
        </View>
        <Text style={styles.badge}>{activeItems.length} active</Text>
      </View>
      <Text style={styles.noteText}>
        These entries show possible associations only. The app will not claim causation.
      </Text>

      <View style={styles.section}>
        <Text style={styles.sectionLabel}>Add item</Text>
        <TextInput
          style={styles.input}
          placeholder="Name, e.g. magnesium, creatine, sauna, knee pain"
          placeholderTextColor="#666"
          value={name}
          onChangeText={setName}
        />
        <PillSelect
          options={['supplement', 'medication', 'nutrition', 'recovery', 'training', 'sleep', 'symptom', 'other'] as const}
          labels={JOURNAL_CATEGORY_LABELS}
          value={category}
          onChange={setCategory}
        />
        {category === 'other' && (
          <TextInput
            style={styles.input}
            placeholder="Custom category"
            placeholderTextColor="#666"
            value={customCategory}
            onChangeText={setCustomCategory}
          />
        )}
        <View style={styles.twoColRow}>
          <TextInput
            style={[styles.input, styles.flexInput]}
            placeholder="Dose"
            placeholderTextColor="#666"
            value={dose}
            onChangeText={setDose}
          />
          <TextInput
            style={[styles.input, styles.flexInput]}
            placeholder="Unit"
            placeholderTextColor="#666"
            value={unit}
            onChangeText={setUnit}
          />
        </View>
        <TextInput
          style={styles.input}
          placeholder="Frequency / timing, e.g. nightly, post-training"
          placeholderTextColor="#666"
          value={frequencyTiming}
          onChangeText={setFrequencyTiming}
        />
        <View style={styles.twoColRow}>
          <TextInput
            style={[styles.input, styles.flexInput]}
            placeholder="Start YYYY-MM-DD"
            placeholderTextColor="#666"
            value={startDate}
            onChangeText={setStartDate}
          />
          <TextInput
            style={[styles.input, styles.flexInput]}
            placeholder="Stop optional"
            placeholderTextColor="#666"
            value={stopDate}
            onChangeText={setStopDate}
          />
        </View>
        <TextInput
          style={[styles.input, styles.multilineInput]}
          placeholder="Notes (optional)"
          placeholderTextColor="#666"
          value={itemNotes}
          onChangeText={setItemNotes}
          multiline
        />
        <Pressable style={styles.saveButton} onPress={handleAddItem}>
          <Text style={styles.saveText}>Add Timeline Item</Text>
        </Pressable>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionLabel}>Add event</Text>
        <PillSelect
          options={['dose_change', 'break_start', 'break_end', 'one_off', 'symptom_note', 'custom_note', 'stop'] as const}
          labels={JOURNAL_ACTION_LABELS}
          value={eventAction}
          onChange={setEventAction}
        />
        <View style={styles.pillRow}>
          <Pressable
            style={[styles.pill, eventItemId === '' && styles.pillActive]}
            onPress={() => setEventItemId('')}>
            <Text style={[styles.pillText, eventItemId === '' && styles.pillTextActive]}>No item</Text>
          </Pressable>
          {customItems.slice(-8).map((item) => (
            <Pressable
              key={item.id}
              style={[styles.pill, eventItemId === item.id && styles.pillActive]}
              onPress={() => setEventItemId(item.id)}>
              <Text style={[styles.pillText, eventItemId === item.id && styles.pillTextActive]}>{item.name}</Text>
            </Pressable>
          ))}
        </View>
        <View style={styles.twoColRow}>
          <TextInput
            style={[styles.input, styles.flexInput]}
            placeholder="Date"
            placeholderTextColor="#666"
            value={eventDate}
            onChangeText={setEventDate}
          />
          <TextInput
            style={[styles.input, styles.flexInput]}
            placeholder="Dose change"
            placeholderTextColor="#666"
            value={eventDose}
            onChangeText={setEventDose}
          />
        </View>
        <TextInput
          style={styles.input}
          placeholder="Unit / note detail"
          placeholderTextColor="#666"
          value={eventUnit}
          onChangeText={setEventUnit}
        />
        <TextInput
          style={[styles.input, styles.multilineInput]}
          placeholder="Event note"
          placeholderTextColor="#666"
          value={eventNotes}
          onChangeText={setEventNotes}
          multiline
        />
        <Pressable style={styles.saveButton} onPress={handleAddEvent}>
          <Text style={styles.saveText}>Add Event</Text>
        </Pressable>
        {savedMessage && <Text style={styles.savedText}>{savedMessage}</Text>}
      </View>

      {activeItems.length > 0 && (
        <View style={styles.timelineGroup}>
          <Text style={styles.sectionLabel}>Active items</Text>
          {activeItems.map((item) => (
            <View key={item.id} style={styles.timelineRow}>
              <View style={styles.timelineTextCol}>
                <Text style={styles.timelineTitle}>{item.name}</Text>
                <Text style={styles.timelineMeta}>
                  {JOURNAL_CATEGORY_LABELS[item.category]} · {formatJournalDose(item)} · since {item.startDate}
                </Text>
              </View>
              <Pressable
                style={styles.smallOutlineBtn}
                onPress={() => stopCustomItem(item.id, todayDate(), 'Stopped from timeline')}>
                <Text style={styles.smallOutlineText}>Stop</Text>
              </Pressable>
            </View>
          ))}
        </View>
      )}

      <View style={styles.timelineGroup}>
        <Text style={styles.sectionLabel}>Recent changes</Text>
        {recentEvents.length > 0 ? recentEvents.map((event) => (
          <View key={event.id} style={styles.timelineRow}>
            <View style={styles.timelineTextCol}>
              <Text style={styles.timelineTitle}>{event.date} · {JOURNAL_ACTION_LABELS[event.action]}</Text>
              <Text style={styles.timelineMeta}>
                {event.itemName}{event.dose || event.unit ? ` · ${[event.dose, event.unit].filter(Boolean).join(' ')}` : ''}
              </Text>
              {!!event.notes && <Text style={styles.timelineNote}>{event.notes}</Text>}
            </View>
          </View>
        )) : (
          <Text style={styles.noteText}>No timeline changes yet.</Text>
        )}
      </View>

      {stoppedItems.length > 0 && (
        <View style={styles.timelineGroup}>
          <Text style={styles.sectionLabel}>Stopped items</Text>
          {stoppedItems.slice(-5).reverse().map((item) => (
            <Text key={item.id} style={styles.timelineMeta}>
              {item.name} · {item.startDate} to {item.stopDate}
            </Text>
          ))}
        </View>
      )}

      <View style={styles.effectBox}>
        <Text style={styles.effectTitle}>Effect insight</Text>
        <Text style={styles.effectBody}>
          Not enough data yet. Future views may show possible associations with low confidence, without claiming cause.
        </Text>
      </View>
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
        {ATHLETE_CAPABILITY_COPY.todaySeedSuggestionLabel}: {coaching.readiness.headline}
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
    syncing: '#d4e157',
    synced: '#4ade80',
    failed: '#ff6b6b',
  };

  const handleSync = async () => {
    await syncToBackend();
  };

  return (
    <View style={styles.card}>
      <View style={styles.syncRow}>
        <View>
          <Text style={styles.cardTitle}>Saved check-ins</Text>
          <Text style={styles.cardSubtitle}>
            {examples.length} item{examples.length !== 1 ? 's' : ''} ready
          </Text>
        </View>
        {authStatus === 'member' && examples.length > 0 && (
          <Pressable
            style={[styles.syncBtn, syncStatus === 'syncing' && { opacity: 0.5 }]}
            onPress={handleSync}
            disabled={syncStatus === 'syncing'}>
            <Text style={styles.syncBtnText}>
              {syncStatus === 'syncing' ? 'Syncing...' : 'Sync'}
            </Text>
          </Pressable>
        )}
      </View>

      {/* Status feedback */}
      <View style={styles.statusRow}>
        <View style={[styles.statusDot, { backgroundColor: statusColors[syncStatus] }]} />
        <Text style={[styles.statusText, { color: statusColors[syncStatus] }]}>
          {syncStatus === 'idle' && examples.length === 0 && 'Log a session or answer a check-in to start'}
          {syncStatus === 'idle' && examples.length > 0 && 'Ready to sync'}
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
            {ex.eligibility?.training_eligible && (
              <Text style={[styles.badge, styles.badgeGreen]}>eligible</Text>
            )}
            {ex.eligibility && !ex.eligibility.training_eligible && (
              <Text style={[styles.badge, styles.badgeRed]}>ineligible</Text>
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
  const journalCount = useDailyJournalStore((s) => s.entries.length);
  const entryCount = feedbackCount + outcomeCount + checkinCount + journalCount;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled">
      <Text style={styles.heading}>Daily Check-in</Text>
      <Text style={styles.subtitle}>
        {entryCount > 0
          ? `${entryCount} entries — improving your coaching context`
          : 'Log subjective context, sessions, and coaching feedback'}
      </Text>
      <DailyJournalCard />
      <CustomJournalTimelineCard />
      <SyncCard />
      <NextDayCheckinCard />
      <RecommendationFeedbackCard />
      <SessionOutcomeCard />

      <View style={styles.infoCard}>
        <Text style={styles.infoTitle}>Keep it simple</Text>
        <Text style={styles.infoBody}>
          Quick check-ins help the app match future suggestions to how
          training actually felt.
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
  cardHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 10,
  },
  cardSubtitle: { fontSize: 13, opacity: 0.6 },
  savedText: { fontSize: 14, color: '#4ade80' },
  noteText: { fontSize: 12, opacity: 0.55, lineHeight: 17 },

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
    borderColor: '#d4e157',
    backgroundColor: 'rgba(212,225,87,0.1)',
  },
  pillText: { fontSize: 14, color: '#999' },
  pillTextActive: { color: '#d4e157', fontWeight: '600' },
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
    backgroundColor: '#d4e157',
    borderColor: '#d4e157',
  },
  ratingNum: { fontSize: 10, opacity: 0.4 },
  ratingNumActive: { opacity: 0.8, color: '#d4e157' },

  input: {
    borderWidth: 1,
    borderColor: '#333',
    borderRadius: 10,
    padding: 12,
    fontSize: 14,
    color: '#f0f0f0',
    backgroundColor: 'rgba(255,255,255,0.05)',
  },
  multilineInput: {
    minHeight: 74,
    textAlignVertical: 'top',
  },
  twoColRow: { flexDirection: 'row', gap: 8 },
  flexInput: { flex: 1 },
  timelineGroup: {
    gap: 8,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.06)',
  },
  timelineRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 10,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.04)',
  },
  timelineTextCol: { flex: 1, gap: 2 },
  timelineTitle: { fontSize: 14, fontWeight: '700' },
  timelineMeta: { fontSize: 12, opacity: 0.55, lineHeight: 17 },
  timelineNote: { fontSize: 12, opacity: 0.42, lineHeight: 17 },
  smallOutlineBtn: {
    paddingVertical: 5,
    paddingHorizontal: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#d4e157',
  },
  smallOutlineText: { fontSize: 12, color: '#d4e157', fontWeight: '700' },
  effectBox: {
    gap: 4,
    padding: 10,
    borderRadius: 8,
    backgroundColor: 'rgba(212,225,87,0.07)',
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.18)',
  },
  effectTitle: { fontSize: 13, fontWeight: '700', color: '#d4e157' },
  effectBody: { fontSize: 12, opacity: 0.65, lineHeight: 17 },

  saveButton: {
    backgroundColor: '#d4e157',
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
    borderColor: '#d4e157',
  },
  syncBtnText: { color: '#d4e157', fontSize: 13, fontWeight: '600' },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 4 },
  statusDot: { width: 8, height: 8, borderRadius: 4 },
  statusText: { fontSize: 12 },
  guestNote: { fontSize: 12, color: '#d4e157', opacity: 0.7 },

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
    color: '#d4e157',
    backgroundColor: 'rgba(212,225,87,0.1)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    overflow: 'hidden',
  },
  badgeGreen: { color: '#4ade80', backgroundColor: 'rgba(74,222,128,0.1)' },
  badgeRed: { color: '#ff6b6b', backgroundColor: 'rgba(255,107,107,0.1)' },
  exampleReadiness: { fontSize: 12, opacity: 0.5, width: 50, textAlign: 'right' },
});
