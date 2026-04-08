/**
 * Subscription tiers and capability model.
 *
 * Design principles:
 * - Free tier = zero marginal cost features only
 * - Low-cost tier = controlled-cost features (sync, export)
 * - Pro = BYO AI, advanced features
 * - AI Premium = hosted inference, model training participation
 * - No expensive path is accidentally exposed in lower tiers
 * - Real billing is NOT implemented — this is gating architecture only
 */

export type Tier = 'free' | 'low_cost' | 'pro' | 'ai_premium';

export type Capability =
  // Free tier (zero cost)
  | 'local_coaching'
  | 'manual_training_log'
  | 'feedback_capture'
  | 'local_health_view'
  | 'basic_insights'
  // Low-cost tier (controlled cost)
  | 'health_sync'
  | 'backend_persistence'
  | 'export_ai_payload'
  | 'preference_coaching'
  | 'training_history'
  // Pro tier
  | 'byo_ai'
  | 'advanced_reports'
  | 'cronometer_sync'
  | 'ergzone_sync'
  | 'data_export_full'
  | 'model_training_participation'
  // AI Premium tier
  | 'hosted_ai_coaching'
  | 'daily_ai_recommendations'
  | 'advanced_ai_insights'
  | 'priority_model_training';

/** Which capabilities each tier includes (cumulative) */
const TIER_CAPABILITIES: Record<Tier, Capability[]> = {
  free: [
    'local_coaching',
    'manual_training_log',
    'feedback_capture',
    'local_health_view',
    'basic_insights',
  ],
  low_cost: [
    // Includes all free
    'local_coaching',
    'manual_training_log',
    'feedback_capture',
    'local_health_view',
    'basic_insights',
    // Plus
    'health_sync',
    'backend_persistence',
    'export_ai_payload',
    'preference_coaching',
    'training_history',
  ],
  pro: [
    // Includes all low_cost
    'local_coaching',
    'manual_training_log',
    'feedback_capture',
    'local_health_view',
    'basic_insights',
    'health_sync',
    'backend_persistence',
    'export_ai_payload',
    'preference_coaching',
    'training_history',
    // Plus
    'byo_ai',
    'advanced_reports',
    'cronometer_sync',
    'ergzone_sync',
    'data_export_full',
    'model_training_participation',
  ],
  ai_premium: [
    // Includes all pro
    'local_coaching',
    'manual_training_log',
    'feedback_capture',
    'local_health_view',
    'basic_insights',
    'health_sync',
    'backend_persistence',
    'export_ai_payload',
    'preference_coaching',
    'training_history',
    'byo_ai',
    'advanced_reports',
    'cronometer_sync',
    'ergzone_sync',
    'data_export_full',
    'model_training_participation',
    // Plus
    'hosted_ai_coaching',
    'daily_ai_recommendations',
    'advanced_ai_insights',
    'priority_model_training',
  ],
};

/** Check if a tier has a capability */
export function tierHasCapability(tier: Tier, cap: Capability): boolean {
  return TIER_CAPABILITIES[tier]?.includes(cap) ?? false;
}

/** Get all capabilities for a tier */
export function getTierCapabilities(tier: Tier): Capability[] {
  return TIER_CAPABILITIES[tier] ?? [];
}

/** Get the minimum tier required for a capability */
export function minimumTierFor(cap: Capability): Tier {
  const order: Tier[] = ['free', 'low_cost', 'pro', 'ai_premium'];
  for (const tier of order) {
    if (TIER_CAPABILITIES[tier].includes(cap)) return tier;
  }
  return 'ai_premium';
}

/** Tier display info */
export const TIER_INFO: Record<Tier, { label: string; color: string }> = {
  free: { label: 'Free', color: '#999' },
  low_cost: { label: 'Starter', color: '#e8ff47' },
  pro: { label: 'Pro', color: '#4ade80' },
  ai_premium: { label: 'AI Premium', color: '#a78bfa' },
};

/** Capability display info */
export const CAPABILITY_INFO: Record<Capability, { label: string; description: string }> = {
  local_coaching: { label: 'Local Coaching', description: 'Rules-based training guidance' },
  manual_training_log: { label: 'Training Log', description: 'Manual session entry' },
  feedback_capture: { label: 'Check-in', description: 'Daily feedback capture' },
  local_health_view: { label: 'Health View', description: 'View health metrics locally' },
  basic_insights: { label: 'Basic Insights', description: 'Flags and trends' },
  health_sync: { label: 'Health Sync', description: 'HealthKit / Health Connect sync' },
  backend_persistence: { label: 'Cloud Sync', description: 'Persist data to your account' },
  export_ai_payload: { label: 'AI Export', description: 'Export AI-ready payloads' },
  preference_coaching: { label: 'Preference Coaching', description: 'Personalized coaching preferences' },
  training_history: { label: 'Training History', description: 'Full session history' },
  byo_ai: { label: 'BYO AI', description: 'Bring your own AI model/key' },
  advanced_reports: { label: 'Advanced Reports', description: 'Detailed trend analysis' },
  cronometer_sync: { label: 'Cronometer', description: 'Nutrition data sync' },
  ergzone_sync: { label: 'ErgZone', description: 'Detailed workout data sync' },
  data_export_full: { label: 'Full Export', description: 'Export all training data' },
  model_training_participation: { label: 'Model Training', description: 'Contribute to model improvement' },
  hosted_ai_coaching: { label: 'AI Coaching', description: 'Server-side AI coaching' },
  daily_ai_recommendations: { label: 'Daily AI', description: 'Daily AI recommendations' },
  advanced_ai_insights: { label: 'AI Insights', description: 'Deep AI-powered analysis' },
  priority_model_training: { label: 'Priority Training', description: 'Priority model personalization' },
};
