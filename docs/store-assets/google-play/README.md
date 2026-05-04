# Google Play store-listing assets

Generated for the Play Console listing pass that's currently
blocking Android tester full auto-promote. See
`docs/PLAY_SUBMIT_SETUP.md` §6 for the full listing checklist.

Updated 2026-05-05.

## Files in this folder

| File | Dimensions | Purpose |
|---|---|---|
| `app-icon-512.png` | 512×512 PNG, RGB | Play Console → Store listing → Main store listing → App icon. Resized from `apps/mobile/assets/images/icon.png` (1024×1024). |
| `feature-graphic-1024x500.png` | 1024×500 PNG, RGB | Play Console → Store listing → Graphics → Feature graphic. App icon centred on `#0A0A0A` background (matches splash colour). |

Both files were produced with `sips` on macOS from the existing app
icon. No new branding was introduced — they reuse what already
ships in the app, scaled and padded.

## What's still missing — phone screenshots

Play requires **at least 2 phone screenshots** (16:9 portrait, e.g.
1080×1920 or higher). Screenshots cannot be reliably produced from
this repo because they require a device or simulator running the
app at a real screen.

**Manual capture path** (15 min total):

1. Open the iOS Simulator (or a connected Android device with the
   app installed).
2. Sign in as a tester (or use the GuestBanner home view — both
   are acceptable as long as no PII shows on screen).
3. Capture two of the following screens, in this order:
   - **Home tab** — readiness summary, AthleteStateStrip, top-of-
     screen hierarchy. The most representative single screen.
   - **Health tab** — AppleHealthCard / Health Connect card with
     a real day of metrics, OR the Train tab session-type chip
     row, OR the 3D map view.
4. Save to `docs/store-assets/google-play/phone-screenshot-1.png`
   and `phone-screenshot-2.png`. Any portrait 9:16 ratio is fine
   provided the long edge is ≥1080.
5. Commit them via the same path used for the icon/graphic above
   (Aaron does this — Claude Code can't commit without local
   capture).

When uploading to Play Console:

- Privacy policy: `https://www.lauburugrapplingmap.com/privacy/`
- Account deletion: `https://www.lauburugrapplingmap.com/account-deletion/`
- App icon: this folder's `app-icon-512.png`
- Feature graphic: this folder's `feature-graphic-1024x500.png`
- Phone screenshots: the two captured per step 4 above

## After all assets are uploaded

Per `docs/MOBILE_RELEASE_SYNC.md` and `docs/PLAY_SUBMIT_SETUP.md`:

1. Save the listing.
2. Run **Review release → Start rollout** once on the v13 draft.
3. Edit `apps/mobile/eas.json`:
   ```jsonc
   "android": {
     "serviceAccountKeyPath": "./google-services-key.json",
     "track": "internal",
     "releaseStatus": "completed"   // changed from "draft"
   }
   ```
4. Commit + push. Future workflow dispatches with
   `submit_to_play=true` will create COMPLETED Internal Testing
   releases — no Play Console click required.

## What this folder is NOT for

- App Store Connect screenshots (separate ratios; see Apple
  guidelines when iOS production listing is in scope).
- Any production-track Play graphics (deferred until tester
  channels are stable AND the production listing pass is done).
- Source/master art (lives in `apps/mobile/assets/images/`).
