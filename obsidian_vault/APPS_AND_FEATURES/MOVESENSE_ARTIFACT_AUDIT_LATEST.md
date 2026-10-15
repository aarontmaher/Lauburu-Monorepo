---
title: "Movesense Artifact Audit (latest)"
tags: [movesense, audit, rule0]
updated: "2026-10-03T15:04:02Z"
---
# Movesense Artifact Audit

Deterministic layer is authoritative; LLM layers are advisory plausibility reviews.

- Records scanned: **46,097** -> unique beats: **37,121** (1.24 records/beat)
- Beat artifact rate: **0.58%**
- Beat flags: `{'ectopic_or_artifact': 214, 'rr_out_of_range': 1}`
- Record flags: `{'hr_rr_mismatch': 1821, 'hr_jump': 14, 'hr_outside_45_185': 3}`
- Window discontinuities: 29 | stale records: 152 (max run 19)

- **gemini**: status `unavailable` model `-` agreement `None`
- **nvidia**: status `ok` model `nvidia/llama-3.2-11b-vision-instruct` agreement `{'compared': 20, 'agree': 20, 'llm_flags_passed_window': 0}`
  - filter gaps suggested: ['stuck_values', 'quantisation_replay', 'motion_noise']
- **medical_local**: status `deferred_ram_gate` model `-` agreement `None`
