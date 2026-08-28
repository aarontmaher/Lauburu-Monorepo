# E2E Test Infra: Canonical TUI Prototypes

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on implementation design.
- Methodology: Category-Partition + Boundary Value Analysis + Pairwise Combinatorial + Real-World Workload Testing.

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---------|---------------------|:------:|:------:|:------:|:------:|
| 1 | Python Textual Prototype | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 2 | Go Bubble Tea Prototype | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 3 | Rust Ratatui Prototype | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 4 | Concurrency & Atomic Locking | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 5 | Toolchain Provisioner (Termux) | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 6 | Wireless Deployment Pipeline | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 7 | Remote Smoke Verification | ORIGINAL_REQUEST Acceptance | 5 | 5 | ✓ | ✓ |

## Test Architecture
- Test runner: `pytest 01_apps/canonical_tui_prototypes/tests/test_tui_e2e.py -v` and `bash 01_apps/canonical_tui_prototypes/verify/verify_termux.sh`
- Test case format: Automated CLI executions with `--verify` and `--timeout`, assertions on exit code, stdout JSON validation, lock contention stress tests.
- Directory layout:
  - `01_apps/canonical_tui_prototypes/tests/test_tui_e2e.py`
  - `01_apps/canonical_tui_prototypes/verify/verify_local.py`
  - `01_apps/canonical_tui_prototypes/verify/verify_termux.sh`

## Test Tiers
1. **Tier 1: Feature Coverage (≥5 per feature)**:
   - Python Textual basic run, verify mode, schema check, UI widgets render, exit code 0.
   - Go Bubble Tea basic run, verify mode, lipgloss styles, table formatting, exit code 0.
   - Rust Ratatui basic run, verify mode, crossterm backend, provider parsing, exit code 0.
   - State reading with default path, custom `--state-path`, custom `--poll-interval`.
2. **Tier 2: Boundary & Corner Cases (≥5 per feature)**:
   - Missing state file (graceful fallback/syncing state).
   - Empty JSON file (0-byte transient state handled with retry).
   - Malformed/corrupted JSON (no unhandled panic/crash).
   - Exhausted quotas (0 remaining tokens, visual warning).
   - Massive token counts / overflow values.
   - Rapid concurrent file replacement (POSIX atomic rename simulation).
3. **Tier 3: Cross-Feature Combinations**:
   - Live quota file mutation while TUIs are polling.
   - Simultaneous execution of Python, Go, and Rust TUIs reading the same lockfile.
   - Remote execution over SSH with mock Termux sandbox.
4. **Tier 4: Real-World Application Scenarios**:
   - End-to-end deployment to live Termux node (Samsung S20+ / Pixel 10 Pro XL).
   - Live compilation in Termux (`go build`, `cargo build --release`).
   - Live smoke verification reading actual `cloud_api_quota_state.json`.

## Coverage Thresholds
- Tier 1: ≥35 test cases
- Tier 2: ≥35 test cases
- Tier 3: ≥10 test cases
- Tier 4: ≥5 realistic application scenarios
