export type AdminWidgetLaneId = 'claude' | 'codex' | 'agent';
export type AdminWidgetLaneState = 'idle' | 'working' | 'blocked' | 'needs_user' | 'needs_review' | 'done' | 'stale' | 'unknown';
export type AdminWidgetFreshness = 'fresh' | 'stale' | 'missing';
export type AdminWidgetGateStatus = 'blocked' | 'partial' | 'ready_for_review' | 'clear' | 'unknown';

export interface AdminHomeWidgetContextInput {
  adminEntitled: boolean;
  generatedAt: string;
  mcp: {
    updatedAt: string | null;
    ageMs: number | null;
    isStale: boolean;
    staleReason: string | null;
  };
  lanes: ReadonlyArray<{
    id: string;
    status: string;
    heartbeatAgeMs?: number | null;
  }>;
  nextPromptTarget: string | null;
  humanApprovalCount: number;
  buildGateStatus: AdminWidgetGateStatus;
  qaGateStatus: AdminWidgetGateStatus;
  overnightQueueCount: number;
  auditQueueCount: number;
}

export interface AdminHomeWidgetContext {
  schemaVersion: 1;
  mode: 'admin';
  generatedAt: string;
  mcp: {
    freshness: AdminWidgetFreshness;
    lastWritebackAgeMs: number | null;
    staleReason: string | null;
  };
  lanes: Array<{
    id: AdminWidgetLaneId;
    state: AdminWidgetLaneState;
    heartbeatAgeMs: number | null;
  }>;
  nextPromptTarget: AdminWidgetLaneId | null;
  approvals: {
    humanApprovalCount: number;
  };
  gates: {
    build: AdminWidgetGateStatus;
    qa: AdminWidgetGateStatus;
  };
  queues: {
    overnightCount: number;
    auditCount: number;
  };
  deepLink: '/admin-dev';
  safety: {
    developerMcpOnly: true;
    adminEntitlementRequired: true;
    includesSecrets: false;
    includesRawLogs: false;
    includesPromptText: false;
    noInstalledBuildVerifiedClaim: true;
  };
}

const LANE_IDS: ReadonlyArray<AdminWidgetLaneId> = ['claude', 'codex', 'agent'];
const LANE_STATES: ReadonlyArray<AdminWidgetLaneState> = ['idle', 'working', 'blocked', 'needs_user', 'needs_review', 'done', 'stale', 'unknown'];
const GATE_STATES: ReadonlyArray<AdminWidgetGateStatus> = ['blocked', 'partial', 'ready_for_review', 'clear', 'unknown'];

function asLaneId(value: string | null | undefined): AdminWidgetLaneId | null {
  const normalized = typeof value === 'string' ? value.toLowerCase().replace(/[^a-z_]+/g, '_') : '';
  if (normalized === 'agent' || normalized === 'cowork') return 'agent';
  return LANE_IDS.includes(normalized as AdminWidgetLaneId) ? normalized as AdminWidgetLaneId : null;
}

function asLaneState(value: string): AdminWidgetLaneState {
  const normalized = value.toLowerCase().replace(/[^a-z_]+/g, '_');
  if (normalized === 'in_progress') return 'working';
  if (normalized === 'complete_waiting_approval') return 'needs_review';
  return LANE_STATES.includes(normalized as AdminWidgetLaneState) ? normalized as AdminWidgetLaneState : 'unknown';
}

function asGateStatus(value: AdminWidgetGateStatus): AdminWidgetGateStatus {
  return GATE_STATES.includes(value) ? value : 'unknown';
}

function count(value: number): number {
  return Number.isFinite(value) ? Math.max(0, Math.floor(value)) : 0;
}

export function buildAdminHomeWidgetContext(input: AdminHomeWidgetContextInput): AdminHomeWidgetContext | null {
  if (!input.adminEntitled) return null;

  const freshness: AdminWidgetFreshness = !input.mcp.updatedAt
    ? 'missing'
    : input.mcp.isStale
      ? 'stale'
      : 'fresh';

  const laneMap = new Map<AdminWidgetLaneId, { state: AdminWidgetLaneState; heartbeatAgeMs: number | null }>();
  for (const row of input.lanes) {
    const id = asLaneId(row.id);
    if (!id) continue;
    laneMap.set(id, {
      state: asLaneState(row.status),
      heartbeatAgeMs: typeof row.heartbeatAgeMs === 'number' && Number.isFinite(row.heartbeatAgeMs) && row.heartbeatAgeMs >= 0
        ? Math.floor(row.heartbeatAgeMs)
        : null,
    });
  }

  return {
    schemaVersion: 1,
    mode: 'admin',
    generatedAt: input.generatedAt,
    mcp: {
      freshness,
      lastWritebackAgeMs: typeof input.mcp.ageMs === 'number' && Number.isFinite(input.mcp.ageMs)
        ? Math.max(0, Math.floor(input.mcp.ageMs))
        : null,
      staleReason: input.mcp.staleReason ? input.mcp.staleReason.slice(0, 64) : null,
    },
    lanes: LANE_IDS.map((id) => ({
      id,
      state: laneMap.get(id)?.state ?? 'unknown',
      heartbeatAgeMs: laneMap.get(id)?.heartbeatAgeMs ?? null,
    })),
    nextPromptTarget: asLaneId(input.nextPromptTarget),
    approvals: {
      humanApprovalCount: count(input.humanApprovalCount),
    },
    gates: {
      build: asGateStatus(input.buildGateStatus),
      qa: asGateStatus(input.qaGateStatus),
    },
    queues: {
      overnightCount: count(input.overnightQueueCount),
      auditCount: count(input.auditQueueCount),
    },
    deepLink: '/admin-dev',
    safety: {
      developerMcpOnly: true,
      adminEntitlementRequired: true,
      includesSecrets: false,
      includesRawLogs: false,
      includesPromptText: false,
      noInstalledBuildVerifiedClaim: true,
    },
  };
}
