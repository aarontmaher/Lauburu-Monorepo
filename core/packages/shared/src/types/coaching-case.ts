/**
 * Coaching case — a structured record of one "asked for a second opinion"
 * cycle: the app generated a prompt packet from current state, handed it
 * off to an external AI (today: ChatGPT via the native share sheet),
 * the user came back, and captured the outcome.
 *
 * This is the foundation for an eventual semi-automatic learning /
 * eval pipeline: every completed case is an (input_context →
 * prompt → outcome → usefulness) tuple that future work can use to
 * (a) surface patterns ("users repeatedly ask about protein on low-
 * recovery days"), (b) build rule candidates ("when recovery < 50
 * and protein < 60% of target, add 'eat a real meal first' to the
 * brief reasons"), (c) run offline evals against the deterministic
 * `buildDailyCoachingBrief` output to measure whether the app's
 * built-in reasoning would have produced the same advice.
 *
 * Deliberately simple: no chat log, no streaming state, no message
 * history. One case = one question + one outcome.
 */

/**
 * Where the case was handed off to. Reserved as a union so a future
 * in-app LLM path (Claude API, OpenAI API, on-device) can land under
 * the same shape without migrating existing cases.
 */
export type CoachingCaseSource =
  | 'external_chatgpt' // Native share sheet → ChatGPT app/web (today's default)
  | 'external_claude' // Native share sheet → Claude app/web (future)
  | 'external_other' // Any other share target the user picked
  | 'in_app_claude' // Future in-app Claude API call
  | 'in_app_openai'; // Future in-app OpenAI API call

/**
 * User's verdict after the case completes. Kept to three values so
 * the UI is a simple three-button row, not a free-form text field.
 * A future "Edit case" path can add notes, but the minimum usefulness
 * signal is one of these.
 */
export type CoachingCaseUsefulness = 'helped' | 'neutral' | 'unhelpful';

/**
 * Minimal snapshot of the app state that produced this case.
 * Captured at prompt-packet generation time so the case is
 * self-contained — future eval runs don't need to reconstruct
 * historical state from other stores.
 */
export interface CoachingCaseContext {
  /** ISO timestamp of when the packet was generated. */
  generated_at: string;
  /** Local date the case is attributed to (YYYY-MM-DD). */
  local_date: string;
  /**
   * WHOOP recovery score 0-100 if available at the moment of capture.
   * Null if no WHOOP data was present.
   */
  whoop_recovery?: number | null;
  /** WHOOP day strain if available. */
  whoop_strain?: number | null;
  /** Readiness level from the daily coaching brief. */
  readiness?: 'green' | 'yellow' | 'red' | 'grey';
  /** Plan hint string for today, if any. */
  plan_hint?: string | null;
  /** Number of enabled planned sessions for today. */
  planned_count?: number;
  /** Recent hard-session count in the last 3 days. */
  recent_hard?: number;
  /** Calories logged today so far, if any. */
  nutrition_calories?: number | null;
  /** Protein logged today so far, if any. */
  nutrition_protein_g?: number | null;
  /** Calorie target, if set. */
  nutrition_calorie_target?: number | null;
  /** Protein target, if set. */
  nutrition_protein_target?: number | null;
  /** Short free-text question/topic the user wanted advice on, if any. */
  user_question?: string | null;
}

/** A case the user has started but not yet completed (awaiting outcome). */
export interface CoachingCaseDraft {
  id: string;
  context: CoachingCaseContext;
  /** Rendered prompt packet text that was shared. */
  prompt_packet: string;
  /** Where the case was handed off. */
  source: CoachingCaseSource;
  /** ISO timestamp when the share/handoff fired. */
  shared_at: string;
}

/** A completed case with an outcome attached. */
export interface CoachingCase extends CoachingCaseDraft {
  completed_at: string;
  usefulness: CoachingCaseUsefulness;
  /** What the AI (or user) ended up recommending, free text, optional. */
  outcome_summary?: string;
  /** Did the user end up following the advice? */
  followed?: boolean;
}

/**
 * Exportable JSONL shape for future eval pipelines. Each line is one
 * completed case, newline-delimited. Future work can read this format
 * directly into an offline eval harness without touching the store.
 */
export interface CoachingCaseExportLine {
  id: string;
  generated_at: string;
  local_date: string;
  source: CoachingCaseSource;
  context: CoachingCaseContext;
  prompt_packet: string;
  completed_at: string;
  usefulness: CoachingCaseUsefulness;
  outcome_summary?: string;
  followed?: boolean;
}
