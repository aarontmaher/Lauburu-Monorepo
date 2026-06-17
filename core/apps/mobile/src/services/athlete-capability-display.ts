export type SeedBackendStatus =
  | 'checking_backend'
  | 'seed_backend'
  | 'fresh_seed_backend'
  | 'stale_seed_backend'
  | 'degraded_backend';

export type AthleteCapabilityMode =
  | 'seed'
  | 'missing_whoop_native'
  | 'partial_confidence'
  | 'provisional'
  | 'live_ready';

export const ATHLETE_CAPABILITY_COPY = {
  whoopSourceLabel: 'WHOOP reference',
  backendSnapshotLabel: 'optional calibration source',
  seedSuggestionLabel: 'Provisional suggestion',
  todaySeedSuggestionLabel: "Today's provisional suggestion",
  provisionalBackendNote:
    'Provisional readiness — refines as Apple Health, training, nutrition, and imported history accumulate.',
  partialConfidenceNote:
    'Treat as provisional readiness, not WHOOP-native recovery.',
  provisionalLoadNote:
    'Use this as a provisional nudge, not a full recovery-vs-load interpretation.',
  missingWhoopNativeNote:
    'Cycle not scored yet — WHOOP will fill recovery/HRV/strain after your next sleep.',
} as const;

export function getSeedBackendStatusCopy(
  status: SeedBackendStatus,
): { text: string; color: string } {
  switch (status) {
    case 'checking_backend':
      return { text: 'Checking backend seed', color: '#a8b84a' };
    case 'seed_backend':
      return { text: 'Seed snapshot · backend', color: '#a8b84a' };
    case 'fresh_seed_backend':
      return { text: 'Fresh seed · backend', color: '#4ade80' };
    case 'stale_seed_backend':
      return { text: 'Stale seed · backend', color: '#d4e157' };
    case 'degraded_backend':
      return { text: 'Cached seed · backend error', color: '#d4e157' };
  }
}

export function formatSeedWhoopLabel(score?: number | null): string {
  if (score == null) return ATHLETE_CAPABILITY_COPY.whoopSourceLabel;
  return `${ATHLETE_CAPABILITY_COPY.whoopSourceLabel} ${Math.round(score)}%`;
}

export function getAthleteCapabilitySummary(
  mode: AthleteCapabilityMode,
): { badge: string; note: string; color: string; borderColor: string } {
  switch (mode) {
    case 'seed':
      return {
        badge: 'Seed mode',
        note: ATHLETE_CAPABILITY_COPY.provisionalBackendNote,
        color: '#a8b84a',
        borderColor: 'rgba(168,184,74,0.35)',
      };
    case 'partial_confidence':
      return {
        badge: 'Partial confidence',
        note: ATHLETE_CAPABILITY_COPY.partialConfidenceNote,
        color: '#d4e157',
        borderColor: 'rgba(212,225,87,0.35)',
      };
    case 'missing_whoop_native':
      return {
        badge: 'Seed only',
        note: ATHLETE_CAPABILITY_COPY.missingWhoopNativeNote,
        color: '#d4e157',
        borderColor: 'rgba(212,225,87,0.35)',
      };
    case 'provisional':
      return {
        badge: 'Provisional',
        note: ATHLETE_CAPABILITY_COPY.provisionalLoadNote,
        color: '#d4e157',
        borderColor: 'rgba(212,225,87,0.35)',
      };
    case 'live_ready':
      return {
        badge: 'WHOOP-backed',
        note: 'Direct WHOOP-backed readiness is available.',
        color: '#4ade80',
        borderColor: 'rgba(74,222,128,0.35)',
      };
  }
}

export function deriveAthleteCapabilityMode(args: {
  seedMode?: boolean;
  provisionalUntilDirectWhoop?: boolean;
  confidence?: 'high' | 'medium' | 'low' | null;
}): AthleteCapabilityMode {
  if (args.provisionalUntilDirectWhoop) return 'missing_whoop_native';
  if (args.seedMode) return 'seed';
  if (args.confidence === 'low' || args.confidence === 'medium') {
    return 'partial_confidence';
  }
  return 'live_ready';
}
