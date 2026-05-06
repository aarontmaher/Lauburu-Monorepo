import { Router } from 'express';
import { getLaneSummaries } from '../services/tmuxBridge';
import {
  CONNECTOR_SCHEMA_VERSION,
  type BuildStatus,
  type CoderLanes,
  type Handoff,
  type WorkStatus,
} from '../types/connector';

const router = Router();

function requireAdminToken(req: any, res: any, next: any): void {
  const expected = process.env.ATHLETE_MEMORY_API_TOKEN;
  if (!expected) {
    res.status(503).json({ ok: false, error: 'Connector routes disabled until ATHLETE_MEMORY_API_TOKEN is configured.' });
    return;
  }
  if (req.header('x-athlete-memory-token') !== expected) {
    res.status(403).json({ ok: false, error: 'Forbidden connector access.' });
    return;
  }
  next();
}

router.use(requireAdminToken);

router.get('/work_status', (_req: any, res: any) => {
  const generatedAt = new Date().toISOString();
  const payload: WorkStatus = {
    schemaVersion: CONNECTOR_SCHEMA_VERSION,
    generatedAt,
    currentPriority: 'Backend/API connector dummy routes and owner-only Admin/Dev display.',
    currentBlocker: 'tmux bridge is not operational yet; route data is static placeholder state.',
    liveStatus: {
      androidVersionCode: 17,
      iosBuildNumber: '18',
      androidPlayTrack: 'internal',
      iosTestflightGroup: 'Team (Expo)',
      lastRailwayDeployAt: null,
      cloudflareWorkerDeployed: false,
    },
    repoStatus: {
      head: 'unknown',
      branch: 'main',
      dirtyFileCount: 0,
      untrackedFileCount: 0,
      lastCommitAt: generatedAt,
      lastCommitMessage: 'unknown until local bridge is operational',
    },
    nextAction: 'Connect tmux bridge producer, then replace dummy route data with sanitized lane summaries.',
  };
  res.status(200).json(payload);
});

router.get('/coder_lanes', (_req: any, res: any) => {
  const generatedAt = new Date().toISOString();
  const payload: CoderLanes = {
    schemaVersion: CONNECTOR_SCHEMA_VERSION,
    generatedAt,
    lanes: getLaneSummaries(generatedAt),
  };
  res.status(200).json(payload);
});

router.get('/build_status', (_req: any, res: any) => {
  const payload: BuildStatus = {
    schemaVersion: CONNECTOR_SCHEMA_VERSION,
    generatedAt: new Date().toISOString(),
    android: {
      versionCode: 17,
      appVersion: '0.1.0',
      githubRunId: null,
      githubStatus: 'queued',
      easBuildId: null,
      easBuildUrl: null,
      playSubmissionId: null,
      playStatus: 'submitted_completed',
      playTrack: 'internal',
    },
    ios: {
      buildNumber: '18',
      appVersion: '0.1.0',
      githubRunId: null,
      githubStatus: 'queued',
      easBuildId: null,
      easBuildUrl: null,
      testflightSubmissionId: null,
      testflightStatus: 'uploaded_processing',
      testflightGroup: 'Team (Expo)',
    },
  };
  res.status(200).json(payload);
});

router.get('/handoff', (_req: any, res: any) => {
  const payload: Handoff = {
    schemaVersion: CONNECTOR_SCHEMA_VERSION,
    generatedAt: new Date().toISOString(),
    latestClaudePrompt: 'CLAUDE-REVIEW-MCP-DUMMY-ROUTES-01',
    latestCodexPrompt: 'CODEX-BACKEND-API-AI-IMPLEMENTATION-01',
    manualSteps: [
      'Aaron: review dummy connector cards in Admin/Dev before the next paired tester build.',
      'Aaron: keep build dispatch owner-tap only.',
    ],
    doNotTouch: [
      'grappling.opml',
      'apps/mobile/app.json',
      'apps/mobile/eas.json',
    ],
    safeToBuild: false,
    safeToBuildReason: 'Backend connector routes are provisional dummy data until tmux bridge output is live and reviewed.',
  };
  res.status(200).json(payload);
});

export default router;
