/**
 * GET /api/control_centre — consolidated snapshot for the iPhone
 * Admin/Dev control-centre screen.
 *
 * Schema source of truth: docs/CONTROL_CENTRE_MVP_SPEC.md.
 *
 * Reads existing connector_* tables — no new schema. When the
 * Phase-2 tables (connector_manual_steps, connector_backlog_items)
 * land, the placeholder branches below switch over without a
 * route-shape change.
 *
 * Privacy contract for this route:
 *   - lane.oneLine is the lastSummary truncated to ≤140 chars after
 *     the bridge's existing two-pass redactor; raw terminal text
 *     never lands here.
 *   - buildDeploy.*.lastChange is server-composed prose ≤120 chars,
 *     never EAS / Play / TestFlight UUIDs or run IDs (those stay on
 *     the private /api/build_status route).
 *   - manualSteps[].text is taken verbatim from the existing
 *     handoff payload (already redacted by the bridge); cap 200.
 *   - suggestionCounts is null until the connector_backlog_items
 *     table ships in Phase 2.
 *   - safety.privateFieldsWithheld is always true so consumers
 *     can assert on it.
 */

import type { Env } from './worker-env';
import { getSupabaseAdapter } from './supabase';
import { buildOperatingRulesSummary, type OperatingRulesSummary } from './operating-rules';

export const CONTROL_CENTRE_SCHEMA_VERSION = 1 as const;

/** ms; rows older than this flip mcpConnectionStatus to 'stale'. */
export const FRESHNESS_WINDOW_MS = 10 * 60 * 1000;

export type StatusLabel = 'live' | 'repo-only' | 'tester-build' | 'blocked';
export type McpConnectionStatus = 'connected' | 'stale' | 'fallback' | 'offline';
export type LaneId = 'claude' | 'codex' | 'claude_chat' | 'chatgpt' | 'cowork';
export type LaneStatus =
  | 'idle' | 'working' | 'blocked' | 'needs_user' | 'needs_review' | 'done';

export interface ControlCentreCard {
  text: string;
  status: StatusLabel;
  updatedAt: string;
}

export interface ControlCentreLane {
  laneId: LaneId;
  status: LaneStatus;
  oneLine: string;
  lastSeenAt: string | null;
  hasOpenPrompt: boolean;
}

export interface ControlCentreBuildDeploySide {
  versionCode?: number | null;
  buildNumber?: string | null;
  status: StatusLabel;
  lastChange: string;
  updatedAt: string;
}

export interface ControlCentreBuildDeploy {
  android: ControlCentreBuildDeploySide & { versionCode: number | null };
  ios: ControlCentreBuildDeploySide & { buildNumber: string | null };
}

export interface ControlCentreManualStep {
  id: string;
  text: string;
  category:
    | 'supabase' | 'cloudflare' | 'eas' | 'play_console'
    | 'app_store_connect' | 'github' | 'other';
  blocking: boolean;
  approvalRequired: boolean;
  approval: 'pending' | 'approved' | 'completed' | 'declined';
  createdAt: string;
  updatedAt: string;
}

export interface ControlCentreBacklogItem {
  id: string;
  title: string;
  priority: number;
  status: 'live' | 'repo-only' | 'tester-build' | 'blocked' | 'done';
  type:
    | 'bug' | 'ux_issue' | 'feature_idea' | 'release_blocker'
    | 'health_data_issue' | 'ai_coaching_idea'
    | 'monetisation_payment_idea' | 'railway_backend_issue'
    | 'source_integration_issue';
  riskLevel: 'low' | 'medium' | 'high';
  needsBuild: boolean;
  updatedAt: string;
}

export interface ControlCentreSuggestionCounts {
  /** docs/FEEDBACK_SUGGESTIONS.md candidates not yet approved. */
  candidate: number;
  /** Items with a Lane-3 approval gate set. */
  awaitingApproval: number;
}

export interface ControlCentreRepoSummary {
  branch: string | null;
  shortHead: string | null;
  dirtyFileCount: number | null;
  updatedAt: string;
}

export interface ControlCentreSafety {
  /** Always false — this route is admin-token-gated. */
  publicSafe: false;
  /** Always true — free-text and IDs are intentionally compressed. */
  privateFieldsWithheld: true;
  /** Sentinel listing the field categories the route deliberately drops. */
  withheld: readonly string[];
}

export interface ControlCentrePromptRef {
  id: string;
  title: string;
  templateId: string;
}

export interface ControlCentreSnapshot {
  schemaVersion: typeof CONTROL_CENTRE_SCHEMA_VERSION;
  generatedAt: string;
  updatedAt: string;
  mcpConnectionStatus: McpConnectionStatus;
  freshnessWindowMs: number;
  dataSource: 'supabase' | 'placeholder';

  priority: ControlCentreCard;
  blocker: ControlCentreCard | null;
  nextAction: ControlCentreCard;

  lanes: ControlCentreLane[];

  buildDeploy: ControlCentreBuildDeploy;

  repo: ControlCentreRepoSummary;

  manualSteps: ControlCentreManualStep[];
  manualStepsCount: number;

  /** Top-1 open item from connector_backlog_items by priority asc. */
  topBacklog: ControlCentreBacklogItem | null;

  /** Live counts when connector_backlog_items + connector_manual_steps
   *  reads succeed; null on read failure. */
  suggestionCounts: ControlCentreSuggestionCounts | null;

  promptLibrary: readonly ControlCentrePromptRef[];

  /** Mirror of docs/OPERATING_RULES.md — count + ids + titles only. Full bodies via `project.get_operating_rules`. */
  operatingRules: OperatingRulesSummary;

  safety: ControlCentreSafety;
}

const PROMPT_LIBRARY: readonly ControlCentrePromptRef[] = [
  { id: 'pl-claude', title: 'Claude prompt', templateId: 'claude_lane_prompt' },
  { id: 'pl-codex', title: 'Codex prompt', templateId: 'codex_lane_prompt' },
  { id: 'pl-chatgpt', title: 'ChatGPT status prompt', templateId: 'chatgpt_status_prompt' },
  { id: 'pl-terminal', title: 'Terminal-check prompt', templateId: 'terminal_check_prompt' },
] as const;

const WITHHELD_FIELDS: readonly string[] = [
  'lane.lastSummary (compressed to ≤140 char oneLine)',
  'buildDeploy.*.easBuildId',
  'buildDeploy.*.githubRunId',
  'buildDeploy.android.playSubmissionId',
  'buildDeploy.ios.testflightSubmissionId',
  'handoff.payload.safeToBuildReason (only the boolean surfaces here)',
  'connector_terminal_summary entries (private /api/terminal_summary only)',
  'currentPromptId / lastPromptId / nextPrompt text bodies',
] as const;

// ── helpers ────────────────────────────────────────────────────────────

function truncate(text: string, cap: number): string {
  if (text.length <= cap) return text;
  const cut = text.lastIndexOf(' ', cap);
  const at = cut < cap / 2 ? cap : cut;
  return `${text.slice(0, at).trimEnd()}…`;
}

function isIsoZ(s: unknown): s is string {
  // Accept the two ISO-8601 UTC forms callers produce:
  //   '2026-05-07T12:34:56Z'              (Worker / new Date().toISOString())
  //   '2026-05-07T12:34:56.123456+00:00'  (Postgres timestamptz default)
  return typeof s === 'string'
    && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$/.test(s);
}

function maxIsoZ(values: ReadonlyArray<string | null | undefined>): string | null {
  let max: string | null = null;
  for (const v of values) {
    if (!isIsoZ(v)) continue;
    if (max === null || v > max) max = v;
  }
  return max;
}

function pickEnum<T extends string>(value: unknown, allowed: readonly T[]): T | null {
  return typeof value === 'string' && (allowed as readonly string[]).includes(value)
    ? (value as T)
    : null;
}

const LANE_STATUSES: readonly LaneStatus[] = [
  'idle', 'working', 'blocked', 'needs_user', 'needs_review', 'done',
] as const;

const LANE_IDS: readonly LaneId[] = [
  'claude', 'codex', 'claude_chat', 'chatgpt', 'cowork',
] as const;

// ── status derivation ──────────────────────────────────────────────────

function derivePriorityStatus(blockerText: string | null): StatusLabel {
  return blockerText && blockerText.length > 0 ? 'blocked' : 'live';
}

const ANDROID_PRIORITY: ReadonlyArray<{ match: (state: { github?: string; play?: string }) => boolean; label: StatusLabel }> = [
  { match: (s) => s.github === 'failure' || s.play === 'failed', label: 'blocked' },
  { match: (s) => s.play === 'rolled_out' || s.play === 'submitted_completed', label: 'live' },
  { match: (s) => s.play === 'submitted_draft' || s.github === 'success' || s.github === 'in_progress' || s.github === 'queued', label: 'tester-build' },
];

function deriveAndroidStatus(github: string | null, play: string | null): StatusLabel {
  for (const rule of ANDROID_PRIORITY) {
    if (rule.match({ github: github ?? undefined, play: play ?? undefined })) return rule.label;
  }
  return 'repo-only';
}

const IOS_PRIORITY: ReadonlyArray<{ match: (state: { github?: string; tf?: string }) => boolean; label: StatusLabel }> = [
  { match: (s) => s.github === 'failure' || s.tf === 'failed' || s.tf === 'invalid_binary', label: 'blocked' },
  { match: (s) => s.tf === 'available', label: 'live' },
  { match: (s) => s.tf === 'uploaded_processing' || s.github === 'success' || s.github === 'in_progress' || s.github === 'queued', label: 'tester-build' },
];

function deriveIosStatus(github: string | null, tf: string | null): StatusLabel {
  for (const rule of IOS_PRIORITY) {
    if (rule.match({ github: github ?? undefined, tf: tf ?? undefined })) return rule.label;
  }
  return 'repo-only';
}

// ── builders ───────────────────────────────────────────────────────────

interface WorkStatusPayload {
  generatedAt?: string;
  currentPriority?: string | null;
  currentBlocker?: string | null;
  nextAction?: string | null;
  liveStatus?: { androidVersionCode?: number | null; iosBuildNumber?: string | null };
  repoStatus?: {
    head?: string | null;
    branch?: string | null;
    dirtyFileCount?: number | null;
    lastCommitAt?: string | null;
    lastCommitMessage?: string | null;
  };
}

interface CoderLanePayload {
  laneId?: string;
  status?: string;
  lastSeenAt?: string | null;
  currentPromptId?: string | null;
  lastPromptId?: string | null;
  lastSummary?: string | null;
}

interface BuildStatusPayload {
  generatedAt?: string;
  android?: {
    versionCode?: number | null;
    githubStatus?: string | null;
    playStatus?: string | null;
    playTrack?: string | null;
  };
  ios?: {
    buildNumber?: string | null;
    githubStatus?: string | null;
    testflightStatus?: string | null;
    testflightGroup?: string | null;
  };
}

interface HandoffPayload {
  generatedAt?: string;
  manualSteps?: unknown;
}

function placeholderCard(text: string, status: StatusLabel, generatedAt: string): ControlCentreCard {
  return { text, status, updatedAt: generatedAt };
}

function buildPriorityCards(
  payload: WorkStatusPayload | null,
  generatedAt: string,
): { priority: ControlCentreCard; blocker: ControlCentreCard | null; nextAction: ControlCentreCard; updatedAt: string } {
  const sourceUpdatedAt = isIsoZ(payload?.generatedAt) ? payload!.generatedAt! : generatedAt;
  const priorityText = truncate(payload?.currentPriority ?? 'No active priority on record.', 280);
  const blockerText = payload?.currentBlocker?.trim() ?? '';
  const nextActionText = truncate(payload?.nextAction ?? 'No next action set.', 280);

  return {
    priority: { text: priorityText, status: derivePriorityStatus(blockerText || null), updatedAt: sourceUpdatedAt },
    blocker: blockerText ? { text: truncate(blockerText, 280), status: 'blocked', updatedAt: sourceUpdatedAt } : null,
    nextAction: { text: nextActionText, status: 'live', updatedAt: sourceUpdatedAt },
    updatedAt: sourceUpdatedAt,
  };
}

function buildLane(row: { lane_id: string; payload: unknown }): ControlCentreLane | null {
  const payload = (row.payload ?? {}) as CoderLanePayload;
  const laneId = pickEnum(row.lane_id, LANE_IDS);
  const status = pickEnum(payload.status, LANE_STATUSES);
  if (!laneId || !status) return null;
  const lastSeenAt = isIsoZ(payload.lastSeenAt) ? payload.lastSeenAt : null;
  const summary = typeof payload.lastSummary === 'string' && payload.lastSummary.length > 0
    ? truncate(payload.lastSummary.replace(/\s+/g, ' ').trim(), 140)
    : `${laneId}: ${status}`;
  return {
    laneId,
    status,
    oneLine: summary,
    lastSeenAt,
    hasOpenPrompt: typeof payload.currentPromptId === 'string' && payload.currentPromptId.length > 0,
  };
}

function buildBuildDeploy(payload: BuildStatusPayload | null, generatedAt: string): ControlCentreBuildDeploy {
  const sourceUpdatedAt = isIsoZ(payload?.generatedAt) ? payload!.generatedAt! : generatedAt;
  const android = payload?.android ?? {};
  const ios = payload?.ios ?? {};
  const androidStatus = deriveAndroidStatus(
    typeof android.githubStatus === 'string' ? android.githubStatus : null,
    typeof android.playStatus === 'string' ? android.playStatus : null,
  );
  const iosStatus = deriveIosStatus(
    typeof ios.githubStatus === 'string' ? ios.githubStatus : null,
    typeof ios.testflightStatus === 'string' ? ios.testflightStatus : null,
  );
  const versionCode = typeof android.versionCode === 'number' ? android.versionCode : null;
  const buildNumber = typeof ios.buildNumber === 'string' ? ios.buildNumber : null;
  return {
    android: {
      versionCode,
      status: androidStatus,
      lastChange: truncate(
        `Android v${versionCode ?? '?'} · ${android.playStatus ?? 'unknown'} on ${android.playTrack ?? 'internal'}`,
        120,
      ),
      updatedAt: sourceUpdatedAt,
    },
    ios: {
      buildNumber,
      status: iosStatus,
      lastChange: truncate(
        `iOS Build ${buildNumber ?? '?'} · ${ios.testflightStatus ?? 'unknown'} → ${ios.testflightGroup ?? 'Team'}`,
        120,
      ),
      updatedAt: sourceUpdatedAt,
    },
  };
}

function buildRepo(workPayload: WorkStatusPayload | null, generatedAt: string): ControlCentreRepoSummary {
  const repo = workPayload?.repoStatus ?? {};
  const branch = typeof repo.branch === 'string' && /^[A-Za-z0-9._\-/]{1,80}$/.test(repo.branch) ? repo.branch : null;
  const head = typeof repo.head === 'string' && /^[0-9a-f]{7,12}$/.test(repo.head) ? repo.head : null;
  const dirty = typeof repo.dirtyFileCount === 'number' && Number.isFinite(repo.dirtyFileCount) ? repo.dirtyFileCount : null;
  return {
    branch,
    shortHead: head,
    dirtyFileCount: dirty,
    updatedAt: isIsoZ(workPayload?.generatedAt) ? workPayload!.generatedAt! : generatedAt,
  };
}

function buildManualStepsFromHandoff(payload: HandoffPayload | null, generatedAt: string): ControlCentreManualStep[] {
  if (!payload || !Array.isArray(payload.manualSteps)) return [];
  const sourceUpdatedAt = isIsoZ(payload.generatedAt) ? payload.generatedAt! : generatedAt;
  const steps: ControlCentreManualStep[] = [];
  for (let i = 0; i < payload.manualSteps.length && steps.length < 10; i++) {
    const raw = payload.manualSteps[i];
    if (typeof raw !== 'string' || raw.length === 0) continue;
    steps.push({
      id: `ms-${i}`,
      text: truncate(raw, 200),
      category: 'other',
      blocking: false,
      approvalRequired: false,
      approval: 'pending',
      createdAt: sourceUpdatedAt,
      updatedAt: sourceUpdatedAt,
    });
  }
  return steps;
}

const STEP_CATEGORIES: ReadonlyArray<ControlCentreManualStep['category']> = [
  'supabase', 'cloudflare', 'eas', 'play_console',
  'app_store_connect', 'github', 'other',
] as const;
const STEP_APPROVALS: ReadonlyArray<ControlCentreManualStep['approval']> = [
  'pending', 'approved', 'completed', 'declined',
] as const;

function buildManualStepsFromTable(rows: Array<{
  id: string; text: string; category: string;
  blocking: boolean; approval_required: boolean; approval: string;
  created_at: string; updated_at: string;
}>): ControlCentreManualStep[] {
  const steps: ControlCentreManualStep[] = [];
  for (const row of rows) {
    if (steps.length >= 10) break;
    const category = pickEnum(row.category, STEP_CATEGORIES);
    const approval = pickEnum(row.approval, STEP_APPROVALS);
    if (!category || !approval) continue;
    steps.push({
      id: row.id,
      text: truncate(row.text ?? '', 200),
      category,
      blocking: !!row.blocking,
      approvalRequired: !!row.approval_required,
      approval,
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    });
  }
  return steps;
}

const BACKLOG_STATUSES: ReadonlyArray<ControlCentreBacklogItem['status']> = [
  'live', 'repo-only', 'tester-build', 'blocked', 'done',
] as const;
const BACKLOG_TYPES: ReadonlyArray<ControlCentreBacklogItem['type']> = [
  'bug', 'ux_issue', 'feature_idea', 'release_blocker',
  'health_data_issue', 'ai_coaching_idea',
  'monetisation_payment_idea', 'railway_backend_issue',
  'source_integration_issue',
] as const;
const BACKLOG_RISKS: ReadonlyArray<ControlCentreBacklogItem['riskLevel']> = [
  'low', 'medium', 'high',
] as const;

function buildBacklogItem(row: {
  id: string; title: string; priority: number; status: string;
  type: string; risk_level: string; needs_build: boolean; updated_at: string;
} | null): ControlCentreBacklogItem | null {
  if (!row) return null;
  const status = pickEnum(row.status, BACKLOG_STATUSES);
  const type = pickEnum(row.type, BACKLOG_TYPES);
  const riskLevel = pickEnum(row.risk_level, BACKLOG_RISKS);
  if (!status || !type || !riskLevel) return null;
  if (typeof row.priority !== 'number' || !Number.isInteger(row.priority) || row.priority < 1 || row.priority > 11) return null;
  return {
    id: row.id,
    title: truncate(row.title ?? '', 120),
    priority: row.priority,
    status,
    type,
    riskLevel,
    needsBuild: !!row.needs_build,
    updatedAt: row.updated_at,
  };
}

function deriveMcpConnectionStatus(
  dataSource: 'supabase' | 'placeholder',
  updatedAt: string | null,
  generatedAt: string,
): McpConnectionStatus {
  if (dataSource === 'placeholder') return 'fallback';
  if (!updatedAt) return 'fallback';
  const ageMs = new Date(generatedAt).getTime() - new Date(updatedAt).getTime();
  if (Number.isFinite(ageMs) && ageMs > FRESHNESS_WINDOW_MS) return 'stale';
  return 'connected';
}

// ── public entry point ─────────────────────────────────────────────────

export async function buildControlCentreSnapshot(env: Env): Promise<ControlCentreSnapshot> {
  const generatedAt = new Date().toISOString();
  const adapter = getSupabaseAdapter(env);

  if (!adapter.configured) {
    const cards = buildPriorityCards(null, generatedAt);
    return {
      schemaVersion: CONTROL_CENTRE_SCHEMA_VERSION,
      generatedAt,
      updatedAt: generatedAt,
      mcpConnectionStatus: 'fallback',
      freshnessWindowMs: FRESHNESS_WINDOW_MS,
      dataSource: 'placeholder',
      priority: cards.priority,
      blocker: cards.blocker,
      nextAction: cards.nextAction,
      lanes: [],
      buildDeploy: buildBuildDeploy(null, generatedAt),
      repo: buildRepo(null, generatedAt),
      manualSteps: [],
      manualStepsCount: 0,
      topBacklog: null,
      suggestionCounts: null,
      promptLibrary: PROMPT_LIBRARY,
      operatingRules: buildOperatingRulesSummary(),
      safety: { publicSafe: false, privateFieldsWithheld: true, withheld: WITHHELD_FIELDS },
    };
  }

  const [workRow, lanesRows, buildRow, handoffRow, manualRows, backlogRow, suggestionCounts] = await Promise.all([
    adapter.fetchSingleRowPayload('connector_work_status'),
    adapter.fetchCoderLaneRows(),
    adapter.fetchSingleRowPayload('connector_build_status'),
    adapter.fetchSingleRowPayload('connector_handoff'),
    adapter.fetchManualSteps(10),
    adapter.fetchTopBacklogItem(),
    adapter.fetchSuggestionCounts(),
  ]);

  const workPayload = (workRow as WorkStatusPayload | null) ?? null;
  const buildPayload = (buildRow as BuildStatusPayload | null) ?? null;
  const handoffPayload = (handoffRow as HandoffPayload | null) ?? null;

  const cards = buildPriorityCards(workPayload, generatedAt);
  const lanes = (lanesRows ?? [])
    .map((r) => buildLane(r))
    .filter((l): l is ControlCentreLane => l !== null);
  const buildDeploy = buildBuildDeploy(buildPayload, generatedAt);
  const repo = buildRepo(workPayload, generatedAt);

  // Prefer rich rows from connector_manual_steps. Fall back to the
  // legacy handoff.manualSteps string array when the table read
  // returns null (network failure) or empty (table not yet seeded).
  const manualSteps =
    Array.isArray(manualRows) && manualRows.length > 0
      ? buildManualStepsFromTable(manualRows)
      : buildManualStepsFromHandoff(handoffPayload, generatedAt);

  const topBacklog = buildBacklogItem(backlogRow);

  const dataSource: 'supabase' | 'placeholder' =
    workPayload || lanes.length > 0 || buildPayload || handoffPayload || manualSteps.length > 0 || topBacklog
      ? 'supabase'
      : 'placeholder';

  const updatedAt = maxIsoZ([
    cards.updatedAt,
    buildDeploy.android.updatedAt,
    buildDeploy.ios.updatedAt,
    repo.updatedAt,
    ...lanes.map((l) => l.lastSeenAt),
    ...manualSteps.map((s) => s.updatedAt),
    topBacklog?.updatedAt,
  ]) ?? generatedAt;

  return {
    schemaVersion: CONTROL_CENTRE_SCHEMA_VERSION,
    generatedAt,
    updatedAt,
    mcpConnectionStatus: deriveMcpConnectionStatus(dataSource, updatedAt, generatedAt),
    freshnessWindowMs: FRESHNESS_WINDOW_MS,
    dataSource,
    priority: cards.priority,
    blocker: cards.blocker,
    nextAction: cards.nextAction,
    lanes,
    buildDeploy,
    repo,
    manualSteps,
    manualStepsCount: manualSteps.length,
    topBacklog,
    suggestionCounts,
    promptLibrary: PROMPT_LIBRARY,
    operatingRules: buildOperatingRulesSummary(),
    safety: { publicSafe: false, privateFieldsWithheld: true, withheld: WITHHELD_FIELDS },
  };
}
