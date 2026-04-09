/**
 * Live session timer — full-screen modal with phase-colored backgrounds.
 *
 * WORK = green background (go hard)
 * REST = red background (stop/recover)
 * Haptic feedback on every phase transition.
 * HR zone placeholder for future live data.
 */
import { useEffect, useRef, useCallback } from 'react';
import { StyleSheet, Pressable, View as RNView } from 'react-native';
import { Text, View } from '@/components/Themed';
import { useRouter } from 'expo-router';
import { useTimerStore } from '../src/store/timer-store';
import { useTrainingStore } from '../src/store/training-store';
import { useHealthStore } from '../src/store/health-store';
import { useAuthStore } from '../src/store/auth-store';
import { CONDITIONING_SUBTYPE_LABELS, MODALITY_LABELS, HR_ZONES, getHRZone, REST_COLOR } from '@lauburu/shared';
import type { HRZone } from '@lauburu/shared';

// Haptic feedback — lazy loaded, gracefully degraded
function triggerHaptic(type: 'transition' | 'complete') {
  try {
    const Haptics = require('expo-haptics');
    if (type === 'complete') {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    } else {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
    }
  } catch {
    // Haptics not available — silent fallback
  }
}

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

// Full-screen background colors per phase
const BG_COLORS: Record<string, string> = {
  idle: '#0a0a0a',
  work: '#1a3a1a',     // dark green
  rest: '#3a1a1a',     // dark red
  running: '#1a2a1a',  // subtle green
  paused: '#1a1a1a',
  complete: '#0a0a0a',
};

const ACCENT_COLORS: Record<string, string> = {
  idle: '#666',
  work: '#4ade80',     // bright green
  rest: '#ff6b6b',     // bright red
  running: '#4ade80',
  paused: '#999',
  complete: '#4ade80',
};

const PHASE_LABELS: Record<string, string> = {
  idle: 'READY',
  work: 'WORK',
  rest: 'REST',
  running: 'GO',
  paused: 'PAUSED',
  complete: 'DONE',
};

/**
 * HR zone display — shows colored zone badge when HR is available.
 * When HR is null (no HR monitor connected), shows
 * a placeholder with zone color strip for context.
 */
function HRZoneDisplay({ currentHR }: { currentHR: number | null }) {
  if (currentHR != null) {
    const zone = getHRZone(currentHR);
    return (
      <RNView style={[styles.hrZone, { borderColor: zone.color + '40' }]}>
        <Text style={styles.hrZoneLabel}>Zone {zone.zone}</Text>
        <Text style={[styles.hrZoneValue, { color: zone.color }]}>
          {Math.round(currentHR)} bpm
        </Text>
        <Text style={[styles.hrZoneNote, { color: zone.color }]}>{zone.label}</Text>
      </RNView>
    );
  }

  // No HR data — show zone strip as reference
  return (
    <RNView style={styles.hrZone}>
      <RNView style={styles.zoneStrip}>
        {HR_ZONES.map((z) => (
          <RNView key={z.zone} style={[styles.zoneDot, { backgroundColor: z.color }]} />
        ))}
      </RNView>
      <Text style={styles.hrZoneNote}>Heart rate monitor for live zones</Text>
    </RNView>
  );
}

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

  // Haptic on phase change
  const prevPhase = useRef(phase);
  useEffect(() => {
    if (prevPhase.current !== phase) {
      if (phase === 'complete') {
        triggerHaptic('complete');
      } else if (phase === 'work' || phase === 'rest') {
        triggerHaptic('transition');
      }
      prevPhase.current = phase;
    }
  }, [phase]);

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
      <RNView style={[styles.container, { backgroundColor: '#0a0a0a' }]}>
        <Text style={{ fontSize: 18, color: '#666' }}>No timer configured</Text>
        <Pressable style={styles.closeBtn} onPress={() => router.back()}>
          <Text style={styles.closeBtnText}>Close</Text>
        </Pressable>
      </RNView>
    );
  }

  const bg = BG_COLORS[phase] ?? '#0a0a0a';
  const accent = ACCENT_COLORS[phase] ?? '#666';
  const label = PHASE_LABELS[phase] ?? '';
  const isActive = phase === 'work' || phase === 'rest' || phase === 'running';

  const handleComplete = () => {
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
    <RNView style={[styles.container, { backgroundColor: bg }]}>
      {/* Header */}
      <RNView style={styles.header}>
        <Text style={[styles.subtypeLabel, { color: '#fff', opacity: 0.5 }]}>
          {CONDITIONING_SUBTYPE_LABELS[config.subtype]}
          {config.modality ? ` · ${MODALITY_LABELS[config.modality]}` : ''}
        </Text>
        {config.mode === 'interval' && (
          <Text style={[styles.roundLabel, { color: accent }]}>
            Round {currentRound}/{config.rounds ?? 1}
          </Text>
        )}
      </RNView>

      {/* Phase label */}
      <Text style={[styles.phaseLabel, { color: accent }]}>{label}</Text>

      {/* Main timer */}
      {config.mode === 'stopwatch' ? (
        <Text style={[styles.timer, { color: '#fff' }]}>{formatElapsed(elapsed)}</Text>
      ) : (
        <Text style={[styles.timer, { color: '#fff' }]}>{formatTime(remaining)}</Text>
      )}

      {/* Elapsed */}
      {config.mode !== 'stopwatch' && (
        <Text style={styles.elapsed}>Total: {formatElapsed(elapsed)}</Text>
      )}

      {/* HR zone — shows live zone when HR available, placeholder otherwise */}
      {isActive && phase !== 'rest' && (
        <HRZoneDisplay currentHR={null} />
      )}
      {phase === 'rest' && (
        <RNView style={[styles.hrZone, { borderColor: REST_COLOR + '30' }]}>
          <Text style={[styles.hrZoneValue, { color: REST_COLOR }]}>REST</Text>
          <Text style={styles.hrZoneNote}>Recover</Text>
        </RNView>
      )}

      {/* Controls */}
      <RNView style={styles.controls}>
        {phase === 'idle' && (
          <Pressable style={[styles.mainBtn, { backgroundColor: '#4ade80' }]} onPress={start}>
            <Text style={styles.mainBtnText}>Start</Text>
          </Pressable>
        )}

        {isActive && (
          <RNView style={styles.controlRow}>
            <Pressable style={styles.secondaryBtn} onPress={pause}>
              <Text style={styles.secondaryBtnText}>Pause</Text>
            </Pressable>
            {config.mode === 'interval' && (
              <Pressable style={styles.secondaryBtn} onPress={skip}>
                <Text style={styles.secondaryBtnText}>Skip</Text>
              </Pressable>
            )}
          </RNView>
        )}

        {phase === 'paused' && (
          <RNView style={styles.controlRow}>
            <Pressable style={[styles.mainBtn, { backgroundColor: '#4ade80' }]} onPress={start}>
              <Text style={styles.mainBtnText}>Resume</Text>
            </Pressable>
            <Pressable style={styles.secondaryBtn} onPress={handleComplete}>
              <Text style={styles.secondaryBtnText}>Finish</Text>
            </Pressable>
          </RNView>
        )}

        {phase === 'complete' && (
          <RNView style={styles.completeSection}>
            <RNView style={styles.summaryCard}>
              <Text style={styles.summaryTitle}>Session Complete</Text>
              <Text style={styles.summaryLine}>
                {CONDITIONING_SUBTYPE_LABELS[config.subtype]}
                {config.modality ? ` · ${MODALITY_LABELS[config.modality]}` : ''}
              </Text>
              <Text style={styles.summaryLine}>
                {formatElapsed(elapsed)} total
                {config.mode === 'interval' ? ` · ${config.rounds ?? 1} rounds` : ''}
              </Text>
            </RNView>
            <Pressable style={[styles.mainBtn, { backgroundColor: '#4ade80' }]} onPress={handleComplete}>
              <Text style={styles.mainBtnText}>Save & Close</Text>
            </Pressable>
            <Pressable style={styles.secondaryBtn} onPress={handleDiscard}>
              <Text style={styles.secondaryBtnText}>Discard</Text>
            </Pressable>
          </RNView>
        )}
      </RNView>

      {/* Close */}
      {phase !== 'complete' && (
        <Pressable style={styles.closeBtn} onPress={handleDiscard}>
          <Text style={styles.closeBtnText}>
            {phase === 'idle' ? 'Cancel' : 'Discard'}
          </Text>
        </Pressable>
      )}

      {/* Machine status */}
      <RNView style={styles.machineStatus}>
        <Text style={styles.machineText}>Phone timer</Text>
      </RNView>
    </RNView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 30,
  },

  header: { alignItems: 'center', gap: 4, marginBottom: 16 },
  subtypeLabel: { fontSize: 15 },
  roundLabel: { fontSize: 22, fontWeight: '700' },

  phaseLabel: { fontSize: 32, fontWeight: '900', letterSpacing: 6, marginBottom: 4 },

  timer: { fontSize: 88, fontWeight: '200', fontVariant: ['tabular-nums'] },

  elapsed: { fontSize: 15, color: '#999', opacity: 0.5, marginTop: 6 },

  // HR zone placeholder
  hrZone: {
    alignItems: 'center',
    marginTop: 16,
    paddingVertical: 8,
    paddingHorizontal: 20,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.05)',
    gap: 2,
  },
  hrZoneLabel: { fontSize: 10, color: '#999', textTransform: 'uppercase', letterSpacing: 1 },
  hrZoneValue: { fontSize: 20, fontWeight: '700', color: '#666' },
  hrZoneNote: { fontSize: 10, color: '#555' },
  zoneStrip: { flexDirection: 'row', gap: 4, marginBottom: 4 },
  zoneDot: { width: 16, height: 6, borderRadius: 3 },

  controls: { marginTop: 32, alignItems: 'center', gap: 16 },
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
    borderColor: 'rgba(255,255,255,0.2)',
    alignItems: 'center',
  },
  secondaryBtnText: { fontSize: 16, color: '#ccc' },

  closeBtn: { position: 'absolute', bottom: 50, padding: 12 },
  closeBtnText: { fontSize: 14, color: '#555' },

  completeSection: { alignItems: 'center', gap: 16, width: '100%' },
  summaryCard: {
    backgroundColor: 'rgba(74,222,128,0.08)',
    borderRadius: 12,
    padding: 20,
    width: '100%',
    alignItems: 'center',
    gap: 6,
  },
  summaryTitle: { fontSize: 20, fontWeight: '700', color: '#4ade80' },
  summaryLine: { fontSize: 14, color: '#999' },

  machineStatus: { position: 'absolute', top: 56, right: 20 },
  machineText: { fontSize: 11, color: '#444' },
});
