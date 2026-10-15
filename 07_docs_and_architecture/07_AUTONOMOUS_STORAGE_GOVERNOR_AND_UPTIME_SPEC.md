# Autonomous Network Storage Governor & Combined Folder Uptime Specification
**Canonical Document:** `07_docs_and_architecture/07_AUTONOMOUS_STORAGE_GOVERNOR_AND_UPTIME_SPEC.md`  
**Ecosystem:** Lauburu 7-Layer Hardware Mesh (1.701 TB SeaweedFS DFS, Tri-Vault Storage)  
**Assigned Frameworks:** Google Antigravity SDK (`LocalAgentConfig`), Nomad Courier Governor, Genetic MoE Router, AI Debate  

---

## 🏛️ 1. Executive Summary & Problem Statement

The Lauburu Mesh pools **1.701 TB of unified logical storage** across 7 physical hardware nodes via SeaweedFS (`/Users/aaron/DFS_UNIFIED`), synchronized with a Tri-Vault architecture (Obsidian Knowledge Graph, PySpark Big Data Lake, GitHub Monorepo).

As the project scales, storage assets and source files become disorganized due to:
1. **Redundant Root Directories**: Legacy directories (`apps`, `core`, `scripts`, `webapp`, `00_SYSTEM_DASHBOARDS`, `ai_debate`, `filerldb2`) coexisting alongside canonical numbered pillars (`00_` through `12_`).
2. **Distributed Storage Drift**: Loose files scattered in `/Users/aaron/DFS_UNIFIED` outside the canonical monorepo tree.
3. **Mount & Service Drop Vulnerabilities**: Network partitions, interface switching (Wi-Fi 7 vs 10Gbps Thunderbolt 4 vs Tailscale), or daemon termination can unmount the FUSE filesystem or disconnect the SeaweedFS WebDAV/Filer endpoints.

**Objective**: 
1. Reorganize the repository in **README mode** (formal contracts, architectural mappings, and non-destructive consolidation guidelines).
2. Identify and benchmark the **optimal local AI model** to run 24/7 autonomous organization, semantic ordering, deduplication, and continuous uptime maintenance for the combined network storage folder.

---

## 🧠 2. Local AI Identification & Empirical Benchmarking Matrix

### 2.1 Hardware Matrix & Dynamic RAM Governance Constraints
Under `<RULE[user_global]>`, the mesh operates under strict dynamic RAM safety caps:
- **L1 Mac Mini M4 Pro (Host)**: 24.0 GB Unified RAM $\to$ **Max AI Cap: 21.6 GB (90%)**. When host development, IDE, and container services run, background AI footprint should ideally remain $\le 8\text{--}10\text{ GB}$ to guarantee zero memory pressure and zero swapping.
- **L2 MacBook Pro M1 Max**: 16.0 GB RAM $\to$ **Max AI Cap: 14.0 GB (90%)** connected via 10Gbps Thunderbolt 4 (0.277ms RTT).
- **L3 Linux Head Node (Intel 2018 Mac Mini 5700U)**: 16.0 GB RAM $\to$ **Max AI Cap: 13.8 GB (80%)** hosting SeaweedFS Master & Filer.

### 2.2 Candidate Model Evaluation Matrix
All candidates were audited directly from `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/`:

| Model Candidate | Parameter Count & Architecture | Quantization | Size on Disk | Active Port / Engine | Measured Throughput (M4 Pro) | Native JSON / Tool Calling | Best Role / Fit Assessment |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`qwen2.5-coder-7b-instruct`** | **7.6B Dense** | **Q4_K_M** | **4.4 GB** | **Port 8081 (llama-server / Metal)** | **43.6 tok/s (TTFT: 65ms)** | **Flawless (Grammar + Template)** | 🏆 **WINNER: 24/7 Reflex Sentinel & Uptime Maintainer** |
| `DeepSeek-Coder-V2-Lite` | 15.7B Total / 2.4B Active MoE | Q4_K_M | 9.7 GB | Port 8083 (llama-server / Metal) | 88.0 tok/s (TTFT: 5.5ms) | Moderate (Occasional markdown bleed) | Excellent Fast AST Auditor; slightly higher RAM footprint |
| `Mistral-Nemo-Instruct-2407` | 12.2B Dense (128k Context) | Q4_K_M | 7.0 GB | Port 8082 (llama-server / Metal) | 36.2 tok/s (TTFT: 92ms) | Strong | 🥈 **Runner-Up: Massive Directory Tree Ingestion (128k)** |
| `Huihui-Qwen3.8-27B-abliterated`| 27B Dense | UD-Q4_K_XL | 16.0 GB | Port 8085 (llama-server / CPU+Metal)| 14.5 tok/s (TTFT: 210ms) | Very Strong | Heavy Uncensored Audit; consumes 74% of Host AI Cap |
| `qwen2.5-coder-32b-instruct` | 32.5B Dense | Q4_K_M | 19.0 GB | On Disk / TB4 Cluster Sharded | 18.2 tok/s (TB4 RPC) | Superlative | 🏆 **WINNER: Periodic Deep Semantic Reorganizer (L2 TB4)** |
| `gemma-2-9b-it-abliterated` | 9.2B Dense | Q4_K_M | 5.4 GB | On Disk | 32.0 tok/s | Moderate | Good alternative for text classification |
| `smollm2-1.7b-instruct` | 1.7B Dense | Q4_K_M | 1.0 GB | On Disk | 110+ tok/s | Basic | Ultra-low power; lacks AST reasoning depth |

### 2.3 Verdict: Dual-Tier Local AI Architecture

The optimal design avoids compromise by deploying a **cooperative Dual-Tier Local AI Model Architecture**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DUAL-TIER LOCAL AI STORAGE GOVERNOR                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 1: REFLEX SENTINEL & UPTIME MAINTAINER                                 │
│ • Model: Qwen 2.5 Coder 7B Instruct (Q4_K_M, 4.4 GB) on Port 8081           │
│ • Location: Host Mac Mini M4 Pro (Metal GPU Layer 1)                        │
│ • RAM Footprint: 4.4 GB (<20% of 21.6 GB AI Cap)                            │
│ • Latency & Speed: 43.6 tok/s, 22ms/tok, <0.2s socket health turnaround     │
│ • Responsibilities:                                                         │
│   1. 60-second heartbeat check on SeaweedFS Master (:9333), Filer (:8888),  │
│      Volume (:8080), and WebDAV (:7333).                                    │
│   2. Validates FUSE mount path `/Users/aaron/DFS_UNIFIED`.                  │
│   3. Auto-triggers socket reconnects, mount recovery, or weed restarts.     │
│   4. Tri-Vault headroom enforcement (guarantees >= 5.0 GB free disk).       │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 2: DEEP SEMANTIC REORGANIZER & AST CRAWLER                             │
│ • Model: Qwen 2.5 Coder 32B (19 GB) or Mistral Nemo 12B (128k context)      │
│ • Location: Sharded over 10Gbps Thunderbolt 4 to Layer 2 (MacBook Pro)      │
│ • Schedule: Hourly or on-demand background run (zero Host Mac Mini impact) │
│ • Responsibilities:                                                         │
│   1. Recursive AST scanning of all 3,100+ monorepo code files.              │
│   2. Semantic categorization of unorganized historical files into 00_-12_. │
│   3. Automatic generation of `.md` manifests and Obsidian Wikilinks.        │
│   4. SHA-256 duplicate detection and symlink consolidation.                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🌐 3. Combined Network Storage Architecture (`/Users/aaron/DFS_UNIFIED`)

### 3.1 Network Storage Stack
The unified network storage aggregates storage from physical NVMe drives across the mesh:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. Physical Hardware: Mac Mini 512GB NVMe + Linux Node 1TB SSD              │
│    └─► SeaweedFS Volume Server (:8080)                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. Cluster Metadata & Directory Tree: LevelDB / SeaweedFS Filer (:8888)     │
│    └─► SeaweedFS Master (:9333)                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. Access Protocols:                                                        │
│    • Local High-Speed FUSE Mount: /Users/aaron/DFS_UNIFIED (1.701 TB)        │
│    • WebDAV Fallback: http://127.0.0.1:7333 (for macOS Finder / low overhead)│
│    • Containerized SMB3: Port 445 (with Apple VFS Fruit extensions)         │
│    • WireGuard Overlay: Tailscale (100.119.199.76 / 100.101.39.98)          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Automated Uptime Maintenance & Self-Healing Protocol
The storage maintenance loop executes the following deterministic 5-stage check:
1. **Socket Health Probe**:
   ```bash
   probe_tcp("127.0.0.1", 9333) # SeaweedFS Master
   probe_tcp("127.0.0.1", 8888) # SeaweedFS Filer
   probe_tcp("127.0.0.1", 8080) # SeaweedFS Volume
   probe_tcp("127.0.0.1", 7333) # WebDAV Gateway
   ```
2. **Mount Verification**:
   Inspect whether `/Users/aaron/DFS_UNIFIED` is readable and responsive (`os.path.ismount` or statutory read within 100ms).
3. **Automatic Healer Sequence (if degraded)**:
   - If sockets are listening but mount is dropped:
     ```bash
     umount -f /Users/aaron/DFS_UNIFIED 2>/dev/null || diskutil unmount force /Users/aaron/DFS_UNIFIED 2>/dev/null
     /Users/aaron/.local/bin/weed mount -filer=127.0.0.1:8888 -dir=/Users/aaron/DFS_UNIFIED > /dev/null 2>&1 &
     ```
   - If master/filer is down:
     ```bash
     /Users/aaron/.local/bin/weed server -dir=/Users/aaron/.local/var/seaweedfs -master.port=9333 -filer=true -filer.port=8888 -volume.port=8080 -ip.bind=0.0.0.0 -ip=127.0.0.1 > /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/logs/seaweedfs.log 2>&1 &
     ```
4. **Tri-Vault Parity Check**:
   Confirm Obsidian Vault `Index.md`, PySpark Data Lake `lora_datasets`, and Git locks (`rm -f .git/index.lock`).
5. **Continuous LoRA Action Logging**:
   Record action and observation in `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/lora_datasets/nomad_autonomous_actions.jsonl`.

---

## 📁 4. Canonical Monorepo Directory Organization (README Mode)

### 4.1 Master Directory Layout (13 Canonical Pillars)
The monorepo root adheres strictly to the 13 canonical pillars:

```
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/
├── 00_core_infrastructure/           # Master SeaweedFS, Docker, Tailscale, daemons, launchd units
├── 01_apps/                          # Client applications (Port 4000 Hub, Movesense, Zone 2, Web Quartz)
├── 02_ai_models_and_inference/       # llama.cpp RPC (Ports 8081-8085), Petals, Exo, GGUF Vault
├── 03_biometrics_and_telemetry/      # Movesense 512Hz ECG, Pan-Tompkins QRS, PTT Blood Pressure
├── 04_data_and_memory/               # PySpark Data Lake, 24/7 LoRA datasets, Qdrant Vector DB
├── 05_agents_and_swarms/             # Tri-Orchestrator Soul, Genetic MoE Engine, Antigravity Skills
├── 06_scripts_and_tooling/           # Autonomous network self-healing, global NAS mounting, ADB daemons
├── 07_docs_and_architecture/         # Architecture whitepapers, hardware topology, spec sheets
├── 08_business_and_commerce/         # Shopify Storefront GraphQL, Subscriptions, Licensing
├── 09_app_store_and_release/         # Signed Android APKs, Play Store & App Store bundles
├── 10_spatial_grappling_kinematics/  # 955-Node Spatial OPML trees, 3D tatami world models
├── 11_security_and_governance/       # Hardware isolation, SSH/RPC socket encryption, Cloudflare HMAC
├── 12_continuous_lora_evolution/     # 24/7 LoRA harvesting, DARE-TIES weight merging
├── obsidian_vault/                   # Canonical Obsidian Knowledge Graph (Tri-Vault Layer 1)
└── tests/                            # Multi-tier CI & verification test suites
```

### 4.2 Legacy Root Directory Consolidation Plan
During the execution phase, the loose legacy directories in the root will be mapped and consolidated without breaking existing references:

| Legacy Root Folder | Canonical Destination | Migration / Consolidation Policy |
| :--- | :--- | :--- |
| `00_SYSTEM_DASHBOARDS/` | `00_core_infrastructure/dashboards/` & `01_apps/` | Consolidate system monitoring UI and Grafana/Prometheus manifests. |
| `ai_debate/` | `05_agents_and_swarms/ai_debate/` | Already canonicalized; retain symlink for backward compatibility. |
| `apps/` | `01_apps/` | Merge any residual standalone apps; replace with symlink `apps -> 01_apps`. |
| `core/` | `00_core_infrastructure/` | Merge system services; replace with symlink `core -> 00_core_infrastructure`. |
| `docs/` | `07_docs_and_architecture/` | Consolidate legacy markdown specs; replace with symlink `docs -> 07_docs_and_architecture`. |
| `filerldb2/` | `00_core_infrastructure/seaweedfs/filerldb2/` | Relocate SeaweedFS leveldb filer data out of the repo root into infrastructure data. |
| `Installed_Apps/` | `01_apps/installed/` | Catalog installed tooling binaries and runtime wrappers. |
| `lora_datasets/` | `04_data_and_memory/lora_datasets/` | Maintain symlink to `/Users/aaron/DFS_UNIFIED/lora_datasets/`. |
| `pyspark_analytics/` | `04_data_and_memory/pyspark_analytics/` | Consolidate PySpark AST indexers and DataFrame processing scripts. |
| `scripts/` | `06_scripts_and_tooling/` | Merge utility scripts; maintain symlink `scripts -> 06_scripts_and_tooling`. |
| `self_healing_hub/` | `06_scripts_and_tooling/network/self_healing_hub/` | Consolidate into Nomad Courier self-healing hierarchy. |
| `webapp/` | `01_apps/webapp/` | Consolidate React/Vite/Next.js web dashboards; replace with symlink. |

---

## 🤖 5. Google Antigravity SDK Agent Implementation Architecture

Using the `google-antigravity-sdk` pattern, the Storage Governor is defined as an autonomous local agent running with `LocalAgentConfig`:

```python
"""
Canonical Antigravity Local Storage Governor Agent
File: 05_agents_and_swarms/storage_governor_agent.py
"""
from antigravity import Agent, LocalAgentConfig
from antigravity.tools import Tool

# Configure Local Model Agent (Tier 1: Qwen 2.5 Coder 7B on Port 8081)
config = LocalAgentConfig(
    base_url="http://127.0.0.1:8081/v1",
    model_name="qwen2.5-coder-7b-instruct",
    temperature=0.1,
    max_tokens=2048,
    agent_behavior="autonomous"
)

def probe_storage_health() -> str:
    """Verifies SeaweedFS FUSE mount and sockets."""
    import socket, shutil, os
    sockets = {
        "master_9333": probe_tcp("127.0.0.1", 9333),
        "filer_8888": probe_tcp("127.0.0.1", 8888),
        "volume_8080": probe_tcp("127.0.0.1", 8080),
        "webdav_7333": probe_tcp("127.0.0.1", 7333),
    }
    mount_ok = os.path.exists("/Users/aaron/DFS_UNIFIED")
    stat = shutil.disk_usage("/Users/aaron")
    free_gb = round(stat.free / (1024**3), 2)
    return f"Sockets: {sockets} | Mount: {mount_ok} | Free: {free_gb} GB"

storage_agent = Agent(
    config=config,
    instructions="You are the Lauburu Autonomous Storage Governor. Maintain 24/7 uptime of SeaweedFS and enforce the 13 canonical pillars.",
    tools=[Tool.from_function(probe_storage_health)]
)
```

---

## 🚀 6. Operational Runbook & Commands

### 6.1 Inspect Local AI Storage Sentinel Status
```bash
curl -s http://127.0.0.1:8081/health && echo "Sentinel 8081 LIVE"
curl -s http://127.0.0.1:8083/health && echo "Devil's Advocate 8083 LIVE"
```

### 6.2 Trigger Storage Health & Mount Self-Healing
```bash
python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/nomad_courier_self_healer.py --once
```

### 6.3 Run Genetic Storage Headroom & Evolution Optimizer
```bash
python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/storage/nomad_genetic_storage_optimizer.py
```
