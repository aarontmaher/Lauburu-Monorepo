import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, TextInput } from 'react-native';
import { Text, View } from '@/components/Themed';
import {
  DAYS_ORDER,
  DAY_LABELS,
  GRAPPLING_SCHEDULE_SUBTYPE_LABELS,
  GRAPPLING_SCHEDULE_SUBTYPES,
  SCHEDULE_SESSION_LABELS,
  countPlannedSessions,
  type DayOfWeek,
  type GrapplingScheduleSubtype,
  type ScheduleSessionType,
} from '@lauburu/shared';
import { usePreferencesStore } from '../store/preferences-store';

const SCHEDULE_TYPES: ScheduleSessionType[] = ['grappling', 'conditioning', 'recovery', 'other'];

function normalizeTimeInput(raw: string): string {
  const cleaned = raw.trim().replace(/[^\d:]/g, '');
  if (!cleaned) return '';
  const [hRaw, mRaw] = cleaned.includes(':')
    ? cleaned.split(':')
    : [cleaned.slice(0, Math.max(1, cleaned.length - 2)), cleaned.length > 2 ? cleaned.slice(-2) : '00'];
  const h = Number(hRaw);
  const m = Number(mRaw || '0');
  if (!Number.isFinite(h) || !Number.isFinite(m) || h < 0 || h > 23 || m < 0 || m > 59) return '';
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

export function WeeklyScheduleEditor() {
  const prefs = usePreferencesStore((s) => s.preferences);
  const addSess = usePreferencesStore((s) => s.addSession);
  const removeSess = usePreferencesStore((s) => s.removeSession);
  const toggleSess = usePreferencesStore((s) => s.toggleSession);
  const updateSess = usePreferencesStore((s) => s.updateSession);
  const [expanded, setExpanded] = useState(false);
  const [expandedDay, setExpandedDay] = useState<DayOfWeek | null>(null);
  const [addingType, setAddingType] = useState<ScheduleSessionType>('grappling');

  const total = countPlannedSessions(prefs.schedule);

  const plannedLabel = (s: { type: ScheduleSessionType; grappling_subtype?: GrapplingScheduleSubtype }) => {
    if (s.type === 'grappling' && s.grappling_subtype) return GRAPPLING_SCHEDULE_SUBTYPE_LABELS[s.grappling_subtype];
    return SCHEDULE_SESSION_LABELS[s.type] ?? s.type;
  };

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>Weekly schedule</Text>
          <Text style={styles.summary}>{total > 0 ? `${total} planned session${total === 1 ? '' : 's'}` : 'Set your recurring training week'}</Text>
        </View>
        <Pressable
          onPress={() => setExpanded((v) => !v)}
          hitSlop={8}
          accessibilityRole="button"
          accessibilityLabel={expanded ? 'Hide weekly schedule editor' : 'Edit weekly schedule'}>
          <Text style={styles.edit}>{expanded ? 'Hide' : total > 0 ? 'Edit' : 'Set'}</Text>
        </Pressable>
      </View>

      {!expanded && total > 0 && (
        <View style={styles.summaryRow}>
          {DAYS_ORDER.map((day) => {
            const count = prefs.schedule[day]?.filter((s) => s.enabled).length ?? 0;
            return (
              <View key={day} style={styles.summaryCell}>
                <Text style={styles.dayShort}>{DAY_LABELS[day].slice(0, 3)}</Text>
                <Text style={[styles.dayCount, count > 0 && styles.dayCountActive]}>{count > 0 ? count : '-'}</Text>
              </View>
            );
          })}
        </View>
      )}

      {expanded && (
        <View style={styles.editor}>
          {DAYS_ORDER.map((day) => {
            const sessions = prefs.schedule[day];
            const isExpanded = expandedDay === day;
            return (
              <View key={day} style={styles.dayBlock}>
                <Pressable
                  style={styles.dayHeader}
                  onPress={() => setExpandedDay(isExpanded ? null : day)}
                  accessibilityRole="button"
                  accessibilityLabel={`${isExpanded ? 'Collapse' : 'Expand'} ${DAY_LABELS[day]} schedule`}>
                  <Text style={styles.dayName}>{DAY_LABELS[day]}</Text>
                  <Text style={styles.dayPlan} numberOfLines={1}>
                    {sessions.filter((s) => s.enabled).length > 0
                      ? sessions.filter((s) => s.enabled).map((s) => {
                        const label = plannedLabel(s);
                        return s.time ? `${s.time} ${label}` : label;
                      }).join(' · ')
                      : 'Rest'}
                  </Text>
                  <Text style={styles.chevron}>{isExpanded ? '▾' : '▸'}</Text>
                </Pressable>

                {isExpanded && (
                  <View style={styles.dayBody}>
                    {sessions.map((s) => (
                      <View key={s.id} style={styles.sessionBlock}>
                        <View style={styles.sessionRow}>
                          <Pressable onPress={() => toggleSess(day, s.id)} hitSlop={8}>
                            <Text style={[styles.check, !s.enabled && { opacity: 0.35 }]}>{s.enabled ? '✓' : '○'}</Text>
                          </Pressable>
                          <Text style={[styles.sessionName, !s.enabled && { opacity: 0.35 }]}>{plannedLabel(s)}</Text>
                          <TimeField value={s.time} onCommit={(time) => updateSess(day, s.id, { time })} />
                          <Pressable onPress={() => removeSess(day, s.id)} hitSlop={8}>
                            <Text style={styles.remove}>×</Text>
                          </Pressable>
                        </View>

                        {s.type === 'grappling' && (
                          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                            <View style={styles.pillRow}>
                              {GRAPPLING_SCHEDULE_SUBTYPES.map((gs) => {
                                const active = s.grappling_subtype === gs;
                                return (
                                  <Pressable
                                    key={gs}
                                    style={[styles.pill, active && styles.pillActive]}
                                    onPress={() => updateSess(day, s.id, { grappling_subtype: active ? undefined : gs })}>
                                    <Text style={[styles.pillText, active && styles.pillTextActive]}>
                                      {GRAPPLING_SCHEDULE_SUBTYPE_LABELS[gs]}
                                    </Text>
                                  </Pressable>
                                );
                              })}
                            </View>
                          </ScrollView>
                        )}
                      </View>
                    ))}

                    <View style={styles.addRow}>
                      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                        <View style={styles.pillRow}>
                          {SCHEDULE_TYPES.map((type) => (
                            <Pressable
                              key={type}
                              style={[styles.pill, addingType === type && styles.pillActive]}
                              onPress={() => setAddingType(type)}>
                              <Text style={[styles.pillText, addingType === type && styles.pillTextActive]}>
                                {SCHEDULE_SESSION_LABELS[type]}
                              </Text>
                            </Pressable>
                          ))}
                        </View>
                      </ScrollView>
                      <Pressable style={styles.addBtn} onPress={() => addSess(day, addingType)}>
                        <Text style={styles.addText}>Add</Text>
                      </Pressable>
                    </View>
                  </View>
                )}
              </View>
            );
          })}
        </View>
      )}
    </View>
  );
}

function TimeField({ value, onCommit }: { value: string | undefined; onCommit: (value: string) => void }) {
  const [text, setText] = useState(value ?? '');
  return (
    <TextInput
      style={styles.timeInput}
      value={text}
      placeholder="--:--"
      placeholderTextColor="#555"
      keyboardType="numbers-and-punctuation"
      maxLength={5}
      onChangeText={setText}
      onBlur={() => {
        const next = normalizeTimeInput(text);
        setText(next);
        if (next !== (value ?? '')) onCommit(next);
      }}
    />
  );
}

const styles = StyleSheet.create({
  card: { padding: 14, borderRadius: 10, backgroundColor: 'rgba(255,255,255,0.05)', gap: 12 },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 },
  title: { fontSize: 15, fontWeight: '700' },
  summary: { fontSize: 12, opacity: 0.62, marginTop: 2 },
  edit: { fontSize: 13, fontWeight: '700', color: '#d4e157' },
  summaryRow: { flexDirection: 'row', justifyContent: 'space-between', gap: 6 },
  summaryCell: { flex: 1, alignItems: 'center', paddingVertical: 6, borderRadius: 8, backgroundColor: 'rgba(0,0,0,0.16)' },
  dayShort: { fontSize: 10, opacity: 0.5 },
  dayCount: { fontSize: 14, fontWeight: '700', color: '#666' },
  dayCountActive: { color: '#d4e157' },
  editor: { gap: 8 },
  dayBlock: { borderRadius: 8, backgroundColor: 'rgba(0,0,0,0.14)', overflow: 'hidden' },
  dayHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: 10 },
  dayName: { width: 82, fontSize: 13, fontWeight: '700' },
  dayPlan: { flex: 1, fontSize: 12, opacity: 0.68 },
  chevron: { fontSize: 12, color: '#d4e157' },
  dayBody: { padding: 10, paddingTop: 0, gap: 8 },
  sessionBlock: { gap: 6 },
  sessionRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  check: { fontSize: 18, color: '#d4e157', width: 22, textAlign: 'center' },
  sessionName: { flex: 1, fontSize: 13, fontWeight: '600' },
  timeInput: {
    width: 56,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
    borderRadius: 7,
    color: '#fff',
    fontSize: 12,
    paddingHorizontal: 7,
    paddingVertical: 6,
  },
  remove: { color: '#ff8a8a', fontSize: 18, width: 20, textAlign: 'center' },
  pillRow: { flexDirection: 'row', gap: 6, alignItems: 'center' },
  pill: { paddingHorizontal: 9, paddingVertical: 6, borderRadius: 999, backgroundColor: 'rgba(255,255,255,0.06)' },
  pillActive: { backgroundColor: '#d4e157' },
  pillText: { fontSize: 11, color: '#ddd', fontWeight: '600' },
  pillTextActive: { color: '#111' },
  addRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  addBtn: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8, backgroundColor: '#d4e157' },
  addText: { color: '#111', fontSize: 12, fontWeight: '800' },
});
