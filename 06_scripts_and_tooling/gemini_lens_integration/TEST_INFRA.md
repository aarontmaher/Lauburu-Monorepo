# E2E Test Infra: Gemini Lens & PyCharm Integration

## Test Philosophy
- **Opaque-box, requirement-driven**: Derived directly from `ORIGINAL_REQUEST.md` (timestamp `2026-10-11T11:05:29Z`) and external contracts.
- **Strict Verification**: No mocking of core business logic. Authentic dry-run execution, zero exit code verification, file integrity validation (SHA256), and process inspection.
- **Methodology**: Systematic 4-Tier Approach (Category-Partition, Boundary Value Analysis, Pairwise Combinatorial, and Real-World Workload Testing).

## Feature Inventory & Test Mapping
| # | Feature | Requirement | Tier 1 | Tier 2 | Tier 3 |
|---|---------|-------------|:------:|:------:|:------:|
| 1 | Personal Admin Auth Provider (`aaron.t.maher@gmail.com`) | R4 | 5 | 5 | ✓ |
| 2 | Workspace OAuth Auth Provider (`lauburu@lauburugrappling.com`) | R4 | 5 | 5 | ✓ |
| 3 | GenAI Client Isolation (No Env Bleed) | R4 | 5 | 5 | ✓ |
| 4 | Screen Lens Perception Harvester | R1 | 5 | 5 | ✓ |
| 5 | Screen Lens Local DB Fallback | R1 | 5 | 5 | ✓ |
| 6 | Gemini Spark MCP SSE Client | R1 | 5 | 5 | ✓ |
| 7 | PyCharm Active Workspace Detector | R2 | 5 | 5 | ✓ |
| 8 | Atomic Notebook Cell Injector | R2 | 5 | 5 | ✓ |
| 9 | PyCharm Metadata Synchronizer (`.idea`) | R2 | 5 | 5 | ✓ |
| 10 | Colab GPU Offload State Manager | R2 | 5 | 5 | ✓ |
| 11 | HTTP 429 Exponential Backoff & Cooldown | R3 | 5 | 5 | ✓ |
| 12 | Offline Queue & Buffer Manager | R3 | 5 | 5 | ✓ |
| 13 | Missing Credential Graceful Degradation | R3 | 5 | 5 | ✓ |
| 14 | Sidecar Cron Specification & Wrapper | R3 | 5 | 5 | ✓ |
| 15 | Programmatic Dry-Run CLI Engine | Acceptance Criteria | 5 | 5 | ✓ |
| 16 | Concurrent Dual-Account Execution Flow | R4 | 5 | 5 | ✓ |

## Test Architecture
- **Test Runner**: `/opt/homebrew/bin/python3 -m pytest tests/`
- **Pass/Fail Semantics**: 100% tests must pass with Exit Code 0. Zero unhandled exceptions.
- **Directory Layout**:
  - `tests/test_sync_dry_run.py`: Acceptance criteria tests for `--dry-run` CLI execution, exit code 0, simulated sync logs for both accounts.
  - `tests/test_auth_isolation.py`: Tests for credential loading, token refresh, and concurrent client isolation.
  - `tests/test_lens_pycharm_sync.py`: Tests for harvesting ports 3037/3035/4003, SQLite fallback, and atomic notebook injection.
  - `tests/test_resilience.py`: Tests for HTTP 429 backoff, offline buffering durability, and missing key resilience.
  - `tests/test_dual_account_e2e.py`: End-to-end integration test validating concurrent execution of both user accounts within the orchestrator notebook.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Full Hourly Dry-Run Cycle | F11, F13, F14, F15, F16 | High |
| 2 | Network Outage During Hourly Cron with Offline Queue Drain | F11, F12, F13, F15 | High |
| 3 | Concurrent Dual-Account Notebook Synchronization in PyCharm | F1, F2, F3, F7, F8, F9, F16 | Very High |
| 4 | Screen Lens Stream Port Offline with SQLite Recovery | F4, F5, F8, F9 | Medium |
| 5 | Host RAM Under 4.8 GB Triggering Colab GPU Offload State | F10, F8, F9, F16 | High |

## Coverage Thresholds
- **Tier 1 (Feature Coverage)**: ≥5 test cases per feature (80+ test assertions).
- **Tier 2 (Boundary & Corner Cases)**: ≥5 test cases per feature (80+ boundary assertions).
- **Tier 3 (Cross-Feature Combinations)**: ≥16 pairwise integration tests.
- **Tier 4 (Real-World Scenarios)**: 5 comprehensive application scenarios.
- **Total Minimum Target**: >180 test assertions across the suite.
