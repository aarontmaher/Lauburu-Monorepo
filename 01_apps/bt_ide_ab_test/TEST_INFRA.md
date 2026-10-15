# E2E Test Infra: IDE Intelligence Architecture

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on implementation design.
- Methodology: Category-Partition + Boundary Value Analysis + Pairwise Combinatorial + Real-World Workload Testing.
- Rule 1 & Rule 5 Compliance: Zero-Mock production truth; isolated unit-test loopback fixtures with simulated multi-IP telemetry; Tri-Proof verification (Actuation, Line-by-line checksum, Visual telemetry).

## Feature Inventory
| # | Feature | Source (Requirement) | Tier 1 | Tier 2 | Tier 3 |
|---|---------|---------------------|:------:|:------:|:------:|
| 1 | F1: Mesh RAM Polling | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 2 | F2: Global RAM Pool Metric | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 3 | F3: Backpressure Suspension | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 4 | F4: Hermes 3 Tool Routing | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 5 | F5: Qwen 2.5 Coder Code Engine | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 6 | F6: Vector DB Context Paging | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 7 | F7: SeaweedFS Hardware Affinity | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 8 | F8: SeaweedFS Volume Logic | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 9 | F9: Context Overflow Detection | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ |
| 10 | F10: Manual Cloud Escalation Gate | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ |
| 11 | F11: Silent Trace Capture | ORIGINAL_REQUEST §R5 | 5 | 5 | ✓ |
| 12 | F12: L3 Overnight Fine-Tuning Loop | ORIGINAL_REQUEST §R5 | 5 | 5 | ✓ |
| 13 | F13: Unified IDE Gateway Server | Acceptance Criteria | 5 | 5 | ✓ |

## Test Architecture
- Test runner: `pytest` via `/Users/aaron/.local/bin/pytest` and master CLI runner `tests/run_all_tiers.py`
- Test case format: pytest unit/integration tests with assert statements, exit code 0, JSON summary reports
- Directory layout:
  - `tests/conftest.py`: Loopback simulated HTTP telemetry endpoints, mock LLM backends, fixtures
  - `tests/test_tier1_features.py`: >=25 Feature Coverage tests (F1.1 to F5.5)
  - `tests/test_tier2_boundaries.py`: >=25 Boundary & Corner case tests (B1.1 to B5.5)
  - `tests/test_tier3_combinations.py`: 7 Pairwise cross-feature integration tests
  - `tests/test_tier4_real_world.py`: 4 Complete real-world application workload simulations
  - `tests/run_all_tiers.py`: Master CLI test runner generating Tri-Proof audit JSON

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Interactive IDE Coding Session Under Memory Stress | F1, F2, F3, F5 | High |
| 2 | Large-Scale Monorepo Multi-File Refactoring | F4, F5, F6, F7, F8 | High |
| 3 | Context Overflow with Manual Cloud Authorization & Overnight Learning | F9, F10, F11, F12 | High |
| 4 | Hardware Fault Injection & Resilient Self-Healing | F1, F7, F8, F13 | High |

## Coverage Thresholds
- Tier 1: >=5 tests per feature (minimum 25 tests)
- Tier 2: >=5 tests per feature (minimum 25 tests)
- Tier 3: Pairwise coverage of major feature interactions (minimum 7 tests)
- Tier 4: Realistic application scenarios (4 scenarios)
- **Total Minimum: >=60 comprehensive tests**
