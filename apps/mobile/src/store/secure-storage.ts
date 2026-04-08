/**
 * expo-secure-store adapter for Supabase auth session persistence.
 * Stores JWT tokens in iOS Keychain / Android Keystore.
 */
import * as SecureStore from 'expo-secure-store';
import type { StorageAdapter } from '@lauburu/shared';

export const secureStorage: StorageAdapter = {
  async getItem(key: string): Promise<string | null> {
    try {
      return await SecureStore.getItemAsync(key);
    } catch {
      return null;
    }
  },
  async setItem(key: string, value: string): Promise<void> {
    try {
      await SecureStore.setItemAsync(key, value);
    } catch {
      // SecureStore has a ~2KB limit per item on some platforms.
      // Supabase session tokens can exceed this — fall back silently.
      // The session will still work in-memory for the current app session.
    }
  },
  async removeItem(key: string): Promise<void> {
    try {
      await SecureStore.deleteItemAsync(key);
    } catch {
      // Ignore — key may not exist.
    }
  },
};
