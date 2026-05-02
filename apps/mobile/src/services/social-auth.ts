/**
 * Social sign-in scaffolding for Apple + Google.
 *
 * NOT live until the next native build. The native modules
 * (`expo-apple-authentication`, `expo-auth-session`, `expo-crypto`)
 * are declared in `apps/mobile/package.json` but won't be linked into
 * the running app until a fresh `eas build` runs. Until then:
 *
 *   - `appleSignInAvailable()` returns false on the current Build 11
 *     bundle (lazy require throws → caught → false).
 *   - `googleSignInAvailable()` returns false unless
 *     EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID (or Android equivalent) is set
 *     AND the native auth-session module is linked.
 *
 * The auth-store callers (signInWithApple/signInWithGoogle) and the
 * AuthForm in settings.tsx therefore get safe `not_available` results
 * if invoked on the current shipped binary, and the UI hides the
 * buttons entirely when availability returns false.
 *
 * Wiring to Supabase uses signInWithIdToken which is the documented
 * cross-provider path: Apple emits an OIDC identity token, Google
 * AuthSession returns an idToken — both go to the same Supabase RPC.
 */

import { Platform } from 'react-native';
import { supabase } from '../store/supabase';

export type SocialProvider = 'apple' | 'google';

export interface SocialAuthResult {
  ok: boolean;
  provider: SocialProvider;
  /** Reason when ok=false. Stable strings safe to surface inline. */
  reason?:
    | 'not_available'        // native module not linked / platform unsupported
    | 'config_missing'       // env vars / client IDs not set
    | 'cancelled'            // user dismissed sheet
    | 'no_id_token'          // provider returned no usable token
    | 'supabase_failed'      // signInWithIdToken rejected
    | 'unknown_error';
  error?: string;
}

// ── Availability probes ─────────────────────────────────────────

export async function appleSignInAvailable(): Promise<boolean> {
  if (Platform.OS !== 'ios') return false;
  try {
    const mod = require('expo-apple-authentication');
    if (!mod || typeof mod.isAvailableAsync !== 'function') return false;
    return Boolean(await mod.isAvailableAsync());
  } catch { return false; }
}

export function googleSignInAvailable(): boolean {
  // Treat as available only if the native auth-session module is
  // linked AND at least one platform's client ID env var is set.
  try {
    require('expo-auth-session');
  } catch { return false; }
  const ios = process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID ?? '';
  const android = process.env.EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID ?? '';
  const web = process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID ?? '';
  if (Platform.OS === 'ios' && ios.length > 0) return true;
  if (Platform.OS === 'android' && android.length > 0) return true;
  // Web client ID covers the Expo dev-client / generic fallback.
  return web.length > 0;
}

// ── Apple ───────────────────────────────────────────────────────

export async function appleSignIn(): Promise<SocialAuthResult> {
  if (Platform.OS !== 'ios') return { ok: false, provider: 'apple', reason: 'not_available' };
  let mod: any;
  try { mod = require('expo-apple-authentication'); }
  catch { return { ok: false, provider: 'apple', reason: 'not_available' }; }
  if (!mod || typeof mod.signInAsync !== 'function') {
    return { ok: false, provider: 'apple', reason: 'not_available' };
  }
  try {
    // Apple requires a sha256-hashed nonce. The plain nonce is sent
    // to Supabase; Apple validates the hashed version. Both come from
    // expo-crypto.
    let crypto: any;
    try { crypto = require('expo-crypto'); }
    catch { return { ok: false, provider: 'apple', reason: 'not_available', error: 'expo-crypto not linked' }; }
    const rawNonce = String(Date.now()) + '-' + Math.random().toString(36).slice(2);
    const hashedNonce = await crypto.digestStringAsync(
      crypto.CryptoDigestAlgorithm.SHA256,
      rawNonce,
    );
    const credential = await mod.signInAsync({
      requestedScopes: [
        mod.AppleAuthenticationScope.FULL_NAME,
        mod.AppleAuthenticationScope.EMAIL,
      ],
      nonce: hashedNonce,
    });
    const idToken: string | null = credential?.identityToken ?? null;
    if (!idToken) return { ok: false, provider: 'apple', reason: 'no_id_token' };
    const { error } = await supabase.auth.signInWithIdToken({
      provider: 'apple',
      token: idToken,
      nonce: rawNonce,
    });
    if (error) return { ok: false, provider: 'apple', reason: 'supabase_failed', error: error.message };
    return { ok: true, provider: 'apple' };
  } catch (e: any) {
    if (e?.code === 'ERR_REQUEST_CANCELED' || /cancel/i.test(String(e?.message ?? ''))) {
      return { ok: false, provider: 'apple', reason: 'cancelled' };
    }
    return { ok: false, provider: 'apple', reason: 'unknown_error', error: e?.message };
  }
}

// ── Google ──────────────────────────────────────────────────────

export async function googleSignIn(): Promise<SocialAuthResult> {
  let authSession: any;
  let crypto: any;
  try { authSession = require('expo-auth-session/providers/google'); }
  catch { return { ok: false, provider: 'google', reason: 'not_available' }; }
  try { crypto = require('expo-crypto'); }
  catch { return { ok: false, provider: 'google', reason: 'not_available' }; }
  const ios = process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID ?? '';
  const android = process.env.EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID ?? '';
  const web = process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID ?? '';
  if (!ios && !android && !web) return { ok: false, provider: 'google', reason: 'config_missing' };
  try {
    // Note: the standard expo-auth-session/providers/google flow uses
    // the React-hook `useAuthRequest`. Calling it imperatively from a
    // service is unusual — when wiring this up in the next native
    // build, prefer the React-hook pattern from the AuthForm
    // component itself. This service-level fallback is kept thin and
    // returns `not_available` so the caller knows to use the hook
    // path. The hook-based flow lives in AuthForm.tsx (added by this
    // batch).
    return { ok: false, provider: 'google', reason: 'not_available', error: 'use_hook_flow_in_auth_form' };
  } catch (e: any) {
    return { ok: false, provider: 'google', reason: 'unknown_error', error: e?.message };
  }
}

/**
 * Auth-store helper: hand the id_token to Supabase. Used by the
 * AuthForm Google-button hook flow (see settings.tsx) since the React
 * hook pattern is the only ergonomic path through expo-auth-session.
 */
export async function exchangeGoogleIdToken(idToken: string): Promise<SocialAuthResult> {
  try {
    const { error } = await supabase.auth.signInWithIdToken({
      provider: 'google',
      token: idToken,
    });
    if (error) return { ok: false, provider: 'google', reason: 'supabase_failed', error: error.message };
    return { ok: true, provider: 'google' };
  } catch (e: any) {
    return { ok: false, provider: 'google', reason: 'unknown_error', error: e?.message };
  }
}
