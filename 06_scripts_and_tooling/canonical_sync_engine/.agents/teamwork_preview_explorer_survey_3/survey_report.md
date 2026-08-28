# Canonical Sync Engine — Comprehensive Specification Requirements & Test Criteria Report
**Document ID:** `CSE-SPEC-SURVEY-03`  
**Agent:** Survey 3 (Spec Miner & Test Criteria Explorer)  
**Working Directory:** `/Users/aaron/teamwork_projects/canonical_sync_engine/.agents/teamwork_preview_explorer_survey_3`  
**Target Project:** `/Users/aaron/teamwork_projects/canonical_sync_engine`  
**Timestamp:** `2026-08-27T07:14:00+10:00`  
**Status:** COMPLETE & VERIFIED  

---

## Executive Summary

This report establishes the **exhaustive functional specifications, architectural requirements, failure mode taxonomy, edge-case mitigation matrix, and 4-tier E2E testing methodology** for the **Canonical Sync Engine (`canonical_sync_engine`)**. 

The engine enforces the Canonical Tri-Vault / Quad-Vault Storage Architecture across the 7-layer physical mesh network (L1–L7 + Gateway), providing:
1. **R1: Mesh Storage Verification:** Dynamic node reachability, disk headroom enforcement ($\ge 10.0\text{ GB}$ free), vault health assertion (`Index.md` Wikilinks, JSONL dataset integrity, Git lock detection), and SHA-256 cryptographic verification.
2. **R2: Quad-Vault Synchronization:** Format translation and atomic multi-target replication across PySpark (Data Lake JSONL/Parquet), Obsidian (Markdown AST with YAML frontmatter & Wikilinks), GitHub (Git repository tree & commit tracking), and Google Drive (Cloud Mirror Backup & cache staging).
3. **R3: Infrastructure Controls:** Zero raw API key exposure, leveraging native authenticated CLIs (`gh`, `git`), local OS mountpoints (`/Volumes/Google Drive/My Drive`), atomic file renaming (`os.replace`), and graceful offline queue fallback.
4. **4-Tier E2E Test Strategy:** Complete test harness culminating in `test_sync_pipeline.py` which injects a dummy truth artifact and programmatically asserts flawless propagation across all 4 vault targets with return code `0`.

---

## 1. Requirement 1 (R1): Mesh Storage Verification

### 1.1 Mesh Node Discovery & Inventory Specification

The storage verification module must maintain a deterministic registry of all physical mesh layers, their network interfaces, dynamic RAM governance caps, and storage roles.

| Layer | Node Identifier | Hostname / IP | Tailscale Mesh IP | Thunderbolt 4 Direct | RAM / AI Cap | Governed Dynamic Cap | Primary Storage Role |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L1** | `Mac_Node` | `192.168.8.230` | `100.119.199.76` | `169.254.187.1` | 24.0 GB (21.6 GB AI) | 90% Host RAM | Primary Host, DFS Root, Obsidian Vault Core |
| **L2** | `MacBook_Pro` | `192.168.8.127` | `100.103.212.21` | `169.254.187.138` | 16.0 GB (14.0 GB AI) | 90% Host RAM | High-Speed NVMe Storage Vault, GGUF Vault |
| **L3** | `Linux_Head_Node` | `192.168.8.224` | `100.101.39.98` | N/A | 16.0 GB (13.8 GB AI) | 80% Host RAM | Docker Hub, Remote DFS Mirror, PySpark Worker |
| **L4** | `Linux_Tablet` | DHCP | `100.81.92.125` | N/A | 8.0 GB (6.5 GB AI) | 75% Host RAM | Mobile Secondary Store, Edge Node |
| **L5** | `MacBook_Air` | `192.168.8.222` | `100.93.158.96` | N/A | 16.0 GB (14.0 GB AI) | 90% Host RAM | LoRA Memory Distillation Worker |
| **L6** | `Pixel_10_Pro_XL` | DHCP | `100.73.38.87` | N/A | 16.0 GB (12.5 GB AI) | 85% Host RAM | Termux Local Cache, Edge Storage |
| **L7** | `Samsung_S20` | DHCP | `100.84.40.95` / `100.99.123.58` | N/A | 12.0 GB (9.0 GB AI) | 75% Host RAM | OpenClaw UI Test Artifact Cache |
| **GW** | `GL.iNet Gateway` | `192.168.8.1` | `100.122.185.123` | N/A | Embedded | Embedded | Hardware Gateway, USB ADB Hub |

#### Probing & Discovery Protocol:
- **Fast-Path Reachability Probe:** Non-blocking TCP socket connect / ICMP ping (timeout $\le 500\text{ ms}$).
- **Multi-Transport Fallback Routing:**
  1. *Primary LAN Route:* `192.168.8.x`
  2. *Ultra-Low-Latency Bridge (L1 ↔ L2):* Thunderbolt 4 DMA (`169.254.187.x`, RTT $0.27\text{ ms}$)
  3. *Zero-Trust Mesh Overlay:* Tailscale WireGuard (`100.x.y.z`)
- **Inventory Health Output:** The probe must output a structured `MeshInventoryReport` dataclass recording node state (`ONLINE`, `DEGRADED`, `OFFLINE`), transport latency, and reachable storage mounts.

---

### 1.2 Disk Headroom & Capacity Enforcement Requirements

Storage verification must measure volume-level capacity and inode availability on all target volumes prior to synchronization.

```
Free Disk Space (GB)
┌────────────────────────────────────────────────────────────────────────┐
│  CRITICAL (< 5.0 GB)  │  DEGRADED (5.0 - 10.0 GB)  │  HEALTHY (>= 10.0 GB)  │
│  Halt Non-Critical    │  Warning Issued            │  Full Sync Operations │
│  Trigger Self-Healing │  Execute Normal Sync       │  Certified Optimal    │
└────────────────────────────────────────────────────────────────────────┘
```

#### Detailed Headroom Invariants:
1. **Host NVMe / Primary DFS Volume (`/Users/aaron` / `/Users/aaron/DFS_UNIFIED`):**
   - Must maintain **$\ge 10.0\text{ GB}$ free disk headroom** (`shutil.disk_usage().free >= 10 * 1024**3`).
   - Free space between $5.0\text{ GB}$ and $10.0\text{ GB}$ issues a `WARN_HEADROOM_DEGRADED` event.
   - Free space $< 5.0\text{ GB}$ issues a `ERR_HEADROOM_CRITICAL` exception and activates automated cache purging (purging `__pycache__`, `.pytest_cache`, and stale logs $> 7$ days per RULE 6.2).
2. **Remote DFS Mounts (`/mnt/dfs_unified` on L2/L3):**
   - Must maintain $\ge 10.0\text{ GB}$ free disk headroom over NFS/SSHFS/SeaweedFS.
3. **Inode Availability:**
   - Inode free percentage (`f_favail / f_files`) must be $\ge 10\%$.

---

### 1.3 Vault Health Criteria & Pre-Flight Invariants

Each of the 4 vaults has strict health criteria that must be verified before and during execution:

#### A. Obsidian Knowledge Vault
- **Path:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/`
- **Health Invariants:**
  1. Directory exists with filesystem permissions `0755` (directory) / `0644` (notes).
  2. `Index.md` exists and is non-empty ($> 0\text{ bytes}$).
  3. `Index.md` contains mandatory master Wikilinks:
     - `[[Index]]`
     - `[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]`
     - `[[CANONICAL_PROJECT_AND_STORAGE_RULE]]`
  4. Environment variable `OBSIDIAN_VAULT_PATH` resolves to `/Users/aaron/DFS_UNIFIED`.

#### B. PySpark & Big Data Lake
- **Paths:** `/Users/aaron/DFS_UNIFIED/lora_datasets/` and `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/`
- **Health Invariants:**
  1. Target dataset directories exist and are writable (`os.access(path, os.W_OK)`).
  2. Master JSONL datasets (`truth_audit_*.jsonl`, `ui_ux_improvements.jsonl`) maintain valid line-delimited JSON syntax without line corruption.
  3. Qdrant Vector DB port (`127.0.0.1:6333`) or local embedded storage path is accessible.

#### C. GitHub Working Tree & Repository
- **Path:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo`
- **Health Invariants:**
  1. Valid Git tree: `git rev-parse --is-inside-work-tree` returns exit code 0.
  2. Stale Git lock absence: File `.git/index.lock` is ABSENT.
     - *Self-Healing:* If `.git/index.lock` exists and process is defunct/stale ($> 10\text{ min}$ old), auto-clear per RULE 6.2.
  3. Clean merge state: Zero unmerged git conflict markers (`<<<<<<< HEAD`, `=======`, `>>>>>>>`).

#### D. Google Drive Cloud Mirror
- **Path:** `/Volumes/Google Drive/My Drive/Lauburu_AI_Memory/lora_datasets/`
- **Health Invariants:**
  1. Volume mount check: Verify `/Volumes/Google Drive/My Drive` is mounted and accessible.
  2. Writable mirror directory: Target backup subdirectory exists or can be created.
  3. Local fallback cache ready: Fallback path `~/.lauburu_cloud_cache/` exists and is writable if unmounted.

---

### 1.4 Cryptographic Hashing & Schema Verification

1. **SHA-256 Parity Audit:**
   - Artifact payloads must be hashed using `hashlib.sha256(payload_bytes).hexdigest()`.
   - Streaming hash calculation for files $> 1\text{ MB}$ using $1\text{ MB}$ buffer chunks.
   - Verification engine compares hashes across all vault representations to guarantee zero bit rot or transformation distortion.
2. **Schema Invariant Rules:**
   - All structured artifacts must strictly adhere to the `CanonicalTruthArtifact` schema definition (detailed in Section 2.1).

---

## 2. Requirement 2 (R2): Quad-Vault Synchronization

### 2.1 Canonical Truth Artifact Intermediate Representation (IR)

The synchronization engine ingests an abstract, format-agnostic data model:

```python
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import datetime
import hashlib
import json

@dataclass
class CanonicalTruthArtifact:
    artifact_id: str                          # Unique ID, e.g. "truth-20260827-071500-a1b2"
    title: str                                # Human-readable title
    category: str                             # Subsystem/category, e.g. "04_data_and_memory"
    source_node: str                          # Originating node, e.g. "L1_Mac_Node"
    content: str                              # Primary text/code/body content
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    schema_version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    sha256_hash: Optional[str] = None

    def compute_hash(self) -> str:
        payload = f"{self.artifact_id}|{self.timestamp}|{self.title}|{self.content}"
        self.sha256_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return self.sha256_hash
```

---

### 2.2 Format Translation & Propagation Pipeline

```
                              ┌──────────────────────────────┐
                              │    CANONICAL TRUTH ARTIFACT  │
                              │    (Standardized Python IR)  │
                              └──────────────┬───────────────┘
                                             │
               ┌─────────────────────────────┼────────────────────────────┐
               │                             │                            │
               ▼                             ▼                            ▼
     ┌──────────────────┐          ┌──────────────────┐         ┌──────────────────┐
     │ 1. PySpark Vault │          │2. Obsidian Vault │         │ 3. GitHub Vault  │
     │  (Data Lake)     │          │ (Knowledge Graph)│         │  (Source Code)   │
     └─────────┬────────┘          └─────────┬────────┘         └─────────┬────────┘
               │ JSONL Record                │ Markdown Note              │ Structured JSON/
               │ Flat Schema                 │ YAML Frontmatter           │ Git Tree Commit
               │ Append / Upsert             │ Master Wikilinks           │ Clean Working Tree
               │                             │                            │
               └─────────────────────────────┼────────────────────────────┘
                                             │
                                             ▼
                                   ┌──────────────────┐
                                   │ 4. Google Drive  │
                                   │  (Cloud Backup)  │
                                   └─────────┬────────┘
                                             │ Exact Cloud Mirror /
                                             │ Local Cache Staging Fallback
                                             │ SHA-256 Parity
```

#### Destination 1: PySpark Data Lake
- **Target File:** `/Users/aaron/DFS_UNIFIED/lora_datasets/truth_audit_master.jsonl` (and daily partitioned JSONL).
- **Transformation Format:** Line-delimited JSON (JSONL). Each row represents a single atomic, complete JSON object.
- **Output Record Schema:**
  ```json
  {
    "id": "truth-20260827-071500-a1b2",
    "timestamp": "2026-08-27T07:15:00Z",
    "source_node": "L1_Mac_Node",
    "category": "04_data_and_memory",
    "title": "Mesh Sync Health Certification",
    "content": "Canonical verification completed across 7 layers.",
    "tags": ["mesh", "storage", "sync", "canonical"],
    "sha256": "3a7b9c1d2e...",
    "metadata": {
      "verified_by": "canonical_sync_engine",
      "schema_version": "1.0.0"
    }
  }
  ```
- **Write Mechanism:** Thread-safe, atomic append (`open(path, 'a', encoding='utf-8')`) with trailing newline `\n` and flush.

#### Destination 2: Obsidian Knowledge Vault
- **Target File:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/04_data_and_memory/<artifact_id>.md`
- **Transformation Format:** Markdown file (`.md`) formatted with strict YAML frontmatter, master Wikilinks, and structured Markdown sections.
- **Output Note Layout:**
  ```markdown
  ---
  title: "Mesh Sync Health Certification"
  artifact_id: "truth-20260827-071500-a1b2"
  timestamp: "2026-08-27T07:15:00Z"
  source_node: "L1_Mac_Node"
  category: "04_data_and_memory"
  sha256: "3a7b9c1d2e..."
  tags:
    - mesh
    - storage
    - sync
    - canonical
  verified: true
  ---

  # 🧠 Mesh Sync Health Certification

  ## Master Navigation & Wikilinks
  - [[Index]]
  - [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
  - [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
  - [[04_data_and_memory]]

  ## Artifact Content
  Canonical verification completed across 7 layers.

  ## Cryptographic & Audit Metadata
  - **Artifact ID:** `truth-20260827-071500-a1b2`
  - **Source Node:** `L1_Mac_Node`
  - **SHA-256:** `3a7b9c1d2e...`
  - **Sync Engine:** `canonical_sync_engine v1.0`
  ```

#### Destination 3: GitHub Working Tree
- **Target File:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/core_data/<artifact_id>.json`
- **Transformation Format:** Pretty-printed structured JSON (indent=2, utf-8, sorted keys).
- **Git Operations:**
  1. Verify `.git/index.lock` is not present.
  2. Write JSON artifact to designated subsystem directory.
  3. Execute `git add <relative_path>` using `subprocess.run(["git", "add", ...])`.
  4. Record staging status in synchronization audit ledger. (Optional auto-commit flag with `feat(sync): persist <artifact_id>`).

#### Destination 4: Google Drive (Cloud Mirror Backup)
- **Target File:** `/Volumes/Google Drive/My Drive/Lauburu_AI_Memory/lora_datasets/<artifact_id>.json`
- **Transformation Format:** Mirrored JSON artifact identical in content and SHA-256 hash to GitHub / PySpark representation.
- **Fail-Safe Fallback:** If `/Volumes/Google Drive/My Drive` is unmounted:
  - Write file to local cloud staging cache: `/Users/aaron/DFS_UNIFIED/cloud_backup_cache/<artifact_id>.json` (or `~/.lauburu_cloud_cache/<artifact_id>.json`).
  - Append to pending upload journal: `/Users/aaron/DFS_UNIFIED/cloud_backup_cache/pending_sync.jsonl`.
  - Issue non-fatal warning status `STATUS_GDRIVE_OFFLINE_QUEUED`.

---

## 3. Requirement 3 (R3): Infrastructure Controls & Safeguards

### 3.1 Credential Safety & Zero-Leakage Invariant
1. **No Embedded API Keys or Secrets:**
   - Under no circumstances shall Google OAuth tokens, service account JSON private keys, GitHub Personal Access Tokens (PATs), or SSH private keys be hardcoded in code, scripts, configs, or test files.
2. **Leverage Local OS & CLI Authentication:**
   - **GitHub Integration:** Relies on local pre-authenticated `gh` CLI (`gh auth status`) or standard `git` over local SSH agent (`~/.ssh/id_ed25519` / `~/.ssh/id_rsa`).
   - **Google Drive Integration:** Relies on native macOS volume mount provided by Google Drive for Desktop (`/Volumes/Google Drive/My Drive/`) or local token keyring via `gdrive_handler.py`.

---

### 3.2 Fail-Safe Fallbacks & Graceful Degradation Matrix

| Trigger / Failure Event | Detected Condition | Immediate Automated Action | Fallback State | Logging & Recovery |
| :--- | :--- | :--- | :--- | :--- |
| **Google Drive Unmounted** | `/Volumes/Google Drive` does not exist or `os.path.isdir()` is False | Divert write to local cache (`~/.lauburu_cloud_cache/`) | `DEGRADED_LOCAL_CACHE` | Record in `pending_sync.jsonl`; retry automatically when mount reappears. |
| **Stale Git Index Lock** | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.git/index.lock` present | Check lock modification time. If age $> 10\text{ min}$ and git process dead, remove lock. | `SELF_HEALED_LOCK` | Log warning `W_GIT_LOCK_PURGED`; proceed with staging. |
| **Low Disk Headroom** | Free disk space on target volume $< 10.0\text{ GB}$ | If $< 5.0\text{ GB}$, purge `__pycache__`, `.pytest_cache`, stale logs. If still $< 5.0\text{ GB}$, halt writes. | `HEADROOM_WARNING` / `CRITICAL_HALT` | Raise `InsufficientHeadroomException` with bytes free details. |
| **Corrupt / Missing `Index.md`** | `Index.md` missing or empty | Re-instantiate canonical `Index.md` with master Wikilinks per Rule 6.2. | `SELF_HEALED_INDEX` | Log `W_INDEX_REGENERATED`; proceed with note linking. |
| **Remote Mesh Node Offline** | Ping/TCP socket to remote node (L2–L7) times out | Mark remote node `OFFLINE` in memory registry; complete all local quad-vault operations. | `PARTIAL_MESH_SYNC` | Queue remote delta to `remote_sync_queue.jsonl` for WoL resurrection. |
| **Corrupt Payload Ingestion** | Missing required fields or schema mismatch | Reject artifact before disk write; raise `InvalidArtifactSchemaException`. | `REJECTED_INPUT` | Return structured validation errors with line/field details. |

---

### 3.3 Atomic File Operations & Collision Safety

To guarantee zero partial writes, corrupted states, or cross-process race conditions:
1. **Write-Then-Rename Atomic Pattern:**
   - All files must be written to a temporary sibling file: `<target_path>.tmp.<pid>_<timestamp>`.
   - Flush file buffer: `f.flush(); os.fsync(f.fileno())`.
   - Atomic rename via `os.replace(temp_path, target_path)`.
2. **Thread & Process Concurrency:**
   - Python `threading.Lock` / inter-process file locks (`fcntl.flock` on Unix) on JSONL append operations.

---

## 4. Acceptance Criteria & 4-Tier E2E Testing Strategy

### 4.1 Testing Methodology Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       4-TIER E2E TESTING FRAMEWORK                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 1: UNIT & FEATURE COVERAGE                                             │
│ • Component isolation: Node discovery, disk headroom checker, format        │
│   converters (IR -> JSONL/MD/JSON), SHA-256 calculator, git lock detector. │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 2: BOUNDARY & ERROR RESILIENCE                                         │
│ • Failure injection: Disk full simulation, corrupt Index.md, stale lock     │
│   collision, unmounted Google Drive volume, invalid schema payloads.        │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 3: CROSS-VAULT DATA CONSISTENCY                                        │
│ • Multi-vault consistency: SHA-256 hash preservation across all 4 targets,  │
│   idempotent sync execution, Wikilink graph resolvability.                  │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 4: REAL-WORLD WORKLOAD E2E PIPELINE (`test_sync_pipeline.py`)          │
│ • Full lifecycle: Inject dummy Truth Artifact -> Run Pipeline -> Program-   │
│   matically assert verified propagation to all 4 destinations (Exit 0).     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 4.2 Tier 1: Unit & Feature Test Specifications

| Test Case ID | Test Target Component | Input Conditions | Expected Outcome |
| :--- | :--- | :--- | :--- |
| `TC-T1-01` | `MeshNodeRegistry` | 7-layer node definitions | Correct IP resolution, dynamic cap lookup, and reachability socket probe. |
| `TC-T1-02` | `HeadroomValidator` | Mock statvfs: 25.0 GB free vs 4.0 GB free | Returns `HEALTHY` for 25.0 GB, `CRITICAL` for 4.0 GB. |
| `TC-T1-03` | `ObsidianVaultValidator` | Vault directory with valid `Index.md` & Wikilinks | Returns `True` (Valid); identifies missing Wikilinks when stripped. |
| `TC-T1-04` | `PySparkFormatter` | `CanonicalTruthArtifact` instance | Generates single-line JSON with all schema keys and trailing `\n`. |
| `TC-T1-05` | `ObsidianFormatter` | `CanonicalTruthArtifact` instance | Generates valid YAML frontmatter + `[[Index]]` master Wikilinks. |
| `TC-T1-06` | `GitLockDetector` | Mock `.git/index.lock` file | Identifies lock presence, measures lock age, triggers safe cleanup if stale. |
| `TC-T1-07` | `CryptographicHasher` | String/bytes payload | Produces byte-exact SHA-256 matching `hashlib.sha256`. |

---

### 4.3 Tier 2: Boundary, Edge Case & Error Resilience Specifications

| Test Case ID | Injected Fault / Boundary Condition | Expected Engine Behavior | Assertion Criteria |
| :--- | :--- | :--- | :--- |
| `TC-T2-01` | **Unmounted Google Drive:** `/Volumes/Google Drive` missing | Diverts backup to local fallback cache directory (`~/.lauburu_cloud_cache/`) | File exists in fallback cache, `pending_sync.jsonl` updated, no unhandled exception. |
| `TC-T2-02` | **Stale Git Lock:** Dummy `.git/index.lock` created with mtime 15 min ago | Detects stale lock and automatically removes it prior to staging | `.git/index.lock` removed; `git add` succeeds. |
| `TC-T2-03` | **Missing / Blank `Index.md`:** `Index.md` deleted | Automatically self-heals `Index.md` with canonical header and master Wikilinks | `Index.md` created with `[[Index]]`, `[[CANONICAL_PROJECT_AND_STORAGE_RULE]]`. |
| `TC-T2-04` | **Special Characters & Emojis:** Title containing quotes, emojis, multiline code | Correctly escapes YAML frontmatter without parser syntax error | `yaml.safe_load(frontmatter)` succeeds without parser error. |
| `TC-T2-05` | **Malformed Artifact Payload:** Missing `artifact_id` or `content` | Rejects artifact immediately during pre-sync validation | Raises `SchemaValidationError` with specific error message. |
| `TC-T2-06` | **Zero Byte / Corrupted JSONL Line:** Appended truncated line | JSONL reader skips or reports corrupt line without crashing parser | Validation parser flags corrupt line; engine recovers. |

---

### 4.4 Tier 3: Cross-Vault Interactions & Data Consistency Specifications

| Test Case ID | Test Scenario | Verification Mechanism | Success Criteria |
| :--- | :--- | :--- | :--- |
| `TC-T3-01` | **SHA-256 Parity Across All 4 Targets** | Extract payload hash from PySpark JSONL, Obsidian frontmatter, GitHub JSON, and GDrive backup | All 4 computed hashes match `artifact.sha256_hash` exactly. |
| `TC-T3-02` | **Sync Idempotency** | Ingest identical artifact twice | Does not duplicate Obsidian note or produce conflicting git states; returns `ALREADY_SYNCED`. |
| `TC-T3-03` | **Wikilink Graph Resolvability** | Scan generated Obsidian Markdown note for Wikilinks regex `\[\[(.*?)\]\]` | All target referenced notes exist in `obsidian_vault/` or master index. |
| `TC-T3-04` | **Atomic Rollback on Storage Failure** | Simulate disk write error midway through 4-vault loop | Clean up temporary `.tmp` files; emit rollback audit record in sync journal. |

---

### 4.5 Tier 4: Real-World Workload Pipeline Test (`test_sync_pipeline.py`)

#### Pipeline Workflow Definition:
```
[1. SETUP] Injects Dummy Truth Artifact (ID: "dummy-truth-<uuid>")
     │
[2. AUDIT] Executes Mesh Storage Pre-Flight Verification (R1)
     │       ├── Probes L1-L7 nodes & checks disk headroom (>= 10 GB)
     │       └── Validates Obsidian Index.md, PySpark paths, Git lock state
     │
[3. TRANSFORM] Executes Multi-Target Format Translation (R2)
     │       ├── Formats PySpark JSONL record
     │       ├── Formats Obsidian Markdown note with YAML & Wikilinks
     │       ├── Formats GitHub structured JSON artifact
     │       └── Formats Google Drive cloud mirror payload
     │
[4. SYNC] Propagates to All 4 Vault Destinations (R2 + R3)
     │       ├── Writes to PySpark Data Lake (/Users/aaron/DFS_UNIFIED/lora_datasets/)
     │       ├── Writes to Obsidian Vault (/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/)
     │       ├── Writes to Git Tree (/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/)
     │       └── Writes to Google Drive Mount (/Volumes/Google Drive/...) or Cloud Cache
     │
[5. ASSERT] Programmatic Integrity Verification
     │       ├── Assert PySpark JSONL contains valid record with matching SHA-256
     │       ├── Assert Obsidian Markdown note exists with valid YAML frontmatter & Wikilinks
     │       ├── Assert Git working tree contains staged/written JSON artifact
     │       ├── Assert Google Drive (or fallback cache) contains identical mirror file
     │       └── Assert Process Return Code is 0
     │
[6. CLEANUP] Idempotent teardown of test dummy artifacts (if in test mode)
```

#### Detailed Test Assertions Required in `test_sync_pipeline.py`:
1. `assert os.path.exists(pyspark_dest)` and JSONL parsing verifies `record["id"] == dummy_artifact.artifact_id` and `record["sha256"] == dummy_artifact.sha256_hash`.
2. `assert os.path.exists(obsidian_dest)` and note contents contain `---`, `title:`, `[[Index]]`, and `[[CANONICAL_PROJECT_AND_STORAGE_RULE]]`.
3. `assert os.path.exists(github_dest)` and JSON content equals dummy artifact payload.
4. `assert os.path.exists(gdrive_dest)` (or fallback cache path) and file SHA-256 equals `dummy_artifact.sha256_hash`.
5. `sys.exit(0)` on 100% assertion pass.

---

## 5. Architectural Recommendations & Directory Structure

To maintain modularity and zero-mock truth enforcement, the implementation of `canonical_sync_engine` should follow this component architecture:

```
canonical_sync_engine/
├── __init__.py
├── config.py                         # Canonical paths, node IPs, headroom thresholds
├── models/
│   ├── __init__.py
│   ├── artifact.py                   # CanonicalTruthArtifact IR dataclass
│   └── report.py                     # HealthReport & SyncResult models
├── verifier/
│   ├── __init__.py
│   ├── node_prober.py                # L1-L7 reachability & latency probing
│   ├── headroom_checker.py           # Inode & disk headroom checks (>=10GB)
│   ├── vault_health.py               # Obsidian Index.md, PySpark, Git lock validators
│   └── hash_audit.py                 # SHA-256 streaming & parity verifier
├── engine/
│   ├── __init__.py
│   ├── sync_coordinator.py           # Master 4-vault orchestration pipeline
│   ├── translators/
│   │   ├── pyspark_translator.py     # IR -> JSONL / Parquet schema converter
│   │   ├── obsidian_translator.py    # IR -> Markdown AST / Frontmatter converter
│   │   ├── git_translator.py         # IR -> Git tree structured JSON
│   │   └── gdrive_translator.py      # IR -> Google Drive cloud mirror payload
│   └── safeguards/
│       ├── lock_manager.py           # Atomic .tmp write & .git/index.lock handler
│       └── gdrive_fallback.py        # Offline cache queue & sync drainer
├── cli.py                            # CLI entrypoint (`agy` / terminal runner)
├── test_sync_pipeline.py             # Master Tier 4 Acceptance Test
└── tests/
    ├── test_tier1_unit.py            # Tier 1: Unit & format tests
    ├── test_tier2_boundary.py        # Tier 2: Fault injection & edge cases
    └── test_tier3_consistency.py     # Tier 3: SHA parity & idempotency
```

---

## 6. Conclusion

The specification requirements and test criteria defined above provide complete, airtight guidance for the design and implementation of `canonical_sync_engine`. All requirements from `ORIGINAL_REQUEST.md`, canonical global rules (`RULE[user_global]`), and monorepo architectural invariants have been formalized into verifiable criteria and test suites.
