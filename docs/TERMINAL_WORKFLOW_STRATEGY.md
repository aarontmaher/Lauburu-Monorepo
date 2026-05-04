# Terminal workflow strategy

How the in-app Admin/Dev workflow relates to Aaron's existing
laptop terminal + Termius/tmux setup. The short answer: **the app
does not embed a terminal.** It triggers safe predefined workflows,
shows their status, and links out to the dashboards that already
exist. Termius/tmux remain the manual fallback.

Updated 2026-05-05.

## Why no embedded terminal

Embedding a raw shell or SSH client in the app would be the fastest
way to break every other guarantee in this codebase. Specifically:

1. **Security.** A raw shell is by definition arbitrary command
   execution. Any path that lets the app run unbounded commands
   becomes a compromise vector — phone theft, OS-level malware,
   shoulder-surf during a demo. The current model — workflow
   dispatch behind a signed backend proxy — has a fixed allowlist.
   That property is load-bearing.
2. **App Store / Play Store review risk.** Both stores have
   rejected apps for "code execution" surfaces, even when they
   were owner-only. An app whose review status is "approved" is
   worth far more than one that ships a terminal.
3. **Accidental destructive commands.** A typo on mobile is more
   likely than on a laptop (autocorrect, fat-finger, no `Tab`
   completion). `rm -rf`, `git push --force`, `supabase db push`
   are one slip away. The dispatch model can't even express most
   of those.
4. **Mobile UX.** A real terminal needs a real keyboard. Soft-
   keyboard escape sequences are awful. Termius already does this
   better; we don't need to compete.
5. **Auditing.** Workflow dispatches show up in GitHub Actions
   history with an actor. Raw shell commands don't.

## What the app does instead

| Need | App approach | Fallback |
|---|---|---|
| Run typecheck | `mobile-typecheck.yml` workflow_dispatch button | `npm run typecheck` in Termius |
| Build/upload Android | `android-aab-build.yml` button (with `submit_to_play=true`) | `eas build` from laptop |
| Build/submit iOS | `ios-testflight-build.yml` button (with `submit_to_testflight=true`) | `eas build` + `eas submit` from laptop |
| Backend smoke | `backend-smoke.yml` button | `curl` from any device |
| Release audit | `release-audit.yml` button | manual checklist |
| Read live logs | external dashboard links (GitHub Actions, Railway, Expo) | direct browser bookmarks |
| Read DB | NOT available in-app | Supabase dashboard in Chrome |
| Run arbitrary SQL | NOT available in-app | Supabase SQL editor in Chrome |
| Run arbitrary git command | NOT available in-app | Termius |

If the need isn't on the left column, it stays a Termius/Chrome
job. The ladder is: in-app first → Chrome dashboard second →
Termius last.

## Termius deep-link strategy

The Admin/Dev "Open shortcuts" section ships an "Open Termius"
button that calls `Linking.openURL('termius://')`. Termius accepts
the bare scheme to launch the app — it does NOT accept arbitrary
SSH commands via the URL, and it does not accept a host/port to
auto-connect via deep link. (This is intentional on Termius's side
and is the right design.) The app's responsibility ends at "bring
Termius to the foreground". From there, Aaron taps his existing
saved host and the tmux startup snippet (configured per-host inside
Termius itself) attaches to the right session.

Fallback chain when `termius://` is not supported:

1. Linking.canOpenURL returns false → show an Alert pointing to the
   App Store / Play Store install path.
2. Show a "Copy tmux attach instructions" disclosure that surfaces
   the standard `tmux attach || tmux new -s lauburu` snippet for
   long-press copy. No SSH credentials, no host names, no ports.
3. The user can also use the existing "Copy terminal check prompt"
   in the Prompt bridge — same effect from any terminal client.

What the app deliberately does NOT do:

- Store SSH host names, ports, usernames, passwords, or keys.
- Render any SSH credential.
- Embed an SSH client.
- Accept raw command input.
- Trigger a "send tmux command via deep link" — Termius doesn't
  expose this and we wouldn't use it if it did.

## Termius / tmux as emergency fallback

Aaron's existing Termius/tmux setup remains intact. It is the
correct tool for:

- Recovering from a bad `git` state (rebase conflicts, accidental
  merge commits, force-push undos).
- Editing files on the fly when Claude Code is offline.
- Running commands that genuinely need a shell (Supabase psql,
  jq pipelines, ad-hoc curl with custom headers).
- Tail-following Railway / Expo logs when the dashboard is slow.

The app is not designed to replace any of this. It's designed to
remove the **routine** terminal trips — typecheck, build, submit,
status — so Termius is reserved for the cases that actually need
it.

## Future: advanced owner-only SSH bridge

Tempting but deferred. If we ever do this, the gates are:

1. **Explicit security review.** Threat model written, attack
   surface enumerated, approved by Aaron in writing (not a chat
   message — a doc commit).
2. **Hard allowlist of commands.** No raw shell. The app sends
   command names from a fixed list; the bridge maps them to
   parameterised invocations. Same shape as the workflow dispatch.
3. **Per-command audit log.** Every command invocation logged to
   a dashboard Aaron can review.
4. **Owner-account-only and biometric-gated.** Even with the
   admin email + dev unlock, the SSH bridge would also require
   FaceID/TouchID at moment of invocation.
5. **Off by default.** Feature flag, defaults off. Documented
   how to disable from a separate device if the phone is lost.

Until all five exist, no SSH bridge.

## What "show workflow logs" looks like in-app

Out of scope for this batch but called out so the spec is clear:
the app can read `GET /repos/:owner/:repo/actions/runs/:id` via
the same backend proxy that handles dispatch, and render the run
status + the URL to the live log on github.com. It does NOT stream
the raw log in-app — too large, too sensitive (env values can
appear in logs even when redacted), and the in-browser view is
already excellent. "View on GitHub" link is the right surface.

## Decision summary

The app is a **structured remote control for predefined workflows
and a context fetcher for status**. It is not a terminal, and is
not trying to be one. Termius/tmux/Chrome continue to handle the
long tail. This split is the right one for safety, store review,
and mobile UX — and it lets the app scale to non-Aaron owners
later without rethinking the security model.
