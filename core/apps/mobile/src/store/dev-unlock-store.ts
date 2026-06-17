import { create } from 'zustand';
import { readStoredJson, writeStoredJson } from './secure-storage';

const KEY = 'lauburu_dev_tools_unlocked';

interface DevUnlockState {
  unlocked: boolean;
  hydrated: boolean;
  hydrate: () => Promise<void>;
  unlock: () => Promise<void>;
  lock: () => Promise<void>;
}

export const useDevUnlockStore = create<DevUnlockState>((set) => ({
  unlocked: false,
  hydrated: false,
  hydrate: async () => {
    try {
      const v = await readStoredJson<{ unlocked: boolean }>(KEY);
      set({ unlocked: !!v?.unlocked, hydrated: true });
    } catch {
      set({ hydrated: true });
    }
  },
  unlock: async () => {
    set({ unlocked: true });
    try { await writeStoredJson(KEY, { unlocked: true }); } catch { /* non-fatal */ }
  },
  lock: async () => {
    set({ unlocked: false });
    try { await writeStoredJson(KEY, { unlocked: false }); } catch { /* non-fatal */ }
  },
}));
