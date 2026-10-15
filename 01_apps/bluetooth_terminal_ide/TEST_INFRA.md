# E2E Test Infra: Canonical Mesh Fallback Terminal

## Test Philosophy
- **Opaque-box, Requirement-Driven**: Derived strictly from `ORIGINAL_REQUEST.md` and user-facing specifications without dependence on internal private variables.
- **Rule 0 & Rule 1 Zero-Mock Truth Verification**: Prohibits `unittest.mock`, `MagicMock`, `patch`, and `monkeypatch`. All tests execute genuine OS processes, authentic local loopback TCP sockets (`127.0.0.1`), real file fixtures, and Textual's async `app.run_test()` pilot.
- **Methodology**: 4-Tier Framework (Category-Partition, Boundary Value Analysis, Pairwise Combinatorial Testing, Real-World Workload Testing) plus Tier 0 AST Static Audit.

## Feature Inventory & Test Matrix
| # | Feature | Source (Requirement) | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---------|----------------------|:------:|:------:|:------:|:------:|
| 1 | Stage 1 BLE GATT NUS Protocol | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 2 | Stage 1 OOB Payload Catalog (WOL, Daemons) | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 3 | Stage 2 Autonomous Outage Prober | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 4 | Stage 2 Dual-Mode Escalation (Magic Packet + Shizuku BNEP) | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 5 | Stage 3 Subnet Reachability Prober | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 6 | Stage 3 Non-Blocking SSH/Mosh Spawner | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- **Location**: `tests/e2e_mesh_fallback/`
- **Master Test Runner**: `python3 tests/e2e_mesh_fallback/run_mesh_fallback_e2e_suite.py`
- **Pass/Fail Semantics**: All suites must pass with Exit Code 0, zero failures, zero skipped critical assertions.
- **Directory Layout**:
  - `fixtures/`: Executable mock-free script fixtures (e.g. `mock_rish.sh`, `mock_ssh.sh`, loopback server factories)
  - `test_tier1_feature_coverage.py`: 30+ isolated happy-path feature tests (>=5 per feature)
  - `test_tier2_boundary_corner.py`: 30+ boundary, corner-case, MTU limit, and timeout tests
  - `test_tier3_cross_feature.py`: Pairwise combination tests (TUI + workers + spawner)
  - `test_tier4_real_world.py`: Real-world scenario tests directly verifying Acceptance Criteria AC1, AC2, AC3
  - `test_zero_mock_compliance.py`: Static AST analysis enforcing Rule 0 across all test and source files

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Acceptance Criterion | Complexity |
|---|----------|--------------------|----------------------|------------|
| 1 | Objective OOB Routing (`/nexus ENABLE_PAN`) | F1, F2, F4 | AC1: Explicitly logs Shizuku SDK bridge invocation | Medium |
| 2 | Simulated Outage Autonomous Escalation | F3, F4 | AC2: Autonomous 1 ➡️ 2 transition without manual input | High |
| 3 | Reachable Subnet Triggers SSH/Mosh Spawn | F5, F6 | AC3: Subnet triggers spawn without crashing TUI event loop | High |
| 4 | Full 3-Stage Escalation Ladder Roundtrip | F1, F2, F3, F4, F5, F6 | End-to-end 1 ➡️ 2 ➡️ 3 roundtrip | High |
| 5 | Demotion & Self-Healing on Link Collapse | F1, F5, F6 | 3 ➡️ 1 demotion & autonomous OOB recovery packet | High |

## Coverage Thresholds
- Tier 1: ≥30 tests (≥5 per feature across 6 features)
- Tier 2: ≥30 tests (≥5 per feature focusing on MTU, timeouts, flapping)
- Tier 3: ≥6 pairwise tests covering TUI, background probers, and subprocess execution
- Tier 4: ≥5 end-to-end application scenarios
- Tier 0: 100% Zero-Mock AST compliance
