const { withAndroidManifest, withMainActivity } = require('@expo/config-plugins');

const HEALTH_PERMISSIONS = [
  'android.permission.health.READ_HEART_RATE',
  'android.permission.health.READ_HEART_RATE_VARIABILITY',
  'android.permission.health.READ_RESTING_HEART_RATE',
  'android.permission.health.READ_STEPS',
  'android.permission.health.READ_ACTIVE_CALORIES_BURNED',
  'android.permission.health.READ_SLEEP',
  'android.permission.health.READ_EXERCISE',
  'android.permission.health.READ_HEALTH_DATA_HISTORY',
];

const HEALTH_RATIONALE_ACTION = 'androidx.health.ACTION_SHOW_PERMISSIONS_RATIONALE';
const DELEGATE_IMPORT = 'import dev.matinzd.healthconnect.permissions.HealthConnectPermissionDelegate';
const DELEGATE_CALL = 'HealthConnectPermissionDelegate.setPermissionDelegate(this)';

function ensureHealthConnectManifest(config) {
  return withAndroidManifest(config, (mod) => {
    const manifest = mod.modResults.manifest;
    const permissions = manifest['uses-permission'] ?? [];
    const existingPermissions = new Set(
      permissions.map((entry) => entry?.$?.['android:name']).filter(Boolean),
    );

    for (const permission of HEALTH_PERMISSIONS) {
      if (!existingPermissions.has(permission)) {
        permissions.push({ $: { 'android:name': permission } });
      }
    }

    manifest['uses-permission'] = permissions;

    const application = manifest.application?.[0];
    const activities = application?.activity ?? [];
    const mainActivity = activities.find((activity) => {
      const name = activity?.$?.['android:name'];
      return name === '.MainActivity' || name === 'com.lauburu.grapplingmap.MainActivity';
    });
    if (!mainActivity) return mod;

    const intentFilters = mainActivity['intent-filter'] ?? [];
    const hasRationaleFilter = intentFilters.some((filter) =>
      (filter.action ?? []).some((action) => action?.$?.['android:name'] === HEALTH_RATIONALE_ACTION),
    );

    if (!hasRationaleFilter) {
      intentFilters.push({
        action: [{ $: { 'android:name': HEALTH_RATIONALE_ACTION } }],
      });
    }

    mainActivity['intent-filter'] = intentFilters;
    return mod;
  });
}

function ensureHealthConnectMainActivityDelegate(config) {
  return withMainActivity(config, (mod) => {
    let contents = mod.modResults.contents;

    if (!contents.includes(DELEGATE_IMPORT)) {
      const packageMatch = contents.match(/^package\s+[^\n]+\n/);
      if (packageMatch) {
        contents = contents.replace(packageMatch[0], `${packageMatch[0]}\n${DELEGATE_IMPORT}\n`);
      } else {
        contents = `${DELEGATE_IMPORT}\n${contents}`;
      }
    }

    if (!contents.includes(DELEGATE_CALL)) {
      contents = contents.replace(
        /super\.onCreate\(([^)]*)\)/,
        (match) => `${match}\n    ${DELEGATE_CALL}`,
      );
    }

    mod.modResults.contents = contents;
    return mod;
  });
}

function withAndroidHealthConnectPermissionDelegate(config) {
  config = ensureHealthConnectManifest(config);
  config = ensureHealthConnectMainActivityDelegate(config);
  return config;
}

module.exports = withAndroidHealthConnectPermissionDelegate;
