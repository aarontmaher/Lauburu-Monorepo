# Science vs App Context Rules

## Purpose
Defines when AI should cite science vs app context vs internal reasoning. Prevents the app from fabricating citations, presenting heuristics as research, or conflating different knowledge sources.

## What Belongs
- Definitions of each knowledge bucket
- Rules for when to use each
- Labeling and attribution requirements

## What Does NOT Belong
- Actual science references or citation database
- Coaching philosophy (see coaching_philosophy.md)
- Prompt engineering for AI outputs

## Truth Status
Canonical. All AI outputs must comply with these rules.

## Stability
Stable. The categories are structural. Specific labeling conventions may be refined.

## Update Cadence
When a new knowledge source is introduced or when the science grounding system is built.

## Key Rules

### Knowledge Buckets

| Bucket | Definition | Example |
|--------|-----------|---------|
| **Science** | Peer-reviewed research or established expert consensus | "HRV trends correlate with autonomic recovery status" |
| **App Context** | Real device data from the user's own integrations | "Your WHOOP recovery was 42% this morning" |
| **Internal Context** | Coaching philosophy and product reasoning built into the app | "We recommend lighter sessions on low-recovery days" |

### When to Use Each

- **Cite science** when making a general physiological or training claim. Example: "Sleep quality affects next-day recovery" can be grounded in research.
- **Cite app context** when referencing the user's actual data. Example: "Your HRV has trended down over the past week" is app context — it comes from their WHOOP data.
- **Cite internal context** when the recommendation follows from the app's coaching philosophy rather than from a specific study. Example: "We suggest a lighter session today" is an internal context decision, not a scientific prescription.

### Mandatory Rules

1. **Never fabricate citations.** If the app does not have a specific study to reference, it must not invent one. "Research suggests..." without a real reference is prohibited.

2. **Never present app heuristics as science.** The coaching engine's rules (e.g., "recovery below 33% triggers a rest recommendation") are product decisions, not scientific findings. They may be informed by science but are not science themselves.

3. **Mark aspirational grounding clearly.** The science bucket is not yet populated with a real citation database. Until it is, any science-adjacent claim must be framed as general knowledge ("It is generally understood that...") rather than as a specific citation. This aspirational state must be acknowledged internally and never hidden behind confident language.

4. **Never conflate user data with general truth.** "Your sleep was poor" (app context) is not the same as "Poor sleep impairs recovery" (science). Both may appear in the same output, but they must be distinguishable.

5. **Prefer app context over science when both apply.** The user's actual data is more relevant to them than a general study. Lead with their data, then optionally support with science context if it adds value.
