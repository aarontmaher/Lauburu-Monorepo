/**
 * Multi-source health status builder — produces machine-readable
 * source-health records for all known providers.
 *
 * Each source gets an explicit status. Sources that are not
 * implemented or not connected are marked honestly.
 */

import type { SourceHealthStatus, FreshnessStatus, UpstreamStatus } from '../../contracts/freshness.types';
import type { HealthSourceProvider } from '../../contracts/health-source-raw.types';

export type SourceConnectionStatus =
  | 'available'
  | 'partial'
  | 'stale'
  | 'unavailable'
  | 'not_connected'
  | 'auth_required'
  | 'auth_expired'
  | 'scaffold_only';

export interface MultiSourceHealthSummary {
  athleteId: string;
  checkedAt: string;
  sources: Array<{
    provider: string;
    connectionStatus: SourceConnectionStatus;
    freshnessStatus: FreshnessStatus;
    lastIngestAt: string | null;
    domainsAvailable: string[];
    missingDomains: string[];
    reason: string | null;
    /** What this source is valid context for. Informational hint for Coach. */
    safeFor: string[];
    /** What this source MUST NOT be used to unlock (readiness, etc). */
    notSafeFor: string[];
    /** For `polar_via_health_connect`: the detected source app, else null. */
    sourceApp: string | null;
    /** Whether this source represents a direct live adapter (true) or an
     * indirect/via-intermediary path (false). Polar via Health Connect is
     * indirect; direct Polar API would be true (but is not yet
     * implemented). */
    directAdapter: boolean;
  }>;
}

/** Build health summary from whatever source-health records exist. */
export function buildMultiSourceHealth(
  athleteId: string,
  sourceHealthRecords: Record<string, SourceHealthStatus | null>,
): MultiSourceHealthSummary {
  const now = new Date().toISOString();

  type ProviderSpec = {
    provider: string;
    implemented: boolean;
    domains: string[];
    safeFor: string[];
    notSafeFor: string[];
    directAdapter: boolean;
  };

  /**
   * Readiness / HRV-fatigue / recovery-strain decisions are reserved for
   * direct WHOOP-native data. No other source — Apple Health, Health
   * Connect, Polar (direct or via HC) — may unlock those. This is why
   * `notSafeFor` is explicit on every row.
   */
  const READINESS_NOT_SAFE = [
    'readiness',
    'hrv_fatigue',
    'recovery_strain',
    'live_whoop_operational_claims',
  ];

  const KNOWN_PROVIDERS: ProviderSpec[] = [
    {
      provider: 'whoop',
      implemented: true,
      domains: ['recovery', 'sleep', 'strain', 'workouts', 'hrv', 'resting_hr'],
      safeFor: ['readiness', 'hrv_fatigue', 'recovery_strain', 'session_context', 'training_history'],
      notSafeFor: [],
      directAdapter: true,
    },
    {
      provider: 'apple_health',
      implemented: true,
      domains: ['sleep', 'workouts', 'steps', 'active_calories', 'resting_hr'],
      safeFor: ['session_context', 'heart_rate_context', 'training_history', 'source_health_questions'],
      notSafeFor: READINESS_NOT_SAFE,
      directAdapter: true,
    },
    {
      provider: 'health_connect',
      implemented: true,
      domains: ['sleep', 'workouts', 'steps', 'active_calories', 'resting_hr', 'hrv'],
      safeFor: ['session_context', 'heart_rate_context', 'training_history', 'source_health_questions'],
      notSafeFor: READINESS_NOT_SAFE,
      directAdapter: true,
    },
    {
      provider: 'polar_via_health_connect',
      implemented: true,
      domains: ['workouts', 'workout_hr', 'heart_rate_samples', 'sleep', 'steps', 'active_calories', 'resting_hr'],
      safeFor: ['session_context', 'heart_rate_context', 'training_history', 'source_health_questions'],
      notSafeFor: [...READINESS_NOT_SAFE, 'direct_polar_auth'],
      directAdapter: false,
    },
    {
      provider: 'samsung_health_via_health_connect',
      implemented: true,
      domains: ['sleep', 'workouts', 'steps', 'active_calories', 'resting_hr', 'heart_rate_samples', 'distance', 'spo2', 'vo2_max', 'body_metrics'],
      safeFor: ['session_context', 'heart_rate_context', 'training_history', 'source_health_questions'],
      notSafeFor: READINESS_NOT_SAFE,
      directAdapter: false,
    },
    {
      provider: 'samsung_health_direct',
      implemented: true,
      domains: ['sleep', 'workouts', 'steps', 'active_calories', 'resting_hr', 'heart_rate_samples', 'distance', 'spo2', 'body_metrics', 'blood_oxygen', 'nutrition', 'water_intake'],
      safeFor: ['session_context', 'heart_rate_context', 'training_history', 'source_health_questions'],
      notSafeFor: READINESS_NOT_SAFE,
      directAdapter: true,
    },
    {
      provider: 'cronometer',
      implemented: true,
      domains: ['calories', 'protein', 'carbs', 'fat', 'fiber', 'water', 'sodium'],
      safeFor: ['nutrition_context', 'source_health_questions'],
      notSafeFor: READINESS_NOT_SAFE,
      directAdapter: true,
    },
    {
      provider: 'manual',
      implemented: true,
      domains: ['calories', 'protein', 'carbs', 'fat'],
      safeFor: ['nutrition_context', 'source_health_questions'],
      notSafeFor: READINESS_NOT_SAFE,
      directAdapter: true,
    },
    {
      provider: 'direct_polar',
      implemented: true,
      domains: ['workouts', 'daily_activity', 'physical_info', 'sleep', 'hrv', 'resting_hr'],
      safeFor: ['session_context', 'heart_rate_context', 'training_history', 'source_health_questions'],
      notSafeFor: READINESS_NOT_SAFE,
      directAdapter: true,
    },
    {
      provider: 'polar',
      implemented: false,
      domains: ['sleep', 'workouts', 'hrv', 'resting_hr'],
      safeFor: [],
      notSafeFor: [...READINESS_NOT_SAFE, 'direct_polar_auth'],
      directAdapter: false,
    },
    {
      provider: 'whoop_direct',
      implemented: true,
      domains: ['recovery', 'sleep', 'strain', 'workouts', 'hrv', 'resting_hr'],
      safeFor: ['readiness', 'hrv_fatigue', 'recovery_strain', 'session_context', 'training_history'],
      notSafeFor: [],
      directAdapter: true,
    },
    {
      provider: 'concept2_logbook',
      implemented: false,
      domains: ['workouts', 'watts', 'distance', 'pace'],
      safeFor: ['session_context', 'training_history'],
      notSafeFor: READINESS_NOT_SAFE,
      directAdapter: false,
    },
    {
      provider: 'garmin',
      implemented: false,
      domains: ['sleep', 'workouts', 'hrv', 'resting_hr'],
      safeFor: [],
      notSafeFor: READINESS_NOT_SAFE,
      directAdapter: false,
    },
  ];

  const ALL_HEALTH_DOMAINS = ['recovery', 'sleep', 'strain', 'workouts', 'hrv', 'resting_hr'];

  const sources = KNOWN_PROVIDERS.map(({ provider, implemented, domains: providerDomains, safeFor, notSafeFor, directAdapter }) => {
    const record = sourceHealthRecords[provider];

    if (!implemented) {
      return {
        provider,
        connectionStatus: 'scaffold_only' as SourceConnectionStatus,
        freshnessStatus: 'missing' as FreshnessStatus,
        lastIngestAt: null,
        domainsAvailable: [],
        missingDomains: providerDomains,
        reason: provider === 'polar'
          ? 'Direct Polar adapter not yet live. Polar may still be available via Health Connect.'
          : `${provider} integration is not yet available.`,
        safeFor,
        notSafeFor,
        sourceApp: null,
        directAdapter,
      };
    }

    if (!record) {
      return {
        provider,
        connectionStatus: 'not_connected' as SourceConnectionStatus,
        freshnessStatus: 'missing' as FreshnessStatus,
        lastIngestAt: null,
        domainsAvailable: [],
        missingDomains: providerDomains,
        reason: `No ${provider} source-health record found.`,
        safeFor,
        notSafeFor,
        sourceApp: null,
        directAdapter,
      };
    }

    const domainMap = record.coverageByDomain ?? {};
    const domainsAvailable: string[] = [];
    const missingDomains: string[] = [];

    for (const domain of providerDomains) {
      const domInfo = domainMap[domain] as { status?: string } | undefined;
      if (domInfo?.status === 'fresh' || domInfo?.status === 'stale') {
        domainsAvailable.push(domain);
      } else {
        missingDomains.push(domain);
      }
    }

    let connectionStatus: SourceConnectionStatus;
    const reason = record.degradedReason ?? '';
    const upstream = record.upstreamStatus;

    // Detect auth states from upstream status or degraded reason
    if (upstream === 'unknown' && reason.toLowerCase().includes('auth_required')) {
      connectionStatus = 'auth_required';
    } else if (upstream === 'unknown' && reason.toLowerCase().includes('auth_expired')) {
      connectionStatus = 'auth_expired';
    } else if (record.freshnessStatus === 'missing' && upstream === 'unknown') {
      // Has a record but never successfully ingested — not connected or auth issue
      connectionStatus = reason.includes('not_connected') ? 'not_connected' : 'not_connected';
    } else if (record.freshnessStatus === 'fresh' && (upstream === 'healthy' || upstream === 'unknown')) {
      connectionStatus = 'available';
    } else if (record.freshnessStatus === 'stale') {
      connectionStatus = 'stale';
    } else if (domainsAvailable.length > 0) {
      connectionStatus = 'partial';
    } else if (upstream === 'down') {
      connectionStatus = 'unavailable';
    } else {
      connectionStatus = 'unavailable';
    }

    // polar_via_health_connect pulls its detected source app from the
    // record's degradedReason metadata passthrough or falls back to
    // 'Polar Flow' — callers are expected to set degradedReason to the
    // detected package / friendly name when they have it.
    let sourceApp: string | null = null;
    if (provider === 'polar_via_health_connect') {
      sourceApp = record.degradedReason?.startsWith('sourceApp:')
        ? record.degradedReason.slice('sourceApp:'.length).trim()
        : 'Polar Flow';
    }

    return {
      provider,
      connectionStatus,
      freshnessStatus: record.freshnessStatus,
      lastIngestAt: record.lastSuccessfulIngestAt,
      domainsAvailable,
      missingDomains,
      reason: record.degradedReason,
      safeFor,
      notSafeFor,
      sourceApp,
      directAdapter,
    };
  });

  return { athleteId, checkedAt: now, sources };
}
