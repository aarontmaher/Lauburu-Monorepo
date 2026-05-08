/**
 * Spend gates store — local cache of pending AI spend gates.
 *
 * Mirrors approval-gates-store.ts (same lifecycle helpers under the
 * hood) but tracks the spend-specific extras: triggerType,
 * estimatedCostClass, precheckSummary, precheckRuleId. Surfaces an
 * "Export prompt" call so Aaron can paste the question into ChatGPT
 * out-of-band rather than approving an in-app paid AI call.
 *
 * MVP wiring:
 *   - hydrate() reads secureStorage; first run seeds from
 *     DEFAULT_SPEND_GATES.
 *   - approve / defer / cancel / markCompleted / applyExpiries
 *     dispatch through @lauburu/shared spend transitions.
 *   - exportPrompt(id) returns the sanitised prompt-export string
 *     so the AdminDev surface can drop it into the clipboard /
 *     SelectableCopyButton.
 */
import { create } from 'zustand';
import {
  approveSpendGate,
  cancelSpendGate,
  completeSpendGate,
  deferSpendGate,
  expireSpendIfDue,
  exportSpendGatePrompt,
  isSpendGateActionable,
  type SpendGate,
} from '@lauburu/shared';
import { readStoredJson, writeStoredJson } from './secure-storage';

const KEY = 'lauburu_spend_gates_v1';
const RESOLVER = 'Aaron iPhone admin-dev';

const DEFAULT_SPEND_GATES: readonly SpendGate[] = [
  {
    id: 'spend-readiness-anomaly-2026-05-09',
    title: 'Approve AI re-read for today’s readiness drop',
    description:
      'Today’s readiness dropped 18 pts vs the rolling baseline; deterministic precheck found no explanatory training/sleep/journal signal. Optional AI call would phrase a one-line association narrative.',
    priority: 'P2',
    actionType: 'mcp_write',
    status: 'pending',
    safeDefault: 'skip',
    createdAt: '2026-05-09T07:00:00Z',
    expiresAt: '2026-05-10T07:00:00Z',
    resolvedAt: null,
    resolvedBy: null,
    deferUntil: null,
    resolutionNote: null,
    ledgerActionId: null,
    actionPayload:
      'Phrase a one-line association narrative for the 18-pt readiness drop. No causation language; no medical advice; associations only.',
    triggerType: 'readiness_anomaly',
    estimatedCostClass: 'small',
    precheckSummary:
      'Readiness drop 18 pts vs baseline 72. Today 54. No deterministic explanatory signal in training, sleep, or journal. Numbers are descriptive only.',
    precheckRuleId: 'precheck-readiness-anomaly-v1',
  },
  {
    id: 'spend-journal-import-ambiguous-2026-05-09',
    title: 'Approve AI re-read of pasted journal text',
    description:
      'Parser flagged 5 of 12 rows as low-confidence and most rows missing required fields. AI re-read MAY recover more rows; precheck still requires user confirmation per row.',
    priority: 'P3',
    actionType: 'mcp_write',
    status: 'pending',
    safeDefault: 'wait',
    createdAt: '2026-05-09T08:00:00Z',
    expiresAt: '2026-05-12T08:00:00Z',
    resolvedAt: null,
    resolvedBy: null,
    deferUntil: null,
    resolutionNote: null,
    ledgerActionId: 'fs020-b20d-ui-after-parser-confirmation',
    actionPayload:
      'Re-parse the pasted note text into journal-rows. Output schema must match ParsedJournalNotesEntry. No medical advice. Uncertain rows still require user confirmation.',
    triggerType: 'journal_import',
    estimatedCostClass: 'medium',
    precheckSummary:
      'Journal import: 12 parsed rows. 7 need user confirmation, 5 low-confidence. Most rows missing required fields. No medical advice. No causation. The user reviews each row before save.',
    precheckRuleId: 'precheck-journal-import-v1',
  },
];

interface SpendGatesPersistedBlob {
  gates: SpendGate[];
  recentLedgerNotes: Array<{ at: string; gateId: string; note: string }>;
}

interface SpendGatesState {
  gates: SpendGate[];
  hydrated: boolean;
  refreshing: boolean;
  recentLedgerNotes: Array<{ at: string; gateId: string; note: string }>;
  hydrate: () => Promise<void>;
  refresh: () => Promise<void>;
  applyExpiries: () => Promise<void>;
  approve: (id: string, note?: string | null) => Promise<{ ok: boolean; reason: string }>;
  defer: (id: string, deferUntil: string, note?: string | null) => Promise<{ ok: boolean; reason: string }>;
  cancel: (id: string, note?: string | null) => Promise<{ ok: boolean; reason: string }>;
  markCompleted: (id: string, note?: string | null) => Promise<{ ok: boolean; reason: string }>;
  exportPrompt: (id: string) => string | null;
  pendingCount: () => number;
  byId: (id: string) => SpendGate | null;
}

const RECENT_LEDGER_NOTES_CAP = 20;

function persist(state: { gates: SpendGate[]; recentLedgerNotes: SpendGatesState['recentLedgerNotes'] }): Promise<void> {
  const blob: SpendGatesPersistedBlob = {
    gates: state.gates,
    recentLedgerNotes: state.recentLedgerNotes.slice(-RECENT_LEDGER_NOTES_CAP),
  };
  return writeStoredJson(KEY, blob);
}

function appendNote(
  state: { recentLedgerNotes: SpendGatesState['recentLedgerNotes'] },
  gateId: string,
  note: string | null,
): SpendGatesState['recentLedgerNotes'] {
  if (!note) return state.recentLedgerNotes;
  return [...state.recentLedgerNotes, { at: new Date().toISOString(), gateId, note }].slice(-RECENT_LEDGER_NOTES_CAP);
}

export const useSpendGatesStore = create<SpendGatesState>((set, get) => ({
  gates: [],
  hydrated: false,
  refreshing: false,
  recentLedgerNotes: [],
  hydrate: async () => {
    try {
      const stored = await readStoredJson<Partial<SpendGatesPersistedBlob>>(KEY);
      if (stored && Array.isArray(stored.gates) && stored.gates.length > 0) {
        set({
          gates: stored.gates,
          recentLedgerNotes: Array.isArray(stored.recentLedgerNotes) ? stored.recentLedgerNotes : [],
          hydrated: true,
        });
        return;
      }
      const seeded: SpendGatesPersistedBlob = {
        gates: DEFAULT_SPEND_GATES.map((g) => ({ ...g })),
        recentLedgerNotes: [],
      };
      try { await writeStoredJson(KEY, seeded); } catch { /* non-fatal */ }
      set({ gates: seeded.gates, recentLedgerNotes: [], hydrated: true });
    } catch {
      set({ gates: DEFAULT_SPEND_GATES.map((g) => ({ ...g })), recentLedgerNotes: [], hydrated: true });
    }
  },
  refresh: async () => {
    set({ refreshing: true });
    try { await get().applyExpiries(); } finally { set({ refreshing: false }); }
  },
  applyExpiries: async () => {
    let changed = false;
    let recent = get().recentLedgerNotes;
    const updated: SpendGate[] = [];
    for (const gate of get().gates) {
      const result = expireSpendIfDue(gate);
      if (result.ok) {
        changed = true;
        updated.push(result.next);
        recent = appendNote({ recentLedgerNotes: recent }, gate.id, result.ledgerNote);
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
    if (!gate) return { ok: false, reason: 'gate not found' };
    const result = approveSpendGate(gate, RESOLVER, { note: note ?? null });
    if (!result.ok) return { ok: false, reason: result.reason };
    const gates = get().gates.map((g) => (g.id === id ? result.next : g));
    const recent = appendNote(get(), id, result.ledgerNote);
    set({ gates, recentLedgerNotes: recent });
    try { await persist({ gates, recentLedgerNotes: recent }); } catch { /* non-fatal */ }
    return { ok: true, reason: result.reason };
  },
  defer: async (id, deferUntil, note) => {
    const gate = get().byId(id);
    if (!gate) return { ok: false, reason: 'gate not found' };
    const result = deferSpendGate(gate, RESOLVER, deferUntil, { note: note ?? null });
    if (!result.ok) return { ok: false, reason: result.reason };
    const gates = get().gates.map((g) => (g.id === id ? result.next : g));
    const recent = appendNote(get(), id, result.ledgerNote);
    set({ gates, recentLedgerNotes: recent });
    try { await persist({ gates, recentLedgerNotes: recent }); } catch { /* non-fatal */ }
    return { ok: true, reason: result.reason };
  },
  cancel: async (id, note) => {
    const gate = get().byId(id);
    if (!gate) return { ok: false, reason: 'gate not found' };
    const result = cancelSpendGate(gate, RESOLVER, { note: note ?? null });
    if (!result.ok) return { ok: false, reason: result.reason };
    const gates = get().gates.map((g) => (g.id === id ? result.next : g));
    const recent = appendNote(get(), id, result.ledgerNote);
    set({ gates, recentLedgerNotes: recent });
    try { await persist({ gates, recentLedgerNotes: recent }); } catch { /* non-fatal */ }
    return { ok: true, reason: result.reason };
  },
  markCompleted: async (id, note) => {
    const gate = get().byId(id);
    if (!gate) return { ok: false, reason: 'gate not found' };
    const result = completeSpendGate(gate, RESOLVER, { note: note ?? null });
    if (!result.ok) return { ok: false, reason: result.reason };
    const gates = get().gates.map((g) => (g.id === id ? result.next : g));
    const recent = appendNote(get(), id, result.ledgerNote);
    set({ gates, recentLedgerNotes: recent });
    try { await persist({ gates, recentLedgerNotes: recent }); } catch { /* non-fatal */ }
    return { ok: true, reason: result.reason };
  },
  exportPrompt: (id) => {
    const gate = get().byId(id);
    return gate ? exportSpendGatePrompt(gate) : null;
  },
  pendingCount: () => get().gates.filter((g) => g.status === 'pending').length,
  byId: (id) => get().gates.find((g) => g.id === id) ?? null,
}));

export { isSpendGateActionable };
