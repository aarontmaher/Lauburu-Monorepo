import { useState } from 'react';
import { Pressable, StyleSheet, TextInput } from 'react-native';
import { Text, View } from '@/components/Themed';
import { useNutritionStore } from '../store/nutrition-store';

export function NutritionTargetsEditor() {
  const targets = useNutritionStore((s) => s.targets);
  const setTargets = useNutritionStore((s) => s.setTargets);

  const [draftCalories, setDraftCalories] = useState(targets?.calories_kcal?.toString() ?? '');
  const [draftProtein, setDraftProtein] = useState(targets?.protein_g?.toString() ?? '');
  const [draftCarbs, setDraftCarbs] = useState(targets?.carbs_g?.toString() ?? '');
  const [draftFat, setDraftFat] = useState(targets?.fat_g?.toString() ?? '');
  const [open, setOpen] = useState(false);
  const [dirty, setDirty] = useState(false);

  const parseOpt = (s: string): number | undefined => {
    if (!s.trim()) return undefined;
    const n = Number(s);
    return Number.isFinite(n) ? n : undefined;
  };

  const handleSave = () => {
    const next = {
      calories_kcal: parseOpt(draftCalories),
      protein_g: parseOpt(draftProtein),
      carbs_g: parseOpt(draftCarbs),
      fat_g: parseOpt(draftFat),
    };
    const anySet = Object.values(next).some((v) => v != null);
    setTargets(anySet ? next : null);
    setDirty(false);
    setOpen(false);
  };

  const handleClear = () => {
    setDraftCalories('');
    setDraftProtein('');
    setDraftCarbs('');
    setDraftFat('');
    setTargets(null);
    setDirty(false);
  };

  const markDirty = (setter: (value: string) => void) => (value: string) => {
    setter(value);
    setDirty(true);
  };

  const summary = targets
    ? [
      targets.calories_kcal != null ? `${targets.calories_kcal} kcal` : null,
      targets.protein_g != null ? `${targets.protein_g}g protein` : null,
      targets.carbs_g != null ? `${targets.carbs_g}g carbs` : null,
      targets.fat_g != null ? `${targets.fat_g}g fat` : null,
    ].filter(Boolean).join(' · ')
    : 'Set daily targets';

  return (
    <View style={styles.wrap}>
      <Pressable
        style={styles.header}
        onPress={() => setOpen((v) => !v)}
        accessibilityRole="button"
        accessibilityLabel={open ? 'Hide daily nutrition targets' : 'Edit daily nutrition targets'}>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>Daily targets</Text>
          <Text style={styles.summary} numberOfLines={2}>{summary}</Text>
        </View>
        <Text style={styles.toggle}>{open ? 'Hide' : targets ? 'Edit' : 'Set'}</Text>
      </Pressable>

      {open && (
        <View style={styles.body}>
          <View style={styles.grid}>
            <TargetField label="Calories" value={draftCalories} onChange={markDirty(setDraftCalories)} suffix="kcal" />
            <TargetField label="Protein" value={draftProtein} onChange={markDirty(setDraftProtein)} suffix="g" />
            <TargetField label="Carbs" value={draftCarbs} onChange={markDirty(setDraftCarbs)} suffix="g" />
            <TargetField label="Fat" value={draftFat} onChange={markDirty(setDraftFat)} suffix="g" />
          </View>
          <View style={styles.actions}>
            {targets && (
              <Pressable style={styles.clearBtn} onPress={handleClear}>
                <Text style={styles.clearText}>Clear</Text>
              </Pressable>
            )}
            <Pressable style={[styles.saveBtn, !dirty && styles.saveBtnDisabled]} onPress={handleSave} disabled={!dirty}>
              <Text style={styles.saveText}>Save targets</Text>
            </Pressable>
          </View>
        </View>
      )}
    </View>
  );
}

function TargetField({
  label,
  value,
  suffix,
  onChange,
}: {
  label: string;
  value: string;
  suffix: string;
  onChange: (value: string) => void;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          value={value}
          onChangeText={onChange}
          keyboardType="number-pad"
          placeholder="--"
          placeholderTextColor="#555"
        />
        <Text style={styles.suffix}>{suffix}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.08)',
    paddingTop: 10,
    gap: 10,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  title: { fontSize: 13, fontWeight: '700' },
  summary: { fontSize: 12, opacity: 0.62, marginTop: 2, lineHeight: 16 },
  toggle: { fontSize: 13, color: '#d4e157', fontWeight: '700' },
  body: { gap: 10 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  field: { width: '48%', gap: 4 },
  fieldLabel: { fontSize: 11, opacity: 0.55 },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
    borderRadius: 8,
    paddingHorizontal: 8,
    backgroundColor: 'rgba(0,0,0,0.18)',
  },
  input: { flex: 1, minHeight: 38, color: '#fff', fontSize: 14, paddingVertical: 8 },
  suffix: { fontSize: 11, opacity: 0.5 },
  actions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 8 },
  clearBtn: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.14)',
  },
  clearText: { color: '#ddd', fontSize: 12, fontWeight: '700' },
  saveBtn: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8, backgroundColor: '#d4e157' },
  saveBtnDisabled: { opacity: 0.45 },
  saveText: { color: '#101010', fontSize: 12, fontWeight: '800' },
});
