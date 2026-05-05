/**
 * Local audit-event store — captures structured "what is the
 * health-source state right now" metadata so Admin/Dev can render
 * recent events and (eventually) ChatGPT / Claude connectors can
 * read aggregated summaries.
 *
 * IMPORTANT: this store contains METADATA ABOUT SOURCES, not the
 * health data itself. See docs/IN_APP_AUDIT_SYSTEM.md for the
 * privacy boundary — values like step counts, HRV ms, sleep
 * durations, workout details NEVER land here.
 *
 * Local-only persistence via secure-storage. Capped at MAX_EVENTS
 * to keep the device buffer bounded. When the backend audit
 * route lands (see docs/IN_APP_AUDIT_SYSTEM.md § "Backend route
 * contract"), the local ring stays as the canonical short-term
 * buffer; the backend layer aggregates across devices.
 */
import { create } from 'zustand';
import { readStoredJson, writeStoredJson } from './secure-storage';

const KEY = 'lauburu_audit_events_v1';
const MAX_EVENTS = 200;

export type AuditEventType =
  | 'health_source_visible'
  | 'health_source_missing'
  | 'permission_requested'
  | 'permission_denied'
  | 'permission_granted'
  | 'sync_started'
  | 'sync_succeeded'
  | 'sync_failed'
  | 'missing_metrics'
  | 'backend_error_hidden'
  | 'raw_error_exposed'
  | 'feedback_submitted';

export type AuditSeverity = 'info' | 'warning' | 'error';

export type AuditSourceId =
  | 'apple_health'
  | 'health_connect'
  | 'whoop_direct'
  | 'polar_direct'
  | 'whoop_csv'
  | 'polar_export'
  | 'manual_checkin'
  | 'manual_training_log'
  | 'ble_machine';

export type AuditPlatform = 'ios' | 'android' | 'web' | 'unknown';

export type AuditStatus =
  | 'new'
  | 'triaged'
  | 'fixed_repo_only'
  | 'shipped'
  | 'verified'
  | 'archived';

export interface AuditEvent {
  id: string;
  createdAt: string;
  userId?: string | null;
  testerId?: string | null;
  platform: AuditPlatform;
  appVersion?: string | null;
  buildNumber?: string | null;
  screen?: string | null;
  eventType: AuditEventType;
  severity: AuditSeverity;
  sourceId?: AuditSourceId | null;
  sourceState?: string | null;
  permissionState?: string | null;
  syncMode?: 'live_sync' | 'historical_upload' | 'manual' | 'unavailable' | null;
  lastSyncedAt?: string | null;
  availableFields?: string[];
  missingFields?: string[];
  staleReason?: string | null;
  userVisibleMessage?: string | null;
  developerMessage?: string | null;
  screenshotUrl?: string | null;
  status: AuditStatus;
}

interface AuditEventState {
  events: AuditEvent[];
  hydrated: boolean;
  hydrate: () => Promise<void>;
  /** Append an event. Caller may omit `id`, `createdAt`, and
   * `status` — the store fills them in. Returns the persisted
   * event for chaining. */
  add: (
    input: Omit<AuditEvent, 'id' | 'createdAt' | 'status'> & {
      status?: AuditStatus;
    },
  ) => Promise<AuditEvent>;
  setStatus: (id: string, status: AuditStatus) => Promise<void>;
  clear: () => Promise<void>;
}

function makeId(): string {
  return `ae_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

export const useAuditEventStore = create<AuditEventState>((set, get) => ({
  events: [],
  hydrated: false,
  hydrate: async () => {
    try {
      const v = await readStoredJson<{ events: AuditEvent[] }>(KEY);
      const events = Array.isArray(v?.events) ? v.events.slice(-MAX_EVENTS) : [];
      set({ events, hydrated: true });
    } catch {
      set({ hydrated: true });
    }
  },
  add: async (input) => {
    // Build the event by taking the caller's fields first then
    // overriding the synthesized id / createdAt / status that the
    // store always controls. Keeps the contract: callers cannot
    // forge an id or backdate a createdAt.
    const { status: callerStatus, ...rest } = input;
    const event: AuditEvent = {
      ...rest,
      id: makeId(),
      createdAt: new Date().toISOString(),
      status: callerStatus ?? 'new',
    };
    const next = [...get().events, event].slice(-MAX_EVENTS);
    set({ events: next });
    try { await writeStoredJson(KEY, { events: next }); } catch { /* non-fatal */ }
    return event;
  },
  setStatus: async (id, status) => {
    const next = get().events.map((e) => (e.id === id ? { ...e, status } : e));
    set({ events: next });
    try { await writeStoredJson(KEY, { events: next }); } catch { /* non-fatal */ }
  },
  clear: async () => {
    set({ events: [] });
    try { await writeStoredJson(KEY, { events: [] }); } catch { /* non-fatal */ }
  },
}));
