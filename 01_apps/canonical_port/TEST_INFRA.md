# E2E Test Infra: Canonical Port TUI — Screen 6 (TrainingScreen & 5 Gyms)

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on implementation internals.
- Strict Zero-Mock rule: all data validation tests verify authentic system calls, file stats, and process queries.
- Methodology: Category-Partition + BVA + Pairwise + Real-World Workload Testing.

## Feature Inventory
| # | Feature | Source (Requirement) | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---------|----------------------|:------:|:------:|:------:|:------:|
| 1 | Ingestion Loop Telemetry | ORIGINAL_REQUEST R1 | 5 | 5 | ✓ | ✓ |
| 2 | Gatekeeper Intercepts | ORIGINAL_REQUEST R1 | 5 | 5 | ✓ | ✓ |
| 3 | Staged HF Epoch VRAM Gate | ORIGINAL_REQUEST R1 | 5 | 5 | ✓ | ✓ |
| 4 | Red/Blue Arena Gym | ORIGINAL_REQUEST R2.1 | 5 | 5 | ✓ | ✓ |
| 5 | Mesh Healing AI Gym | ORIGINAL_REQUEST R2.2 | 5 | 5 | ✓ | ✓ |
| 6 | AI Stealth Compute Arena | ORIGINAL_REQUEST R2.3 | 5 | 5 | ✓ | ✓ |
| 7 | Software Dev Game Leaderboard | ORIGINAL_REQUEST R2.4 | 5 | 5 | ✓ | ✓ |
| 8 | Spatial Grappling 3D Kinematics | ORIGINAL_REQUEST R2.5 | 5 | 5 | ✓ | ✓ |
| 9 | TUI Screen 6 & TrainingView Mounting | ORIGINAL_REQUEST R3 | 5 | 5 | ✓ | ✓ |
| 10 | MPSC Ring Buffering & Braille Sparklines | ORIGINAL_REQUEST R3 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- Test runner: `uv run pytest tests/ -v` and Textual Pilot async testing (`app.run_test()`).
- Invariant: Zero mock data arrays; missing hardware/files return explicit zero/empty states or waiting placeholders (`--`).
- Directory layout:
  - `tests/unit/`: Component-level unit tests for data collectors, ring buffers, Braille visualizers, and widgets.
  - `tests/e2e/`: End-to-end integration tests mounting Canonical TUI, switching to Screen 6, navigating tabs, and verifying telemetry stream updates.

## Coverage Thresholds
- Tier 1: ≥5 test cases per feature (Feature Coverage - happy paths)
- Tier 2: ≥5 test cases per feature (Boundary, corner cases, missing files, zero VRAM, empty logs)
- Tier 3: Pairwise cross-feature interactions (e.g. MPSC stream + Braille sparkline updates, Screen 6 switching while collector active)
- Tier 4: Real-world workload & endurance scenarios (continuous 100-cycle telemetry updates without memory leak or frame drop)
