/**
 * Clear all per-user local caches on sign out / account switch.
 *
 * CRITICAL: prevents one user's data (WHOOP, nutrition, HIIT, health,
 * training, preferences, coaching cases, evidence) from being visible
 * to the next user on the same device.
 *
 * Does NOT clear:
 *   - shared tour dismissal (UX preference, not user data)
 *   - shared consent defaults
 *   - shared tier/subscription cache (re-resolved on next auth)
 *
 * The Supabase session itself is cleared by auth-store.signOut via
 * supabase.auth.signOut() which removes its own storage entries.
 */
import { secureStorage } from './secure-storage';

const PER_USER_KEYS = [
  // Nutrition
  'nutrition_today_v1',
  'nutrition_targets_v1',
  'barcode_favorites_v1',
  'nutrition_history_v1',
  'nutrition_evidence_v1',
  // HIIT
  'hiit_protocols_v1',
  'hiit_workouts_v1',
  // Health
  'health_sync_meta_v1',
  // Training
  'training_sessions_v1',
  // Coaching cases
  'coaching_cases_v1',
  'coaching_pending_v1',
  // Reference progress (per-user)
  'reference_progress_v1',
  // Preferences (per-user)
  'coaching_preferences_v1',
  // Feedback
  'feedback_store_v1',
  // Cronometer connection state (per-user)
  'cronometer_connection_v1',
  // Coach answer history
  'ai_coach_answers_v1',
];

export async function clearAllUserData(): Promise<void> {
  // 1. Purge persisted per-user secureStorage keys
  await Promise.all(
    PER_USER_KEYS.map((key) =>
      Promise.resolve(secureStorage.removeItem(key)).catch(() => {}),
    ),
  );

  // 2. Reset in-memory Zustand stores so the next signed-in user
  //    does not see residual state from the previous user.
  //    Dynamic requires to avoid circular imports at module load.
  try {
    const { useWhoopStore } = require('./whoop-store');
    useWhoopStore.setState({ status: 'idle', day: null, fetchedAt: null, error: null });
  } catch {}
  try {
    const { useNutritionStore } = require('./nutrition-store');
    useNutritionStore.setState({
      today: null, targets: null, favorites: [], historyDays: [],
      loading: false, error: null, hydrated: true,
    });
  } catch {}
  try {
    const { useNutritionEvidenceStore } = require('./nutrition-evidence-store');
    useNutritionEvidenceStore.setState({ items: [], hydrated: true });
  } catch {}
  try {
    const { useHIITProtocolsStore } = require('./hiit-protocols-store');
    useHIITProtocolsStore.setState({ protocols: [], pendingTimerLog: null, hydrated: true });
  } catch {}
  try {
    const { useHIITWorkoutStore } = require('./hiit-workout-store');
    useHIITWorkoutStore.setState({ workouts: [], hydrated: true });
  } catch {}
  try {
    const { useTrainingStore } = require('./training-store');
    useTrainingStore.setState({ sessions: [], hydrated: true });
  } catch {}
  try {
    const { useCoachingCasesStore } = require('./coaching-cases-store');
    useCoachingCasesStore.setState({ cases: [], pending: null, hydrated: true });
  } catch {}
  try {
    const { useHealthStore } = require('./health-store');
    const hs = useHealthStore.getState();
    // Health store exposes its own reset if available, otherwise wipe selectively
    if (typeof (hs as any).reset === 'function') (hs as any).reset();
  } catch {}
  try {
    const { useBacklogAnalysisStore } = require('./backlog-analysis-store');
    useBacklogAnalysisStore.getState().reset();
  } catch {}
  try {
    const { useSamsungHealthStore } = require('./samsung-health-store');
    useSamsungHealthStore.getState().reset();
  } catch {}
}
