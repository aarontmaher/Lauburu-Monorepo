/**
 * HealthConnectAvailabilityHint — Android-only banner that
 * surfaces above the Health Connect / Samsung Health primary
 * card when the system reports Health Connect is missing or
 * needs an update. Reads from
 * `services/health.android.ts` `HealthConnectService.
 * getAvailabilityDetail()` (added in commit 36581d9) which
 * returns a stable code mapping to the BLE SDK status enum.
 *
 * UI contract:
 *   - 'available'                 → render nothing (silent)
 *   - 'provider_update_required'  → "Update Health Connect" CTA
 *                                   that opens the Play Store
 *                                   listing
 *   - 'sdk_unavailable'           → "Install Health Connect" CTA
 *                                   that opens the Play Store
 *                                   listing
 *   - 'unknown'                   → render nothing (silent)
 *
 * Deep-link target: the Health Connect APK ID on Play.
 *
 * The component exits early on iOS so it's safe to mount
 * unconditionally from the Health tab.
 */
import { useEffect, useState } from 'react';
import { Platform, Pressable, Linking, StyleSheet } from 'react-native';
import { Text, View } from '@/components/Themed';

const HEALTH_CONNECT_PACKAGE_ID = 'com.google.android.apps.healthdata';
const HEALTH_CONNECT_PLAY_URL = `https://play.google.com/store/apps/details?id=${HEALTH_CONNECT_PACKAGE_ID}`;

type AvailabilityCode = 'available' | 'provider_update_required' | 'sdk_unavailable' | 'unknown';

export function HealthConnectAvailabilityHint() {
  const [code, setCode] = useState<AvailabilityCode | null>(null);

  useEffect(() => {
    if (Platform.OS !== 'android') return;
    let cancelled = false;
    (async () => {
      try {
        // Lazy-load so the iOS bundle doesn't pull the Android-only
        // health-connect path. Same pattern other Android-only
        // surfaces in this codebase use.
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const mod = require('../services/health.android');
        const Ctor = mod?.HealthConnectService;
        if (typeof Ctor !== 'function') return;
        const svc = new Ctor();
        if (typeof svc.getAvailabilityDetail !== 'function') return;
        const detail = await svc.getAvailabilityDetail();
        if (!cancelled) setCode(detail.code as AvailabilityCode);
      } catch {
        // Native module missing on this build — stay silent so the
        // Health tab doesn't show a false "install Health Connect"
        // hint when the issue is actually that we're in Expo Go or
        // a build without the native dependency linked.
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (Platform.OS !== 'android') return null;
  if (code == null) return null;
  if (code === 'available' || code === 'unknown') return null;

  const isUpdate = code === 'provider_update_required';
  const title = isUpdate ? 'Update Health Connect' : 'Install Health Connect';
  const body = isUpdate
    ? 'Your Health Connect version is too old to sync. Update it from the Play Store, then return and tap Connect.'
    : 'Health Connect is required to sync Android health data. Install it from the Play Store, then return and tap Connect.';

  const onPress = async () => {
    try {
      await Linking.openURL(HEALTH_CONNECT_PLAY_URL);
    } catch {
      // openURL failures (no Play Store on device — extremely rare)
      // fall through silently. The user can still navigate to the
      // Play Store manually.
    }
  };

  return (
    <View style={styles.card}>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.body}>{body}</Text>
      <Pressable onPress={onPress} style={styles.btn} accessibilityRole="button" accessibilityLabel={title}>
        <Text style={styles.btnText}>{isUpdate ? 'Open Play Store · Update' : 'Open Play Store · Install'}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    padding: 12,
    borderRadius: 12,
    backgroundColor: 'rgba(212,225,87,0.08)',
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.25)',
    gap: 6,
  },
  title: { fontSize: 14, fontWeight: '700', color: '#d4e157' },
  body: { fontSize: 12, lineHeight: 17, opacity: 0.85 },
  btn: {
    marginTop: 4,
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 8,
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(212,225,87,0.18)',
    borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.35)',
  },
  btnText: { fontSize: 12, fontWeight: '700', color: '#d4e157' },
});
