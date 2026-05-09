import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(__dirname, '../..');
const SETTINGS = fs.readFileSync(path.join(ROOT, 'apps/mobile/app/(tabs)/settings.tsx'), 'utf8');
const SOCIAL_AUTH = fs.readFileSync(path.join(ROOT, 'apps/mobile/src/services/social-auth.ts'), 'utf8');
const AUTH_STORE = fs.readFileSync(path.join(ROOT, 'apps/mobile/src/store/auth-store.ts'), 'utf8');
const APP_JSON = JSON.parse(fs.readFileSync(path.join(ROOT, 'apps/mobile/app.json'), 'utf8'));

assert.ok(
  /AppleAuthenticationButton/.test(SETTINGS),
  'iOS sign-in must render the native AppleAuthenticationButton when available',
);
assert.ok(
  /AppleAuthenticationButtonType\.SIGN_IN/.test(SETTINGS),
  'Apple button must use the platform sign-in button type',
);
assert.ok(
  /Google\.useIdTokenAuthRequest/.test(SETTINGS),
  'Google sign-in must use the Expo AuthSession ID-token hook',
);
assert.ok(
  /EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID/.test(SETTINGS) &&
    /EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID/.test(SETTINGS) &&
    /EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID/.test(SETTINGS),
  'Google sign-in must be configurable per mobile platform without hard-coded secrets',
);
assert.ok(
  /signInWithGoogleIdToken\(idToken\)/.test(SETTINGS),
  'Google id_token must be handed to the existing auth store flow',
);
assert.ok(
  /signInWithIdToken\(\{\s*provider: 'apple'/s.test(SOCIAL_AUTH),
  'Apple sign-in must exchange the Apple identity token through Supabase',
);
assert.ok(
  /signInWithIdToken\(\{\s*provider: 'google'/s.test(SOCIAL_AUTH),
  'Google sign-in must exchange the Google id_token through Supabase',
);
assert.ok(
  /Google did not return a usable token/.test(AUTH_STORE),
  'Auth store must reject empty Google id_tokens truthfully',
);
assert.ok(
  APP_JSON.expo.plugins.includes('expo-apple-authentication'),
  'Expo config must include the Apple authentication plugin',
);
assert.equal(
  APP_JSON.expo.ios?.usesAppleSignIn,
  true,
  'iOS config must declare Apple Sign-In usage',
);
assert.ok(
  APP_JSON.expo.ios?.entitlements?.['com.apple.developer.applesignin']?.includes('Default'),
  'iOS entitlements must include Sign in with Apple',
);

const tokenLoggingPattern = /console\.(log|warn|error)\([^)]*(idToken|identityToken|access_token|refresh_token)/i;
assert.equal(
  tokenLoggingPattern.test(`${SETTINGS}\n${SOCIAL_AUTH}\n${AUTH_STORE}`),
  false,
  'Social auth code must not log tokens or secrets',
);
