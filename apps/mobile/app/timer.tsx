/**
 * Live session timer — full-screen modal overlay.
 *
 * Modes:
 * - Interval: work/rest countdown with round tracking
 * - Duration: simple countdown
 * - Stopwatch: count up
 *
 * Designed to be usable mid-workout on a phone near the bike/mat.
 * Large text, high contrast, minimal controls.
 *
 * Future: bike-connected mode adds live RPM/watts/calories alongside timer.
 */
import { useEffect, useRef } from 'react';
import { StyleSheet, Pressable, View as RNView } from 'react-native';
import { Text, View } from '@/components/Themed';
import { useRouter } from 'expo-router';
import { useTimerStore } from '../src/store/timer-store';
import { useTrainingStore } from '../src/store/training-store';
import { useHealthStore } from '../src/store/health-store';
import { useAuthStore } from '../src/store/auth-store';
import { CONDITIONING_SUBTYPE_LABELS, MODALITY_LABELS } from '@lauburu/shared';

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function formatElapsed(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

const PHASE_COLORS: Record<string, string> = {
  idle: '#666',
  work: '#e8ff47',
  rest: '#4ade80',
  running: '#e8ff47',
  paused: '#999',
  complete: '#4ade80',
};

const PHASE_LABELS: Record<string, string> = {
  idle: 'Ready',
  work: 'WORK',
  rest: 'REST',
  running: 'GO',
  paused: 'Paused',
  complete: 'Done',
};

export default function TimerScreen() {
  const router = useRouter();
  const config = useTimerStore((s) => s.config);
  const phase = useTimerStore((s) => s.phase);
  const remaining = useTimerStore((s) => s.remaining_s);
  const currentRound = useTimerStore((s) => s.currentRound);
  const elapsed = useTimerStore((s) => s.elapsed_s);
  const start = useTimerStore((s) => s.start);
  const pause = useTimerStore((s) => s.pause);
  const skip = useTimerStore((s) => s.skip);
  const tick = useTimerStore((s) => s.tick);
  const reset = useTimerStore((s) => s.reset);

  const addSession = useTrainingStore((s) => s.addSession);
  const syncData = useHealthStore((s) => s.syncData);
  const user = useAuthStore((s) => s.user);

  // Tick every second
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (phase === 'work' || phase === 'rest' || phase === 'running') {
      intervalRef.current = setInterval(tick, 1000);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [phase, tick]);

  if (!config) {
    return (
      <View style={styles.container}>
        <Text style={styles.noConfig}>No timer configured</Text>
        <Pressable style={styles.closeBtn} onPress={() => router.back()}>
          <Text style={styles.closeBtnText}>Close</Text>
        </Pressable>
      </View>
    );
  }

  const color = PHASE_COLORS[phase];
  const label = PHASE_LABELS[phase];
  const isActive = phase === 'work' || phase === 'rest' || phase === 'running';

  const handleComplete = () => {
    // Log the session
    const durationMin = Math.max(1, Math.round(elapsed / 60));
    addSession({
      date: new Date().toISOString().slice(0, 10),
      type: 'conditioning',
      intensity: durationMin >= 30 ? 'hard' : durationMin >= 15 ? 'moderate' : 'light',
      duration_min: durationMin,
      conditioning: {
        subtype: config.subtype,
        modality: config.modality,
        interval: config.mode === 'interval' ? {
          work_duration_s: config.work_s ?? 30,
          rest_duration_s: config.rest_s ?? 30,
          rounds: config.rounds ?? 1,
        } : undefined,
      },
    });
    if (user?.id) syncData(user.id);
    reset();
    router.back();
  };

  const handleDiscard = () => {
    reset();
    router.back();
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.subtypeLabel}>
          {CONDITIONING_SUBTYPE_LABELS[config.subtype]}
          {config.modality ? ` · ${MODALITY_LABELS[config.modality]}` : ''}
        </Text>
        {config.mode === 'interval' && (
          <Text style={styles.roundLabel}>
            Round {currentRound}/{config.rounds ?? 1}
          </Text>
        )}
      </View>

      {/* Phase indicator */}
      <Text style={[styles.phaseLabel, { color }]}>{label}</Text>

      {/* Main timer display */}
      {config.mode === 'stopwatch' ? (
        <Text style={[styles.timer, { color }]}>{formatElapsed(elapsed)}</Text>
      ) : (
        <Text style={[styles.timer, { color }]}>{formatTime(remaining)}</Text>
      )}

      {/* Elapsed (for interval/duration modes) */}
      {config.mode !== 'stopwatch' && (
        <Text style={styles.elapsed}>Total: {formatElapsed(elapsed)}</Text>
      )}

      {/* Controls */}
      <View style={styles.controls}>
        {phase === 'idle' && (
          <Pressable style={[styles.mainBtn, { backgroundColor: '#e8ff47' }]} onPress={start}>
            <Text style={styles.mainBtnText}>Start</Text>
          </Pressable>
        )}

        {isActive && (
          <View style={styles.controlRow}>
            <Pressable style={styles.secondaryBtn} onPress={pause}>
              <Text style={styles.secondaryBtnText}>Pause</Text>
            </Pressable>
            {config.mode === 'interval' && (
              <Pressable style={styles.secondaryBtn} onPress={skip}>
                <Text style={styles.secondaryBtnText}>Skip</Text>
              </Pressable>
            )}
          </View>
        )}

        {phase === 'paused' && (
          <View style={styles.controlRow}>
            <Pressable style={[styles.mainBtn, { backgroundColor: '#e8ff47' }]} onPress={start}>
              <Text style={styles.mainBtnText}>Resume</Text>
            </Pressable>
            <Pressable style={styles.secondaryBtn} onPress={handleComplete}>
              <Text style={styles.secondaryBtnText}>Finish</Text>
            </Pressable>
          </View>
        )}

        {phase === 'complete' && (
          <View style={styles.controlRow}>
            <Pressable style={[styles.mainBtn, { backgroundColor: '#4ade80' }]} onPress={handleComplete}>
              <Text style={styles.mainBtnText}>Save & Close</Text>
            </Pressable>
            <Pressable style={styles.secondaryBtn} onPress={handleDiscard}>
              <Text style={styles.secondaryBtnText}>Discard</Text>
            </Pressable>
          </View>
        )}
      </View>

      {/* Close button (always visible) */}
      {phase !== 'complete' && (
        <Pressable style={styles.closeBtn} onPress={handleDiscard}>
          <Text style={styles.closeBtnText}>
            {phase === 'idle' ? 'Cancel' : 'Discard & Close'}
          </Text>
        </Pressable>
      )}

      {/* Future: bike metrics would appear here */}
      {/* <BikeMetrics rpm={null} watts={null} calories={null} /> */}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0a',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 30,
  },
  noConfig: { fontSize: 18, opacity: 0.5 },

  header: { alignItems: 'center', gap: 4, marginBottom: 20 },
  subtypeLabel: { fontSize: 16, opacity: 0.6 },
  roundLabel: { fontSize: 20, fontWeight: '600', opacity: 0.8 },

  phaseLabel: { fontSize: 28, fontWeight: '800', letterSpacing: 4, marginBottom: 8 },

  timer: { fontSize: 96, fontWeight: '200', fontVariant: ['tabular-nums'] },

  elapsed: { fontSize: 16, opacity: 0.4, marginTop: 8 },

  controls: { marginTop: 40, alignItems: 'center', gap: 16 },
  controlRow: { flexDirection: 'row', gap: 16 },

  mainBtn: {
    paddingVertical: 18,
    paddingHorizontal: 48,
    borderRadius: 16,
    minWidth: 160,
    alignItems: 'center',
  },
  mainBtnText: { fontSize: 20, fontWeight: '700', color: '#0a0a0a' },

  secondaryBtn: {
    paddingVertical: 14,
    paddingHorizontal: 24,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#444',
    alignItems: 'center',
  },
  secondaryBtnText: { fontSize: 16, color: '#999' },

  closeBtn: { position: 'absolute', bottom: 50, padding: 12 },
  closeBtnText: { fontSize: 14, color: '#666' },
});
