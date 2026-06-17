import type { AppAthleteState } from './app-athlete-state';

export type HomeWidgetPlatform = 'ios' | 'android';
export type HomeWidgetActionId = 'train' | 'recover' | 'journal' | 'connect_health' | 'review';
export type HomeWidgetHealthSourceStatus = 'connected' | 'missing' | 'stale';
export type HomeWidgetTruthLabel = 'fresh' | 'stale' | 'missing' | 'provisional';

export interface HomeWidgetQuickAction {
  id: 'start_journal' | 'open_timer' | 'view_readiness';
  label: string;
  route: string;
}

export interface HomeWidgetContext {
  schemaVersion: 1;
  date: string;
  platform: HomeWidgetPlatform;
  readiness: {
    label: string;
    band: AppAthleteState['recovery_context']['band'];
    score: number | null;
    confidence: AppAthleteState['readiness_confidence']['level'];
    truthLabel: HomeWidgetTruthLabel;
    note: string;
  };
  nextAction: {
    id: HomeWidgetActionId;
    label: string;
    route: string;
  };
  healthSource: {
    source: 'apple_health' | 'health_connect';
    label: 'Apple Health' | 'Health Connect';
    status: HomeWidgetHealthSourceStatus;
    truthLabel: HomeWidgetTruthLabel;
    freshnessHours: number | null;
  };
  quickActions: HomeWidgetQuickAction[];
  safety: {
    productMcpSafe: true;
    includesDeveloperMcpData: false;
    noStrongReadinessClaim: boolean;
  };
}

const NATIVE_HEALTH_STALE_HOURS = 24;

const QUICK_ACTIONS: HomeWidgetQuickAction[] = [
  { id: 'start_journal', label: 'Journal', route: '/(tabs)/feedback' },
  { id: 'open_timer', label: 'Timer', route: '/timer' },
  { id: 'view_readiness', label: 'Readiness', route: '/(tabs)/health' },
];

function platformHealthSource(platform: HomeWidgetPlatform): HomeWidgetContext['healthSource']['source'] {
  return platform === 'ios' ? 'apple_health' : 'health_connect';
}

function platformHealthLabel(platform: HomeWidgetPlatform): HomeWidgetContext['healthSource']['label'] {
  return platform === 'ios' ? 'Apple Health' : 'Health Connect';
}

function sourceStatus(state: AppAthleteState): HomeWidgetHealthSourceStatus {
  const native = state.source_roles.native_health;
  const freshness = state.data_quality.freshness_hours.native_health;
  if (native.role !== 'broad_baseline') return 'missing';
  if (freshness == null) return 'missing';
  if (freshness > NATIVE_HEALTH_STALE_HOURS) return 'stale';
  return 'connected';
}

function readinessTruthLabel(state: AppAthleteState, healthStatus: HomeWidgetHealthSourceStatus): HomeWidgetTruthLabel {
  if (healthStatus === 'missing') return 'missing';
  if (healthStatus === 'stale') return 'stale';
  if (state.readiness_confidence.level !== 'high' || state.provisional.seed_mode) return 'provisional';
  return 'fresh';
}

function readinessLabel(state: AppAthleteState, truthLabel: HomeWidgetTruthLabel): string {
  if (truthLabel === 'missing') return 'Readiness needs data';
  if (truthLabel === 'stale') return 'Readiness stale';
  const band = state.recovery_context.band;
  if (band === 'unknown') return 'Readiness provisional';
  return truthLabel === 'fresh'
    ? `Readiness ${band}`
    : `Provisional ${band}`;
}

function readinessScore(state: AppAthleteState, truthLabel: HomeWidgetTruthLabel): number | null {
  if (truthLabel !== 'fresh') return null;
  return state.recovery_context.score_0_100;
}

function nextActionFor(state: AppAthleteState, healthStatus: HomeWidgetHealthSourceStatus): HomeWidgetContext['nextAction'] {
  if (healthStatus === 'missing') {
    return { id: 'connect_health', label: 'Connect health', route: '/(tabs)/health' };
  }
  if (state.readiness_confidence.level === 'low') {
    return { id: 'journal', label: 'Start journal', route: '/(tabs)/feedback' };
  }
  if (state.recovery_context.band === 'low' || state.acute_fatigue.band === 'high') {
    return { id: 'recover', label: 'Review recovery', route: '/(tabs)/health' };
  }
  if (state.load_context.sessions_7d === 0 || state.load_context.band === 'under') {
    return { id: 'train', label: 'Open timer', route: '/timer' };
  }
  return { id: 'review', label: 'View readiness', route: '/(tabs)/health' };
}

export function buildHomeWidgetContext(input: {
  platform: HomeWidgetPlatform;
  state: AppAthleteState;
}): HomeWidgetContext {
  const healthStatus = sourceStatus(input.state);
  const healthTruth: HomeWidgetTruthLabel = healthStatus === 'connected' ? 'fresh' : healthStatus;
  const rTruth = readinessTruthLabel(input.state, healthStatus);
  return {
    schemaVersion: 1,
    date: input.state.date,
    platform: input.platform,
    readiness: {
      label: readinessLabel(input.state, rTruth),
      band: input.state.recovery_context.band,
      score: readinessScore(input.state, rTruth),
      confidence: input.state.readiness_confidence.level,
      truthLabel: rTruth,
      note: input.state.recovery_context.note,
    },
    nextAction: nextActionFor(input.state, healthStatus),
    healthSource: {
      source: platformHealthSource(input.platform),
      label: platformHealthLabel(input.platform),
      status: healthStatus,
      truthLabel: healthTruth,
      freshnessHours: input.state.data_quality.freshness_hours.native_health,
    },
    quickActions: QUICK_ACTIONS,
    safety: {
      productMcpSafe: true,
      includesDeveloperMcpData: false,
      noStrongReadinessClaim: rTruth !== 'fresh',
    },
  };
}
