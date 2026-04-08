/**
 * Platform-agnostic health service factory.
 *
 * EXPO GO SAFETY:
 * metro.config.js blocks @kingstinct/react-native-healthkit and
 * react-native-health-connect from being bundled. This means
 * health.ios.ts and health.android.ts can safely require() them —
 * the require resolves to an empty module in Expo Go.
 *
 * The isExpoGo() check provides an additional runtime guard so
 * we never even try to instantiate native services in Expo Go.
 */
import { Platform } from 'react-native';
import Constants from 'expo-constants';
import type { IHealthService } from '@lauburu/shared';

let _instance: IHealthService | null = null;

/** True when running inside Expo Go */
export function isExpoGo(): boolean {
  return Constants.appOwnership === 'expo';
}

export function getHealthService(): IHealthService {
  if (_instance) return _instance;

  if (isExpoGo()) {
    _instance = STUB;
    return _instance;
  }

  try {
    if (Platform.OS === 'ios') {
      const { HealthKitService } = require('./health.ios');
      _instance = new HealthKitService();
    } else if (Platform.OS === 'android') {
      const { HealthConnectService } = require('./health.android');
      _instance = new HealthConnectService();
    } else {
      _instance = STUB;
    }
  } catch (e) {
    console.warn('Native health module unavailable:', e);
    _instance = STUB;
  }

  return _instance!;
}

const STUB: IHealthService = {
  isAvailable: async () => false,
  checkPermissions: async () => ({
    available: false,
    permissions: {
      heart_rate: 'unavailable' as const,
      resting_heart_rate: 'unavailable' as const,
      hrv: 'unavailable' as const,
      sleep: 'unavailable' as const,
      steps: 'unavailable' as const,
      active_calories: 'unavailable' as const,
      workouts: 'unavailable' as const,
    },
  }),
  requestPermissions: async () => ({
    available: false,
    permissions: {
      heart_rate: 'unavailable' as const,
      resting_heart_rate: 'unavailable' as const,
      hrv: 'unavailable' as const,
      sleep: 'unavailable' as const,
      steps: 'unavailable' as const,
      active_calories: 'unavailable' as const,
      workouts: 'unavailable' as const,
    },
  }),
  fetchSamples: async () => [],
  fetchWorkouts: async () => [],
  fetchSleep: async () => [],
};
