# No-API owner workflow

What the in-app Admin/Dev surface can and can't do without paid LLM
API access. Read this before adding any feature that assumes Claude
or ChatGPT will reason over input from inside the app.

Updated 2026-05-05.

## Principle

Build the no-API workflow first. Paid LLM access is gated until the
data, monetisation, and usage caps designed in
`AI_PROVIDER_STRATEGY.md` and `AI_MONETISATION_AND_USAGE_STRATEGY.md`
are real. Until then, the app is a **structured workflow runner +
status surface + clipboard bridge** — not a coach for Aaron.

## Template-based prompt generation

The Admin/Dev Prompt bridge generates Claude Code, Claude Chrome,
ChatGPT status, Codex, and terminal-check prompts deterministically
from a structured `OwnerWorkflowContext`:

- `currentPriority` / `currentBlocker` / `lastStatus`
- `selectedTaskBundle` (free text Aaron types)
- `protectedRules` (the standing do-not-touch list)
- `manualStepsForAaron` / `canDeleteFromNotepad` /
  `doNotDeleteYet`

No model is involved. Each builder is pure string composition over
the context. Implemented in
`apps/mobile/src/services/prompt-templates.ts`; the context is
served by `apps/mobile/src/store/owner-workflow-store.ts` (today
hard-coded; later wired to a backend route or to a future Admin/Dev
edit form, without changing the builder signatures).

The builders bake the standing non-negotiables into every prompt
so Aaron doesn't have to re-state them — every generated prompt is
self-contained and safe to paste cold into the chosen runner.

Every generated prompt also starts with the MCP-first operating
rule. The runner must check, in order: `get_work_status`,
`list_pending_suggestions`, `get_automation_state`, `get_handoff`,
and `/api/control_centre` if available. The runner must report MCP
state, freshness/staleness, chosen next task, and whether fallback
terminal / control-centre state was needed before doing work.

The same operating block carries the build and workflow guardrails:
keep coder lanes parallel and non-overlapping; use
`Implementation-complete, awaiting Agent functional confirmation`
until Agent confirms; do not call work fully complete until Aaron
has tested or approved it; and do not run EAS builds unless Agent
has confirmed a worthwhile on-device change and Aaron approves.
It also carries the clear-steps / automate-first rule: if a worker
needs Aaron, it must first give exact step-by-step instructions,
automate every safe part, and use Claude / Codex / Agent before
asking Aaron. Outputs must split follow-up into `automated by
coder/agent`, `manual Aaron step`, and `blocked until Aaron acts`.
Aaron should only handle secrets, approvals, logins, 2FA, vendor
dashboards, and safety-sensitive confirmations.

Every generated prompt that mentions build, tester-build,
TestFlight, Play Internal Testing, or EAS work must include this
sentence verbatim: "Do not run EAS builds unless Agent has confirmed a worthwhile on-device change and Aaron approves."
Prompts may say implementation is complete when code is committed,
typecheck/tests pass, no obvious blockers remain, and expected
behaviour is described, but they must use the status
`Implementation-complete, awaiting Agent functional confirmation`
until Agent has completed a functional audit. Do not call mobile
work `fully complete` until Aaron has tested or approved it.

When paid LLM access lands, this layer does NOT change. A future
runner-specific endpoint may auto-summarise recent work into the
`selectedTaskBundle` field; the builder shape stays identical.

## What works without any paid API

These are all live (or will be in the next paired build):

- **Trigger predefined GitHub Actions workflows** through the signed
  backend dispatch endpoint. No API charge — GitHub Actions runner
  minutes are billed separately and orthogonal to LLM cost.
- **Show workflow / build / submit status** by polling the same
  backend dispatch endpoint and the existing `/admin/status` route.
- **Open external dashboards** (Play Console, App Store Connect,
  GitHub Actions, Expo, Railway). Just `Linking.openURL`.
- **Copy structured prompts to the clipboard** for pasting into
  ChatGPT, Claude Code, or another LLM the user already pays for.
  The app produces the prompt; the user runs it elsewhere.
- **Capture owner backlog locally** through the Quick capture form.
  Stored in the same secure-storage zustand pattern other stores
  use; survives restarts; never leaves the device.
- **Read normalised health metrics, trends, and readiness output**
  from cached artifacts. All deterministic — `Lauburu Readiness`
  and `Grappler Readiness` compute on-device-side data already
  pushed to the backend through existing routes.
- **Show structured Coach answers** templated from those artifacts.
  No LLM narrative paragraph yet; the deterministic answer is the
  baseline and remains the free-tier output even after paid LLM
  ships.

## What does NOT work without paid API

These are deliberately not in this batch:

- **Reading the user's live ChatGPT or Claude conversation.** No
  vendor exposes a "let an external app read what I'm currently
  typing" API. Even if they did, that would be a privacy nightmare.
- **Typing into Aaron's Claude Code terminal.** The terminal is on
  his laptop; the app is on his phone. Bridging them would need an
  SSH bridge (see `TERMINAL_WORKFLOW_STRATEGY.md` — gated on five
  prerequisites). Workflow dispatch is the safe replacement.
- **Reasoning over screenshots / Apple Notes automatically.** No
  vision or text reasoning is wired. Aaron drives the reasoning by
  pasting context into ChatGPT himself.
- **Running arbitrary terminal commands.** Out of scope by the same
  decision recorded in `TERMINAL_WORKFLOW_STRATEGY.md`.
- **Drafting a "next prompt" intelligently.** Today the prompt
  bridge ships fixed prompts that Aaron can copy. A future
  iteration could fill in the prompt with current state — but that
  requires LLM + monetisation gates first.
- **Live AI-generated coach narrative.** Same gate — design only in
  `AI_PROVIDER_STRATEGY.md`, no implementation yet.

## Ladder for "do I need paid API for this?"

Before adding any feature that touches Claude/ChatGPT/Gemini, walk
this ladder. If a higher rung satisfies the need, do that instead.

1. **Can deterministic compute do it?** Use the existing artifacts
   pipeline (multi-window trends, readiness, source breakdown).
2. **Can a fixed prompt the user copies elsewhere do it?** Add it
   to the prompt bridge.
3. **Can a dispatched workflow do it?** Add a new safe workflow
   under `.github/workflows/` and a button.
4. **Does it genuinely require live LLM reasoning over private app
   data?** Then it is gated on paid API + monetisation rollout.
   Document the requirement; do NOT implement.

The shape of "this needs paid API" is rarer than it looks. Most
"AI" use cases on the laptop today are actually rung 1–3.

## Anti-rules

- **Do not stub a fake LLM response** that resolves out of
  hard-coded text. Either it's deterministic (then label it as
  such) or it's not implemented yet.
- **Do not add per-user usage tracking for unbilled features.**
  Tracking exists when there's something to bill. Until then,
  workflow dispatches are server-logged, end of story.
- **Do not promise the user "AI will help"** in copy that ships in
  the no-API mode. The deterministic Coach is the product today.
- **Do not log prompts that contain user health data even at the
  no-API stage.** The prompt bridge ships fixed prompts that
  contain no user data; that's fine. If a future prompt bridge
  template starts including user data, it must follow the logging
  rules in `AI_PROVIDER_STRATEGY.md` from day one.

## When the no-API mode ends

The no-API foundation persists indefinitely as the **free tier**
(`docs/AI_MONETISATION_AND_USAGE_STRATEGY.md`). Paid AI is added on
top, never replacing it. The free tier remains genuinely useful
even when paid AI is live; that's a non-negotiable from the
monetisation doc.

When paid AI lands, this document gets a §"Paid AI mode" appendix
listing what changed; the rest stays as-is.
