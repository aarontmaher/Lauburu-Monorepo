/**
 * Auth state store — mirrors website AUTH_STATE / AUTH_USER pattern.
 * Email/password auth only (no OAuth — matches website).
 */
import { create } from 'zustand';
import type { User, Session } from '@supabase/supabase-js';
import { supabase } from './supabase';

type AuthStatus = 'loading' | 'guest' | 'member';

interface AuthState {
  status: AuthStatus;
  user: User | null;
  session: Session | null;

  /** Restore persisted session on app launch. */
  initialize: () => Promise<void>;

  /** Email/password sign-up. Returns error string or null on success. */
  signUp: (email: string, password: string) => Promise<string | null>;

  /** Email/password sign-in. Returns error string or null on success. */
  signIn: (email: string, password: string) => Promise<string | null>;

  /** Sign out and clear state. */
  signOut: () => Promise<void>;

  /** Get current access token for API calls. */
  getAccessToken: () => Promise<string | null>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  status: 'loading',
  user: null,
  session: null,

  initialize: async () => {
    try {
      const { data, error } = await supabase.auth.getSession();
      if (error) throw error;

      if (data.session?.user) {
        set({
          status: 'member',
          user: data.session.user,
          session: data.session,
        });
      } else {
        set({ status: 'guest', user: null, session: null });
      }
    } catch {
      set({ status: 'guest', user: null, session: null });
    }

    // Listen for future auth changes (token refresh, sign-in from another tab, etc.)
    supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        set({ status: 'member', user: session.user, session });
      } else {
        set({ status: 'guest', user: null, session: null });
      }
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

  signOut: async () => {
    try {
      await supabase.auth.signOut();
    } catch {
      // Force local state clear even if network call fails.
    }
    set({ status: 'guest', user: null, session: null });
  },

  getAccessToken: async () => {
    // Prefer fresh session from store.
    const { session } = get();
    if (session?.access_token) return session.access_token;

    // Fallback: ask Supabase (handles refresh).
    try {
      const { data } = await supabase.auth.getSession();
      return data.session?.access_token ?? null;
    } catch {
      return null;
    }
  },
}));
