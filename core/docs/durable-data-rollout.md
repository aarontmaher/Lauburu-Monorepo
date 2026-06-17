# Durable data rollout — operator checklist

Single document for the three remaining operator-side blockers. Mobile is already patched and shipping via OTA `e2e717e1-0ed6-49bb-8b55-f6d8a35091ea` (Readiness on Home + WHOOP demoted). The backend durable-data layer below needs operator action; nothing here is safe to fake.

---

## 0 — Pre-flight (read first)

- All migrations are additive (`create extension if not exists`, `create table if not exists`, `create policy`). No drops. Safe to dry-run against a Supabase branch first.
- Mobile does NOT assume any of these tables exist. Save-to-Account already degrades cleanly when the Supabase mirror is unavailable; Custom Readiness keeps working off Apple Health alone.
- Chat-app server source for the cap lifts (90 → 1825 days) is committed in repo; Railway production still runs the previous bundle until you redeploy.

---

## 1 — Supabase JWT keys (current model: JWT Signing Keys)

**Background:** Supabase has migrated projects from the legacy "JWT signing algorithm" toggle to **JWT Signing Keys**. There is no algorithm dropdown anymore. Edge functions (including `/health-import`) verify against the project's active signing key via JWKS — any of HS256 / RS256 / ES256 is valid.

**Default state for `aarontmaher's Project` (ref `rejalrfmievikabgsakf`):** an active signing key already exists. The Save-to-Account Supabase mirror should work as long as:
- the user's mobile session token is signed by that active key, AND
- the chat-app service role token (used for server-side writes) is current.

**When you'd need to act:**
- Recently rotated keys → mobile session needs a fresh token. **Action**: on the phone, sign out → sign back in. Tap **Save to Account**.
- Active key was revoked without a standby promoted → no token verifies. **Action**: Project Settings → JWT Keys → confirm an active key, promote a standby if needed.
- Service role key rotated → chat-app's `SUPABASE_SERVICE_ROLE_KEY` env on Railway is stale. **Action**: update env, redeploy chat-app.

**No code-side action required for HS256 vs RS256 vs ES256** — the mobile pre-flight algorithm-rejection has been removed (it was tied to the legacy model).

**Validate:** sign out + sign back in on the phone, tap **Save to Account**. The Supabase mirror line should be green `✓ Supabase mirror saved: N days (range)`. If it stays yellow, the on-card admin-fix panel will name the actual blocker (key needs attention, RLS denied, etc.).

---

## 2 — Apply migrations (in order)

Both files are additive and live in repo:

```
supabase/migrations/0001_durable_account_storage.sql
supabase/migrations/0002_manual_imports.sql
```

### 0001 — durable account storage
8 tables: `athlete_profiles`, `source_connection_state`, `raw_source_events`, `normalized_daily_metrics`, `interpreted_daily_artifacts`, `interpreted_weekly_artifacts`, `athlete_memory`, `memory_promotion_candidates`. RLS scoped `auth.uid() = user_id` on every select. Derived layers (`normalized_*`, `interpreted_*`, `athlete_memory` writes) are select-only for clients — service-role writes only. Daily refresh **must not** mutate `athlete_memory`.

### 0002 — manual imports
2 tables: `manual_imports` (dedupe key `(user_id, file_hash)`, RLS select+insert self) + `unsupported_manual_fields` (RLS select self, service-role-only inserts).

### Apply order (always branch first)

```bash
# Branch / preview project
npx supabase link --project-ref <branch-ref>
npx supabase db push --linked --include-all

# Validate (run inside Supabase SQL Editor or psql)
select relname, relrowsecurity
  from pg_class
  where relname in (
    'athlete_profiles','source_connection_state','raw_source_events',
    'normalized_daily_metrics','interpreted_daily_artifacts',
    'interpreted_weekly_artifacts','athlete_memory',
    'memory_promotion_candidates','manual_imports',
    'unsupported_manual_fields'
  );
-- expect 10 rows, all with relrowsecurity = true

select schemaname, tablename, policyname, cmd, qual
  from pg_policies
  where schemaname = 'public'
  order by tablename, policyname;
-- expect select_own / insert_own policies referencing auth.uid()

-- Sanity: dry-import as a real test user via the chat-app service
-- role, then read back via that user's JWT — confirm select-own only
-- returns the test user's rows.
```

```bash
# After branch run is clean
npx supabase link --project-ref <production-ref>
npx supabase db push --linked --include-all
```

---

## 3 — chat-app Railway redeploy

**Why:** the 90 → 1825-day cap lifts in `chat-app/src/server/routes/internal.ts` (`store.getNormalizedRecent(athleteId, 1825)`) and `chat-app/src/server/routes/backlog.ts` (`Math.min(1825, body.windowDays ?? 30)`) are repo-only. Mobile already attaches the wider Coach windows via the OTA — backend ignores extra fields silently until redeployed.

**Action:**

```bash
cd chat-app
npm install
npm run build
# Verify:
npm run typecheck
npm run test:contracts

# Push to Railway (preferred path: git push on the linked branch)
git push origin main
# OR if you use the Railway CLI:
railway up --service lauburu-ai-backend
```

Required env on the Railway service (already present, just confirm):

- `INTERNAL_API_TOKEN` — server-to-server token (matches `EXPO_PUBLIC_INTERNAL_API_TOKEN` in mobile env).
- `ATHLETE_MEMORY_API_TOKEN` — public-facing athlete-memory bearer.
- `SUPABASE_URL` — your project URL.
- `SUPABASE_SERVICE_ROLE_KEY` — service role for server-side writes to the new tables. **Never expose to mobile.**
- `SUPABASE_JWT_SECRET` — required if you flipped to HS256 in step 1; the chat-app verifies user JWTs with this.

After deploy, smoke-check:

```bash
curl -sS https://lauburu-ai-backend-production.up.railway.app/healthz | jq .
# Then run the round-trip suite from chat-app/DEPLOY.md.
```

Mobile-visible state markers that should immediately become accurate after this redeploy:

- `whoopDirectAvailable` / `whoopCsvAvailable` / `appleHealthAvailable` — already returned client-side via AppAthleteState.source_roles.
- `customReadinessAvailable` — driven by AppAthleteState.recovery_context.score_0_100 not being null. App-side; redeploy doesn't change.
- Long-term history depth — backend now serves 1825 days; mobile renders up to 365 days locally + Coach attaches 60d nutrition + 30 sessions.

---

## 4 — Aggregation activation (later)

`chat-app/src/server/services/aggregation/index.ts` is in repo as a skeleton. Once steps 1–3 are live AND user-consent flow is shipped:

1. Add a column or table for explicit per-user `aggregation_consent_at` (a follow-up migration `0003_aggregation_consent.sql` — not yet authored).
2. Set `process.env.AGGREGATION_ENABLED=1` on the chat-app Railway service.
3. Replace the skeleton's `isAggregationReady()` placeholder with a real check that
   - confirms `process.env.AGGREGATION_ENABLED === '1'`,
   - confirms a `select 1 from public.normalized_daily_metrics limit 1` returns a row,
   - and confirms a non-empty consenting cohort exists.
4. Until activated, all public methods on the aggregation module return `{ ok: false, reason: 'aggregation_not_ready' }` — safe to leave imported / called from any future code path.

`K_MIN_COHORT = 10`; bucketed (`training_high_freq` / `training_low_freq` / `sleep_high` / `sleep_low`); percentile-only output; never per-user values; never names/emails/exact timestamps/device IDs; never includes `athlete_memory`.

---

## 5 — End-to-end verification (after 1–3 land)

| Check | Expected |
|---|---|
| Mobile Save to Account | green `✓ Railway primary saved: …` + green `✓ Supabase mirror saved: N days` (no longer yellow) |
| Mobile Health card | unchanged: WHOOP demoted, Readiness primary on Home |
| Coach long-trend question | response references trend windows >90 days when history is present |
| Manual WHOOP zip re-upload | second upload of the same zip is a no-op (`unique (user_id, file_hash)`) |
| Cross-user isolation probe | sign in as user B, read attempt against user A's `normalized_daily_metrics` row → empty result (RLS) |
| Privacy boundary | `select count(*) from public.athlete_memory where user_id <> auth.uid()` from a non-service JWT → 0 rows |
| Aggregation surface | until step 4, no Coach answer references "anonymized cohort" — verified by grep over Coach output |

---

## 6 — What stays repo-only / what's live

| Layer | Status |
|---|---|
| Mobile OTA (Readiness on Home, WHOOP demoted, custom-readiness composite, source-state markers, idle-copy fix, Echelon parser, vendor debug) | **live** (most recent published OTA `e2e717e1-0ed6-49bb-8b55-f6d8a35091ea`) |
| Mobile `.env.production` `EXPO_PUBLIC_WHOOP_BRIDGE_OWNER_IDS` | **live** in OTA — also baked into `eas.json` envs for the next native rebuild |
| Supabase migrations 0001 + 0002 | **applied to staging (`ksvpbdenovthxbhsjgkx`) and production (`rejalrfmievikabgsakf`)**; 10 tables, RLS on, 15 policies. ✅ |
| Supabase JWT model | **JWT Signing Keys (current)**; no algorithm flip needed. Mobile pre-flight removed; mirror request now flows through to the edge function. |
| chat-app cap-lift (`90 → 1825d`) | **repo only** — awaits Railway redeploy |
| `chat-app/src/server/services/aggregation/` skeleton | **repo only**, inert until normalized table is reachable + consent gating + env flag |
