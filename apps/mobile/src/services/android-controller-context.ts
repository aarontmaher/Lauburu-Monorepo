export type AndroidControllerNotificationCategory =
  | 'idle_lane'
  | 'approval_needed'
  | 'audit_complete'
  | 'mcp_stale'
  | 'build_blocked';

export type AndroidControllerFreshness = 'fresh' | 'stale' | 'missing';
export type AndroidControllerGateState = 'blocked' | 'partial' | 'clear' | 'unknown';
export type AndroidControllerHealthConnectState =
  | 'connected'
  | 'stale'
  | 'permission_needed'
  | 'sync_needed'
  | 'not_registered'
  | 'sync_failed'
  | 'unknown';

export interface AndroidControllerLaneInput {
  id: string;
  status: string;
  heartbeatAgeMs?: number | null;
  terminalDisagreement?: boolean;
}

export interface AndroidControllerContextInput {
  adminEntitled: boolean;
  platform: string;
  generatedAt: string;
  mcp: {
    updatedAt: string | null;
    ageMs: number | null;
    isStale: boolean;
    staleReason: string | null;
  };
  lanes: ReadonlyArray<AndroidControllerLaneInput>;
  nextPromptTarget: string | null;
  humanApprovalCount: number;
  buildGateStatus: AndroidControllerGateState;
  qaGateStatus: AndroidControllerGateState;
  overnightQueueCount: number;
  auditQueueCount: number;
  healthConnect: {
    state: AndroidControllerHealthConnectState;
    lastSyncAt: string | null;
    availableMetrics: number;
    missingMetrics: ReadonlyArray<string>;
  };
  latestEvidencePath: string | null;
}

export interface AndroidControllerContext {
  schemaVersion: 1;
  mode: 'android_admin_controller';
  platform: 'android';
  generatedAt: string;
  mcp: {
    freshness: AndroidControllerFreshness;
    lastWritebackAgeMs: number | null;
    staleReason: string | null;
  };
  lanes: Array<{
    id: string;
    status: string;
    heartbeatAgeMs: number | null;
    terminalDisagreement: boolean;
  }>;
  nextPromptTarget: string | null;
  approvals: {
    humanApprovalCount: number;
  };
  gates: {
    build: AndroidControllerGateState;
    qa: AndroidControllerGateState;
  };
  queues: {
    overnightCount: number;
    auditCount: number;
  };
  notifications: {
    categories: AndroidControllerNotificationCategory[];
  };
  auditRunner: {
    startAuditCommand: string;
    screenshotCommand: string;
    videoCommand: string;
    latestEvidencePath: string | null;
    simulatorOrMirrorEvidenceOnly: true;
    canClearInstalledDeviceGate: false;
  };
  healthConnect: {
    state: AndroidControllerHealthConnectState;
    lastSyncAt: string | null;
    availableMetrics: number;
    missingMetrics: string[];
  };
  deepLinks: {
    adminDev: '/admin-dev';
    approvalQueue: '/admin-dev#approval-queue';
    latestEvidence: '/admin-dev#latest-evidence';
  };
  safety: {
    publicSafe: true;
    adminEntitlementRequired: true;
    includesSecrets: false;
    includesRawLogs: false;
    noReleaseActions: true;
    noInstalledBuildVerifiedClaim: true;
  };
}

export const ANDROID_CONTROLLER_NOTIFICATION_CATEGORIES: AndroidControllerNotificationCategory[] = [
  'idle_lane',
  'approval_needed',
  'audit_complete',
  'mcp_stale',
  'build_blocked',
];

const GATE_STATES: ReadonlyArray<AndroidControllerGateState> = ['blocked', 'partial', 'clear', 'unknown'];
const HEALTH_CONNECT_STATES: ReadonlyArray<AndroidControllerHealthConnectState> = [
  'connected',
  'stale',
  'permission_needed',
  'sync_needed',
  'not_registered',
  'sync_failed',
  'unknown',
];

function normalizeGate(value: AndroidControllerGateState): AndroidControllerGateState {
  return GATE_STATES.includes(value) ? value : 'unknown';
}

function normalizeHealthConnect(value: AndroidControllerHealthConnectState): AndroidControllerHealthConnectState {
  return HEALTH_CONNECT_STATES.includes(value) ? value : 'unknown';
}

function count(value: number): number {
  return Number.isFinite(value) ? Math.max(0, Math.floor(value)) : 0;
}

function cleanText(value: string | null | undefined, max = 80): string | null {
  if (!value) return null;
  const compact = value.replace(/\s+/g, ' ').trim();
  return compact ? compact.slice(0, max) : null;
}

export function buildAndroidControllerContext(input: AndroidControllerContextInput): AndroidControllerContext | null {
  if (!input.adminEntitled || input.platform !== 'android') return null;

  const freshness: AndroidControllerFreshness = !input.mcp.updatedAt
    ? 'missing'
    : input.mcp.isStale
      ? 'stale'
      : 'fresh';

  return {
    schemaVersion: 1,
    mode: 'android_admin_controller',
    platform: 'android',
    generatedAt: input.generatedAt,
    mcp: {
      freshness,
      lastWritebackAgeMs: typeof input.mcp.ageMs === 'number' && Number.isFinite(input.mcp.ageMs)
        ? Math.max(0, Math.floor(input.mcp.ageMs))
        : null,
      staleReason: cleanText(input.mcp.staleReason, 64),
    },
    lanes: input.lanes.slice(0, 8).map((lane) => ({
      id: cleanText(lane.id, 32) ?? 'lane',
      status: cleanText(lane.status, 32) ?? 'unknown',
      heartbeatAgeMs: typeof lane.heartbeatAgeMs === 'number' && Number.isFinite(lane.heartbeatAgeMs) && lane.heartbeatAgeMs >= 0
        ? Math.floor(lane.heartbeatAgeMs)
        : null,
      terminalDisagreement: lane.terminalDisagreement === true,
    })),
    nextPromptTarget: cleanText(input.nextPromptTarget, 32),
    approvals: {
      humanApprovalCount: count(input.humanApprovalCount),
    },
    gates: {
      build: normalizeGate(input.buildGateStatus),
      qa: normalizeGate(input.qaGateStatus),
    },
    queues: {
      overnightCount: count(input.overnightQueueCount),
      auditCount: count(input.auditQueueCount),
    },
    notifications: {
      categories: ANDROID_CONTROLLER_NOTIFICATION_CATEGORIES,
    },
    auditRunner: {
      startAuditCommand: 'audit-system/run-audit.sh --platform android',
      screenshotCommand: 'adb exec-out screencap -p > audit-artifacts/android/<timestamp>/screen.png',
      videoCommand: 'scrcpy --record audit-artifacts/android/<timestamp>/samsung-audit.mp4',
      latestEvidencePath: cleanText(input.latestEvidencePath, 120),
      simulatorOrMirrorEvidenceOnly: true,
      canClearInstalledDeviceGate: false,
    },
    healthConnect: {
      state: normalizeHealthConnect(input.healthConnect.state),
      lastSyncAt: cleanText(input.healthConnect.lastSyncAt, 40),
      availableMetrics: count(input.healthConnect.availableMetrics),
      missingMetrics: input.healthConnect.missingMetrics.map((item) => cleanText(item, 32)).filter((item): item is string => !!item).slice(0, 8),
    },
    deepLinks: {
      adminDev: '/admin-dev',
      approvalQueue: '/admin-dev#approval-queue',
      latestEvidence: '/admin-dev#latest-evidence',
    },
    safety: {
      publicSafe: true,
      adminEntitlementRequired: true,
      includesSecrets: false,
      includesRawLogs: false,
      noReleaseActions: true,
      noInstalledBuildVerifiedClaim: true,
    },
  };
}
