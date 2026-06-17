# FS-020 B-20d UI Handoff

Status: parser-facing handoff only. Do not build the B-20d UI until the parser slice has Agent functional confirmation.

## Scope

B-20d is the mobile preview and confirmation UI for journal imports. It should consume the parser result from B-20c and let the user review entries before anything is saved.

The UI should handle:

- Apple Notes paste/import preview.
- Generic CSV preview.
- Cronometer CSV preview.
- Free-text journal preview.
- Term confirmation for sensitive matches.
- Macro summary preview when nutrition rows are present.
- Clear skipped-row and missing-field messages.

## Required First Screen

- Source type.
- Parsed item count.
- Skipped item count.
- Confirmation-needed count.
- A compact warning that this is context logging, not medical guidance.

## Review States

- `ready_to_import`: row can be imported.
- `needs_confirmation`: user must confirm canonical term/category before import.
- `missing_required_field`: row cannot import until fixed.
- `skipped`: row is ignored, with a short reason.

## Confirmation Rules

Sensitive categories must not be silently accepted:

- medication
- peptide
- inhaler
- sleep_aid when prescription-like

Allowed UI copy:

- "Confirm before saving"
- "Matched term"
- "Not enough context"
- "Skipped"

Avoid:

- Medical advice.
- Causation claims.
- Safety inference.
- Clinical thresholds.
- "You should" / "this will help".
- User-private data in shared dictionary or research snippets.
- Public-write tools.
- EAS build.
- App version/build bump.

## Macro Preview Rules

Show macro totals only when the parser has enough fields:

- protein grams
- carbs grams
- fat grams
- calories if supplied
- bodyweight-derived protein g/kg only if bodyweight is supplied by the same user import

When interval or source detail is missing, say:

- "Workout summary imported; interval splits not available."
- "Macro summary imported; source details may be incomplete."

## Privacy Rules

- Do not display raw IDs, tokens, hashes, service-role values, or internal config.
- Do not export journal details through public MCP surfaces.
- Store only user-scoped rows behind RLS.
- Use synthetic fixtures for tests and demos.

## B-20d Agent Acceptance Checklist

- Synthetic Apple Notes fixture renders without private data.
- Synthetic Cronometer fixture renders macro totals and missingness.
- Sensitive terms require confirmation.
- Non-sensitive supplement examples can be accepted without medical wording.
- Skipped rows show short reasons.
- No import/save action is available until confirmation-needed rows are resolved.
- Repo-only QA is recorded with `npm run bridge:agent-qa -- scripts/templates/agent-qa-parser-fs020-template.json`.
