/**
 * Pure helpers for prompt-dispatcher.mjs.
 *
 * The dispatcher is intentionally conservative: it only selects
 * explicitly approved, public-safe prompts, and refuses build /
 * upload / release-shaped work even when a queue row asks for it.
 */

const ALLOWED_LANES = new Set(['claude', 'codex']);
const READY_STATUSES = new Set(['queued', 'ready', 'approved']);
const PRIORITY_RANK = new Map([
  ['P0', 0],
  ['P1', 1],
  ['P2', 2],
  ['P3', 3],
]);

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

export function isLaneIdle(lane) {
  if (!isObject(lane)) return false;
  const status = text(lane.status).toLowerCase();
  const terminalStatus = text(lane.terminalStatus).toLowerCase();
  return status === 'idle' && (terminalStatus === '' || terminalStatus === 'idle');
}

export function unsafePromptReason(promptText) {
  const body = text(promptText);
  if (!body) return 'prompt text is empty';
  for (const line of body.split('\n')) {
    if (NEGATION_LINE.test(line)) continue;
    const hit = UNSAFE_PROMPT_PATTERNS.find((pattern) => pattern.test(line));
    if (hit) return `prompt contains blocked term: ${hit.source}`;
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
        source: text(item.source || 'local_queue') || 'local_queue',
      };
    })
    .filter((item) => item !== null);
}

export function eligibility(item, lanesById) {
  if (!item) return { eligible: false, reason: 'missing item' };
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
