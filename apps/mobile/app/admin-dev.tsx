/**
 * Admin / Dev Control Center — MVP.
 *
 * Hidden screen reachable only by long-pressing the Settings → About →
 * Version row when signed in as an admin. NOT a tab. NOT a public
 * surface. Read-only this batch — no command execution, no token
 * printing, no workflow_dispatch.
 *
 * Sections:
 *   1. App build / runtime info (from expo-application + expo-updates)
 *   2. Backend health (uses existing internal-token endpoint —
 *      /v1/internal/athletes/:id/ai-health-context)
 *   3. Data / AI status (counts and date range from the same call)
 *   4. Release / status links (Expo, Railway, Play Console reminders)
 *   5. Prompt library (clipboard copy)
 *   6. Status handoff template (clipboard copy)
 *   7. Workflow triggers — placeholders (disabled, copy explains why)
 *
 * Hard rules:
 *   - No tokens or secret values rendered.
 *   - No arbitrary shell. Disabled trigger buttons surface intent only.
 *   - Admin gate by email allowlist (matches Settings tester-tools gate).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Alert, AppState, Linking, Platform, Pressable, ScrollView, StyleSheet, TextInput, Text as RNText } from 'react-native';
import { Stack, useRouter } from 'expo-router';
import * as Application from 'expo-application';
import * as Updates from 'expo-updates';
import Constants from 'expo-constants';

import { Text, View } from '@/components/Themed';
import { useAuthStore } from '../src/store/auth-store';
import { useDevUnlockStore } from '../src/store/dev-unlock-store';
import {
  useOwnerBacklogStore,
  type OwnerBacklogItem,
  type OwnerBacklogPlatform,
  type OwnerBacklogType,
} from '../src/store/owner-backlog-store';
import { useOwnerWorkflowStore } from '../src/store/owner-workflow-store';
import { useAuditEventStore } from '../src/store/audit-event-store';
import { useAdminDevNotificationStore } from '../src/store/admin-dev-notification-store';
import { useApprovalGatesStore } from '../src/store/approval-gates-store';
import { useSpendGatesStore, isSpendGateActionable } from '../src/store/spend-gates-store';
import { useResearchJobsStore } from '../src/store/research-jobs-store';
import type { ApprovalGate, SpendGate, ResearchJob } from '@lauburu/shared';
import { fetchAgentStatus, type AgentStatusEntry } from '../src/services/agent-status-client';
import {
  fetchConnectorSnapshot,
  type ConnectorDataSource,
  type ConnectorSnapshot,
} from '../src/services/connector-status-client';
import {
  fetchMcpV2DashboardSnapshot,
  type McpV2DashboardSnapshot,
} from '../src/services/mcp-v2-client';
import {
  summariseLaneProgress,
  type LaneProgressSummary,
} from '../src/services/lane-progress-summary';
import { StatusPill } from '../src/components/primitives/StatusPill';
import type { Tone } from '../src/components/primitives/_helpers';
import {
  buildClaudeCodePrompt,
  buildClaudeChromePrompt,
  buildChatGPTStatusPrompt,
  buildCodexPrompt,
  buildTerminalCheckPrompt,
  buildTmuxAttachInstructions,
} from '../src/services/prompt-templates';

const ADMIN_EMAILS = new Set(['aaron.t.maher@gmail.com']);

const EXPO_PROJECT_URL = 'https://expo.dev/accounts/aaronmaher/projects/lauburu-grappling-map';
const EXPO_BUILDS_URL = `${EXPO_PROJECT_URL}/builds`;
const EXPO_UPDATES_URL = `${EXPO_PROJECT_URL}/updates`;
const RAILWAY_URL = 'https://railway.com/project';
const GITHUB_REPO_URL = 'https://github.com/aaronmaher/lauburu-grappling-map';
const GITHUB_ACTIONS_URL = `${GITHUB_REPO_URL}/actions`;
const PLAY_CONSOLE_URL = 'https://play.google.com/console';
const APPSTORE_CONNECT_URL = 'https://appstoreconnect.apple.com/';

interface BackendHealth {
  ok: boolean;
  totalNormalizedDays: number | null;
  firstDate: string | null;
  lastDate: string | null;
  sourcesConnected: number | null;
  readinessStatus: string | null;
  checkedAt: string;
  error?: string;
}

interface AdminStatus {
  workflowDispatchAvailable: boolean;
  workflowAllowlist: string[];
  blockers: string[];
  androidBuildWorkflowAvailable?: boolean;
  iosBuildWorkflowAvailable?: boolean;
  releaseAuditWorkflowAvailable?: boolean;
  playUploadConfigured?: boolean | null;
  testflightSubmitConfigured?: boolean | null;
  testflightGroupAssignmentConfigured?: boolean | null;
  androidPlayPromoteAutomatic?: boolean | null;
  otaBlocked?: boolean;
  otaBlockerReason?: string;
}

const PROMPT_LIBRARY: Array<{ label: string; body: string }> = [
  {
    label: 'Play metadata blocker status',
    body: 'Chrome is handling Play Console app-content / closed testing setup. Do not rerun Android proof until Chrome confirms play listing fully complete. If complete, rerun Android auto-promote proof once. Do not trigger Production.',
  },
  {
    label: 'Compact ChatGPT status block',
    body: [
      'Print a compact status block for ChatGPT. No secrets, no long logs.',
      '',
      'CHATGPT_STATUS_START',
      'Task:',
      'Live:',
      'Repo-only:',
      'Verified:',
      'Blocker:',
      'Next:',
      'CHATGPT_STATUS_END',
    ].join('\n'),
  },
  {
    label: 'Android AAB next build',
    body: 'Continue automation. Bump apps/mobile/app.json android.versionCode by 1, run mobile typecheck, build a new Android production AAB on EAS, then verify the manifest (CAMERA absent, target API 35) and report the artifact link + Play Console upload steps. Do not touch iOS. Do not run Supabase db push.',
  },
  {
    label: 'AI multi-timeframe trends',
    body: 'Audit /coach/ask + buildTrendsAnswer for any remaining hard-coded windows. Confirm 7/14/30/90/180/365/all-time bundles are produced and the answer header reflects the requested window. If the AI store has fewer normalised days than requested, the answer must say so explicitly. Run typecheck and deploy chat-app to Railway only if backend changed.',
  },
  {
    label: 'App-owned Readiness primary',
    body: 'Verify Lauburu Readiness is the only product-truth readiness. WHOOP/Polar/Health Connect/Samsung must remain evidence sources only. No "Polar readiness" or "WHOOP recovery" surfaced as primary. Surface explicit "evidence-only" framing wherever a third-party readiness might leak through.',
  },
  {
    label: 'Cloud runner workflow plan',
    body: 'Push the local repo to a private GitHub repo, add .github/workflows/deploy-backend.yml (typecheck + railway up on push to main when chat-app or packages/shared changes), and add .github/workflows/eas-android.yml (workflow_dispatch + push to release/android-* triggers eas-cli build). Use ${{ secrets.EXPO_TOKEN }} and ${{ secrets.RAILWAY_TOKEN }} — do not commit any secret values. Output the workflow YAML and setup steps for me to run from my phone.',
  },
  {
    label: 'Admin/Dev Control Center next stage',
    body: 'Extend the in-app Admin/Dev screen: connect the Backend health card to a live /api/admin/status endpoint that returns booleans/counts/links only (no secrets), and wire the Workflow trigger placeholders to a GitHub Actions workflow_dispatch through a signed backend proxy (do not call GitHub directly from the app). Keep it admin-gated.',
  },
];

const STATUS_HANDOFF_TEMPLATE = [
  'CHATGPT_STATUS_START',
  'Task:',
  'Live:',
  'Repo-only:',
  'Verified:',
  'Blocker:',
  'Next:',
  'CHATGPT_STATUS_END',
].join('\n');

const SAFE_PHONE_COMMANDS = {
  bridgeSnapshot: 'npm run bridge:snapshot',
  bridgeVerify: 'npm run bridge:verify',
  workerDeploy: 'cd cloudflare-worker && wrangler deploy',
} as const;

/**
 * Top-of-screen workflow truths. These mirror docs/APP_DEVELOPMENTS.md
 * and are intentionally hard-coded for now — the long-term shape is a
 * backend route that serves the same fields. When the doc changes,
 * update these in the next paired build. Keep each line short; the UI
 * renders compact chips, not paragraphs.
 */
const CURRENT_PRIORITY = 'MCP connector consistency + Admin/Dev iPhone control centre.';
const NEXT_ACTION = 'Verify live MCP data on iPhone, then promote the next approved candidate suggestion.';

function compactGitCommit(value: unknown): string {
  if (typeof value !== 'string') return '—';
  const trimmed = value.trim();
  if (trimmed.length === 0 || trimmed === '${GITHUB_SHA}') return '—';
  return trimmed.length > 12 ? trimmed.slice(0, 12) : trimmed;
}

function connectorCheckedTime(checkedAt: string | null | undefined): string {
  if (!checkedAt) return '—';
  const checkedMs = new Date(checkedAt).getTime();
  if (!Number.isFinite(checkedMs)) return '—';
  return new Date(checkedAt).toLocaleTimeString();
}

function connectorIsStale(checkedAt: string | null | undefined): boolean {
  if (!checkedAt) return false;
  const checkedMs = new Date(checkedAt).getTime();
  if (!Number.isFinite(checkedMs)) return false;
  return Date.now() - checkedMs >= 10 * 60_000;
}

function connectorPayloadGeneratedAt(snapshot: ConnectorSnapshot | null): string | null {
  if (!snapshot) return null;
  const values = [
    snapshot.workStatus?.generatedAt,
    snapshot.coderLanes?.generatedAt,
    snapshot.buildStatus?.generatedAt,
    snapshot.handoff?.generatedAt,
    snapshot.terminalSummary?.generatedAt,
  ].filter((value): value is string => typeof value === 'string' && value.trim().length > 0);
  if (values.length === 0) return null;
  const latest = values
    .map((value) => ({ value, ms: new Date(value).getTime() }))
    .filter((item) => Number.isFinite(item.ms))
    .sort((a, b) => b.ms - a.ms)[0];
  return latest?.value ?? null;
}

function connectorPayloadFreshnessLabel(snapshot: ConnectorSnapshot | null): string {
  const generatedAt = connectorPayloadGeneratedAt(snapshot);
  if (!generatedAt) return snapshot ? 'bridge time unknown' : 'not connected';
  const generatedMs = new Date(generatedAt).getTime();
  if (!Number.isFinite(generatedMs)) return 'bridge time unknown';
  const ageMinutes = Math.max(0, Math.floor((Date.now() - generatedMs) / 60_000));
  if (ageMinutes >= 10) return `bridge stale · ${ageMinutes}m old`;
  if (ageMinutes >= 1) return `bridge fresh · ${ageMinutes}m old`;
  return 'bridge fresh · just now';
}

function connectorPayloadIsStale(snapshot: ConnectorSnapshot | null): boolean {
  const generatedAt = connectorPayloadGeneratedAt(snapshot);
  return generatedAt ? connectorIsStale(generatedAt) : false;
}

function connectorSnapshotLabel(snapshot: ConnectorSnapshot | null): string {
  if (!snapshot) return 'Repo-only';
  if (connectorPayloadIsStale(snapshot)) return 'Stale snapshot';
  if (snapshot.source !== 'mcp') return 'Fallback placeholder';
  const dataSources: Array<ConnectorDataSource | undefined> = [
    snapshot.workStatus?.dataSource,
    snapshot.coderLanes?.dataSource,
    snapshot.buildStatus?.dataSource,
    snapshot.handoff?.dataSource,
    snapshot.terminalSummary?.dataSource,
  ];
  const hasPlaceholder = dataSources.some((source) =>
    source?.source === 'placeholder' || source?.schemaRequired === true
  );
  return hasPlaceholder ? 'Fallback placeholder' : 'Live MCP data';
}

type McpV2CurrentState = {
  source?: string;
  freshness?: {
    updatedAt?: string | null;
    ageMs?: number | null;
    isStale?: boolean;
    staleReason?: string;
    windowMs?: number;
  };
  agents?: Array<{
    id?: string;
    status?: string;
    taskSummary?: string;
    lastCommit?: string | null;
    updatedAt?: string | null;
    lastSeenAt?: string | null;
    lastStateChangeAt?: string | null;
    source?: string | null;
    /**
     * Optional 0..100 progress percentage. The MCP server may emit
     * this when a lane is mid-task; missing / non-finite values
     * render as "unknown" in the UI rather than 0% (which would
     * imply the lane has not started).
     */
    progressPct?: number | null;
    /**
     * Optional next-prompt recommendation. The MCP server may
     * surface a suggested PROMPT-ID / instruction for the human to
     * dispatch next. Free-form text — UI renders verbatim if
     * present, "—" otherwise. NEVER fabricated client-side.
     */
    recommendedNextPrompt?: string | null;
    lastMarkers?: {
      MCP_RESULT?: string | null;
      MCP_BLOCKER?: string | null;
      MCP_COMMIT?: string | null;
      MCP_TESTS?: string | null;
      MCP_NEXT?: string | null;
      AGENT_QA_RESULT_JSON?: { status?: string | null; gate?: string | null; platform?: string | null } | null;
      markerCount?: number;
      markerHash?: string;
    } | null;
  }>;
  currentPriority?: string | null;
  currentBlocker?: string | null;
  nextAction?: string | null;
  liveStatus?: {
    android?: { versionCode?: number | null; status?: string | null; playTrack?: string | null } | null;
    ios?: { buildNumber?: string | null; status?: string | null } | null;
    repo?: { branch?: string | null; shortHead?: string | null } | null;
  };
  /**
   * Overnight Prompt Queue summary surfaced on the public MCP
   * payload per CODEX-OVERNIGHT-PROMPT-QUEUE-IMPL-01. Counts +
   * the safe-to-run-unattended flag are public-safe. Full row
   * content lives behind the admin tool `project.list_overnight_queue`.
   */
  overnightQueue?: {
    count?: number | null;
    recommendedTaskId?: string | null;
    safeToRunUnattended?: boolean | null;
    hasStaleEntries?: boolean | null;
  } | null;
};

const WORKER_NEEDS_DIRECTION_STATUSES = new Set([
  'idle',
  'needs_review',
  'blocked',
  'needs_user',
  'complete_waiting_approval',
]);
const DIRECTION_WORKERS = ['claude', 'codex', 'agent'] as const;

function getMcpCurrentState(snapshot: McpV2DashboardSnapshot | null): McpV2CurrentState | null {
  if (!snapshot?.projectCurrentState.ok) return null;
  const payload = snapshot.projectCurrentState.payload;
  return payload && typeof payload === 'object' ? payload as McpV2CurrentState : null;
}

function ageLabelMs(ageMs: number | null | undefined): string {
  if (typeof ageMs !== 'number' || !Number.isFinite(ageMs)) return '—';
  if (ageMs < 60_000) return `${Math.max(0, Math.floor(ageMs / 1000))}s ago`;
  if (ageMs < 3_600_000) return `${Math.floor(ageMs / 60_000)}m ago`;
  if (ageMs < 86_400_000) return `${Math.floor(ageMs / 3_600_000)}h ago`;
  return `${Math.floor(ageMs / 86_400_000)}d ago`;
}

function mcpFreshnessSummary(current: McpV2CurrentState | null): {
  label: string;
  stale: boolean;
  reason: string;
  updatedAt: string;
  ageLabel: string;
  ageMs: number | null;
} {
  const freshness = current?.freshness;
  const stale = freshness?.isStale === true;
  const reason = typeof freshness?.staleReason === 'string' ? freshness.staleReason : 'unknown';
  const updatedAt = freshness?.updatedAt ? new Date(freshness.updatedAt).toLocaleTimeString() : '—';
  const ageMs = typeof freshness?.ageMs === 'number' ? freshness.ageMs : null;
  const ageLabel = ageLabelMs(ageMs);
  if (!current) {
    return { label: 'MCP current-state unavailable', stale: true, reason: 'unavailable', updatedAt, ageLabel: '—', ageMs: null };
  }
  if (stale) return { label: `MCP readable · stale (${reason}) · ${ageLabel}`, stale, reason, updatedAt, ageLabel, ageMs };
  return { label: `MCP live · fresh · ${ageLabel}`, stale, reason, updatedAt, ageLabel, ageMs };
}

interface MarkerWritebackSummary {
  totalMarkers: number;
  perLane: Array<{ id: string; markerCount: number; mostRecent: string | null; markerHash: string }>;
  hasAny: boolean;
  qaSummary: string | null;
}

function summariseMarkerWriteback(current: McpV2CurrentState | null): MarkerWritebackSummary {
  const empty: MarkerWritebackSummary = { totalMarkers: 0, perLane: [], hasAny: false, qaSummary: null };
  if (!current?.agents || current.agents.length === 0) return empty;
  let total = 0;
  let qaSummary: string | null = null;
  const perLane = current.agents.map((a) => {
    const m = a.lastMarkers ?? null;
    const count = typeof m?.markerCount === 'number' ? m.markerCount : 0;
    total += count;
    let mostRecent: string | null = null;
    if (m) {
      mostRecent =
        m.MCP_RESULT ?? m.MCP_BLOCKER ?? m.MCP_TESTS ?? m.MCP_NEXT ?? m.MCP_COMMIT ?? null;
      if (!qaSummary && m.AGENT_QA_RESULT_JSON) {
        const qa = m.AGENT_QA_RESULT_JSON;
        if (qa.status || qa.gate || qa.platform) {
          qaSummary = `${a.id ?? 'lane'}: ${qa.status ?? '—'} · ${qa.gate ?? '—'} · ${qa.platform ?? '—'}`;
        }
      }
    }
    return {
      id: a.id ?? 'lane',
      markerCount: count,
      mostRecent,
      markerHash: typeof m?.markerHash === 'string' ? m.markerHash.slice(0, 8) : '',
    };
  });
  return { totalMarkers: total, perLane, hasAny: total > 0, qaSummary };
}

interface DeveloperModeRecommendation {
  recommendation: 'keep_on' | 'safe_to_turn_off' | 'unknown';
  shortLabel: string;
  reason: string;
}

function summariseDeveloperModeRecommendation(
  freshness: ReturnType<typeof mcpFreshnessSummary>,
  releaseGate: ReleaseGateSummary,
  laneHeartbeat: LaneHeartbeatSummary,
): DeveloperModeRecommendation {
  // Defensive defaults — Developer Mode stays ON unless every signal
  // says otherwise. See docs/MCP_LONGTERM_ACCESS_ARCHITECTURE.md § 2
  // for the canonical criteria. Mobile only checks the device-side
  // signals it can read; a fully "safe to turn OFF" verdict still
  // requires Aaron to confirm the off-device steps (Surface B
  // shipped, push wiring shipped, no active MCP-creation-fix
  // prompts).
  const reasons: string[] = [];
  if (freshness.stale) {
    reasons.push(`MCP freshness ${freshness.reason}`);
  }
  if (laneHeartbeat.ok && laneHeartbeat.driftWarning) {
    reasons.push('lane drift suspected');
  }
  if (!releaseGate.ok) {
    reasons.push('release gate not loaded');
  } else if (releaseGate.iosAllowed === null && releaseGate.androidAllowed === null) {
    reasons.push('release gate booleans unknown');
  }
  if (!freshness.stale && (!laneHeartbeat.ok || !laneHeartbeat.driftWarning) && releaseGate.ok) {
    return {
      recommendation: 'safe_to_turn_off',
      shortLabel: 'Developer Mode safe to turn OFF (device-side)',
      reason: 'MCP freshness fresh, lane heartbeat fresh, release gate readable. Off-device prerequisites (Surface B, push wiring, no active MCP fix prompts) still apply — confirm before flipping the toggle.',
    };
  }
  if (reasons.length === 0) {
    return {
      recommendation: 'unknown',
      shortLabel: 'Developer Mode status unknown',
      reason: 'Not enough signal yet — refresh and check back.',
    };
  }
  return {
    recommendation: 'keep_on',
    shortLabel: 'Keep Developer Mode ON',
    reason: reasons.join(' · '),
  };
}

interface LaneHeartbeatSummary {
  ok: boolean;
  laneCount: number;
  oldestLastSeenAgeMs: number | null;
  newestLastSeenAgeMs: number | null;
  driftWarning: boolean;
  /** Per-lane shorthand: "claude · idle · 12s" / "codex · working · stale 4m" */
  perLaneLines: string[];
  /** ISO timestamp of the freshest lastSeenAt across lanes. */
  freshestLastSeenAt: string | null;
  /** ISO timestamp of the freshest lastStateChangeAt across lanes. */
  freshestLastStateChangeAt: string | null;
}

const LANE_DRIFT_WARN_MS = 60_000;

function summariseLaneHeartbeat(current: McpV2CurrentState | null): LaneHeartbeatSummary {
  const empty: LaneHeartbeatSummary = {
    ok: false,
    laneCount: 0,
    oldestLastSeenAgeMs: null,
    newestLastSeenAgeMs: null,
    driftWarning: false,
    perLaneLines: [],
    freshestLastSeenAt: null,
    freshestLastStateChangeAt: null,
  };
  if (!current?.agents || current.agents.length === 0) return empty;
  const now = Date.now();
  let oldest: number | null = null;
  let newest: number | null = null;
  let freshSeen: string | null = null;
  let freshChange: string | null = null;
  const lines: string[] = [];
  for (const a of current.agents) {
    const seen = typeof a.lastSeenAt === 'string' ? a.lastSeenAt : typeof a.updatedAt === 'string' ? a.updatedAt : null;
    const seenT = seen ? Date.parse(seen) : NaN;
    let ageMs: number | null = null;
    if (Number.isFinite(seenT)) {
      ageMs = now - seenT;
      if (oldest === null || ageMs > oldest) oldest = ageMs;
      if (newest === null || ageMs < newest) newest = ageMs;
      if (!freshSeen || (seen && seen > freshSeen)) freshSeen = seen;
    }
    const change = typeof a.lastStateChangeAt === 'string' ? a.lastStateChangeAt : null;
    if (change && (!freshChange || change > freshChange)) freshChange = change;
    const stale = ageMs !== null && ageMs > LANE_DRIFT_WARN_MS;
    const ageLabel = ageMs === null ? 'no heartbeat' : stale ? `stale ${ageLabelMs(ageMs)}` : ageLabelMs(ageMs);
    lines.push(`${a.id ?? 'lane'} · ${a.status ?? 'unknown'} · ${ageLabel}`);
  }
  return {
    ok: true,
    laneCount: current.agents.length,
    oldestLastSeenAgeMs: oldest,
    newestLastSeenAgeMs: newest,
    driftWarning: oldest !== null && oldest > LANE_DRIFT_WARN_MS,
    perLaneLines: lines,
    freshestLastSeenAt: freshSeen,
    freshestLastStateChangeAt: freshChange,
  };
}

interface ReleaseGateSummary {
  ok: boolean;
  message: string | null;
  publicSafe: boolean;
  iosAllowed: boolean | null;
  androidAllowed: boolean | null;
  reason: string;
  installedIos: string | null;
  installedAndroid: number | null;
  targetIos: string | null;
  targetAndroid: number | null;
  shortLabel: string;
}

function summariseReleaseGate(snapshot: McpV2DashboardSnapshot | null): ReleaseGateSummary {
  const empty: ReleaseGateSummary = {
    ok: false,
    message: snapshot?.releaseGate?.ok === false ? snapshot.releaseGate.message : 'release.get_gate not loaded',
    publicSafe: false,
    iosAllowed: null,
    androidAllowed: null,
    reason: '—',
    installedIos: null,
    installedAndroid: null,
    targetIos: null,
    targetAndroid: null,
    shortLabel: 'Loading…',
  };
  if (!snapshot?.releaseGate?.ok) return empty;
  const payload = snapshot.releaseGate.payload as {
    buildAllowed?: { ios?: boolean; android?: boolean };
    reason?: string;
    publicSafe?: boolean;
    installedBuild?: { iosBuildNumber?: string | null; androidVersionCode?: number | null };
    targetBuild?: { iosBuildNumber?: string | null; androidVersionCode?: number | null };
  } | undefined;
  if (!payload || typeof payload !== 'object') return empty;
  const ios = payload.buildAllowed?.ios;
  const android = payload.buildAllowed?.android;
  const reason = typeof payload.reason === 'string' && payload.reason.trim().length > 0 ? payload.reason.trim() : '—';
  const iosLabel = ios === true ? 'iOS ✓' : ios === false ? 'iOS ✕' : 'iOS ?';
  const androidLabel = android === true ? 'Android ✓' : android === false ? 'Android ✕' : 'Android ?';
  return {
    ok: true,
    message: null,
    publicSafe: payload.publicSafe === true,
    iosAllowed: typeof ios === 'boolean' ? ios : null,
    androidAllowed: typeof android === 'boolean' ? android : null,
    reason,
    installedIos: payload.installedBuild?.iosBuildNumber ?? null,
    installedAndroid: typeof payload.installedBuild?.androidVersionCode === 'number' ? payload.installedBuild.androidVersionCode : null,
    targetIos: payload.targetBuild?.iosBuildNumber ?? null,
    targetAndroid: typeof payload.targetBuild?.androidVersionCode === 'number' ? payload.targetBuild.androidVersionCode : null,
    shortLabel: `${iosLabel} · ${androidLabel}`,
  };
}

interface LaneOverviewSummary {
  ok: boolean;
  total: number | null;
  byStatus: Record<string, number>;
  shortLabel: string;
  idleCount: number;
  workingCount: number;
  blockedCount: number;
  needsReviewCount: number;
}

function summariseLaneOverview(snapshot: McpV2DashboardSnapshot | null): LaneOverviewSummary {
  const empty: LaneOverviewSummary = {
    ok: false,
    total: null,
    byStatus: {},
    shortLabel: 'lanes —',
    idleCount: 0,
    workingCount: 0,
    blockedCount: 0,
    needsReviewCount: 0,
  };
  if (!snapshot?.laneOverview?.ok) return empty;
  const payload = snapshot.laneOverview.payload as {
    totalLanes?: number;
    byStatus?: Record<string, number>;
  } | undefined;
  if (!payload || typeof payload !== 'object') return empty;
  const byStatus = payload.byStatus ?? {};
  const total = typeof payload.totalLanes === 'number' ? payload.totalLanes : null;
  const parts = Object.entries(byStatus).filter(([, v]) => typeof v === 'number' && v > 0).map(([k, v]) => `${k}=${v}`);
  const shortLabel = parts.length > 0 ? parts.join(' / ') : 'all idle';
  return {
    ok: true,
    total,
    byStatus,
    shortLabel,
    idleCount: typeof byStatus.idle === 'number' ? byStatus.idle : 0,
    workingCount: typeof byStatus.working === 'number' ? byStatus.working : 0,
    blockedCount: typeof byStatus.blocked === 'number' ? byStatus.blocked : 0,
    needsReviewCount: typeof byStatus.needs_review === 'number' ? byStatus.needs_review : 0,
  };
}

function mcpRule12Status(snapshot: McpV2DashboardSnapshot | null): {
  visible: boolean;
  label: string;
} {
  const payload = snapshot?.projectOperatingRules.ok ? snapshot.projectOperatingRules.payload : null;
  const rules = (payload as { rules?: Array<{ id?: number; title?: string }> } | null)?.rules ?? [];
  const rule12 = rules.find((rule) => rule.id === 12);
  if (!rule12) return { visible: false, label: 'Rule 12 not loaded' };
  return { visible: true, label: rule12.title ?? 'Coders run all laptop commands' };
}

function workerNeedsDirection(status: string | null | undefined): boolean {
  return WORKER_NEEDS_DIRECTION_STATUSES.has((status ?? '').trim().toLowerCase());
}

function allWorkersDirectionState(current: McpV2CurrentState | null): {
  key: string | null;
  waitingWorkers: string[];
  missingWorkers: string[];
  freshnessTimestamp: string;
} {
  const freshness = current?.freshness;
  const freshnessTimestamp = freshness?.updatedAt ?? '—';
  if (!current || freshness?.isStale === true) {
    return { key: null, waitingWorkers: [], missingWorkers: [], freshnessTimestamp };
  }
  const agents = current.agents ?? [];
  const waitingWorkers: string[] = [];
  const missingWorkers: string[] = [];
  const keyParts = [freshness?.updatedAt ?? 'unknown'];

  for (const worker of DIRECTION_WORKERS) {
    const agent = agents.find((entry) => entry.id === worker);
    if (!agent) {
      missingWorkers.push(worker);
      continue;
    }
    keyParts.push(worker, agent.status ?? 'unknown', agent.lastCommit ?? 'none');
    if (workerNeedsDirection(agent.status)) waitingWorkers.push(worker);
  }

  if (missingWorkers.length > 0 || waitingWorkers.length !== DIRECTION_WORKERS.length) {
    return { key: null, waitingWorkers, missingWorkers, freshnessTimestamp };
  }

  return {
    key: [
      ...keyParts,
      current.currentPriority ?? '',
      current.nextAction ?? '',
    ].join('|'),
    waitingWorkers,
    missingWorkers,
    freshnessTimestamp,
  };
}

function connectorDataSourceLabel(snapshot: ConnectorSnapshot | null): string {
  if (!snapshot) return 'repo-only / error';
  const dataSources: Array<ConnectorDataSource | undefined> = [
    snapshot.workStatus?.dataSource,
    snapshot.coderLanes?.dataSource,
    snapshot.buildStatus?.dataSource,
    snapshot.handoff?.dataSource,
    snapshot.terminalSummary?.dataSource,
  ].filter(Boolean);
  if (dataSources.length === 0) {
    return snapshot.source === 'mcp' ? 'supabase or worker' : 'fallback backend';
  }
  const sourceNames = Array.from(new Set(dataSources.map((source) => source?.source).filter(Boolean)));
  if (sourceNames.includes('placeholder') || dataSources.some((source) => source?.schemaRequired === true)) {
    return 'placeholder';
  }
  if (sourceNames.includes('supabase')) return 'supabase';
  return sourceNames.join(' / ') || 'unknown';
}

function buildAgentAuditPrompt(snapshot: ConnectorSnapshot | null): string {
  const work = snapshot?.workStatus ?? null;
  const lanes = snapshot?.coderLanes?.lanes ?? [];
  const laneSummary = lanes.length > 0
    ? lanes.map((lane) => `${lane.laneId}:${lane.status}`).join(', ')
    : 'no lanes reported';
  return [
    'PROMPT-ID: AGENT-MOBILE-UX-AUDIT-FROM-PHONE-01',
    'TYPE: AGENT / MOBILE UX AUDIT WORKER',
    'LANE: Mobile app UX audit only',
    '',
    'RULES',
    '- Work only from normal tester/user UX evidence.',
    '- Do not touch backend, Cloudflare, Supabase, MCP auth, health source logic, or app version/build numbers.',
    '- Do not add build triggers, raw terminal control, backlog editing, or paid AI.',
    '- Normal testers must not see Admin/Dev or coder state.',
    '',
    'CURRENT APP-CONTROL STATUS',
    `Priority: ${work?.currentPriority ?? '—'}`,
    `Blocker: ${work?.currentBlocker ?? 'none'}`,
    `Next action: ${work?.nextAction ?? '—'}`,
    `MCP: ${connectorSnapshotLabel(snapshot)} · ${connectorPayloadFreshnessLabel(snapshot)}`,
    `Lanes: ${laneSummary}`,
    '',
    'TASK',
    'Audit the mobile app UX from screenshots/device feedback. Identify tester-facing clutter, confusing hierarchy, duplicate actions, and developer/debug text that should be hidden or moved to Admin/Dev. Return findings and the smallest safe mobile-only patch plan.',
    '',
    'OUTPUT',
    '- Findings by screen',
    '- Smallest safe patch',
    '- What must stay untouched',
    '- Manual iPhone/Android verification checklist',
  ].join('\n');
}

/** Static label list for the dynamic prompt-bridge buttons. The
 * body of each prompt is computed at render time from the
 * `useOwnerWorkflowStore` context so changes to priority / blocker
 * / last status flow through without an app rebuild. */
const BRIDGE_PROMPT_KINDS = [
  'claude_code',
  'claude_chrome',
  'chatgpt_status',
  'codex',
  'current_status',
  'terminal_check',
] as const;
type BridgePromptKind = typeof BRIDGE_PROMPT_KINDS[number];

const BRIDGE_PROMPT_LABELS: Record<BridgePromptKind, string> = {
  claude_code: 'Copy next Claude Code prompt',
  claude_chrome: 'Copy Claude Chrome prompt',
  chatgpt_status: 'Copy ChatGPT check / status prompt',
  codex: 'Copy Codex prompt',
  current_status: 'Copy current status block',
  terminal_check: 'Copy terminal check prompt',
};

/** External dashboard / Termius shortcuts. Each is a `Linking.openURL`
 * with a single fallback path documented inline. None of them store
 * credentials; Termius / Play Console / ASC handle their own login. */
const EXTERNAL_SHORTCUTS: Array<{ label: string; url: string; fallbackHint?: string }> = [
  { label: 'Open Termius', url: 'termius://', fallbackHint: 'If Termius is not installed, the App Store opens. tmux attach instructions are also copyable below.' },
  { label: 'Open GitHub Actions', url: GITHUB_ACTIONS_URL },
  { label: 'Open EAS builds', url: EXPO_BUILDS_URL },
  { label: 'Open Play Console', url: PLAY_CONSOLE_URL },
  { label: 'Open App Store Connect', url: APPSTORE_CONNECT_URL },
];

async function fetchAdminStatus(): Promise<AdminStatus | null> {
  try {
    const apiBase = (process.env.EXPO_PUBLIC_AI_PUBLIC_URL ?? '').replace(/\/$/, '');
    const memToken = process.env.EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN ?? '';
    if (!apiBase || !memToken) return null;
    const res = await fetch(`${apiBase}/admin/status`, { headers: { 'x-athlete-memory-token': memToken } });
    if (!res.ok) return null;
    const json: any = await res.json();
    return {
      workflowDispatchAvailable: !!json?.workflowDispatchAvailable,
      workflowAllowlist: Array.isArray(json?.workflowAllowlist) ? json.workflowAllowlist : [],
      blockers: Array.isArray(json?.blockers) ? json.blockers : [],
      androidBuildWorkflowAvailable: !!json?.androidBuildWorkflowAvailable,
      iosBuildWorkflowAvailable: !!json?.iosBuildWorkflowAvailable,
      releaseAuditWorkflowAvailable: !!json?.releaseAuditWorkflowAvailable,
      playUploadConfigured: typeof json?.playUploadConfigured === 'boolean' ? json.playUploadConfigured : null,
      testflightSubmitConfigured: typeof json?.testflightSubmitConfigured === 'boolean' ? json.testflightSubmitConfigured : null,
      testflightGroupAssignmentConfigured: typeof json?.testflightGroupAssignmentConfigured === 'boolean' ? json.testflightGroupAssignmentConfigured : null,
      androidPlayPromoteAutomatic: typeof json?.androidPlayPromoteAutomatic === 'boolean' ? json.androidPlayPromoteAutomatic : null,
      otaBlocked: !!json?.otaBlocked,
      otaBlockerReason: typeof json?.otaBlockerReason === 'string' ? json.otaBlockerReason : undefined,
    };
  } catch { return null; }
}

async function fetchBackendHealth(): Promise<BackendHealth> {
  const checkedAt = new Date().toISOString();
  try {
    const apiBase = (process.env.EXPO_PUBLIC_AI_BACKEND_URL ?? '').replace(/\/$/, '');
    const internalToken = process.env.EXPO_PUBLIC_INTERNAL_API_TOKEN ?? '';
    const athleteId = process.env.EXPO_PUBLIC_ATHLETE_ID ?? '';
    if (!apiBase || !internalToken || !athleteId) {
      return { ok: false, totalNormalizedDays: null, firstDate: null, lastDate: null, sourcesConnected: null, readinessStatus: null, checkedAt, error: 'Backend env not configured.' };
    }
    const res = await fetch(`${apiBase}/athletes/${encodeURIComponent(athleteId)}/ai-health-context`, {
      headers: { 'x-internal-token': internalToken },
    });
    if (!res.ok) return { ok: false, totalNormalizedDays: null, firstDate: null, lastDate: null, sourcesConnected: null, readinessStatus: null, checkedAt, error: `HTTP ${res.status}` };
    const json: any = await res.json();
    return {
      ok: true,
      totalNormalizedDays: json?.data_coverage?.total_normalized_days ?? null,
      firstDate: json?.data_coverage?.first_date ?? null,
      lastDate: json?.data_coverage?.last_date ?? null,
      sourcesConnected: Array.isArray(json?.sources_connected) ? json.sources_connected.length : null,
      readinessStatus: json?.readiness?.status ?? null,
      checkedAt,
    };
  } catch (e: any) {
    return { ok: false, totalNormalizedDays: null, firstDate: null, lastDate: null, sourcesConnected: null, readinessStatus: null, checkedAt, error: e?.message ?? 'unknown' };
  }
}

export default function AdminDevScreen() {
  const router = useRouter();
  const userEmail = useAuthStore((s) => s.user?.email ?? null);
  const isAdmin = userEmail != null && ADMIN_EMAILS.has(userEmail.toLowerCase());
  const devUnlocked = useDevUnlockStore((s) => s.unlocked);
  const lockDevTools = useDevUnlockStore((s) => s.lock);
  const localDevAccess = __DEV__ && devUnlocked;
  const accessGranted = isAdmin || localDevAccess;

  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [adminStatus, setAdminStatus] = useState<AdminStatus | null>(null);
  const [connectorSnapshot, setConnectorSnapshot] = useState<ConnectorSnapshot | null>(null);
  const [mcpV2Snapshot, setMcpV2Snapshot] = useState<McpV2DashboardSnapshot | null>(null);
  const [mcpV2Error, setMcpV2Error] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [openPromptIdx, setOpenPromptIdx] = useState<number | null>(null);
  const [handoffOpen, setHandoffOpen] = useState(false);
  const allWorkerDirectionAlertsEnabled = useAdminDevNotificationStore((s) => s.allWorkerDirectionAlertsEnabled);
  const setAllWorkerDirectionAlertsEnabled = useAdminDevNotificationStore((s) => s.setAllWorkerDirectionAlertsEnabled);
  const lastAllWorkerDirectionAlertKey = useAdminDevNotificationStore((s) => s.lastAllWorkerDirectionAlertKey);
  const markAllWorkerDirectionAlertSeen = useAdminDevNotificationStore((s) => s.markAllWorkerDirectionAlertSeen);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const [h, a, c, m] = await Promise.all([
        fetchBackendHealth(),
        fetchAdminStatus(),
        isAdmin ? fetchConnectorSnapshot() : Promise.resolve(null),
        isAdmin ? fetchMcpV2DashboardSnapshot().catch((err: unknown) => {
          setMcpV2Error(err instanceof Error ? err.message : 'mcp_v2 fetch failed');
          return null;
        }) : Promise.resolve(null),
      ]);
      setHealth(h);
      setAdminStatus(a);
      setConnectorSnapshot(c);
      setMcpV2Snapshot(m);
      if (m) setMcpV2Error(null);
    } finally { setRefreshing(false); }
  }, [isAdmin]);

  useEffect(() => { void refresh(); }, [refresh]);

  // Auto-refresh on app foreground/resume so installed-device QA
  // sees the latest MCP snapshot without a manual pull-to-refresh.
  // Subscription is added once on mount; the listener calls the
  // current `refresh` via a ref so we don't re-subscribe whenever
  // the callback identity changes.
  const refreshRef = useRef(refresh);
  useEffect(() => { refreshRef.current = refresh; }, [refresh]);
  useEffect(() => {
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active') {
        void refreshRef.current();
      }
    });
    return () => { sub.remove(); };
  }, []);

  // Approval gates store — local-first; no server writeback yet.
  const approvalGates = useApprovalGatesStore((s) => s.gates);
  const approvalRefreshing = useApprovalGatesStore((s) => s.refreshing);
  const approvalLedgerNotePreview = useApprovalGatesStore((s) => s.ledgerNotePreview);
  const approvalRecentNotes = useApprovalGatesStore((s) => s.recentLedgerNotes);
  const hydrateApprovalGates = useApprovalGatesStore((s) => s.hydrate);
  const refreshApprovalGates = useApprovalGatesStore((s) => s.refresh);
  const approveApprovalGate = useApprovalGatesStore((s) => s.approve);
  const deferApprovalGate = useApprovalGatesStore((s) => s.defer);
  const cancelApprovalGate = useApprovalGatesStore((s) => s.cancel);
  useEffect(() => { void hydrateApprovalGates(); }, [hydrateApprovalGates]);

  // Spend gates store — local-first; export-prompt for out-of-band AI calls.
  const spendGates = useSpendGatesStore((s) => s.gates);
  const spendRefreshing = useSpendGatesStore((s) => s.refreshing);
  const hydrateSpendGates = useSpendGatesStore((s) => s.hydrate);
  const refreshSpendGates = useSpendGatesStore((s) => s.refresh);
  const approveSpendGate = useSpendGatesStore((s) => s.approve);
  const deferSpendGate = useSpendGatesStore((s) => s.defer);
  const cancelSpendGate = useSpendGatesStore((s) => s.cancel);
  const exportSpendPrompt = useSpendGatesStore((s) => s.exportPrompt);
  useEffect(() => { void hydrateSpendGates(); }, [hydrateSpendGates]);

  // Research jobs store — Deep Research offload (no auto-call).
  const researchJobs = useResearchJobsStore((s) => s.jobs);
  const hydrateResearchJobs = useResearchJobsStore((s) => s.hydrate);
  const refreshResearchArtifacts = useResearchJobsStore((s) => s.refreshArtifactStatuses);
  const exportResearchPrompt = useResearchJobsStore((s) => s.exportPrompt);
  const markResearchSubmitted = useResearchJobsStore((s) => s.markSubmitted);
  const markResearchCompleted = useResearchJobsStore((s) => s.markCompleted);
  const cancelResearchJob = useResearchJobsStore((s) => s.cancel);
  const [researchPasteState, setResearchPasteState] = useState<Record<string, string>>({});
  useEffect(() => { void hydrateResearchJobs(); }, [hydrateResearchJobs]);

  const buildInfo = useMemo(() => {
    const expoExtra = Constants.expoConfig?.extra as Record<string, unknown> | undefined;
    const easExtra = expoExtra?.eas as Record<string, unknown> | undefined;
    const gitCommit =
      process.env.EXPO_PUBLIC_GIT_COMMIT
      ?? expoExtra?.gitCommit
      ?? easExtra?.gitCommit;
    return {
      appVersion: Application.nativeApplicationVersion ?? '—',
      buildNumber: Application.nativeBuildVersion ?? '—',
      repoHead: compactGitCommit(gitCommit),
      platform: Platform.OS,
      runtimeVersion: Updates.runtimeVersion ?? '—',
      updateId: (Updates as any).updateId ?? null,
      channel: (Updates as any).channel ?? null,
      isEmbeddedLaunch: (Updates as any).isEmbeddedLaunch ?? null,
    };
  }, []);

  // expo-clipboard isn't bundled in the current native build, so we
  // surface prompt text inside selectable RNText blocks. Users
  // long-press to invoke the system copy menu — no new native dep.

  if (!accessGranted) {
    return (
      <View style={styles.container}>
        <Stack.Screen options={{ title: 'Admin / Dev', headerBackTitle: 'Settings' }} />
        <Text style={styles.heading}>Admin / Dev</Text>
        <Text style={styles.body}>
          This screen is gated to the project admin account, or after a local 7-tap unlock on the Settings → About → Version row.
        </Text>
        <Pressable style={styles.btn} onPress={() => router.back()}>
          <Text style={styles.btnText}>Back to Settings</Text>
        </Pressable>
      </View>
    );
  }

  const apiHost = (process.env.EXPO_PUBLIC_AI_BACKEND_URL ?? '').replace(/^https?:\/\//, '').split('/')[0] || '—';

  // Truth chips — derived from adminStatus + buildInfo so the UI can
  // distinguish live / uploaded / repo-only / blocked at a glance.
  const androidPromoteAuto = adminStatus?.androidPlayPromoteAutomatic === true;
  const iosBuildAvailable = adminStatus?.iosBuildWorkflowAvailable === true;
  const androidBuildAvailable = adminStatus?.androidBuildWorkflowAvailable === true;
  const dispatchAvailable = adminStatus?.workflowDispatchAvailable === true;
  const connectorWork = connectorSnapshot?.workStatus ?? null;
  const mcpCurrentState = getMcpCurrentState(mcpV2Snapshot);
  const mcpFreshness = mcpFreshnessSummary(mcpCurrentState);
  // Diagnostics visibility: any non-ok call, OR null snapshot, OR
  // unavailable freshness — surfaces the safe per-call category +
  // HTTP status to the panel below. We never render the raw response
  // body or token; the upstream client already discards both.
  const mcpV2DiagnosticsAnyFailed = !!(mcpV2Snapshot?.diagnostics?.some((d) => d.reason !== 'ok'));
  const mcpV2DiagnosticsVisible = mcpV2Snapshot == null
    || mcpV2DiagnosticsAnyFailed
    || mcpFreshness.reason === 'unavailable';
  const rule12 = mcpRule12Status(mcpV2Snapshot);
  const mcpAgents = mcpCurrentState?.agents ?? [];
  const mcpClaudeLane = mcpAgents.find((agent) => agent.id === 'claude') ?? null;
  const mcpCodexLane = mcpAgents.find((agent) => agent.id === 'codex') ?? null;
  const laneProgress: LaneProgressSummary = summariseLaneProgress(mcpCurrentState ?? null);
  const overnightQueueSummary = mcpCurrentState?.overnightQueue ?? null;
  const overnightQueueCount = typeof overnightQueueSummary?.count === 'number' ? overnightQueueSummary.count : 0;
  const overnightQueueHasStale = overnightQueueSummary?.hasStaleEntries === true;
  const overnightQueueSafeToRun = overnightQueueSummary?.safeToRunUnattended === true;
  const overnightQueueRecommendedId = typeof overnightQueueSummary?.recommendedTaskId === 'string' ? overnightQueueSummary.recommendedTaskId : null;
  const releaseGateSummary = summariseReleaseGate(mcpV2Snapshot);
  const laneOverviewSummary = summariseLaneOverview(mcpV2Snapshot);
  const laneHeartbeat = summariseLaneHeartbeat(mcpCurrentState);
  const developerModeRecommendation = summariseDeveloperModeRecommendation(mcpFreshness, releaseGateSummary, laneHeartbeat);
  const markerWriteback = summariseMarkerWriteback(mcpCurrentState);
  const nowPriority = mcpCurrentState?.currentPriority ?? connectorWork?.currentPriority ?? CURRENT_PRIORITY;
  const nowBlocker = mcpCurrentState?.currentBlocker ?? connectorWork?.currentBlocker ?? 'No MCP blocker reported.';
  const nowNextAction = mcpCurrentState?.nextAction ?? connectorWork?.nextAction ?? NEXT_ACTION;
  const nowLanes = connectorSnapshot?.coderLanes?.lanes ?? [];
  const laneStatusCounts = nowLanes.reduce<Record<string, number>>((acc, lane) => {
    acc[lane.status] = (acc[lane.status] ?? 0) + 1;
    return acc;
  }, {});
  const laneCountSummary = Object.entries(laneStatusCounts)
    .map(([status, count]) => `${count} ${status}`)
    .join(' · ');
  const firstScreenLaneCount = nowLanes.length > 0 ? nowLanes.length : mcpAgents.length;
  const firstScreenLaneMeta = laneCountSummary
    || (mcpAgents.length > 0
      ? mcpAgents.map((agent) => `${agent.id ?? 'lane'}:${agent.status ?? 'unknown'}`).join(' · ')
      : 'no status');
  const nowLaneSummary = nowLanes.length > 0
    ? nowLanes.map((lane) => `${lane.laneId}: ${lane.status}`).join(' · ')
    : mcpAgents.length > 0
      ? mcpAgents.map((agent) => `${agent.id ?? 'lane'}: ${agent.status ?? 'unknown'}`).join(' · ')
    : 'No lane status yet.';
  const nowRepoSummary = connectorWork
    ? `${connectorWork.repoStatus.branch}@${connectorWork.repoStatus.head} · ${connectorWork.repoStatus.dirtyFileCount} dirty`
    : mcpCurrentState?.liveStatus?.repo
      ? `${mcpCurrentState.liveStatus.repo.branch ?? 'main'}@${mcpCurrentState.liveStatus.repo.shortHead ?? '—'}`
      : 'Repo-only until MCP work status loads.';
  const nowBuildSummary = connectorSnapshot?.buildStatus
    ? `Android ${connectorSnapshot.buildStatus.android.versionCode ?? '—'} · ${connectorSnapshot.buildStatus.android.githubStatus ?? '—'} / iOS ${connectorSnapshot.buildStatus.ios.buildNumber ?? '—'} · ${connectorSnapshot.buildStatus.ios.githubStatus ?? '—'}`
    : mcpCurrentState?.liveStatus
      ? `Android ${mcpCurrentState.liveStatus.android?.versionCode ?? '—'} · ${mcpCurrentState.liveStatus.android?.status ?? '—'} / iOS ${mcpCurrentState.liveStatus.ios?.buildNumber ?? '—'} · ${mcpCurrentState.liveStatus.ios?.status ?? '—'}`
    : 'Build status not loaded.';
  const nowSnapshotLabel = connectorSnapshotLabel(connectorSnapshot);
  const nowSourceLabel = connectorDataSourceLabel(connectorSnapshot);
  const nowBridgeFreshness = connectorPayloadFreshnessLabel(connectorSnapshot);
  const mcpStatus = isAdmin
    ? connectorSnapshot
      ? `${nowSnapshotLabel} · ${nowBridgeFreshness} · fetched ${connectorCheckedTime(connectorSnapshot.checkedAt)}`
      : refreshing
        ? 'MCP refreshing…'
        : `${nowSnapshotLabel} · MCP not connected`
    : null;
  const safeToBuildLabel = 'Agent confirmation required before EAS build';
  const deployCommandAllowedByDocs = nowNextAction.toLowerCase().includes('wrangler deploy');
  const fs008Visible = nowNextAction.toLowerCase().includes('fs-008') || nowPriority.toLowerCase().includes('fs-008');
  const workerDirectionState = allWorkersDirectionState(mcpCurrentState);
  const showAllWorkersBanner = isAdmin
    && allWorkerDirectionAlertsEnabled
    && workerDirectionState.key != null
    && workerDirectionState.key !== lastAllWorkerDirectionAlertKey;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Stack.Screen options={{ title: 'Admin / Dev', headerBackTitle: 'Settings' }} />
      <Text style={styles.heading}>Admin / Dev</Text>
      <Text style={styles.subtitle}>Owner control centre. Compact status. No secrets. No remote shell.</Text>

      <Section title="Now">
        {showAllWorkersBanner && (
          <View style={styles.noticeBlock}>
            <Text style={styles.chipLabel}>Worker input needed</Text>
            <Text style={styles.chipBody}>All workers need direction</Text>
            <Text style={styles.note}>Priority: {nowPriority}</Text>
            <Text style={styles.note}>Next: {nowNextAction}</Text>
            <Text style={styles.note}>Waiting: {workerDirectionState.waitingWorkers.join(', ')}</Text>
            <Text style={styles.note}>MCP freshness: {workerDirectionState.freshnessTimestamp}</Text>
            <Pressable
              style={styles.btn}
              onPress={() => {
                if (workerDirectionState.key) void markAllWorkerDirectionAlertSeen(workerDirectionState.key);
              }}>
              <Text style={styles.btnText}>Acknowledge</Text>
            </Pressable>
          </View>
        )}
        {isAdmin && (
          <View style={styles.summaryGrid}>
            <View style={styles.summaryTile}>
              <Text style={styles.chipLabel}>MCP</Text>
              <Text style={styles.summaryValue}>{refreshing && !mcpV2Snapshot ? 'Refreshing…' : mcpFreshness.label}</Text>
              <Text style={styles.summaryMeta}>updated {mcpFreshness.updatedAt}</Text>
            </View>
            <View style={styles.summaryTile}>
              <Text style={styles.chipLabel}>Fetched</Text>
              <Text style={styles.summaryValue}>{connectorSnapshot ? connectorCheckedTime(connectorSnapshot.checkedAt) : '—'}</Text>
              <Text style={styles.summaryMeta}>{nowSourceLabel}</Text>
            </View>
            <View style={styles.summaryTile}>
              <Text style={styles.chipLabel}>Lanes</Text>
              <Text style={styles.summaryValue}>{laneOverviewSummary.ok ? `${laneOverviewSummary.total ?? 0}` : `${firstScreenLaneCount}`}</Text>
              <Text style={styles.summaryMeta}>{laneOverviewSummary.ok ? laneOverviewSummary.shortLabel : firstScreenLaneMeta}</Text>
            </View>
            <View style={styles.summaryTile}>
              <Text style={styles.chipLabel}>Idle</Text>
              <Text style={styles.summaryValue}>{laneOverviewSummary.idleCount}</Text>
              <Text style={styles.summaryMeta}>
                {laneOverviewSummary.workingCount} working · {laneOverviewSummary.blockedCount} blocked · {laneOverviewSummary.needsReviewCount} review
              </Text>
            </View>
            <View style={styles.summaryTile}>
              <Text style={styles.chipLabel}>Release gate</Text>
              <Text style={styles.summaryValue}>{releaseGateSummary.ok ? releaseGateSummary.shortLabel : 'Loading…'}</Text>
              <Text style={styles.summaryMeta} numberOfLines={2}>
                {releaseGateSummary.ok
                  ? releaseGateSummary.reason
                  : releaseGateSummary.message ?? 'release.get_gate not loaded'}
              </Text>
            </View>
            <View style={styles.summaryTile}>
              <Text style={styles.chipLabel}>Rule 12</Text>
              <Text style={styles.summaryValue}>{rule12.visible ? 'Live' : '—'}</Text>
              <Text style={styles.summaryMeta} numberOfLines={2}>{rule12.label}</Text>
            </View>
            <View style={styles.summaryTile}>
              <Text style={styles.chipLabel}>Build / repo</Text>
              <Text style={styles.summaryValue}>{connectorSnapshot?.buildStatus ? 'Loaded' : 'Repo-only'}</Text>
              <Text style={styles.summaryMeta}>{nowRepoSummary}</Text>
            </View>
          </View>
        )}
        <View style={styles.chipBlock}>
          <Text style={styles.chipLabel}>Build gate</Text>
          <Text style={styles.chipBody}>
            {releaseGateSummary.ok
              ? `${releaseGateSummary.shortLabel} · ${safeToBuildLabel}`
              : safeToBuildLabel}
          </Text>
          {releaseGateSummary.ok && (
            <Text style={styles.note}>Reason: {releaseGateSummary.reason}</Text>
          )}
          {releaseGateSummary.ok && (releaseGateSummary.installedAndroid != null || releaseGateSummary.installedIos != null) && (
            <Text style={styles.note}>
              Installed Android v{releaseGateSummary.installedAndroid ?? '—'} · iOS Build {releaseGateSummary.installedIos ?? '—'}
              {releaseGateSummary.targetAndroid != null || releaseGateSummary.targetIos != null
                ? `  →  target Android v${releaseGateSummary.targetAndroid ?? '—'} · iOS Build ${releaseGateSummary.targetIos ?? '—'}`
                : ''}
            </Text>
          )}
          <Text style={styles.note}>No EAS build until Agent confirms the on-device value and Aaron approves.</Text>
        </View>
        {/* Build-state separation: makes the repo-only vs installed-
            build-verified distinction explicit so a tester does not
            confuse a repo-side patch (e.g. Health Connect activity-
            alias) with an installed-device confirmation. The badge
            tone is intentionally neutral until a versionCode is
            installed; only the matched-installed state goes green. */}
        <View style={styles.chipBlock}>
          <Text style={styles.chipLabel}>Build state separation</Text>
          {(() => {
            const installedAndroid = releaseGateSummary.ok ? releaseGateSummary.installedAndroid : null;
            const targetAndroid = releaseGateSummary.ok ? releaseGateSummary.targetAndroid : null;
            const installedIos = releaseGateSummary.ok ? releaseGateSummary.installedIos : null;
            const targetIos = releaseGateSummary.ok ? releaseGateSummary.targetIos : null;
            const androidMatched = installedAndroid != null && targetAndroid != null && installedAndroid === targetAndroid;
            const iosMatched = installedIos != null && targetIos != null && String(installedIos) === String(targetIos);
            const androidLabel = installedAndroid == null
              ? `Android — repo-only (target v${targetAndroid ?? '—'} not installed)`
              : androidMatched
                ? `Android — installed-build verified (v${installedAndroid})`
                : `Android — repo-only patch ahead of installed (installed v${installedAndroid} → target v${targetAndroid ?? '—'})`;
            const iosLabel = installedIos == null
              ? `iOS — repo-only (target build ${targetIos ?? '—'} not installed)`
              : iosMatched
                ? `iOS — installed-build verified (build ${installedIos})`
                : `iOS — repo-only patch ahead of installed (installed ${installedIos} → target ${targetIos ?? '—'})`;
            return (
              <>
                <View style={[styles.laneProgressRow, { marginTop: 0 }]}>
                  <Text style={styles.chipBody}>{androidLabel}</Text>
                  <StatusPill label={androidMatched ? 'verified' : 'repo-only'} tone={androidMatched ? 'fresh' : 'neutral'} />
                </View>
                <View style={styles.laneProgressRow}>
                  <Text style={styles.chipBody}>{iosLabel}</Text>
                  <StatusPill label={iosMatched ? 'verified' : 'repo-only'} tone={iosMatched ? 'fresh' : 'neutral'} />
                </View>
              </>
            );
          })()}
          <Text style={styles.note}>
            Repo-only = patch is on main but not yet bundled into an installed build. Installed-build verified = the installed versionCode/build matches the patched target. No EAS build is triggered from this screen.
          </Text>
        </View>
        {isAdmin && (
          <View style={styles.chipBlock}>
            <Text style={styles.chipLabel}>Owner alerts</Text>
            <Text style={styles.chipBody}>
              All-worker direction banner: {allWorkerDirectionAlertsEnabled ? 'enabled' : 'disabled'}
            </Text>
            <Text style={styles.note}>
              Fires only when MCP is fresh and Claude, Codex, and Agent are all idle, blocked, need review, need user input, or complete waiting approval.
            </Text>
            {workerDirectionState.missingWorkers.length > 0 && (
              <Text style={styles.note}>
                {workerDirectionState.missingWorkers.map((worker) => `${worker[0]?.toUpperCase()}${worker.slice(1)} not reporting yet`).join(' · ')}
              </Text>
            )}
            <Text style={styles.note}>Push notifications are not configured in this app, so this is in-app only.</Text>
            <Pressable
              style={styles.btn}
              onPress={() => void setAllWorkerDirectionAlertsEnabled(!allWorkerDirectionAlertsEnabled)}>
              <Text style={styles.btnText}>{allWorkerDirectionAlertsEnabled ? 'Disable worker direction banner' : 'Enable worker direction banner'}</Text>
            </Pressable>
          </View>
        )}
        {mcpFreshness.stale && (
          <View style={styles.warningBlock}>
            <Text style={styles.chipLabel}>Stale writeback</Text>
            <Text style={styles.chipBody}>MCP readable but writeback is stale ({mcpFreshness.ageLabel}). Run bridge snapshot/verify or deploy worker.</Text>
            <Text style={styles.note}>Reason: {mcpFreshness.reason} · updated {mcpFreshness.updatedAt}</Text>
          </View>
        )}
        {/* MCP transport diagnostics — visible only on admin and only
            when the v2 snapshot has any non-ok call OR the snapshot
            is null/error. Renders categorical reasons + HTTP status
            codes + the resolved endpoint URL so installed-device QA
            can see WHY MCP is unavailable without exposing tokens or
            raw response bodies. Added 2026-05-09 alongside the
            base-URL normalisation fix. */}
        {isAdmin && mcpV2DiagnosticsVisible && (
          <View style={styles.warningBlock}>
            <Text style={styles.chipLabel}>MCP transport diagnostics</Text>
            <Text style={styles.chipBody}>
              {mcpV2Snapshot == null
                ? `MCP fetch did not return a snapshot${mcpV2Error ? ` · ${mcpV2Error}` : ''}.`
                : `MCP fetch reached the worker${mcpV2DiagnosticsAnyFailed ? ' but some calls failed.' : ' — see per-call statuses below.'}`}
            </Text>
            {mcpV2Snapshot?.resolvedCoreEndpoint && (
              <Text style={styles.note}>Core endpoint: {mcpV2Snapshot.resolvedCoreEndpoint}</Text>
            )}
            {mcpV2Snapshot?.resolvedAdminEndpoint && (
              <Text style={styles.note}>Admin endpoint: {mcpV2Snapshot.resolvedAdminEndpoint}</Text>
            )}
            {mcpV2Snapshot && (
              <Text style={styles.note}>Env source: {mcpV2Snapshot.envSource} · fetched in {mcpV2Snapshot.fetchDurationMs}ms</Text>
            )}
            {mcpV2Snapshot?.diagnostics?.map((d) => (
              <Text key={`mcp-diag-${d.endpoint}`} style={styles.note}>
                {d.endpoint}: {d.reason}{d.httpStatus != null ? ` · HTTP ${d.httpStatus}` : ''}
              </Text>
            ))}
            <Text style={styles.note}>
              Diagnostics never include tokens, raw bodies, or stack traces — only the categorical reason and HTTP status.
            </Text>
          </View>
        )}
        {laneHeartbeat.ok && laneHeartbeat.driftWarning && (
          <View style={styles.warningBlock}>
            <Text style={styles.chipLabel}>Lane drift suspected</Text>
            <Text style={styles.chipBody}>
              Terminal/MCP drift suspected — lane heartbeat is stale ({ageLabelMs(laneHeartbeat.oldestLastSeenAgeMs)}). Start `npm run bridge:watch` on the laptop, or run `npm run bridge:snapshot` once to refresh.
            </Text>
            {laneHeartbeat.perLaneLines.map((line, idx) => (
              <Text key={`heartbeat-${idx}`} style={styles.note}>{line}</Text>
            ))}
          </View>
        )}
        {isAdmin && (
          <View style={styles.chipBlock}>
            <Text style={styles.chipLabel}>Live marker writeback</Text>
            <Text style={styles.chipBody}>
              {markerWriteback.hasAny
                ? `${markerWriteback.totalMarkers} marker${markerWriteback.totalMarkers === 1 ? '' : 's'} ingested across ${markerWriteback.perLane.length} lane${markerWriteback.perLane.length === 1 ? '' : 's'}`
                : 'No live markers in the latest snapshot.'}
            </Text>
            {markerWriteback.perLane.map((lane) => (
              <Text key={`marker-${lane.id}`} style={styles.note}>
                {lane.id} · {lane.markerCount} marker{lane.markerCount === 1 ? '' : 's'}{lane.markerHash ? ` · hash ${lane.markerHash}` : ''}{lane.mostRecent ? ` · "${lane.mostRecent.slice(0, 80)}"` : ''}
              </Text>
            ))}
            {markerWriteback.qaSummary && (
              <Text style={styles.note}>QA digest: {markerWriteback.qaSummary}</Text>
            )}
            <Text style={styles.note}>
              Markers (MCP_RESULT / MCP_BLOCKER / MCP_COMMIT / MCP_TESTS / MCP_NEXT / AGENT_QA_RESULT_JSON) are extracted from coder/agent stdout each snapshot. Run `npm run bridge:watch` to fire snapshots on marker change within 10–30s.
            </Text>
          </View>
        )}
        {/* Rule 1 enforcement banner — every lane that is idle,
            blocked, needs_user, needs_review, or
            complete_waiting_approval (or terminal-idle while MCP
            still says working) MUST appear here with a
            recommended-next-prompt directive. This banner is the
            UI surface of `promptsRequired` from
            apps/mobile/src/services/lane-progress-summary.ts.
            Anti-rule: progress 'unknown' renders as the literal
            string, never coerced to 0%. */}
        {isAdmin && laneProgress.promptsRequired.length > 0 && (
          <View style={styles.warningBlock}>
            <Text style={styles.chipLabel}>Rule 1 — no idle lanes</Text>
            <Text style={styles.chipBody}>
              {laneProgress.promptsRequired.length} lane{laneProgress.promptsRequired.length === 1 ? '' : 's'} need{laneProgress.promptsRequired.length === 1 ? 's' : ''} a recommended next prompt before the next status reply.
            </Text>
            {laneProgress.promptsRequired.map((p) => (
              <Text key={`rule1-${p.laneId}`} style={styles.note}>
                {p.laneId} ({p.idleStatus}) → target {p.recommendedNextPromptTarget} · progress {p.promptProgressPercent === 'unknown' ? 'unknown' : `${p.promptProgressPercent}%`} · {p.recommendedNextPromptSummary ?? p.recommendedNextPromptText ?? 'queue a prompt'}
              </Text>
            ))}
            <Text style={styles.note}>
              Stale cached `working` MUST NEVER suppress this banner. See docs/OPERATING_RULES.md § rule 24 ("Rule 1") for the full contract.
            </Text>
          </View>
        )}
        {/* Lane progress strip — Claude / Codex / Agent (and any
            other lane the MCP server reports). Each row shows the
            lane status, age, fresh/stale/unknown badge, a progress
            bar (or "unknown" when no progress was reported), and
            the recommended next prompt when the server provided
            one. Renders even when MCP is unavailable so the human
            can see "MCP unavailable" rather than an empty strip. */}
        {isAdmin && (
          <View style={styles.chipBlock}>
            <Text style={styles.chipLabel}>Lane progress</Text>
            <Text style={styles.chipBody}>
              {laneProgress.source === 'unavailable'
                ? 'MCP unavailable — lane progress cannot be loaded.'
                : `${laneProgress.lanes.length} lane${laneProgress.lanes.length === 1 ? '' : 's'} reporting · snapshot ${laneProgress.snapshotFreshness}${laneProgress.snapshotStaleReason ? ` (${laneProgress.snapshotStaleReason})` : ''}`}
            </Text>
            {laneProgress.lanes.map((lane) => {
              const tone: Tone = lane.freshness === 'fresh'
                ? 'fresh'
                : lane.freshness === 'stale'
                  ? 'warning'
                  : 'neutral';
              const fillColor = lane.freshness === 'fresh' ? '#4ade80' : lane.freshness === 'stale' ? '#ff8a8a' : 'rgba(255,255,255,0.35)';
              const widthPct = lane.progressPct ?? 0;
              return (
                <View key={`lane-progress-${lane.id}`} style={{ marginTop: 8 }}>
                  <View style={styles.laneProgressRow}>
                    <Text style={styles.laneProgressName}>{lane.id}</Text>
                    <StatusPill label={lane.freshness} tone={tone} dot={lane.freshness === 'fresh'} />
                  </View>
                  <Text style={styles.laneProgressMeta}>
                    {lane.status} · age {lane.ageLabel} · progress {lane.progressPct == null ? 'unknown' : `${lane.progressPct}%`}
                  </Text>
                  {lane.taskSummary && (
                    <Text style={styles.note}>{lane.taskSummary}</Text>
                  )}
                  <View style={styles.laneProgressBarTrack}>
                    {lane.progressPct != null && (
                      <View
                        style={[
                          styles.laneProgressBarFill,
                          { width: `${Math.max(2, widthPct)}%`, backgroundColor: fillColor },
                        ]}
                      />
                    )}
                  </View>
                  <Text style={styles.note}>
                    Next: {lane.recommendedNextPrompt ?? '—'}
                  </Text>
                </View>
              );
            })}
          </View>
        )}
        {/* Overnight Prompt Queue — admin-only summary surface
            (counts + the recommended-task pointer + stale flag).
            Full row content lives behind the admin tool
            `project.list_overnight_queue` and is not rendered
            here yet; this block is the always-visible status
            tile so an idle lane has somewhere to look for the
            next overnight candidate. Per spec: SECONDARY surface
            — does NOT reorder the Top-7 priority list. Auto-
            refreshes via the AppState resume listener added in
            commit 9f3143a. */}
        {isAdmin && (
          <View style={styles.chipBlock}>
            <Text style={styles.chipLabel}>Overnight queue</Text>
            <Text style={styles.chipBody}>
              {overnightQueueSummary == null
                ? 'MCP has not yet started emitting an overnight queue field — repo-only summariser shipped, awaiting worker wiring.'
                : overnightQueueCount === 0
                  ? 'Queue empty. Tag a backlog item with safe_overnight=true and lane_owner to fill it.'
                  : `${overnightQueueCount} task${overnightQueueCount === 1 ? '' : 's'} queued${overnightQueueRecommendedId ? ` · recommended ${overnightQueueRecommendedId.slice(0, 8)}` : ''}${overnightQueueSafeToRun ? ' · safe to run unattended' : ' · requires Aaron interaction'}`}
            </Text>
            {overnightQueueHasStale && (
              <Text style={styles.note}>One or more queue rows have not been updated in over the stale threshold — refresh or void per Rule 18 (action ledger).</Text>
            )}
            <Text style={styles.note}>
              Recommendation only — Aaron approves before any overnight execution. P0/P1 blockers always win over the queue. No EAS / TestFlight / Play upload overnight without explicit approval per rule 7.
            </Text>
          </View>
        )}
        {laneHeartbeat.ok && !laneHeartbeat.driftWarning && isAdmin && (
          <View style={styles.chipBlock}>
            <Text style={styles.chipLabel}>Lane heartbeat</Text>
            <Text style={styles.chipBody}>
              {laneHeartbeat.laneCount} lane{laneHeartbeat.laneCount === 1 ? '' : 's'} · oldest {ageLabelMs(laneHeartbeat.oldestLastSeenAgeMs)} · newest {ageLabelMs(laneHeartbeat.newestLastSeenAgeMs)}
            </Text>
            {laneHeartbeat.perLaneLines.map((line, idx) => (
              <Text key={`heartbeat-${idx}`} style={styles.note}>{line}</Text>
            ))}
            <Text style={styles.note}>source: tmux_bridge · drift threshold {Math.round(LANE_DRIFT_WARN_MS / 1000)}s</Text>
          </View>
        )}
        {!mcpFreshness.stale && isAdmin && (
          <View style={styles.chipBlock}>
            <Text style={styles.chipLabel}>Live writeback</Text>
            <Text style={styles.chipBody}>MCP freshness is live ({mcpFreshness.ageLabel}). Rule 12 is active: coders run laptop commands; Aaron approves from phone.</Text>
            <Text style={styles.note}>Updated {mcpFreshness.updatedAt}</Text>
          </View>
        )}
        {isAdmin && (
          <View style={developerModeRecommendation.recommendation === 'keep_on' ? styles.warningBlock : styles.chipBlock}>
            <Text style={styles.chipLabel}>Developer Mode</Text>
            <Text style={styles.chipBody}>{developerModeRecommendation.shortLabel}</Text>
            <Text style={styles.note}>{developerModeRecommendation.reason}</Text>
            <Text style={styles.note}>
              Off-device prerequisites: Surface B shipped, push wiring shipped, no active MCP-creation-fix prompts. See docs/MCP_LONGTERM_ACCESS_ARCHITECTURE.md § 2 for the full criteria.
            </Text>
          </View>
        )}
        <View style={styles.chipBlock}>
          <Text style={styles.chipLabel}>Priority</Text>
          <Text style={styles.chipBody}>{nowPriority}</Text>
        </View>
        <View style={styles.chipBlock}>
          <Text style={styles.chipLabel}>Blocker</Text>
          <Text style={styles.chipBody}>{nowBlocker}</Text>
        </View>
        <View style={styles.chipBlock}>
          <Text style={styles.chipLabel}>Next action</Text>
          <Text style={styles.chipBody}>{nowNextAction}</Text>
          {fs008Visible && (
            <Text style={styles.note}>Manual decision visible: FS-008 WHOOP migration approve/defer.</Text>
          )}
        </View>
        {isAdmin && (
          <View style={styles.chipBlock}>
            <Text style={styles.chipLabel}>Lanes</Text>
            <Text style={styles.chipBody}>{nowLaneSummary}</Text>
            <Text style={styles.note}>
              Claude: {mcpClaudeLane ? `${mcpClaudeLane.status} · ${mcpClaudeLane.lastCommit ?? '—'}` : '—'} · Codex: {mcpCodexLane ? `${mcpCodexLane.status} · ${mcpCodexLane.lastCommit ?? '—'}` : '—'}
            </Text>
          </View>
        )}
        {isAdmin && (
          <View style={styles.chipBlock}>
            <Text style={styles.chipLabel}>Build / repo</Text>
            <Text style={styles.chipBody}>{nowBuildSummary}</Text>
            <Text style={styles.note}>{nowRepoSummary}</Text>
          </View>
        )}
        {mcpStatus && <Text style={styles.note}>{mcpStatus} · source {nowSourceLabel}</Text>}
        {isAdmin && (
          <View style={{ gap: 6 }}>
            <Text style={styles.rowLabel}>Fallback / diagnostic commands</Text>
            <Text style={styles.note}>
              Rule 12 is live. These are copy-only diagnostics for stale writeback or verification; the app does not execute commands.
            </Text>
            <SelectableCopyButton label="Copy bridge snapshot command" body={SAFE_PHONE_COMMANDS.bridgeSnapshot} />
            <SelectableCopyButton label="Copy bridge verify command" body={SAFE_PHONE_COMMANDS.bridgeVerify} />
            <SelectableCopyButton
              label="Copy Worker deploy command"
              body={deployCommandAllowedByDocs ? SAFE_PHONE_COMMANDS.workerDeploy : null}
              disabledReason="Worker deploy copy appears only when MCP/docs next action says wrangler deploy is needed."
            />
          </View>
        )}
      </Section>

      {isAdmin && <ConnectorStatusSection snapshot={connectorSnapshot} refreshing={refreshing} onRefresh={refresh} />}
      {isAdmin && (
        <McpV2LiveSection
          snapshot={mcpV2Snapshot}
          fetchError={mcpV2Error}
          refreshing={refreshing}
          onRefresh={refresh}
        />
      )}
      <AgentStatusSection />

      <Section title="Approval gates">
        <Text style={styles.note}>
          Automation pauses on these gates. Approve to unblock; defer to ping again later; safeDefault applies if a gate expires unanswered. No server writeback yet — approving updates the local cache and emits a ledger note Aaron / Codex can paste into data/action-ledger/pending_actions.json.
        </Text>
        <Pressable
          style={[styles.btn, approvalRefreshing && { opacity: 0.5 }]}
          disabled={approvalRefreshing}
          onPress={() => { void refreshApprovalGates(); }}>
          <Text style={styles.btnText}>{approvalRefreshing ? 'Refreshing…' : 'Apply expiries / refresh gates'}</Text>
        </Pressable>
        {approvalGates.length === 0 ? (
          <Text style={styles.note}>No approval gates loaded.</Text>
        ) : (
          approvalGates.map((gate) => (
            <ApprovalGateRow
              key={gate.id}
              gate={gate}
              lockReason={useApprovalGatesStore.getState().lockReason(gate.id)}
              onApprove={() => { void approveApprovalGate(gate.id); }}
              onDefer={(deferUntil) => { void deferApprovalGate(gate.id, deferUntil); }}
              onCancel={() => { void cancelApprovalGate(gate.id); }}
            />
          ))
        )}
        {approvalLedgerNotePreview() && (
          <View style={styles.chipBlock}>
            <Text style={styles.chipLabel}>Last ledger note (paste into data/action-ledger/pending_actions.json)</Text>
            <SelectableCopyButton
              label="Copy last ledger note"
              body={approvalLedgerNotePreview()}
              disabledReason="No ledger note yet — approve a gate to emit one."
            />
          </View>
        )}
        {approvalRecentNotes.length > 1 && (
          <View style={styles.chipBlock}>
            <Text style={styles.chipLabel}>Recent ledger notes ({approvalRecentNotes.length})</Text>
            {approvalRecentNotes.slice().reverse().slice(0, 5).map((note) => (
              <Text key={`${note.gateId}-${note.at}`} style={styles.note} numberOfLines={3}>
                {new Date(note.at).toLocaleTimeString()} · {note.gateId} · {note.note}
              </Text>
            ))}
          </View>
        )}
      </Section>

      <Section title="Deep Research offload">
        <Text style={styles.note}>
          Pending external research jobs. The app NEVER auto-calls Deep Research. Copy the prompt, run it in ChatGPT / OpenAI Deep Research, paste the result back, then tap Mark complete. Jobs deduplicate by reuseHash so the same scope is not researched twice.
        </Text>
        <Pressable style={styles.btn} onPress={() => { void refreshResearchArtifacts(); }}>
          <Text style={styles.btnText}>Refresh artifact statuses</Text>
        </Pressable>
        {researchJobs.length === 0 ? (
          <Text style={styles.note}>No research jobs loaded.</Text>
        ) : (
          researchJobs.map((job) => (
            <ResearchJobRow
              key={job.id}
              job={job}
              promptExport={exportResearchPrompt(job.id)}
              pasteValue={researchPasteState[job.id] ?? ''}
              onPasteChange={(value) => setResearchPasteState((prev) => ({ ...prev, [job.id]: value }))}
              onMarkSubmitted={() => { void markResearchSubmitted(job.id); }}
              onMarkCompleted={() => {
                const result = (researchPasteState[job.id] ?? '').trim();
                if (!result) {
                  Alert.alert('Deep Research', 'Paste the Deep Research result before marking complete.');
                  return;
                }
                void markResearchCompleted(job.id, result).then((res) => {
                  if (res.ok) {
                    setResearchPasteState((prev) => ({ ...prev, [job.id]: '' }));
                  } else {
                    Alert.alert('Deep Research', `Could not store result: ${res.reason}`);
                  }
                });
              }}
              onCancel={() => { void cancelResearchJob(job.id); }}
            />
          ))
        )}
      </Section>

      <Section title="AI spend gates">
        <Text style={styles.note}>
          Pause AI calls until Aaron approves spend. Each gate carries a deterministic precheck summary so the non-AI answer is visible BEFORE you spend tokens. Export prompt lets you paste the question into ChatGPT out-of-band instead of approving an in-app paid call.
        </Text>
        <Pressable
          style={[styles.btn, spendRefreshing && { opacity: 0.5 }]}
          disabled={spendRefreshing}
          onPress={() => { void refreshSpendGates(); }}>
          <Text style={styles.btnText}>{spendRefreshing ? 'Refreshing…' : 'Apply expiries / refresh'}</Text>
        </Pressable>
        {spendGates.length === 0 ? (
          <Text style={styles.note}>No AI spend gates loaded.</Text>
        ) : (
          spendGates.map((gate) => (
            <SpendGateRow
              key={gate.id}
              gate={gate}
              exportPrompt={exportSpendPrompt(gate.id)}
              onApprove={() => { void approveSpendGate(gate.id); }}
              onDefer={(deferUntil) => { void deferSpendGate(gate.id, deferUntil); }}
              onCancel={() => { void cancelSpendGate(gate.id); }}
            />
          ))
        )}
      </Section>

      <Section title="AI Coach status">
        <Row label="Backend reachable" value={health == null ? '—' : health.ok ? 'yes ✓' : 'no'} />
        <Row label="Trend windows" value="7d / 14d / 30d / 90d / 180d / 365d / all-time" />
        <Row
          label="All-history analysis"
          value={
            health?.ok && health.totalNormalizedDays != null && health.totalNormalizedDays > 0
              ? `enabled (${health.totalNormalizedDays} normalised days)`
              : health?.ok ? 'no data yet — connect Apple Health / Health Connect / WHOOP'
              : '—'
          }
        />
        {health?.ok && (health?.totalNormalizedDays ?? 0) > 0 && (health?.totalNormalizedDays ?? 0) < 95 && (
          <Text style={styles.note}>
            Coverage {health?.totalNormalizedDays}d &lt; 95 — long-term answers say so explicitly.
          </Text>
        )}
        {!health?.ok && (
          <Text style={styles.note}>
            Backend not reachable — Coach answers fall back to deterministic local templates. Trend windows still work over locally-cached normalized days.
          </Text>
        )}
      </Section>

      <Section title="Primary actions">
        <WorkflowTriggerButton
          id="android-aab-build"
          label="Build Android + upload to Internal Testing"
          subtitle="Routine: builds AAB, uploads as COMPLETED Internal Testing release, testers auto-update within 15–60 min."
          enabled={androidBuildAvailable}
          disabledReason={androidBuildAvailable ? undefined : 'Workflow android-aab-build.yml not available — push repo + add GITHUB_DISPATCH_TOKEN.'}
          inputs={{ submit_to_play: 'true' }}
          confirmCopy="Builds the Android AAB and uploads as a COMPLETED Internal Testing release (verified working on run 25361589282). Tester devices auto-update within 15–60 min — no Play Console click. Costs an EAS build credit. Continue?"
        />
        <WorkflowTriggerButton
          id="ios-testflight-build"
          label="Build iOS + submit to TestFlight"
          subtitle="Builds IPA, submits to ASC, assigns Team (Expo)."
          enabled={iosBuildAvailable}
          disabledReason={iosBuildAvailable ? undefined : 'Workflow ios-testflight-build.yml not available — push repo + add GITHUB_DISPATCH_TOKEN.'}
          inputs={{ submit_to_testflight: 'true' }}
          confirmCopy="Builds the iOS IPA, uploads to App Store Connect, and assigns the build to internal group Team (Expo). Apple processing 5–30 min then TestFlight notifies testers. Costs an EAS build credit. Continue?"
        />
        <WorkflowTriggerButton
          id="mobile-typecheck"
          label="Run typecheck"
          subtitle="Checks if app code still compiles."
          enabled={dispatchAvailable}
          disabledReason={dispatchAvailable ? undefined : 'GitHub dispatch not configured.'}
        />
        <WorkflowTriggerButton
          id="release-audit"
          label="Run release audit"
          subtitle="Checks Android, iOS, EAS, GitHub Actions, and store blockers."
          enabled={dispatchAvailable}
          disabledReason={dispatchAvailable ? undefined : 'GitHub dispatch not configured.'}
        />
      </Section>

      <Section title="Android — Internal Testing">
        <Row label="Tester-live" value="v14 ✓ received; repo target v17" />
        <Row label="Auto-promote" value="PROVEN end-to-end — run 25361589282" />
        <Row label="Routine path" value="Build Android + upload → tester device updates within 15–60 min, no manual steps" />
        <Row label="releaseStatus" value="completed (eas.json)" />
        <Text style={styles.note}>
          Play Console "Release history" UI paginates / filters EAS-COMPLETED releases differently from manual rollouts — if earlier pages don't show v14, that's a Play Console UI quirk, not a missing release. Ground truth: tester device receives the new versionCode. Settings → About → Version code on the device confirms which build is running.
        </Text>
        <WorkflowTriggerButton
          id="android-aab-build"
          label="Build Android AAB (no upload)"
          subtitle="Builds an AAB on EAS only. For dry runs / external upload."
          enabled={androidBuildAvailable}
          disabledReason={androidBuildAvailable ? undefined : 'Workflow android-aab-build.yml not available — push repo + add GITHUB_DISPATCH_TOKEN.'}
          confirmCopy="Builds the Android AAB on EAS. Costs an EAS build credit. The AAB stays on EAS until you separately upload it. Continue?"
        />
      </Section>

      <Section title="iOS — TestFlight">
        <Row label="TestFlight channel" value="works ✓; repo target Build 18" />
        <Row label="Build / submit automation" value={iosBuildAvailable ? 'auto ✓' : 'workflow not configured'} />
        <Row label="Auto-assign to Team (Expo)" value={adminStatus?.testflightGroupAssignmentConfigured === true ? 'auto ✓' : '—'} />
        <Row label="HealthKit Mac/Vision warning" value="fixed in prior TestFlight builds — accept any prompt" />
        <Text style={styles.note}>
          TestFlight is not silent OTA — testers update through the TestFlight app once Apple finishes processing each build (5–30 min after EAS submit).
        </Text>
        <WorkflowTriggerButton
          id="ios-testflight-build"
          label="Build iOS (no submit)"
          subtitle="Builds an IPA on EAS only. For dry runs / external submit."
          enabled={iosBuildAvailable}
          disabledReason={iosBuildAvailable ? undefined : 'Workflow ios-testflight-build.yml not available — push repo + add GITHUB_DISPATCH_TOKEN.'}
          confirmCopy="Builds the iOS IPA on EAS. Costs an EAS build credit. The IPA stays on EAS until you separately submit it. Continue?"
        />
      </Section>

      <Section title="OTA">
        <Row label="Status" value="blocked (EAS SDK 54 server gate)" />
        <Text style={styles.note}>
          OTA is unavailable on the EAS Update server for SDK 54. Use the Play / TestFlight build buttons above instead — there is no OTA dispatch button intentionally.
        </Text>
      </Section>

      <Section title="Diagnostics">
        <WorkflowTriggerButton
          id="backend-smoke"
          label="Run backend smoke"
          subtitle="Pings the Railway backend health and AI context routes."
          enabled={dispatchAvailable}
          disabledReason={dispatchAvailable ? undefined : 'GitHub dispatch not configured.'}
        />
      </Section>

      <QuickCaptureSection />

      <HealthConnectAuditStatusSection />

      <AuditSummarySection />

      <PromptBridgeSection statusBlock={STATUS_HANDOFF_TEMPLATE} />

      <Section title="Open shortcuts">
        <Text style={styles.note}>
          Termius is the manual-fallback terminal. Workflow buttons above are the safe automation path; raw shell stays out of the app intentionally — see docs/TERMINAL_WORKFLOW_STRATEGY.md.
        </Text>
        {EXTERNAL_SHORTCUTS.map((s) => (
          <ExternalShortcutButton key={s.label} label={s.label} url={s.url} fallbackHint={s.fallbackHint} />
        ))}
      </Section>

      <Section title="Advanced details">
        <Text style={styles.note}>
          Build / runtime / backend / data sections below. Read-only diagnostics — useful for handoffs to ChatGPT or Claude. Long-press any value to copy.
        </Text>
      </Section>

      <Section title="App build / runtime">
        <Row label="Version" value={buildInfo.appVersion} />
        <Row label={Platform.OS === 'ios' ? 'iOS build number' : 'Android versionCode'} value={String(buildInfo.buildNumber)} />
        <Row label="Repo HEAD" value={buildInfo.repoHead} />
        <Row label="Platform" value={buildInfo.platform} />
        <Row label="Runtime version" value={String(buildInfo.runtimeVersion)} />
        <Row label="Update id" value={buildInfo.updateId ? String(buildInfo.updateId).slice(0, 18) + '…' : 'embedded'} />
        <Row label="Channel" value={buildInfo.channel ?? 'production'} />
        <Row label="OTA status" value="Blocked (EAS SDK 54 server gate)" />
      </Section>

      <Section title="Backend status">
        <Row label="Host" value={apiHost} />
        <Row label="Healthy" value={health == null ? '—' : health.ok ? 'yes' : 'no'} />
        <Row label="Last checked" value={health?.checkedAt ? new Date(health.checkedAt).toLocaleTimeString() : '—'} />
        {health?.error && <Row label="Error" value={health.error} />}
        <Pressable style={[styles.btn, refreshing && { opacity: 0.5 }]} disabled={refreshing} onPress={refresh}>
          <Text style={styles.btnText}>{refreshing ? 'Refreshing…' : 'Refresh status'}</Text>
        </Pressable>
      </Section>

      <Section title="Data / AI status">
        <Row label="Normalised days" value={health?.totalNormalizedDays != null ? String(health.totalNormalizedDays) : '—'} />
        <Row label="Date range" value={health?.firstDate && health?.lastDate ? `${health.firstDate} → ${health.lastDate}` : '—'} />
        <Row label="Sources connected" value={health?.sourcesConnected != null ? String(health.sourcesConnected) : '—'} />
        <Row label="Readiness status" value={health?.readinessStatus ?? '—'} />
        <Row label="Multi-window trends" value="7 / 14 / 30 / 90 / 180 / 365 / all-time (live)" />
        {health?.totalNormalizedDays != null && health.totalNormalizedDays < 95 && (
          <Text style={styles.note}>AI store coverage is &lt; 95 days — long-term answers will say so explicitly.</Text>
        )}
      </Section>

      <Section title="AI Coach — provenance">
        <Row label="Personal-data-backed labelling" value="on" />
        <Row label="Cross-user / general trends" value="off (consent + k-threshold pending)" />
        <Row label="Paid LLM API" value="not implemented (deferred — see docs/AI_PROVIDER_STRATEGY.md)" />
        <Text style={styles.note}>
          Top-of-screen "AI Coach status" is the live state (reachability, trend windows, all-history). This section carries the policy guarantees that don't change at runtime.
        </Text>
      </Section>

      <Section title="Release / status links">
        <LinkRow label="Expo project" url={EXPO_PROJECT_URL} />
        <LinkRow label="Expo builds" url={EXPO_BUILDS_URL} />
        <LinkRow label="Expo updates" url={EXPO_UPDATES_URL} />
        <LinkRow label="Railway dashboard" url={RAILWAY_URL} />
        <LinkRow label="GitHub repo" url={GITHUB_REPO_URL} />
        <LinkRow label="GitHub Actions" url={GITHUB_ACTIONS_URL} />
        <LinkRow label="Play Console" url={PLAY_CONSOLE_URL} />
        <LinkRow label="App Store Connect" url={APPSTORE_CONNECT_URL} />
        <Text style={styles.note}>
          Reminders: Play Console → Lauburu Grappling Map → Testing → Internal testing → Create new release; TestFlight for iOS Build 12 stays separate.
        </Text>
      </Section>

      <Section title="Prompt library">
        <Text style={styles.note}>Tap to expand. Long-press text to copy.</Text>
        {PROMPT_LIBRARY.map((p, idx) => (
          <View key={p.label} style={{ gap: 6 }}>
            <Pressable
              style={styles.btn}
              onPress={() => setOpenPromptIdx(openPromptIdx === idx ? null : idx)}>
              <Text style={styles.btnText}>{openPromptIdx === idx ? '▾ ' : '▸ '}{p.label}</Text>
            </Pressable>
            {openPromptIdx === idx && (
              <RNText selectable style={styles.copyBlock}>{p.body}</RNText>
            )}
          </View>
        ))}
      </Section>

      <Section title="Status handoff template">
        <Pressable style={styles.btn} onPress={() => setHandoffOpen((v) => !v)}>
          <Text style={styles.btnText}>{handoffOpen ? '▾ Hide' : '▸ Show'} template</Text>
        </Pressable>
        {handoffOpen && (
          <RNText selectable style={styles.copyBlock}>{STATUS_HANDOFF_TEMPLATE}</RNText>
        )}
      </Section>

      <Section title="Access">
        <Row label="Source" value={isAdmin ? 'admin email' : localDevAccess ? 'local dev unlock' : '—'} />
        {!isAdmin && localDevAccess && (
          <Pressable
            style={[styles.btn, { backgroundColor: 'rgba(255,80,80,0.12)', borderColor: 'rgba(255,80,80,0.4)' }]}
            onPress={async () => {
              await lockDevTools();
              router.back();
            }}>
            <Text style={[styles.btnText, { color: '#ff8a8a' }]}>Lock developer tools on this device</Text>
          </Pressable>
        )}
      </Section>

      <Section title="Workflow dispatch — diagnostics">
        <Row label="Dispatch endpoint" value={dispatchAvailable ? 'reachable' : 'not configured'} />
        <Row label="Allowlist" value={adminStatus?.workflowAllowlist?.length ? `${adminStatus.workflowAllowlist.length} workflows` : '—'} />
        <WorkflowTriggerButton
          id="ota-diagnostic"
          label="Run OTA diagnostic"
          subtitle="Reads-only — verifies the EAS Update server SDK 54 block."
          enabled={dispatchAvailable}
          disabledReason={dispatchAvailable ? undefined : 'GitHub dispatch not configured.'}
        />
        {adminStatus?.blockers && adminStatus.blockers.length > 0 && (
          <Text style={styles.note}>
            {adminStatus.blockers.join(' ')}
          </Text>
        )}
        <Text style={styles.note}>
          {dispatchAvailable
            ? 'Each workflow button posts to the protected dispatch endpoint, which triggers a single GitHub Actions workflow_dispatch on main. No secrets pass through this app.'
            : 'Workflow buttons stay disabled until: (1) push repo to GitHub, (2) mint a fine-grained PAT with Actions:read/write + Contents/Metadata:read, (3) add it to Railway as GITHUB_DISPATCH_TOKEN with GITHUB_REPO=owner/repo. One-time setup.'}
        </Text>
      </Section>
    </ScrollView>
  );
}

function PromptBridgeSection({ statusBlock }: { statusBlock: string }) {
  const ctx = useOwnerWorkflowStore((s) => s.context);
  const setSelectedTaskBundle = useOwnerWorkflowStore((s) => s.setSelectedTaskBundle);
  const [openKind, setOpenKind] = useState<BridgePromptKind | null>(null);
  const [taskBundleDraft, setTaskBundleDraft] = useState(ctx.selectedTaskBundle ?? '');

  // Apply the user's typed task bundle to the store on blur — so the
  // template builders pick it up. Local-only.
  const onTaskBundleBlur = useCallback(() => {
    setSelectedTaskBundle(taskBundleDraft);
  }, [taskBundleDraft, setSelectedTaskBundle]);

  const bodyFor = useCallback(
    (kind: BridgePromptKind): string => {
      switch (kind) {
        case 'claude_code': return buildClaudeCodePrompt(ctx);
        case 'claude_chrome': return buildClaudeChromePrompt(ctx);
        case 'chatgpt_status': return buildChatGPTStatusPrompt(ctx);
        case 'codex': return buildCodexPrompt(ctx);
        case 'current_status': return statusBlock;
        case 'terminal_check': return buildTerminalCheckPrompt(ctx);
      }
    },
    [ctx, statusBlock],
  );

  return (
    <Section title="Prompt bridge">
      <Text style={styles.note}>
        Templates are deterministic — no paid AI API. Long-press text after expanding to copy, then open Termius / Claude Code / ChatGPT and paste. Templates pull priority / blocker / last status / protected rules / manual steps from the workflow context; edit task bundle below to scope the prompt.
      </Text>
      <Text style={styles.captureLabel}>Selected task bundle (optional)</Text>
      <TextInput
        value={taskBundleDraft}
        onChangeText={setTaskBundleDraft}
        onBlur={onTaskBundleBlur}
        placeholder='e.g. "Grappler Readiness Batch B"'
        placeholderTextColor="#666"
        style={styles.captureInput}
      />
      {BRIDGE_PROMPT_KINDS.map((kind) => (
        <View key={kind} style={{ gap: 6 }}>
          <Pressable
            style={styles.btn}
            onPress={() => setOpenKind(openKind === kind ? null : kind)}>
            <Text style={styles.btnText}>{openKind === kind ? '▾ ' : '▸ '}{BRIDGE_PROMPT_LABELS[kind]}</Text>
          </Pressable>
          {openKind === kind && (
            <>
              <Text style={styles.btnSubtitle}>Long-press the block below to copy. Then open Termius / Claude Code and paste.</Text>
              <RNText selectable style={styles.copyBlock}>{bodyFor(kind)}</RNText>
            </>
          )}
        </View>
      ))}
    </Section>
  );
}

/**
 * External shortcut button. Tries the deep-link URL first; if the
 * URL scheme isn't installed (most common case for `termius://`),
 * shows a fallback Alert with the App Store hint and offers to copy
 * a tmux attach snippet via the existing long-press-to-copy block.
 */
function ExternalShortcutButton({
  label,
  url,
  fallbackHint,
}: {
  label: string;
  url: string;
  fallbackHint?: string;
}) {
  const [tmuxOpen, setTmuxOpen] = useState(false);
  const isTermius = url.startsWith('termius:');
  const onPress = useCallback(async () => {
    try {
      const supported = await Linking.canOpenURL(url);
      if (!supported) throw new Error('not_supported');
      await Linking.openURL(url);
    } catch {
      Alert.alert(
        label,
        fallbackHint ?? `Could not open ${url}. The app may not be installed on this device.`,
      );
    }
  }, [url, label, fallbackHint]);
  return (
    <View style={{ gap: 4 }}>
      <Pressable style={styles.btn} onPress={onPress}>
        <Text style={styles.btnText}>{label}</Text>
      </Pressable>
      {isTermius && (
        <>
          <Pressable
            style={[styles.btn, { backgroundColor: 'rgba(255,255,255,0.04)', borderColor: 'rgba(255,255,255,0.12)' }]}
            onPress={() => setTmuxOpen((v) => !v)}>
            <Text style={[styles.btnText, { color: '#cfd3da' }]}>{tmuxOpen ? '▾ Hide tmux attach instructions' : '▸ Copy tmux attach instructions'}</Text>
          </Pressable>
          {tmuxOpen && (
            <RNText selectable style={styles.copyBlock}>{buildTmuxAttachInstructions()}</RNText>
          )}
        </>
      )}
    </View>
  );
}

const QUICK_CAPTURE_TYPES: { id: OwnerBacklogType; label: string }[] = [
  { id: 'bug', label: 'Bug' },
  { id: 'ux', label: 'UX' },
  { id: 'feature', label: 'Feature' },
  { id: 'release_blocker', label: 'Release' },
  { id: 'health_data', label: 'Health' },
  { id: 'ai_coaching', label: 'AI' },
  { id: 'monetisation', label: 'Money' },
];

const QUICK_CAPTURE_PLATFORMS: { id: OwnerBacklogPlatform; label: string }[] = [
  { id: 'both', label: 'Both' },
  { id: 'ios', label: 'iOS' },
  { id: 'android', label: 'Android' },
];

const STANDING_TOP_FIVE: string[] = [
  '1. MCP connector consistency',
  '2. Admin/Dev iPhone control centre',
  '3. App live MCP consumer',
  '4. Feedback suggestions approval workflow',
  '5. Health / Data Source reliability',
];

function AgentStatusSection() {
  // Hard gate: this surface is owner-email-allowlisted. The local
  // 7-tap dev unlock alone is NOT enough — devUnlocked grants
  // access to the rest of Admin/Dev (read-only diagnostics) but
  // must NOT pull `Coder status` content because the underlying
  // statuses can carry summaries Aaron writes (commit refs, run
  // ids, work-in-progress notes) that are not for testers even if
  // they've stumbled onto Admin/Dev via the unlock taps.
  // Re-compute isAdmin here rather than trusting a prop so the
  // surface is self-protective: if a future caller mounts this
  // component outside Admin/Dev, the email gate still applies.
  const userEmail = useAuthStore((s) => s.user?.email ?? null);
  const isAdmin = userEmail != null && ADMIN_EMAILS.has(userEmail.toLowerCase());

  const [agents, setAgents] = useState<Record<string, AgentStatusEntry | null> | null>(null);
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [open, setOpen] = useState(false);

  const refresh = useCallback(async () => {
    if (!isAdmin) return;  // never fetch for non-admin
    setLoading(true);
    const data = await fetchAgentStatus();
    if (data) {
      setAgents(data.agents);
      setGeneratedAt(data.generatedAt);
    }
    setLoading(false);
  }, [isAdmin]);

  useEffect(() => {
    if (!isAdmin) return;  // never poll for non-admin
    void refresh();
    const t = setInterval(() => { void refresh(); }, 30_000);
    return () => clearInterval(t);
  }, [refresh, isAdmin]);

  if (!isAdmin) {
    // Per the hardening pass: non-admin users get NO placeholder
    // section at all. Even the "owner-account only" note signalled
    // that this surface exists, which is more than testers /
    // dev-unlock viewers need to know. Return null so the layout
    // collapses cleanly.
    return null;
  }

  const order = ['claude', 'codex', 'claude-code-guide', 'other'] as const;
  const populated = agents
    ? order.filter((k) => agents[k] != null) as Array<typeof order[number]>
    : [];

  return (
    <Section title="Legacy coder diagnostics">
      <Text style={styles.note}>
        Owner-only fallback source. Use Connector control centre first; open this only when debugging the older agent-status path.
      </Text>
      <Pressable
        style={[styles.btn, { backgroundColor: 'rgba(255,255,255,0.04)', borderColor: 'rgba(255,255,255,0.12)' }]}
        onPress={() => setOpen((v) => !v)}>
        <Text style={[styles.btnText, { color: '#cfd3da' }]}>{open ? '▾ Hide diagnostics' : '▸ Show diagnostics'}</Text>
      </Pressable>
      {!open && generatedAt && <Text style={styles.note}>Last fetched {new Date(generatedAt).toLocaleTimeString()}.</Text>}
      {!open && agents != null && <Text style={styles.note}>{populated.length} legacy lanes available.</Text>}
      {open && (
        <>
      <Pressable style={[styles.btn, loading && { opacity: 0.5 }]} disabled={loading} onPress={refresh}>
        <Text style={styles.btnText}>{loading ? 'Refreshing…' : 'Refresh now'}</Text>
      </Pressable>
      {generatedAt && <Row label="Last fetched" value={new Date(generatedAt).toLocaleTimeString()} />}
      {agents == null && !loading && (
        <Text style={styles.note}>Backend not reachable — connector route may not be deployed yet.</Text>
      )}
      {agents != null && populated.length === 0 && (
        <Text style={styles.note}>No agent has reported a status yet. Run scripts/mark-agent-done.sh to seed one.</Text>
      )}
      {populated.map((agent) => {
        const e = agents![agent]!;
        const tone =
          e.status === 'done' ? '#4ade80'
          : e.status === 'in_progress' ? '#d4e157'
          : e.status === 'needs_review' ? '#ffa500'
          : e.status === 'blocked' ? '#ff8a8a'
          : '#888';
        return (
          <View key={agent} style={[styles.row, { flexDirection: 'column', alignItems: 'flex-start', gap: 4 }]}>
            <Text style={[styles.rowLabel, { color: tone }]}>
              {agent} · {e.status}
            </Text>
            {e.task.length > 0 && <Text style={styles.rowValue}>Task: {e.task}</Text>}
            {e.summary.length > 0 && <Text style={[styles.rowValue, { textAlign: 'left' }]} numberOfLines={4}>{e.summary}</Text>}
            {e.verification.length > 0 && <Text style={styles.rowValue}>Verified: {e.verification}</Text>}
            {e.nextAction.length > 0 && <Text style={[styles.rowValue, { color: '#d4e157' }]}>Next: {e.nextAction}</Text>}
            {e.updatedAt && (
              <Text style={[styles.rowValue, { opacity: 0.6, fontSize: 10 }]}>
                Updated {new Date(e.updatedAt).toLocaleString()}
              </Text>
            )}
          </View>
        );
      })}
        </>
      )}
    </Section>
  );
}

function ConnectorStatusSection({
  snapshot,
  refreshing,
  onRefresh,
}: {
  snapshot: ConnectorSnapshot | null;
  refreshing: boolean;
  onRefresh: () => void;
}) {
  const work = snapshot?.workStatus ?? null;
  const build = snapshot?.buildStatus ?? null;
  const handoff = snapshot?.handoff ?? null;
  const lanes = snapshot?.coderLanes?.lanes ?? [];
  const terminalEntries = snapshot?.terminalSummary?.entries ?? [];
  const latestTerminal = terminalEntries[0] ?? null;
  const claudeLane = lanes.find((lane) => lane.laneId.toLowerCase().includes('claude')) ?? null;
  const codexLane = lanes.find((lane) => lane.laneId.toLowerCase().includes('codex')) ?? null;
  const [detailsOpen, setDetailsOpen] = useState(false);
  const stateLabel = connectorSnapshotLabel(snapshot);
  const dataSourceLabel = connectorDataSourceLabel(snapshot);
  const bridgeFreshness = connectorPayloadFreshnessLabel(snapshot);
  const mcpState = snapshot
    ? `${stateLabel} · ${bridgeFreshness} · fetched ${connectorCheckedTime(snapshot.checkedAt)}`
    : refreshing
      ? 'MCP refreshing…'
      : `${stateLabel} · MCP not connected`;
  const summaryLine = snapshot
    ? `${lanes.length} lanes · ${terminalEntries.length} terminal summaries · ${handoff?.manualSteps.length ?? 0} manual steps`
    : 'Set EXPO_PUBLIC_MCP_BASE_URL + admin token, then refresh.';
  const handoffSummary = snapshot ? [
    'MOBILE_CONTROL_CENTRE_HANDOFF',
    `Checked: ${snapshot.checkedAt}`,
    `Source: ${snapshot.source}`,
    `Priority: ${work?.currentPriority ?? '—'}`,
    `Blocker: ${work?.currentBlocker ?? 'none'}`,
    `Next action: ${work?.nextAction ?? '—'}`,
    `Repo: ${work ? `${work.repoStatus.branch}@${work.repoStatus.head} · ${work.repoStatus.lastCommitMessage}` : '—'}`,
    `Claude: ${claudeLane ? `${claudeLane.status} · ${claudeLane.lastSummary ?? 'no summary'}` : '—'}`,
    `Codex: ${codexLane ? `${codexLane.status} · ${codexLane.lastSummary ?? 'no summary'}` : '—'}`,
    `Android: ${build ? `v${build.android.versionCode ?? '—'} · ${build.android.githubStatus ?? '—'} · Play ${build.android.playStatus ?? '—'}` : '—'}`,
    `iOS: ${build ? `${build.ios.buildNumber ?? '—'} · ${build.ios.githubStatus ?? '—'} · TestFlight ${build.ios.testflightStatus ?? '—'}` : '—'}`,
    `Latest terminal: ${latestTerminal ? `${latestTerminal.laneId} · ${latestTerminal.summary}` : '—'}`,
    `Safe to build: ${handoff ? (handoff.safeToBuild ? 'yes' : 'no') : '—'}`,
    `Build gate: ${handoff?.safeToBuildReason ?? '—'}`,
    `Manual steps: ${handoff?.manualSteps.slice(0, 3).join(' | ') || '—'}`,
  ].join('\n') : null;
  return (
    <Section title="Connector control centre">
      <Text style={styles.note}>
        Owner-only connector snapshot. No raw terminal logs, no shell execution, no secrets. Terminal rows are compact summaries only.
      </Text>
      <View style={styles.chipBlock}>
        <Text style={styles.chipLabel}>MCP status</Text>
        <Text style={styles.chipBody}>{mcpState}</Text>
        <Text style={styles.note}>{summaryLine} · source {dataSourceLabel}</Text>
        {stateLabel === 'Stale snapshot' && (
          <Text style={styles.note}>
            Stale means the bridge payload timestamp is older than the freshness window; the Worker/backend can still be reachable.
          </Text>
        )}
      </View>
      {snapshot && (
        <View style={styles.summaryGrid}>
          <View style={styles.summaryTile}>
            <Text style={styles.chipLabel}>Lanes</Text>
            <Text style={styles.summaryValue}>{lanes.length}</Text>
            <Text style={styles.summaryMeta}>{lanes.map((lane) => lane.status).join(' · ') || 'none'}</Text>
          </View>
          <View style={styles.summaryTile}>
            <Text style={styles.chipLabel}>Repo</Text>
            <Text style={styles.summaryValue}>{work?.repoStatus.head ?? '—'}</Text>
            <Text style={styles.summaryMeta}>{work ? `${work.repoStatus.dirtyFileCount} dirty` : 'repo-only'}</Text>
          </View>
        </View>
      )}
      <Pressable style={[styles.btn, refreshing && { opacity: 0.5 }]} disabled={refreshing} onPress={onRefresh}>
        <Text style={styles.btnText}>{refreshing ? 'Refreshing…' : 'Refresh connector status'}</Text>
      </Pressable>
      {snapshot == null && (
        <Text style={styles.note}>Connector routes are not reachable or the admin token is not configured.</Text>
      )}
      {snapshot?.checkedAt && <Row label="Checked" value={new Date(snapshot.checkedAt).toLocaleTimeString()} />}
      {snapshot && (
        <Row
          label="Status source"
          value={snapshot.source === 'mcp' ? `Cloudflare MCP / ${dataSourceLabel}` : `Backend fallback / ${dataSourceLabel}`}
        />
      )}
      <View style={{ gap: 6 }}>
        <Text style={styles.rowLabel}>Phone copy prompts</Text>
        <SelectableCopyButton
          label="Copy Claude prompt"
          body={handoff?.latestClaudePrompt ?? claudeLane?.nextPrompt ?? null}
          disabledReason="No Claude prompt in handoff or lane status yet."
        />
        <SelectableCopyButton
          label="Copy Codex prompt"
          body={handoff?.latestCodexPrompt ?? codexLane?.nextPrompt ?? null}
          disabledReason="No Codex prompt in handoff or lane status yet."
        />
        <SelectableCopyButton
          label="Copy Agent audit prompt"
          body={buildAgentAuditPrompt(snapshot)}
        />
        <SelectableCopyButton
          label="Copy handoff summary"
          body={handoffSummary}
          disabledReason="Connector snapshot is not available yet."
        />
      </View>
      {lanes.length > 0 && (
        <View style={{ gap: 6 }}>
          {lanes.map((lane) => (
            <View key={lane.laneId} style={[styles.row, { flexDirection: 'column', alignItems: 'flex-start', gap: 4 }]}>
              <Text style={styles.rowLabel}>{lane.laneId} · {lane.status}</Text>
              {lane.currentPromptId && <Text style={styles.rowValue}>Prompt: {lane.currentPromptId}</Text>}
              {lane.lastSummary && <Text style={[styles.rowValue, { textAlign: 'left' }]} numberOfLines={3}>{lane.lastSummary}</Text>}
              <Text style={[styles.rowValue, { opacity: 0.6 }]}>
                Typecheck: {lane.lastTypecheckResult ?? '—'} · Dirty files: {lane.dirtyFiles.length}
              </Text>
              {lane.nextPrompt && (
                <Text style={[styles.rowValue, { color: '#d4e157', opacity: 1, textAlign: 'left' }]} numberOfLines={2}>
                  Next prompt: {lane.nextPrompt}
                </Text>
              )}
            </View>
          ))}
        </View>
      )}
      <Pressable
        style={[styles.btn, { backgroundColor: 'rgba(255,255,255,0.04)', borderColor: 'rgba(255,255,255,0.12)' }]}
        onPress={() => setDetailsOpen((v) => !v)}>
        <Text style={[styles.btnText, { color: '#cfd3da' }]}>{detailsOpen ? '▾ Hide diagnostics' : '▸ Show diagnostics'}</Text>
      </Pressable>
      {detailsOpen && (
        <>
          {work && (
            <>
              <Row label="Priority" value={work.currentPriority ?? '—'} />
              <Row label="Blocker" value={work.currentBlocker ?? 'none'} />
              <Row label="Repo" value={`${work.repoStatus.branch}@${work.repoStatus.head} · ${work.repoStatus.dirtyFileCount} dirty / ${work.repoStatus.untrackedFileCount} untracked`} />
              <Row label="Latest commit" value={work.repoStatus.lastCommitMessage || '—'} />
              <Row label="Next action" value={work.nextAction ?? '—'} />
              <Row label="Live status" value={work.liveStatus.cloudflareWorkerDeployed ? 'Cloudflare worker marked live' : 'Repo-only / not marked live'} />
              <Row label="Tester builds" value={`Android ${work.liveStatus.androidVersionCode ?? '—'} · iOS ${work.liveStatus.iosBuildNumber ?? '—'}`} />
            </>
          )}
          {build && (
            <>
              <Row label="Android build" value={`v${build.android.versionCode ?? '—'} · ${build.android.githubStatus ?? '—'} · Play ${build.android.playStatus ?? '—'}`} />
              <Row label="iOS build" value={`${build.ios.buildNumber ?? '—'} · ${build.ios.githubStatus ?? '—'} · TestFlight ${build.ios.testflightStatus ?? '—'}`} />
            </>
          )}
          {handoff && (
            <>
              <Row label="Safe to build" value={handoff.safeToBuild ? 'yes' : 'no'} />
              <Row label="Build gate reason" value={handoff.safeToBuildReason} />
              <Row label="Latest Claude prompt" value={handoff.latestClaudePrompt ?? '—'} />
              <Row label="Latest Codex prompt" value={handoff.latestCodexPrompt ?? '—'} />
              {handoff.manualSteps.slice(0, 3).map((step, idx) => (
                <Row key={`${idx}-${step}`} label={`Manual ${idx + 1}`} value={step} />
              ))}
            </>
          )}
          {latestTerminal && (
            <View style={[styles.row, { flexDirection: 'column', alignItems: 'flex-start', gap: 4 }]}>
              <Text style={styles.rowLabel}>Latest terminal · {latestTerminal.laneId}</Text>
              <Text style={[styles.rowValue, { textAlign: 'left' }]} numberOfLines={3}>{latestTerminal.summary}</Text>
              <Text style={[styles.rowValue, { textAlign: 'left', opacity: 0.65 }]} numberOfLines={2}>
                Verified: {latestTerminal.verification || '—'}
              </Text>
              <Text style={[styles.rowValue, { textAlign: 'left', color: '#d4e157', opacity: 1 }]} numberOfLines={2}>
                Next: {latestTerminal.nextAction || '—'}
              </Text>
            </View>
          )}
        </>
      )}
    </Section>
  );
}

function McpV2LiveSection({
  snapshot,
  fetchError,
  refreshing,
  onRefresh,
}: {
  snapshot: McpV2DashboardSnapshot | null;
  fetchError: string | null;
  refreshing: boolean;
  onRefresh: () => void;
}) {
  const [diagnosticsOpen, setDiagnosticsOpen] = useState(false);
  const fetchedLabel = snapshot ? mcpV2RelativeAge(snapshot.fetchedAt) : '—';
  const stale = snapshot ? mcpV2IsStale(snapshot.fetchedAt) : false;
  const baseUrl = snapshot?.baseUrl ?? null;
  const serverName = snapshot?.serverInfo?.name ?? '—';
  const protocolVersion = snapshot?.protocolVersion ?? '—';
  const toolTotal = snapshot?.toolCounts.total ?? 0;
  const namespaces = snapshot?.toolCounts.byNamespace ?? {};
  const namespaceLabel = Object.keys(namespaces).length > 0
    ? Object.entries(namespaces).map(([ns, n]) => `${ns}:${n}`).join(' · ')
    : 'no tools loaded';
  const nsCount = Object.keys(namespaces).length;
  const overallState = !snapshot
    ? 'loading'
    : !snapshot.serverInfo
      ? 'unreachable'
      : stale
        ? 'stale'
        : 'connected';
  const overallStateLabel = {
    loading: 'Loading…',
    unreachable: 'Unreachable',
    stale: 'Stale',
    connected: 'Connected',
  }[overallState];

  return (
    <Section title="MCP Live (v2)">
      <View style={styles.summaryGrid}>
        <View style={styles.summaryTile}>
          <Text style={styles.chipLabel}>State</Text>
          <Text style={styles.summaryValue}>{refreshing && !snapshot ? 'Refreshing…' : overallStateLabel}</Text>
          <Text style={styles.summaryMeta}>{`Fetched ${fetchedLabel}`}</Text>
        </View>
        <View style={styles.summaryTile}>
          <Text style={styles.chipLabel}>Server</Text>
          <Text style={styles.summaryValue} numberOfLines={1}>{serverName}</Text>
          <Text style={styles.summaryMeta}>{`Protocol ${protocolVersion}`}</Text>
        </View>
        <View style={styles.summaryTile}>
          <Text style={styles.chipLabel}>Tools</Text>
          <Text style={styles.summaryValue}>{`${toolTotal} · ${nsCount}ns`}</Text>
          <Text style={styles.summaryMeta} numberOfLines={2}>{namespaceLabel}</Text>
        </View>
        <View style={styles.summaryTile}>
          <Text style={styles.chipLabel}>Endpoint</Text>
          <Text style={styles.summaryValue}>{baseUrl ? '/mcp/v2' : 'not configured'}</Text>
          <Text style={styles.summaryMeta} numberOfLines={2}>{baseUrl ? 'public + admin tools' : 'EXPO_PUBLIC_MCP_BASE_URL unset'}</Text>
        </View>
      </View>

      {fetchError ? (
        <View style={styles.chipBlock}>
          <Text style={styles.chipLabel}>Fetch error</Text>
          <Text style={styles.chipBody}>{fetchError}</Text>
        </View>
      ) : null}

      {snapshot ? (
        <>
          <McpV2ToolRow label="project.get_current_state" auth="public" result={snapshot.projectCurrentState} formatter={formatProjectCurrentState} />
          <McpV2ToolRow label="project.get_operating_rules" auth="public" result={snapshot.projectOperatingRules} formatter={formatOperatingRules} />
          <McpV2ToolRow label="project.get_overview" auth="public" result={snapshot.projectOverview} formatter={formatProjectOverview} />
          <McpV2ToolRow label="project.get_work_status" auth="public" result={snapshot.projectWorkStatus} formatter={formatProjectWorkStatus} />
          <McpV2ToolRow label="mobile.get_lane_overview" auth="public" result={snapshot.laneOverview} formatter={formatLaneOverview} />
          <McpV2ToolRow label="mobile.get_build_overview" auth="public" result={snapshot.buildOverview} formatter={formatBuildOverview} />
          <McpV2ToolRow label="handoff.get_latest" auth="public" result={snapshot.handoffLatest} formatter={formatHandoffLatest} />
        </>
      ) : (
        <View style={styles.chipBlock}>
          <Text style={styles.chipLabel}>State</Text>
          <Text style={styles.chipBody}>{refreshing ? 'Loading MCP v2 snapshot…' : 'No snapshot. Tap refresh.'}</Text>
        </View>
      )}

      <Pressable
        accessibilityRole="button"
        onPress={() => setDiagnosticsOpen((v) => !v)}
        style={styles.btn}
      >
        <Text style={styles.btnText}>{diagnosticsOpen ? '▾ Hide diagnostics' : '▸ Show diagnostics'}</Text>
      </Pressable>
      {diagnosticsOpen && (
        <View style={styles.chipBlock}>
          <Text style={styles.chipLabel}>Diagnostics</Text>
          <Text style={styles.chipBody}>
            {`Public-safe namespaces (project / mobile.*_overview / integrations / handoff / website): No Auth.`}
          </Text>
          <Text style={styles.chipBody}>
            {`Private namespaces (mobile.get_<full>): admin token required. Token sourced from EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN; never displayed.`}
          </Text>
          <Text style={styles.chipBody}>
            {`Source labels: dataSource.source = 'supabase' | 'placeholder'; mcpConnectionStatus = connected | stale | fallback | offline.`}
          </Text>
        </View>
      )}

      <Pressable
        accessibilityRole="button"
        onPress={onRefresh}
        disabled={refreshing}
        style={[styles.btn, refreshing && { opacity: 0.5 }]}
      >
        <Text style={styles.btnText}>{refreshing ? 'Refreshing…' : 'Refresh MCP v2'}</Text>
      </Pressable>
    </Section>
  );
}

function McpV2ToolRow({
  label,
  auth,
  result,
  formatter,
}: {
  label: string;
  auth: 'public' | 'admin';
  result: { ok: true; payload: unknown } | { ok: false; message: string };
  formatter: (payload: unknown) => string;
}) {
  return (
    <View style={styles.chipBlock}>
      <Text style={styles.chipLabel}>{`${label}  ·  ${auth === 'public' ? 'No Auth' : 'admin'}`}</Text>
      {result.ok ? (
        <Text style={styles.chipBody}>{formatter(result.payload)}</Text>
      ) : (
        <Text style={styles.chipBody}>{`error: ${result.message}`}</Text>
      )}
    </View>
  );
}

function mcpV2RelativeAge(iso: string): string {
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return '—';
  const ageMs = Date.now() - t;
  if (ageMs < 0) return 'just now';
  if (ageMs < 60_000) return `${Math.floor(ageMs / 1000)}s ago`;
  if (ageMs < 3600_000) return `${Math.floor(ageMs / 60_000)}m ago`;
  return `${Math.floor(ageMs / 3600_000)}h ago`;
}

function mcpV2IsStale(iso: string): boolean {
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return true;
  return Date.now() - t > 10 * 60 * 1000;
}

function formatProjectCurrentState(payload: unknown): string {
  const p = payload as {
    source?: string;
    freshness?: { isStale?: boolean; staleReason?: string; updatedAt?: string | null };
    currentPriority?: string | null;
    nextAction?: string | null;
  };
  const freshness = p.freshness;
  const state = freshness?.isStale ? `stale (${freshness.staleReason ?? 'unknown'})` : 'fresh';
  const updated = freshness?.updatedAt ? mcpV2RelativeAge(freshness.updatedAt) : '—';
  return [
    `state: ${state} · source=${p.source ?? '—'} · updated ${updated}`,
    `priority: ${p.currentPriority ?? '—'}`,
    `next: ${p.nextAction ?? '—'}`,
  ].join('\n');
}

function formatOperatingRules(payload: unknown): string {
  const p = payload as { rules?: Array<{ id?: number; title?: string }> };
  const rules = p.rules ?? [];
  const rule12 = rules.find((rule) => rule.id === 12);
  return rule12
    ? `Rule 12 live: ${rule12.title ?? 'Coders run all laptop commands'}`
    : `Rule 12 not found · rules loaded: ${rules.length}`;
}

function formatProjectOverview(payload: unknown): string {
  const p = payload as {
    mobileTopPriority?: { source?: string; title?: string; status?: string } | null;
    openManualStepsCount?: number;
    websitePendingCount?: number | null;
  };
  const top = p.mobileTopPriority?.title ?? '—';
  const status = p.mobileTopPriority?.status ?? '—';
  const open = typeof p.openManualStepsCount === 'number' ? p.openManualStepsCount : 0;
  const pending = p.websitePendingCount;
  const pendingLabel = pending == null ? '—' : String(pending);
  return `mobile top: ${top} (${status}) · open manual: ${open} · website pending: ${pendingLabel}`;
}

function formatProjectWorkStatus(payload: unknown): string {
  const p = payload as { currentPriority?: string | null; currentBlocker?: string | null; nextAction?: string | null; blocked?: boolean };
  const lines = [`priority: ${p.currentPriority ?? '—'}`];
  if (p.currentBlocker) lines.push(`blocker: ${p.currentBlocker}`);
  if (p.nextAction) lines.push(`next: ${p.nextAction}`);
  return lines.join('\n');
}

function formatLaneOverview(payload: unknown): string {
  const p = payload as { totalLanes?: number; byStatus?: Record<string, number> };
  const total = p.totalLanes ?? 0;
  const by = p.byStatus ?? {};
  const parts = Object.entries(by).filter(([, v]) => v > 0).map(([k, v]) => `${k}=${v}`);
  return `${total} lanes${parts.length ? ` · ${parts.join(' / ')}` : ' · all idle'}`;
}

function formatBuildOverview(payload: unknown): string {
  const p = payload as {
    android?: { versionCode?: number | null; githubStatus?: string | null; playStatus?: string | null; playTrack?: string | null };
    ios?: { buildNumber?: string | null; githubStatus?: string | null; testflightStatus?: string | null };
  };
  const a = p.android ?? {};
  const i = p.ios ?? {};
  return [
    `Android v${a.versionCode ?? '?'}: gh=${a.githubStatus ?? '—'} play=${a.playStatus ?? '—'} (${a.playTrack ?? '—'})`,
    `iOS Build ${i.buildNumber ?? '?'}: gh=${i.githubStatus ?? '—'} tf=${i.testflightStatus ?? '—'}`,
  ].join('\n');
}

function formatHandoffLatest(payload: unknown): string {
  const p = payload as { entries?: Array<{ source?: string; generatedAt?: string | null; summary?: string }> };
  const entries = p.entries ?? [];
  if (entries.length === 0) return 'no handoff entries';
  return entries.slice(0, 2).map((e) => {
    const src = e.source ?? '—';
    const at = e.generatedAt ? mcpV2RelativeAge(e.generatedAt) : '—';
    const sum = (e.summary ?? '').slice(0, 80);
    return `[${src}] ${at}: ${sum}`;
  }).join('\n');
}

function SelectableCopyButton({
  label,
  body,
  disabledReason,
}: {
  label: string;
  body: string | null;
  disabledReason?: string;
}) {
  const [open, setOpen] = useState(false);
  const disabled = body == null || body.trim().length === 0;
  return (
    <View style={{ gap: 4 }}>
      <Pressable
        style={[styles.btn, disabled && { opacity: 0.4 }]}
        disabled={disabled}
        onPress={() => setOpen((v) => !v)}>
        <Text style={styles.btnText}>{open ? '▾ ' : '▸ '}{label}</Text>
      </Pressable>
      {disabled && <Text style={styles.btnDisabledReason}>{disabledReason ?? 'Prompt text unavailable.'}</Text>}
      {open && (
        <>
          <Text style={styles.btnSubtitle}>Long-press the block below to copy from the phone.</Text>
          <RNText selectable style={styles.copyBlock}>{body ?? ''}</RNText>
        </>
      )}
    </View>
  );
}

function HealthConnectAuditStatusSection() {
  const events = useAuditEventStore((s) => s.events);
  const hcEvents = events.filter((e) => e.sourceId === 'health_connect');
  const latest = hcEvents[hcEvents.length - 1] ?? null;
  const latestVisible = [...hcEvents].reverse().find((e) =>
    e.eventType === 'health_source_visible' || e.eventType === 'health_source_missing'
  ) ?? null;
  const latestPermission = [...hcEvents].reverse().find((e) =>
    e.eventType === 'permission_granted' || e.eventType === 'permission_denied' || e.eventType === 'permission_requested'
  ) ?? null;
  const latestSync = [...hcEvents].reverse().find((e) =>
    e.eventType === 'sync_succeeded' || e.eventType === 'sync_failed' || e.eventType === 'sync_started'
  ) ?? null;
  const latestMissing = [...hcEvents].reverse().find((e) => e.eventType === 'missing_metrics') ?? null;

  const fmt = (e: { eventType: string; severity: string; createdAt: string } | null) => e
    ? `${e.eventType} · ${e.severity} · ${new Date(e.createdAt).toLocaleTimeString()}`
    : '—';

  return (
    <Section title="Health Connect audit">
      <Text style={styles.note}>
        Android local audit only — source-state metadata, not raw health values.
      </Text>
      <Row label="Events" value={String(hcEvents.length)} />
      <Row label="Latest" value={fmt(latest)} />
      <Row label="Visibility" value={fmt(latestVisible)} />
      <Row label="Permission" value={fmt(latestPermission)} />
      <Row label="Sync" value={fmt(latestSync)} />
      <Row label="Missing metrics" value={fmt(latestMissing)} />
      {latestSync?.availableFields && latestSync.availableFields.length > 0 && (
        <Row label="Available fields" value={latestSync.availableFields.join(', ')} />
      )}
      {latestMissing?.missingFields && latestMissing.missingFields.length > 0 && (
        <Row label="Missing fields" value={latestMissing.missingFields.join(', ')} />
      )}
    </Section>
  );
}

function AuditSummarySection() {
  const events = useAuditEventStore((s) => s.events);
  const recent = events.slice(-8).reverse();
  const counts = events.reduce<Record<string, number>>((acc, e) => {
    acc[e.eventType] = (acc[e.eventType] ?? 0) + 1;
    return acc;
  }, {});
  const totalErrors = events.filter((e) => e.severity === 'error').length;
  const totalWarnings = events.filter((e) => e.severity === 'warning').length;
  return (
    <Section title="Audit · last events">
      <Text style={styles.note}>
        Local-only metadata about source state — never raw health values. Capped at 200 events. See docs/IN_APP_AUDIT_SYSTEM.md.
      </Text>
      <Row label="Total events" value={String(events.length)} />
      <Row label="Errors / Warnings" value={`${totalErrors} / ${totalWarnings}`} />
      {Object.keys(counts).length === 0 && (
        <Text style={styles.note}>No events captured yet. Capture sites land in follow-up batches per the audit doc.</Text>
      )}
      {recent.map((e) => (
        <View key={e.id} style={styles.row}>
          <Text style={styles.rowLabel} numberOfLines={1}>{e.eventType}{e.sourceId ? ` · ${e.sourceId}` : ''}</Text>
          <Text style={styles.rowValue} numberOfLines={2} ellipsizeMode="tail">
            {e.severity}{e.userVisibleMessage ? ` · ${e.userVisibleMessage}` : ''}
          </Text>
        </View>
      ))}
    </Section>
  );
}

function QuickCaptureSection() {
  const items = useOwnerBacklogStore((s) => s.items);
  const add = useOwnerBacklogStore((s) => s.add);
  const remove = useOwnerBacklogStore((s) => s.remove);
  const updateStatus = useOwnerBacklogStore((s) => s.updateStatus);

  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [details, setDetails] = useState('');
  const [blocker, setBlocker] = useState('');
  const [type, setType] = useState<OwnerBacklogType>('bug');
  const [platform, setPlatform] = useState<OwnerBacklogPlatform>('both');
  const [priority, setPriority] = useState<number>(7);

  const canSubmit = title.trim().length > 0;

  const onAdd = useCallback(async () => {
    if (!canSubmit) return;
    const trimmedBlocker = blocker.trim();
    await add({
      title: title.trim(),
      details: details.trim(),
      blocker: trimmedBlocker.length > 0 ? trimmedBlocker : undefined,
      type,
      platform,
      priority,
      status: trimmedBlocker.length > 0 ? 'blocked' : 'new',
    });
    setTitle('');
    setDetails('');
    setBlocker('');
    setType('bug');
    setPlatform('both');
    setPriority(7);
    setOpen(false);
  }, [canSubmit, title, details, blocker, type, platform, priority, add]);

  return (
    <Section title="Backlog · Quick capture">
      <Text style={styles.note}>
        Standing top-5 mirrors docs/APP_DEVELOPMENTS.md. Quick capture stores ad-hoc items locally only — never synced. Backend sync is a separate batch.
      </Text>
      {STANDING_TOP_FIVE.map((line) => (
        <Text key={line} style={styles.backlogStandingLine}>{line}</Text>
      ))}

      <Pressable style={styles.btn} onPress={() => setOpen((v) => !v)}>
        <Text style={styles.btnText}>{open ? '▾ Close capture' : `▸ Quick capture${items.length > 0 ? ` (${items.length} stored)` : ''}`}</Text>
      </Pressable>

      {open && (
        <View style={styles.captureBox}>
          <Text style={styles.captureLabel}>Title</Text>
          <TextInput
            value={title}
            onChangeText={setTitle}
            placeholder="One-line summary"
            placeholderTextColor="#666"
            style={styles.captureInput}
          />
          <Text style={styles.captureLabel}>Details</Text>
          <TextInput
            value={details}
            onChangeText={setDetails}
            placeholder="Optional — repro, links, why it matters"
            placeholderTextColor="#666"
            multiline
            numberOfLines={3}
            textAlignVertical="top"
            style={[styles.captureInput, styles.captureInputMulti]}
          />
          <Text style={styles.captureLabel}>Blocker (optional — sets status to blocked)</Text>
          <TextInput
            value={blocker}
            onChangeText={setBlocker}
            placeholder="e.g. needs Play listing screenshots"
            placeholderTextColor="#666"
            style={styles.captureInput}
          />
          <Text style={styles.captureLabel}>Type</Text>
          <View style={styles.captureRow}>
            {QUICK_CAPTURE_TYPES.map((t) => (
              <Pressable key={t.id} style={[styles.pill, type === t.id && styles.pillActive]} onPress={() => setType(t.id)}>
                <Text style={[styles.pillText, type === t.id && styles.pillTextActive]}>{t.label}</Text>
              </Pressable>
            ))}
          </View>
          <Text style={styles.captureLabel}>Platform</Text>
          <View style={styles.captureRow}>
            {QUICK_CAPTURE_PLATFORMS.map((p) => (
              <Pressable key={p.id} style={[styles.pill, platform === p.id && styles.pillActive]} onPress={() => setPlatform(p.id)}>
                <Text style={[styles.pillText, platform === p.id && styles.pillTextActive]}>{p.label}</Text>
              </Pressable>
            ))}
          </View>
          <Text style={styles.captureLabel}>Priority — see docs/FEEDBACK_PRIORITY_MODEL.md</Text>
          <View style={styles.captureRow}>
            {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
              <Pressable key={n} style={[styles.pillSmall, priority === n && styles.pillActive]} onPress={() => setPriority(n)}>
                <Text style={[styles.pillText, priority === n && styles.pillTextActive]}>{n}</Text>
              </Pressable>
            ))}
          </View>
          <Pressable
            style={[styles.btn, !canSubmit && { opacity: 0.4 }]}
            disabled={!canSubmit}
            onPress={onAdd}>
            <Text style={styles.btnText}>Save to backlog</Text>
          </Pressable>
        </View>
      )}

      {items.length > 0 && (
        <View style={{ gap: 6 }}>
          {items.map((it) => <BacklogItemRow key={it.id} item={it} onRemove={remove} onStatus={updateStatus} />)}
        </View>
      )}
    </Section>
  );
}

function BacklogItemRow({
  item,
  onRemove,
  onStatus,
}: {
  item: OwnerBacklogItem;
  onRemove: (id: string) => Promise<void>;
  onStatus: (id: string, status: OwnerBacklogItem['status']) => Promise<void>;
}) {
  return (
    <View style={styles.backlogItem}>
      <View style={{ flex: 1, gap: 2 }}>
        <Text style={styles.backlogTitle} numberOfLines={2}>P{item.priority} · {item.title}</Text>
        <Text style={styles.backlogMeta}>
          {item.type} · {item.platform} · {item.status} · {new Date(item.createdAt).toLocaleDateString()}
        </Text>
        {item.blocker && item.blocker.length > 0 && (
          <Text style={[styles.backlogMeta, { color: '#ff8a8a' }]} numberOfLines={2}>Blocker: {item.blocker}</Text>
        )}
        {item.details.length > 0 && <Text style={styles.backlogDetails} numberOfLines={3}>{item.details}</Text>}
      </View>
      <View style={{ gap: 4 }}>
        {item.status !== 'tester_live' && item.status !== 'done' && (
          <Pressable onPress={() => onStatus(item.id, 'tester_live')} hitSlop={6}>
            <Text style={[styles.backlogAction, { color: '#4ade80' }]}>Tester-live</Text>
          </Pressable>
        )}
        {item.status !== 'done' && (
          <Pressable onPress={() => onStatus(item.id, 'done')} hitSlop={6}>
            <Text style={[styles.backlogAction, { color: '#9ca3af' }]}>Done</Text>
          </Pressable>
        )}
        <Pressable onPress={() => onRemove(item.id)} hitSlop={6}>
          <Text style={[styles.backlogAction, { color: '#ff8a8a' }]}>Delete</Text>
        </Pressable>
      </View>
    </View>
  );
}

function WorkflowTriggerButton({
  id,
  label,
  subtitle,
  enabled,
  inputs,
  confirmCopy,
  disabledReason,
}: {
  id: string;
  label: string;
  /** One-line plain-language explanation of what this button does. */
  subtitle?: string;
  enabled: boolean;
  /** Optional `inputs` to forward to GitHub Actions workflow_dispatch. */
  inputs?: Record<string, string>;
  /** Optional override for the confirm Alert body. */
  confirmCopy?: string;
  /** Shown beneath the label when `enabled` is false — must explain
   * the exact blocker so the user knows what step to take next. */
  disabledReason?: string;
}) {
  const [busy, setBusy] = useState(false);
  const showDispatchButton = __DEV__ === true;
  const onPress = useCallback(() => {
    if (!enabled || busy) return;
    Alert.alert(
      `Trigger "${label}"?`,
      confirmCopy ?? `Dispatches the GitHub Actions workflow "${id}" on main. No app code change. Continue?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Dispatch',
          style: 'default',
          onPress: async () => {
            setBusy(true);
            try {
              const apiBase = (process.env.EXPO_PUBLIC_AI_PUBLIC_URL ?? '').replace(/\/$/, '');
              const memToken = process.env.EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN ?? '';
              const res = await fetch(
                `${apiBase}/admin/workflows/${encodeURIComponent(id)}/dispatch`,
                {
                  method: 'POST',
                  headers: {
                    'content-type': 'application/json',
                    'x-athlete-memory-token': memToken,
                  },
                  body: JSON.stringify({ ref: 'main', inputs: inputs ?? {} }),
                },
              );
              const json: any = await res.json().catch(() => ({}));
              if (!res.ok || json?.ok === false) {
                throw new Error(json?.error ?? `HTTP ${res.status}`);
              }
              Alert.alert(
                'Dispatched',
                `${label} accepted. Check GitHub Actions for the run.`,
              );
            } catch (e: any) {
              Alert.alert('Dispatch failed', e?.message ?? 'Unknown error.');
            } finally {
              setBusy(false);
            }
          },
        },
      ],
    );
  }, [id, label, enabled, busy, inputs, confirmCopy]);
  if (!showDispatchButton) {
    return (
      <View style={{ gap: 2 }}>
        <Text style={styles.note}>
          Dispatch button hidden in production builds until FS-019 (per-user JWT auth) lands.
        </Text>
      </View>
    );
  }
  const dimmed = !enabled || busy;
  return (
    <View style={{ gap: 2 }}>
      <Pressable
        style={[styles.btn, dimmed && { opacity: 0.4 }]}
        disabled={dimmed}
        onPress={onPress}>
        <Text style={styles.btnText}>{busy ? 'Dispatching…' : label}</Text>
      </Pressable>
      {subtitle && enabled && <Text style={styles.btnSubtitle}>{subtitle}</Text>}
      {!enabled && disabledReason && <Text style={styles.btnDisabledReason}>{disabledReason}</Text>}
    </View>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

function ResearchJobRow({
  job,
  promptExport,
  pasteValue,
  onPasteChange,
  onMarkSubmitted,
  onMarkCompleted,
  onCancel,
}: {
  job: ResearchJob;
  promptExport: string | null;
  pasteValue: string;
  onPasteChange: (value: string) => void;
  onMarkSubmitted: () => void;
  onMarkCompleted: () => void;
  onCancel: () => void;
}) {
  const [open, setOpen] = useState(false);
  const isActive = job.status === 'draft' || job.status === 'submitted';
  const completedLabel = (() => {
    if (!job.completedAt) return '';
    const t = new Date(job.completedAt).getTime();
    if (!Number.isFinite(t)) return '';
    const ageMs = Date.now() - t;
    if (ageMs < 3_600_000) return `${Math.max(1, Math.floor(ageMs / 60_000))}m ago`;
    if (ageMs < 86_400_000) return `${Math.floor(ageMs / 3_600_000)}h ago`;
    return `${Math.floor(ageMs / 86_400_000)}d ago`;
  })();
  return (
    <View style={styles.chipBlock}>
      <Pressable onPress={() => setOpen((v) => !v)} hitSlop={6}>
        <Text style={styles.chipLabel}>
          {job.triggerType} · {job.status}
          {job.artifactStatus ? ` · artifact ${job.artifactStatus}` : ''}
          {completedLabel ? ` · completed ${completedLabel}` : ''}
        </Text>
        <Text style={styles.chipBody}>{job.topic}</Text>
        <Text style={styles.note} numberOfLines={2}>reuseHash {job.reuseHash} · scope {job.scopeKeys.join(', ') || '—'}</Text>
      </Pressable>
      {open && (
        <View style={{ gap: 6, marginTop: 6 }}>
          <Text style={styles.note}>Prompt: {job.prompt}</Text>
          {job.result && (
            <Text style={styles.note} numberOfLines={6}>Result (cached): {job.result}</Text>
          )}
          {job.citations.length > 0 && (
            <Text style={styles.note}>Citations: {job.citations.join(' · ')}</Text>
          )}
          <Text style={styles.note}>freshnessWindowDays: {job.freshnessWindowDays}{job.staleAfter ? ` · staleAfter ${new Date(job.staleAfter).toLocaleDateString()}` : ''}</Text>
          {job.supersededBy && (
            <Text style={styles.note}>Superseded by: {job.supersededBy}</Text>
          )}
        </View>
      )}
      <SelectableCopyButton
        label="Copy prompt for Deep Research"
        body={promptExport}
        disabledReason="Job not loaded — refresh and try again."
      />
      {isActive && (
        <View style={{ gap: 6, marginTop: 8 }}>
          <TextInput
            style={[styles.captureInput, { minHeight: 100, textAlignVertical: 'top' }]}
            placeholder="Paste Deep Research result here, then Mark complete"
            placeholderTextColor="#666"
            multiline
            value={pasteValue}
            onChangeText={onPasteChange}
          />
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
            {job.status === 'draft' && (
              <Pressable style={[styles.btn, { flexGrow: 1, minWidth: 100, opacity: 0.85 }]} onPress={onMarkSubmitted}>
                <Text style={styles.btnText}>Mark submitted</Text>
              </Pressable>
            )}
            <Pressable style={[styles.btn, { flexGrow: 1, minWidth: 100 }]} onPress={onMarkCompleted}>
              <Text style={styles.btnText}>Mark complete</Text>
            </Pressable>
            <Pressable style={[styles.btn, { flexGrow: 1, minWidth: 100, opacity: 0.6 }]} onPress={onCancel}>
              <Text style={styles.btnText}>Cancel</Text>
            </Pressable>
          </View>
        </View>
      )}
    </View>
  );
}

function SpendGateRow({
  gate,
  exportPrompt,
  onApprove,
  onDefer,
  onCancel,
}: {
  gate: SpendGate;
  exportPrompt: string | null;
  onApprove: () => void;
  onDefer: (deferUntil: string) => void;
  onCancel: () => void;
}) {
  const [open, setOpen] = useState(false);
  const isActive = isSpendGateActionable(gate);
  const expiresLabel = (() => {
    const t = new Date(gate.expiresAt).getTime();
    if (!Number.isFinite(t)) return '—';
    const remaining = t - Date.now();
    if (remaining <= 0) return 'expired';
    if (remaining < 3_600_000) return `${Math.max(1, Math.floor(remaining / 60_000))}m left`;
    if (remaining < 86_400_000) return `${Math.floor(remaining / 3_600_000)}h left`;
    return `${Math.floor(remaining / 86_400_000)}d left`;
  })();
  const deferOneDay = () => {
    const until = new Date(Date.now() + 86_400_000).toISOString();
    onDefer(until);
  };
  return (
    <View style={styles.chipBlock}>
      <Pressable onPress={() => setOpen((v) => !v)} hitSlop={6}>
        <Text style={styles.chipLabel}>
          {gate.priority} · {gate.triggerType} · cost: {gate.estimatedCostClass} · {gate.status} · {expiresLabel}
        </Text>
        <Text style={styles.chipBody}>{gate.title}</Text>
        <Text style={styles.note} numberOfLines={3}>Precheck: {gate.precheckSummary}</Text>
      </Pressable>
      {open && (
        <View style={{ gap: 6, marginTop: 6 }}>
          <Text style={styles.note}>Reason for AI: {gate.description}</Text>
          {gate.actionPayload && (
            <Text style={styles.note}>Proposed AI action: {gate.actionPayload}</Text>
          )}
          <Text style={styles.note}>safeDefault if expired: {gate.safeDefault}</Text>
          {gate.precheckRuleId && (
            <Text style={styles.note}>Precheck rule: {gate.precheckRuleId}</Text>
          )}
          {gate.resolvedAt && (
            <Text style={styles.note}>
              Resolved {new Date(gate.resolvedAt).toLocaleString()} by {gate.resolvedBy ?? '—'}
              {gate.resolutionNote ? ` — ${gate.resolutionNote}` : ''}
            </Text>
          )}
        </View>
      )}
      <SelectableCopyButton
        label="Export prompt for ChatGPT"
        body={exportPrompt}
        disabledReason="Gate not loaded — refresh and try again."
      />
      {isActive && (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
          <Pressable style={[styles.btn, { flexGrow: 1, minWidth: 100 }]} onPress={onApprove}>
            <Text style={styles.btnText}>Approve spend</Text>
          </Pressable>
          <Pressable style={[styles.btn, { flexGrow: 1, minWidth: 100, opacity: 0.85 }]} onPress={deferOneDay}>
            <Text style={styles.btnText}>Defer 24h</Text>
          </Pressable>
          <Pressable style={[styles.btn, { flexGrow: 1, minWidth: 100, opacity: 0.6 }]} onPress={onCancel}>
            <Text style={styles.btnText}>Cancel</Text>
          </Pressable>
        </View>
      )}
    </View>
  );
}

function ApprovalGateRow({
  gate,
  lockReason,
  onApprove,
  onDefer,
  onCancel,
}: {
  gate: ApprovalGate;
  lockReason: string | null;
  onApprove: () => void;
  onDefer: (deferUntil: string) => void;
  onCancel: () => void;
}) {
  const [open, setOpen] = useState(false);
  const isLocked = lockReason != null && (gate.status === 'pending' || gate.status === 'deferred');
  const isActive = (gate.status === 'pending' || gate.status === 'deferred') && !isLocked;
  const expiresLabel = (() => {
    const expires = new Date(gate.expiresAt).getTime();
    if (!Number.isFinite(expires)) return '—';
    const remaining = expires - Date.now();
    if (remaining <= 0) return 'expired';
    if (remaining < 3_600_000) return `${Math.max(1, Math.floor(remaining / 60_000))}m left`;
    if (remaining < 86_400_000) return `${Math.floor(remaining / 3_600_000)}h left`;
    return `${Math.floor(remaining / 86_400_000)}d left`;
  })();
  const deferOneDay = () => {
    const until = new Date(Date.now() + 86_400_000).toISOString();
    onDefer(until);
  };
  return (
    <View style={styles.chipBlock}>
      <Pressable onPress={() => setOpen((v) => !v)} hitSlop={6}>
        <Text style={styles.chipLabel}>
          {gate.priority} · {gate.actionType} · {gate.status}{isLocked ? ' · locked' : ''} · {expiresLabel}
        </Text>
        <Text style={styles.chipBody}>{gate.title}</Text>
        {isLocked && (
          <Text style={styles.note}>🔒 {lockReason}</Text>
        )}
      </Pressable>
      {open && (
        <View style={{ gap: 6, marginTop: 6 }}>
          <Text style={styles.note}>{gate.description}</Text>
          {gate.actionPayload && (
            <Text style={styles.note}>Next step: {gate.actionPayload}</Text>
          )}
          <Text style={styles.note}>safeDefault if expired: {gate.safeDefault}</Text>
          {gate.ledgerActionId && (
            <Text style={styles.note}>Unblocks ledger: {gate.ledgerActionId}</Text>
          )}
          {gate.dependsOnGateId && (
            <Text style={styles.note}>Depends on gate: {gate.dependsOnGateId}</Text>
          )}
          {gate.resolvedAt && (
            <Text style={styles.note}>
              Resolved {new Date(gate.resolvedAt).toLocaleString()} by {gate.resolvedBy ?? '—'}
              {gate.resolutionNote ? ` — ${gate.resolutionNote}` : ''}
            </Text>
          )}
        </View>
      )}
      {isActive && (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
          <Pressable style={[styles.btn, { flexGrow: 1, minWidth: 100 }]} onPress={onApprove}>
            <Text style={styles.btnText}>Approve</Text>
          </Pressable>
          <Pressable style={[styles.btn, { flexGrow: 1, minWidth: 100, opacity: 0.85 }]} onPress={deferOneDay}>
            <Text style={styles.btnText}>Defer 24h</Text>
          </Pressable>
          <Pressable style={[styles.btn, { flexGrow: 1, minWidth: 100, opacity: 0.6 }]} onPress={onCancel}>
            <Text style={styles.btnText}>Cancel</Text>
          </Pressable>
        </View>
      )}
    </View>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue} numberOfLines={2} ellipsizeMode="tail">{value}</Text>
    </View>
  );
}

function LinkRow({ label, url }: { label: string; url: string }) {
  return (
    <Pressable style={styles.row} onPress={() => Linking.openURL(url)}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={[styles.rowValue, { color: '#d4e157' }]} numberOfLines={1} ellipsizeMode="tail">Open</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 20, gap: 18, paddingBottom: 40 },
  heading: { fontSize: 22, fontWeight: '700' },
  subtitle: { fontSize: 12, opacity: 0.55 },
  section: { gap: 8 },
  sectionTitle: { fontSize: 12, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 1, opacity: 0.5 },
  body: { fontSize: 13, opacity: 0.7 },
  row: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingVertical: 10, paddingHorizontal: 12, borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.05)', gap: 8,
  },
  rowLabel: { fontSize: 13, fontWeight: '600' },
  rowValue: { fontSize: 12, opacity: 0.65, textAlign: 'right', flexShrink: 1 },
  btn: {
    paddingVertical: 10, paddingHorizontal: 14, borderRadius: 10,
    backgroundColor: 'rgba(212,225,87,0.15)', borderWidth: 1,
    borderColor: 'rgba(212,225,87,0.35)', alignItems: 'center',
  },
  btnText: { fontSize: 12, fontWeight: '700', color: '#d4e157' },
  btnSubtitle: { fontSize: 11, opacity: 0.55, paddingHorizontal: 4, marginTop: 1, marginBottom: 2 },
  btnDisabledReason: { fontSize: 11, color: '#ff8a8a', paddingHorizontal: 4, marginTop: 1, marginBottom: 2 },
  note: { fontSize: 11, opacity: 0.55, lineHeight: 15, marginTop: 2 },
  summaryGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  summaryTile: {
    flexGrow: 1, flexBasis: '47%', minHeight: 58,
    paddingVertical: 8, paddingHorizontal: 10, borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.09)',
    gap: 2,
  },
  summaryValue: { fontSize: 13, fontWeight: '700' },
  summaryMeta: { fontSize: 10, opacity: 0.55, lineHeight: 13 },
  chipBlock: {
    paddingVertical: 8, paddingHorizontal: 12, borderRadius: 10,
    backgroundColor: 'rgba(212,225,87,0.06)',
    borderWidth: 1, borderColor: 'rgba(212,225,87,0.2)',
    gap: 4,
  },
  warningBlock: {
    paddingVertical: 8, paddingHorizontal: 12, borderRadius: 10,
    backgroundColor: 'rgba(255,138,138,0.08)',
    borderWidth: 1, borderColor: 'rgba(255,138,138,0.28)',
    gap: 4,
  },
  noticeBlock: {
    paddingVertical: 10, paddingHorizontal: 12, borderRadius: 10,
    backgroundColor: 'rgba(212,225,87,0.12)',
    borderWidth: 1, borderColor: 'rgba(212,225,87,0.38)',
    gap: 6,
  },
  chipLabel: { fontSize: 10, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 1, opacity: 0.55 },
  chipBody: { fontSize: 13, lineHeight: 17 },
  laneProgressRow: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    gap: 8, marginTop: 6,
  },
  laneProgressName: { fontSize: 12, fontWeight: '700' },
  laneProgressMeta: { fontSize: 10, opacity: 0.6 },
  laneProgressBarTrack: {
    height: 6, borderRadius: 3, marginTop: 4,
    backgroundColor: 'rgba(255,255,255,0.07)',
    overflow: 'hidden',
  },
  laneProgressBarFill: {
    height: '100%', borderRadius: 3,
  },
  backlogStandingLine: { fontSize: 12, lineHeight: 17, opacity: 0.75 },
  captureBox: {
    gap: 8, padding: 10, borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)',
  },
  captureLabel: { fontSize: 11, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5, opacity: 0.55 },
  captureInput: {
    backgroundColor: '#0f0f0f', color: '#e0e0e0',
    borderRadius: 8, paddingHorizontal: 10, paddingVertical: 8, fontSize: 13,
  },
  captureInputMulti: { minHeight: 64 },
  captureRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  pill: {
    paddingHorizontal: 10, paddingVertical: 6, borderRadius: 14,
    backgroundColor: '#2a2a2a',
  },
  pillSmall: {
    paddingHorizontal: 9, paddingVertical: 5, borderRadius: 12,
    backgroundColor: '#2a2a2a', minWidth: 30, alignItems: 'center',
  },
  pillActive: { backgroundColor: '#d4e157' },
  pillText: { fontSize: 12, color: '#ccc', fontWeight: '600' },
  pillTextActive: { color: '#0a0a0a', fontWeight: '700' },
  backlogItem: {
    flexDirection: 'row', gap: 10, padding: 10, borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)',
    alignItems: 'flex-start',
  },
  backlogTitle: { fontSize: 13, fontWeight: '700' },
  backlogMeta: { fontSize: 11, opacity: 0.55 },
  backlogDetails: { fontSize: 12, opacity: 0.75, lineHeight: 16 },
  backlogAction: { fontSize: 11, fontWeight: '700' },
  copyBlock: {
    fontSize: 11, lineHeight: 15, color: '#cfd3da',
    backgroundColor: 'rgba(255,255,255,0.04)',
    padding: 10, borderRadius: 8,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
});
