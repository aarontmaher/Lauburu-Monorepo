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
    'MCP connector consistency + Admin/Dev iPhone control centre.',
  currentBlocker:
    'Phone verification is still pending for live MCP status, lane summary, copy prompts, and stale/fallback states.',
  lastStatus: [
    'Cloudflare/Supabase MCP foundation exists; mobile Admin/Dev consumes the Worker through EXPO_PUBLIC_MCP_BASE_URL.',
    'Recent Admin/Dev phone patches added first-screen MCP status, lane summary, build/repo summary, and copy prompts.',
    'Health/Data Source reliability remains the next product lane after MCP/control-centre phone verification.',
    'Verified: mobile typecheck passed for the latest Admin/Dev lane.',
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
    'No backend, Cloudflare, Supabase, MCP auth, or health-source rewrites from this mobile lane',
    'Use predefined GitHub Actions workflows only after owner confirmation',
  ],
  manualStepsForAaron: [
    'Install the next paired tester build on iPhone and open Admin/Dev.',
    'Confirm MCP shows Live MCP data, Stale snapshot, Fallback placeholder, Repo-only, or error language correctly.',
    'Confirm Copy Claude prompt, Copy Codex prompt, Copy Agent audit prompt, and Copy handoff summary are usable from the phone.',
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
    'MCP connector consistency across private /mcp, public /mcp/public, REST /api/*, docs, tests, and mobile consumer',
    'Admin/Dev iPhone control centre device verification',
    'App live MCP consumer tester-build verification',
    'Feedback suggestions approval workflow',
    'Health/Data Source reliability: Apple Health on iOS and Health Connect on Android',
    'Grappler Readiness architecture only — no user-facing UI',
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
