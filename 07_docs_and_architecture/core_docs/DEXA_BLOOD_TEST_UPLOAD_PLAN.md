# DEXA scans + blood test uploads — plan

How occasional body-composition scans and blood panels become
**evidence/context** in the app without becoming
diagnostic/medical surfaces. Spec only — no implementation
tonight, and a hard gate on it ever creating a clinical-claim
surface.

Updated 2026-05-06.

## Priority

Below #1 (Apple Health iOS), #2 (Health Connect Android), #3
(WHOOP/Polar secondary), #4 (Grappler Readiness prototype),
#5 (HIIT / conditioning), #6 (Nutrition).

These are point-in-time / quarterly assessments for trend
context, not daily readiness inputs.

## What goes in

### DEXA scan

User uploads a DEXA report (PDF, screenshot, or manual entry of
the headline numbers). Captured fields:

- Total body mass (kg).
- Lean mass (kg) — total + per region (arms, legs, trunk).
- Fat mass (kg) + body fat %.
- Bone mineral density (g/cm²) — total + region-specific.
- Visceral adipose tissue (kg or score, depending on machine).
- Date of scan.
- Reference range for the user's age/sex (when present in the
  report).
- Source: machine model + clinic if user provides.

### Blood panel

User uploads a blood-test report. Captured fields (only those
the user explicitly logs — no auto-OCR yet):

- Iron / ferritin / TIBC / transferrin saturation.
- Vitamin D (25-OH).
- B12 / folate.
- Hormones (testosterone, DHEA-S, cortisol — when the panel
  includes them).
- Thyroid (TSH, fT3, fT4).
- Inflammatory markers (CRP, ESR).
- Metabolic markers (glucose, HbA1c, lipid panel).
- Reference ranges as printed on the report.
- Date of draw + lab name.

## What the app does with this data

**Strict rules:**

1. **Trend context only.** When the user asks Coach about
   long-term trends, recent DEXA scans + blood markers can
   appear as **factual sentences** in the answer (e.g. "vitamin
   D was 28 ng/mL on 2026-04-12 vs 35 ng/mL on 2025-11-04").
   No interpretation.
2. **No diagnostic claims.** The app does NOT say "you have a
   deficiency", "your testosterone is low", "you need
   supplementation". Reference ranges are surfaced as the
   report's own range; the app does not interpret abnormal
   values.
3. **No treatment recommendations.** No supplement suggestions,
   no medication suggestions, no dietary intervention based on
   a blood marker.
4. **No medical advice surface.** A persistent disclaimer at
   the top of the upload UI: "Lauburu surfaces these reports
   as evidence for trend tracking. It does not provide medical
   advice. Consult your physician for clinical interpretation."

## What the app NEVER does

- Does NOT auto-pull from clinic portals (Quest, Labcorp,
  hospital MyChart, etc.) — every upload is explicit user
  action.
- Does NOT share DEXA / blood data with third parties.
- Does NOT include DEXA / blood values in any AI prompt sent to
  a paid LLM API (gated by `AI_PROVIDER_STRATEGY.md`; even when
  paid AI lands, sensitive medical fields stay device-local
  unless the user explicitly opts each value into the AI
  context).
- Does NOT send DEXA / blood values to the connector tools per
  `CONNECTOR_SECURITY_MODEL.md` invariant 4 (no raw athlete
  health data).
- Does NOT compute a "biological age" or similar marketing
  metric.
- Does NOT make claims tied to health outcomes ("low ferritin
  means…").

## Storage

- **Device-local secure storage** for the structured fields the
  user logs.
- **Optional Supabase row** if the user opts into cross-device
  sync — gated by an explicit "back up to cloud" toggle. Until
  that toggle exists, DEXA / blood data lives on the device only.
- **Photos / PDFs of the report** stay device-local. No upload
  path to the backend or to any cloud — even when sync exists,
  raw documents are too sensitive to ship without an explicit
  per-document confirmation.

## UI shape (target)

Single section in Health tab → More sources → Body composition /
Lab work disclosure (collapsed by default).

```
Body composition (DEXA)
Last scan: 2026-04-12 — 76.8kg, 11.2% body fat, lean 68.2kg
Trend (4 scans): lean +1.4kg, fat −0.8kg vs first scan
[Add scan]

Lab work (blood)
Last panel: 2026-03-21 (Quest)
Vitamin D: 28 ng/mL (range 30–100, flagged on lab report)
Ferritin: 102 ng/mL (range 30–400)
[Add panel]
```

The "flagged on lab report" sub-line repeats the lab's own
flagging — the app does not add its own flag.

## Implementation order (when in priority)

1. Spec (this doc).
2. Local-only DEXA entry form (manual fields, no PDF parsing).
3. Local-only blood-panel entry form.
4. Health-tab "Body composition / Lab work" disclosure.
5. Coach context bundle: include the most-recent values + dates
   when the user asks a long-term trend question.
6. Cross-device cloud sync toggle (with the explicit privacy
   confirm modal).
7. PDF parsing — much later, only if user demand justifies the
   privacy/ETL effort.

## Out of scope

- OCR of DEXA / blood test PDFs.
- Auto-fetching from clinic portals.
- Comparison against population norms beyond what the lab report
  itself prints.
- Recommending labs to the user ("you should test your TSH").
- Integration with telehealth platforms.
- Anything that resembles diagnosis or prescription.
