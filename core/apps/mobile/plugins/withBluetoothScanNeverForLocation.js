const { withAndroidManifest } = require('@expo/config-plugins');

const BLUETOOTH_SCAN = 'android.permission.BLUETOOTH_SCAN';

function ensureBluetoothScanNeverForLocation(config) {
  return withAndroidManifest(config, (mod) => {
    const manifest = mod.modResults.manifest;
    const permissions = manifest['uses-permission'] ?? [];
    const scanPermission = permissions.find(
      (entry) => entry?.$?.['android:name'] === BLUETOOTH_SCAN,
    );

    if (scanPermission?.$) {
      scanPermission.$['android:usesPermissionFlags'] = 'neverForLocation';
    } else {
      permissions.push({
        $: {
          'android:name': BLUETOOTH_SCAN,
          'android:usesPermissionFlags': 'neverForLocation',
        },
      });
    }

    manifest['uses-permission'] = permissions;
    return mod;
  });
}

module.exports = ensureBluetoothScanNeverForLocation;
