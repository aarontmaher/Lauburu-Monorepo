export type MobilePlatform = 'ios' | 'android' | 'web' | 'windows' | 'macos';

export interface NativeHealthSourceCopy {
  sourceName: string;
  shortName: string;
  hubLabel: string;
  dataKind: string;
}

export function getNativeHealthSourceCopy(platform: MobilePlatform | string): NativeHealthSourceCopy {
  if (platform === 'ios') {
    return {
      sourceName: 'Apple Health / HealthKit',
      shortName: 'Apple Health',
      hubLabel: 'Apple Health / HealthKit hub data',
      dataKind: 'hub',
    };
  }
  return {
    sourceName: 'Health Connect',
    shortName: 'Health Connect',
    hubLabel: 'Health Connect hub data',
    dataKind: 'hub',
  };
}

export type DirectIntegrationState =
  | 'connected'
  | 'partial'
  | 'awaiting_cycle'
  | 'stale'
  | 'reconnect_required'
  | 'setup_required'
  | 'not_connected'
  | 'unknown';

export function getWhoopDirectStateLabel(state: string, opts: { awaitingCycle?: boolean; stale?: boolean } = {}): {
  label: string;
  state: DirectIntegrationState;
} {
  if (opts.stale) return { label: 'WHOOP Direct stale', state: 'stale' };
  if (opts.awaitingCycle) return { label: 'WHOOP Direct awaiting cycle', state: 'awaiting_cycle' };
  if (state === 'connected') return { label: 'WHOOP Direct connected', state: 'connected' };
  if (state === 'partial') return { label: 'WHOOP Direct partial', state: 'partial' };
  if (state === 'error') return { label: 'WHOOP Direct reconnect needed', state: 'reconnect_required' };
  if (state === 'config_missing') return { label: 'WHOOP Direct setup needed', state: 'setup_required' };
  if (state === 'auth_required' || state === 'disconnected') return { label: 'WHOOP Direct not connected', state: 'not_connected' };
  return { label: 'WHOOP Direct setup needed', state: 'setup_required' };
}

export function getPolarDirectStateLabel(connected: boolean): { label: string; state: DirectIntegrationState } {
  return connected
    ? { label: 'Polar AccessLink connected', state: 'connected' }
    : { label: 'Polar AccessLink planned', state: 'setup_required' };
}

export function getReadinessSeedBadge(input: {
  hasLiveWhoopRecovery: boolean;
  confidenceLevel?: string | null;
}): { label: 'Seed' | 'Live'; note: string; provisional: boolean } {
  if (input.hasLiveWhoopRecovery) {
    return {
      label: 'Live',
      note: 'Includes verified WHOOP Direct recovery when available. Still app-owned, not a vendor score.',
      provisional: false,
    };
  }
  const confidence = input.confidenceLevel ? `${input.confidenceLevel} confidence` : 'directional';
  return {
    label: 'Seed',
    note: `Provisional ${confidence}. Connect verified sources before relying on readiness.`,
    provisional: true,
  };
}

export type ReadinessConfidenceLevel = 'low' | 'medium' | 'high';

export interface HubReadinessEvidenceInput {
  platform: MobilePlatform | string;
  fields: {
    hrv?: number | null;
    restingHr?: number | null;
    sleepHours?: number | null;
    activeCalories?: number | null;
    steps?: number | null;
    workouts?: number | null;
  };
  insufficientHistory?: boolean;
  missing?: {
    hrv?: boolean;
    restingHr?: boolean;
    sleep?: boolean;
    strain?: boolean;
    workoutDetail?: boolean;
  };
  provenance?: string[];
  polarHubDetected?: boolean;
  samsungHubDetected?: boolean;
  manualSessionData?: boolean;
  journalContext?: boolean;
}

export interface HubReadinessEvidence {
  confidence: ReadinessConfidenceLevel;
  label: string;
  note: string;
  sourceLabels: string[];
  inputLabels: string[];
  missingLabels: string[];
}

export function buildHubReadinessEvidence(input: HubReadinessEvidenceInput): HubReadinessEvidence {
  const nativeCopy = getNativeHealthSourceCopy(input.platform);
  const sourceLabels = [nativeCopy.hubLabel];
  const provenance = input.provenance ?? [];
  const hasProvenance = (pattern: RegExp) => provenance.some((source) => pattern.test(source));

  if (input.polarHubDetected || hasProvenance(/polar/i)) {
    sourceLabels.push(`Polar via ${nativeCopy.shortName}`);
  }
  if (input.samsungHubDetected || hasProvenance(/samsung/i)) {
    sourceLabels.push(`Samsung Health via ${nativeCopy.shortName}`);
  }
  if (input.manualSessionData) {
    sourceLabels.push('Manual / logged training');
  }
  if (input.journalContext) {
    sourceLabels.push('Daily journal');
  }

  const inputLabels: string[] = [];
  const missingLabels = new Set<string>();
  const fields = input.fields;

  if (fields.sleepHours != null) inputLabels.push('sleep');
  else missingLabels.add('sleep');

  if (fields.hrv != null) inputLabels.push('HRV');
  else if (input.missing?.hrv !== false) missingLabels.add('HRV');

  if (fields.restingHr != null) inputLabels.push('resting HR');
  else if (input.missing?.restingHr !== false) missingLabels.add('resting HR');

  if (fields.activeCalories != null || fields.steps != null) inputLabels.push('activity');
  else missingLabels.add('activity');

  if ((fields.workouts ?? 0) > 0 || input.manualSessionData) inputLabels.push('training log');
  else if (input.missing?.workoutDetail !== false) missingLabels.add('training log');

  if (input.journalContext) {
    inputLabels.push('subjective check-in');
  } else {
    missingLabels.add('journal');
  }

  if (input.missing?.strain) {
    missingLabels.add('direct strain');
  }
  if (input.insufficientHistory) {
    missingLabels.add('history baseline');
  }

  const signalCount = inputLabels.length;
  let confidence: ReadinessConfidenceLevel = 'low';
  if (signalCount >= 4 && !input.insufficientHistory) confidence = 'high';
  else if (signalCount >= 3) confidence = 'medium';

  const label = `${confidence[0].toUpperCase()}${confidence.slice(1)} confidence`;
  const note =
    confidence === 'high'
      ? 'Hub-fed readiness has several current inputs, but remains provisional.'
      : confidence === 'medium'
        ? 'Hub-fed readiness has useful inputs, with some missing fields.'
        : 'Hub-fed readiness is a light signal until more metrics sync.';

  return {
    confidence,
    label,
    note,
    sourceLabels: [...new Set(sourceLabels)],
    inputLabels,
    missingLabels: Array.from(missingLabels),
  };
}
