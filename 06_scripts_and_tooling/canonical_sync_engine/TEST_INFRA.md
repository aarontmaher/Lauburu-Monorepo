# E2E Test Infra: canonical_sync_engine

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on implementation internals.
- Methodology: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinatorial + Real-World Workload Testing.
- Zero-Mock Truth Invariant: Actual disk operations, real SHA-256 assertions, live format validations, verified exit codes.

## Feature Inventory & Test Mapping
| # | Feature | Source | Tier 1 (Unit) | Tier 2 (Boundary) | Tier 3 (Cross-Vault) | Tier 4 (E2E) |
|---|---------|--------|:-------------:|:-----------------:|:--------------------:|:------------:|
| F1 | `TruthArtifact` Data Model & Hash | R2, Survey | 5 | 5 | ✓ | ✓ |
| F2 | Fast-Path Health Checker (<3ms) | R1, Rule 6.3 | 5 | 5 | ✓ | ✓ |
| F3 | Mesh Node Storage Scanner (L1-L7) | R1, Survey | 5 | 5 | ✓ | ✓ |
| F4 | Storage Health Invariant Validator | R1, Rule 6.1 | 5 | 5 | ✓ | ✓ |
| F5 | Pre-Flight Self-Healer (Rule 6.2) | R1, Rule 6.2 | 5 | 5 | ✓ | ✓ |
| F6 | PySpark Vault Syncer (JSONL) | R2 | 5 | 5 | ✓ | ✓ |
| F7 | Obsidian Vault Syncer (Markdown) | R2 | 5 | 5 | ✓ | ✓ |
| F8 | Git Monorepo Vault Syncer (Worktree) | R2, R3 | 5 | 5 | ✓ | ✓ |
| F9 | Google Drive Vault Syncer (3-Tier) | R2, R3 | 5 | 5 | ✓ | ✓ |
| F10 | Atomic Sync Engine Coordinator | R2 | 5 | 5 | ✓ | ✓ |
| F11 | Unified CLI Interface | R1, R2, R3 | 5 | 5 | ✓ | ✓ |
| F12 | E2E Acceptance Test Pipeline | Acceptance Criteria | 5 | 5 | ✓ | ✓ |

## Test Architecture
- Test Runner: `pytest` or standalone `python3 tests/e2e/test_sync_pipeline.py`.
- Acceptance Runner: `python3 tests/e2e/test_sync_pipeline.py` returning exit code `0`.
- Directory Layout:
  - `tests/unit/`: Testing models, individual verifiers, self-healing, and vault syncer formatters.
  - `tests/integration/`: Testing engine coordinator, atomic rollback, and CLI invocations.
  - `tests/e2e/`: Full acceptance test script injecting truth artifact, running sync engine, asserting propagation to all 4 destinations on disk, verifying SHA-256 integrity, and verifying health report.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Pass Criteria |
|---|----------|--------------------|---------------|
| 1 | Baseline Truth Artifact Propagation | F1, F6, F7, F8, F9, F10, F12 | Artifact written to all 4 vaults, SHA256 identical, exit code 0 |
| 2 | Degraded Storage Pre-Flight Auto-Healing | F2, F4, F5, F10 | Missing vault dirs and stale git locks healed automatically before sync succeeds |
| 3 | Offline Cloud Fallback Mirroring | F9, F10, F12 | Unmounted Google Drive seamlessly writes to local VFS cache without crashing |
| 4 | High-Concurrency Multi-Artifact Batch Sync | F1, F6, F7, F8, F9, F10 | Batch of diverse artifact types (TRUTH_AUDIT, AI_DEBATE, etc.) synced atomically with zero data corruption |
| 5 | Multi-Node Health Telemetry Audit | F3, F4, F11 | Mesh scanner inventories active nodes, reports headroom, and emits structured audit artifact |

## Coverage Thresholds
- Tier 1: >= 5 test cases per feature (>= 60 tests total)
- Tier 2: >= 5 boundary/corner test cases per feature (>= 60 tests total)
- Tier 3: Pairwise cross-vault synchronization consistency tests (>= 15 tests)
- Tier 4: >= 5 end-to-end real-world workload acceptance scenarios
- **Acceptance Script:** `tests/e2e/test_sync_pipeline.py` standalone executable returning exit code 0.
