/**
 * Verifies the prebuild-rendered AndroidManifest.xml at
 * `apps/mobile/android/app/src/main/AndroidManifest.xml` contains
 * the Health Connect registration markers so a future EAS build
 * cannot ship without them. The manifest is gitignored, so this
 * test is permissive when the file is absent — it only asserts
 * that, when present, the manifest reflects the patched config
 * plugin output.
 *
 * Anti-rule: this test does NOT trigger `expo prebuild` itself
 * (the developer or CI must run it before this test runs). The
 * static plugin-source test in
 * `test-android-health-connect-crash-guard.ts` covers the case
 * where prebuild has not yet been run.
 */

import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(new URL('../..', import.meta.url).pathname);
const MANIFEST = path.join(ROOT, 'apps/mobile/android/app/src/main/AndroidManifest.xml');
const MAIN_ACTIVITY = path.join(ROOT, 'apps/mobile/android/app/src/main/java/com/lauburu/grapplingmap/MainActivity.kt');

if (!fs.existsSync(MANIFEST)) {
  console.log('AndroidManifest.xml not present — skipping prebuild manifest check (run `npx expo prebuild --platform android --no-install --clean` to regenerate).');
  process.exit(0);
}

const manifest = fs.readFileSync(MANIFEST, 'utf8');

// Required Health Connect permissions — exactly the eight the
// config plugin declares.
for (const permission of [
  'android.permission.health.READ_HEART_RATE',
  'android.permission.health.READ_HEART_RATE_VARIABILITY',
  'android.permission.health.READ_RESTING_HEART_RATE',
  'android.permission.health.READ_STEPS',
  'android.permission.health.READ_ACTIVE_CALORIES_BURNED',
  'android.permission.health.READ_SLEEP',
  'android.permission.health.READ_EXERCISE',
  'android.permission.health.READ_HEALTH_DATA_HISTORY',
]) {
  assert.ok(manifest.includes(permission), `manifest missing permission: ${permission}`);
}

// Rationale intent-filter for Android 13- compatibility.
assert.ok(
  manifest.includes('androidx.health.ACTION_SHOW_PERMISSIONS_RATIONALE'),
  'manifest must declare the Health Connect rationale action',
);

// Android 14+ activity-alias — the actual fix.
for (const marker of [
  '<activity-alias android:name=".ViewPermissionUsageActivity"',
  'android:permission="android.permission.START_VIEW_PERMISSION_USAGE"',
  'android:targetActivity=".MainActivity"',
  'android.intent.action.VIEW_PERMISSION_USAGE',
  'android.intent.category.HEALTH_PERMISSIONS',
]) {
  assert.ok(manifest.includes(marker), `manifest missing Android 14+ HC registration marker: ${marker}`);
}

// MainActivity native delegate hookup so requestPermission resolves
// against the correct ActivityResultLauncher.
if (fs.existsSync(MAIN_ACTIVITY)) {
  const mainActivity = fs.readFileSync(MAIN_ACTIVITY, 'utf8');
  for (const marker of [
    'import dev.matinzd.healthconnect.permissions.HealthConnectPermissionDelegate',
    'HealthConnectPermissionDelegate.setPermissionDelegate(this)',
  ]) {
    assert.ok(mainActivity.includes(marker), `MainActivity.kt missing native delegate marker: ${marker}`);
  }
}

console.log('Prebuilt AndroidManifest.xml + MainActivity.kt contain Health Connect registration markers.');
