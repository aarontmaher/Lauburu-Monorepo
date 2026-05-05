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
    'Fix Play Console listing-pass metadata gap so future Android dispatches can land releaseStatus=completed.',
  currentBlocker:
    'Run 25349253529 FAILED at the submit step. Play API: "The app is missing the required metadata to submit the app to Google Play Store." Aaron-side fix only — Data safety / Content rating / Target audience / Health Connect declaration likely incomplete.',
  lastStatus: [
    'Android proof FAILED at submit step. EAS build succeeded (AAB to6EtkZB68rBopsR9JNYMV.aab); Play API auth OK; Play rejected COMPLETED release for missing metadata.',
    'iOS Build 15 + TestFlight submit SUCCEEDED (run 25349256198).',
    'iOS HealthKit Mac/Vision warning fix shipped on Build 15. Owner FAB rule + Admin/Dev redesign also live on Build 15.',
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
    'iOS Build 15: SUCCEEDED — accept the TestFlight update prompt to install Build 15 on Aaron\'s device',
    'Android: open Play Console → Lauburu → Dashboard or Internal testing for the v14 draft, look for any red/amber "complete this section" prompt',
    'Most likely missing: Data safety final save, Content rating final save, Target audience final save, Health Connect declaration final save — Aaron may have started but not committed each questionnaire',
    'Once each remaining listing-pass questionnaire shows "Saved" / "Complete", reply "play listing fully complete" so I can re-dispatch the Android workflow once',
    'Do NOT re-dispatch the Android workflow yet — it will fail the same way until the metadata gap is closed',
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
