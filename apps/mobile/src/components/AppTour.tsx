/**
 * AppTour — full-screen modal overlay that walks new users through
 * every major app surface on first launch.
 *
 * Tour state is a global Zustand store so Settings replay can trigger
 * the same modal that _layout.tsx renders.
 *
 * Steps cover: Home, AI Coach, Health sources, Nutrition, Training,
 * HIIT, Map, Filters, Syllabus, Reference, Settings.
 *
 * Behavior:
 *   - Full-screen dimmed overlay with centered card
 *   - Step X of Y progress bar
 *   - Back / Next / Skip / Got it
 *   - Persistent dismiss via secureStorage
 *   - Replay from Settings
 *   - No fake feature claims
 */
import { useState, useEffect } from 'react';
import { StyleSheet, Pressable, Modal, Dimensions, ScrollView } from 'react-native';
import { Text, View } from '@/components/Themed';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { create } from 'zustand';
import { secureStorage } from '../store/secure-storage';

const TOUR_DISMISSED_KEY = 'app_tour_dismissed_v2';

/**
 * Mobile-specific tour steps — 11 steps covering every app surface.
 * This is the single source of truth for mobile tour content.
 * The shared SEED_TOUR (5 steps) is for the website only.
 */
const TOUR_STEPS = [
  {
    title: 'Welcome to Lauburu',
    body: 'Your grappling intelligence hub. This quick tour shows you what each section does.',
    detail: null,
  },
  {
    title: 'Home',
    body: 'Today\'s recovery snapshot, training guidance, and AI Coach insights — all in one place.',
    detail: 'Recovery data comes from WHOOP when connected. Seed data is used until a live sync completes.',
  },
  {
    title: 'AI Coach',
    body: 'Tap the floating coach button from any screen. Ask about training, recovery, nutrition, or HIIT.',
    detail: 'Answers use your real app data. The Coach will tell you when data is missing or stale rather than guessing.',
  },
  {
    title: 'Health Sources',
    body: 'WHOOP and Apple Health / Health Connect are tracked independently. Each shows its real connection status.',
    detail: 'WHOOP provides recovery/HRV/strain as one input. Apple Health / Health Connect provides sleep, HRV, steps, and dietary data. The app combines them into its own device-agnostic analysis — vendor scores are inputs, not the whole brain.',
  },
  {
    title: 'Nutrition',
    body: 'Log meals via manual entry, barcode scan, or AI photo estimate. Only confirmed entries count.',
    detail: 'Barcode scans use Open Food Facts. AI photo estimates require your review before entering totals. Apple Health dietary totals merge in when you grant nutrition read access.',
  },
  {
    title: 'Train',
    body: 'Log grappling sessions, conditioning, HIIT intervals, and steady-state cardio.',
    detail: 'HIIT sessions track per-set watts, HR, and calories. Named protocols are saved for quick recall.',
  },
  {
    title: 'HIIT Progress',
    body: 'The Coach can compare your latest HIIT session to previous ones — watts drop-off, HR drift, and set-by-set changes.',
    detail: 'Bluetooth machine capture (FTMS bikes, rowers, ski ergs) is available in Build 9+. Manual entry always captures the essentials regardless of device.',
  },
  {
    title: '3D Map',
    body: 'The interactive 3D mind map shows every position and how they connect. Tap nodes to explore move chains.',
    detail: 'Use the side handle to switch between All, My game, Learned, and Drilling views.',
  },
  {
    title: 'Belt Syllabus',
    body: 'Your belt roadmap maps requirements to real positions and techniques in the Reference system.',
    detail: 'Progress updates as you mark techniques drilling or learned.',
  },
  {
    title: 'Reference',
    body: 'The full technique tree — positions, roles, headings, and individual techniques.',
    detail: 'Mark items as drilling or learned to build your personal game map.',
  },
  {
    title: 'Settings',
    body: 'Configure coaching preferences, data consent, and subscription tier. Replay this tour anytime from Settings.',
    detail: null,
  },
];

// ---------------------------------------------------------------------------
// Global tour state (Zustand) — shared between _layout.tsx and settings.tsx
// ---------------------------------------------------------------------------

interface TourState {
  visible: boolean;
  ready: boolean;
  hydrate: () => Promise<void>;
  dismiss: () => Promise<void>;
  replay: () => Promise<void>;
}

export const useAppTourStore = create<TourState>((set) => ({
  visible: false,
  ready: false,

  hydrate: async () => {
    try {
      const stored = await secureStorage.getItem(TOUR_DISMISSED_KEY);
      set({ visible: stored !== 'true', ready: true });
    } catch {
      set({ visible: true, ready: true });
    }
  },

  dismiss: async () => {
    set({ visible: false });
    try { await secureStorage.setItem(TOUR_DISMISSED_KEY, 'true'); } catch {}
  },

  replay: async () => {
    try { await secureStorage.removeItem(TOUR_DISMISSED_KEY); } catch {}
    set({ visible: true });
  },
}));

// ---------------------------------------------------------------------------
// Tour component
// ---------------------------------------------------------------------------

interface AppTourProps {
  visible: boolean;
  onDismiss: () => void;
}

export function AppTour({ visible, onDismiss }: AppTourProps) {
  const [step, setStep] = useState(0);
  const insets = useSafeAreaInsets();

  useEffect(() => { if (visible) setStep(0); }, [visible]);

  if (!visible) return null;

  const current = TOUR_STEPS[step];
  const isFirst = step === 0;
  const isLast = step === TOUR_STEPS.length - 1;
  const { width: screenW, height: screenH } = Dimensions.get('window');
  const cardWidth = Math.min(screenW - 48, 380);
  // Leave room for safe areas + some breathing space
  const maxCardH = screenH - insets.top - insets.bottom - 80;

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      statusBarTranslucent>
      <View
        style={[
          styles.overlay,
          { paddingTop: insets.top + 24, paddingBottom: insets.bottom + 24 },
        ]}>
        <View style={[styles.card, { width: cardWidth, maxHeight: maxCardH }]}>
          {/* Progress — always visible, not scrollable */}
          <View style={styles.progressRow}>
            <Text style={styles.progressText}>
              {step + 1} of {TOUR_STEPS.length}
            </Text>
            <Pressable onPress={onDismiss} hitSlop={8}>
              <Text style={styles.skipText}>Skip tour</Text>
            </Pressable>
          </View>

          <View style={styles.progressBarBg}>
            <View
              style={[
                styles.progressBarFill,
                { width: `${((step + 1) / TOUR_STEPS.length) * 100}%` },
              ]}
            />
          </View>

          {/* Scrollable content — handles long detail text on small screens */}
          <ScrollView
            style={styles.scrollContent}
            showsVerticalScrollIndicator={false}
            bounces={false}>
            <Text style={styles.title}>{current.title}</Text>
            <Text style={styles.body}>{current.body}</Text>
            {current.detail && (
              <Text style={styles.detail}>{current.detail}</Text>
            )}
          </ScrollView>

          {/* Navigation — always visible, not scrollable */}
          <View style={styles.navRow}>
            <Pressable
              style={[styles.navBtn, isFirst && styles.navBtnDisabled]}
              disabled={isFirst}
              onPress={() => setStep((s) => Math.max(0, s - 1))}>
              <Text style={[styles.navBtnText, isFirst && styles.navBtnTextDisabled]}>
                Back
              </Text>
            </Pressable>

            {isLast ? (
              <Pressable style={styles.doneBtn} onPress={onDismiss}>
                <Text style={styles.doneBtnText}>Got it</Text>
              </Pressable>
            ) : (
              <Pressable
                style={styles.doneBtn}
                onPress={() => setStep((s) => Math.min(TOUR_STEPS.length - 1, s + 1))}>
                <Text style={styles.doneBtnText}>Next</Text>
              </Pressable>
            )}
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.75)',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
  },
  card: {
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 24,
  },
  scrollContent: {
    flexGrow: 0,
    flexShrink: 1,
  },
  progressRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  progressText: {
    color: '#888',
    fontSize: 13,
    fontWeight: '600',
  },
  skipText: {
    color: '#666',
    fontSize: 13,
  },
  progressBarBg: {
    height: 3,
    backgroundColor: '#333',
    borderRadius: 2,
    marginBottom: 20,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: 3,
    backgroundColor: '#d4e157',
    borderRadius: 2,
  },
  title: {
    fontSize: 20,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 10,
  },
  body: {
    fontSize: 15,
    color: '#ccc',
    lineHeight: 22,
    marginBottom: 8,
  },
  detail: {
    fontSize: 13,
    color: '#888',
    lineHeight: 19,
    marginBottom: 8,
  },
  navRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 20,
  },
  navBtn: {
    paddingVertical: 10,
    paddingHorizontal: 16,
  },
  navBtnDisabled: {
    opacity: 0.3,
  },
  navBtnText: {
    color: '#aaa',
    fontSize: 14,
    fontWeight: '600',
  },
  navBtnTextDisabled: {
    color: '#555',
  },
  doneBtn: {
    backgroundColor: '#d4e157',
    paddingVertical: 10,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  doneBtnText: {
    color: '#0a0a0a',
    fontSize: 14,
    fontWeight: '700',
  },
});
