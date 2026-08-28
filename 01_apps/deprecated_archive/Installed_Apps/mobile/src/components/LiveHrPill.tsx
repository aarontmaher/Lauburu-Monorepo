/**
 * LiveHrPill — tiny HR/power chip that self-subscribes to the shared
 * BLE broadcast stream in ble-connect.ts.
 *
 * Renders nothing until a live sample arrives, and auto-hides 6s
 * after the last sample stops flowing. Safe to drop into any screen
 * — does not start its own BLE session.
 */
import { useEffect, useState } from 'react';
import { StyleSheet } from 'react-native';
import { Text, View } from '@/components/Themed';
import { subscribeHr, subscribeFtms, getLastLiveSample } from '../services/ble-connect';

const STALE_MS = 6_000;

export function LiveHrPill() {
  const [bpm, setBpm] = useState<number | null>(null);
  const [power, setPower] = useState<number | null>(null);
  const [lastAt, setLastAt] = useState<number | null>(null);

  useEffect(() => {
    // Hydrate from last-known sample on mount so we don't flicker from
    // empty → populated if the user just navigated here mid-session.
    try {
      const last = getLastLiveSample();
      if (last.bpm != null) setBpm(last.bpm);
      if (last.bpmAtMs != null) setLastAt(last.bpmAtMs);
      if (last.ftms?.instantaneousPowerW != null) setPower(last.ftms.instantaneousPowerW);
    } catch { /* non-fatal */ }

    const unsubHr = subscribeHr((b, at) => { setBpm(b); setLastAt(at); });
    const unsubFtms = subscribeFtms((s) => {
      if (typeof s.instantaneousPowerW === 'number') setPower(s.instantaneousPowerW);
      if (typeof s.heartRateBpm === 'number') { setBpm(s.heartRateBpm); setLastAt(s.atEpochMs); }
    });
    return () => { unsubHr(); unsubFtms(); };
  }, []);

  // Auto-hide when last HR sample is older than STALE_MS.
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (lastAt == null) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [lastAt]);

  const fresh = lastAt != null && now - lastAt < STALE_MS;
  if (!fresh || bpm == null) return null;

  return (
    <View style={styles.pill}>
      <Text style={styles.hr}>♥ {bpm} bpm</Text>
      {power != null && <Text style={styles.power}>⚡ {power} W</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(74,222,128,0.08)',
    borderWidth: 1,
    borderColor: 'rgba(74,222,128,0.25)',
  },
  hr: { color: '#4ade80', fontSize: 13, fontWeight: '700' },
  power: { color: '#d4e157', fontSize: 13, fontWeight: '700' },
});
