/**
 * Samsung Health Data SDK direct integration service.
 *
 * Architecture:
 *   - The Samsung Health Data SDK is a native Android AAR that must be
 *     manually placed in android/app/src/main/libs/ and configured in
 *     build.gradle. It is NOT available via npm or Maven.
 *   - This service provides the JS-side interface. When the native
 *     module is present, it bridges to the SDK. When absent, it returns
 *     truthful "sdk_unavailable" states.
 *   - Developer mode gives READ-ONLY access without Samsung partnership.
 *     To enable: Samsung Health → Settings → About → tap version 10x →
 *     add your app package name.
 *   - Writing requires a Samsung Health Data SDK partnership application.
 *
 * Data types available in developer mode (read-only):
 *   - Steps, Daily step count trend
 *   - Exercise sessions
 *   - Sleep sessions + stages
 *   - Heart rate
 *   - Blood oxygen (SpO2)
 *   - Blood pressure, blood glucose, body temperature
 *   - Height, weight
 *   - Nutrition, water intake, caffeine intake
 *
 * Requirements:
 *   - Android 10+ (API 29+)
 *   - Samsung Health app 6.30.2+ installed
 *   - Developer mode enabled OR Samsung partnership approved
 *   - Physical device (emulator not supported)
 */

import { Platform } from 'react-native';

export type SamsungHealthDirectStatus =
  | 'not_checked'
  | 'connected'
  | 'sdk_unavailable'    // native module not installed
  | 'app_not_installed'  // Samsung Health app not on device
  | 'developer_mode_required' // SDK present but dev mode not enabled for this package
  | 'permission_required'
  | 'sync_needed'
  | 'partial'
  | 'stale'
  | 'error';

export interface SamsungHealthDirectState {
  status: SamsungHealthDirectStatus;
  sdkAvailable: boolean;
  samsungHealthAppInstalled: boolean;
  developerModeActive: boolean;
  lastSyncAt: string | null;
  domainsAvailable: string[];
  reason: string | null;
}

/**
 * Check if the Samsung Health Data SDK native module is available.
 * Returns false on iOS, in Expo Go, or when the native AAR is not
 * installed in the Android build.
 */
export function isSamsungHealthSdkAvailable(): boolean {
  if (Platform.OS !== 'android') return false;
  try {
    // The native module would be registered as 'SamsungHealthDataModule'
    // by our custom native Android code. If the module doesn't exist,
    // NativeModules.SamsungHealthDataModule will be undefined.
    const { NativeModules } = require('react-native');
    return NativeModules.SamsungHealthDataModule != null;
  } catch {
    return false;
  }
}

/**
 * Check the full Samsung Health direct connection state.
 * Pure JS — delegates to native module when available.
 */
export async function checkSamsungHealthDirectStatus(): Promise<SamsungHealthDirectState> {
  if (Platform.OS !== 'android') {
    return {
      status: 'sdk_unavailable',
      sdkAvailable: false,
      samsungHealthAppInstalled: false,
      developerModeActive: false,
      lastSyncAt: null,
      domainsAvailable: [],
      reason: 'Samsung Health direct is Android-only.',
    };
  }

  if (!isSamsungHealthSdkAvailable()) {
    return {
      status: 'sdk_unavailable',
      sdkAvailable: false,
      samsungHealthAppInstalled: false,
      developerModeActive: false,
      lastSyncAt: null,
      domainsAvailable: [],
      reason: 'Samsung Health Data SDK native module is not installed. To add it: (1) download the SDK AAR from developer.samsung.com/health/data, (2) place it in android/app/src/main/libs/, (3) add the Gradle dependency, (4) create the native bridge module, (5) rebuild the APK.',
    };
  }

  // When native module IS available, call into it for real status.
  try {
    const { NativeModules } = require('react-native');
    const mod = NativeModules.SamsungHealthDataModule;
    const result = await mod.checkStatus();
    return {
      status: result.status ?? 'error',
      sdkAvailable: true,
      samsungHealthAppInstalled: result.appInstalled ?? false,
      developerModeActive: result.developerMode ?? false,
      lastSyncAt: result.lastSyncAt ?? null,
      domainsAvailable: result.domainsAvailable ?? [],
      reason: result.reason ?? null,
    };
  } catch (e) {
    return {
      status: 'error',
      sdkAvailable: true,
      samsungHealthAppInstalled: false,
      developerModeActive: false,
      lastSyncAt: null,
      domainsAvailable: [],
      reason: e instanceof Error ? e.message : 'Native module call failed',
    };
  }
}

/**
 * Request Samsung Health permissions via the native module.
 * No-op when SDK is unavailable.
 */
export async function requestSamsungHealthPermissions(): Promise<boolean> {
  if (!isSamsungHealthSdkAvailable()) return false;
  try {
    const { NativeModules } = require('react-native');
    return await NativeModules.SamsungHealthDataModule.requestPermissions();
  } catch {
    return false;
  }
}

/**
 * Read Samsung Health data for a date range via the native module.
 * Returns raw records that can be normalized into the standard pipeline.
 */
export async function readSamsungHealthData(
  startDate: string,
  endDate: string,
): Promise<{
  steps: Array<{ date: string; count: number }>;
  sleep: Array<{ date: string; totalMinutes: number; stages?: any[] }>;
  heartRate: Array<{ date: string; bpm: number; timestamp: string }>;
  exercises: Array<{ date: string; type: string; durationMin: number; calories?: number }>;
  spo2: Array<{ date: string; value: number; timestamp: string }>;
  weight: Array<{ date: string; kg: number }>;
} | null> {
  if (!isSamsungHealthSdkAvailable()) return null;
  try {
    const { NativeModules } = require('react-native');
    return await NativeModules.SamsungHealthDataModule.readData(startDate, endDate);
  } catch {
    return null;
  }
}

/**
 * Setup instructions for adding Samsung Health Data SDK to the project.
 */
export const SAMSUNG_HEALTH_SETUP_INSTRUCTIONS = [
  '1. Download the Samsung Health Data SDK AAR from https://developer.samsung.com/health/data',
  '2. Place samsung-health-data-api-1.0.0.aar in android/app/src/main/libs/',
  '3. Add to android/app/build.gradle: implementation files("src/main/libs/samsung-health-data-api-1.0.0.aar")',
  '4. Add Gson dependency: implementation "com.google.code.gson:gson:2.13.1"',
  '5. Create the SamsungHealthDataModule native bridge (Kotlin) in android/app/src/main/java/...',
  '6. Register the native module in the ReactPackage',
  '7. Enable developer mode: Samsung Health → Settings → About → tap version 10x → add com.lauburu.grapplingmap',
  '8. Rebuild the APK: npx eas-cli build --profile preview --platform android',
];
