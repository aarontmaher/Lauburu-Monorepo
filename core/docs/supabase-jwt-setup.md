# Supabase JWT setup (Save-to-Account mirror)

The Save-to-Account flow has two halves:

1. **Railway primary ingest** (`/v1/internal/ingest/*`) — working today, authenticated by `x-internal-token`. Apple Health days, nutrition, HIIT, training sessions, and AppAthleteState snapshots land here.
2. **Supabase mirror** (`/functions/v1/health-import`) — the redundant durability path. Authenticated by the user's Supabase access-token `Authorization: Bearer <jwt>`.

Only the second half is affected by JWT key configuration.

## Current model: JWT Signing Keys (not the legacy algorithm flip)

Supabase has migrated all projects from the legacy "JWT signing algorithm" toggle to the new **JWT Signing Keys** system. Project Settings → JWT Keys (sometimes nested under API → JWT Keys) shows:

> Legacy JWT secret has been migrated to new JWT Signing Keys. Legacy JWT secret can only be changed by rotating to a standby key and then revoking it. It is used to only verify JSON Web Tokens by Supabase products. This includes the anon and service_role JWT based API keys.

Practically:
- There is **no algorithm dropdown** anymore.
- Tokens are validated against an **active signing key**; you can rotate by promoting a **standby key** to active and revoking the old one.
- Edge functions (including `/health-import`) verify against the project's JWKS automatically — they accept whichever algorithm the active key uses.

## When the mirror fails

Failures now come from **key state**, not algorithm choice:

- **Token issued by an old / revoked key** → 401 from the edge function. User needs to sign out + sign back in so the client pulls a new token signed by the active key.
- **No active signing key** → all verifications fail. Promote a standby key to active in Project Settings → JWT Keys.
- **Service role key was rotated** → server-side ingest paths (chat-app) need their `SUPABASE_SERVICE_ROLE_KEY` env updated and Railway redeployed.

## Operator checklist (when needed)

### Routine "I rotated keys, mirror is blocked":
1. Open https://supabase.com/dashboard → `aarontmaher's Project` (ref `rejalrfmievikabgsakf`) → **Project Settings → JWT Keys**.
2. Confirm exactly one key is **active**. If multiple keys are listed (active + standby), that's normal during a rotation window.
3. On the phone: sign out of Lauburu, sign back in. The new session will mint a token signed by the active key.
4. Tap **Save to Account**. Supabase mirror line should flip from yellow `blocked · redundant path only` → green `✓ Supabase mirror saved: N days (range)`.

### "I want to rotate signing keys":
1. Project Settings → JWT Keys → **Create standby key**.
2. Test in staging by promoting the standby and verifying the mirror still works.
3. Once confirmed, **Revoke** the old active key.
4. Update any backend services that hold `SUPABASE_SERVICE_ROLE_KEY` (currently chat-app on Railway). Redeploy chat-app afterward.

## Mobile-side behavior (post-fix)

Old behavior: client pre-flighted the JWT header for `alg: ES*` and short-circuited Save-to-Account before hitting the edge function. **Removed** — under JWT Signing Keys, ES256 / RS256 / HS256 are all valid algorithms; the algorithm name doesn't predict whether the token will verify.

New behavior:
- Save-to-Account always attempts the mirror request.
- If the edge function returns 401 / "jwt" / "signing" / "unauthor", the client surfaces a yellow `Supabase mirror blocked · redundant path only` line + an admin-fix panel reading "Supabase JWT key needs attention. Sign out / back in. If recently rotated, confirm an active signing key exists in Project Settings → JWT Keys."
- Apple Health → Coach continues to work via Railway `/ingest/*` regardless.

## Apply the durable storage migrations (in order)

Both files are in repo and **both have been applied to staging (`ksvpbdenovthxbhsjgkx`) and production (`rejalrfmievikabgsakf`)** as of the durable-data rollout:

```
supabase/migrations/0001_durable_account_storage.sql
supabase/migrations/0002_manual_imports.sql
```

If a future branch / rebuilt environment needs them re-applied, run:
```bash
npx supabase link --project-ref <branch-or-prod-ref>
npx supabase db push --linked --include-all
```

Validation SQL (Project SQL Editor):
```sql
select relname, relrowsecurity from pg_class
  where relkind = 'r'
  and relname in (
    'athlete_profiles','source_connection_state','raw_source_events',
    'normalized_daily_metrics','interpreted_daily_artifacts',
    'interpreted_weekly_artifacts','athlete_memory',
    'memory_promotion_candidates','manual_imports',
    'unsupported_manual_fields'
  );
-- expect 10 rows, all relrowsecurity = true

select tablename, policyname, cmd, qual, with_check
  from pg_policies
  where schemaname = 'public'
  order by tablename, policyname;
-- expect 15 policies referencing auth.uid() = user_id in qual or with_check
```

## What stays truthful whether or not the mirror is live

- Railway primary ingest is the canonical write path today. The Supabase mirror is redundancy.
- WHOOP Direct data remains a backend snapshot, not WHOOP-native live readiness unless `recovery_score` is present in the current cycle.
- Shared KB never mixes athlete-private memory (see `docs/architecture/shared_kb/memory_separation_policy.md`).
