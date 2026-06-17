/**
 * Data governance and consent types.
 *
 * Consent is versioned so future policy changes can be tracked.
 * Each flag is independent — users can opt into personal coaching
 * improvement without opting into de-identified research.
 *
 * CONSENT_VERSION should be bumped when the meaning of any flag
 * changes or new flags are added. Existing consents at older
 * versions remain valid for the flags they cover.
 */

export const CONSENT_VERSION = 1;

export interface DataConsent {
  /** Schema version — bump when consent meaning changes */
  version: number;

  /** When consent was last granted or updated */
  granted_at: string;

  /** When consent was last updated (may differ from granted_at on edits) */
  updated_at: string;

  /** Where consent was given */
  source: 'mobile_app' | 'website' | 'api';

  /**
   * Allow this data to improve MY personal coaching.
   * Required for the feedback loop to be useful.
   * Data stays in the user's account.
   */
  personal_coaching: boolean;

  /**
   * Allow de-identified data to improve global coaching models.
   * Data is stripped of user identity before use.
   * Opt-in only.
   */
  deidentified_models: boolean;

  /**
   * Allow aggregated, anonymous data for research/analytics.
   * No individual records are exposed.
   * Opt-in only.
   */
  analytics_research: boolean;

  /**
   * Has the user explicitly revoked all data-use consent?
   * When true, no training examples should be persisted or used.
   */
  revoked: boolean;
}

export const DEFAULT_CONSENT: DataConsent = {
  version: CONSENT_VERSION,
  granted_at: '',
  updated_at: '',
  source: 'mobile_app',
  personal_coaching: true,
  deidentified_models: false,
  analytics_research: false,
  revoked: false,
};

/**
 * Eligibility tags attached to each TrainingExample.
 * Determined at assembly time from the user's current consent state.
 */
export interface DataEligibility {
  /** User ID (for ownership, not for de-identified use) */
  user_id: string | null;

  /** Is this example eligible for personal coaching improvement? */
  training_eligible: boolean;

  /** Is this example eligible for de-identified global model training? */
  deidentified_eligible: boolean;

  /** Is this example eligible for research/analytics aggregation? */
  analytics_eligible: boolean;

  /** Consent version at time of tagging */
  consent_version: number;

  /** When eligibility was determined */
  tagged_at: string;
}

/**
 * Build eligibility tags from current consent state.
 */
export function buildEligibility(
  userId: string | null,
  consent: DataConsent,
): DataEligibility {
  return {
    user_id: userId,
    training_eligible: consent.personal_coaching && !consent.revoked,
    deidentified_eligible: consent.deidentified_models && !consent.revoked,
    analytics_eligible: consent.analytics_research && !consent.revoked,
    consent_version: consent.version,
    tagged_at: new Date().toISOString(),
  };
}
