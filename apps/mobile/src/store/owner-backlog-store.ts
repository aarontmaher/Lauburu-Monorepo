/**
 * Owner-only Quick capture backlog — local-only store.
 *
 * Captures Aaron's brain-dump items (bugs / UX / features / release
 * blockers / health-data / AI / monetisation) to secure storage on
 * the device. Mirrors the shape backend support will accept once
 * implemented (separate batch); no migration needed when the
 * `/admin/backlog` route lands.
 *
 * Persistence is explicit and local. NOT synced. NOT shared. The
 * canonical cross-conversation backlog still lives in
 * `docs/APP_DEVELOPMENTS.md`; this store is for in-the-moment
 * capture between commits.
 */
import { create } from 'zustand';
import { readStoredJson, writeStoredJson } from './secure-storage';

const KEY = 'lauburu_owner_backlog_v1';

export type OwnerBacklogType =
  | 'bug'
  | 'ux'
  | 'feature'
  | 'release_blocker'
  | 'health_data'
  | 'ai_coaching'
  | 'monetisation';

export type OwnerBacklogPlatform = 'android' | 'ios' | 'both';
export type OwnerBacklogStatus = 'open' | 'in_progress' | 'shipped' | 'wont_fix';

export interface OwnerBacklogItem {
  id: string;
  title: string;
  details: string;
  type: OwnerBacklogType;
  platform: OwnerBacklogPlatform;
  /** Priority 1–10 per docs/FEEDBACK_PRIORITY_MODEL.md. */
  priority: number;
  status: OwnerBacklogStatus;
  /** Always 'owner' from this store; shape-compatible with future
   * tester-feedback merge where source can also be a tester id. */
  source: 'owner';
  createdAt: string;
}

interface OwnerBacklogState {
  items: OwnerBacklogItem[];
  hydrated: boolean;
  hydrate: () => Promise<void>;
  add: (input: Omit<OwnerBacklogItem, 'id' | 'createdAt' | 'source' | 'status'> & { status?: OwnerBacklogStatus }) => Promise<OwnerBacklogItem>;
  updateStatus: (id: string, status: OwnerBacklogStatus) => Promise<void>;
  remove: (id: string) => Promise<void>;
  clear: () => Promise<void>;
}

function makeId(): string {
  return `bk_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

export const useOwnerBacklogStore = create<OwnerBacklogState>((set, get) => ({
  items: [],
  hydrated: false,
  hydrate: async () => {
    try {
      const v = await readStoredJson<{ items: OwnerBacklogItem[] }>(KEY);
      const items = Array.isArray(v?.items) ? v.items : [];
      set({ items, hydrated: true });
    } catch {
      set({ hydrated: true });
    }
  },
  add: async (input) => {
    const item: OwnerBacklogItem = {
      id: makeId(),
      title: input.title,
      details: input.details,
      type: input.type,
      platform: input.platform,
      priority: input.priority,
      status: input.status ?? 'open',
      source: 'owner',
      createdAt: new Date().toISOString(),
    };
    const next = [item, ...get().items];
    set({ items: next });
    try { await writeStoredJson(KEY, { items: next }); } catch { /* non-fatal */ }
    return item;
  },
  updateStatus: async (id, status) => {
    const next = get().items.map((it) => (it.id === id ? { ...it, status } : it));
    set({ items: next });
    try { await writeStoredJson(KEY, { items: next }); } catch { /* non-fatal */ }
  },
  remove: async (id) => {
    const next = get().items.filter((it) => it.id !== id);
    set({ items: next });
    try { await writeStoredJson(KEY, { items: next }); } catch { /* non-fatal */ }
  },
  clear: async () => {
    set({ items: [] });
    try { await writeStoredJson(KEY, { items: [] }); } catch { /* non-fatal */ }
  },
}));
