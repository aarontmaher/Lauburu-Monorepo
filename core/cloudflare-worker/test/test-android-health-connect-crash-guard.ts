import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(new URL('../..', import.meta.url).pathname);

const healthAndroid = fs.readFileSync(
  path.join(ROOT, 'apps/mobile/src/services/health.android.ts'),
  'utf8',
);
const healthActions = fs.readFileSync(
  path.join(ROOT, 'apps/mobile/src/components/HealthActionsPanel.tsx'),
  'utf8',
);
const appJson = fs.readFileSync(path.join(ROOT, 'apps/mobile/app.json'), 'utf8');
const configPlugin = fs.readFileSync(
  path.join(ROOT, 'apps/mobile/plugins/withAndroidHealthConnectPermissionDelegate.js'),
  'utf8',
);

assert.ok(
  appJson.includes('./plugins/withAndroidHealthConnectPermissionDelegate'),
  'app.json must run the tracked Health Connect native config plugin',
);
for (const marker of [
  'HealthConnectPermissionDelegate.setPermissionDelegate(this)',
  'import dev.matinzd.healthconnect.permissions.HealthConnectPermissionDelegate',
  'withMainActivity',
  'withAndroidManifest',
]) {
  assert.ok(configPlugin.includes(marker), `config plugin missing native delegate marker: ${marker}`);
}

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
  assert.ok(appJson.includes(permission), `app.json missing ${permission}`);
  assert.ok(configPlugin.includes(permission), `config plugin missing ${permission}`);
}

assert.ok(
  configPlugin.includes('androidx.health.ACTION_SHOW_PERMISSIONS_RATIONALE'),
  'config plugin must expose the Health Connect permissions rationale action',
);

// Android 14+ — without the ViewPermissionUsageActivity activity-alias
// + HEALTH_PERMISSIONS category, Health Connect's "Apps & permissions"
// screen does NOT list the app even when the rationale intent-filter
// is present. Aaron's v20 installed-device evidence (2026-05-09): app
// opens HC but is not listed.
for (const marker of [
  'ViewPermissionUsageActivity',
  'android.permission.START_VIEW_PERMISSION_USAGE',
  'android.intent.action.VIEW_PERMISSION_USAGE',
  'android.intent.category.HEALTH_PERMISSIONS',
  "'activity-alias'",
]) {
  assert.ok(configPlugin.includes(marker), `config plugin missing Android 14+ HC registration marker: ${marker}`);
}

// The runtime probe surfaces the "did-not-register" signal so the
// UI can route to a retry-prompt instead of pretending the user
// just denied through a dialog.
for (const marker of [
  'didLastPermissionRequestFailToRegister',
  'lastPermissionRegistrationStatus',
  'did_not_register',
  'DID_NOT_REGISTER_MS',
]) {
  assert.ok(healthAndroid.includes(marker), `health.android.ts missing did-not-register probe: ${marker}`);
}

// HealthActionsPanel must wire the runtime probe through to a
// distinct status pill + a retry-labeled primary action so installed
// QA can recognise the failure mode without reading logs.
for (const marker of [
  'hcDidNotRegister',
  'HC_DID_NOT_REGISTER_STATUS',
  'Retry permission request',
  'Health Connect did not register the app',
]) {
  assert.ok(healthActions.includes(marker), `HealthActionsPanel missing did-not-register UI marker: ${marker}`);
}

// Connect button's primary path MUST call requestPermissions BEFORE
// any openHealthConnectSettings fallback — the v20 root-cause
// hypothesis is that an earlier refactor routed the first tap
// through the settings opener, which never registers the app with
// HC. Static check: the first occurrence of `requestPermissions(`
// in onConnectHealthConnect's body precedes the first
// `openHealthConnectSettings` reference within the same function.
{
  const fnStart = healthActions.indexOf('const onConnectHealthConnect = useCallback');
  assert.ok(fnStart > 0, 'onConnectHealthConnect handler must exist');
  const fnEnd = healthActions.indexOf('}, [requestPermissions, syncData', fnStart);
  assert.ok(fnEnd > fnStart, 'onConnectHealthConnect closing dependency array must exist');
  const fnBody = healthActions.slice(fnStart, fnEnd);
  const reqIdx = fnBody.indexOf('requestPermissions(');
  const openIdx = fnBody.indexOf('openHealthConnectSettings');
  assert.ok(reqIdx > 0, 'onConnectHealthConnect must call requestPermissions');
  if (openIdx >= 0) {
    assert.ok(reqIdx < openIdx, 'onConnectHealthConnect must call requestPermissions BEFORE any openHealthConnectSettings fallback');
  }
}

for (const marker of [
  'HealthConnectConnectError',
  'getAvailabilityDetail()',
  'initialize_failed',
  'permission_request_failed',
  'Could not open Health Connect permissions',
]) {
  assert.ok(healthAndroid.includes(marker), `health.android.ts missing crash guard marker: ${marker}`);
}

assert.ok(
  healthActions.includes('requestError'),
  'HealthActionsPanel should surface Health Connect request errors instead of only generic denial copy',
);

console.log('Android Health Connect crash guard checks OK');
