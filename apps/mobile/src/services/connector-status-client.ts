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
}

export interface ConnectorSnapshot {
  checkedAt: string;
  workStatus: ConnectorWorkStatus | null;
  coderLanes: { schemaVersion: number; generatedAt: string; lanes: ConnectorLane[] } | null;
  buildStatus: ConnectorBuildStatus | null;
  handoff: ConnectorHandoff | null;
}

function connectorApiBase(): string | null {
  const publicBase = (process.env.EXPO_PUBLIC_AI_PUBLIC_URL ?? '').replace(/\/$/, '');
  if (!publicBase) return null;
  return publicBase.replace(/\/athlete-memory$/, '');
}

async function fetchConnectorJson<T>(path: string): Promise<T | null> {
  try {
    const apiBase = connectorApiBase();
    const memToken = process.env.EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN ?? '';
    if (!apiBase || !memToken) return null;
    const res = await fetch(`${apiBase}${path}`, {
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
  const [workStatus, coderLanes, buildStatus, handoff] = await Promise.all([
    fetchConnectorJson<ConnectorWorkStatus>('/work_status'),
    fetchConnectorJson<{ schemaVersion: number; generatedAt: string; lanes: ConnectorLane[] }>('/coder_lanes'),
    fetchConnectorJson<ConnectorBuildStatus>('/build_status'),
    fetchConnectorJson<ConnectorHandoff>('/handoff'),
  ]);

  if (!workStatus && !coderLanes && !buildStatus && !handoff) return null;
  return {
    checkedAt: new Date().toISOString(),
    workStatus,
    coderLanes,
    buildStatus,
    handoff,
  };
}
