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
