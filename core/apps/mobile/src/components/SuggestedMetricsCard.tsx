/**
 * SuggestedMetricsCard — optional "things you could track" prompts.
 *
 * Rules enforced by the underlying `computeSuggestedMetrics`:
 *   - only renders when at least one suggestion is justified
 *   - max 3 suggestions shown at once
 *   - never auto-enables anything
 *   - framed as optional
 *
 * The card is intentionally low-key: it's *not* a dashboard feature,
 * it's a Coach hint that only appears when the app can see a real
 * blind spot that would unlock more useful analysis.
 */
import { useEffect, useMemo, useState } from 'react';
import { StyleSheet, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { Text, View } from '@/components/Themed';
import { useHealthStore } from '../store/health-store';
import { useWhoopStore } from '../store/whoop-store';
import { useNutritionStore } from '../store/nutrition-store';
import { useTrainingStore } from '../store/training-store';
import { computeSuggestedMetrics } from '../services/suggested-metrics';
import { readStoredJson } from '../store/secure-storage';

const WHOOP_CSV_CACHE_KEY = 'whoop_csv_imported_v1';

export function SuggestedMetricsCard() {
  const router = useRouter();
  const healthDays = useHealthStore((s) => s.days);
  const healthLastSyncAt = useHealthStore((s) => s.lastSyncAt);
  const whoopStatus = useWhoopStore((s) => s.status);
  const whoopDay = useWhoopStore((s) => s.day);
  const nutritionToday = useNutritionStore((s) => s.today);
  const sessions = useTrainingStore((s) => s.sessions);

  // Hydrate WHOOP CSV imported state from secureStorage cache. The
  // WhoopCsvRow writes this whenever it refreshes status. Unknown (no
  // cache) is treated as "imported" conservatively — we'd rather not
  // pester a WHOOP user with an "upload your export" suggestion if
  // we don't know they haven't.
  const [whoopCsvImported, setWhoopCsvImported] = useState<boolean | null>(null);
  useEffect(() => {
    void (async () => {
      try {
        const cached = await readStoredJson<{ imported: boolean }>(WHOOP_CSV_CACHE_KEY);
        setWhoopCsvImported(cached?.imported ?? false);
      } catch { setWhoopCsvImported(false); }
    })();
  }, []);

  const suggestions = useMemo(() => {
    const todayIso = new Date().toISOString().slice(0, 10);
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 7);
    const cutoffStr = cutoff.toISOString().slice(0, 10);
    const recent = sessions.filter((s) => s.date >= cutoffStr && s.date <= todayIso);
    const withRpe = recent.filter((s: any) => typeof s.rpe === 'number' && s.rpe > 0);
    const grappling = recent.filter((s) => s.type.toLowerCase().includes('grap'));
    const grapplingRounds = grappling.filter((s: any) => Array.isArray(s?.rounds) && s.rounds.length > 0);

    return computeSuggestedMetrics({
      appleHealthConnected: healthDays.length > 0 && !!healthLastSyncAt,
      whoopConnected: whoopStatus === 'ready' && whoopDay != null,
      whoopCsvImported: whoopCsvImported ?? true, // null → treat as imported (no suggestion) until cache hydrates
      hasNutritionToday: nutritionToday != null,
      waterLoggedToday: !!nutritionToday && (nutritionToday.water_ml ?? 0) > 0,
      caloriesLoggedToday: !!nutritionToday && (nutritionToday.calories_kcal ?? 0) > 0,
      proteinLoggedToday: !!nutritionToday && (nutritionToday.protein_g ?? 0) > 0,
      sessionsLast7d: recent.length,
      sessionsLast7dWithRpe: withRpe.length,
      grapplingSessionsLast7d: grappling.length,
      grapplingSessionsWithRoundMarkers: grapplingRounds.length,
      hasWeightLogged: false,
    });
  }, [healthDays.length, healthLastSyncAt, whoopStatus, whoopDay, nutritionToday, sessions, whoopCsvImported]);

  if (suggestions.length === 0) return null;

  return (
    <View style={styles.card}>
      <Text style={styles.title}>Could improve your Coach analysis</Text>
      <Text style={styles.sub}>Optional. Only shows when it would unlock something real.</Text>
      {suggestions.map((s) => (
        <Pressable
          key={s.id}
          onPress={() => { if (s.route) router.push(s.route as any); }}
          style={styles.row}
          accessibilityRole="button"
          accessibilityLabel={`Suggestion: ${s.title}`}>
          <Text style={styles.rowTitle}>{s.title}</Text>
          <Text style={styles.rowWhy}>{s.why}</Text>
          <Text style={styles.rowUnlocks}>Unlocks: {s.unlocks}</Text>
          <Text style={styles.rowEffort}>Effort: {s.effort}</Text>
        </Pressable>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    padding: 14,
    borderRadius: 12,
    backgroundColor: 'rgba(212,225,87,0.06)',
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.18)',
    gap: 8,
  },
  title: { fontSize: 14, fontWeight: '700', color: '#d4e157' },
  sub: { fontSize: 11, opacity: 0.55 },
  row: {
    paddingVertical: 8,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: 'rgba(255,255,255,0.08)',
    gap: 2,
  },
  rowTitle: { fontSize: 13, fontWeight: '600' },
  rowWhy: { fontSize: 12, opacity: 0.75, lineHeight: 16 },
  rowUnlocks: { fontSize: 11, opacity: 0.6 },
  rowEffort: { fontSize: 11, opacity: 0.5 },
});
