/**
 * Pure helpers for queue classification + owner routing.
 *
 * Per docs/QUEUE_TAXONOMY_SPEC.md — three durable queues
 * plus the existing overnight queue. Classifier picks the
 * right queue_kind from a queue item's title (+ optional
 * hints). Router maps queue_kind → suggested lane_owner.
 *
 * Pure functions; no I/O. Worker-side and laptop-side both
 * import from here so they classify identically.
 */

export const QUEUE_KINDS = Object.freeze([
  'automation_workflow',
  'app_functionality',
  'app_ux_ui',
  'overnight',
]);

export const LANE_OWNERS = Object.freeze(['claude', 'codex', 'agent', 'aaron']);

const OWNER_BY_KIND = Object.freeze({
  automation_workflow: 'claude',
  app_functionality: 'codex',
  app_ux_ui: 'agent',
  overnight: null, // any owner; rest of system decides
});

const EXPLICIT_TAGS = Object.freeze({
  '[automation]': 'automation_workflow',
  '[functionality]': 'app_functionality',
  '[ux]': 'app_ux_ui',
  '[overnight]': 'overnight',
});

const AUTOMATION_KEYWORDS = [
  'mcp', 'freshness', 'writeback', 'watcher', 'push', 'approval',
  'gate', 'lane', 'idle', 'admin/dev', 'admin-dev', 'deploy',
  'bridge', 'snapshot', 'audit-bundle', 'audit bundle',
  'control-centre', 'control centre', 'no-idle', 'staleReason',
  'heartbeat',
];

const UX_KEYWORDS = [
  'dark theme', 'premium', 'palette', 'primitive', 'copy',
  'hedge', 'anti-claim', 'contrast', 'padding', 'layout',
  'redesign', 'polish', 'accessibility', 'screen-record-only',
  'visual', 'spacing', 'typography', 'icon', 'a11y',
];

const FUNCTIONALITY_KEYWORDS = [
  'journal', 'parser', 'health connect', 'apple health',
  'training', 'map', 'syllabus', 'drill', 'technique',
  'mastery', 'video analysis', 'coach', 'fs-018', 'fs-020',
  'fs-021', 'fs-022', 'readiness', 'whoop', 'polar',
  'cronometer', 'maestro flow',
];

const OVERNIGHT_KEYWORDS = [
  'overnight', 'unattended', 'long-running', 'long running',
  'batch', '8-hour-build', 'cron',
];

function findFirstTag(s) {
  if (typeof s !== 'string') return null;
  const lower = s.toLowerCase();
  for (const [tag, kind] of Object.entries(EXPLICIT_TAGS)) {
    if (lower.includes(tag)) return kind;
  }
  return null;
}

function matchAny(s, keywords) {
  if (typeof s !== 'string' || s.length === 0) return false;
  const lower = s.toLowerCase();
  return keywords.some((k) => lower.includes(k));
}

/**
 * Classify a queue item's title (and optional hints) into
 * one of the four queue_kinds.
 *
 * @param {string} title — short title; ≤140 chars typical.
 * @param {object} [opts] — { laneHint?: 'automation_workflow'|'app_functionality'|'app_ux_ui'|'overnight' }
 * @returns {{ queue_kind: string, lane_owner: string|null, unclassified: boolean, matchedRule: string }}
 */
export function classifyQueueItem(title, opts = {}) {
  // 0. Programmatic lane hint (caller already knows).
  if (opts.laneHint && QUEUE_KINDS.includes(opts.laneHint)) {
    return {
      queue_kind: opts.laneHint,
      lane_owner: OWNER_BY_KIND[opts.laneHint],
      unclassified: false,
      matchedRule: 'lane_hint',
    };
  }

  // 1. Explicit tag wins.
  const tagKind = findFirstTag(title);
  if (tagKind) {
    return {
      queue_kind: tagKind,
      lane_owner: OWNER_BY_KIND[tagKind],
      unclassified: false,
      matchedRule: 'explicit_tag',
    };
  }

  // 2. Automation Workflow keywords.
  if (matchAny(title, AUTOMATION_KEYWORDS)) {
    return {
      queue_kind: 'automation_workflow',
      lane_owner: OWNER_BY_KIND.automation_workflow,
      unclassified: false,
      matchedRule: 'automation_keyword',
    };
  }

  // 3. App UX/UI keywords.
  if (matchAny(title, UX_KEYWORDS)) {
    return {
      queue_kind: 'app_ux_ui',
      lane_owner: OWNER_BY_KIND.app_ux_ui,
      unclassified: false,
      matchedRule: 'ux_keyword',
    };
  }

  // 4. App Functionality keywords.
  if (matchAny(title, FUNCTIONALITY_KEYWORDS)) {
    return {
      queue_kind: 'app_functionality',
      lane_owner: OWNER_BY_KIND.app_functionality,
      unclassified: false,
      matchedRule: 'functionality_keyword',
    };
  }

  // 5. Overnight keywords.
  if (matchAny(title, OVERNIGHT_KEYWORDS)) {
    return {
      queue_kind: 'overnight',
      lane_owner: null,
      unclassified: false,
      matchedRule: 'overnight_keyword',
    };
  }

  // 6. Fallback — Claude's lane (automation_workflow), flagged
  // for re-classification.
  return {
    queue_kind: 'automation_workflow',
    lane_owner: OWNER_BY_KIND.automation_workflow,
    unclassified: true,
    matchedRule: 'fallback',
  };
}

/**
 * Decide if a queue item recommendation should be surfaced to
 * an idle lane.
 *
 * Per docs/QUEUE_TAXONOMY_SPEC.md § 5 P0 protection: queue
 * items NEVER override active P0 blockers or P1 work. The
 * caller must pass the active blockers + active priorities
 * so this function can reason about them.
 *
 * @param {object} item — { queue_kind, lane_owner, priority, status, dependencies? }
 * @param {object} state — { activeP0Blocker?: object|null, activeP1Items?: object[], laneIdle?: boolean }
 * @returns {{ recommend: boolean, reason: string }}
 */
export function shouldRecommendToIdleLane(item, state = {}) {
  if (!item || typeof item !== 'object') {
    return { recommend: false, reason: 'no item' };
  }
  if (state.activeP0Blocker) {
    return {
      recommend: false,
      reason: 'P0 blocker active — queue items never override P0',
    };
  }
  if (Array.isArray(state.activeP1Items) && state.activeP1Items.length > 0) {
    return {
      recommend: false,
      reason: `${state.activeP1Items.length} P1 item(s) active — queue items defer to P1`,
    };
  }
  if (state.laneIdle === false) {
    return { recommend: false, reason: 'target lane is not idle' };
  }
  if (item.status !== 'prioritized' && item.status !== 'in_progress') {
    return {
      recommend: false,
      reason: `item.status=${item.status} — only prioritized / in_progress items are recommended`,
    };
  }
  if (item.priority === 'overnight_only' && state.isOvernightWindow !== true) {
    return {
      recommend: false,
      reason: 'overnight_only item outside overnight window',
    };
  }
  return {
    recommend: true,
    reason: 'no blocker / no P1 / lane idle / item ready — recommend',
  };
}

/**
 * Compute stale_age_hours threshold per queue_kind.
 * Per docs/QUEUE_TAXONOMY_SPEC.md § 4.
 */
export function staleThresholdHours(queueKind) {
  switch (queueKind) {
    case 'automation_workflow': return 72;
    case 'app_functionality': return 168;
    case 'app_ux_ui': return 168;
    case 'overnight': return 24;
    default: return 168;
  }
}

/**
 * Decide whether an item should be flagged stale based on
 * its last-update timestamp + queue kind.
 */
export function isItemStale({ queue_kind, lastUpdatedAt, now = Date.now() }) {
  if (!lastUpdatedAt) return true;
  const ageHours = (now - new Date(lastUpdatedAt).getTime()) / 3_600_000;
  return ageHours > staleThresholdHours(queue_kind);
}
