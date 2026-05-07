import { create } from 'zustand';
import { readStoredJson, writeStoredJson } from './secure-storage';

const KEY = 'lauburu_admin_dev_notifications_v1';

interface AdminDevNotificationPrefs {
  allWorkerDirectionAlertsEnabled: boolean;
  lastAllWorkerDirectionAlertKey: string | null;
  lastAllWorkerDirectionAlertAt: string | null;
}

interface AdminDevNotificationState extends AdminDevNotificationPrefs {
  hydrated: boolean;
  hydrate: () => Promise<void>;
  setAllWorkerDirectionAlertsEnabled: (enabled: boolean) => Promise<void>;
  markAllWorkerDirectionAlertSeen: (key: string) => Promise<void>;
}

const DEFAULT_PREFS: AdminDevNotificationPrefs = {
  allWorkerDirectionAlertsEnabled: true,
  lastAllWorkerDirectionAlertKey: null,
  lastAllWorkerDirectionAlertAt: null,
};

function persistPrefs(prefs: AdminDevNotificationPrefs) {
  return writeStoredJson(KEY, prefs);
}

export const useAdminDevNotificationStore = create<AdminDevNotificationState>((set, get) => ({
  ...DEFAULT_PREFS,
  hydrated: false,
  hydrate: async () => {
    try {
      const stored = await readStoredJson<Partial<AdminDevNotificationPrefs>>(KEY);
      set({
        allWorkerDirectionAlertsEnabled:
          stored?.allWorkerDirectionAlertsEnabled ?? DEFAULT_PREFS.allWorkerDirectionAlertsEnabled,
        lastAllWorkerDirectionAlertKey: stored?.lastAllWorkerDirectionAlertKey ?? null,
        lastAllWorkerDirectionAlertAt: stored?.lastAllWorkerDirectionAlertAt ?? null,
        hydrated: true,
      });
    } catch {
      set({ hydrated: true });
    }
  },
  setAllWorkerDirectionAlertsEnabled: async (enabled) => {
    const next: AdminDevNotificationPrefs = {
      allWorkerDirectionAlertsEnabled: enabled,
      lastAllWorkerDirectionAlertKey: get().lastAllWorkerDirectionAlertKey,
      lastAllWorkerDirectionAlertAt: get().lastAllWorkerDirectionAlertAt,
    };
    set(next);
    try { await persistPrefs(next); } catch { /* non-fatal */ }
  },
  markAllWorkerDirectionAlertSeen: async (key) => {
    const next: AdminDevNotificationPrefs = {
      allWorkerDirectionAlertsEnabled: get().allWorkerDirectionAlertsEnabled,
      lastAllWorkerDirectionAlertKey: key,
      lastAllWorkerDirectionAlertAt: new Date().toISOString(),
    };
    set(next);
    try { await persistPrefs(next); } catch { /* non-fatal */ }
  },
}));
