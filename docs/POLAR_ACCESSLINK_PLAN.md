# Polar AccessLink — integration outline

This is an **outline-only** document per
`CLAUDE-MCP-UNIFICATION-SPEC-04`. No implementation plan
gate-by-gate yet; that lands when WHOOP OAuth migration
(FS-008) ships and the Worker has a proven OAuth pattern to
copy.

The current Polar story for users: data flows
**Polar device → Polar Flow app → Apple Health (iOS) /
Health Connect (Android) → Lauburu** as
`synced from hub`. AccessLink direct integration is **not
required** for parity — it is an upgrade path, not a fix.

Updated 2026-05-07.

## Why bother with AccessLink at all

Hub-routed Polar data has gaps:

- **Per-event timing**: Polar's heart-rate-variability and
  R-R interval streams aren't always written to Apple Health
  at full resolution. AccessLink exposes per-second HR + R-R
  arrays directly.
- **Training-load metrics**: Polar's Recovery Pro / Cardio
  Load / Muscle Load / Strain values don't write to the hub.
  AccessLink exposes them.
- **Sleep stages**: Polar Sleep Plus produces stage breakdowns
  the hub doesn't always carry intact.
- **Non-platform-native users**: a Polar user on iOS who hasn't
  configured Apple Health can still feed Lauburu via
  AccessLink without changing phones.

For Aaron's MVP the gap is small. AccessLink is a P2 feature
behind WHOOP, not a P1 blocker.

## Status

| Field | Value |
|---|---|
| FS candidate | FS-012 (`docs/FEEDBACK_SUGGESTIONS.md`) |
| Status | `planned` |
| Lane | A |
| Roadmap rank | P1.5 (label hygiene) → P2 (AccessLink direct) |
| Truth label | reserved (`Polar Direct` / `Polar AccessLink`) — never used today |
| Blocker | (1) FS-008 must ship first so Worker has a proven OAuth pattern. (2) Polar AccessLink developer access (request + approval). (3) Aaron approval to spend the integration work. |

## Outline

### O.1 Vendor model

- Polar AccessLink is a partner OAuth-2 API. Apply at
  https://www.polar.com/accesslink-api/. Approval can take
  weeks.
- Per-user OAuth, scoped tokens. Same model as WHOOP — single
  client ID / secret on the server, per-user access /
  refresh tokens.
- Webhooks are POST to a configured URL when a new exercise /
  daily activity / physical-info entry lands. AccessLink also
  supports polling.

### O.2 Worker contract (mirror of WHOOP)

When this lands, it follows the same Worker pattern as the
WHOOP migration in `docs/WHOOP_DIRECT_SETUP.md` § M.1:

- Routes:
  - `GET /api/integrations/polar/connect` — start OAuth.
  - `GET /api/integrations/polar/callback` — exchange code.
  - `POST /api/integrations/polar/webhook` — receive events.
  - `GET /api/integrations/polar/status` (admin) — diagnostic.
- Secrets via `wrangler secret put`:
  `POLAR_CLIENT_ID`, `POLAR_CLIENT_SECRET`,
  `POLAR_TOKEN_ENC_KEY`,
  `INTEGRATION_STATE_SECRET` (shared with WHOOP).
- Storage: new `polar_tokens` Supabase table, RLS-gated like
  `whoop_tokens` (same shape as `docs/WHOOP_DIRECT_SETUP.md`
  § M.2 step 2 — copy & rename).

### O.3 Truth-label rules (anti-overlap with hub)

Polar AccessLink data lands as truth label **`Polar Direct`**
(reserved label, finally usable). Polar hub-routed data keeps
its `synced from hub` label. The two paths coexist:

- If both feeds carry the same date's data, `Polar Direct`
  takes precedence in the readiness compute. Hub stays
  visible in the veteran "More sources" disclosure as a
  cross-check.
- If only the hub feed has the date, Lauburu reads from the
  hub. The truth label STAYS `synced from hub`. Coders MUST
  NOT relabel hub-sourced rows as `Polar Direct` just because
  the user is also AccessLink-connected.
- If only AccessLink has the date (user disabled hub
  forwarding), label is `Polar Direct`. No fallback to the
  hub for that date.

Anti-rule: **the user-visible source name is "Polar Direct"
or "Polar via Apple Health" / "Polar via Health Connect" —
never "Polar live" / "Polar AccessLink (Direct)" / "Polar +
hub" / any hyphenation that hides the provenance distinction.**

### O.4 Confidence ceiling

| Window | Truth label | Confidence ceiling |
|---|---|---|
| Day 0 ship | `seed/provisional` | `confidence: low` |
| Day 1–7 | `seed/provisional` | `confidence: low` only |
| Day 7+ if conditions match WHOOP § M.3 | `Polar Direct` (`live`) | `confidence: medium` (never `high`) |

Same four conditions as WHOOP for `seed/provisional` → `live`
promotion (≥7 days clean, daily readings present, Aaron
tester confirmation, FS-012 `approved_done` line).

### O.5 Beginner / veteran UX

| | Beginner | Veteran |
|---|---|---|
| Default state | "Polar Direct" surface **hidden** | "Polar Direct" connect button visible only after Apple Health / Health Connect already populated |
| If user never connects AccessLink | Polar via hub keeps showing as today | Polar Direct row shows `setup required` chip |
| If user connects AccessLink | one card per Polar metric flips to `Polar Direct` | per-metric provenance row in More Sources shows direct vs hub |

### O.6 Rate limits & data volume

- AccessLink rate limit: per Polar's docs, ~3000 requests /
  day / app. Polling cadence MUST stay ≤1 fetch / user / 5
  min outside of webhook events.
- Webhook events should debounce 30s per user before triggering
  a fetch (multiple Polar metric writes for one workout fan
  out into multiple webhooks).

### O.7 Out of scope

- **Polar Beat / older Polar accounts that don't migrate to
  Polar Flow.** AccessLink only covers Flow accounts.
- **BLE HR strap from a Polar device.** That's the
  `Bluetooth HR sensor` lane (§ 1.6 of audit doc), not
  AccessLink.
- **Polar M200 / M430 / V650** legacy devices that don't sync
  to Flow. Out of scope.
- **Real-time HR streaming.** AccessLink is a daily-summary +
  exercise-export API, not a live stream.

### O.8 Anti-rules

- **No "Polar Direct" UI label** until this plan has shipped
  and the truth label crossed `seed/provisional` → `live`.
- **No partial AccessLink ship.** Connect → fetch → render →
  truth-label → tester-confirm in one bundle. Half-shipping
  produces user-facing confusion (a connect button that
  doesn't actually flow data).
- **No copying WHOOP-specific UI to Polar.** Each direct
  source has its own card; do not generalise prematurely.
- **No paying for Polar AccessLink "Pro" tier** unless Aaron
  reviews the cost / benefit. The free tier covers everything
  in this outline.

## Cross-references

- `docs/HEALTH_NUTRITION_READINESS_AUDIT.md` § 1.5 / § 3.1.
- `docs/HEALTH_CONNECTIVITY_TRUTH_SPEC.md` (truth labels).
- `docs/WHOOP_DIRECT_SETUP.md` § M (the OAuth pattern this
  outline copies).
- `docs/WHOOP_POLAR_SYNC_STRATEGY.md` (anti-rules around
  vendor labels).
- `docs/FEEDBACK_SUGGESTIONS.md` FS-012.
