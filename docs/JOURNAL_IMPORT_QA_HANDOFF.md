# Journal-import QA handoff (FS-020 B-20c parser + B-20d UI)

Status: handoff prepared in advance of Codex committing the FS-020
parser + paste-import UI. This doc describes the QA gate for the
journal-import flow; it does NOT prescribe parser internals
(Codex owns those per FS-020).

This is a doc-only handoff. It does not modify any FS-020 code.

## Lane ownership

- **Codex owns**: parser implementation + paste-import UI
  extension on `(tabs)/feedback.tsx` + `custom-journal-store.ts`
  + `packages/shared/src/journal/*` + parser tests.
- **Claude owns**: this QA handoff doc, AGENT_QA template,
  synthetic-fixture references, public-safety reminders.
- **Aaron owns**: tap-test of the import flow once Codex commits
  and a QA build is approved.

## Privacy and safety rules

These rules apply to BOTH Codex's parser/UI and any test fixture
or doc.

1. Aaron's real Notes-app journal data is private. It MUST NOT be
   copied into any repo file (fixtures, tests, docs, comments).
2. Synthetic fixtures only. The repo's
   `cloudflare-worker/test/fixtures/journal-import-synthetic-fixtures.ts`
   is the source of truth for parser test data. It uses generic
   drug names + synthetic structure.
3. The import-preview UI MUST keep the raw original line private
   on-device. Do NOT log raw text to MCP, action ledger, or any
   public surface.
4. Sensitive categories (medications, peptides, prescription
   inhalers, sleep aids) MUST require user confirmation before
   save when `journal_term_normalizations.needs_user_confirmation`
   is true. Never silent-save.
5. No medical advice. No causal claims. Associations only,
   provisional, missingness-aware.
6. Public MCP surfaces must NOT expose raw journal text or
   personally identifying journal patterns.

## UI flow Aaron will tap-test

(Spec'd by Codex in FS-020. This is the QA observation list, not
the implementation order.)

1. Open the app → Feedback / Track-something tab.
2. Tap the "Import notes" entry point (label may vary; expect
   wording near "Track something" or "Import journal" card).
3. Paste a synthetic Apple-Notes-shaped block into the text area.
   Suggested synthetic snippet (do NOT use Aaron's real notes):

   ```
   Peptides
   BPC 157
   2026-05-01 started 100 mcg daily
   2026-05-08 changed to 200 mcg daily

   Lungs and Sinuses
   Salbutamol
   2026-05-03 single use 2 puffs pre-training
   ```

4. Tap "Preview" (label may vary).
5. Verify the preview screen renders one row per parsed event.
   Each row should expose:
   - **date** (parsed or "unknown date" if ambiguous)
   - **section / category** (Peptides / Lungs and Sinuses / etc.)
   - **item / canonical candidate** (BPC 157 / Salbutamol / etc.)
   - **amount + unit** (100 mcg / 2 puffs / etc., or "unknown")
   - **event type** (started / changed dose / single use / stop /
     break / permanent stop)
   - **confidence** (user_reported vs imported_uncertain)
   - **warnings** (e.g. "needs confirmation: prescription
     medication" / "ambiguous dose change boundary")
6. Verify rows for sensitive categories are flagged
   `needs_user_confirmation` and CANNOT be saved without explicit
   per-row confirm.
7. Verify confirm/edit/skip controls per row.
8. Tap Save → verify only confirmed rows are saved. Ambiguous
   unconfirmed rows are skipped (or held for re-review), not
   silently saved.
9. Confirm copy on screen says (or equivalent):
   - "Preview before saving"
   - "Private journal data — stays on your device unless you save"
   - "Not medical advice"
   - "Associations only, not causation"
10. Confirm raw original line is NOT echoed to any visible log,
    debug surface, or action ledger.

## Negative-path checks

- **Empty paste** → expect "nothing to preview" state, no crash.
- **Garbage text** (random characters) → expect graceful "no
  events parsed" or all-rows-imported_uncertain state.
- **Mixed CSV + free-text** → expect parser to either pick the
  dominant shape or surface multiple-shape warning.
- **Misspelt term** (e.g. "amitriptaline" vs "amitriptyline") →
  expect alias resolution OR `needs_user_confirmation: true`.
- **Date ambiguity** ("started last week") → expect "unknown
  date" or relative-date resolution with low confidence.
- **Stop without start** → expect parser to flag orphaned stop
  event, not silently apply.

## Confidence + association safety reminders for QA

- Readiness/insights screens should NEVER assert that a journal
  event caused a metric change. Phrasing must be associations-only
  (e.g. "associated with", "co-occurred with", NEVER "caused" or
  "improved" or "worsened").
- Insights derived from imported notes should show `imported_uncertain`
  badges where the original parse was ambiguous.
- Sensitive-category items (medications/peptides/inhalers/sleep
  aids) require explicit user confirmation in BOTH preview AND
  insights surfaces before they appear in pattern-engine output.

## AGENT_QA_RESULT_JSON template (journal-import flow)

For pass:

```json
{
  "status": "pass",
  "gate": "fs020_journal_import",
  "platform": "android",
  "deviceName": "<device>",
  "installedBuild": {
    "androidVersionCode": 20,
    "appVersion": "0.1.0",
    "channel": "production",
    "track": "internal_testing"
  },
  "results": {
    "journalImportEntryPoint": "pass",
    "journalImportPasteArea": "pass",
    "journalImportPreviewRows": "pass",
    "journalImportSensitiveConfirmation": "pass",
    "journalImportSaveOnlyConfirmed": "pass",
    "journalImportPrivacyCopy": "pass",
    "journalImportNegativePaths": "pass"
  },
  "evidence": {
    "screenshotRefs": ["<screenshot or recording ref>"],
    "notes": "Synthetic paste preview rendered correctly; sensitive items required confirmation."
  }
}
```

For fail:

```json
{
  "status": "fail",
  "gate": "fs020_journal_import",
  "platform": "android",
  "deviceName": "<device>",
  "installedBuild": {
    "androidVersionCode": 20,
    "appVersion": "0.1.0"
  },
  "results": {
    "journalImportSensitiveConfirmation": "fail"
  },
  "requiredFixes": [
    "Sensitive-category row was saved without per-row confirm. <which fixture/scenario>."
  ],
  "evidence": {
    "screenshotRefs": ["<failure screen recording>"],
    "notes": "<context>"
  }
}
```

For blocked:

```json
{
  "status": "partial",
  "gate": "fs020_journal_import",
  "platform": "android",
  "deviceName": null,
  "installedBuild": {
    "androidVersionCode": null
  },
  "results": {
    "journalImportEntryPoint": "not_tested"
  },
  "requiredFixes": [
    "<exact reason: e.g. Codex parser/UI not yet committed; QA build not yet shipped; tester device unavailable>"
  ],
  "evidence": {
    "notes": "<context>"
  }
}
```

## QA gate sequencing

The journal-import flow is gated behind:

1. Codex commits FS-020 B-20c parser + B-20d UI extension.
2. Tree typecheck + parser tests greenify.
3. Aaron approves a NEW QA build (versionCode 20+) — the v19 .aab
   currently downloaded does NOT include FS-020 UI.
4. Aaron installs the new QA build and runs the tap-test above.
5. AGENT_QA result recorded via `npm run bridge:agent-qa`.

The current v19 build (Health Connect retest) is unrelated and
must NOT be conflated with the journal-import gate. v19 is a
separate gate (Health Connect → Connect crash fix) that needs
its own pass before ANY new QA build is dispatched.

## What this doc does NOT do

- It does NOT prescribe parser internals.
- It does NOT modify any FS-020 code.
- It does NOT include Aaron's real journal text.
- It does NOT clear the v19 release gate.
- It does NOT promote any release to public.
