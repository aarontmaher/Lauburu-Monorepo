/**
 * User coaching preferences — seed for future personalization.
 *
 * These preferences shape coaching output without requiring model training.
 * They provide the initial personalization axis; the feedback loop data
 * will eventually allow model-based personalization on top.
 */

export interface CoachingPreferences {
  /** How conservative should recovery recommendations be? */
  recovery_conservatism: 'conservative' | 'moderate' | 'aggressive';

  /** Preferred coaching tone */
  tone: 'direct' | 'encouraging' | 'analytical';

  /** Are you in competition prep mode? Affects load thresholds. */
  comp_prep: boolean;

  /** Bias toward training even when signals are mixed? */
  hard_day_bias: 'train_through' | 'balanced' | 'err_on_rest';

  /** Primary training goal */
  goal: 'general_fitness' | 'competition' | 'skill_development' | 'weight_management';

  /** Typical training days per week (for consistency assessment) */
  target_sessions_per_week: number;
}

export const DEFAULT_PREFERENCES: CoachingPreferences = {
  recovery_conservatism: 'moderate',
  tone: 'direct',
  comp_prep: false,
  hard_day_bias: 'balanced',
  goal: 'skill_development',
  target_sessions_per_week: 4,
};
