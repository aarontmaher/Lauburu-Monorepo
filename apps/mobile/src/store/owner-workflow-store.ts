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
    'Confirm Android v14 lands on a tester device — workflow side of auto-update proof PASSED.',
  currentBlocker:
    'None code-side. Awaiting tester device to receive v14 within 15–60 min of run 25361589282 success at 06:59:36 UTC.',
  lastStatus: [
    'Android proof PASSED end-to-end on retry: run 25361589282 → EAS build ✓ → Submit AAB to Play Internal Testing ✓ at 06:59:36 UTC. Play accepted the COMPLETED release.',
    'iOS Build 15 + TestFlight submit SUCCEEDED earlier (run 25349256198).',
    'iOS HealthKit Mac/Vision warning fix shipped on Build 15. Owner FAB rule + Admin/Dev redesign also live on Build 15. BLE CPS/CSC fix lands on next paired build.',
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
    'Observe a tester device for v14 over the next 15–60 min — Play accepted the COMPLETED release on run 25361589282 at 06:59:36 UTC; no Play Console click should be required',
    'Accept the TestFlight update prompt to install Build 15 (already on App Store Connect from run 25349256198)',
    'When v14 confirmed on a tester device, reply "v14 received" — that closes the auto-update lane',
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
