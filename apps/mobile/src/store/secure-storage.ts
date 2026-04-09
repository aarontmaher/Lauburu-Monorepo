/**
 * Storage adapter for Supabase auth session persistence.
 *
 * Tries expo-secure-store (Keychain/Keystore) first.
 * Falls back to in-memory storage if native module is unavailable
 * (e.g., Expo Go without native modules, or stale prebuild).
 */
import type { StorageAdapter } from '@lauburu/shared';

/** In-memory fallback — sessions survive for the app lifetime only */
const memoryStore = new Map<string, string>();

let _secureStore: any = null;
let _checked = false;

function getSecureStore(): any {
  if (_checked) return _secureStore;
  _checked = true;
  try {
    const mod = require('expo-secure-store');
    // Verify the native module is actually available
    if (mod && typeof mod.getItemAsync === 'function') {
      _secureStore = mod;
    }
  } catch {
    _secureStore = null;
  }
  return _secureStore;
}

export const secureStorage: StorageAdapter = {
  async getItem(key: string): Promise<string | null> {
    const ss = getSecureStore();
    if (ss) {
      try {
        return await ss.getItemAsync(key);
      } catch {
        // Fall through to memory
      }
    }
    return memoryStore.get(key) ?? null;
  },

  async setItem(key: string, value: string): Promise<void> {
    const ss = getSecureStore();
    if (ss) {
      try {
        await ss.setItemAsync(key, value);
        return;
      } catch {
        // Fall through to memory
      }
    }
    memoryStore.set(key, value);
  },

  async removeItem(key: string): Promise<void> {
    const ss = getSecureStore();
    if (ss) {
      try {
        await ss.deleteItemAsync(key);
      } catch {
        // Ignore
      }
    }
    memoryStore.delete(key);
  },
};
