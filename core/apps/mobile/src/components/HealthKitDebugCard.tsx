/**
 * HealthKitDebugCard — on-device diagnostic for iOS HealthKit linking.
 *
 * Shows whether the native @kingstinct/react-native-healthkit module
 * actually loaded at runtime. If HealthKit symbols were stripped from
 * the build or Nitro failed to register the CoreModule, the card shows
 * the exact error so testers can screenshot it instead of guessing.
 *
 * Render conditionally: only on iOS, always visible to testers so
 * Aaron can confirm from the installed app which build is live.
 */
import { useCallback, useEffect, useState } from 'react';
import { Platform, Pressable, StyleSheet } from 'react-native';
import * as Application from 'expo-application';
import { Text, View } from '@/components/Themed';
import { getHealthKitNativeDebug, type HealthKitNativeDebug } from '../services/health.ios';

export function HealthKitDebugCard() {
  const [debug, setDebug] = useState<HealthKitNativeDebug | null>(null);
  const [expanded, setExpanded] = useState(false);

  const refresh = useCallback(() => {
    if (Platform.OS !== 'ios') return;
    try {
      setDebug(getHealthKitNativeDebug());
    } catch (e: any) {
      setDebug({
        platform: Platform.OS,
        moduleLoaded: false,
        moduleKeys: [],
        hasIsHealthDataAvailable: false,
        isHealthDataAvailableResult: null,
        isHealthDataAvailableRawError: null,
        requireError: e?.message ?? 'debug call failed',
        availabilityError: null,
        lastCallError: null,
        requestAuthorizationAttempted: false,
        lastAuthRequestAt: null,
        lastAuthRequestOk: null,
        lastAuthRequestReturn: null,
        lastAuthRequestError: null,
        lastCanaryReadCount: null,
        requestedReadTypes: [],
      });
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (Platform.OS !== 'ios') return null;

  const buildNumber =
    Application.nativeBuildVersion ?? '(unknown)';
  const appVersion =
    Application.nativeApplicationVersion ?? '(unknown)';

  const headline = debug
    ? debug.isHealthDataAvailableResult === true
      ? 'HealthKit ready'
      : debug.moduleLoaded
        ? 'Module loaded, HealthKit unavailable'
        : 'Native module failed to load'
    : 'checking…';

  const headlineColor =
    debug?.isHealthDataAvailableResult === true ? '#4ade80' : '#ff6b6b';

  return (
    <View style={styles.card}>
      <Pressable onPress={() => setExpanded((v) => !v)} style={styles.header}>
        <View>
          <Text style={styles.title}>HealthKit debug</Text>
          <Text style={[styles.headline, { color: headlineColor }]}>{headline}</Text>
          <Text style={styles.mono}>
            v{appVersion} · build {buildNumber}
          </Text>
        </View>
        <Text style={styles.toggle}>{expanded ? 'Hide' : 'Show'}</Text>
      </Pressable>

      {expanded && debug && (
        <View style={styles.body}>
          <Text style={styles.mono}>platform: {debug.platform}</Text>
          <Text style={styles.mono}>moduleLoaded: {String(debug.moduleLoaded)}</Text>
          <Text style={styles.mono}>
            hasIsHealthDataAvailable: {String(debug.hasIsHealthDataAvailable)}
          </Text>
          <Text style={styles.mono}>
            isHealthDataAvailableResult: {String(debug.isHealthDataAvailableResult)}
          </Text>
          {debug.requireError && (
            <Text style={[styles.mono, styles.red]}>requireError: {debug.requireError}</Text>
          )}
          {debug.availabilityError && (
            <Text style={[styles.mono, styles.red]}>availabilityError: {debug.availabilityError}</Text>
          )}
          {debug.lastCallError && (
            <Text style={[styles.mono, styles.amber]}>lastCallError: {debug.lastCallError}</Text>
          )}
          {debug.isHealthDataAvailableRawError && (
            <Text style={[styles.mono, styles.red]}>
              isHealthDataAvailableRawError: {debug.isHealthDataAvailableRawError}
            </Text>
          )}
          <Text style={styles.label}>Last auth request</Text>
          <Text style={styles.mono}>attempted: {String(debug.requestAuthorizationAttempted)}</Text>
          <Text style={styles.mono}>at: {debug.lastAuthRequestAt ?? '(never)'}</Text>
          <Text style={styles.mono}>ok: {String(debug.lastAuthRequestOk)}</Text>
          {debug.lastAuthRequestReturn && (
            <Text style={styles.mono}>return: {debug.lastAuthRequestReturn}</Text>
          )}
          {debug.lastAuthRequestError && (
            <Text style={[styles.mono, styles.red]}>
              error: {debug.lastAuthRequestError}
            </Text>
          )}
          <Text style={styles.mono}>canaryReadCount: {String(debug.lastCanaryReadCount)}</Text>
          {debug.requestedReadTypes.length > 0 && (
            <>
              <Text style={styles.label}>Requested read types</Text>
              <Text style={styles.mono}>
                {debug.requestedReadTypes.map((t) => t.replace('HKQuantityTypeIdentifier', 'Q.').replace('HKCategoryTypeIdentifier', 'C.')).join(', ')}
              </Text>
            </>
          )}
          <Text style={styles.label}>Module exports (first 20)</Text>
          <Text style={styles.mono}>
            {debug.moduleKeys.length > 0
              ? debug.moduleKeys.slice(0, 20).join(', ')
              : '(none)'}
          </Text>
          <Pressable style={styles.refreshBtn} onPress={refresh}>
            <Text style={styles.refreshText}>Refresh</Text>
          </Pressable>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    padding: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.04)',
    gap: 4,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  title: { fontSize: 13, fontWeight: '600', opacity: 0.6 },
  headline: { fontSize: 13, fontWeight: '600', marginTop: 2 },
  toggle: { fontSize: 12, color: '#d4e157' },
  body: { gap: 4, marginTop: 8 },
  label: {
    fontSize: 11,
    fontWeight: '600',
    opacity: 0.5,
    textTransform: 'uppercase',
    marginTop: 6,
  },
  mono: { fontSize: 11, opacity: 0.7, fontFamily: 'SpaceMono' },
  red: { color: '#ff6b6b', opacity: 1 },
  amber: { color: '#ffa500', opacity: 1 },
  refreshBtn: {
    alignSelf: 'flex-start',
    marginTop: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
    borderColor: '#d4e157',
    borderWidth: 1,
  },
  refreshText: { color: '#d4e157', fontSize: 12, fontWeight: '600' },
});
