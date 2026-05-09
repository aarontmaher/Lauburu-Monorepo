/**
 * Home screen actionable top slot — pure selection helper.
 *
 * Contract spec: `docs/HOME_SCREEN_ACTIONABILITY_SPEC.md`.
 *
 * Anti-rules baked in:
 *
 * - No medical advice copy. Action labels are functional verb-
 *   noun only; the helper rejects anything that contains
 *   directive readiness or training-prescription language.
 * - No fabricated next-action. Returns null when no
 *   high-leverage action is computable from the inputs.
 * - No causation language at the data layer.
 * - No EAS / TestFlight / Play / production release surface
 *   reachable from any returned action.
 *
 * The helper is pure: no React imports, no clock side effects
 * (caller injects `nowMs`), no native modules. Tested by
 * `cloudflare-worker/test/test-home-top-action-selection.ts`.
 */

import type { TruthLabel } from '../components/primitives/_helpers';
import type { ConfidenceLevel } from '../components/primitives/_helpers';

export interface HomeTopActionInput {
  /**
   * Per-source health truth states. Sources whose state is
   * `'setup required'` AND that the user has previously
   * connected (i.e. `previouslyConnected: true`) win precedence
   * rule #1 — relink.
   */
  sources: ReadonlyArray<{
    id: string;
    label: string;
    sourceState: TruthLabel;
    previouslyConnected: boolean;
  }>;
  /** True iff the user has a training session scheduled for the local "today". */
  todaySessionScheduled: boolean;
  /**
   * Wall-clock ms of the last time the user opened the Train
   * tab, or null if never. Drives precedence rule #2.
   */
  lastPlanOpenAtMs: number | null;
  /**
   * Wall-clock ms used to evaluate "after noon local time"
   * checks. Caller injects so tests stay deterministic.
   */
  nowMs: number;
  /** True iff the user has logged any nutrition entry for today. */
  fuelLoggedToday: boolean;
  /** Count of un-captured "Ask ChatGPT" coaching follow-up drafts. */
  pendingFollowupCount: number;
  /** Readiness compute confidence; null when readiness has not been computed yet. */
  readinessConfidence: ConfidenceLevel | null;
  /**
   * Local hour-of-day (0..23). Caller derives from
   * `new Date().getHours()` at the call site so the helper
   * stays pure. Used for the "before noon" check on rule #3.
   */
  localHour: number;
}

export interface HomeTopActionOutput {
  label: string;
  detail: string;
  routeOrAction: string;
  confidence: ConfidenceLevel;
  dismissible: boolean;
  /** Identifier for telemetry / dedupe — never user-visible. */
  precedenceRule: 'setup_required' | 'todays_plan' | 'log_fuel' | 'pending_followup';
}

/** 12 hours, ms — drives precedence rule #2's "not opened recently" check. */
const TWELVE_HOURS_MS = 12 * 60 * 60 * 1000;

const BANNED_LABEL_PATTERNS: ReadonlyArray<RegExp> = [
  /\b(rest|skip|push harder|train harder|recover|recovered|fatigued|overtrained|under-?trained)\b/i,
  /\b(diagnos(?:e|es|is|tic)|clinical(?:ly)?|treats?|cures?)\b/i,
  /\b(this caused|caused by)\b/i,
];

function refusesBannedCopy(label: string, detail: string): boolean {
  const combined = `${label} ${detail}`;
  return BANNED_LABEL_PATTERNS.some((p) => p.test(combined));
}

/**
 * Defence-in-depth: every action this helper returns is checked
 * against the banned-copy patterns before it leaves the helper.
 * If a future maintainer adds a directive label, the helper
 * returns null rather than emitting it.
 */
function safeOutput(output: HomeTopActionOutput): HomeTopActionOutput | null {
  if (refusesBannedCopy(output.label, output.detail)) return null;
  return output;
}

export function selectTopAction(
  input: HomeTopActionInput,
): HomeTopActionOutput | null {
  // Precedence rule #4: pending coaching follow-up wins over
  // every fuel/log item because the user explicitly asked for
  // it. Surfaced FIRST so it never gets buried.
  if (input.pendingFollowupCount > 0) {
    return safeOutput({
      label: 'Open follow-up',
      detail: `${input.pendingFollowupCount} unfinished coaching draft${input.pendingFollowupCount === 1 ? '' : 's'} ready to capture.`,
      routeOrAction: '/(tabs)/feedback',
      confidence: input.readinessConfidence ?? 'unknown',
      dismissible: false,
      precedenceRule: 'pending_followup',
    });
  }

  // Precedence rule #1: setup-required blocker on a previously-
  // connected source. A missing source is more actionable than
  // starting a session blind.
  const blocker = input.sources.find(
    (s) => s.sourceState === 'setup required' && s.previouslyConnected === true,
  );
  if (blocker) {
    return safeOutput({
      label: `Reconnect ${blocker.label}`,
      detail: 'A previously connected source needs setup again.',
      routeOrAction: '/(tabs)/health',
      confidence: input.readinessConfidence ?? 'unknown',
      dismissible: false,
      precedenceRule: 'setup_required',
    });
  }

  // Precedence rule #2: today's session not opened in the last 12h.
  if (input.todaySessionScheduled) {
    const noOpenYet = input.lastPlanOpenAtMs == null;
    const stalePlanOpen = input.lastPlanOpenAtMs != null
      && input.nowMs - input.lastPlanOpenAtMs > TWELVE_HOURS_MS;
    if (noOpenYet || stalePlanOpen) {
      return safeOutput({
        label: "Open today's plan",
        detail: 'A session is scheduled — review it before training.',
        routeOrAction: '/(tabs)/train',
        confidence: input.readinessConfidence ?? 'unknown',
        dismissible: true,
        precedenceRule: 'todays_plan',
      });
    }
  }

  // Precedence rule #3: fuel not logged before local noon.
  if (input.localHour >= 12 && !input.fuelLoggedToday) {
    return safeOutput({
      label: 'Log fuel',
      detail: 'No nutrition entries for today yet.',
      routeOrAction: '/(tabs)/feedback',
      confidence: input.readinessConfidence ?? 'unknown',
      dismissible: true,
      precedenceRule: 'log_fuel',
    });
  }

  // No high-leverage action — UI renders the literal "Nothing
  // scheduled" copy from the spec. Anti-rule: never invent.
  return null;
}

/** Public placeholder copy for the empty slot. UI uses this verbatim. */
export const HOME_TOP_ACTION_EMPTY_COPY =
  'Nothing scheduled — when ready, train or log a session.';
