# Continue from iPhone (or anywhere)

Quick-start shortcuts for common tasks. Run from `~/LauburuGrapplingMap-mobile/`
on the Mac (via Tailscale + Blink/Termius SSH) or locally.

## Live probes

```sh
# Backend healthcheck
curl -sI https://lauburu-ai-backend-production.up.railway.app/api/athlete-memory/tour

# WHOOP status (synthetic JWT — safe to run anywhere)
HDR=$(echo -n '{"alg":"HS256","typ":"JWT"}' | base64 | tr -d '=' | tr '/+' '_-')
PAY=$(echo -n '{"sub":"probe-user"}' | base64 | tr -d '=' | tr '/+' '_-')
curl -s -H "x-athlete-memory-token: $ATHLETE_MEMORY_API_TOKEN" \
     -H "Authorization: Bearer $HDR.$PAY.sig" \
     https://lauburu-ai-backend-production.up.railway.app/api/integrations/whoop/status

# Feedback recent (durable now that the volume is mounted)
curl -s https://lauburu-ai-backend-production.up.railway.app/api/feedback/recent
```

## Mobile typecheck

```sh
npm --workspace @lauburu/mobile run typecheck
```

## Publish OTA (JS-only changes)

```sh
cd apps/mobile
npx eas-cli update --branch preview --message "Short description"
```

The iOS update ID appears in the last line of output. The app pulls on next
open (sometimes two launches — Expo downloads on launch N, applies on N+1).

## iOS preview build (for native-config changes)

```sh
cd apps/mobile
npx expo prebuild --platform ios --clean   # only if iOS native config changed
npx eas-cli build --profile preview --platform ios --non-interactive --no-wait
```

Build page appears as a URL in the output — open on iPhone Safari, tap Install.

## Backend deploy (Railway)

```sh
railway up --detach
```

Volume is already mounted at `/app/chat-app/data` — WHOOP tokens and feedback
attachments persist across redeploys.

## Railway / WHOOP runtime

```sh
# Service status
railway status

# Env var names + (masked) values
railway variables --service lauburu-ai-backend --kv | grep WHOOP

# Logs tail
railway logs --service lauburu-ai-backend

# Volume info
railway volume list
```

## Smoke check after any deploy

```sh
# 1. Backend up?
curl -sI https://lauburu-ai-backend-production.up.railway.app/api/athlete-memory/tour | head -1

# 2. Mobile JS bundle hash
# open Health tab in the app — the Health Actions panel shows:
#   update: <first-8-chars-of-new-update-id>
# Confirm this matches the iOS update ID from the `eas update` call.

# 3. WHOOP status (should be auth_required or connected for real users)
# Run the WHOOP probe above.
```

## Where things live

- Mobile app: `apps/mobile/`
- Shared types + Coach/readiness logic: `packages/shared/src/`
- Backend server: `chat-app/src/server/`
- Docs: `docs/TESTFLIGHT.md`, `docs/WHOOP_DIRECT_SETUP.md`, `CONTINUE.md`

## If something breaks

1. `railway logs --service lauburu-ai-backend` — latest backend errors.
2. Open the app → Health tab → Health actions panel shows `update:` + `health service:` lines. Screenshot = half the diagnosis.
3. HealthKit debug card (iOS) — tap Show + Refresh. `lastAuthRequestError` or `canaryReadCount` pinpoints Apple Health state.
4. `/api/feedback/recent` — tester feedback including auto-attached context.
