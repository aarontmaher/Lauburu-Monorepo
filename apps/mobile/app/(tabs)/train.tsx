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
import type { SessionType, SessionIntensity, TrainingSession, ConditioningSubtype, ConditioningDetail, Modality, LiftingFocus, DayPlanSummary, SessionSegment, PartnerFormat } from '@lauburu/shared';
import {
  SESSION_TYPE_LABELS, INTENSITY_LABELS, TAG_OPTIONS,
  CONDITIONING_SUBTYPE_LABELS, MODALITY_LABELS, LIFTING_FOCUS_LABELS,
  RESPIRATORY_DEVICE_LABELS, HIIT_PRESETS, PARTNER_FORMAT_LABELS,
  buildDayPlanSummary, SCHEDULE_SESSION_LABELS,
  SESSION_PRESETS, SEGMENT_TYPE_LABELS, createDefaultSegments,
} from '@lauburu/shared';
import { usePreferencesStore } from '../../src/store/preferences-store';
import { useTimerStore } from '../../src/store/timer-store';
import type { TimerConfig } from '../../src/store/timer-store';
import { useRouter } from 'expo-router';

const SESSION_TYPES: SessionType[] = ['class', 'sparring', 'drilling', 'wrestling', 'comp', 'open_mat', 'conditioning', 'other'];
const INTENSITIES: SessionIntensity[] = ['light', 'moderate', 'hard'];
const DURATION_PRESETS = [30, 45, 60, 90, 120];

const INTENSITY_COLORS: Record<string, string> = {
  light: '#4ade80',
  moderate: '#d4e157',
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
// Selector row — compact stacked selector with AI suggestion
// ---------------------------------------------------------------------------

function SelectorRow<T extends string>({
  label,
  options,
  labels,
  value,
  onChange,
  suggestion,
  suggestionLabel,
}: {
  label: string;
  options: T[];
  labels: Record<T, string>;
  value: T;
  onChange: (v: T) => void;
  suggestion?: T;
  suggestionLabel?: string;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <View style={styles.selectorRow}>
      <Pressable style={styles.selectorHeader} onPress={() => setExpanded(!expanded)}>
        <Text style={styles.selectorLabel}>{label}</Text>
        <View style={styles.selectorValueRow}>
          <Text style={styles.selectorValue}>{labels[value]}</Text>
          <Text style={styles.selectorChevron}>{expanded ? '▾' : '▸'}</Text>
        </View>
      </Pressable>

      {suggestion && suggestion !== value && (
        <Pressable style={styles.aiSuggestionBubble} onPress={() => { onChange(suggestion); setExpanded(false); }}>
          <Text style={styles.aiSuggestionText}>
            AI coach suggestion: {suggestionLabel ?? labels[suggestion]}
          </Text>
        </Pressable>
      )}

      {expanded && (
        <View style={styles.selectorOptions}>
          {options.map((opt) => (
            <Pressable
              key={opt}
              style={[styles.selectorOption, value === opt && styles.selectorOptionActive]}
              onPress={() => { onChange(opt); setExpanded(false); }}>
              <Text style={[styles.selectorOptionText, value === opt && styles.selectorOptionTextActive]}>
                {labels[opt]}
              </Text>
            </Pressable>
          ))}
        </View>
      )}
    </View>
  );
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
  const timerSetup = useTimerStore((s) => s.setup);
  const router = useRouter();

  // Top-level mode: Grappling / HIIT / Steady State / Weights
  type TopMode = 'grappling' | 'hiit' | 'zone2' | 'weights' | null;
  const [topMode, setTopMode] = useState<TopMode>(
    editing ? (editing.type === 'conditioning'
      ? (editing.conditioning?.subtype === 'weight_training' ? 'weights'
        : editing.conditioning?.subtype === 'zone2' || editing.conditioning?.subtype === 'steady_state' || editing.conditioning?.subtype === 'recovery_cardio' ? 'zone2'
        : 'hiit')
      : 'grappling')
    : null,
  );

  const [sessionType, setSessionType] = useState<SessionType>(editing?.type ?? 'class');
  const [intensity, setIntensity] = useState<SessionIntensity>(editing?.intensity ?? 'moderate');
  const [duration, setDuration] = useState(editing?.duration_min ?? 60);
  const [rounds, setRounds] = useState(editing?.rounds?.toString() ?? '');
  const [rpe, setRpe] = useState(editing?.rpe?.toString() ?? '');
  const [notes, setNotes] = useState(editing?.notes ?? '');
  const [selectedTags, setSelectedTags] = useState<string[]>(editing?.tags ?? ['no-gi']);

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
    editing?.conditioning?.weight_training?.focus ?? 'strength',
  );

  // Respiratory state
  const [respType, setRespType] = useState<import('@lauburu/shared').RespiratoryType>(
    editing?.conditioning?.respiratory?.respiratory_type ?? 'inspiratory',
  );
  const [respDevice, setRespDevice] = useState<import('@lauburu/shared').RespiratoryDevice>(
    (editing?.conditioning?.respiratory?.device_used as any) ?? 'none',
  );
  const [respResistance, setRespResistance] = useState(editing?.conditioning?.respiratory?.resistance_level?.toString() ?? '');
  const [respBreaths, setRespBreaths] = useState(editing?.conditioning?.respiratory?.breaths?.toString() ?? '30');
  const [respSets, setRespSets] = useState(editing?.conditioning?.respiratory?.sets?.toString() ?? '3');
  const [respTiming, setRespTiming] = useState<'pre_training' | 'post_training' | 'standalone'>(
    editing?.conditioning?.respiratory?.timing ?? 'standalone',
  );

  const isConditioning = sessionType === 'conditioning';
  const isInterval = isConditioning && ['hiit', 'intervals', 'sprint_intervals', 'circuit'].includes(condSubtype);
  const isWeightTraining = isConditioning && condSubtype === 'weight_training';
  const isRespiratory = isConditioning && ['respiratory_training', 'breathing_warmup', 'recovery_breathing'].includes(condSubtype);
  const [showMore, setShowMore] = useState(false);
  const [selectedHIITPreset, setSelectedHIITPreset] = useState('30_30');

  // Segment state — auto-populated for grappling
  const [segments, setSegments] = useState<SessionSegment[]>(editing?.segments ?? []);
  const [expandedSegId, setExpandedSegId] = useState<string | null>(null);

  const addSegment = (type: import('@lauburu/shared').SegmentType) => {
    setSegments((prev) => [
      ...prev,
      { id: `seg-${Date.now()}`, type, duration_min: 15, tags: [] },
    ]);
  };

  const removeSegment = (id: string) => {
    setSegments((prev) => prev.filter((s) => s.id !== id));
    if (expandedSegId === id) setExpandedSegId(null);
  };

  const updateSegment = (id: string, updates: Partial<SessionSegment>) => {
    setSegments((prev) => prev.map((s) => s.id === id ? { ...s, ...updates } : s));
  };

  // Top mode handlers
  const selectTopMode = (mode: TopMode) => {
    setTopMode(mode);
    if (mode === 'grappling') {
      setSessionType('class');
      // Auto-detect common structure
      if (segments.length === 0 && !editing) {
        setSegments(createDefaultSegments());
      }
    } else if (mode === 'hiit') {
      setSessionType('conditioning');
      setCondSubtype('hiit');
    } else if (mode === 'zone2') {
      setSessionType('conditioning');
      setCondSubtype('zone2');
      setDuration(30);
    } else if (mode === 'weights') {
      setSessionType('conditioning');
      setCondSubtype('weight_training');
      setDuration(45);
    }
  };

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
    if (isRespiratory) {
      detail.respiratory = {
        respiratory_type: respType,
        device_used: respDevice !== 'none' ? respDevice : undefined,
        resistance_level: respResistance ? parseInt(respResistance, 10) : undefined,
        breaths: respBreaths ? parseInt(respBreaths, 10) : undefined,
        sets: respSets ? parseInt(respSets, 10) : undefined,
        timing: respTiming,
      };
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
      segments: segments.length > 0 ? segments : undefined,
      preset_id: undefined,
    };

    if (editing) {
      editSession(editing.id, input);
    } else {
      addSession(input);
    }

    if (user?.id) syncData(user.id).catch(() => {});
    onDone();
  };

  return (
    <View style={styles.formSection}>
      {/* Top-level choice */}
      {!editing && !topMode && (
        <View style={styles.quickGrid}>
          <Pressable style={styles.quickBtn} onPress={() => selectTopMode('grappling')}>
            <Text style={styles.quickBtnEmoji}>🥋</Text>
            <Text style={styles.quickBtnText}>Grappling</Text>
          </Pressable>
          <Pressable style={styles.quickBtn} onPress={() => selectTopMode('hiit')}>
            <Text style={styles.quickBtnEmoji}>⚡</Text>
            <Text style={styles.quickBtnText}>HIIT</Text>
          </Pressable>
          <Pressable style={styles.quickBtn} onPress={() => selectTopMode('zone2')}>
            <Text style={styles.quickBtnEmoji}>🫀</Text>
            <Text style={styles.quickBtnText}>Steady State</Text>
          </Pressable>
          <Pressable style={styles.quickBtn} onPress={() => selectTopMode('weights')}>
            <Text style={styles.quickBtnEmoji}>🏋️</Text>
            <Text style={styles.quickBtnText}>Weights</Text>
          </Pressable>
        </View>
      )}

      {/* Mode header — tap to change */}
      {topMode && !editing && (
        <Pressable onPress={() => setTopMode(null)}>
          <Text style={styles.modeHeader}>
            {topMode === 'grappling' ? '🥋 Grappling'
              : topMode === 'hiit' ? '⚡ HIIT'
              : topMode === 'weights' ? '🏋️ Weights'
              : '🫀 Steady State'}
            <Text style={styles.modeChange}> (change)</Text>
          </Text>
        </Pressable>
      )}

      {/* Grappling — auto-detected structure, editable */}
      {topMode === 'grappling' && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Session parts</Text>
          <Text style={styles.segmentHint}>
            {segments.length > 0 ? 'Tap to relabel · expand for details' : 'Common structure auto-filled'}
          </Text>

          {/* Editable segment cards */}
          {segments.map((seg, i) => {
            const isExpanded = expandedSegId === seg.id;
            return (
              <View key={seg.id}>
                {/* Compact row — tap type to cycle, tap card to expand */}
                <Pressable
                  style={[styles.segmentRow, isExpanded && styles.segmentRowExpanded]}
                  onPress={() => setExpandedSegId(isExpanded ? null : seg.id)}>
                  <Text style={styles.segmentNum}>{i + 1}</Text>
                  <View style={styles.segmentInfo}>
                    <Text style={styles.segmentType}>{SEGMENT_TYPE_LABELS[seg.type]}</Text>
                    <Text style={styles.segmentMeta}>
                      {seg.duration_min}min
                      {seg.partner_format ? ` · ${PARTNER_FORMAT_LABELS[seg.partner_format]}` : ''}
                      {seg.rounds ? ` · ${seg.rounds}rds` : ''}
                    </Text>
                  </View>
                  <Text style={styles.segmentChevron}>{isExpanded ? '▾' : '▸'}</Text>
                  <Pressable onPress={() => removeSegment(seg.id)} hitSlop={8}>
                    <Text style={styles.segmentRemove}>✕</Text>
                  </Pressable>
                </Pressable>

                {/* Expanded detail — progressive disclosure */}
                {isExpanded && (
                  <View style={styles.segmentDetail}>
                    {/* Quick relabel */}
                    <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                      <View style={styles.pillRow}>
                        {(['technique', 'drilling', 'positional', 'wrestling', 'takedowns',
                          'live_rounds', 'open_mat', 'comp_prep', 'conditioning_finisher', 'other'] as import('@lauburu/shared').SegmentType[]).map((st) => (
                          <Pressable
                            key={st}
                            style={[styles.pillSmall, seg.type === st && styles.pillActive]}
                            onPress={() => updateSegment(seg.id, { type: st })}>
                            <Text style={[styles.pillSmallText, seg.type === st && styles.pillTextActive]}>
                              {SEGMENT_TYPE_LABELS[st]}
                            </Text>
                          </Pressable>
                        ))}
                      </View>
                    </ScrollView>

                    {/* Duration + rounds */}
                    <View style={styles.rowInputs}>
                      <View style={styles.halfInput}>
                        <Text style={styles.sectionLabel}>Duration</Text>
                        <View style={styles.pillRow}>
                          {[10, 15, 20, 25, 30].map((d) => (
                            <Pressable key={d}
                              style={[styles.pillSmall, seg.duration_min === d && styles.pillActive]}
                              onPress={() => updateSegment(seg.id, { duration_min: d })}>
                              <Text style={[styles.pillSmallText, seg.duration_min === d && styles.pillTextActive]}>{d}m</Text>
                            </Pressable>
                          ))}
                        </View>
                      </View>
                    </View>

                    {/* Partner format */}
                    <View>
                      <Text style={styles.sectionLabel}>Format</Text>
                      <View style={styles.pillRow}>
                        {(['group_training', 'one_partner', 'rotating_partners', 'solo'] as PartnerFormat[]).map((pf) => (
                          <Pressable key={pf}
                            style={[styles.pillSmall, seg.partner_format === pf && styles.pillActive]}
                            onPress={() => updateSegment(seg.id, { partner_format: seg.partner_format === pf ? undefined : pf })}>
                            <Text style={[styles.pillSmallText, seg.partner_format === pf && styles.pillTextActive]}>
                              {PARTNER_FORMAT_LABELS[pf]}
                            </Text>
                          </Pressable>
                        ))}
                      </View>
                    </View>

                    {/* Topic worked — free text */}
                    <TextInput
                      style={styles.input}
                      placeholder="Position or topic worked"
                      placeholderTextColor="#555"
                      value={seg.topic_worked ?? ''}
                      onChangeText={(t) => updateSegment(seg.id, { topic_worked: t || undefined })}
                    />
                  </View>
                )}
              </View>
            );
          })}

          {/* Add segment — compact */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <View style={styles.pillRow}>
              {(['technique', 'drilling', 'positional', 'wrestling', 'takedowns',
                'live_rounds', 'conditioning_finisher'] as import('@lauburu/shared').SegmentType[]).map((st) => (
                <Pressable key={st} style={styles.pillSmall} onPress={() => addSegment(st)}>
                  <Text style={styles.pillSmallText}>+ {SEGMENT_TYPE_LABELS[st]}</Text>
                </Pressable>
              ))}
            </View>
          </ScrollView>
        </View>
      )}

      {/* HIIT — protocol */}
      {topMode === 'hiit' && (
        <SelectorRow
          label="Protocol"
          options={HIIT_PRESETS.map((p) => p.id) as string[]}
          labels={Object.fromEntries(HIIT_PRESETS.map((p) => [p.id, p.id === 'custom' ? 'Custom' : `${p.label} — ${p.description}`])) as Record<string, string>}
          value={selectedHIITPreset}
          onChange={(id) => {
            setSelectedHIITPreset(id);
            const preset = HIIT_PRESETS.find((p) => p.id === id);
            if (preset && id !== 'custom') {
              setWorkDur(String(preset.work_s));
              setRestDur(String(preset.rest_s));
              setIntervalRounds(String(preset.rounds));
            }
          }}
          suggestion="30_30"
          suggestionLabel="30/30 — matches your recovery"
        />
      )}

      {/* Steady State */}
      {topMode === 'zone2' && (
        <SelectorRow
          label="Type"
          options={['zone2', 'tempo', 'recovery_cardio'] as ConditioningSubtype[]}
          labels={{ zone2: 'Zone 2', tempo: 'Tempo', recovery_cardio: 'Recovery Session' } as any}
          value={condSubtype}
          onChange={setCondSubtype as any}
          suggestion={'zone2' as any}
          suggestionLabel="Zone 2 builds aerobic base"
        />
      )}

      {/* Weights — focus + custom duration */}
      {topMode === 'weights' && (
        <>
          <SelectorRow
            label="Focus"
            options={['strength', 'functional_muscle', 'rehab'] as LiftingFocus[]}
            labels={LIFTING_FOCUS_LABELS as any}
            value={liftFocus}
            onChange={setLiftFocus as any}
            suggestion={'strength' as any}
            suggestionLabel="Strength matches your training goal"
          />
          <View style={styles.selectorRow}>
            <View style={styles.selectorHeader}>
              <Text style={styles.selectorLabel}>Duration</Text>
              <TextInput
                style={[styles.input, { width: 80, marginLeft: 8 }]}
                value={String(duration)}
                onChangeText={(t) => setDuration(parseInt(t, 10) || 0)}
                keyboardType="number-pad"
                placeholder="45"
                placeholderTextColor="#666"
              />
              <Text style={styles.selectorLabel}> min</Text>
            </View>
          </View>
        </>
      )}

      {/* AI suggestion — shown after mode selection */}
      {topMode && !editing && (
        <View style={styles.suggestionCard}>
          <Text style={styles.suggestionLabel}>AI coach suggestion</Text>
          <Text style={styles.suggestionText}>
            {topMode === 'hiit' ? 'Based on your recovery, 30/30 intervals are a good match today.'
              : topMode === 'zone2' ? 'Zone 2 for 30min would build your aerobic base without impacting tomorrow.'
              : topMode === 'weights' ? 'Moderate intensity for 45min fits your current recovery.'
              : 'Your usual structure looks good for today.'}
          </Text>
          <Text style={styles.suggestionNote}>
            {topMode === 'hiit' ? 'Adjust protocol above if you prefer a different format.'
              : topMode === 'zone2' ? 'Increase duration as your base improves.'
              : topMode === 'weights' ? 'Adjust focus above to target specific muscle groups.'
              : 'Edit segments to match what you actually did.'}
          </Text>
        </View>
      )}

      {/* Full type selector for editing */}
      {editing && (
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
      )}

      {/* Conditioning subtype — only for editing or when not using top-mode flow */}
      {isConditioning && editing && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Cardio</Text>
          <View style={styles.pillRow}>
            {(['hiit', 'intervals', 'sprint_intervals', 'steady_state', 'zone2', 'tempo', 'circuit', 'recovery_cardio'] as ConditioningSubtype[]).map((st) => (
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
          <Text style={[styles.sectionLabel, { marginTop: 8 }]}>Strength / Recovery</Text>
          <View style={styles.pillRow}>
            {(['weight_training', 'mobility', 'respiratory_training', 'other'] as ConditioningSubtype[]).map((st) => (
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

      {/* === Everything below only shows after a top-level choice === */}

      {/* Modality (for conditioning with equipment) */}
      {topMode && isConditioning && !isWeightTraining && !isRespiratory && (
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

      {/* Interval detail — only editable for Custom preset or non-HIIT-mode intervals */}
      {isInterval && (topMode !== 'hiit' || selectedHIITPreset === 'custom') && (
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
      {isWeightTraining && editing && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Focus</Text>
          <View style={styles.pillRow}>
            {(['strength', 'functional_muscle', 'rehab'] as LiftingFocus[]).map((f) => (
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

      {/* Respiratory detail */}
      {isRespiratory && (
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>Device</Text>
          <View style={styles.pillRow}>
            {(['none', 'airofit', 'wello2', 'other'] as import('@lauburu/shared').RespiratoryDevice[]).map((d) => (
              <Pressable
                key={d}
                style={[styles.pill, respDevice === d && styles.pillActive]}
                onPress={() => setRespDevice(d)}>
                <Text style={[styles.pillText, respDevice === d && styles.pillTextActive]}>
                  {RESPIRATORY_DEVICE_LABELS[d]}
                </Text>
              </Pressable>
            ))}
          </View>
          <Text style={styles.sectionLabel}>Breathing Type</Text>
          <View style={styles.pillRow}>
            {(['inspiratory', 'expiratory', 'mixed'] as const).map((t) => (
              <Pressable
                key={t}
                style={[styles.pill, respType === t && styles.pillActive]}
                onPress={() => setRespType(t)}>
                <Text style={[styles.pillText, respType === t && styles.pillTextActive]}>
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </Text>
              </Pressable>
            ))}
          </View>
          <Text style={styles.sectionLabel}>Timing</Text>
          <View style={styles.pillRow}>
            {(['pre_training', 'post_training', 'standalone'] as const).map((t) => (
              <Pressable
                key={t}
                style={[styles.pill, respTiming === t && styles.pillActive]}
                onPress={() => setRespTiming(t)}>
                <Text style={[styles.pillText, respTiming === t && styles.pillTextActive]}>
                  {t === 'pre_training' ? 'Pre-training' : t === 'post_training' ? 'Post-training' : 'Standalone'}
                </Text>
              </Pressable>
            ))}
          </View>
          <View style={styles.rowInputs}>
            <View style={styles.halfInput}>
              <Text style={styles.sectionLabel}>Breaths</Text>
              <TextInput style={styles.input} value={respBreaths} onChangeText={setRespBreaths} keyboardType="number-pad" placeholder="30" placeholderTextColor="#666" />
            </View>
            <View style={styles.halfInput}>
              <Text style={styles.sectionLabel}>Sets</Text>
              <TextInput style={styles.input} value={respSets} onChangeText={setRespSets} keyboardType="number-pad" placeholder="3" placeholderTextColor="#666" />
            </View>
            <View style={styles.halfInput}>
              <Text style={styles.sectionLabel}>Resistance</Text>
              <TextInput style={styles.input} value={respResistance} onChangeText={setRespResistance} keyboardType="number-pad" placeholder="—" placeholderTextColor="#666" />
            </View>
          </View>
        </View>
      )}

      {/* Intensity — only after selection */}
      {(topMode || editing) && (
        <SelectorRow
          label="Intensity"
          options={INTENSITIES}
          labels={INTENSITY_LABELS as Record<string, string>}
          value={intensity}
          onChange={setIntensity as any}
          suggestion="moderate"
          suggestionLabel="Moderate fits your recovery today"
        />
      )}

      {/* Duration — hidden for preset HIIT and weights (weights has its own input) */}
      {(topMode || editing) && topMode !== 'weights' && !(topMode === 'hiit' && selectedHIITPreset !== 'custom') && (
      <View style={styles.section}>
        <Text style={styles.sectionLabel}>
          {topMode === 'zone2' ? 'Suggested duration' : 'Duration'}
        </Text>
        <View style={styles.pillRow}>
          {(topMode === 'zone2'
            ? [20, 30, 45, 60, 90]
            : DURATION_PRESETS
          ).map((d) => (
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
      )}

      {/* More options — only after selection */}
      {(topMode || editing) && <Pressable onPress={() => setShowMore(!showMore)}>
        <Text style={styles.moreToggle}>
          {showMore ? '▾ Less options' : '▸ More options (tags, RPE, notes)'}
        </Text>
      </Pressable>}

      {(topMode || editing) && showMore && (
        <>
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
        </>
      )}

      {/* Submit + Start Timer — only after selection */}
      {(topMode || editing) && <View style={styles.submitRow}>
        <Pressable style={[styles.submitButton, { flex: 1 }]} onPress={handleSubmit}>
          <Text style={styles.submitText}>
            {editing ? 'Save Changes' : 'Log Session'}
          </Text>
        </Pressable>

        {isConditioning && !editing && (
          <Pressable
            style={styles.timerButton}
            onPress={() => {
              const timerMode = isInterval ? 'interval'
                : ['steady_state', 'zone2', 'tempo'].includes(condSubtype) ? 'duration'
                : 'stopwatch';
              const cfg: TimerConfig = {
                mode: timerMode,
                subtype: condSubtype,
                modality: condModality,
                work_s: isInterval ? parseInt(workDur, 10) || 30 : undefined,
                rest_s: isInterval ? parseInt(restDur, 10) || 30 : undefined,
                rounds: isInterval ? parseInt(intervalRounds, 10) || 10 : undefined,
                total_s: timerMode === 'duration' ? duration * 60 : undefined,
              };
              timerSetup(cfg);
              router.push('/timer');
            }}>
            <Text style={styles.timerButtonText}>Start Timer</Text>
          </Pressable>
        )}
      </View>}

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
      {session.conditioning && (
        <Text style={styles.sessionCondDetail}>
          {CONDITIONING_SUBTYPE_LABELS[session.conditioning.subtype]}
          {session.conditioning.modality ? ` · ${MODALITY_LABELS[session.conditioning.modality]}` : ''}
          {session.conditioning.interval
            ? ` · ${session.conditioning.interval.work_duration_s}s/${session.conditioning.interval.rest_duration_s}s × ${session.conditioning.interval.rounds}`
            : ''}
          {session.conditioning.weight_training
            ? ` · ${LIFTING_FOCUS_LABELS[session.conditioning.weight_training.focus]}`
            : ''}
        </Text>
      )}
      {session.segments && session.segments.length > 0 && (
        <Text style={styles.sessionSegments}>
          {session.segments.map((s) => SEGMENT_TYPE_LABELS[s.type]).join(' → ')}
        </Text>
      )}
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
// Today's plan card with quick-log
// ---------------------------------------------------------------------------

function TodayPlanCard({
  onQuickLog,
}: {
  onQuickLog: (type: SessionType, intensity: SessionIntensity) => void;
}) {
  const schedule = usePreferencesStore((s) => s.preferences.schedule);
  const sessions = useTrainingStore((s) => s.sessions);
  const summary = buildDayPlanSummary(todayDate(), schedule, sessions);

  if (summary.status === 'rest_day' || summary.status === 'no_plan') {
    return (
      <View style={styles.planCard}>
        <Text style={styles.planTitle}>Today's Plan</Text>
        <Text style={styles.planEmpty}>
          {summary.status === 'rest_day' ? 'Rest day — no sessions planned.' : 'No sessions planned.'}
        </Text>
      </View>
    );
  }

  const statusColors: Record<string, string> = {
    completed: '#4ade80',
    missed: '#ff6b6b',
    upcoming: '#d4e157',
  };
  const statusIcons: Record<string, string> = {
    completed: '✓',
    missed: '✕',
    upcoming: '○',
  };

  return (
    <View style={styles.planCard}>
      <View style={styles.planHeader}>
        <Text style={styles.planTitle}>Today's Plan</Text>
        <Text style={styles.planCount}>
          {summary.completedCount}/{summary.plannedCount}
        </Text>
      </View>
      {summary.planned.map((p) => (
        <View key={p.planned.id} style={styles.planRow}>
          <Text style={[styles.planIcon, { color: statusColors[p.status] }]}>
            {statusIcons[p.status]}
          </Text>
          <View style={styles.planInfo}>
            <Text style={[styles.planType, p.status === 'completed' && styles.planCompleted]}>
              {SCHEDULE_SESSION_LABELS[p.planned.type] ?? p.planned.type}
              {p.planned.time ? ` · ${p.planned.time}` : ''}
            </Text>
          </View>
          {p.status === 'upcoming' && (
            <Pressable
              style={styles.quickLogBtn}
              onPress={() => onQuickLog(
                p.planned.type as SessionType,
                p.planned.intensity ?? 'moderate',
              )}>
              <Text style={styles.quickLogText}>Log</Text>
            </Pressable>
          )}
          {p.status === 'completed' && (
            <Text style={styles.planDoneLabel}>Done</Text>
          )}
        </View>
      ))}
      {summary.unplannedSessions.length > 0 && (
        <Text style={styles.planExtra}>
          +{summary.unplannedSessions.length} unplanned session{summary.unplannedSessions.length !== 1 ? 's' : ''}
        </Text>
      )}
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
  const addSession = useTrainingStore((s) => s.addSession);
  const [editingSession, setEditingSession] = useState<TrainingSession | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  // Quick-log: prefill form from planned session
  const handleQuickLog = (type: SessionType, intensity: SessionIntensity) => {
    addSession({
      date: todayDate(),
      type,
      intensity,
      duration_min: 60,
    });
    if (user?.id) syncData(user.id).catch(() => {});
    setSubmitted(true);
    setTimeout(() => setSubmitted(false), 3000);
  };

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
    if (user?.id) syncData(user.id).catch(() => {});
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

      {/* Today's plan with quick-log */}
      <TodayPlanCard onQuickLog={handleQuickLog} />

      {/* Toggle form */}
      {!showForm && (
        <Pressable style={styles.showFormBtn} onPress={() => setShowForm(true)}>
          <Text style={styles.showFormText}>+ Log a new session</Text>
        </Pressable>
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
    borderColor: '#d4e157',
    backgroundColor: 'rgba(212,225,87,0.1)',
  },
  pillText: { fontSize: 14, color: '#999' },
  pillTextActive: { color: '#d4e157', fontWeight: '600' },

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

  // Presets
  presetRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  presetCard: {
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#333',
    backgroundColor: 'rgba(255,255,255,0.03)',
    gap: 2,
    minWidth: '30%',
  },
  presetCardActive: { borderColor: '#d4e157', backgroundColor: 'rgba(212,225,87,0.08)' },
  presetLabel: { fontSize: 13, fontWeight: '600', color: '#ccc' },
  presetLabelActive: { color: '#d4e157' },
  presetDesc: { fontSize: 10, opacity: 0.5 },
  presetDur: { fontSize: 10, opacity: 0.4 },

  // Segments
  segmentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 8,
    backgroundColor: 'rgba(255,255,255,0.03)',
    marginBottom: 4,
  },
  segmentNum: { fontSize: 12, fontWeight: '700', color: '#555', width: 16 },
  segmentInfo: { flex: 1 },
  segmentType: { fontSize: 13, fontWeight: '600' },
  segmentMeta: { fontSize: 11, opacity: 0.5 },
  segmentRowExpanded: { borderBottomLeftRadius: 0, borderBottomRightRadius: 0, marginBottom: 0 },
  segmentChevron: { fontSize: 12, opacity: 0.4, marginRight: 4 },
  segmentRemove: { fontSize: 13, color: '#ff6b6b', padding: 4 },
  segmentDetail: {
    backgroundColor: 'rgba(255,255,255,0.02)',
    paddingHorizontal: 10,
    paddingVertical: 10,
    borderBottomLeftRadius: 8,
    borderBottomRightRadius: 8,
    marginBottom: 4,
    gap: 8,
  },
  segmentHint: { fontSize: 12, opacity: 0.4, marginBottom: 4 },
  addSegRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 4 },
  pillSmall: { paddingVertical: 4, paddingHorizontal: 8, borderRadius: 12, borderWidth: 1, borderColor: '#444' },
  pillSmallText: { fontSize: 11, color: '#999' },
  scheduleAddBtn: { paddingVertical: 4, paddingHorizontal: 10, borderRadius: 6, backgroundColor: 'rgba(212,225,87,0.15)' },
  scheduleAddBtnText: { color: '#d4e157', fontSize: 12, fontWeight: '600' },
  modeHeader: { fontSize: 18, fontWeight: '700', color: '#d4e157', paddingVertical: 4 },
  modeChange: { fontSize: 12, fontWeight: '400', color: '#888' },

  quickGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, justifyContent: 'center' },
  quickRow: { flexDirection: 'row', gap: 10, justifyContent: 'center' },

  // AI coach suggestion
  suggestionCard: {
    padding: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(212,225,87,0.06)',
    borderLeftWidth: 3,
    borderLeftColor: '#d4e157',
    gap: 4,
  },
  suggestionLabel: { fontSize: 11, color: '#d4e157', fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5 },
  suggestionText: { fontSize: 13, color: '#ccc', lineHeight: 18 },
  suggestionNote: { fontSize: 11, opacity: 0.4 },
  protocolNote: { fontSize: 12, opacity: 0.5, marginTop: 4 },

  // Stacked selector row
  selectorRow: {
    backgroundColor: 'rgba(255,255,255,0.03)',
    borderRadius: 10,
    padding: 12,
    gap: 8,
  },
  selectorHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  selectorLabel: { fontSize: 14, opacity: 0.6 },
  selectorValueRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  selectorValue: { fontSize: 15, fontWeight: '600', color: '#d4e157' },
  selectorChevron: { fontSize: 12, opacity: 0.4 },
  selectorOptions: { gap: 2 },
  selectorOption: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
  },
  selectorOptionActive: { backgroundColor: 'rgba(212,225,87,0.1)' },
  selectorOptionText: { fontSize: 14, color: '#999' },
  selectorOptionTextActive: { color: '#d4e157', fontWeight: '600' },
  aiSuggestionBubble: {
    backgroundColor: 'rgba(212,225,87,0.08)',
    borderRadius: 8,
    paddingVertical: 6,
    paddingHorizontal: 10,
    alignSelf: 'flex-start',
  },
  aiSuggestionText: { fontSize: 11, color: '#d4e157', opacity: 0.8 },
  quickBtn: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 16,
    borderRadius: 14,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
    gap: 4,
  },
  quickBtnEmoji: { fontSize: 24 },
  quickBtnText: { fontSize: 13, fontWeight: '600', color: '#ccc' },
  moreToggle: { fontSize: 13, color: '#888', paddingVertical: 4 },
  submitRow: { flexDirection: 'row', gap: 10 },
  submitButton: {
    backgroundColor: '#d4e157',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  submitText: { color: '#0a0a0a', fontSize: 17, fontWeight: '700' },
  timerButton: {
    backgroundColor: '#4ade80',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 20,
  },
  timerButtonText: { color: '#0a0a0a', fontSize: 15, fontWeight: '700' },

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
  actionText: { fontSize: 13, color: '#d4e157' },
  sessionCondDetail: { fontSize: 12, color: '#d4e157', opacity: 0.7 },
  sessionSegments: { fontSize: 12, color: '#64b5f6', opacity: 0.7 },

  // Plan card
  planCard: {
    padding: 14,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 8,
  },
  planHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  planTitle: { fontSize: 16, fontWeight: '600' },
  planCount: { fontSize: 14, color: '#d4e157', fontWeight: '600' },
  planEmpty: { fontSize: 13, opacity: 0.5 },
  planRow: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 4 },
  planIcon: { fontSize: 16, width: 20, textAlign: 'center' },
  planInfo: { flex: 1 },
  planType: { fontSize: 14 },
  planCompleted: { opacity: 0.5, textDecorationLine: 'line-through' },
  planDoneLabel: { fontSize: 11, color: '#4ade80', opacity: 0.7 },
  planExtra: { fontSize: 12, opacity: 0.5, marginTop: 2 },
  quickLogBtn: {
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 6,
    backgroundColor: 'rgba(212,225,87,0.15)',
  },
  quickLogText: { color: '#d4e157', fontSize: 12, fontWeight: '600' },
  showFormBtn: {
    padding: 14,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#444',
    borderStyle: 'dashed',
    alignItems: 'center',
  },
  showFormText: { color: '#999', fontSize: 15 },
  sessionTags: { fontSize: 12, opacity: 0.5 },
  sessionNotes: { fontSize: 13, opacity: 0.6, lineHeight: 18 },
});
