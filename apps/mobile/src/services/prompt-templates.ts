/**
 * Deterministic owner-workflow prompt templates.
 *
 * NO paid AI API. NO model call. Pure string composition over the
 * structured `OwnerWorkflowContext` so Aaron can copy a ready-to-
 * paste prompt for whichever runner he's on (Claude Code, Claude
 * via Chrome, ChatGPT, Codex, or a quick terminal check).
 *
 * Templates intentionally bake in the standing non-negotiables
 * (do-not-touch list) so Aaron doesn't have to re-state them every
 * lane — every generated prompt is self-contained and safe to paste
 * cold.
 *
 * When the no-API mode ends and paid AI is wired, a future
 * iteration may auto-fill the "selected task bundle" section by
 * summarising recent work; the function shape stays the same.
 */

export interface OwnerWorkflowContext {
  /** Single most-important thing right now — short. */
  currentPriority: string;
  /** What is preventing progress on the priority — short. */
  currentBlocker: string;
  /** Last CHATGPT_STATUS_END block (or short summary). */
  lastStatus: string;
  /** Optional task bundle the user is about to dispatch. */
  selectedTaskBundle?: string;
  /** Repo paths / behaviours that must NOT be touched. */
  protectedRules: string[];
  /** Steps only Aaron can do (Play Console, App Store screenshots, etc.). */
  manualStepsForAaron: string[];
  /** Items safe to remove from Apple Notes. */
  canDeleteFromNotepad: string[];
  /** Items still load-bearing in Apple Notes. */
  doNotDeleteYet: string[];
}

/** Small helper — prefix bullet lines with `- ` if missing. */
function bulletise(items: string[]): string {
  if (items.length === 0) return '(none)';
  return items.map((line) => (line.trim().startsWith('-') ? line : `- ${line}`)).join('\n');
}

function header(promptType: string, lane: string): string {
  const idStamp = new Date().toISOString().replace(/[-:.]/g, '').slice(0, 13);
  return [
    `PROMPT-ID: OWNER-${promptType.toUpperCase()}-${idStamp}`,
    `TYPE: ${promptType}`,
    `LANE: ${lane}`,
  ].join('\n');
}

const STANDING_RULES_FALLBACK = [
  'grappling.opml — never edit',
  'No secrets or tokens in output',
  'No Supabase db push',
  'No SDK upgrade',
  'No OTA',
  'No paid AI API implementation yet',
  'No arbitrary shell execution',
];

function rules(ctx: OwnerWorkflowContext): string {
  const merged = ctx.protectedRules.length > 0 ? ctx.protectedRules : STANDING_RULES_FALLBACK;
  return bulletise(merged);
}

/** Claude Code (terminal CLI) — full implementation prompt. */
export function buildClaudeCodePrompt(ctx: OwnerWorkflowContext): string {
  return [
    header('CLAUDE-CODE', ctx.selectedTaskBundle ?? 'Mobile owner workflow'),
    '',
    'CURRENT PRIORITY',
    ctx.currentPriority || '(set in Admin/Dev → Now)',
    '',
    'CURRENT BLOCKER',
    ctx.currentBlocker || '(set in Admin/Dev → Now)',
    '',
    'LAST STATUS',
    ctx.lastStatus || '(no prior status block recorded)',
    '',
    'PROTECTED — DO NOT TOUCH',
    rules(ctx),
    '',
    'MANUAL FOR AARON — do not re-do',
    bulletise(ctx.manualStepsForAaron),
    '',
    'CAN DELETE FROM NOTEPAD',
    bulletise(ctx.canDeleteFromNotepad),
    '',
    'DO NOT DELETE YET',
    bulletise(ctx.doNotDeleteYet),
    '',
    'TASK',
    ctx.selectedTaskBundle
      ? `Continue the lane: ${ctx.selectedTaskBundle}.`
      : '(describe the lane in one or two short paragraphs)',
    '',
    'OUTPUT',
    'End with a CHATGPT_STATUS_START / CHATGPT_STATUS_END block covering: live / repo-only / blocked / verified / next.',
  ].join('\n');
}

/**
 * Claude via Chrome (Claude.ai web). Different from Claude Code:
 * the model has no shell, so the prompt asks for review/design
 * rather than file edits. Useful for second opinions on
 * architecture or copy review.
 */
export function buildClaudeChromePrompt(ctx: OwnerWorkflowContext): string {
  return [
    header('CLAUDE-CHROME', ctx.selectedTaskBundle ?? 'Owner workflow review'),
    '',
    `CURRENT PRIORITY: ${ctx.currentPriority || '(unset)'}`,
    `CURRENT BLOCKER: ${ctx.currentBlocker || '(unset)'}`,
    '',
    'LAST STATUS:',
    ctx.lastStatus || '(no prior status block)',
    '',
    'You do not have shell access. Do NOT propose code edits as patches; propose them as a numbered plan.',
    '',
    'STANDING RULES — bake into every recommendation:',
    rules(ctx),
    '',
    'MANUAL FOR AARON (do not duplicate as code work):',
    bulletise(ctx.manualStepsForAaron),
    '',
    'TASK',
    ctx.selectedTaskBundle
      ? `Review and propose the next reviewable batch for: ${ctx.selectedTaskBundle}.`
      : '(describe the review lane)',
    '',
    'OUTPUT',
    'A numbered plan with files affected, plus a one-paragraph summary suitable for pasting into ChatGPT or back into Claude Code.',
  ].join('\n');
}

/** ChatGPT — status / check / strategy lane. */
export function buildChatGPTStatusPrompt(ctx: OwnerWorkflowContext): string {
  return [
    header('CHATGPT-STATUS', ctx.selectedTaskBundle ?? 'Owner status check'),
    '',
    `CURRENT PRIORITY: ${ctx.currentPriority || '(unset)'}`,
    `CURRENT BLOCKER: ${ctx.currentBlocker || '(unset)'}`,
    '',
    'LAST STATUS:',
    ctx.lastStatus || '(none)',
    '',
    'TASK',
    'Triage what should be the next Claude Code lane. Account for the standing rules below; if a proposed lane violates one, drop it.',
    '',
    'STANDING RULES:',
    rules(ctx),
    '',
    'MANUAL FOR AARON — already done or queued:',
    bulletise(ctx.manualStepsForAaron),
    '',
    'OUTPUT',
    'A single CHATGPT_STATUS_START / CHATGPT_STATUS_END block summarising the current lane and proposing the next one. Keep it under 25 lines.',
  ].join('\n');
}

/** Codex / OpenAI coding agent — implementation prompt. */
export function buildCodexPrompt(ctx: OwnerWorkflowContext): string {
  return [
    header('CODEX', ctx.selectedTaskBundle ?? 'Owner workflow code lane'),
    '',
    `Repo root: ~/LauburuGrapplingMap-mobile (mobile-first, Expo SDK 54, TypeScript).`,
    '',
    'CURRENT PRIORITY:',
    ctx.currentPriority || '(unset)',
    '',
    'CURRENT BLOCKER:',
    ctx.currentBlocker || '(unset)',
    '',
    'STANDING RULES — every patch must respect these:',
    rules(ctx),
    '',
    'MANUAL FOR AARON — do NOT add code that re-does these:',
    bulletise(ctx.manualStepsForAaron),
    '',
    'TASK',
    ctx.selectedTaskBundle
      ? `Implement: ${ctx.selectedTaskBundle}.`
      : '(describe the implementation lane)',
    '',
    'CONSTRAINTS',
    '- Output a small reviewable diff, not a rewrite.',
    '- Run `cd apps/mobile && npx tsc --noEmit` before reporting done.',
    '- Do NOT install new native modules without a config-plugin note.',
    '',
    'OUTPUT',
    'Diff, plus a one-paragraph summary and a CHATGPT_STATUS block.',
  ].join('\n');
}

/** Quick terminal check — short paste-into-Claude-Code prompt. */
export function buildTerminalCheckPrompt(ctx: OwnerWorkflowContext): string {
  return [
    'Quick terminal check — paste into Claude Code on the laptop:',
    '',
    '1. cd ~/LauburuGrapplingMap-mobile',
    '2. git status --short && git log --oneline -5',
    '3. cd apps/mobile && npx tsc --noEmit',
    '4. Report: any uncommitted files, any tsc errors, what was the last commit, and whether HEAD matches origin/main.',
    '',
    'Standing rules (do NOT violate):',
    rules(ctx),
    '',
    `Lane: ${ctx.selectedTaskBundle ?? '(none — diagnostic only)'}`,
  ].join('\n');
}

/**
 * tmux attach instructions — for when Aaron is moving from phone
 * to laptop and wants to drop into the same tmux session his
 * Claude Code is running in. No SSH credentials are stored or
 * displayed; this is a copy-paste hint, not a command runner.
 */
export function buildTmuxAttachInstructions(): string {
  return [
    'tmux attach (paste into your existing terminal — Termius, iTerm, etc.):',
    '',
    '  tmux attach -t lauburu',
    '',
    'Read-only attach (watch without typing — useful when Aaron is already',
    'driving the session and the phone is just observing):',
    '',
    '  tmux attach -r -t lauburu',
    '',
    'Create the named session if it does not exist yet:',
    '',
    '  tmux new -s lauburu',
    '',
    'List existing sessions:',
    '',
    '  tmux ls',
    '',
    'Termius can run any of the above on first connect via the host\'s',
    '"Startup snippet" setting — configure once per host in Termius itself,',
    'not in this app. No SSH credentials are stored in or sent through this',
    'app.',
  ].join('\n');
}
