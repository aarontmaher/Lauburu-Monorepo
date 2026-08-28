# Feedback + backlog priority model

Single sort order for everything in `docs/APP_DEVELOPMENTS.md`, the
in-app Quick capture, and the tester feedback queue. When two items
look "equally important", apply this ladder top-to-bottom; the
first rule that distinguishes them wins.

Updated 2026-05-05.

## Priority ladder (highest to lowest)

Updated 2026-05-06 to reflect the active product phase: **Apple
Health + Health Connect testing is the primary user lane.**
Health-source connection blockers move up two ranks; release
blockers stay #1 because nothing reaches testers without them.

1. **Tester auto-update / release blocker.**
   Anything that prevents a build from reaching testers (Play
   listing pass, EAS submit failure, signing/provisioning, store
   rejection). Without testers on current builds, every other
   improvement is invisible.
2. **Login / account blocker.**
   Sign-up, sign-in, password reset, Apple-Sign-In, account
   deletion. A locked-out user has no app at all.
3. **Apple Health / Android Health / Health Connect connection
   blocker.** PRIORITY ELEVATED — the current product phase is
   Aaron + girlfriend testing health-source flows on iPhone +
   Android. A primary platform health source that won't connect
   blocks the whole testing programme.
4. **Misleading health / readiness claim.**
   Surfacing a wearable as primary readiness when product truth
   is Lauburu/Grappler Readiness; showing synthetic data; over-
   stating data coverage; claiming a metric is fed when it's
   actually empty.
5. **Core mobile navigation blocker.**
   Tab bar broken, FAB unreachable, app crashes on launch, modal
   stuck.
6. **Feedback / screenshot upload broken.**
   If testers can't tell us what's wrong, every later issue
   becomes invisible. Ranks above general first-user confusion.
7. **Major first-user confusion.**
   First-launch UX failure: GuestBanner missing, tab order
   wrong, AppTour broken, "where do I sync?" not obvious.
8. **Repeated tester issue.**
   Same complaint from ≥2 testers in the feedback queue — even
   if individually low severity.
9. **Revenue / conversion blocker.**
   Paywall blocking a paid action, IAP failing, entitlements
   not syncing. Empty until paid AI / membership ships, but
   reserve the slot.
10. **Nice-to-have polish.**
    Spacing tweaks, copy edits, optional UX upgrades.
11. **Future feature / spec only.**
    Design docs, RFCs, "we should consider…". Lives in
    `docs/APP_DEVELOPMENTS.md` Next-top-5 or backlog files; does
    not enter active sprint until promoted.

## Project-phase weighting (2026-05-06)

The ladder is universal; today's project phase adds these
specific rankings on top:

- **Apple Health / Android Health / Health Connect issues** rank
  ABOVE WHOOP, Polar, nutrition, DEXA / blood test uploads, paid
  API AI, Shopify / payments, and local Mac/tmux bridge polish.
- **WHOOP / Polar direct-sync issues** rank below the primary
  health sources but above feature ideas.
- **Raw export uploads** (WHOOP CSV, Polar export) are
  historical-backfill convenience — rank polish-tier unless
  broken in a way that crashes the app.

## Status labels

Apply one (or more — they compose) to every backlog item so
its state is unambiguous across Apple Notes, Quick capture, and
the in-app Backlog card.

- **`live bug`** — reproducible on a tester device today. Highest
  urgency at any priority level.
- **`repo-only`** — fix is on `main` but no build has shipped.
  Will land in next paired build; do NOT dispatch a one-off.
- **`tester-only`** — affects internal testers only (e.g. dev
  unlock, owner FAB). Do NOT prioritise above any user-visible
  blocker.
- **`future feature`** — spec only, not yet started. Belongs in
  priority 10.
- **`do not build yet`** — actively gated. The reason must be
  named (e.g. "gated on Grappler Readiness Batch B").
- **`needs data first`** — feature requires a metric we don't
  capture yet (e.g. perceived intensity slider).
- **`needs monetisation first`** — feature is paid-AI dependent;
  blocked by `AI_MONETISATION_AND_USAGE_STRATEGY.md` triggers.
- **`blocked by user-only step`** — only Aaron can unblock it
  (Play Console listing pass, App Store screenshots, etc.).
- **`blocked by secret`** — needs a token / key configured
  somewhere (Railway env, GitHub Actions secret, EAS env).
- **`blocked by store setup`** — Play Console field, App Store
  Connect declaration, App Tracking Transparency etc.

A single item can carry several labels — e.g. "Android
auto-promote" today is `repo-only` + `blocked by store setup`
+ `blocked by user-only step`.

## Status enum (extends backlog store)

Used by `apps/mobile/src/store/owner-backlog-store.ts` and the
future connector tools. Extended set (from
`docs/CONNECTOR_BACKLOG_TOOLS_PLAN.md`):

- `new` — incoming, untriaged. Connector- and tester-created
  items default here with `needsReview: true`.
- `triaged` — owner has read it; not yet accepted into work.
- `accepted` — owner has decided to work on it.
- `in_progress` — being implemented now.
- `repo_only` — done in code but not yet on a tester device.
- `built` — packaged into an EAS build but not yet promoted.
- `tester_live` — installed on at least one tester device.
- `done` — verified or otherwise closed.
- `blocked` — needs `blocker` field populated.
- `do_not_build_yet` — explicitly deferred.
- `archived` — terminal-after-`done`. Owner-only transition; the
  connector cannot move items to `archived`.

## How the in-app Quick capture maps to this

The owner-only Quick capture stores items locally with:

- `type` (bug / ux / feature / release_blocker / health_data /
  ai_coaching / monetisation)
- `platform` (android / ios / both)
- `priority` (1–10, this ladder)
- `status` labels (above)
- `source = 'owner'` (distinguishes from tester feedback)
- `createdAt`

When backend support for owner backlog lands (separate batch),
the same shape is what the route accepts — no migration needed.

## How tester feedback maps to this

Tester feedback already carries `severity` (low / medium /
high / blocking) and `type`. When triaging, map:

- severity blocking → priority 1–4 depending on type.
- severity high → priority 4–7.
- severity medium → priority 7–9.
- severity low → priority 9–10.

Severity is the tester's read; priority is Aaron's. They don't
have to match — a tester marking something `blocking` doesn't
guarantee it lands at the top of the ladder.

## Anti-rules

- **Do not order by recency.** A new request does not jump the
  ladder by virtue of being new.
- **Do not order by tester volume alone.** "Five testers asked
  for X" is rule 7 — repeated tester issue — but does not beat
  rules 1–6.
- **Do not order by Aaron's enthusiasm.** Excitement about a
  feature lives in priority 10 until rules 1–9 are clear.
- **Do not silently demote a `live bug`.** A live bug stays at
  its priority until fixed; reclassifying it as "polish"
  requires evidence the impact was overestimated.
