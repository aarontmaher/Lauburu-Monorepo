# Connector security model

The rules every connector configuration (ChatGPT Connectors,
Claude MCP, Codex agent, future direct API integrations) must
respect when reading or writing Lauburu state.

This doc is the **invariant set**. Routes and tool implementations
in `RAILWAY_CONNECTOR_TOOLS.md` and
`CONNECTOR_BACKLOG_TOOLS_PLAN.md` extend this — they never relax
it.

Updated 2026-05-06.

## Invariants

These hold for every connector route, no exceptions.

1. **Owner-only authentication.** Every connector route requires
   the shared `ATHLETE_MEMORY_API_TOKEN` header. There is no
   public, per-tester, or anonymous access. The token lives on
   Railway env + the mobile app's
   `EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN` build env. It is NOT given
   to non-Aaron users.
2. **Read-only first, write-second.** The first wave of connector
   tools (`get_*`) is GET-only. The write wave (`create_*`,
   `update_*`, `mark_*`, `save_*`) lands after the read wave has
   been live and audited; even then, dangerous writes need a
   human-tap second factor.
3. **No raw secrets in any response.** Tokens, env values, OAuth
   client secrets, service-account keys, refresh tokens — never
   serialised to the wire. Routes that need to indicate presence
   return booleans (`dispatchAvailable: true`), not values.
4. **No raw athlete health data exposed.** The connector does NOT
   return raw HealthKit / Health Connect samples, raw WHOOP cycle
   records, raw food logs, sleep stages with timestamps, or any
   identifiable health time series. Aggregated state is OK
   (`healthSourceStatus.appleHealth: 'live'`); individual values
   are not.
5. **No full private athlete data dumps.** No connector route
   returns more than a single tester's identifiers, and only
   when the owner is reviewing an explicit feedback record. No
   bulk export of `auth.users`, `normalized_daily_metrics`, or
   `raw_source_events` exists or will exist.
6. **No arbitrary database access.** Connectors cannot run free-
   form SQL, cannot list tables, cannot describe schemas via the
   API. The Supabase service-role key never appears in any
   connector response.
7. **No arbitrary terminal execution.** The dispatch endpoint
   accepts only the `ADMIN_WORKFLOW_ALLOWLIST` set; any other
   workflow id is rejected with 400. Connectors are NOT given
   access to the dispatch endpoint at all in the first iteration
   — build dispatch is a human tap from Admin/Dev.
8. **No raw HealthKit / Health Connect mutations.** Even when
   the write wave lands, the connector cannot edit
   `normalized_daily_metrics` or `raw_source_events`. AI is
   read-only over health data, full stop. Humans (the user, on
   their own device) are the only mutators of source health
   records.
9. **Audit log on every write.** Every write tool call appends a
   line to Railway's request log with: timestamp + tool name +
   shape of the change (no field values for sensitive fields).
   When a durable Supabase audit table lands, the same line goes
   there. Errors are logged separately.
10. **Dangerous writes need human-tap second factor.** Listed in
    `CONNECTOR_BACKLOG_TOOLS_PLAN.md` §"Write tools" — priority
    changes are written as `priorityDraft` not direct,
    archiving is owner-only, build dispatch is owner-only, paid
    AI invocation is owner-only, stable athlete-memory writes
    are owner-only.

## Threat model

Designed to defend against:

- **Stolen connector token / mobile bundle reverse-engineered.**
  Token gives access to admin GET routes only. No raw user data,
  no raw secrets, no shell. Worst case: an attacker reads
  Aaron's project state. Mitigation: rotate the token on Railway
  if leaked. Tokens NOT rotated routinely; rotated on incident.
- **Compromised connector / hallucinating LLM.** Read tools have
  no side effects. Write tools (when they exist) write to
  `*_draft` fields that the owner promotes; any direct change
  requires a human tap. The dispatch endpoint is intentionally
  not connectorised.
- **Cross-user data leak.** Per-user `:athleteId/*` routes are
  JWT-gated with an ownership cross-check (already enforced —
  see `RAILWAY_BACKEND_AUDIT.md`). Connectors don't hit those
  routes; they read owner-state only, which doesn't carry per-
  user PII beyond what feedback records already contain.
- **Replayed connector calls.** Idempotent reads are safe to
  replay. Writes will use a per-action idempotency key (when
  introduced) so duplicate calls don't double-apply.

## Out of scope (for now)

- **OAuth-style per-user connector tokens.** First iteration is
  shared owner token only. If a non-Aaron owner ever needs
  access, the shared token rotates and a per-owner mint flow
  lands.
- **Streaming responses.** First iteration is request / response.
- **Server-Sent Events for live status.** Polling is enough for
  now (`get_work_status` is cheap).
- **Reading per-user health time series.** Explicitly forbidden
  per invariant 4.

## How this is enforced today

| Invariant | Enforcement |
|---|---|
| Owner-only auth | `requireAdminToken` middleware |
| No secrets in response | Hand-curated route handlers + audit doc + grep checks |
| No raw athlete data | Routes do not call the per-athlete reads from connector handlers |
| No arbitrary DB access | No SQL passthrough exists |
| No arbitrary shell | `ADMIN_WORKFLOW_ALLOWLIST` is a hard-coded array |
| No HealthKit mutations | Mobile-side only; backend has no /update endpoint for health rows |
| Audit log | Every workflow dispatch already logs `[admin-dispatch] workflow=… ref=… repo=… ok=…` to Railway logs (no token) |
| Dangerous-write gating | Spec'd in CONNECTOR_BACKLOG_TOOLS_PLAN; first writes require human-tap accept in Admin/Dev |
