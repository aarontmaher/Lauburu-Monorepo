/**
 * NutritionCard — first real mobile nutrition surface.
 *
 * Shows today's calories + macros + water with a compact edit-in-place
 * flow. Source today is manual entry only; the component reads/writes
 * through `useNutritionStore` which matches the shared `NutritionRecord`
 * shape so a future Cronometer API swap is a drop-in replacement.
 *
 * States:
 *   empty → "No fuel logged yet" + + Log meal button
 *   filled, not editing → 5-cell metric grid + updated-at line + Edit
 *   editing → five inline TextInputs + Save / Cancel
 *
 * When targets are set (via store.setTargets), the metric grid gets a
 * tiny percent-of-target badge under each value. Honest: the badge only
 * renders for fields that actually have a target AND a value.
 */
import { useState } from 'react';
import { StyleSheet, Pressable, TextInput } from 'react-native';
import { Text, View } from '@/components/Themed';
import { useNutritionStore } from '../store/nutrition-store';
import { NUTRITION_SOURCE_LABELS } from '@lauburu/shared';
import type { NutritionSource } from '@lauburu/shared';

/**
 * Entry modes exposed to the user. Manual is the only live path today.
 * Label scan and barcode are accuracy-first scanner seams (both rank
 * above photo AI in the shared architecture — see nutrition.ts header).
 * AI photo is deliberately the last option and framed as a convenience
 * layer, not the default truth source.
 */
type EntryMode = 'manual' | 'label_scan' | 'barcode' | 'ai_photo';

const ENTRY_MODES: { id: EntryMode; label: string; source: NutritionSource }[] = [
  { id: 'manual', label: 'Manual', source: 'manual' },
  { id: 'label_scan', label: 'Label scan', source: 'nutrition_label_scan' },
  { id: 'barcode', label: 'Barcode', source: 'barcode' },
  { id: 'ai_photo', label: 'AI photo', source: 'ai_estimate' },
];

function formatInt(value: number | undefined | null): string {
  if (value == null) return '—';
  return String(Math.round(value));
}

function formatRelative(iso: string | undefined): string {
  if (!iso) return '';
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const diffMs = Date.now() - then;
  const mins = Math.round(diffMs / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function pctOfTarget(value: number | undefined, target: number | undefined): string | null {
  if (value == null || target == null || target === 0) return null;
  const pct = Math.round((value / target) * 100);
  return `${pct}%`;
}

function MetricCell({
  label,
  value,
  unit,
  targetPct,
}: {
  label: string;
  value: string;
  unit: string;
  targetPct: string | null;
}) {
  return (
    <View style={styles.metricCell}>
      <Text style={styles.metricValue}>
        {value}
        <Text style={styles.metricUnit}>{unit}</Text>
      </Text>
      <Text style={styles.metricLabel}>{label}</Text>
      {targetPct ? <Text style={styles.metricPct}>{targetPct} of target</Text> : null}
    </View>
  );
}

export function NutritionCard() {
  const today = useNutritionStore((s) => s.today);
  const targets = useNutritionStore((s) => s.targets);
  const updateToday = useNutritionStore((s) => s.updateToday);

  const [editing, setEditing] = useState(false);
  const [entryMode, setEntryMode] = useState<EntryMode>('manual');
  const [draftCalories, setDraftCalories] = useState('');
  const [draftProtein, setDraftProtein] = useState('');
  const [draftCarbs, setDraftCarbs] = useState('');
  const [draftFat, setDraftFat] = useState('');
  const [draftWater, setDraftWater] = useState('');

  const startEdit = () => {
    setDraftCalories(today?.calories_kcal?.toString() ?? '');
    setDraftProtein(today?.protein_g?.toString() ?? '');
    setDraftCarbs(today?.carbs_g?.toString() ?? '');
    setDraftFat(today?.fat_g?.toString() ?? '');
    setDraftWater(today?.water_ml?.toString() ?? '');
    setEditing(true);
  };

  const cancelEdit = () => {
    setEditing(false);
  };

  const saveEdit = () => {
    const parseOpt = (s: string): number | undefined => {
      if (!s.trim()) return undefined;
      const n = Number(s);
      return Number.isFinite(n) ? n : undefined;
    };
    updateToday({
      calories_kcal: parseOpt(draftCalories),
      protein_g: parseOpt(draftProtein),
      carbs_g: parseOpt(draftCarbs),
      fat_g: parseOpt(draftFat),
      water_ml: parseOpt(draftWater),
    });
    setEditing(false);
  };

  const hasAnyValue =
    today &&
    (today.calories_kcal != null ||
      today.protein_g != null ||
      today.carbs_g != null ||
      today.fat_g != null ||
      today.water_ml != null);

  const sourceLabel = today ? NUTRITION_SOURCE_LABELS[today.source] : 'Manual';

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <View style={styles.titleBlock}>
          <Text style={styles.cardTitle}>Nutrition</Text>
          <Text style={styles.sourceLabel}>{sourceLabel.toLowerCase()} · today</Text>
        </View>
        {!editing && (
          <Pressable onPress={startEdit} style={styles.editBtn} hitSlop={6}>
            <Text style={styles.editBtnText}>{hasAnyValue ? 'Edit' : '+ Log'}</Text>
          </Pressable>
        )}
      </View>

      {/* Empty state */}
      {!editing && !hasAnyValue && (
        <Text style={styles.emptyText}>
          No fuel logged yet today. Tap + Log to enter calories and macros
          manually. A Cronometer auto-sync will replace this flow in a
          future batch.
        </Text>
      )}

      {/* Display mode */}
      {!editing && hasAnyValue && today && (
        <>
          <View style={styles.metricsGrid}>
            <MetricCell
              label="Calories"
              value={formatInt(today.calories_kcal)}
              unit=" kcal"
              targetPct={pctOfTarget(today.calories_kcal, targets?.calories_kcal)}
            />
            <MetricCell
              label="Protein"
              value={formatInt(today.protein_g)}
              unit=" g"
              targetPct={pctOfTarget(today.protein_g, targets?.protein_g)}
            />
            <MetricCell
              label="Carbs"
              value={formatInt(today.carbs_g)}
              unit=" g"
              targetPct={pctOfTarget(today.carbs_g, targets?.carbs_g)}
            />
            <MetricCell
              label="Fat"
              value={formatInt(today.fat_g)}
              unit=" g"
              targetPct={pctOfTarget(today.fat_g, targets?.fat_g)}
            />
            <MetricCell
              label="Water"
              value={formatInt(today.water_ml)}
              unit=" ml"
              targetPct={null}
            />
          </View>
          <Text style={styles.updatedAt}>
            Updated {formatRelative(today.updated_at)}
          </Text>
        </>
      )}

      {/* Edit mode */}
      {editing && (
        <>
          {/* Entry mode picker — accuracy-first ordering. Manual is the
              only live path today; label scan + barcode + AI photo are
              scaffolded with honest placeholders. Label scan and barcode
              RANK ABOVE AI photo per the shared architecture. */}
          <View style={styles.modeRow}>
            {ENTRY_MODES.map((m) => {
              const isActive = entryMode === m.id;
              return (
                <Pressable
                  key={m.id}
                  style={[styles.modePill, isActive && styles.modePillActive]}
                  onPress={() => setEntryMode(m.id)}>
                  <Text
                    style={[
                      styles.modePillText,
                      isActive && styles.modePillTextActive,
                    ]}>
                    {m.label}
                  </Text>
                </Pressable>
              );
            })}
          </View>

          {/* Label scan placeholder — accuracy-first seam */}
          {entryMode === 'label_scan' && (
            <View style={styles.placeholderPanel}>
              <Text style={styles.placeholderTitle}>Label scan · coming soon</Text>
              <Text style={styles.placeholderBody}>
                Point the camera at a package's nutrition label. Values
                come straight from the package print — most accurate for
                packaged foods, ranks above AI photo estimates.
              </Text>
              <Text style={styles.placeholderHint}>
                Use Manual for now. The scan flow will write records with
                source "Label scan" so coaching can trust them directly.
              </Text>
            </View>
          )}

          {/* Barcode placeholder */}
          {entryMode === 'barcode' && (
            <View style={styles.placeholderPanel}>
              <Text style={styles.placeholderTitle}>Barcode · coming soon</Text>
              <Text style={styles.placeholderBody}>
                Scan the barcode on a packaged item. The app looks up a
                product database for structured macros. Accurate for
                well-known products, ranks above AI photo estimates.
              </Text>
              <Text style={styles.placeholderHint}>
                Use Manual for now. Scanned records will be tagged with
                source "Barcode".
              </Text>
            </View>
          )}

          {/* AI photo placeholder — framed as convenience */}
          {entryMode === 'ai_photo' && (
            <View style={styles.placeholderPanel}>
              <Text style={styles.placeholderTitle}>AI photo · convenience layer</Text>
              <Text style={styles.placeholderBody}>
                A future option for unpackaged or restaurant meals where
                no label or barcode exists. AI photo is NOT the default
                truth source — coaching will weight it below Manual,
                Label scan, and Barcode, and you'll always be able to
                review and correct each estimate.
              </Text>
              <Text style={styles.placeholderHint}>
                Use Manual for now. Corrected AI records will be tagged
                with source "AI (corrected)" for audit.
              </Text>
            </View>
          )}

          {/* Manual entry grid — the only live entry path today */}
          {entryMode === 'manual' && (
          <View style={styles.editGrid}>
            <View style={styles.editField}>
              <Text style={styles.editLabel}>Calories (kcal)</Text>
              <TextInput
                style={styles.editInput}
                value={draftCalories}
                onChangeText={setDraftCalories}
                keyboardType="number-pad"
                placeholder="—"
                placeholderTextColor="#555"
              />
            </View>
            <View style={styles.editField}>
              <Text style={styles.editLabel}>Protein (g)</Text>
              <TextInput
                style={styles.editInput}
                value={draftProtein}
                onChangeText={setDraftProtein}
                keyboardType="number-pad"
                placeholder="—"
                placeholderTextColor="#555"
              />
            </View>
            <View style={styles.editField}>
              <Text style={styles.editLabel}>Carbs (g)</Text>
              <TextInput
                style={styles.editInput}
                value={draftCarbs}
                onChangeText={setDraftCarbs}
                keyboardType="number-pad"
                placeholder="—"
                placeholderTextColor="#555"
              />
            </View>
            <View style={styles.editField}>
              <Text style={styles.editLabel}>Fat (g)</Text>
              <TextInput
                style={styles.editInput}
                value={draftFat}
                onChangeText={setDraftFat}
                keyboardType="number-pad"
                placeholder="—"
                placeholderTextColor="#555"
              />
            </View>
            <View style={styles.editField}>
              <Text style={styles.editLabel}>Water (ml)</Text>
              <TextInput
                style={styles.editInput}
                value={draftWater}
                onChangeText={setDraftWater}
                keyboardType="number-pad"
                placeholder="—"
                placeholderTextColor="#555"
              />
            </View>
          </View>
          )}

          {/* Action row — Save only shows for Manual; scanner modes
              show just Cancel while they're placeholders. */}
          <View style={styles.editActions}>
            <Pressable onPress={cancelEdit} style={styles.cancelBtn}>
              <Text style={styles.cancelBtnText}>
                {entryMode === 'manual' ? 'Cancel' : 'Close'}
              </Text>
            </Pressable>
            {entryMode === 'manual' && (
              <Pressable onPress={saveEdit} style={styles.saveBtn}>
                <Text style={styles.saveBtnText}>Save</Text>
              </Pressable>
            )}
          </View>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 10,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  titleBlock: { gap: 2 },
  cardTitle: { fontSize: 18, fontWeight: '600' },
  sourceLabel: {
    fontSize: 11,
    opacity: 0.4,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  editBtn: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#d4e157',
  },
  editBtnText: { color: '#d4e157', fontSize: 13, fontWeight: '600' },

  emptyText: { fontSize: 13, opacity: 0.5, lineHeight: 18 },

  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  metricCell: {
    minWidth: '30%',
    flexGrow: 1,
    padding: 10,
    borderRadius: 8,
    backgroundColor: 'rgba(255,255,255,0.03)',
    gap: 2,
  },
  metricValue: { fontSize: 16, fontWeight: '700', color: '#d4e157' },
  metricUnit: { fontSize: 11, opacity: 0.5, fontWeight: '500' },
  metricLabel: { fontSize: 11, opacity: 0.5 },
  metricPct: { fontSize: 10, color: '#a8b84a', opacity: 0.8 },

  updatedAt: { fontSize: 11, opacity: 0.4 },

  modeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  modePill: {
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#444',
  },
  modePillActive: {
    borderColor: '#d4e157',
    backgroundColor: 'rgba(212,225,87,0.1)',
  },
  modePillText: { fontSize: 12, color: '#999' },
  modePillTextActive: { color: '#d4e157', fontWeight: '600' },

  placeholderPanel: {
    padding: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(212,225,87,0.05)',
    borderLeftWidth: 3,
    borderLeftColor: '#d4e157',
    gap: 6,
  },
  placeholderTitle: {
    fontSize: 12,
    color: '#d4e157',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  placeholderBody: { fontSize: 12, opacity: 0.7, lineHeight: 17 },
  placeholderHint: { fontSize: 11, opacity: 0.45, lineHeight: 15, fontStyle: 'italic' },

  editGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  editField: { minWidth: '30%', flexGrow: 1, gap: 4 },
  editLabel: {
    fontSize: 11,
    opacity: 0.5,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  editInput: {
    borderWidth: 1,
    borderColor: '#333',
    borderRadius: 8,
    paddingVertical: 8,
    paddingHorizontal: 10,
    fontSize: 14,
    color: '#f0f0f0',
    backgroundColor: 'rgba(255,255,255,0.04)',
  },
  editActions: {
    flexDirection: 'row',
    gap: 8,
    justifyContent: 'flex-end',
  },
  cancelBtn: {
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#666',
  },
  cancelBtnText: { color: '#999', fontSize: 13 },
  saveBtn: {
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 8,
    backgroundColor: '#d4e157',
  },
  saveBtnText: { color: '#0a0a0a', fontSize: 13, fontWeight: '700' },
});
