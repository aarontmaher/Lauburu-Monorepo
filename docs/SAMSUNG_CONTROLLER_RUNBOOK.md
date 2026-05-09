# Samsung phone Admin/Dev controller — runbook

Owner-only runbook for using the installed Lauburu Android build on a
Samsung-class phone as the day-to-day automatic controller for
Claude / Codex / Agent / MCP automation loops.

## Scope and honesty rules

- **Repo-only by default.** Every controller surface is labelled
  `repo-only` until an installed build is confirmed running the
  matching `versionCode`. The Build state separation card in
  Admin/Dev is the source of truth — `installed-build verified`
  appears only when the installed `versionCode` matches the
  patched target.
- **No release actions.** The controller never triggers an EAS
  build, a TestFlight submit, a Play upload, or a worker deploy.
  The buttons surface intent only (copy commands, open approvals,
  view evidence).
- **Mirror evidence cannot clear installed-device gates.**
  Screenshots and `scrcpy` recordings find bugs but cannot promote
  the audit gate to `installed-build verified`. The runbook below
  always finishes on the installed phone.

## Controller home tiles

The Samsung controller home is a phone-first compact dashboard
inside Admin/Dev. It renders only when the signed-in user is the
admin and `Platform.OS === 'android'`. Tiles:

| Tile | Source | Evidence label |
|---|---|---|
| MCP freshness pill | `project.get_current_state` writeback age | `repo-only` (decided locally) |
| Top priority + recommended next action | `project.get_current_state` `currentPriority` / `nextAction` | as supplied by MCP — falls back to repo defaults |
| Lane tiles (claude/codex/agent) | `summariseLaneProgress` over MCP agents | `repo-only` until MCP returns server evidence |
| Automation loops (bridge-watch/mcp-poll/prompt-dry-run) | Same lanes payload, when MCP emits the loop ids | `repo-only` |
| Approvals · Audit queue · Overnight · Build/QA gates · Health Connect | Mobile stores + MCP gate snapshot | mixed — Build gate carries its own state |
| Audit Runner commands | Hard-coded safe commands in `AndroidControllerContext` | `repo-only` |

## Notification decision layer

`apps/mobile/src/services/controller-notification-decisions.ts`
turns the same inputs into a stable, ordered list of
`ControllerNotificationDecision` rows. Categories:

- `mcp_stale` — MCP writeback is `stale` or `missing`. Title and
  body include the stale reason.
- `lane_blocked` — any lane is `blocked`, `needs_user`,
  `needs_review`, or `complete_waiting_approval`. One decision
  per blocked lane.
- `approval_needed` — at least one local approval gate is
  `pending`.
- `installed_device_qa_needed` — fired by Admin/Dev when the
  release-gate summary shows the installed `versionCode` does not
  match the patched target.
- `all_lanes_idle` — every primary lane (`claude`, `codex`,
  `agent`) is idle or stale, none working.
- `idle_lane` — fall-through, fires only for primary lanes when
  `all_lanes_idle` did not.

Every decision carries `evidenceLabel: 'repo-only'`. The decision
layer never invents `live-now` or `installed-build verified`. Every
title is ≤ 60 chars and every body ≤ 240 chars; both are stripped
of secrets and raw logs by construction (the inputs are already
sanitised by `buildAndroidControllerContext`).

The decision dispatcher (`dispatchControllerDecisions` in
`push-approval-notifications.ts`) is idempotent on a 5-minute
slice. The dedupe map persists in the admin-dev notification
store, so a quick background → foreground cycle does not re-fire
the same alert. When `expo-notifications` is not installed (the
current state) the dispatcher still records the dedupe key so the
in-app banner channel does not repeat either.

### Installed-device blockers for live push

Local foreground notifications work today on any installed build
that includes `expo-notifications`. The app does not currently
include the dependency, so the dispatcher gracefully no-ops — see
`docs/APPROVAL_GATES_AND_PUSH.md` for the dep + native plumbing
checklist.

For background push (FCM), the additional blockers live on the
MCP daemon side and are tracked by the `widgetsStatus.push`
payload — `evidence_label` flips from `planned-only` to `live-now`
once `fcm_configured = true`. None of those flips are owned by
the mobile lane.

## Mirror to laptop (scrcpy over Wi-Fi)

The Samsung Galaxy S20+ pairs over Wireless Debugging. The IP/port
appear under **Settings → Developer options → Wireless debugging →
IP address & port** and rotate every time the phone toggles
Wireless Debugging or rejoins Wi-Fi.

```sh
adb connect 192.168.20.14:37907    # replace with the current IP/port
adb devices -l                     # confirm "device" state, model SM_G986B
nohup scrcpy -s 192.168.20.14:37907 \
  --max-size 1080 \
  --video-bit-rate 4M \
  --max-fps 30 \
  --no-audio \
  --window-title "Samsung Galaxy S20+ (192.168.20.14)" \
  >/tmp/scrcpy.log 2>&1 &
disown
```

Verified working invocation on macOS Darwin 25.x with scrcpy 3.3.4
against Android 13 / SM-G986B: `Renderer: metal · Texture:
488×1080`. The captured size is portrait-oriented to match the
phone's 1080×2400 override.

Why these flags:
- `--max-size 1080` matches the phone's `wm size override`, avoids
  upscaling.
- `--video-bit-rate 4M` survives flaky Wi-Fi without artefacts.
- `--max-fps 30` keeps the encoder budget under Wi-Fi headroom.
- `--no-audio` sidesteps Samsung's flaky aaudio stream over
  wireless adb.
- `nohup … & disown` detaches the process so closing the launching
  shell does not kill the mirror window.

If the window does not appear:
1. Check `pgrep -lf scrcpy` — the process should be alive.
2. Read `/tmp/scrcpy.log` for `Renderer: metal · Texture: …`. If
   missing after 10 s, the SDL window failed to open — usually
   another scrcpy process is holding the device server (`pkill -f
   scrcpy` and retry).
3. If the device shows as `offline`, retry the IP/port — Samsung
   rotates the wireless-debugging port on every reconnect.
4. For installed-device evidence capture, prefer the headless
   record path (no GUI required):
   ```sh
   scrcpy -s <ip>:<port> --no-playback \
     --record audit-artifacts/android/$(date +%Y%m%dT%H%M%S)Z/samsung-audit.mp4 \
     --time-limit 60
   ```

## Daily workflow

1. **Morning sweep.** Open Admin/Dev. The controller home banner
   renders the top decision. Resolve highest priority first
   (`mcp_stale` → `lane_blocked` → `approval_needed` → `installed_device_qa_needed`
   → idle).
2. **Stale MCP.** Tap "Copy MCP refresh prompt" or run
   `npm run bridge:snapshot && npm run bridge:verify` from the
   laptop tmux pane. The Samsung controller does not have laptop
   shell access by design.
3. **Idle lane.** Tap "Copy <lane> prompt" on the lane tile, paste
   into the worker's pane (Claude Code / Codex). The dispatcher
   queue (`docs/PROMPT_DISPATCHER.md`) is the canonical safe path.
4. **Approval pending.** Banner action "Open approvals" jumps to
   the approval-gates list further down Admin/Dev. Approve / defer
   / deny on phone — actions write to the local store immediately.
5. **Audit gate open.** Run the installed-device audit using the
   commands the controller exposes:
   - `audit-system/run-audit.sh --platform android`
   - `adb exec-out screencap -p > audit-artifacts/android/<ts>/screen.png`
   - `scrcpy --record audit-artifacts/android/<ts>/samsung-audit.mp4`

   These are mirror/simulator evidence — a separate installed-device
   QA pass on the same physical phone is required before the gate
   clears.

## Verification on a Samsung phone

| Check | How |
|---|---|
| Controller home renders | Sign in as admin → Settings → About → long-press Version → Admin / Dev. Confirm the Samsung controller card shows three primary lane tiles (`claude`, `codex`, `agent`). |
| Stale MCP banner | Stop the bridge (`pkill -f bridge-watch`). Within ~90s the controller banner flips to "MCP stale" with the stale reason. Restart `npm run mcp:auto` and confirm it returns to fresh after the next refresh. |
| Idle lane prompt | Force an idle status by leaving every Claude/Codex pane idle (no commands). Confirm the "all lanes idle" banner appears and the body includes the recommended next action. |
| Approval push | Create a synthetic local approval gate via the existing approval-gates UI. The banner switches to "Approvals: 1" and survives a foreground refresh without re-firing inside 5 minutes. |
| Mute toggle | Tap "Mute Samsung controller notifications" in Owner alerts. Confirm the banner stops rendering. |

The above checks run repo-only in the simulator/emulator. The
final claim "Samsung controller usable as automatic controller
on installed device" requires the same pass on the physical
Samsung phone, which is an installed-device QA gate.
