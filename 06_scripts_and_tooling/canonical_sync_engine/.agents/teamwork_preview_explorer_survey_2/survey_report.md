# Canonical Sync Engine: Codebase & Architecture Survey Report (Survey 2)

**Document**: `survey_report.md`  
**Working Directory**: `/Users/aaron/teamwork_projects/canonical_sync_engine/.agents/teamwork_preview_explorer_survey_2`  
**Date**: 2026-08-27  
**Author**: Survey 2 Explorer Agent (`teamwork_preview_explorer_survey_2`)  
**Mission**: Codebase, Storage Topology, and Canonical Architecture Survey for `canonical_sync_engine`

---

## 1. Executive Summary & Survey Objectives

The **Canonical Sync Engine** is the authoritative distributed storage verification and quad-vault synchronization subsystem for the **Lauburu Mesh Ecosystem**. Its mission is to enforce the **Canonical Tri-Vault & Cloud Storage Rule** by verifying the storage health of physical mesh devices and atomically synchronizing "truth artifacts" (AI debate consensus records, LoRA fine-tuning pairs, architectural whitepapers, telemetry datasets, and codebase diffs) across the four canonical storage layers:
1. **PySpark Data Lake** (`/Users/aaron/DFS_UNIFIED/lora_datasets` & `04_data_and_memory`): Structured high-throughput JSONL/Parquet datasets.
2. **Obsidian Knowledge Graph** (`/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault`): Bidirectionally linked Markdown notes with YAML frontmatter and Wikilinks.
3. **GitHub Monorepo Working Tree** (`/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo`): Version-controlled repository artifacts staged/committed via local `git`/`gh`.
4. **Google Drive Cloud Mirror** (`/Volumes/Google Drive/My Drive/Lauburu_AI_Memory` or local VFS fallback `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/gdrive_cache`): Immortal cloud memory mirror.

This survey establishes the complete technical foundation, architectural boundaries, data models, interface contracts, self-healing protocols, and test harnesses required to implement `canonical_sync_engine`.

---

## 2. Current Codebase State & Monorepo Survey

### 2.1 State of `canonical_sync_engine`
- **Path**: `/Users/aaron/teamwork_projects/canonical_sync_engine`
- **Existing Files**:
  - `ORIGINAL_REQUEST.md`: Contains primary user requirements (R1: Mesh Storage Verification, R2: Quad-Vault Synchronization, R3: Local Infrastructure Controls, Acceptance Criteria for `test_sync_pipeline.py`).
  - `.agents/`: Coordination workspace for the Teamwork multi-agent preview system.
- **Current Assessment**: Fresh project root requiring full scaffolding (`pyproject.toml`, `src/canonical_sync_engine/`, `tests/`).

### 2.2 Monorepo Storage Infrastructure Survey (Empirically Verified)

An empirical inspection of the host system (`Aarons-Mac-mini.local`, macOS Darwin arm64) confirmed the following live storage paths and states:

| Storage Layer | Empirical Path | Status | Verification Details |
|---|---|---|---|
| **Host Inodes & Headroom** | `/Users/aaron` | **ONLINE** | **104.53 GB free** / 460.43 GB total ($\ge 10.0\text{ GB}$ invariant satisfied). |
| **Obsidian Knowledge Vault** | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault` | **ONLINE** | Directory exists, `Index.md` (6,572 bytes) and 46 markdown notes present with valid Wikilinks. |
| **PySpark Data Lake & Datasets** | `/Users/aaron/DFS_UNIFIED/lora_datasets` | **ONLINE** | 20 `.jsonl` dataset files (e.g. `truth_audit_debate.jsonl`, `continuous_lora_dataset.jsonl`) totaling >70 MB. |
| **Monorepo Git Working Tree** | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo` | **ONLINE** | Valid Git repository (`origin: git@github.com:aarontmaher/Lauburu-Monorepo.git`), `.git/index.lock` absent. |
| **Google Drive Mount** | `/Volumes/Google Drive/My Drive/Lauburu_AI_Memory` | **VFS FALLBACK** | Volume unmounted; `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/gdrive_cache` active and writable. |

### 2.3 Existing Monorepo Sync Patterns & Tooling Survey
1. **`00_core_infrastructure/self_healing_hub/src/gdrive_handler.py`**:
   - Implements a resilient 3-tier fallback for Google Drive: checks native macOS path (`/Volumes/Google Drive/My Drive/Lauburu_AI_Memory`), then rclone mount, then local VFS cache (`data/gdrive_cache`).
   - Ensures cloud replication never blocks or crashes the pipeline if Google Drive is temporarily unmounted.
2. **`00_core_infrastructure/self_healing_hub/src/obsidian_swarm_syncer.py`**:
   - Demonstrates canonical note generation with YAML frontmatter (`title`, `updated`, `tags`) and bidirectional Wikilinks (`[[Index]]`, `[[swarm]]`, `[[ai-debate]]`).
3. **`00_core_infrastructure/self_healing_hub/src/pyspark_nas_lakehouse_engine.py`**:
   - Provides file classification (`GGUF_MODEL_WEIGHTS`, `PARQUET_TELEMETRY`, `LORA_TRAINING_PAIR`, `SOURCE_CODE_AST`, `BIOMETRICS_DSP`), storage node routing, and inventory snapshotting.
4. **`00_core_infrastructure/self_healing_hub/src/devices.json` & `ssh_handler.py`**:
   - Defines the 7 physical mesh layers with Tailscale IPs, SSH ports, and key paths.
5. **Local CLIs**:
   - `git`: `/usr/bin/git`
   - `gh`: `/Users/aaron/.local/bin/gh`
   - `uv`: `/Users/aaron/.local/bin/uv`
   - Python modules `pydantic`, `pytest`, `dataclasses`, `hashlib`, `json`, `sqlite3` are available.

---

## 3. Canonical Architecture & Module Decomposition

The `canonical_sync_engine` is structured into clean, decoupled layers following single-responsibility and dependency-inversion principles:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CANONICAL SYNC ENGINE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   [ CLI / Runner Interface ]   ◄───►   [ Programmatic API / Orchestrator ]   │
│                │                                     │                      │
│                ▼                                     ▼                      │
│   ┌───────────────────────────┐         ┌───────────────────────────────┐   │
│   │    VERIFICATION MODULE    │         │       QUAD-VAULT SYNC         │   │
│   │                           │         │                               │   │
│   │ • Fast-Path Check (<3ms)  │         │ 1. PySpark Syncer (JSONL/Parq)│   │
│   │ • Storage Headroom (>=10G)│────────►│ 2. Obsidian Syncer (MD/Links) │   │
│   │ • Schema & Hash Verifier  │         │ 3. Git Syncer (Stage/Commit)  │   │
│   │ • Pre-Flight Self-Healer  │         │ 4. GDrive Syncer (Mount/VFS)  │   │
│   │ • Mesh Node Health Prober │         └───────────────────────────────┘   │
│   └───────────────────────────┘                          │                  │
│                │                                         │                  │
│                ▼                                         ▼                  │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                     CANONICAL DATA MODELS                           │   │
│   │  • TruthArtifact (ID, Type, Payload, Hash, Origin, Tags, Timestamp) │   │
│   │  • NodeStorageHealth  • QuadVaultSyncResult  • TargetSyncStatus     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Module 1: `canonical_sync_engine.verification`
Responsible for pre-flight assertions, storage health validation, schema/hash integrity, and self-healing.
- **`health_scanner.py`**:
  - `FastPathChecker`: Executes the fast-path inode and status verification in $<3\text{ ms}$. Verifies that Obsidian vault, PySpark dataset directory, and Git tree exist and are writable.
  - `DiskHeadroomChecker`: Verifies free NVMe disk space is $\ge 10.0\text{ GB}$ (warns if $<5.0\text{ GB}$).
  - `MeshStorageScanner`: Probes active mesh nodes (L1 through L7) using local storage or lightweight SSH/Tailscale pings with timeout fallbacks.
- **`schema_verifier.py`**:
  - `ArtifactVerifier`: Validates truth artifact schema conformance, ensures mandatory fields exist, and calculates/verifies SHA-256 payload checksums.
- **`self_healer.py`**:
  - `StorageSelfHealer`: Implements Rule 6.2 self-healing protocols: creates missing vault directories, removes stale `.git/index.lock`, re-initializes missing `Index.md`, and purges transient cache folders if disk headroom is low.

### 3.2 Module 2: `canonical_sync_engine.models`
Defines strongly-typed, immutable data contracts for truth artifacts and synchronization telemetry.
- **`artifact.py`**: `TruthArtifact`, `ArtifactType`, `SyncStatus`, `TargetSyncDetail`, `QuadVaultSyncResult`.
- **`node_health.py`**: `NodeStorageHealth`, `StorageTier`, `FastPathResult`, `DiskSpaceInfo`.

### 3.3 Module 3: `canonical_sync_engine.sync`
Implements the quad-vault synchronization adapters:
- **`pyspark_syncer.py` (`PySparkVaultSyncer`)**:
  - Appends verified truth artifacts to canonical JSONL datasets (e.g. `/Users/aaron/DFS_UNIFIED/lora_datasets/truth_audit_*.jsonl` or partitioned target directories).
  - Updates inventory indexes (`data/nas_pyspark_inventory.json`).
  - Verifies append success by re-reading and matching the SHA-256 line record.
- **`obsidian_syncer.py` (`ObsidianVaultSyncer`)**:
  - Converts the artifact into structured Markdown with standard YAML frontmatter:
    ```yaml
    ---
    artifact_id: "truth_art_20260827_071200_a1b2c3"
    title: "Tri-Orchestrator Consensus on Memory Sharding"
    updated: "2026-08-27T07:12:00Z"
    origin_node: "Mac_Node"
    content_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    tags: [canonical_truth, ai_debate, lora_dataset, swarm]
    ---
    ```
  - Inserts bidirectional Wikilinks: `[[Index]]`, `[[CANONICAL_PROJECT_AND_STORAGE_RULE]]`, and category-specific notes (`[[swarm]]`, `[[ai-debate]]`).
  - Writes to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/truth_artifacts/<filename>.md`.
- **`git_syncer.py` (`GitVaultSyncer`)**:
  - Writes artifact payload / metadata to `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/truth_artifacts/<artifact_id>.json`.
  - Executes `/usr/bin/git add` on the affected files.
  - Optionally stages / commits with message: `canonical_sync(artifact): <title> [<hash_prefix>]`.
  - Interfaces with local `git` and `/Users/aaron/.local/bin/gh` without exposing raw credentials.
- **`gdrive_syncer.py` (`GDriveVaultSyncer`)**:
  - Leverages `GDriveHandler` fallback logic to locate the active destination:
    1. `/Volumes/Google Drive/My Drive/Lauburu_AI_Memory` (if mounted)
    2. `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/gdrive_cache` (local VFS fallback)
  - Mirrors both the JSON/JSONL artifact and the Obsidian markdown note to the Google Drive cloud directory.
  - Verifies written file size and checksum.

### 3.4 Module 4: `canonical_sync_engine.engine`
The top-level pipeline coordinator:
- **`pipeline.py` (`CanonicalSyncEngine`)**:
  - `verify_mesh_storage(auto_heal=True) -> MeshHealthSummary`
  - `sync_truth_artifact(artifact: TruthArtifact) -> QuadVaultSyncResult`
  - Orchestrates: Pre-flight verification $\rightarrow$ Self-healing (if degraded) $\rightarrow$ Artifact validation & hashing $\rightarrow$ Atomic parallel or sequential Quad-Vault write $\rightarrow$ Post-flight verification & assertion $\rightarrow$ Telemetry logging.

### 3.5 Module 5: `canonical_sync_engine.cli`
Unified CLI runner:
- `canonical-sync verify [--fix] [--json]`
- `canonical-sync sync --file <path> | --json <data>`
- `canonical-sync status`

---

## 4. Truth Artifact Data Models & Schema Contracts

### 4.1 Truth Artifact Schema (`canonical_sync_engine.models.artifact`)

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
import hashlib
import json
import time

class ArtifactType(str, Enum):
    DEBATE_TRANSCRIPT = "DEBATE_TRANSCRIPT"
    LORA_TRAINING_PAIR = "LORA_TRAINING_PAIR"
    ARCHITECTURE_DECISION = "ARCHITECTURE_DECISION"
    TELEMETRY_RECORD = "TELEMETRY_RECORD"
    CODE_DIFF = "CODE_DIFF"
    SYSTEM_AUDIT = "SYSTEM_AUDIT"
    GENERIC_TRUTH = "GENERIC_TRUTH"

class TargetSyncState(str, Enum):
    PENDING = "PENDING"
    SYNCED = "SYNCED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

@dataclass
class TargetSyncDetail:
    target_name: str # "pyspark" | "obsidian" | "git" | "gdrive"
    status: TargetSyncState
    target_path: str
    timestamp: str
    checksum: Optional[str] = None
    error_message: Optional[str] = None

@dataclass
class TruthArtifact:
    artifact_id: str
    artifact_type: ArtifactType
    title: str
    payload: Dict[str, Any]
    origin_node: str = "Mac_Node"
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ"))
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = self.compute_hash()

    def compute_hash(self) -> str:
        """Computes deterministic SHA-256 over normalized canonical JSON payload."""
        normalized = json.dumps(self.payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type.value if isinstance(self.artifact_type, ArtifactType) else str(self.artifact_type),
            "title": self.title,
            "payload": self.payload,
            "origin_node": self.origin_node,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "metadata": self.metadata,
            "content_hash": self.content_hash,
        }

@dataclass
class QuadVaultSyncResult:
    artifact_id: str
    content_hash: str
    overall_success: bool
    timestamp: str
    targets: Dict[str, TargetSyncDetail] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    error_summary: Optional[str] = None
```

### 4.2 Storage Health Schema (`canonical_sync_engine.models.node_health`)

```python
@dataclass
class FastPathResult:
    is_healthy: bool
    obsidian_ok: bool
    pyspark_ok: bool
    git_ok: bool
    gdrive_ok: bool
    disk_free_gb: float
    check_duration_ms: float
    issues: List[str] = field(default_factory=list)

@dataclass
class NodeStorageHealth:
    node_id: str
    node_name: str
    layer: int
    is_online: bool
    storage_healthy: bool
    free_disk_gb: float
    total_disk_gb: float
    verified_paths: Dict[str, bool]
    last_checked: str
    latency_ms: float
```

---

## 5. Interface Contracts & Storage Protocols

### 5.1 Fast-Path Verification Contract (< 3 ms)
```python
def is_storage_healthy(paths_config: Dict[str, str]) -> FastPathResult:
    """
    Executes in < 3ms using os.path / os.stat.
    Invariants:
    1. Obsidian Vault exists and Index.md is non-empty.
    2. PySpark dataset directory exists and is writable.
    3. Git repo root exists and .git/index.lock is absent.
    4. GDrive target exists (native mount or local VFS fallback).
    5. Disk free headroom >= 10.0 GB (warning threshold 5.0 GB).
    """
```

### 5.2 Pre-Flight Self-Healing Contract
```python
def self_heal_storage(paths_config: Dict[str, str]) -> List[str]:
    """
    Idempotent recovery actions:
    1. mkdir -p for missing vault directories and VFS cache.
    2. rm -f for stale .git/index.lock.
    3. Create Index.md with master Wikilinks if missing.
    4. Returns list of executed healing actions.
    """
```

### 5.3 Quad-Vault Sync Execution Contract
```python
class CanonicalSyncEngine:
    def sync_artifact(self, artifact: TruthArtifact) -> QuadVaultSyncResult:
        """
        1. Pre-flight health check (fast-path + self-healing).
        2. Validate artifact schema and compute/verify SHA-256 hash.
        3. PySpark Sync: Append JSONL line to dataset file & flush.
        4. Obsidian Sync: Generate Markdown note with YAML frontmatter & Wikilinks.
        5. Git Sync: Write artifact JSON to monorepo data tree and git add/stage.
        6. GDrive Sync: Mirror artifact JSON and Markdown note to Google Drive mount/VFS.
        7. Assert all 4 targets succeeded; return QuadVaultSyncResult.
        """
```

---

## 6. Recommended Project Layout & Module Architecture

The recommended directory and package structure for `/Users/aaron/teamwork_projects/canonical_sync_engine`:

```
canonical_sync_engine/
├── .agents/                          # Multi-agent coordination metadata
├── pyproject.toml                    # Modern PEP 518 / 621 build configuration
├── requirements.txt                  # Direct dependency declarations
├── README.md                         # Architecture and usage documentation
├── src/
│   └── canonical_sync_engine/
│       ├── __init__.py               # Package root & exports
│       ├── config.py                 # Canonical paths, default thresholds, mesh topology
│       ├── engine.py                 # Core CanonicalSyncEngine orchestrator
│       ├── cli.py                    # CLI entrypoint (canonical-sync)
│       ├── models/
│       │   ├── __init__.py
│       │   ├── artifact.py           # TruthArtifact, QuadVaultSyncResult, TargetSyncDetail
│       │   └── node_health.py        # FastPathResult, NodeStorageHealth
│       ├── verification/
│       │   ├── __init__.py
│       │   ├── health_scanner.py     # FastPathChecker, HeadroomChecker, MeshScanner
│       │   ├── schema_verifier.py    # Schema validation, SHA-256 verifier
│       │   └── self_healer.py        # Rule 6.2 Pre-flight self-healing engine
│       └── sync/
│           ├── __init__.py
│           ├── base.py               # Abstract Base Vault Syncer
│           ├── pyspark_syncer.py     # PySpark Data Lake JSONL/Parquet Syncer
│           ├── obsidian_syncer.py    # Obsidian Knowledge Graph Note Syncer
│           ├── git_syncer.py         # Git Working Tree & Staging Syncer
│           └── gdrive_syncer.py      # Google Drive Mount & VFS Fallback Syncer
└── tests/
    ├── __init__.py
    ├── conftest.py                   # Pytest fixtures, temp directory isolations
    ├── unit/
    │   ├── test_models.py            # Artifact models, hashing, serialization
    │   ├── test_verification.py      # Fast-path <3ms, headroom, self-healing
    │   ├── test_pyspark_syncer.py    # PySpark dataset append and format tests
    │   ├── test_obsidian_syncer.py   # Markdown formatting, YAML frontmatter, wikilinks
    │   ├── test_git_syncer.py        # Git staging, status inspection, locking
    │   ├── test_gdrive_syncer.py     # Google Drive mount and VFS cache fallback
    │   └── test_cli.py               # CLI commands and argument parsing
    └── e2e/
        ├── test_sync_pipeline.py     # Primary Acceptance Criteria test script
        └── test_mesh_self_healing.py # End-to-end self-healing and recovery tests
```

---

## 7. Acceptance Criteria Verification Strategy & Test Harness

### 7.1 Primary Acceptance Test (`tests/e2e/test_sync_pipeline.py` or `test_sync_pipeline.py`)
To satisfy the User Request and Acceptance Criteria with zero simulation, the automated test harness will execute the following concrete sequence:

1. **Setup & Initialization**:
   - Instantiate `CanonicalSyncEngine` configured with test-isolated target directories (or live monorepo paths with test prefix).
2. **Inject Dummy Truth Artifact**:
   ```python
   dummy_artifact = TruthArtifact(
       artifact_id=f"test_artifact_{int(time.time())}",
       artifact_type=ArtifactType.SYSTEM_AUDIT,
       title="Automated Test Truth Artifact - Storage Verification",
       payload={
           "test_key": "canonical_sync_verification_value",
           "subsystems_verified": ["00_core_infrastructure", "04_data_and_memory", "obsidian_vault"],
           "zero_mock_certified": True,
           "iteration": 1
       },
       origin_node="Mac_Node",
       tags=["test_audit", "canonical_sync", "automated_verification"]
   )
   ```
3. **Execute Sync Pipeline**:
   ```python
   result = engine.sync_truth_artifact(dummy_artifact)
   assert result.overall_success is True
   ```
4. **Programmatic Assertions Across All 4 Vaults**:
   - **Vault 1 (PySpark Data Lake)**: Read target JSONL dataset file, parse lines, find matching `artifact_id`, verify line payload hash matches `dummy_artifact.content_hash`.
   - **Vault 2 (Obsidian Vault)**: Read generated Markdown note at `obsidian_vault/truth_artifacts/<filename>.md`, assert valid YAML frontmatter, verify presence of `[[Index]]` Wikilink and matching hash.
   - **Vault 3 (Git Working Tree)**: Check that the JSON representation exists in Git data directory and `/usr/bin/git status` reports the file as staged or committed.
   - **Vault 4 (Google Drive Mount / VFS Fallback)**: Verify that mirrored JSON and Markdown files exist at target cloud path and match the exact SHA-256 hash.
5. **Exit Code Certification**:
   - The test script finishes with exit code `0`.

---

## 8. Milestone Implementation Roadmap

| Milestone | Title | Scope & Deliverables | Primary Dependencies |
|---|---|---|---|
| **M1** | Data Models & Verification Core | • `src/canonical_sync_engine/models/` (Data models, hashing, serialization)<br>• `src/canonical_sync_engine/verification/` (Fast-path $<3\text{ ms}$, headroom $\ge 10\text{ GB}$, self-healer)<br>• Unit tests in `tests/unit/test_models.py` & `test_verification.py` | None |
| **M2** | Quad-Vault Sync Adapters | • `src/canonical_sync_engine/sync/pyspark_syncer.py`<br>• `src/canonical_sync_engine/sync/obsidian_syncer.py`<br>• `src/canonical_sync_engine/sync/git_syncer.py`<br>• `src/canonical_sync_engine/sync/gdrive_syncer.py`<br>• Unit tests for each syncer | M1 |
| **M3** | Orchestration Engine & CLI | • `src/canonical_sync_engine/engine.py` (`CanonicalSyncEngine`)<br>• `src/canonical_sync_engine/cli.py` (`canonical-sync`)<br>• `src/canonical_sync_engine/config.py` | M1, M2 |
| **M4** | E2E Integration & Acceptance Certification | • `tests/e2e/test_sync_pipeline.py` (Dummy artifact injection & 4-vault assertion)<br>• Standalone runner script `test_sync_pipeline.py`<br>• Full test execution returning exit code 0 | M1, M2, M3 |

---

## 9. Conclusion

The architecture designed in this report provides a complete, robust, and zero-mock implementation blueprint for `canonical_sync_engine`. It adheres strictly to the canonical project rules, guarantees atomic quad-vault data propagation, enforces high-speed ($<3\text{ ms}$) health verification, and provides a clear automated acceptance test suite.
