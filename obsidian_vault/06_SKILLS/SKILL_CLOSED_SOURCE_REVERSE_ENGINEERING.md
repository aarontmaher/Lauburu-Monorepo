---
title: "Skill: Closed-Source Reverse Engineering"
tags: [skill, reverse_engineering, abliterated_models, sandbox, clean_room, c11, rust_wgpu]
created: "2026-09-04 10:06:00"
---

# 🕵️‍♂️ Closed-Source Reverse Engineering & Protocol Reconstruction Skill

Canonical Definition: [[CANONICAL_PROJECT_AND_STORAGE_RULE]]  
Skill File: `~/.gemini/config/skills/closed-source-reverse-engineering/SKILL.md`

## Overview
Operates abliterated local models (`Huihui-Qwen3.8-27B-abliterated`, `Mistral-Nemo-Instruct-2407-abliterated`, `Qwen2.5-7B-Instruct-abliterated`, `gemma-2-9b-it-abliterated`) inside an isolated sandbox (`01_apps/screen_lens/sandbox_evolution/reverse_engineering/`) to reverse engineer proprietary closed-source software, binary libraries, private APIs, and hardware BLE protocols that the Lauburu Mesh utilizes but did not create.

## Two-Tier Clean-Room Protocol
1. **Tier A (Abliterated Analyzer Swarm):** Inspects disassembled assembly (`otool`, `llvm-objdump`), raw hex dumps, and socket traffic. Emits purely functional behavioral specifications, framing state machines, and mathematical formulas.
2. **Tier B (Clean-Room Implementer Swarm):** Polyglot language specialists (C11, Rust/wgpu, Python, TypeScript) develop 100% original, zero-dependency implementations from scratch based solely on the functional specifications.
3. **Tri-Proof Verification:** Automated test harness verifies bit-for-bit packet reproduction against recorded authentic fixtures (Exit Code 0).
4. **LoRA Distillation:** Reconstructed schemas and clean-room parsers stream directly to `continuous_lora_dataset.jsonl`.
