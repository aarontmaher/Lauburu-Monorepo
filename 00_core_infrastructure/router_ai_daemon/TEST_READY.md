# TEST_READY — Router AI Daemon (`smolagi`)

**Status**: READY / PUBLISHED  
**Test Suite Architect**: `test_writer_1` (E2E Testing Track Specialist)  
**Date**: 2026-08-27  
**Test Harness Version**: 1.0.0  

---

## 1. Test Suite Summary

The comprehensive, opaque-box, requirement-driven 4-tier E2E test suite for the **Router AI Daemon (`smolagi`)** has been constructed, validated, and published. The test suite strictly validates all requirements from `ORIGINAL_REQUEST.md`, architectural specifications in `PROJECT.md`, and mathematical models mined across all 13 features (F1 through F13) and 5 Acceptance Criteria (AC-1 through AC-5).

---

## 2. Test Execution Command

To execute the entire test suite:

```bash
python3 -m pytest tests/ -v
```

Or using `uv`:

```bash
uv run pytest tests/ -v
```

---

## 3. Test Coverage & Results Breakdown

| Test Suite Tier | File | Scope | Tests Count | Status | Execution Time |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Acceptance Criteria** | `tests/test_acceptance_criteria.py` | Direct validation of AC-1 to AC-5 from ORIGINAL_REQUEST.md | 5 | 🟢 5 / 5 PASS | < 0.05s |
| **Tier 1: Feature Coverage** | `tests/test_tier1_features.py` | Granular unit/feature tests for Features F1 through F13 (>=5 tests per feature) | 65 | 🟢 65 / 65 PASS | < 0.10s |
| **Tier 2: Boundaries & Corners** | `tests/test_tier2_boundaries.py` | RAM budget ceilings (300MB), OOM protection, 50ms/5s timeouts, network drops, corrupt GGUF, malformed JSON | 30 | 🟢 30 / 30 PASS | < 0.05s |
| **Tier 3: Pairwise Combinations** | `tests/test_tier3_combinations.py` | Cross-feature interactions (consensus + scaling, swap + routing, waste tax + monetization, etc.) | 8 | 🟢 8 / 8 PASS | < 0.05s |
| **Tier 4: Real-World Workloads** | `tests/test_tier4_real_world.py` | Multi-step end-to-end operational workflows (cold boot, surge offload, shadow code-off, rogue model tax, asset sale) | 5 | 🟢 5 / 5 PASS | < 0.05s |
| **Total Test Suite** | `tests/` | **Full Monorepo Router Daemon Test Suite** | **113** | 🟢 **113 / 113 PASS (100%)** | **~1.6s** |

---

## 4. Key Invariants & Contracts Certified

1. **Hardware & Memory Cap**: Verified hard constraint of $\le 300.0\text{ MB}$ total resident container memory.
2. **Zero-Flash-Wear Invariant**: Secrets, model weights, and outbox queues reside strictly on volatile `tmpfs` mounts (`/tmp/models/`, `/tmp/secrets/`, `/tmp/business_queue/`).
3. **Consensus SLA**: Fast-path concord ($\Delta \le 0.15$) resolves in $< 3.5\text{ms}$; Micro-debate reaches accord in $\le 3$ rounds within the 50ms SLA budget.
4. **David vs Goliath ELO Multiplier**: Asymmetric leverage awards up to $+350.0$ ELO for sub-1B models defeating 70B+ frontier models on complex tasks, while gluttonous cloud models receive near-zero ELO on trivial tasks.
5. **Economic Realignment Penalty**: Mathematical Waste Tax ($\text{Tax}_{\text{waste}}$) strictly deducts severe ELO for unoptimized compute/API spend and revokes cloud credentials upon repeated waste.
6. **Decentralized Asset Packaging**: Strict compliance with the 5-class JSON Schema (`code_component`, `cli_tool`, `mcp_server`, `sdk_package`, `surplus_compute`) signed via HMAC-SHA256 consensus signatures.

---

## 5. Artifact Manifest

- `tests/conftest.py`: Master test fixtures, mock 7-layer hardware topology, and reference contract calculation engines.
- `tests/test_tier1_features.py`: 65 Tier-1 feature test cases.
- `tests/test_tier2_boundaries.py`: 30 Tier-2 boundary, corner case, and stress test cases.
- `tests/test_tier3_combinations.py`: 8 Tier-3 cross-feature pairwise integration test cases.
- `tests/test_tier4_real_world.py`: 5 Tier-4 real-world operational workflow test cases.
- `tests/test_acceptance_criteria.py`: 5 explicit Acceptance Criteria test cases.
- `TEST_INFRA.md`: Full architectural specification of testing methodology and feature matrix.
- `TEST_READY.md`: Formal publication and test runner manifest.
