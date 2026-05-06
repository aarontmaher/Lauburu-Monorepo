/**
 * ChatGPT connector / control-centre state types.
 *
 * Spec source of truth: docs/CHATGPT_CONNECTOR_STATE_CONTRACT.md
 * (commit dadde0e). This file is the authoritative TypeScript
 * interface for both the read-route handlers (chat-app server)
 * and the future tmux bridge writer.
 *
 * Rules (mirroring docs/CONNECTOR_SECURITY_MODEL.md invariants 1–10):
 * - schemaVersion is required on every payload.
 * - All string fields pass through redactTokenLikeSubstrings()
 *   before serialization. Callers MUST NOT pre-redact; route
 *   handlers redact at the response boundary so writers can
 *   keep raw context locally.
 * - Field additions are additive-only. Removals require a
 *   schemaVersion bump and a doc commit.
 * - No raw athlete health values, no OAuth tokens, no env values
 *   appear in any of these shapes — even pre-redactor.
 * - All five payloads are admin-token gated at the route layer.
 */

/** Connector schema version. Bump on any breaking change. */
export const CONNECTOR_SCHEMA_VERSION = 1 as const;

/** Coder lane identifiers. Stable; new lanes append. */
export type LaneId = 'claude' | 'codex' | 'claude_chat' | 'chatgpt' | 'cowork';

/** Lane status enum. Bridge falls back to 'idle' on read failure
 *  — never fabricates 'working' / 'done'. */
export type LaneStatus =
  | 'idle'
  | 'working'
  | 'blocked'
  | 'needs_user'
  | 'needs_review'
  | 'done';

/** GitHub Actions run status. Mirrors gh run view JSON. */
export type GithubRunStatus =
  | 'queued'
  | 'in_progress'
  | 'success'
  | 'failure'
  | 'cancelled';

/** Play Console submission lifecycle. */
export type PlayStatus =
  | 'submitted_draft'
  | 'submitted_completed'
  | 'rolled_out'
  | 'failed';

/** TestFlight submission lifecycle. */
export type TestflightStatus =
  | 'uploaded_processing'
  | 'available'
  | 'invalid_binary'
  | 'failed';

/** Typecheck result the bridge extracts from terminal output. */
export type TypecheckResult = 'pass' | 'fail' | 'unknown';

// ---------------------------------------------------------------------------
// 1. work_status
// ---------------------------------------------------------------------------

export interface WorkStatusLiveStatus {
  androidVersionCode: number | null;
  iosBuildNumber: string | null;
  androidPlayTrack: 'internal' | 'closed' | 'open' | 'production' | null;
  iosTestflightGroup: string | null;
  /** ISO timestamp of the most recent Railway deploy seen. */
  lastRailwayDeployAt: string | null;
  cloudflareWorkerDeployed: boolean;
}

export interface WorkStatusRepoStatus {
  /** Short SHA. */
  head: string;
  branch: string;
  dirtyFileCount: number;
  untrackedFileCount: number;
  /** ISO timestamp of HEAD. */
  lastCommitAt: string;
  /** Plain-text subject; redactor applied. */
  lastCommitMessage: string;
}

export interface WorkStatus {
  schemaVersion: typeof CONNECTOR_SCHEMA_VERSION;
  /** ISO timestamp the payload was assembled. */
  generatedAt: string;
  /** One sentence; redactor applied. Null when nothing in flight. */
  currentPriority: string | null;
  /** One sentence; null when nothing blocks. */
  currentBlocker: string | null;
  liveStatus: WorkStatusLiveStatus;
  repoStatus: WorkStatusRepoStatus;
  /** One actionable next step in plain English. */
  nextAction: string | null;
}

// ---------------------------------------------------------------------------
// 2. coder_lanes
// ---------------------------------------------------------------------------

export interface CoderLaneRow {
  laneId: LaneId;
  status: LaneStatus;
  /** ISO timestamp of the most recent bridge snapshot. */
  lastSeenAt: string | null;
  /** Prompt-ID currently in flight. Null when idle. */
  currentPromptId: string | null;
  /** Prompt-ID of the most recently completed turn. */
  lastPromptId: string | null;
  /** Bridge-extracted summary, capped 1200 chars, redactor applied. */
  lastSummary: string | null;
  /** Short SHA of the most recent commit attributed to this lane. */
  lastCommit: string | null;
  lastTypecheckResult: TypecheckResult | null;
  /** Repo-relative paths only; redactor applied to each entry. */
  dirtyFiles: string[];
  /** Owner-set; never auto-set by the bridge. */
  nextPrompt: string | null;
}

export interface CoderLanes {
  schemaVersion: typeof CONNECTOR_SCHEMA_VERSION;
  generatedAt: string;
  lanes: CoderLaneRow[];
}

// ---------------------------------------------------------------------------
// 3. build_status
// ---------------------------------------------------------------------------

export interface AndroidBuildStatus {
  versionCode: number | null;
  appVersion: string | null;
  githubRunId: string | null;
  githubStatus: GithubRunStatus | null;
  easBuildId: string | null;
  /** Public expo.dev URL; safe to surface. */
  easBuildUrl: string | null;
  playSubmissionId: string | null;
  playStatus: PlayStatus | null;
  playTrack: 'internal' | 'closed' | 'open' | 'production' | null;
}

export interface IosBuildStatus {
  buildNumber: string | null;
  appVersion: string | null;
  githubRunId: string | null;
  githubStatus: GithubRunStatus | null;
  easBuildId: string | null;
  easBuildUrl: string | null;
  testflightSubmissionId: string | null;
  testflightStatus: TestflightStatus | null;
  testflightGroup: string | null;
}

export interface BuildStatus {
  schemaVersion: typeof CONNECTOR_SCHEMA_VERSION;
  generatedAt: string;
  android: AndroidBuildStatus;
  ios: IosBuildStatus;
}

// ---------------------------------------------------------------------------
// 4. handoff
// ---------------------------------------------------------------------------

export interface Handoff {
  schemaVersion: typeof CONNECTOR_SCHEMA_VERSION;
  generatedAt: string;
  /** Prompt-ID of the most recent Claude prompt. */
  latestClaudePrompt: string | null;
  /** Prompt-ID of the most recent Codex prompt. */
  latestCodexPrompt: string | null;
  /** Plain-English steps the owner must do by hand. Redactor applied. */
  manualSteps: string[];
  /** Repo-relative paths the active lanes must NOT touch. */
  doNotTouch: string[];
  /** Hard gate on the in-app Dispatch button. Owner-set only. */
  safeToBuild: boolean;
  /** One sentence explaining the safeToBuild value. */
  safeToBuildReason: string;
}

// ---------------------------------------------------------------------------
// 5. terminal_summary
// ---------------------------------------------------------------------------

export interface TerminalSummaryEntry {
  laneId: LaneId;
  /** ISO timestamp the entry was captured. */
  at: string;
  /** Bridge-extracted summary, capped 1200 chars, redactor applied. */
  summary: string;
  /** Short verification claim, capped 240 chars. */
  verification: string;
  /** Owner-actionable next step, capped 240 chars. */
  nextAction: string;
  /** Process exit code if known; -1 means "still running". */
  exitCode: number | null;
}

export interface TerminalSummary {
  schemaVersion: typeof CONNECTOR_SCHEMA_VERSION;
  generatedAt: string;
  /** Most recent first. Cap: 10 entries per lane, 50 total. */
  entries: TerminalSummaryEntry[];
}

// ---------------------------------------------------------------------------
// Write payloads (bridge / owner only)
// ---------------------------------------------------------------------------

/** POST /admin/lane-status body. */
export interface LaneStatusWritePayload {
  schemaVersion: typeof CONNECTOR_SCHEMA_VERSION;
  /** Single lane row to upsert. Bridge daemon signs the request. */
  row: CoderLaneRow;
  /** Bridge daemon HMAC over JSON.stringify(row). */
  bridgeSignature: string;
}

/** POST /admin/terminal-summary body. */
export interface TerminalSummaryWritePayload {
  schemaVersion: typeof CONNECTOR_SCHEMA_VERSION;
  entry: TerminalSummaryEntry;
  bridgeSignature: string;
}

/** POST /admin/handoff body. Owner-tap only — no bridge signature. */
export interface HandoffWritePayload {
  schemaVersion: typeof CONNECTOR_SCHEMA_VERSION;
  /** Partial update; server merges with current handoff. */
  patch: Partial<Omit<Handoff, 'schemaVersion' | 'generatedAt'>>;
  /** Required when toggling safeToBuild from false → true. */
  ownerConfirmation: 'i_have_verified_the_lanes' | null;
}

// ---------------------------------------------------------------------------
// Route → response type map
// ---------------------------------------------------------------------------

export interface ConnectorRouteMap {
  'GET /api/work_status': WorkStatus;
  'GET /api/coder_lanes': CoderLanes;
  'GET /api/build_status': BuildStatus;
  'GET /api/handoff': Handoff;
  'GET /api/athlete-memory/admin/work-status': WorkStatus;
  'GET /api/athlete-memory/admin/agent-status': CoderLanes;
  'GET /api/athlete-memory/admin/build-status': BuildStatus;
  'GET /api/athlete-memory/admin/handoff': Handoff;
  'GET /api/athlete-memory/admin/terminal-summary': TerminalSummary;
  'POST /api/athlete-memory/admin/lane-status': { ok: true } | { ok: false; reason: string };
  'POST /api/athlete-memory/admin/terminal-summary': { ok: true } | { ok: false; reason: string };
  'POST /api/athlete-memory/admin/handoff': { ok: true; merged: Handoff } | { ok: false; reason: string };
}

/** Reasons a write route may reject. Stable enum for clients. */
export type ConnectorWriteRejection =
  | 'admin_token_missing'
  | 'admin_token_mismatch'
  | 'bridge_signature_invalid'
  | 'owner_confirmation_required'
  | 'schema_version_mismatch'
  | 'payload_redaction_failed'
  | 'lane_id_unknown'
  | 'rate_limited';
