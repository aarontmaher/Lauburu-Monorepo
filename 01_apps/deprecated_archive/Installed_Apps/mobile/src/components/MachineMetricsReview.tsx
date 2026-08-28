/**
 * MachineMetricsReview — compact post-session capture for cardio machine
 * numbers that WHOOP cannot see.
 *
 * Used primarily on the live timer's "complete" phase so that after a
 * phone-timer HIIT/zone2 session, the user can optionally tap in what
 * the machine console showed (distance, calories, avg power, avg HR,
 * etc.) before the session is saved. Everything is optional — the
 * timer's Save & Close path stays fast and works with zero fields
 * entered.
 *
 * The fields shown adapt to modality via `machineKindForModality`:
 * rowers get pace/strokes, bikes get power/cadence, treadmills get
 * speed, and so on. This is the same philosophy as the train.tsx
 * EntryForm machine block, extracted here so the timer flow can
 * capture metrics without dragging the full entry form along.
 *
 * Controlled component: parent owns the `Partial<MachineMetrics>`
 * state and passes it in via `value`, receiving updates via
 * `onChange`. Parent decides when the metrics get attached to a
 * session and whether the source flips to `manual_machine_entry`.
 *
 * Future-ready: when live BLE/FTMS lands, the same component can be
 * used as the manual override surface after a connected session, and
 * the parent can prefill `value` from the live connector's final
 * sample so the user sees the live numbers and can adjust.
 */
import { StyleSheet, TextInput } from 'react-native';
import { Text, View } from '@/components/Themed';
import type { MachineMetrics, Modality } from '@lauburu/shared';
import { machineKindForModality } from '../services/machine-connector';

interface Props {
  /** Modality of the session. Drives which fields are shown. */
  modality: Modality | undefined;
  /** Current metrics state — parent-owned. */
  value: Partial<MachineMetrics>;
  /** Callback invoked on every edit. */
  onChange: (next: Partial<MachineMetrics>) => void;
}

/** Field descriptor — label, units, the MachineMetrics key it writes to. */
interface FieldDef {
  key: keyof MachineMetrics;
  label: string;
  placeholder: string;
}

/**
 * Pick the fields to show for a given modality. Keep it compact — no
 * more than ~6 per modality so the timer complete screen doesn't turn
 * into a data-entry wall.
 */
function fieldsForModality(modality: Modality | undefined): FieldDef[] {
  const kind = machineKindForModality(modality);
  switch (kind) {
    case 'bike':
      return [
        { key: 'distance_m', label: 'Distance (m)', placeholder: 'e.g. 5000' },
        { key: 'calories', label: 'Calories', placeholder: 'e.g. 220' },
        { key: 'avg_power_w', label: 'Avg power (W)', placeholder: 'e.g. 185' },
        { key: 'max_power_w', label: 'Max power (W)', placeholder: 'e.g. 420' },
        { key: 'avg_cadence', label: 'Avg cadence (rpm)', placeholder: 'e.g. 82' },
        { key: 'avg_hr_bpm', label: 'Avg HR (bpm)', placeholder: 'e.g. 148' },
      ];
    case 'rower':
      return [
        { key: 'distance_m', label: 'Distance (m)', placeholder: 'e.g. 2000' },
        { key: 'calories', label: 'Calories', placeholder: 'e.g. 140' },
        { key: 'avg_pace_s', label: 'Avg /500m (sec)', placeholder: 'e.g. 115' },
        { key: 'strokes', label: 'Strokes', placeholder: 'e.g. 220' },
        { key: 'avg_cadence', label: 'Avg SPM', placeholder: 'e.g. 28' },
        { key: 'avg_hr_bpm', label: 'Avg HR (bpm)', placeholder: 'e.g. 155' },
      ];
    case 'skierg':
      return [
        { key: 'distance_m', label: 'Distance (m)', placeholder: 'e.g. 2000' },
        { key: 'calories', label: 'Calories', placeholder: 'e.g. 140' },
        { key: 'avg_power_w', label: 'Avg power (W)', placeholder: 'e.g. 180' },
        { key: 'avg_pace_s', label: 'Avg /500m (sec)', placeholder: 'e.g. 118' },
        { key: 'avg_hr_bpm', label: 'Avg HR (bpm)', placeholder: 'e.g. 155' },
      ];
    case 'treadmill':
      return [
        { key: 'distance_m', label: 'Distance (m)', placeholder: 'e.g. 3000' },
        { key: 'calories', label: 'Calories', placeholder: 'e.g. 180' },
        { key: 'avg_speed_kmh', label: 'Avg speed (km/h)', placeholder: 'e.g. 11' },
        { key: 'max_speed_kmh', label: 'Max speed (km/h)', placeholder: 'e.g. 16' },
        { key: 'avg_hr_bpm', label: 'Avg HR (bpm)', placeholder: 'e.g. 160' },
      ];
    default:
      return [
        { key: 'distance_m', label: 'Distance (m)', placeholder: 'optional' },
        { key: 'calories', label: 'Calories', placeholder: 'optional' },
        { key: 'avg_hr_bpm', label: 'Avg HR (bpm)', placeholder: 'optional' },
      ];
  }
}

/**
 * Parse a text input into a number or undefined. Empty string clears
 * the field. Non-numeric input is ignored — the previous numeric value
 * is preserved so the user doesn't lose typed data on a typo.
 */
function parseNumericField(raw: string): number | undefined {
  const trimmed = raw.trim();
  if (trimmed.length === 0) return undefined;
  const n = Number(trimmed);
  if (!Number.isFinite(n)) return undefined;
  return n;
}

export function MachineMetricsReview({ modality, value, onChange }: Props) {
  const fields = fieldsForModality(modality);

  const updateField = (key: keyof MachineMetrics, raw: string) => {
    const parsed = parseNumericField(raw);
    const next: Partial<MachineMetrics> = { ...value };
    if (parsed == null) {
      delete next[key];
    } else {
      (next as Record<string, number>)[key as string] = parsed;
    }
    onChange(next);
  };

  return (
    <View style={styles.wrap}>
      <Text style={styles.label}>Machine data (optional)</Text>
      <Text style={styles.hint}>
        Tap in what the machine console showed — WHOOP can't see these.
      </Text>
      <View style={styles.grid}>
        {fields.map((f) => {
          const current = value[f.key];
          const displayValue =
            current == null ? '' : String(current);
          return (
            <View key={f.key} style={styles.cell}>
              <Text style={styles.cellLabel}>{f.label}</Text>
              <TextInput
                style={styles.input}
                value={displayValue}
                onChangeText={(t) => updateField(f.key, t)}
                placeholder={f.placeholder}
                placeholderTextColor="#555"
                keyboardType="decimal-pad"
                returnKeyType="done"
              />
            </View>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    padding: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 6,
    width: '100%',
  },
  label: {
    fontSize: 11,
    color: '#b0b8c3',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  hint: {
    fontSize: 10,
    opacity: 0.5,
    fontStyle: 'italic',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 4,
    marginHorizontal: -4,
  },
  cell: {
    width: '50%',
    paddingHorizontal: 4,
    paddingVertical: 4,
  },
  cellLabel: {
    fontSize: 10,
    opacity: 0.55,
    marginBottom: 2,
  },
  input: {
    backgroundColor: 'rgba(0,0,0,0.35)',
    borderWidth: 1,
    borderColor: '#333',
    borderRadius: 6,
    paddingVertical: 6,
    paddingHorizontal: 8,
    fontSize: 13,
    color: '#e6ecf3',
  },
});
