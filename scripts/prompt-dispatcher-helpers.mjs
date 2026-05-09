/**
 * Pure helpers for prompt-dispatcher.mjs.
 *
 * The dispatcher is intentionally conservative: it only selects
 * explicitly approved, public-safe prompts, and refuses build /
 * upload / release-shaped work even when a queue row asks for it.
 */

const ALLOWED_LANES = new Set(['agent', 'claude', 'codex']);
const READY_STATUSES = new Set(['queued', 'ready', 'approved']);
const PRIORITY_RANK = new Map([
  ['P0', 0],
  ['P1', 1],
  ['P2', 2],
  ['P3', 3],
]);
const DEFAULT_BRIDGE_FRESH_MS = 60_000;

export const UNSAFE_PROMPT_PATTERNS = Object.freeze([
  /\beas\b/i,
  /\bbuild\b/i,
  /\bsubmit\b/i,
  /\bupload\b/i,
  /\brelease\b/i,
  /\bproduction\b/i,
  /\bplay console\b/i,
  /\btestflight\b/i,
  /\bapp store\b/i,
  /\bgoogle play\b/i,
  /\bwrangler deploy\b/i,
  /\bdeploy\b/i,
  /\bsecret\b/i,
  /\btoken\b/i,
]);

const NEGATION_LINE = /^\s*(-\s*)?(no|never|do not|don't|without)\b/i;

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function text(value) {
  return typeof value === 'string' ? value.trim() : '';
}

function nowIso() {
  return new Date().toISOString();
}

export function isLaneIdle(lane) {
  if (!isObject(lane)) return false;
  const status = text(lane.status).toLowerCase();
  const terminalStatus = text(lane.terminalStatus).toLowerCase();
  return status === 'idle' && (terminalStatus === '' || terminalStatus === 'idle');
}

export function allKnownLanesInactive(lanes) {
  const known = ['agent', 'claude', 'codex'];
  const lanesById = Object.fromEntries((Array.isArray(lanes) ? lanes : [])
    .filter((lane) => isObject(lane) && text(lane.laneId))
    .map((lane) => [text(lane.laneId).toLowerCase(), lane]));
  return known.every((laneId) => {
    const lane = lanesById[laneId];
    if (!lane) return true;
    const status = text(lane.status).toLowerCase();
    return status === 'idle' || status === 'blocked' || status === 'needs_user' || status === 'unknown';
  });
}

export function classifyLocalBridgeSnapshot(snapshot, opts = {}) {
  const nowMs = Number.isFinite(opts.nowMs) ? opts.nowMs : Date.now();
  const maxAgeMs = Number.isFinite(opts.maxAgeMs) ? opts.maxAgeMs : DEFAULT_BRIDGE_FRESH_MS;
  if (!isObject(snapshot)) {
    return {
      fresh: false,
      reason: 'missing local bridge snapshot',
      recovery: 'run npm run terminal:auto -- --attach mcp-auto first',
    };
  }
  const generatedAt = text(snapshot.generatedAt);
  const generatedMs = Date.parse(generatedAt);
  if (!Number.isFinite(generatedMs)) {
    return {
      fresh: false,
      reason: 'local bridge snapshot has no valid generatedAt',
      recovery: 'run npm run terminal:auto -- --attach mcp-auto first',
    };
  }
  const ageMs = Math.max(0, nowMs - generatedMs);
  if (ageMs > maxAgeMs) {
    return {
      fresh: false,
      reason: `local bridge snapshot stale (${Math.round(ageMs / 1000)}s old; max ${Math.round(maxAgeMs / 1000)}s)`,
      recovery: 'run npm run terminal:auto -- --attach mcp-auto first',
      ageMs,
      generatedAt,
    };
  }
  return { fresh: true, reason: 'local bridge snapshot fresh', ageMs, generatedAt };
}

export function unsafePromptReason(promptText) {
  const body = text(promptText);
  if (!body) return 'prompt text is empty';
  for (const line of body.split('\n')) {
    if (NEGATION_LINE.test(line)) continue;
    for (const pattern of UNSAFE_PROMPT_PATTERNS) {
      const flags = pattern.flags.includes('g') ? pattern.flags : `${pattern.flags}g`;
      const matcher = new RegExp(pattern.source, flags);
      for (const match of line.matchAll(matcher)) {
        const prefix = line.slice(0, match.index ?? 0);
        const suffix = line.slice((match.index ?? 0) + match[0].length);
        if (/(^|[\s([{;:,-])(no|never|without|do not|don't)\s+(?:\S+\s+){0,4}$/i.test(prefix)) {
          continue;
        }
        if (/^build$/i.test(match[0]) && /(?:installed-|build[- ]graph|build[- ]state)$/i.test(prefix)) {
          continue;
        }
        if (/^release$/i.test(match[0]) && /^[-\s]*gate\b/i.test(suffix)) {
          continue;
        }
        return `prompt contains blocked term: ${pattern.source}`;
      }
    }
  }
  return null;
}

export function normalizeQueueItems(input) {
  const items = Array.isArray(input?.prompts)
    ? input.prompts
    : Array.isArray(input?.queue)
      ? input.queue
      : Array.isArray(input)
        ? input
        : [];

  return items
    .map((item) => {
      if (!isObject(item)) return null;
      const id = text(item.id);
      const targetLane = text(item.targetLane ?? item.targetWorker ?? item.targetWorkerOrPerson).toLowerCase();
      const promptText = text(item.promptText ?? item.prompt ?? item.actionText);
      const status = text(item.status || 'queued').toLowerCase();
      if (!id || !ALLOWED_LANES.has(targetLane) || !promptText) return null;
      return {
        id,
        targetLane,
        promptText,
        status,
        priority: text(item.priority || 'P2').toUpperCase(),
        approved: item.approved === true || item.dispatchApproved === true,
        publicSafe: item.publicSafe === true,
        createdAt: text(item.createdAt),
        dispatchedAt: text(item.dispatchedAt),
        consumedAt: text(item.consumedAt),
        source: text(item.source || 'local_queue') || 'local_queue',
      };
    })
    .filter((item) => item !== null);
}

export function eligibility(item, lanesById) {
  if (!item) return { eligible: false, reason: 'missing item' };
  if (item.dispatchedAt || item.consumedAt) return { eligible: false, reason: 'already dispatched' };
  if (!READY_STATUSES.has(item.status)) return { eligible: false, reason: `status ${item.status} is not dispatchable` };
  if (item.approved !== true) return { eligible: false, reason: 'not approved' };
  if (item.publicSafe !== true) return { eligible: false, reason: 'not public-safe' };
  const unsafe = unsafePromptReason(item.promptText);
  if (unsafe) return { eligible: false, reason: unsafe };
  const lane = lanesById?.[item.targetLane];
  if (!isLaneIdle(lane)) return { eligible: false, reason: `target lane ${item.targetLane} is not idle` };
  return { eligible: true, reason: 'eligible' };
}

function priorityScore(priority) {
  return PRIORITY_RANK.has(priority) ? PRIORITY_RANK.get(priority) : 99;
}

export function selectNextPrompt({ queueInput, lanes }) {
  const lanesById = Object.fromEntries((Array.isArray(lanes) ? lanes : [])
    .filter((lane) => isObject(lane) && text(lane.laneId))
    .map((lane) => [text(lane.laneId).toLowerCase(), lane]));
  const queue = normalizeQueueItems(queueInput);
  const decisions = queue.map((item) => ({ item, ...eligibility(item, lanesById) }));
  const eligible = decisions
    .filter((decision) => decision.eligible)
    .map((decision) => decision.item)
    .sort((a, b) => {
      const p = priorityScore(a.priority) - priorityScore(b.priority);
      if (p !== 0) return p;
      return a.createdAt.localeCompare(b.createdAt);
    });

  return {
    selected: eligible[0] ?? null,
    decisions,
  };
}

function laneFromAction(action) {
  const target = text(action?.targetWorkerOrPerson || action?.owner).toLowerCase();
  if (target.includes('codex')) return 'codex';
  if (target.includes('claude')) return 'claude';
  if (target.includes('agent')) return 'agent';
  return 'manual';
}

function priorityFromAction(action) {
  const p = text(action?.priority || 'P2').toUpperCase();
  return PRIORITY_RANK.has(p) ? p : 'P2';
}

function statusFromAction(action, lane, promptText) {
  const status = text(action?.status).toLowerCase();
  if (status === 'completed' || status === 'superseded' || status === 'void') return 'stale';
  if (lane === 'manual') return 'manual_required';
  if (status === 'blocked') return 'blocked';
  if (status && status !== 'pending') return status;
  if (unsafePromptReason(promptText)) return 'blocked_unsafe';
  return 'queued';
}

function promptForAction(action, lane) {
  const title = text(action?.lane || action?.id || 'Queued work');
  const actionText = text(action?.actionText);
  const trigger = text(action?.triggerCondition);
  const evidence = text(action?.evidenceSummaryOrLink);
  const target = lane === 'manual' ? 'Aaron' : lane.charAt(0).toUpperCase() + lane.slice(1);
  return `${target} lane - ${title}

MCP/action-ledger item: ${text(action?.id)}

Task:
${actionText}

Trigger/condition:
${trigger || 'No trigger supplied.'}

Context/evidence:
${evidence || 'No evidence summary supplied.'}

Non-negotiable rules:
- Repo-only until installed-device QA proves otherwise.
- No EAS/TestFlight/Play upload/release actions from automation.
- No credential, token, secret, or private worker text in logs or prompts.
- Do not claim installed-device QA is cleared unless evidence includes actual installed app version and device proof.
- Keep live-now, repo-only, preview-only, and installed-app verified claims clearly separated.

Stop conditions:
- Patch or audit only the smallest safe bundle.
- Run targeted tests/checks.
- Commit only related files.
- Write MCP-safe status; omit sensitive values.

Output only:
- Changed files:
- Commands run:
- Verification results:
- Commit:
- Live/repo status:
- Remaining blockers:
- Next action:`;
}

export function generatePromptQueueFromActionLedger(actionLedger, existingQueueInput = {}, opts = {}) {
  const generatedAt = text(opts.generatedAt) || nowIso();
  const existing = normalizeQueueItems(existingQueueInput);
  const existingById = new Map(existing.map((item) => [item.id, item]));
  const actions = Array.isArray(actionLedger?.pendingActions) ? actionLedger.pendingActions : [];
  const topPriority = Array.isArray(actionLedger?.currentPriorityOrder) ? actionLedger.currentPriorityOrder[0] : null;
  const prompts = actions.map((action) => {
    const baseId = `ledger-${text(action.id)}`;
    const previous = existingById.get(baseId);
    if (previous?.dispatchedAt || previous?.consumedAt) return previous;
    const lane = laneFromAction(action);
    const promptText = promptForAction(action, lane);
    const status = statusFromAction(action, lane, promptText);
    return {
      id: baseId,
      source: 'action_ledger',
      actionId: text(action.id),
      targetLane: lane,
      priority: priorityFromAction(action),
      status,
      approved: lane !== 'manual' && status === 'queued',
      publicSafe: true,
      createdAt: text(action.createdAt) || generatedAt,
      updatedAt: text(action.updatedAt) || generatedAt,
      summary: text(action.actionText).slice(0, 180),
      promptText,
      manualRequired: lane === 'manual',
      unsafeReason: unsafePromptReason(promptText),
    };
  });

  return {
    schemaVersion: 1,
    generatedAt,
    source: 'action_ledger',
    topPriority: topPriority
      ? {
          id: text(topPriority.id),
          title: text(topPriority.title),
          status: text(topPriority.status),
        }
      : null,
    prompts,
  };
}

export function markPromptDispatched(queueInput, selected, dispatchedAt = nowIso()) {
  if (!selected) return queueInput;
  const prompts = Array.isArray(queueInput?.prompts) ? queueInput.prompts : [];
  return {
    ...queueInput,
    updatedAt: dispatchedAt,
    prompts: prompts.map((item) => {
      if (item?.id !== selected.id) return item;
      return {
        ...item,
        status: 'dispatched',
        dispatchedAt,
        consumedAt: dispatchedAt,
      };
    }),
  };
}

export function buildDispatchEvent({ selected, dryRun, dispatched, reason, observedAt }) {
  return {
    schemaVersion: 1,
    observedAt,
    eventType: dryRun ? 'prompt_dispatch_dry_run' : 'prompt_dispatch',
    dispatched: dispatched === true,
    selected: selected
      ? {
          id: selected.id,
          targetLane: selected.targetLane,
          priority: selected.priority,
          source: selected.source,
        }
      : null,
    reason: text(reason),
  };
}
