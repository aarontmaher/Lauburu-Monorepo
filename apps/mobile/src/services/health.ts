/**
 * Platform-agnostic health service factory.
 * Returns HealthKit on iOS, Health Connect on Android.
 *
 * Usage:
 *   import { getHealthService } from '../services/health';
 *   const service = getHealthService();
 *   const perms = await service.requestPermissions();
 */
import { Platform } from 'react-native';
import type { IHealthService } from '@lauburu/shared';

let _instance: IHealthService | null = null;

export function getHealthService(): IHealthService {
  if (_instance) return _instance;

  if (Platform.OS === 'ios') {
    // Dynamic import to avoid loading HealthKit module on Android
    const { HealthKitService } = require('./health.ios');
    _instance = new HealthKitService();
  } else if (Platform.OS === 'android') {
    const { HealthConnectService } = require('./health.android');
    _instance = new HealthConnectService();
  } else {
    // Web/other — stub that reports unavailable
    _instance = createUnavailableStub();
  }

  return _instance!;
}

function createUnavailableStub(): IHealthService {
  const unavailable: Record<string, 'unavailable'> = {
    heart_rate: 'unavailable',
    resting_heart_rate: 'unavailable',
    hrv: 'unavailable',
    sleep: 'unavailable',
    steps: 'unavailable',
    active_calories: 'unavailable',
    workouts: 'unavailable',
  };
  return {
    isAvailable: async () => false,
    checkPermissions: async () => ({
      available: false,
      permissions: unavailable as any,
    }),
    requestPermissions: async () => ({
      available: false,
      permissions: unavailable as any,
    }),
    fetchSamples: async () => [],
    fetchWorkouts: async () => [],
    fetchSleep: async () => [],
  };
}
