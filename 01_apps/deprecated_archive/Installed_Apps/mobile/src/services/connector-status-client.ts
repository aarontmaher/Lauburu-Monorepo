import { AI_PUBLIC_BASE, mcpWorkerRootUrl } from './ai-backend-config';

export interface ConnectorWorkStatus {
  schemaVersion: number;
  generatedAt: string;
  currentPriority: string | null;
  currentBlocker: string | null;
  liveStatus: {
    androidVersionCode: number | null;
    iosBuildNumber: string | null;
    androidPlayTrack: string | null;
    iosTestflightGroup: string | null;
    cloudflareWorkerDeployed: boolean;
  };
  repoStatus: {
    head: string;
    branch: string;
    dirtyFileCount: number;
    untrackedFileCount: number;
    lastCommitMessage: string;
  };
  nextAction: string | null;
  dataSource?: ConnectorDataSource;
}

export interface ConnectorLane {
  laneId: string;
  status: string;
  lastSeenAt: string | null;
  currentPromptId: string | null;
  lastPromptId: string | null;
  lastSummary: string | null;
  lastCommit: string | null;
  lastTypecheckResult: string | null;
  dirtyFiles: string[];
  nextPrompt: string | null;
}

export interface ConnectorBuildStatus {
  schemaVersion: number;
  generatedAt: string;
  android: {
    versionCode: number | null;
    appVersion: string | null;
    githubStatus: string | null;
    playStatus: string | null;
    playTrack: string | null;
  };
  ios: {
    buildNumber: string | null;
    appVersion: string | null;
    githubStatus: string | null;
    testflightStatus: string | null;
    testflightGroup: string | null;
  };
  dataSource?: ConnectorDataSource;
}

export interface ConnectorHandoff {
  schemaVersion: number;
  generatedAt: string;
  latestClaudePrompt: string | null;
  latestCodexPrompt: string | null;
  manualSteps: string[];
  doNotTouch: string[];
  safeToBuild: boolean;
  safeToBuildReason: string;
  dataSource?: ConnectorDataSource;
}

export interface ConnectorTerminalSummaryEntry {
  laneId: string;
  at: string;
  summary: string;
  verification: string;
  nextAction: string;
  exitCode: number | null;
}

export interface ConnectorTerminalSummary {
  schemaVersion: number;
  generatedAt: string;
  entries: ConnectorTerminalSummaryEntry[];
  dataSource?: ConnectorDataSource;
}

export interface ConnectorDataSource {
  source?: string;
  reason?: string;
  message?: string;
  schemaRequired?: boolean;
}

export interface ConnectorSnapshot {
  checkedAt: string;
  source: 'mcp' | 'public_backend';
  workStatus: ConnectorWorkStatus | null;
  coderLanes: { schemaVersion: number; generatedAt: string; lanes: ConnectorLane[]; dataSource?: ConnectorDataSource } | null;
  buildStatus: ConnectorBuildStatus | null;
  handoff: ConnectorHandoff | null;
  terminalSummary: ConnectorTerminalSummary | null;
}

function connectorApiBase(): { baseUrl: string; source: ConnectorSnapshot['source'] } {
  // Source of truth — strips any /mcp/v2[/admin] / /api / /mcp/core
  // suffix the env may already include, then re-appends `/api` once.
  // Older code here appended `/api` even when the env was set to the
  // full `<root>/mcp/v2` URL, producing `/mcp/v2/api/*` paths the
  // worker does not route. The env has shipped both shapes (worker
  // root and full /mcp/v2 URL) at different points; centralise the
  // normalisation in `mcpWorkerRootUrl`.
  const root = mcpWorkerRootUrl();
  if (root) {
    return { baseUrl: `${root}/api`, source: 'mcp' };
  }
  const publicBase = AI_PUBLIC_BASE.replace(/\/$/, '');
  return { baseUrl: publicBase.replace(/\/athlete-memory$/, ''), source: 'public_backend' };
}

async function fetchConnectorJson<T>(baseUrl: string, path: string): Promise<T | null> {
  try {
    const memToken = process.env.EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN ?? '';
    if (!memToken) return null;
    const res = await fetch(`${baseUrl}${path}`, {
      headers: {
        Accept: 'application/json',
        'x-athlete-memory-token': memToken,
      },
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export async function fetchConnectorSnapshot(): Promise<ConnectorSnapshot | null> {
  const { baseUrl, source } = connectorApiBase();
  const [workStatus, coderLanes, buildStatus, handoff, terminalSummary] = await Promise.all([
    fetchConnectorJson<ConnectorWorkStatus>(baseUrl, '/work_status'),
    fetchConnectorJson<{ schemaVersion: number; generatedAt: string; lanes: ConnectorLane[] }>(baseUrl, '/coder_lanes'),
    fetchConnectorJson<ConnectorBuildStatus>(baseUrl, '/build_status'),
    fetchConnectorJson<ConnectorHandoff>(baseUrl, '/handoff'),
    fetchConnectorJson<ConnectorTerminalSummary>(baseUrl, '/terminal_summary'),
  ]);

  if (!workStatus && !coderLanes && !buildStatus && !handoff && !terminalSummary) return null;
  return {
    checkedAt: new Date().toISOString(),
    source,
    workStatus,
    coderLanes,
    buildStatus,
    handoff,
    terminalSummary,
  };
}
