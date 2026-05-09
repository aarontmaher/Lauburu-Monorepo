import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(new URL('../..', import.meta.url).pathname);
const SOURCE = fs.readFileSync(
  path.join(ROOT, 'apps/mobile/src/components/HealthActionsPanel.tsx'),
  'utf8',
);

const connectStart = SOURCE.indexOf('const onConnectHealthConnect = useCallback');
assert.ok(connectStart > 0, 'onConnectHealthConnect exists');
const connectEnd = SOURCE.indexOf('setBusy(\'hc-connect\')', connectStart);
assert.ok(connectEnd > connectStart, 'connect auth gate appears before busy/connect flow');
const connectGate = SOURCE.slice(connectStart, connectEnd);

assert.ok(
  connectGate.includes("Alert.alert('Health Connect', 'Sign in to connect Health Connect.');"),
  'Health Connect connect flow must show sign-in-to-connect copy before native permission work',
);
assert.ok(
  SOURCE.includes("Alert.alert('Health Connect', 'Sign in to connect Health Connect.');"),
  'Health Connect sync flow must use same sign-in-to-connect copy',
);
assert.equal(
  SOURCE.includes("Alert.alert('Health Connect', 'Sign in first.');"),
  false,
  'Health Connect must not show generic Sign in first copy',
);

console.log('Health Connect auth gate copy contract test passed.');
