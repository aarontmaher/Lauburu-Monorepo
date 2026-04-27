/**
 * Storage adapter for Supabase auth session persistence.
 *
 * Tries expo-secure-store (Keychain/Keystore) first.
 * Falls back to Expo file storage, then finally in-memory storage
 * if native modules are unavailable (e.g., Expo Go or stale prebuild).
 */
import type { StorageAdapter } from '@lauburu/shared';

/** In-memory fallback — sessions survive for the app lifetime only */
const memoryStore = new Map<string, string>();
const FILESYSTEM_DIRNAME = 'lauburu-storage';

let _secureStore: any = null;
let _checked = false;
let _fileSystem: any = null;
let _fileSystemChecked = false;

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

function getFileSystem(): any {
  if (_fileSystemChecked) return _fileSystem;
  _fileSystemChecked = true;
  try {
    const mod = require('expo-file-system/legacy');
    if (
      mod &&
      typeof mod.readAsStringAsync === 'function' &&
      typeof mod.writeAsStringAsync === 'function' &&
      typeof mod.deleteAsync === 'function' &&
      typeof mod.makeDirectoryAsync === 'function' &&
      typeof mod.documentDirectory === 'string'
    ) {
      _fileSystem = mod;
    }
  } catch {
    _fileSystem = null;
  }
  return _fileSystem;
}

function buildFileUri(key: string): string | null {
  const fs = getFileSystem();
  const documentDirectory = fs?.documentDirectory;
  if (typeof documentDirectory !== 'string' || documentDirectory.length === 0) {
    return null;
  }
  return `${documentDirectory}${FILESYSTEM_DIRNAME}/${encodeURIComponent(key)}.json`;
}

async function ensureFilesystemDir(): Promise<boolean> {
  const fs = getFileSystem();
  const documentDirectory = fs?.documentDirectory;
  if (typeof documentDirectory !== 'string' || documentDirectory.length === 0) {
    return false;
  }
  const dirUri = `${documentDirectory}${FILESYSTEM_DIRNAME}`;
  try {
    await fs.makeDirectoryAsync(dirUri, { intermediates: true });
    return true;
  } catch {
    return false;
  }
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
    const fileUri = buildFileUri(key);
    const fs = getFileSystem();
    if (fs && fileUri) {
      try {
        return await fs.readAsStringAsync(fileUri);
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
    const fs = getFileSystem();
    const fileUri = buildFileUri(key);
    if (fs && fileUri) {
      try {
        const ready = await ensureFilesystemDir();
        if (ready) {
          await fs.writeAsStringAsync(fileUri, value);
          return;
        }
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
    const fs = getFileSystem();
    const fileUri = buildFileUri(key);
    if (fs && fileUri) {
      try {
        await fs.deleteAsync(fileUri, { idempotent: true });
      } catch {
        // Ignore
      }
    }
    memoryStore.delete(key);
  },
};

export async function readStoredJson<T>(
  key: string,
): Promise<T | null> {
  try {
    const raw = await secureStorage.getItem(key);
    if (!raw) return null;
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export async function writeStoredJson(
  key: string,
  value: unknown,
): Promise<void> {
  try {
    await secureStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Silent — local-first persistence should never block the UI.
  }
}

export async function removeStoredJson(key: string): Promise<void> {
  try {
    await secureStorage.removeItem(key);
  } catch {
    // Silent — local-first persistence should never block the UI.
  }
}
