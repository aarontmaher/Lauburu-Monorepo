/**
 * Owner-workflow context — the structured fields that feed the
 * deterministic prompt templates in `services/prompt-templates.ts`.
 *
 * Today the values mirror docs/APP_DEVELOPMENTS.md and are
 * hard-coded at module load. The store shape is the contract: a
 * future iteration can wire `hydrate` to a backend route, or to a
 * future Admin/Dev edit form, without changing how the templates
 * consume the data.
 *
 * Local-only, no sync. No paid AI API.
 */
import { create } from 'zustand';
import type { OwnerWorkflowContext } from '../services/prompt-templates';

const DEFAULT_CONTEXT: OwnerWorkflowContext = {
  currentPriority:
    'Android auto-promote proof build (v14) — verify result.',
  currentBlocker:
    'Proof workflow run 25349253529 in flight: preflight passed (PLAY_SA_JSON present), TypeScript clean, EAS Android build in progress, Play submit step pending downstream.',
  lastStatus: [
    'Auto-update: iOS end-to-end auto-ship live. Android v11 last manual upload; v14 build dispatched for proof.',
    'Repo-only: iOS HealthKit Mac/Vision warning fix; Admin/Dev redesign + Primary actions; Android auto-promote flip.',
    'Live workflows: android-aab-build run 25349253529 (in_progress), ios-testflight-build run 25349256198 (in_progress).',
    'Verified: tsc --noEmit clean across all commits this lane.',
  ].join(' '),
  selectedTaskBundle: undefined,
  protectedRules: [
    'grappling.opml — never edit',
    'No secrets or tokens in any output',
    'No Supabase db push',
    'No SDK upgrade',
    'No OTA',
    'No paid AI API implementation',
    'No arbitrary shell execution from the app',
    'No raw terminal embedded in the app',
    'Use predefined GitHub Actions workflows only',
  ],
  manualStepsForAaron: [
    'Watch GitHub Actions runs 25349253529 (Android) and 25349256198 (iOS) to green',
    'Once Android run is green, observe a tester device for v14 within 15–60 min — no Play Console click should be required',
    'Once iOS run is green, accept the TestFlight update prompt to install Build 15',
  ],
  canDeleteFromNotepad: [
    'Wire iOS auto-group assignment (DONE — Build 14)',
    'Add Privacy / Account-deletion pages to website (DONE)',
    'Document AI provider strategy (DONE)',
    'Document AI monetisation / cost guardrails (DONE)',
    'Audit which wearable claims are actually live (DONE)',
    'Fix iOS HealthKit Mac/Vision warning (DONE — repo-only on main)',
    'Add /admin/status backend route + signed dispatch (DONE)',
    'Hide Dev/Admin FAB from normal testers (DONE)',
    'Hide Feedback FAB from owner (DONE)',
  ],
  doNotDeleteYet: [
    'Play Console listing pass (Aaron-side)',
    'Flip releaseStatus to completed after the listing pass',
    'Next paired build (v14 + Build 15) bundling repo-only UX work + iOS warning fix',
    'Grappler Readiness Batches B/C/D',
    'AI provider implementation — gated',
    'Public production release — out of scope until tester channels are fully auto',
  ],
};

interface OwnerWorkflowState {
  context: OwnerWorkflowContext;
  /** Sets the optional task-bundle field used by every template
   * (e.g. "Grappler Readiness Batch B"). Resets to undefined when
   * cleared. Local-only. */
  setSelectedTaskBundle: (bundle: string | undefined) => void;
}

export const useOwnerWorkflowStore = create<OwnerWorkflowState>((set) => ({
  context: DEFAULT_CONTEXT,
  setSelectedTaskBundle: (bundle) =>
    set((s) => ({
      context: { ...s.context, selectedTaskBundle: bundle && bundle.trim().length > 0 ? bundle.trim() : undefined },
    })),
}));
