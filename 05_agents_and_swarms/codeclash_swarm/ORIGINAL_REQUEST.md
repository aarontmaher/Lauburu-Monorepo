# Original User Request

## Initial Request — 2026-08-31T07:29:33Z

<USER_REQUEST>
Build a sovereign native screen observation CLI (`lauburu-lens`) to replace external capture binaries, and construct a CodeClash-powered adversarial Software Engineering & Code Analysis Swarm with 24/7 ELO tournaments.

Working directory: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/codeclash_swarm
Integrity mode: development

## Requirements

### R1. Native macOS Screen Lens CLI (`lauburu-lens`)
Implement an ultra-lightweight, native Rust/Swift capture daemon and CLI utilizing macOS `ScreenCaptureKit` and Apple Vision Framework OCR.
- Replace external Screenpipe dependency with a zero-bloat binary running on local port `:3035` / SQLite `~/.lauburu/screen_lens.sqlite`.
- Integrate subcommands directly into `lauburu-cli` / `lauburu-tui` (`lauburu lens start`, `lauburu lens query`, `lauburu lens status`).

### R2. CodeClash Arena & Tournament Engine (`codeclash_arena_engine.py`)
Implement a goal-oriented software engineering competition harness modeled on the CodeClash benchmark (`https://codeclash.ai/`, `codeclash-ai/codeclash`).
- Support multi-round head-to-head coding battles: Red Team (Bug Injection / Obfuscation / Vulnerability Search) vs Blue Team (AST Reconstruction / Static Analysis / Patch Synthesis).
- Compute Bradley-Terry ELO rankings across local models (Hermes 3, Qwen2.5-Coder, DeepSeek-R1-32B, Abliterated models).

### R3. Automated Software Engineering & AST Decompiler Engine (`ast_analysis_specialist.py`)
Build an automated code analysis engine capable of:
- High-throughput AST parsing, control-flow graph (CFG) extraction, and symbol resolution across Python, Rust, TypeScript, and Go.
- Reverse engineering and reconstructing clean source code from compiled bytecode/AST representations.
- Generating rigorous, adversarial pytest/cargo test suites targeting edge cases and regressions.

### R4. Swarm Truth Audit & Continuous LoRA Training Stream
Interlock the CodeClash tournament results with the Lauburu Tri-Vault architecture:
- Emit battle trajectories, winner patches, and debate transcripts to `04_data_and_memory/lora_datasets/codeclash_swe_training.jsonl`.
- Update the live ELO leaderboard in `obsidian_vault/04_ANALYTICS/CODECLASH_LEADERBOARD_2026.md` and TUI Tab 4.
- Enforce the Rule 6.3 Fast-Path storage invariant (>= 10.0 GB NVMe free space).

## Acceptance Criteria

### Compilation & Execution
- [ ] `lauburu-lens` captures desktop OCR frames and serves query endpoints via SQLite with 0 external cloud dependencies.
- [ ] `codeclash_arena_engine.py` executes a full 3-match tournament battle and records objective ELO ratings.
- [ ] `ast_analysis_specialist.py` extracts CFGs and parses complex polyglot AST trees without errors.
- [ ] 100% of integration test suites pass with zero mock data (Rule #0 compliant).
</USER_REQUEST>
<ADDITIONAL_METADATA>
The current local time is: 2026-08-31T17:29:33+10:00.
</ADDITIONAL_METADATA>
