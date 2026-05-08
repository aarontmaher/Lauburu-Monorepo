/**
 * Approval gates store — local cache of the data/approval-gates/
 * gates.json ring buffer plus optimistic mobile-side transitions.
 *
 * MVP wiring:
 *   - hydrate() loads from secureStorage; if empty, seeds from the
 *     compiled-in fallback (see DEFAULT_GATES).
 *   - refresh() is a hook for future MCP fetch; today it's a no-op
 *     placeholder so the AdminDev surface can call it without
 *     breaking when the project.list_approval_gates tool ships.
 *   - approve / defer / cancel / complete dispatch through the pure
 *     transition helpers in @lauburu/shared so the contract matches
 *     the eventual server-side writeback.
 *   - All transitions are optimistic + persisted locally; the server
 *     writeback happens when the backend route lands. Until then,
 *     "approve" puts the gate in `approved` locally and emits a
 *     ledgerNote that Aaron / Codex can paste into the action ledger.
 *
 * Privacy: this store never holds tokens or secrets. The pure
 * helpers refuse to construct/mutate gates whose fields look
 * secret-shaped.
 */
import { create } from 'zustand';
import {
  approveGate,
  cancelGate,
  completeGate,
  deferGate,
  expireIfDue,
  gateLockReason,
  isActionable,
  isGateUnlocked,
  type ApprovalGate,
  type ApprovalTransitionResult,
} from '@lauburu/shared';
import { readStoredJson, writeStoredJson } from './secure-storage';

const KEY = 'lauburu_approval_gates_v1';
const RESOLVER = 'Aaron iPhone admin-dev';

const DEFAULT_GATES: readonly ApprovalGate[] = [
  // Mirrors data/approval-gates/gates.json so the device has
  // something to render before the first refresh() lands.
  {
    id: 'gate-android-v20-play-upload',
    title: 'Approve Android v20 Play Internal upload',
    description:
      'Manually upload v20 AAB to Play Console Internal Testing. EAS build 58071abc finished; AAB pending Aaron drag-drop. v20 carries the Health Connect crash patch and the Health Connect debug-card surface.',
    priority: 'P0',
    actionType: 'play_console_upload',
    status: 'pending',
    safeDefault: 'wait',
    createdAt: '2026-05-08T13:01:40Z',
    expiresAt: '2026-05-15T00:00:00Z',
    resolvedAt: null,
    resolvedBy: null,
    deferUntil: null,
    resolutionNote: null,
    ledgerActionId: 'qa-android-versioncode-20-build-dispatched',
    dependsOnGateId: null,
    actionPayload:
      'Open Play Console → Lauburu → Testing → Internal testing → Create release → upload ~/Downloads/lauburu-android-versionCode20-health-connect-debug-surface.aab → Save → Review → Start rollout to Internal Testing.',
  },
  {
    id: 'gate-mcp-core-worker-deploy',
    title: 'Approve worker deploy of project.ping diagnostic',
    description:
      'Diagnostic tool added to /mcp/v2 core surface (commit 1081d65). Code is committed but not deployed; existing /mcp/v2 still works without it. Deploy unblocks Agent troubleshooting via project.ping.',
    priority: 'P2',
    actionType: 'worker_deploy',
    status: 'pending',
    safeDefault: 'wait',
    createdAt: '2026-05-08T14:30:00Z',
    expiresAt: '2026-05-22T00:00:00Z',
    resolvedAt: null,
    resolvedBy: null,
    deferUntil: null,
    resolutionNote: null,
    ledgerActionId: null,
    actionPayload: 'cd cloudflare-worker && npx wrangler deploy --env preview',
    // Worker deploy depends on the v20 Play upload completing, so
    // the deploy gate stays locked until Aaron upload-approves the
    // build first. This is the canonical chained-approvals example.
    dependsOnGateId: 'gate-android-v20-play-upload',
  },
];

interface ApprovalGatesPersistedBlob {
  gates: ApprovalGate[];
  /** Append-only audit trail of recent ledger notes the store emitted. Capped. */
  recentLedgerNotes: Array<{ at: string; gateId: string; note: string }>;
  hydratedFromDefaultsAt: string | null;
}

interface ApprovalGatesState {
  gates: ApprovalGate[];
  hydrated: boolean;
  refreshing: boolean;
  recentLedgerNotes: Array<{ at: string; gateId: string; note: string }>;
  hydrate: () => Promise<void>;
  refresh: () => Promise<void>;
  applyExpiries: () => Promise<void>;
  approve: (id: string, note?: string | null) => Promise<ApprovalTransitionResult>;
  defer: (id: string, deferUntil: string, note?: string | null) => Promise<ApprovalTransitionResult>;
  cancel: (id: string, note?: string | null) => Promise<ApprovalTransitionResult>;
  markCompleted: (id: string, note?: string | null) => Promise<ApprovalTransitionResult>;
  pendingCount: () => number;
  actionableGates: () => ApprovalGate[];
  byId: (id: string) => ApprovalGate | null;
  ledgerNotePreview: () => string | null;
  /** Whether the gate's upstream dependency (if any) has cleared. */
  isUnlocked: (id: string) => boolean;
  /** Human reason a gate is locked, or null when ready. */
  lockReason: (id: string) => string | null;
}

const RECENT_LEDGER_NOTES_CAP = 20;

function persist(state: { gates: ApprovalGate[]; recentLedgerNotes: ApprovalGatesState['recentLedgerNotes'] }): Promise<void> {
  const blob: ApprovalGatesPersistedBlob = {
    gates: state.gates,
    recentLedgerNotes: state.recentLedgerNotes.slice(-RECENT_LEDGER_NOTES_CAP),
    hydratedFromDefaultsAt: null,
  };
  return writeStoredJson(KEY, blob);
}

function recordLedgerNote(
  state: { recentLedgerNotes: ApprovalGatesState['recentLedgerNotes'] },
  gateId: string,
  note: string | null,
): ApprovalGatesState['recentLedgerNotes'] {
  if (!note) return state.recentLedgerNotes;
  const entry = { at: new Date().toISOString(), gateId, note };
  return [...state.recentLedgerNotes, entry].slice(-RECENT_LEDGER_NOTES_CAP);
}

export const useApprovalGatesStore = create<ApprovalGatesState>((set, get) => ({
  gates: [],
  hydrated: false,
  refreshing: false,
  recentLedgerNotes: [],
  hydrate: async () => {
    try {
      const stored = await readStoredJson<Partial<ApprovalGatesPersistedBlob>>(KEY);
      if (stored && Array.isArray(stored.gates) && stored.gates.length > 0) {
        set({
          gates: stored.gates,
          recentLedgerNotes: Array.isArray(stored.recentLedgerNotes) ? stored.recentLedgerNotes : [],
          hydrated: true,
        });
        return;
      }
      const seeded: ApprovalGatesPersistedBlob = {
        gates: DEFAULT_GATES.map((gate) => ({ ...gate })),
        recentLedgerNotes: [],
        hydratedFromDefaultsAt: new Date().toISOString(),
      };
      try { await writeStoredJson(KEY, seeded); } catch { /* non-fatal */ }
      set({ gates: seeded.gates, recentLedgerNotes: [], hydrated: true });
    } catch {
      set({
        gates: DEFAULT_GATES.map((gate) => ({ ...gate })),
        recentLedgerNotes: [],
        hydrated: true,
      });
    }
  },
  refresh: async () => {
    // Placeholder for the future project.list_approval_gates MCP
    // call. Today we just re-apply expiries so a stale device
    // surfaces safeDefault decisions without a server round-trip.
    set({ refreshing: true });
    try {
      await get().applyExpiries();
    } finally {
      set({ refreshing: false });
    }
  },
  applyExpiries: async () => {
    const updated: ApprovalGate[] = [];
    let changed = false;
    let recent = get().recentLedgerNotes;
    for (const gate of get().gates) {
      const result = expireIfDue(gate);
      if (result.ok) {
        changed = true;
        updated.push(result.next);
        recent = recordLedgerNote({ recentLedgerNotes: recent }, gate.id, result.ledgerNote);
      } else {
        updated.push(gate);
      }
    }
    if (!changed) return;
    set({ gates: updated, recentLedgerNotes: recent });
    try { await persist({ gates: updated, recentLedgerNotes: recent }); } catch { /* non-fatal */ }
  },
  approve: async (id, note) => {
    const gate = get().byId(id);
    if (!gate) return { ok: false, reason: 'gate not found', next: makeMissingGate(id), ledgerNote: null };
    const gateById = new Map(get().gates.map((g) => [g.id, g] as const));
    const result = approveGate(gate, RESOLVER, { note: note ?? null, gateById });
    if (!result.ok) return result;
    const gates = get().gates.map((g) => (g.id === id ? result.next : g));
    const recent = recordLedgerNote(get(), id, result.ledgerNote);
    set({ gates, recentLedgerNotes: recent });
    try { await persist({ gates, recentLedgerNotes: recent }); } catch { /* non-fatal */ }
    return result;
  },
  defer: async (id, deferUntil, note) => {
    const gate = get().byId(id);
    if (!gate) return { ok: false, reason: 'gate not found', next: makeMissingGate(id), ledgerNote: null };
    const gateById = new Map(get().gates.map((g) => [g.id, g] as const));
    const result = deferGate(gate, RESOLVER, deferUntil, { note: note ?? null, gateById });
    if (!result.ok) return result;
    const gates = get().gates.map((g) => (g.id === id ? result.next : g));
    const recent = recordLedgerNote(get(), id, result.ledgerNote);
    set({ gates, recentLedgerNotes: recent });
    try { await persist({ gates, recentLedgerNotes: recent }); } catch { /* non-fatal */ }
    return result;
  },
  cancel: async (id, note) => {
    const gate = get().byId(id);
    if (!gate) return { ok: false, reason: 'gate not found', next: makeMissingGate(id), ledgerNote: null };
    const result = cancelGate(gate, RESOLVER, { note: note ?? null });
    if (!result.ok) return result;
    const gates = get().gates.map((g) => (g.id === id ? result.next : g));
    const recent = recordLedgerNote(get(), id, result.ledgerNote);
    set({ gates, recentLedgerNotes: recent });
    try { await persist({ gates, recentLedgerNotes: recent }); } catch { /* non-fatal */ }
    return result;
  },
  markCompleted: async (id, note) => {
    const gate = get().byId(id);
    if (!gate) return { ok: false, reason: 'gate not found', next: makeMissingGate(id), ledgerNote: null };
    const result = completeGate(gate, RESOLVER, { note: note ?? null });
    if (!result.ok) return result;
    const gates = get().gates.map((g) => (g.id === id ? result.next : g));
    const recent = recordLedgerNote(get(), id, result.ledgerNote);
    set({ gates, recentLedgerNotes: recent });
    try { await persist({ gates, recentLedgerNotes: recent }); } catch { /* non-fatal */ }
    return result;
  },
  pendingCount: () => get().gates.filter((g) => g.status === 'pending').length,
  actionableGates: () => get().gates.filter((g) => isActionable(g)),
  byId: (id) => get().gates.find((g) => g.id === id) ?? null,
  ledgerNotePreview: () => {
    const recent = get().recentLedgerNotes;
    return recent.length > 0 ? recent[recent.length - 1].note : null;
  },
  isUnlocked: (id) => {
    const gate = get().byId(id);
    if (!gate) return false;
    const gateById = new Map(get().gates.map((g) => [g.id, g] as const));
    return isGateUnlocked(gate, gateById);
  },
  lockReason: (id) => {
    const gate = get().byId(id);
    if (!gate) return 'gate not found';
    const gateById = new Map(get().gates.map((g) => [g.id, g] as const));
    return gateLockReason(gate, gateById);
  },
}));

function makeMissingGate(id: string): ApprovalGate {
  return {
    id,
    title: 'missing',
    description: 'gate not found in store',
    priority: 'P3',
    actionType: 'other',
    status: 'cancelled',
    safeDefault: 'skip',
    createdAt: new Date().toISOString(),
    expiresAt: new Date().toISOString(),
    resolvedAt: null,
    resolvedBy: null,
    deferUntil: null,
    resolutionNote: null,
    ledgerActionId: null,
    actionPayload: null,
    dependsOnGateId: null,
  };
}
