/**
 * Auth state store — mirrors website AUTH_STATE / AUTH_USER pattern.
 * Preserves the existing Supabase session flow for email/password and
 * provider ID-token sign-in.
 */
import { create } from 'zustand';
import type { User, Session } from '@supabase/supabase-js';
import { supabase } from './supabase';

type AuthStatus = 'loading' | 'guest' | 'member';

/**
 * Email verification status for the current user.
 *   not_configured — Supabase project has email confirmation disabled;
 *                    account is usable immediately, no email is sent
 *   pending         — confirmation required; user must click email link
 *   verified        — email confirmed
 *   unknown         — no session / indeterminate
 */
export type EmailVerificationStatus = 'not_configured' | 'pending' | 'verified' | 'unknown';

interface AuthState {
  status: AuthStatus;
  user: User | null;
  session: Session | null;
  /** Verification status derived from Supabase user metadata. */
  emailVerificationStatus: EmailVerificationStatus;

  /** Restore persisted session on app launch. */
  initialize: () => Promise<void>;

  /** Email/password sign-up. Returns error string or null on success. */
  signUp: (email: string, password: string) => Promise<string | null>;

  /** Email/password sign-in. Returns error string or null on success. */
  signIn: (email: string, password: string) => Promise<string | null>;

  /**
   * Sign in with Apple. iOS-only. Returns error string or null on
   * success. Returns 'not_available' (as the error string) when the
   * native module isn't linked or platform isn't iOS — UI should
   * hide the button rather than calling this.
   */
  signInWithApple: () => Promise<string | null>;

  /**
   * Hand a Google OIDC id_token to Supabase. The token itself is
   * obtained via expo-auth-session's React-hook flow in the
   * sign-in component (so the AuthForm calls this AFTER the hook
   * resolves). Returns error string or null on success.
   */
  signInWithGoogleIdToken: (idToken: string) => Promise<string | null>;

  /**
   * Send a Supabase password-reset email. The provider emails the
   * user a recovery link — we never email or display the password
   * itself. Returns error string or null on success.
   */
  requestPasswordReset: (email: string) => Promise<string | null>;

  /** Sign out and clear state. */
  signOut: () => Promise<void>;

  /** Get current access token for API calls. */
  getAccessToken: () => Promise<string | null>;
}

/**
 * Derive verification status from a Supabase User.
 * If Supabase returns email_confirmed_at, the email is verified.
 * If the user has a session but no email_confirmed_at, email pending.
 * Our project currently has email confirmation DISABLED (auto-confirm),
 * so we surface this as "not_configured" when email_confirmed_at is
 * populated immediately on signup — meaning no email was actually sent.
 */
function deriveEmailVerificationStatus(user: User | null): EmailVerificationStatus {
  if (!user) return 'unknown';
  // If email_confirmed_at is set, it's either auto-confirmed (not_configured)
  // or user clicked the email link (verified). Distinguish by timing:
  // if confirmed within 5 seconds of created_at, treat as auto-confirm.
  const confirmed = user.email_confirmed_at;
  const created = user.created_at;
  if (!confirmed) return 'pending';
  if (!created) return 'verified';
  const diff = Math.abs(new Date(confirmed).getTime() - new Date(created).getTime());
  return diff < 5000 ? 'not_configured' : 'verified';
}

/**
 * Detect Supabase stale-session errors (Refresh Token Not Found,
 * invalid_grant, expired refresh, etc.). When the SDK can't refresh
 * the access token from the locally-stored refresh token, every
 * subsequent API call throws until local storage is cleared. QA on
 * simulator / TestFlight hits this when a server-side rotation
 * invalidates the local token; the app needs to recover instead of
 * looping on the error.
 */
function isStaleSessionError(err: unknown): boolean {
  if (!err) return false;
  const e = err as { message?: unknown; status?: unknown; code?: unknown };
  const msg = typeof e.message === 'string' ? e.message.toLowerCase() : String(err).toLowerCase();
  if (/refresh.token.not.found|invalid.refresh.token|invalid_grant|refresh_token_not_found|jwt.expired|token has expired/i.test(msg)) {
    return true;
  }
  if (e.status === 401 && /refresh|grant|jwt|token/i.test(msg)) return true;
  if (e.code === 'refresh_token_not_found' || e.code === 'invalid_grant') return true;
  return false;
}

/**
 * Clear ONLY the Supabase auth session from local storage. Does NOT
 * clear per-user data (clear-user-data.ts handles that on full
 * signOut). Safe to call when the session is already invalid — the
 * underlying signOut({ scope: 'local' }) is best-effort.
 */
async function clearStaleAuthSession(): Promise<void> {
  try {
    await supabase.auth.signOut({ scope: 'local' });
  } catch {
    // Already cleared or network unreachable; the local-scope variant
    // does not call the server, so we accept whatever state remains.
  }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  status: 'loading',
  user: null,
  session: null,
  emailVerificationStatus: 'unknown',

  initialize: async () => {
    try {
      const { data, error } = await supabase.auth.getSession();
      if (error) throw error;

      if (data.session?.user) {
        set({
          status: 'member',
          user: data.session.user,
          session: data.session,
          emailVerificationStatus: deriveEmailVerificationStatus(data.session.user),
        });
      } else {
        set({ status: 'guest', user: null, session: null, emailVerificationStatus: 'unknown' });
      }
    } catch (err) {
      if (isStaleSessionError(err)) {
        if (__DEV__) console.warn('[auth] initialize: stale refresh token; clearing local session and falling back to guest');
        await clearStaleAuthSession();
      }
      set({ status: 'guest', user: null, session: null, emailVerificationStatus: 'unknown' });
    }

    // Listen for future auth changes (token refresh, sign-in from another tab, etc.)
    supabase.auth.onAuthStateChange((event, session) => {
      // Token refresh failures land here as TOKEN_REFRESHED + null session,
      // or as SIGNED_OUT — either way we drop to guest. The TOKEN_REFRESHED
      // case with a non-null session is the happy refresh path.
      if (session?.user) {
        set({
          status: 'member',
          user: session.user,
          session,
          emailVerificationStatus: deriveEmailVerificationStatus(session.user),
        });
        return;
      }
      if (__DEV__ && event === 'TOKEN_REFRESHED' && !session) {
        console.warn('[auth] onAuthStateChange: TOKEN_REFRESHED with null session — refresh failed; dropping to guest');
      }
      set({ status: 'guest', user: null, session: null, emailVerificationStatus: 'unknown' });
    });
  },

  signUp: async (email, password) => {
    try {
      const { error } = await supabase.auth.signUp({
        email,
        password,
      });
      if (error) return error.message;
      return null;
    } catch (e: any) {
      return e?.message ?? 'Sign-up failed';
    }
  },

  signIn: async (email, password) => {
    try {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (error) return error.message;
      return null;
    } catch (e: any) {
      return e?.message ?? 'Sign-in failed';
    }
  },

  signInWithApple: async () => {
    // Lazy require keeps the OTA bundle from failing if the native
    // module isn't linked yet (current TestFlight Build 11 doesn't
    // ship expo-apple-authentication; Build 12 will).
    let mod: any;
    try { mod = require('../services/social-auth'); }
    catch { return 'Apple Sign-In not available on this build.'; }
    try {
      const result = await mod.appleSignIn();
      if (result.ok) return null;
      if (result.reason === 'cancelled') return null; // user cancel — no error UI
      if (result.reason === 'not_available') return 'Apple Sign-In needs the next app build.';
      if (result.reason === 'no_id_token') return 'Apple did not return a usable token.';
      return result.error ?? `Apple Sign-In failed (${result.reason ?? 'unknown'}).`;
    } catch (e: any) {
      return e?.message ?? 'Apple Sign-In failed';
    }
  },

  signInWithGoogleIdToken: async (idToken: string) => {
    if (!idToken || idToken.trim().length === 0) return 'Google did not return a usable token.';
    let mod: any;
    try { mod = require('../services/social-auth'); }
    catch { return 'Google Sign-In not available on this build.'; }
    try {
      const result = await mod.exchangeGoogleIdToken(idToken);
      if (result.ok) return null;
      return result.error ?? `Google Sign-In failed (${result.reason ?? 'unknown'}).`;
    } catch (e: any) {
      return e?.message ?? 'Google Sign-In failed';
    }
  },

  requestPasswordReset: async (email: string) => {
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email);
      if (error) return error.message;
      return null;
    } catch (e: any) {
      return e?.message ?? 'Could not send reset email.';
    }
  },

  signOut: async () => {
    try {
      await supabase.auth.signOut();
    } catch {
      // Force local state clear even if network call fails.
    }
    set({ status: 'guest', user: null, session: null, emailVerificationStatus: 'unknown' });

    // Clear all per-user local caches to prevent cross-user data leak.
    // Uses dynamic require to avoid circular imports at module load.
    try {
      const { clearAllUserData } = require('./clear-user-data');
      await clearAllUserData();
    } catch {
      // If the module isn't present, still sign out — just warn in dev.
    }
  },

  getAccessToken: async () => {
    // Prefer fresh session from store.
    const { session } = get();
    if (session?.access_token) return session.access_token;

    // Fallback: ask Supabase (handles refresh). On stale-refresh-token
    // errors, clear the local session and drop to guest so subsequent
    // calls don't loop on the same error.
    try {
      const { data, error } = await supabase.auth.getSession();
      if (error) throw error;
      return data.session?.access_token ?? null;
    } catch (err) {
      if (isStaleSessionError(err)) {
        if (__DEV__) console.warn('[auth] getAccessToken: stale refresh token; clearing local session');
        await clearStaleAuthSession();
        set({ status: 'guest', user: null, session: null, emailVerificationStatus: 'unknown' });
      }
      return null;
    }
  },
}));
