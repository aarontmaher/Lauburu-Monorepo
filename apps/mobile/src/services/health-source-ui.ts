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
    ? { label: 'Polar Direct connected', state: 'connected' }
    : { label: 'Polar Direct setup needed', state: 'setup_required' };
}

export function getReadinessSeedBadge(input: {
  hasLiveWhoopRecovery: boolean;
  confidenceLevel?: string | null;
}): { label: 'Seed' | 'Live'; note: string; provisional: boolean } {
  if (input.hasLiveWhoopRecovery) {
    return {
      label: 'Live',
      note: 'Includes live WHOOP Direct recovery when available. Still app-owned, not a vendor score.',
      provisional: false,
    };
  }
  const confidence = input.confidenceLevel ? `${input.confidenceLevel} confidence` : 'directional';
  return {
    label: 'Seed',
    note: `Provisional ${confidence}. Connect live sources before treating readiness as a strong signal.`,
    provisional: true,
  };
}
