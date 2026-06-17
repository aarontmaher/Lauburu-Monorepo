import { create } from 'zustand';
import { readStoredJson, writeStoredJson } from './secure-storage';

const KEY = 'lauburu_admin_dev_notifications_v1';

interface AdminDevNotificationPrefs {
  allWorkerDirectionAlertsEnabled: boolean;
  lastAllWorkerDirectionAlertKey: string | null;
  lastAllWorkerDirectionAlertAt: string | null;
  /**
   * Controller dedupe map: dedupeKey → ISO timestamp of last fire.
   * Used by the controller-notification decision layer so a stale
   * state visible across multiple foreground refreshes does not
   * spawn the same notification repeatedly. Persisted so a quick
   * background→foreground does not re-fire either.
   */
  controllerDedupe: Record<string, string>;
  /** Toggle for the Samsung-phone controller push channel. */
  controllerNotificationsEnabled: boolean;
}

interface AdminDevNotificationState extends AdminDevNotificationPrefs {
  hydrated: boolean;
  hydrate: () => Promise<void>;
  setAllWorkerDirectionAlertsEnabled: (enabled: boolean) => Promise<void>;
  markAllWorkerDirectionAlertSeen: (key: string) => Promise<void>;
  setControllerNotificationsEnabled: (enabled: boolean) => Promise<void>;
  /** Returns true if the dedupe key has not been recorded recently. */
  shouldFireControllerKey: (dedupeKey: string, ttlMs?: number) => boolean;
  recordControllerKey: (dedupeKey: string) => Promise<void>;
}

const DEFAULT_PREFS: AdminDevNotificationPrefs = {
  allWorkerDirectionAlertsEnabled: true,
  lastAllWorkerDirectionAlertKey: null,
  lastAllWorkerDirectionAlertAt: null,
  controllerDedupe: {},
  controllerNotificationsEnabled: true,
};

/** Default dedupe TTL — matches the 5-minute slice in decideControllerNotifications. */
const CONTROLLER_DEDUPE_TTL_MS = 5 * 60 * 1000;

function pruneDedupe(map: Record<string, string>, ttlMs: number): Record<string, string> {
  const cutoff = Date.now() - ttlMs;
  const next: Record<string, string> = {};
  for (const [key, iso] of Object.entries(map)) {
    const ts = Date.parse(iso);
    if (Number.isFinite(ts) && ts >= cutoff) next[key] = iso;
  }
  return next;
}

function persistPrefs(prefs: AdminDevNotificationPrefs) {
  return writeStoredJson(KEY, prefs);
}

function snapshotPrefs(state: AdminDevNotificationPrefs): AdminDevNotificationPrefs {
  return {
    allWorkerDirectionAlertsEnabled: state.allWorkerDirectionAlertsEnabled,
    lastAllWorkerDirectionAlertKey: state.lastAllWorkerDirectionAlertKey,
    lastAllWorkerDirectionAlertAt: state.lastAllWorkerDirectionAlertAt,
    controllerDedupe: state.controllerDedupe,
    controllerNotificationsEnabled: state.controllerNotificationsEnabled,
  };
}

export const useAdminDevNotificationStore = create<AdminDevNotificationState>((set, get) => ({
  ...DEFAULT_PREFS,
  hydrated: false,
  hydrate: async () => {
    try {
      const stored = await readStoredJson<Partial<AdminDevNotificationPrefs>>(KEY);
      const dedupe = stored?.controllerDedupe && typeof stored.controllerDedupe === 'object'
        ? pruneDedupe(stored.controllerDedupe as Record<string, string>, CONTROLLER_DEDUPE_TTL_MS)
        : {};
      set({
        allWorkerDirectionAlertsEnabled:
          stored?.allWorkerDirectionAlertsEnabled ?? DEFAULT_PREFS.allWorkerDirectionAlertsEnabled,
        lastAllWorkerDirectionAlertKey: stored?.lastAllWorkerDirectionAlertKey ?? null,
        lastAllWorkerDirectionAlertAt: stored?.lastAllWorkerDirectionAlertAt ?? null,
        controllerDedupe: dedupe,
        controllerNotificationsEnabled:
          stored?.controllerNotificationsEnabled ?? DEFAULT_PREFS.controllerNotificationsEnabled,
        hydrated: true,
      });
    } catch {
      set({ hydrated: true });
    }
  },
  setAllWorkerDirectionAlertsEnabled: async (enabled) => {
    set({ allWorkerDirectionAlertsEnabled: enabled });
    try { await persistPrefs(snapshotPrefs(get())); } catch { /* non-fatal */ }
  },
  markAllWorkerDirectionAlertSeen: async (key) => {
    set({
      lastAllWorkerDirectionAlertKey: key,
      lastAllWorkerDirectionAlertAt: new Date().toISOString(),
    });
    try { await persistPrefs(snapshotPrefs(get())); } catch { /* non-fatal */ }
  },
  setControllerNotificationsEnabled: async (enabled) => {
    set({ controllerNotificationsEnabled: enabled });
    try { await persistPrefs(snapshotPrefs(get())); } catch { /* non-fatal */ }
  },
  shouldFireControllerKey: (dedupeKey, ttlMs = CONTROLLER_DEDUPE_TTL_MS) => {
    const iso = get().controllerDedupe[dedupeKey];
    if (!iso) return true;
    const ts = Date.parse(iso);
    if (!Number.isFinite(ts)) return true;
    return Date.now() - ts >= ttlMs;
  },
  recordControllerKey: async (dedupeKey) => {
    const next = pruneDedupe(get().controllerDedupe, CONTROLLER_DEDUPE_TTL_MS);
    next[dedupeKey] = new Date().toISOString();
    set({ controllerDedupe: next });
    try { await persistPrefs(snapshotPrefs(get())); } catch { /* non-fatal */ }
  },
}));
