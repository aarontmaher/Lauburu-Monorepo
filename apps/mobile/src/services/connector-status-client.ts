import { AI_PUBLIC_BASE, MCP_BASE_URL } from './ai-backend-config';

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
  if (MCP_BASE_URL) {
    const trimmed = MCP_BASE_URL.replace(/\/$/, '');
    const apiBase = trimmed.endsWith('/api') ? trimmed : `${trimmed}/api`;
    return { baseUrl: apiBase, source: 'mcp' };
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
