/**
 * Supabase client factory.
 * The mobile app passes in a storage adapter (expo-secure-store);
 * the web can pass localStorage. This keeps the shared layer platform-agnostic.
 */
import { SUPABASE_URL, SUPABASE_ANON_KEY } from '../constants/config';

export interface StorageAdapter {
  getItem: (key: string) => Promise<string | null> | string | null;
  setItem: (key: string, value: string) => Promise<void> | void;
  removeItem: (key: string) => Promise<void> | void;
}

export interface SupabaseClientOptions {
  storage: StorageAdapter;
}

/**
 * Create a configured Supabase client.
 * Consumer must install @supabase/supabase-js and pass `createClient` in.
 *
 * Usage:
 *   import { createClient } from '@supabase/supabase-js';
 *   const supabase = initSupabase(createClient, { storage: myAdapter });
 */
export function initSupabase(
  createClient: (url: string, key: string, options: Record<string, unknown>) => unknown,
  options: SupabaseClientOptions,
) {
  return createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    auth: {
      storage: options.storage,
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false, // no browser URL on mobile
    },
  });
}
