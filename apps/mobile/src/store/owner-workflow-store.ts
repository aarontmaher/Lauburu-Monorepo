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
    'First proof Android build with releaseStatus=completed to confirm full auto-promote on Internal Testing track.',
  currentBlocker:
    'No code blockers. Aaron-side: trigger Build Android + upload to Internal Testing once to verify the auto-promote path on a real release.',
  lastStatus: [
    'Auto-update: iOS end-to-end auto-ship live. Android upload-to-Play DRAFT was live; releaseStatus now flipped to completed in eas.json.',
    'Repo-only: iOS HealthKit Mac/Vision warning fix on main; Admin/Dev redesign on main; Android auto-promote flip on main.',
    'Blocked: nothing in code; awaiting one proof Android build to confirm completed-status auto-promote.',
    'Verified: tsc --noEmit clean.',
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
    'Trigger Build Android + upload to Internal Testing from Admin/Dev once to verify auto-promote',
    'TestFlight + Play Store auto-update on Aaron\'s own devices — accept the prompts',
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
