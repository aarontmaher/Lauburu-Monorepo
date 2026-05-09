/**
 * Typed client for the headless-agent controller surfaces on the
 * Lauburu MCP. Mirrors the server-side response shapes from
 * grapplingmap-mcp:server.api_controller_overview and the approval-
 * inbox actions (approve / reject / defer).
 *
 * Repo-only scaffold: the existing apps/mobile/app/admin-dev.tsx can
 * import these helpers when the next mobile-side bundle wires the
 * controller tiles into the native screen. Until then this file is
 * a build-clean type contract — no rendering changes, no behaviour
 * changes.
 *
 * Status discipline: every tile carries an `evidenceLabel` so the
 * eventual UI can render the operating-rules badge per tile without
 * a second fetch.
 */

export type ControllerEvidenceLabel =
  | 'live-now'
  | 'preview-only'
  | 'installed-build verified'
  | 'planned-only'
  | 'repo-only';

export interface ControllerIntegrityTile {
  gate_status: 'green' | 'degraded' | 'red';
  blocking_release: boolean;
  breach_count: number;
  evidence_label: ControllerEvidenceLabel;
}

export interface ControllerApprovalsTile {
  total: number;
  needs_now: number;
  deferred: number;
  overdue_defers: number;
  evidence_label: ControllerEvidenceLabel;
}

export interface ControllerLanesTile {
  total: number;
  idle: number;
  stale: number;
  crashed: number;
  terminal_disagreement: number;
  evidence_label: ControllerEvidenceLabel;
}

export interface ControllerHighPriorityTile {
  pending: number;
  evidence_label: ControllerEvidenceLabel;
}

export interface ControllerAuditTile {
  audit_review_pending: number;
  release_gate_open: number;
  recent_session: null | {
    session_id: string;
    platform: 'ios_device' | 'android_device' | 'ios_simulator' | 'android_emulator';
    build_id: string;
    session_dir: string;
    created_at: string;
  };
  evidence_label: ControllerEvidenceLabel;
}

export interface ControllerOvernightTile {
  pending: number;
  evidence_label: ControllerEvidenceLabel;
}

export interface ControllerOverview {
  ok: true;
  computed_at: string;
  tiles: {
    integrity: ControllerIntegrityTile;
    approvals: ControllerApprovalsTile;
    lanes: ControllerLanesTile;
    high_priority_queue: ControllerHighPriorityTile;
    audit: ControllerAuditTile;
    overnight: ControllerOvernightTile;
  };
  freshness: {
    work_status_updated_at: string | null;
    last_real_device_audit_at: string | null;
  };
}

export type ApprovalAction =
  | { action: 'approve'; target_queue?: string }
  | { action: 'reject'; reason: string }
  | { action: 'defer'; defer_until: string; reason?: string };

export interface ApprovalActionResponse {
  ok: boolean;
  action?: 'approved' | 'rejected' | 'deferred';
  item?: unknown;
  error?: string;
}

export interface ControllerClientOptions {
  /** Base URL of the MCP, e.g. `https://mcp.lauburugrapplingmap.com`. */
  baseUrl: string;
  /** Operator/admin bearer; never persisted to disk by this module. */
  token: string;
  /** Optional fetch timeout in ms (default 8000). */
  timeoutMs?: number;
}

class ControllerClientError extends Error {
  status: number;
  body: string;
  constructor(status: number, body: string, message: string) {
    super(message);
    this.name = 'ControllerClientError';
    this.status = status;
    this.body = body;
  }
}

async function call<T>(
  opts: ControllerClientOptions,
  path: string,
  init?: RequestInit,
): Promise<T> {
  const url = opts.baseUrl.replace(/\/+$/, '') + path;
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), opts.timeoutMs ?? 8000);
  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      signal: ctl.signal,
      headers: {
        ...(init?.headers ?? {}),
        Authorization: `Bearer ${opts.token}`,
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
    });
  } finally {
    clearTimeout(timer);
  }
  const text = await res.text();
  if (!res.ok) {
    throw new ControllerClientError(res.status, text, `HTTP ${res.status}`);
  }
  return text ? (JSON.parse(text) as T) : ({} as T);
}

export async function fetchControllerOverview(
  opts: ControllerClientOptions,
): Promise<ControllerOverview> {
  return call<ControllerOverview>(opts, '/api/controller-overview');
}

/**
 * Approve / reject / defer an item in the human-approval queue.
 * Server enforces validation: reject requires a non-empty reason;
 * defer requires an ISO-8601 `defer_until`; both 400 otherwise.
 */
export async function submitApprovalAction(
  opts: ControllerClientOptions,
  jobId: string,
  body: ApprovalAction,
): Promise<ApprovalActionResponse> {
  return call<ApprovalActionResponse>(opts, `/api/approval-inbox/${encodeURIComponent(jobId)}`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Snapshot of the widget + push channel status. `push.evidence_label`
 * flips from `planned-only` to `live-now` once the FCM env vars are
 * set on the MCP daemon.
 */
export interface WidgetsStatus {
  ok: true;
  computed_at: string;
  widget: {
    foreground_poll_seconds: number;
    background_poll_seconds: number;
    evidence_label: ControllerEvidenceLabel;
  };
  push: {
    fcm_configured: boolean;
    fcm_project_present: boolean;
    fcm_credentials_present: boolean;
    topics: Record<string, string>;
    last_notification_at: string | null;
    evidence_label: ControllerEvidenceLabel;
  };
  operator_action_required: string | null;
}

export async function fetchWidgetsStatus(
  opts: ControllerClientOptions,
): Promise<WidgetsStatus> {
  return call<WidgetsStatus>(opts, '/api/widgets-status');
}

export { ControllerClientError };
