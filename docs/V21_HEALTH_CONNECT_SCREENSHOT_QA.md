# Android v21 Health Connect screenshot QA checklist

Aaron-facing checklist for verifying the v21 Health Connect
registration fix on an installed Android device. Each step
captures one screenshot. The bundle becomes the
installed-device evidence Agent uses to flip the v20 audit
finding from "patched, awaiting retest" to "verified".

**Do not start until v21 EAS build `a52a921e` has finished
AND been uploaded to Play Console Internal Testing AND
installed/updated on the device.** The build-state
separation panel in Admin/Dev should show
`Android — installed-build verified (v21)` (green) before
the screenshot run begins; if it says `repo-only` or shows
v20, stop.

## Pre-flight

- [ ] EAS build status = `FINISHED` at
      <https://expo.dev/accounts/aaronmaher/projects/lauburu-grappling-map/builds/a52a921e-5709-4d9f-9daa-fad720602492>
- [ ] AAB uploaded to Play Console → Internal testing → rollout
      started
- [ ] Internal-tester invite tapped on the device; install/
      update completed
- [ ] App opens, signs in with admin email
- [ ] Admin/Dev → "Build state separation" reads
      `Android — installed-build verified (v21)` with the green
      `verified` StatusPill

## Capture set (10 screenshots)

| # | Step | Pass criterion | Screenshot filename |
|---|---|---|---|
| 01 | Open the app cold; let the home screen render. | Header reads "Lauburu Grappling Map". No error toast. Readiness band visible. | `v21-01-home.png` |
| 02 | Navigate Health → Manage Sources (or whatever the source-management surface is named). | Health Connect row is visible with a SourceChip pill. The pill state is one of the canonical eight TruthLabels (live / synced from hub / imported summary / seed/provisional / setup required / planned / missing / stale). | `v21-02-manage-sources.png` |
| 03 | Tap **Connect** on the Health Connect row. | The OS Health Connect permissions dialog appears. (**This is the v20 failure point — v20 did NOT show the dialog.**) | `v21-03-permissions-dialog.png` |
| 04 | Grant at least one permission (Steps + Heart Rate is enough); tap Done. | Returns to the Lauburu app. The Health Connect row chip flips to `live` (or `seed/provisional` if no records yet). | `v21-04-after-grant.png` |
| 05 | Open the Android **Settings → Apps → Health Connect → App permissions**. | **Lauburu Grappling Map** appears in the list. (**This is the v20 root-cause symptom — v20 was not listed.**) | `v21-05-hc-apps-list.png` |
| 06 | Tap Lauburu Grappling Map within Health Connect → see permission detail. | The permissions Lauburu requested are visible (Steps, HR, HRV, RHR, ActiveCal, Sleep, Exercise, History). | `v21-06-hc-permission-detail.png` |
| 07 | Return to Lauburu → Health → tap **Sync** on the Health Connect row. | Sync completes; the meta line updates with metrics count + ages. | `v21-07-after-sync.png` |
| 08 | Open Admin/Dev (admin email signed in). Scroll to "Lane progress" chip block. | All lanes (Claude / Codex / Agent) render with status, age, fresh/stale/unknown StatusPill, progress bar (filled or "progress unknown"), "Next: …" line. | `v21-08-lane-progress.png` |
| 09 | Admin/Dev → "Build state separation" panel. | `Android — installed-build verified (v21)` with green `verified` StatusPill. iOS row shows `repo-only` (no v21 iOS yet). | `v21-09-build-state-separation.png` |
| 10 | Admin/Dev → "MCP" summary tile + "MCP transport diagnostics" panel (only if it renders). | "MCP" tile shows `MCP live · fresh · <age>` within 1.5s of fresh open. The diagnostics panel does NOT render (every call green). | `v21-10-mcp-status.png` |

## Failure-mode capture (only if the happy path doesn't hold)

If at step 03 the OS dialog does NOT appear AND at step 05
Health Connect → Apps does NOT list Lauburu Grappling Map:

- [ ] Stay on the Manage Sources screen. The Health Connect row
      chip should now read `'setup required'` and the row meta
      hint should read "Health Connect did not register the app
      — open Health Connect → Apps and verify Lauburu Grappling
      Map appears, then tap Retry permission request."
- [ ] The primary action label should read `Retry permission
      request` (not `Connect`). Capture: `v21-FAIL-did-not-register.png`.
- [ ] Tap **Retry permission request** once. If HC still does
      not list the app, the manifest fix did not apply at
      prebuild — the EAS build's bundled
      `android/app/src/main/AndroidManifest.xml` is missing the
      `ViewPermissionUsageActivity` activity-alias. Open the
      EAS build logs at
      <https://expo.dev/accounts/aaronmaher/projects/lauburu-grappling-map/builds/a52a921e-5709-4d9f-9daa-fad720602492>
      and search the logs for `ViewPermissionUsageActivity`. If
      absent → the config plugin failed to apply.

## Recording the result

After all 10 (or 11 with FAIL) screenshots are captured:

1. Ingest the 10 screenshots with the locked v21 label preset:

   ```sh
   npm run audit:android-scrcpy -- \
     --label-preset v21-health-connect \
     --android-version-code 21 \
     --audit-gate release_gate \
     --verification-status captured_only \
     --zip
   ```

   `captured_only` is intentional: this records the post-upload
   click-through evidence bundle without claiming the release
   gate passed. The script writes both `manifest.json` and
   `agent-qa-v21-health-connect-captured-only.json` beside the
   screenshots. That QA JSON is a `partial` scaffold with both
   release booleans false; it is evidence ingestion only, not an
   installed-device pass.

2. Upload the screenshots to the audit-bundle aggregator path
   (or attach to the action ledger entry
   `qa-android-versioncode-21-build-dispatched`).
3. If you need to record the captured-only bundle before Agent has
   made a verdict, run:

   ```sh
   npm run bridge:agent-qa -- \
     artifacts/app-audit/android-scrcpy/<timestamp>/agent-qa-v21-health-connect-captured-only.json
   ```

   This keeps `androidHealthConnect: partial` and does not clear
   the release gate.

4. After Agent reviews the screenshots, replace the scaffold with
   Agent's verdict and run `npm run bridge:agent-qa` with:

   ```json
   {
     "status": "<pass|fail|partial>",
     "platform": "android",
     "installedBuild": {
       "androidVersionCode": 21
     },
     "androidVersionCode": 21,
     "gate": "release_gate",
     "results": {
       "androidHealthConnect": "<pass|fail|partial>"
     },
     "evidence": {
       "screenshotRefs": ["v21-01-home.png", "...", "v21-10-mcp-status.png"],
       "notes": "<one-line summary>"
     }
   }
   ```

5. The bridge writes the result back to MCP. The Build State
   Separation panel's `Android — installed-build verified` badge
   already reflects v21; Agent's audit decision (verified vs
   needs-patch) flips on this `androidHealthConnect` field.

## Anti-rules

- **No installed-device verified claim** until this checklist
  produces a `pass` AGENT_QA_RESULT_JSON via `bridge:agent-qa`.
  The "verified" StatusPill in the Build State Separation panel
  is presence-of-versionCode; it is NOT the same as Agent's
  audit verdict.
- **No Play Console upload of v20.** Aaron's earlier upload of
  v20 is consumed; v21 is the only valid retest target.
- **No production rollout from this checklist.** The whole flow
  is Internal Testing only. Production release requires a
  separate approval gate.
- **No screenshots of the readiness band/score paired with
  causal language.** Per rule 9 + truth spec, readiness numbers
  are provisional. Captured screenshots are evidence of UI
  state, not health claims.
- **No tokens / raw URLs with credentials in screenshots.**
  Crop or redact any screen that shows an EAS / Supabase /
  Cloudflare admin URL with a query string token.

## Cross-references

- Build evidence: `docs/INSTALLED_DEVICE_QA_RELEASE_GATE.md`
  § "Android v21 retest readiness bundle (2026-05-09)".
- Approval gate: `gate-android-v21-install-test` in
  `data/approval-gates/gates.json`.
- Audit packet: `docs/AGENT_AUDIT_PACKET_2026-05-09.md`.
- Operating rules: rule 7 (cost), rule 9 (provisional health
  claims), rule 11 (MCP-first), rule 24 ("Rule 1 — no idle
  lanes").
