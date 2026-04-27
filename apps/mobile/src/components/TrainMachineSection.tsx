/**
 * TrainMachineSection — the one place that owns machine capture.
 *
 * Product ownership decision: machine capture belongs in Train
 * (part of session execution), NOT Health (which owns Apple Health
 * / WHOOP / enrichment / source status).
 *
 * Behavior:
 *   - BLE native module NOT linked (Build 8 and older): render
 *     nothing. Manual-entry HIIT still works; no dead affordance.
 *   - Linked, no device paired: render a compact chip "Pair HR
 *     strap / machine for live HR + watts". Tap to expand.
 *   - Expanded: mount the full FTMSMachineCard (Scan / Connect /
 *     Start live read / live HR/power display).
 *   - Live stream flowing: section stays expanded for control, but
 *     the LiveHrPill above shows the actual numbers so the user
 *     can see them even if they collapse.
 */
import { useCallback, useEffect, useState } from 'react';
import { StyleSheet, Pressable } from 'react-native';
import { Text, View } from '@/components/Themed';
import { FTMSMachineCard } from './IntegrationCards';
import { SafeErrorBoundary } from './SafeErrorBoundary';
import { getBleMachineState, getLastLiveSample } from '../services/ble-connect';

export function TrainMachineSection() {
  const [moduleLinked, setModuleLinked] = useState<boolean | null>(null);
  // Auto-expanded by default on Build 9 so the Scan button is
  // immediately visible. Users previously saw just a chip and didn't
  // realize it was tappable.
  const [open, setOpen] = useState(true);
  const [state, setState] = useState(() => {
    try { return getBleMachineState(); } catch { return null; }
  });

  useEffect(() => {
    let cancelled = false;
    const poll = () => {
      try {
        const s = getBleMachineState();
        if (!cancelled) {
          setState(s);
          setModuleLinked(!!s?.moduleLinked);
        }
      } catch {
        if (!cancelled) setModuleLinked(false);
      }
    };
    poll();
    const t = setInterval(poll, 2500);
    return () => { cancelled = true; clearInterval(t); };
  }, []);

  // Auto-open when a device is connected or streaming — the user
  // almost certainly wants the controls visible at that point.
  useEffect(() => {
    if (!state) return;
    if (state.status === 'connected' || state.status === 'receiving_data' || state.status === 'scanning') {
      setOpen(true);
    }
  }, [state?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  const last = (() => { try { return getLastLiveSample(); } catch { return null; } })();
  const freshStream = last?.bpmAtMs != null && Date.now() - last.bpmAtMs < 6_000;

  const toggle = useCallback(() => setOpen((v) => !v), []);

  if (moduleLinked == null) return null; // still probing
  // On builds without the BLE native module linked, show a short
  // honest status card instead of hiding silently. Keeps the user
  // informed about why the pair/scan flow isn't available yet.
  if (moduleLinked === false) {
    return (
      <View style={styles.notLinkedCard}>
        <Text style={styles.notLinkedTitle}>Bluetooth machine capture</Text>
        <Text style={styles.notLinkedBody}>
          {'Install the latest TestFlight build \u2014 this build doesn\u2019t have the native BLE module compiled in. Manual HIIT logging still works and flows into Recent Days + Coach immediately.'}
        </Text>
      </View>
    );
  }

  const paired = state?.status === 'connected' || state?.status === 'receiving_data';
  const headerLabel = freshStream
    ? 'Machine streaming · tap for controls'
    : paired
      ? `Paired: ${state?.connectedDevice?.name ?? 'device'} · tap to start live read`
      : state?.status === 'scanning'
        ? 'Scanning for machines\u2026'
        : 'Pair HR strap or FTMS machine';
  const headerSub = paired
    ? 'Live HR + power will flow into this session\u2019s save'
    : 'Live HR + watts auto-fill the HIIT save when available';

  return (
    <View style={styles.wrap}>
      <Pressable onPress={toggle} style={styles.header} hitSlop={6}>
        <View style={styles.dot} />
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>{headerLabel}</Text>
          <Text style={styles.sub}>{headerSub}</Text>
        </View>
        <Text style={styles.arrow}>{open ? '▾' : '▸'}</Text>
      </Pressable>
      {open && (
        <View style={styles.body}>
          <SafeErrorBoundary label="Train machine capture">
            <FTMSMachineCard />
          </SafeErrorBoundary>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 8 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(212,225,87,0.06)',
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.18)',
  },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#d4e157' },
  title: { fontSize: 13, fontWeight: '700', color: '#d4e157' },
  sub: { fontSize: 11, opacity: 0.7 },
  arrow: { color: '#d4e157', fontSize: 16, fontWeight: '700' },
  body: { marginTop: 4 },
  notLinkedCard: {
    padding: 10,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
    gap: 4,
  },
  notLinkedTitle: { fontSize: 13, fontWeight: '700', opacity: 0.8 },
  notLinkedBody: { fontSize: 11, opacity: 0.6, lineHeight: 15 },
});
