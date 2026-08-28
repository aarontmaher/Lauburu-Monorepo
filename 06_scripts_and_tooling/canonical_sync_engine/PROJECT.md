# Project: canonical_sync_engine

## Architecture
`canonical_sync_engine` is a distributed storage verification and quad-vault synchronization engine. It asserts the storage health of active mesh nodes and synchronizes canonical truth artifacts across four targets:
1. **PySpark Data Lake** (`lora_datasets/` and `04_data_and_memory/` JSONL/Delta format).
2. **Obsidian Vault** (`obsidian_vault/` Markdown notes with YAML frontmatter and bidirectional Wikilinks).
3. **GitHub Monorepo** (Git working tree structured JSON/data with `git` / `gh` CLI).
4. **Google Drive Cloud Mirror** (`/Volumes/Google Drive/My Drive` or resilient 3-tier local VFS fallback `data/gdrive_cache`).

```
                              [TruthArtifact Ingestion / CLI]
                                             │
                                             ▼
                        ┌─────────────────────────────────────────┐
                        │        CanonicalSyncEngine Core         │
                        └────────────────────┬────────────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
          [Mesh Storage Verification]                 [Pre-Flight Self-Healing]
         • Active Mesh Node Probing                  • Missing Inodes Auto-Creation
         • Headroom >= 10.0 GB Check                 • Stale Git Lock Removal
         • Rule 6 Health Invariants                  • Master Index Recovery
                       │
                       ▼
          [Quad-Vault Synchronization Adapters]
      ┌──────────────┬──────────────┬──────────────┬──────────────┐
      ▼              ▼              ▼              ▼              ▼
[PySpark Syncer] [Obsidian]    [Git Syncer]   [GDrive Syncer] [Audit Log]
 (JSONL Append)   (Wiki MD)    (Worktree Stg)  (3-Tier Mirror) (Telemetry)
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | `TruthArtifact` Data Model | Canonical representation with unique ID, type, payload, SHA-256 hash, timestamps, metadata | M1 | Survey & R2 |
| 2 | Fast-Path Health Checker | Sub-3ms inode & storage status check per Rule 6.3 | M1 | Survey & R1 |
| 3 | Mesh Node Storage Scanner | Multi-layer mesh probe (L1-L7) via local stats, SSH, ADB with non-blocking timeouts | M1 | R1 |
| 4 | Storage Health Invariant Validator | Invariant check: disk headroom >=10.0 GB, Index.md Wikilinks, no stale git locks | M1 | R1 & Rule 6.1 |
| 5 | Pre-Flight Self-Healer | Automatic healing of missing directories, stale locks, and missing Index.md per Rule 6.2 | M1 | R1 & Rule 6.2 |
| 6 | PySpark Vault Adapter | Atomic JSONL append to `truth_audit_master.jsonl` & Lakehouse dataset schemas | M2 | R2 |
| 7 | Obsidian Vault Adapter | Markdown note generation with YAML frontmatter, tags, Wikilinks `[[Index]]` | M2 | R2 |
| 8 | Git Vault Adapter | File staging in working tree using local `git` / `gh` CLI (zero credential leakage) | M2 | R2 & R3 |
| 9 | Google Drive Vault Adapter | 3-tier resilient synchronization (native mount -> rclone -> local VFS fallback cache) | M2 | R2 & R3 |
| 10 | Atomic Sync Engine Coordinator | `CanonicalSyncEngine` orchestrating verification, parallel vault sync, rollback, and verification | M3 | R2 |
| 11 | Unified CLI Interface | CLI (`canonical-sync verify`, `sync`, `status`, `heal`) | M3 | R1, R2, R3 |
| 12 | E2E Acceptance Test Pipeline | Standalone `test_sync_pipeline.py` injecting dummy artifact, syncing, asserting 4-vault propagation | M4 | Acceptance Criteria |
| 13 | Comprehensive Tier 1-4 Test Suite | Feature, boundary, cross-vault, and real-world application test suite | M4 | Test Methodology |
| 14 | Adversarial Coverage Hardening | Tier 5 white-box stress testing, corrupt payload handling, network fault recovery | M4 | Hardening |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Core Models & Mesh Storage Health Verification | `models/`, `verification/`, mesh scanner, invariant validator, pre-flight self-healer | None | DONE |
| M2 | Quad-Vault Synchronization Adapters | `sync/` (PySpark, Obsidian, Git, GDrive adapters with format conversion) | M1 | DONE |
| M3 | Canonical Sync Engine & CLI Interface | `engine/`, `cli/`, configuration manager, atomic coordination, telemetry logging | M1, M2 | DONE |
| M4 | Comprehensive E2E Testing & Acceptance Verification | `test_sync_pipeline.py`, Tier 1-4 test suite, Tier 5 adversarial stress testing | M1, M2, M3 | DONE |

## Interface Contracts
### `canonical_sync_engine.models`
```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
import datetime

class ArtifactType(str, Enum):
    TRUTH_AUDIT = "truth_audit"
    AI_DEBATE_CONSENSUS = "ai_debate_consensus"
    ARCHITECTURAL_DECISION = "architectural_decision"
    TELEMETRY_RECORD = "telemetry_record"
    LORA_PAIR = "lora_pair"
    BENCHMARK_RESULT = "benchmark_result"

@dataclass
class TruthArtifact:
    artifact_id: str
    artifact_type: ArtifactType
    title: str
    payload: Dict[str, Any]
    source_node: str
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    sha256_hash: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### `canonical_sync_engine.verification`
```python
@dataclass
class StorageHealthReport:
    is_healthy: bool
    disk_free_gb: float
    headroom_satisfied: bool
    obsidian_healthy: bool
    pyspark_healthy: bool
    git_healthy: bool
    gdrive_healthy: bool
    node_reports: Dict[str, Dict[str, Any]]
    violations: List[str]
    healed_actions: List[str]

class StorageVerifier:
    def fast_path_check(self) -> bool: ...
    def full_verification(self, scan_remote_nodes: bool = True) -> StorageHealthReport: ...
    def pre_flight_self_heal(self) -> List[str]: ...
```

### `canonical_sync_engine.sync`
```python
@dataclass
class VaultSyncResult:
    vault_name: str
    success: bool
    target_path: str
    sha256_hash: str
    error: Optional[str] = None
    bytes_written: int = 0

class BaseVaultSyncer:
    def sync(self, artifact: TruthArtifact) -> VaultSyncResult: ...
    def verify(self, artifact: TruthArtifact) -> bool: ...
```

### `canonical_sync_engine.engine`
```python
@dataclass
class QuadVaultSyncResult:
    artifact_id: str
    sha256_hash: str
    success: bool
    vault_results: Dict[str, VaultSyncResult]
    health_report: Optional[StorageHealthReport] = None
    errors: List[str] = field(default_factory=list)

class CanonicalSyncEngine:
    def sync_truth_artifact(self, artifact: TruthArtifact, verify_first: bool = True) -> QuadVaultSyncResult: ...
```

## Code Layout
```
canonical_sync_engine/
├── __init__.py
├── config.py                         # Central vault paths and environment configuration
├── models/
│   ├── __init__.py
│   ├── artifact.py                   # TruthArtifact and ArtifactType
│   ├── health.py                     # NodeStorageHealth and StorageHealthReport
│   └── sync_result.py                # VaultSyncResult and QuadVaultSyncResult
├── verification/
│   ├── __init__.py
│   ├── fast_path.py                  # <3ms fast-path verification
│   ├── headroom.py                   # Disk space & inode quota checks
│   ├── mesh_scanner.py               # L1-L7 multi-layer node storage scanner
│   ├── invariants.py                 # Rule 6 health invariants
│   └── self_healer.py                # Rule 6.2 pre-flight self-healing
├── sync/
│   ├── __init__.py
│   ├── base.py                       # BaseVaultSyncer abstract interface
│   ├── pyspark_syncer.py             # PySpark Data Lake JSONL adapter
│   ├── obsidian_syncer.py            # Obsidian Vault Markdown adapter with Wikilinks
│   ├── git_syncer.py                 # Git Monorepo worktree adapter with gh/git CLI
│   └── gdrive_syncer.py              # Google Drive adapter with 3-tier VFS fallback
├── engine/
│   ├── __init__.py
│   └── coordinator.py                # CanonicalSyncEngine atomic pipeline coordinator
├── cli/
│   ├── __init__.py
│   └── main.py                       # CLI entry point (canonical-sync)
tests/
├── __init__.py
├── conftest.py                       # Test fixtures, temp vault sandboxes, mock nodes
├── unit/
│   ├── test_models.py
│   ├── test_verification.py
│   ├── test_self_healer.py
│   └── test_vault_syncers.py
├── integration/
│   ├── test_sync_engine.py
│   └── test_cli.py
└── e2e/
    └── test_sync_pipeline.py         # Canonical acceptance test script
```
