# Test Infrastructure Specification: Dual Track Opaque-Box E2E Test Suite

## 1. Executive Summary & Testing Philosophy

This document defines the authoritative **Dual Track Opaque-Box E2E Testing Infrastructure** for the **Lauburu Mesh Ecosystem Sovereign Storage Pooling, Read-Only Governance & Project-Specific ELO Engine** project.

### Testing Methodology
The test suite is architected around formal, rigorous software engineering verification principles:
1. **Opaque-Box Requirements-Driven Verification**: Test cases evaluate system behavior strictly against public interface contracts, functional requirements (R1, R2, R3), and acceptance criteria documented in `ORIGINAL_REQUEST.md` and `PROJECT.md`.
2. **Cardinal Law #1 (Zero-Mock & Zero-Simulation Mandate)**: Absolute prohibition against fake/simulated telemetry, mock arrays, or dummy assertions. All tests interact with authentic filesystem inodes, real C11 shared libraries (`liblauburu_storage.dylib`), live SHA-256 cryptographic digests, genuine POSIX permission bits, and authentic Bradley-Terry mathematical computations.
3. **Four-Tier Verification Matrix**:
   - **Tier 1: Feature Coverage (Isolation)**: Exhaustive functional verification of each feature in isolation (minimum 5 tests per feature).
   - **Tier 2: Boundary & Corner Cases (BVA & Robustness)**: Mathematical extremes, zero/empty inputs, oversized payloads, rate limits, exponent overflows, corruption injection, and permission rejections (minimum 5 tests per feature).
   - **Tier 3: Cross-Feature Combinations (Pairwise Interaction)**: Pairwise integration across subsystems (e.g. C11 storage bitrot feeding ELO backend health trials, read-only governance protecting against corrupted configs, 7-layer ring allocation feeding ELO infrastructure scorecards).
   - **Tier 4: Real-World Workload Scenarios**: End-to-end multi-step production pipelines simulating real mesh workloads (1,085 GB distributed storage dispersal across 7 layers, overnight ELO scorecard tracking, Tri-Vault health continuous auditing).
4. **Sub-Millisecond SLA & Deterministic Invariants**: Explicit microsecond-level performance benchmarking asserting:
   - C11 Dispersal latency $\le 2.0\text{ ms}$ (target $1.30\text{ ms}$)
   - C11 Reassembly latency $\le 0.5\text{ ms}$ (target $0.22\text{ ms}$)
   - ELO 3-Category Scorecard evaluation latency $\le 50.0\ \mu\text{s}$ (target $13.92\ \mu\text{s}$)
   - 100% Bit-for-bit SHA-256 exact match across storage slice/reassemble cycles
   - Zero undetected bitrot corruption via Fletcher32

---

## 2. Feature Inventory & Verification Mapping

The test infrastructure maps directly to the three core requirements (R1, R2, R3) and features (F1 through F8) defined in `PROJECT.md`:

| Feature ID | Feature Name | Core Specifications & Constraints | Primary Test Target |
|:---|:---|:---|:---|
| **F1** | Consistent Hash Ring & Routing | 7 physical mesh layers; 16 virtual ring slots per node (112 total); sorted ring (`qsort`); clockwise binary search routing with circular wrap; zero node starvation across 10,000 hashes. | `lauburu_pooled_storage.c`, `liblauburu_storage.dylib` |
| **F2** | 64KB Slicing & Fletcher32 Checksum | 64KB slicing (`DEFAULT_CHUNK_SIZE = 65536`); memory-alignment safe 16-bit word processing; odd-byte zero-padding; $< 10\text{ ns/KB}$ checksum throughput. | `compute_fletcher32`, `storage_pool_disperse_payload` |
| **F3** | 7-Layer Mesh Sovereign Storage Pooling | 1.0 MB test payload dispersal $\le 2.0\text{ ms}$; reassembly $\le 0.5\text{ ms}$; bit-for-bit SHA-256 verification; bitrot fault injection detection. | `storage_pool_reassemble_payload`, `lauburu_storage_bench` |
| **F4** | Canonical Context Map 0444 Mode | Mode `0444` (`-r--r--r--`) on primary (`07_docs_and_architecture/STORAGE_ARCHITECTURE_CONTEXT_MAP.md`) and Obsidian mirror; write bits stripped (`mode & 0o222 == 0`). | Filesystem `stat`, `os.access(..., os.W_OK) == False` |
| **F5** | Context Map Write Rejection & Parity | Adversarial write rejection (`PermissionError`); 100% bit-for-bit SHA256 parity (`80e96726...0b02`); YAML frontmatter freeze declaration; Git index tracking; Tri-Vault health. | `tests/test_storage_architecture_governance.py`, `git status` |
| **F6** | Bradley-Terry ELO Bounds & Overflow Guard | Ratings strictly bounded to $[1000.0, 3000.0]$; exponent clamped to $[-20.0, 20.0]$ in logistic expectation; $E_A + E_B = 1.0$ symmetry; underdog upset asymmetry. | `00_core_infrastructure/router_ai_daemon/src/elo/elo_engine.py` |
| **F7** | 3-Category Scorecard & Wilson CI | Wilson score empirical confidence intervals for finite Bernoulli trials; $n=0, k=0, k=n$ robustness; `CategoryScorecard` across Frontend, Backend, AI Models; composite ELO weighting ($0.30, 0.35, 0.35$). | `evaluate_project_scorecard`, `calculate_wilson_confidence_interval` |
| **F8** | ELO Engine Latency Verification | Mean scorecard evaluation latency $\le 50.0\ \mu\text{s}$ (target $13.92\ \mu\text{s}$); P99 $\le 50.0\ \mu\text{s}$ over 10,000 runs. | `time.perf_counter_ns`, `ProjectEloScorecard` |

---

## 3. Test Tier Specifications & Thresholds

| Tier | File Name | Purpose | Minimum Required Tests |
|:---|:---|:---|:---|
| **Tier 1** | `test_tier1_feature_coverage.py` | Validates each feature (Storage Pooling, Governance, ELO Engine) in strict isolation against documented interface contracts | $\ge 5$ tests per feature ($\ge 15$ total) |
| **Tier 2** | `test_tier2_boundary_corner.py` | Stresses extreme inputs, error paths, resource limits, 0-byte/huge payloads, rating bounds [1000, 3000], exponent overflows, bitrot flips, odd-byte padding | $\ge 5$ tests per feature ($\ge 15$ total) |
| **Tier 3** | `test_tier3_pairwise_combinations.py` | Verifies cross-feature interactions and state transitions across 2-way combinations (Storage + ELO, Governance + Storage, ELO + Governance) | $\ge 6$ pairwise interaction tests |
| **Tier 4** | `test_tier4_real_world_workload.py` | Executes full end-to-end mesh workloads (1,085 GB cluster dispersal simulation, continuous multi-epoch ELO tracking, Tri-Vault storage health verification) | $\ge 4$ complete application scenarios |
| **Master** | `run_e2e_tests.py` | Orchestrates all tiers, generates JSON test reports, verifies 100% pass rate with zero mocks | Single-command unified execution |

### Minimum Test Thresholds:
- **Tier 1**: $\ge 15$ tests
- **Tier 2**: $\ge 15$ tests
- **Tier 3**: $\ge 6$ tests
- **Tier 4**: $\ge 4$ tests
- **Total Suite Target**: $\ge 40$ rigorous opaque-box tests

---

## 4. Interface Contracts & Verification Schemas

### 4.1 C11 Sovereign Storage Pooling Contract (`lauburu_pooled_storage.h`)
```c
void storage_pool_init_ring(void);
bool storage_pool_add_node(const char *node_id, const char *role, uint64_t capacity_bytes);
void storage_pool_sort_ring(void);
int storage_pool_find_node(uint32_t chunk_hash);
uint32_t compute_fletcher32(const uint8_t *data, size_t len);
StoragePoolReport storage_pool_disperse_payload(
    const uint8_t *payload,
    size_t payload_len,
    StorageChunkMeta *out_metas,
    size_t max_chunks,
    uint8_t **out_chunks
);
bool storage_pool_reassemble_payload(
    const StorageChunkMeta *metas,
    uint8_t **chunks,
    size_t chunk_count,
    uint8_t *out_buffer,
    size_t expected_len
);
```

### 4.2 Storage Context Map Governance Contract
- **Primary Path**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/07_docs_and_architecture/STORAGE_ARCHITECTURE_CONTEXT_MAP.md`
- **Obsidian Mirror**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/07_STORAGE/CANONICAL_STORAGE_ARCHITECTURE_CONTEXT_MAP.md`
- **Permissions**: Mode `0444` (`-r--r--r--`).
- **Canonical SHA-256**: `80e96726403861ba55f8d9029442fb44e581bfb2da345adc0a27fce024ef0b02`
- **Frontmatter**: `status: READ_ONLY_AWAITING_CLOUD_CONSENSUS`, `access_mode: READ_ONLY`

### 4.3 ELO Engine Scorecard Contract (`elo_engine.py`)
```python
MIN_ELO_RATING: float = 1000.0
MAX_ELO_RATING: float = 3000.0

calculate_expected_score(rating_a: float, rating_b: float) -> Tuple[float, float]
calculate_wilson_confidence_interval(successes: int, trials: int, confidence: float = 0.95) -> Tuple[float, float]
evaluate_project_scorecard(
    frontend_rating: float, frontend_trials: int, frontend_passes: int,
    backend_rating: float, backend_trials: int, backend_passes: int,
    ai_rating: float, ai_trials: int, ai_passes: int,
    ...
) -> ProjectEloScorecard
```

---

## 5. Execution Command & Report Specification

```bash
# Execute master test runner
python3 tests/e2e_storage_elo/run_e2e_tests.py

# Execute via pytest with full verbosity
pytest -v tests/e2e_storage_elo/
```

- **JSON Report**: `reports/e2e_storage_elo_report.json`
- **Exit Code**: `0` on 100% pass; non-zero on any failure or mock violation.
