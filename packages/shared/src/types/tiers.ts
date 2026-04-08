/**
 * Subscription tiers and capability model.
 *
 * Business rules (NON-NEGOTIABLE):
 * 1. Free = ONLY zero/near-zero marginal cost features
 *    - Must not trigger meaningful backend/inference cost
 *    - May include features that help data collection (retention + training data)
 * 2. Low-cost = low but real cost (storage, sync, cloud processing)
 *    - We must not lose money at this tier
 * 3. Pro = BYO AI + richer third-party integrations
 *    - Variable cost, controlled by user's own API keys
 * 4. AI Premium = hosted inference + expensive intelligence
 *    - Only tier that triggers our inference spend
 * 5. We must not lose money at any tier
 *
 * Cost audit per capability:
 * - local_* / basic_*        → client-side only, zero cost          → FREE
 * - health_sync              → on-device HealthKit/HC, zero cost    → FREE
 * - preference_coaching      → local rules engine, zero cost        → FREE
 * - feedback/training data   → local Zustand, zero cost             → FREE
 * - model_training_participation → consent flag only, zero cost     → FREE
 * - backend_persistence      → Supabase storage + MCP writes       → LOW_COST
 * - training_history (cloud) → Supabase reads, small cost           → LOW_COST
 * - export_ai_payload        → requires backend context             → LOW_COST
 * - byo_ai                   → user pays their own inference        → PRO
 * - cronometer/ergzone       → third-party API integration cost     → PRO
 * - hosted_ai_*              → our inference spend                  → AI_PREMIUM
 */

export type Tier = 'free' | 'low_cost' | 'pro' | 'ai_premium';

export type Capability =
  // Free tier — zero marginal cost, drives retention + data collection
  | 'local_coaching'
  | 'manual_training_log'
  | 'feedback_capture'
  | 'local_health_view'
  | 'basic_insights'
  | 'health_sync'            // on-device only, no backend cost
  | 'preference_coaching'    // local rules, no backend cost
  | 'model_training_participation' // consent flag only
  // Low-cost tier — real but controlled backend cost
  | 'backend_persistence'
  | 'export_ai_payload'
  | 'training_history'       // cloud history reads
  // Pro tier — user-funded integrations
  | 'byo_ai'
  | 'advanced_reports'
  | 'cronometer_sync'
  | 'ergzone_sync'
  | 'data_export_full'
  // AI Premium tier — our inference spend
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
    'health_sync',
    'preference_coaching',
    'model_training_participation',
  ],
  low_cost: [
    // All free
    'local_coaching',
    'manual_training_log',
    'feedback_capture',
    'local_health_view',
    'basic_insights',
    'health_sync',
    'preference_coaching',
    'model_training_participation',
    // Plus: backend cost features
    'backend_persistence',
    'export_ai_payload',
    'training_history',
  ],
  pro: [
    // All low_cost
    'local_coaching',
    'manual_training_log',
    'feedback_capture',
    'local_health_view',
    'basic_insights',
    'health_sync',
    'preference_coaching',
    'model_training_participation',
    'backend_persistence',
    'export_ai_payload',
    'training_history',
    // Plus: user-funded integrations
    'byo_ai',
    'advanced_reports',
    'cronometer_sync',
    'ergzone_sync',
    'data_export_full',
  ],
  ai_premium: [
    // All pro
    'local_coaching',
    'manual_training_log',
    'feedback_capture',
    'local_health_view',
    'basic_insights',
    'health_sync',
    'preference_coaching',
    'model_training_participation',
    'backend_persistence',
    'export_ai_payload',
    'training_history',
    'byo_ai',
    'advanced_reports',
    'cronometer_sync',
    'ergzone_sync',
    'data_export_full',
    // Plus: our inference spend
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
export const TIER_INFO: Record<Tier, { label: string; color: string; price: string }> = {
  free: { label: 'Free', color: '#999', price: 'Free' },
  low_cost: { label: 'Starter', color: '#e8ff47', price: 'Low cost' },
  pro: { label: 'Pro', color: '#4ade80', price: 'Monthly' },
  ai_premium: { label: 'AI Premium', color: '#a78bfa', price: 'Premium' },
};

/** Capability display info with cost rationale */
export const CAPABILITY_INFO: Record<Capability, {
  label: string;
  description: string;
  cost_note: string;
}> = {
  // Free
  local_coaching: { label: 'Local Coaching', description: 'Rules-based training guidance', cost_note: 'Runs on device' },
  manual_training_log: { label: 'Training Log', description: 'Manual session entry', cost_note: 'Local storage' },
  feedback_capture: { label: 'Check-in', description: 'Daily feedback capture', cost_note: 'Local storage' },
  local_health_view: { label: 'Health View', description: 'View health metrics', cost_note: 'On-device data' },
  basic_insights: { label: 'Basic Insights', description: 'Flags and trends', cost_note: 'Local computation' },
  health_sync: { label: 'Health Sync', description: 'HealthKit / Health Connect', cost_note: 'On-device API' },
  preference_coaching: { label: 'Personalized Rules', description: 'Preference-aware coaching', cost_note: 'Local rules engine' },
  model_training_participation: { label: 'Help Improve', description: 'Consent to improve coaching', cost_note: 'Consent flag only' },
  // Low-cost
  backend_persistence: { label: 'Cloud Sync', description: 'Save data to your account', cost_note: 'Backend storage' },
  export_ai_payload: { label: 'AI Export', description: 'Export coaching payloads', cost_note: 'Backend context' },
  training_history: { label: 'Full History', description: 'Cloud training history', cost_note: 'Backend reads' },
  // Pro
  byo_ai: { label: 'BYO AI', description: 'Use your own AI model', cost_note: 'Your API key' },
  advanced_reports: { label: 'Advanced Reports', description: 'Detailed analysis', cost_note: 'Backend processing' },
  cronometer_sync: { label: 'Cronometer', description: 'Nutrition data sync', cost_note: 'Third-party API' },
  ergzone_sync: { label: 'ErgZone', description: 'Workout detail sync', cost_note: 'Third-party API' },
  data_export_full: { label: 'Full Export', description: 'Export all data', cost_note: 'Backend processing' },
  // AI Premium
  hosted_ai_coaching: { label: 'AI Coaching', description: 'Server-side AI', cost_note: 'Our inference cost' },
  daily_ai_recommendations: { label: 'Daily AI', description: 'AI recommendations', cost_note: 'Our inference cost' },
  advanced_ai_insights: { label: 'AI Insights', description: 'Deep AI analysis', cost_note: 'Our inference cost' },
  priority_model_training: { label: 'Priority AI', description: 'Priority personalization', cost_note: 'Our compute cost' },
};
