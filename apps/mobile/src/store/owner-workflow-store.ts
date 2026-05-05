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
    'Apple Health (iPhone — Aaron) + Health Connect (Android — girlfriend) usable for daily testing.',
  currentBlocker:
    'Free-tier gate was hiding primary platform health cards from non-member users. Removed in this batch; ships with next paired build.',
  lastStatus: [
    'Auto-update PROVEN end-to-end: Android run 25361589282 → Play accepted COMPLETED release at 06:59:36 UTC → tester device received v14.',
    'iOS Build 15 + TestFlight submit SUCCEEDED earlier (run 25349256198) carrying iOS HealthKit Mac/Vision warning fix, owner FAB rule, Admin/Dev redesign, AI Coach UX cleanup, BLE CPS/CSC fix.',
    'Future paired builds: bump versionCode + buildNumber and dispatch Build Android + upload + Build iOS + submit. No manual steps.',
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
    'Auto-update lane closed — no manual release steps for routine paired builds',
    'Future paired build: bump app.json android.versionCode + ios.buildNumber, dispatch Build Android + upload + Build iOS + submit from Admin/Dev Primary actions',
  ],
  canDeleteFromNotepad: [
    'Wire iOS auto-group assignment (DONE — Build 14)',
    'Add Privacy / Account-deletion pages to website (DONE)',
    'Document AI provider strategy (DONE)',
    'Document AI monetisation / cost guardrails (DONE)',
    'Audit which wearable claims are actually live (DONE)',
    'Fix iOS HealthKit Mac/Vision warning (DONE — shipped Build 15)',
    'Add /admin/status backend route + signed dispatch (DONE)',
    'Hide Dev/Admin FAB from normal testers (DONE)',
    'Hide Feedback FAB from owner (DONE)',
    'Play Console listing pass (DONE — Aaron-side)',
    'Flip releaseStatus to completed (DONE — eas.json)',
    'Android auto-promote proof: workflow + Play API + tester device (DONE 2026-05-06 — run 25361589282 + v14 received)',
  ],
  doNotDeleteYet: [
    'Grappler Readiness Batch B — extend NextDayCheckin sliders',
    'Grappler Readiness Batch C — extend TrainingSession schema',
    'Grappler Readiness Batch D — bucket-ring UI on AthleteStateStrip',
    'AI provider implementation — gated by AI_PROVIDER_STRATEGY.md + AI_MONETISATION_AND_USAGE_STRATEGY.md triggers',
    'Stage-5 local Mac/tmux bridge — eight hard rules required',
    'Public production release — out of scope until production listing pass is done',
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
