# SeaweedFS High Availability & Stabilization Comprehensive Survey Report

**Surveyor:** Survey Explorer 1  
**Working Directory:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/survey_explorer_1`  
**Target Subsystem:** `00_core_infrastructure` (SeaweedFS DFS, FUSE Mounts, Tailscale 7-Node Mesh)  
**Date:** 2026-08-26  
**Status:** COMPLETE (Read-Only Investigation & Blueprint Mapping)

---

## 1. Executive Summary

This survey maps the complete architecture, storage configuration, network topology, and operational failure modes of the **SeaweedFS Distributed File System (DFS)** pool in the Lauburu Monorepo.

Currently, SeaweedFS aggregates **1.701 TB** of additive NVMe/SSD storage across 4 core nodes in a 7-node Tailscale WireGuard mesh. However, the current deployment suffers from critical **Single-Point-of-Failure (SPOF)** vulnerabilities and **Kernel FUSE lockups**:
1. **Single Master Bottleneck:** The SeaweedFS Master runs solely on the Linux Head Node (`100.101.39.98:9333`) without Raft peer consensus (`-peers=100.101.39.98:9333`). Any network hiccup, sleep transition, or reboot takes down volume assignments, filers, and writes across the entire mesh.
2. **FUSE Mount Freeze (D-State Lockup):** The `/mnt/dfs_unified` mount (`systemd/dfs-fuse-mount.service`) hangs indefinitely during network drops because standard unmount commands block on active kernel VFS handles.
3. **No Autonomous Storage Healer:** The existing `smolagents` Reflex Arc scripts (`scripts/smolagents_healer.py` and `scripts/smolagents_swarm_healer.py`) lack storage-specific tools to test Raft consensus or forcefully detach (`umount -l`) frozen FUSE mounts.
4. **Configuration IP Drift:** Volume configs feature conflicting IP addresses (`100.84.87.3` vs `100.119.199.76` for `Mac_Node`).

This report provides the full topological inventory, single-point-of-failure analysis, and precise implementation contracts for **R1 (3-Node Raft Cluster)**, **R2 (FUSE Mount Zombie Watchdog)**, and **R3 (Smolagents Healer Tools)**.

---

## 2. 7-Node Hardware & Network Mesh Inventory

The Lauburu Mesh is governed by an encrypted Tailscale WireGuard overlay (`100.x.y.z`), high-speed local 2.5GbE LAN (`192.168.8.x`), and direct 40Gbps Thunderbolt 4 DMA bridges (`169.254.x.x`).

| Layer | Device ID | Hardware Description | Tailscale IP | LAN / TB4 IP | Storage Role & Capacity | SeaweedFS Role |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Layer 1** | `Mac_Node` | Apple M4 Pro Mac Mini Host (24GB) | `100.119.199.76` *(drift: 100.84.87.3)* | `192.168.8.230` / TB4 `169.254.87.238` | 368 GB NVMe (`/Volumes/Lauburu-Monorepo/data/dfs_bricks`) | **Master Peer 2** & Volume Server (max=25) |
| **Layer 2** | `MacBook_Pro` | Headless MacBook Pro Vault (16GB) | `100.103.212.21` | `192.168.8.127` / TB4 `169.254.122.166` | 285 GB SSD (`/Volumes/Lauburu-Monorepo/data/dfs_bricks`) | **Master Peer 3** & Volume Server (max=20) |
| **Layer 3** | `Linux_Head_Node` | AMD Ryzen 7 5700U Laptop (16GB) | `100.101.39.98` | `192.168.8.224` | 848 GB NVMe (`/mnt/ssd_1tb/dfs_bricks`) | **Master Peer 1**, Filer (`:8888`), Volume (max=50), SMB3 Gateway |
| **Layer 4** | `Linux_Tablet` | Bedside Linux Tablet (Debian ARM/x86) | `100.81.92.125` | `192.168.8.173` | Stateless Compute & HUD | Client / Consumer |
| **Layer 5** | `MacBook_Air` *(Mac Mini)* | Apple M4 MacBook Air / Compute (16GB) | `100.93.158.96` | `192.168.8.222` | 200 GB NVMe (`/Volumes/Lauburu-Monorepo/data/dfs_bricks`) | Volume Server (max=15) |
| **Layer 6** | `Pixel_10_Pro_XL` | Google Pixel 10 Pro XL (Tensor G5 / Termux) | `100.73.38.87` | `192.168.8.160` (ADB `:5555`, SSH `:8022`) | Edge AI TPU & Vision | Client / Agent Node |
| **Layer 7** | `Samsung_S20` | Samsung Galaxy S20+ (Snapdragon / Termux) | `100.84.40.95` *(alt: 100.99.123.58)* | `192.168.8.158` (ADB `:5555`, SSH `:8022`) | Automated UI Tester | Client / Agent Node |

**Total Aggregated Storage:** **1.701 TB** (100% additive pool, default replication `000`, zero mirroring).

---

## 3. Existing SeaweedFS Configurations & Files

### 3.1 Primary Docker Compose Files
1. **Unified Cluster Manifest:** `00_core_infrastructure/docker/docker-compose.dfs-unified.yml` & `docker-compose.dfs.yml`
   - Defines `dfs_master`, `dfs_filer`, `dfs_linux_volume`, `dfs_samba_gateway`, `dfs_mac_host_volume`, `dfs_macbook_vault_volume`, `dfs_mac_mini_volume`.
2. **Master & Filer Stack:** `00_core_infrastructure/docker/docker-compose.dfs-master.yml`
   - Target Host: `Linux_Head_Node` (`100.101.39.98`).
   - Image: `chrislusf/seaweedfs:latest`.
   - Command: `master -ip=100.101.39.98 -port=9333 -port.grpc=19333 -mdir=/data/dfs_master -volumeSizeLimitMB=1024 -defaultReplication=000 -peers=100.101.39.98:9333`.
   - Volume: `/mnt/ssd_1tb/dfs_master:/data/dfs_master:rw`.
3. **Per-Node Compose Files:**
   - `00_core_infrastructure/docker/docker-compose.dfs.linux-head.yml` (Master, Filer, Linux Volume, Samba).
   - `00_core_infrastructure/docker/docker-compose.dfs.m4-mini.yml` (Node 1 M4 Volume, max=25).
   - `00_core_infrastructure/docker/docker-compose.dfs.macbook-pro.yml` (Node 2 MacBook Pro Vault Volume, max=20).
   - `00_core_infrastructure/docker/docker-compose.dfs.mac-mini.yml` (Node 4 Compute Volume, max=15).
   - `00_core_infrastructure/docker/docker-compose.dfs-volume-linux.yml` & `docker-compose.dfs-volume-mac.yml`.

### 3.2 Systemd FUSE Service
- **File:** `00_core_infrastructure/systemd/dfs-fuse-mount.service`
- **ExecStart:**
  ```bash
  /usr/local/bin/weed mount \
      -filer=100.101.39.98:8888 \
      -dir=/mnt/dfs_unified \
      -filer.path=/ \
      -allowOthers=true \
      -umask=000 \
      -cacheCapacityMB=128 \
      -chunkSizeLimitMB=16 \
      -concurrentWriters=32 \
      -readOnly=false
  ```
- **ExecStop:** `/bin/fusermount3 -u -z /mnt/dfs_unified`
- **Restart Policy:** `Restart=always`, `RestartSec=5`, `TimeoutSec=30`

### 3.3 Samba NAS Gateway
- **Compose:** `00_core_infrastructure/docker/docker-compose.samba.yml`
- **Config:** `00_core_infrastructure/docker/smb_pool_config.conf`
- **Image:** `dperson/samba:latest`
- **Mounts:** `/mnt/dfs_unified:/mnt/nas:rw`
- **Apple Extensions:** `vfs objects = catia fruit streams_xattr`, `fruit:aapl = yes`, `fruit:model = Macpro`
- **Export URI:** `smb://100.101.39.98/nas`

### 3.4 Key Ports & Protocol Matrix

| Service | Port (HTTP/TCP) | gRPC Port | Protocol / Transport | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **SeaweedFS Master** | `9333` | `19333` | HTTP REST / gRPC Raft | Cluster consensus, volume allocation, topology tracking |
| **SeaweedFS Filer** | `8888` | `18888` | HTTP REST / gRPC | POSIX directory namespace, LevelDB metadata backend |
| **SeaweedFS Volume** | `8080` | `18080` | HTTP / gRPC Sync | Raw chunk / needle storage (.dat / .idx files) |
| **Samba SMB3 Gateway** | `445`, `139` | N/A | SMB3 + Apple VFS Fruit | Native macOS Finder & iOS file sharing |
| **Llama.cpp RPC Engine** | `50052` | N/A | GGML Binary Tensor RPC | Distributed AI inference tensor sharding |
| **Mesh Healer API / Health** | `5001`, `8000` | N/A | HTTP REST | Self-healing hub, diagnostic telemetry, and task dispatch |

---

## 4. Single-Point-of-Failure (SPOF) & Vulnerability Analysis

```
                       [ CURRENT ARCHITECTURE: SPOF FRAGILITY ]

  [Mac_Node: 100.119.199.76]       [MacBook_Pro: 100.103.212.21]      [Mac_Mini: 100.93.158.96]
      (Volume Worker)                     (Volume Worker)                 (Volume Worker)
             │                                   │                               │
             ▼                                   ▼                               ▼
       (Heartbeat)                         (Heartbeat)                     (Heartbeat)
             └───────────────────────────────────┼───────────────────────────────┘
                                                 │
                                                 ▼
                                    ┌────────────────────────┐
                                    │ Linux Head Node        │
                                    │ 100.101.39.98          │
                                    │  • Single Master :9333 ◄── CRITICAL SPOF (No Raft Peers)
                                    │  • Single Filer  :8888 ◄── CRITICAL SPOF
                                    │  • FUSE Mount   /mnt/..◄── CRITICAL FREEZE (D-State)
                                    │  • Samba Gateway :445  │
                                    └────────────────────────┘
```

### Vulnerability 1: Standalone Single Master (No Raft High Availability)
- In all existing compose files (`docker-compose.dfs-master.yml`, `docker-compose.dfs.yml`), `dfs_master` has `-peers=100.101.39.98:9333` (single instance).
- **Failure Impact:** If `100.101.39.98` experiences a transient Wi-Fi disconnect, high CPU load, or reboot, all volume nodes (`Mac_Node`, `MacBook_Pro`, `Mac_Mini`) lose their master connection. Write operations fail immediately, volume assignments halt, and file lookups fail across the swarm.

### Vulnerability 2: Kernel FUSE Mount Lockup (Uninterruptible Sleep / D-State)
- `dfs-fuse-mount.service` executes `/usr/local/bin/weed mount -filer=100.101.39.98:8888 -dir=/mnt/dfs_unified`.
- When the network drops between a client and the filer, in-flight VFS system calls (`read`, `write`, `stat`, `getdents`) block in kernel space (`TASK_UNINTERRUPTIBLE` / `D` state).
- Running standard `umount /mnt/dfs_unified` returns `device is busy` or hangs forever.
- Processes attempting to inspect the directory (including `ls`, `df`, `file managers`, or Python daemons) freeze, eventually locking up host memory and shells.
- **Remedy Required:** Must use lazy unmounting (`fusermount3 -u -z /mnt/dfs_unified` or `umount -l /mnt/dfs_unified`) combined with aggressive timeout-based watchdog polling.

### Vulnerability 3: IP Drift & Hardcoded Configuration Errors
- `docker-compose.dfs.m4-mini.yml` and `docker-compose.dfs.yml` hardcode `-ip=100.84.87.3` for `Mac_Node`. However, `00_core_infrastructure/self_healing_hub/src/devices.json` records `Mac_Node` as `100.119.199.76`.
- If the master attempts to route chunk reads/writes to `100.84.87.3`, packets are blackholed, causing silent volume timeouts.

### Vulnerability 4: Absence of Storage Healing in Agent Reflex Arc
- The existing `smolagents` scripts (`scripts/smolagents_healer.py` and `scripts/smolagents_swarm_healer.py`) only expose an ADB tool (`execute_adb_command`).
- They do NOT possess tools to inspect Raft master status (`wget http://<master>/dir/status`), verify volume health, kill stuck FUSE processes, or trigger `umount -l` recovery.

---

## 5. Architectural Stabilization Blueprint

To satisfy requirements R1, R2, and R3, the following technical components must be deployed:

```
                  [ PROPOSED ARCHITECTURE: 3-NODE RAFT HA CLUSTER ]

  ┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
  │ Master 1 (Linux Head)  │ Raft │ Master 2 (Mac Host)    │ Raft │ Master 3 (MacBook Pro) │
  │ 100.101.39.98:9333     │◄────►│ 100.119.199.76:9333    │◄────►│ 100.103.212.21:9333    │
  │ gRPC: 19333            │ Sync │ gRPC: 19333            │ Sync │ gRPC: 19333            │
  └───────────▲────────────┘      └───────────▲────────────┘      └───────────▲────────────┘
              │                               │                               │
              └───────────────────────────────┼───────────────────────────────┘
                                              │ -mserver=Master1,Master2,Master3
              ┌───────────────────────────────┴───────────────────────────────┐
              │                                                               │
              ▼                                                               ▼
  ┌────────────────────────┐                                      ┌────────────────────────┐
  │ Filer Cluster          │                                      │ Distributed Volume     │
  │  - Linux: 100.101.39.98│                                      │  - Linux (848 GB)      │
  │  - Mac:   100.119.199.76                                      │  - Mac Host (368 GB)   │
  │ (Multi-Master Aware)   │                                      │  - MacBook Pro (285 GB)│
  └───────────┬────────────┘                                      │  - Mac Mini (200 GB)   │
              │                                                   └────────────────────────┘
              ▼
  ┌────────────────────────┐
  │ FUSE Watchdog Daemon   │ ──► Continuous `timeout 2 stat` probe
  │  • fuse_watchdog.sh    │ ──► On hang: `umount -l` + kill stuck PIDs + remount
  │  • seaweed_tools.py    │ ──► smolagents `@tool` Reflex Arc integration
  └────────────────────────┘
```

### 5.1 R1: 3-Node Raft Consensus Deployment (`docker-compose.yml`)
- **Master Node 1:** `Linux_Head_Node` (`100.101.39.98:9333`, gRPC `19333`)
- **Master Node 2:** `Mac_Node` (`100.119.199.76:9333`, gRPC `19333`)
- **Master Node 3:** `MacBook_Pro` (`100.103.212.21:9333`, gRPC `19333`)
- **Consensus Peer Spec:**
  ```
  -peers=100.101.39.98:9333,100.119.199.76:9333,100.103.212.21:9333
  ```
- **Volume & Filer Parameter:**
  ```
  -mserver=100.101.39.98:9333,100.119.199.76:9333,100.103.212.21:9333
  ```
- **Quorum Rule:** Cluster maintains read/write quorum if any 1 of the 3 master nodes fails (2/3 majority maintained).

### 5.2 R2: FUSE Mount Zombie Watchdog (`fuse_watchdog.sh`)
- **Polling Loop:** Every 5 seconds, performs a timed probe:
  `timeout 2 stat -f /mnt/dfs_unified > /dev/null 2>&1`
- **Failure Trigger:** If probe times out (exit code 124) or fails with I/O error:
  1. Identifies and terminates blocking processes: `lsof -t /mnt/dfs_unified | xargs -r kill -9` or `fuser -k -m /mnt/dfs_unified`.
  2. Executes lazy unmounting: `fusermount3 -u -z /mnt/dfs_unified 2>/dev/null || umount -l /mnt/dfs_unified 2>/dev/null`.
  3. Validates unmount completion.
  4. Triggers clean remount via systemd (`systemctl restart dfs-fuse-mount.service`) or direct `weed mount` invocation.
  5. Implements exponential backoff to prevent thrashing during sustained network outages.

### 5.3 R3: Smolagents Mesh Healer Integration (`seaweed_tools.py`)
- Python tools decorated with `@tool` from `smolagents`:
  - `check_raft_consensus(master_endpoints: str = "100.101.39.98:9333,100.119.199.76:9333,100.103.212.21:9333") -> str`
    - Queries `/dir/status` and `/cluster/status` across all master endpoints via HTTP/REST.
    - Parses leader election state, active peers, volume count, and free space.
    - Returns structured JSON health telemetry.
  - `heal_fuse_mount(mount_point: str = "/mnt/dfs_unified", filer_endpoints: str = "100.101.39.98:8888") -> str`
    - Tests mount responsiveness.
    - If unresponsive, executes lazy unmount (`umount -l`), restarts FUSE service/process, and confirms recovery.
    - Returns diagnostic and recovery summary.

---

## 6. Implementation File Manifest (Target Artifacts)

| Target Path | Purpose | Key Specifications |
| :--- | :--- | :--- |
| `00_core_infrastructure/docker/docker-compose.dfs-ha-cluster.yml` | 3-Node Raft SeaweedFS Stack | Master peers across `100.101.39.98`, `100.119.199.76`, `100.103.212.21` with multi-master `-mserver` volume flags |
| `00_core_infrastructure/scripts/fuse_watchdog.sh` | FUSE Mount Zombie Watchdog Daemon | 5s probe, `timeout 2 stat`, `lsof` PID eviction, `fusermount3 -u -z` / `umount -l`, systemd integration |
| `00_core_infrastructure/scripts/seaweed_tools.py` | Smolagents Autonomous Reflex Tools | `@tool` functions: `check_raft_consensus()` and `heal_fuse_mount()` with type hints and docstrings |
| `00_core_infrastructure/systemd/dfs-fuse-watchdog.service` | Systemd Watchdog Service | Keeps `fuse_watchdog.sh` running 24/7 on Linux head node |

---

## 7. Verification & Test Plan

1. **Raft Cluster Verification:**
   - Command: `curl -s http://100.101.39.98:9333/cluster/status | jq .`
   - Invalidation condition: `IsLeader` false on all nodes, or peers list does not show 3 nodes.
2. **Watchdog Verification:**
   - Command: Test watchdog execution with a simulated hang: `bash 00_core_infrastructure/scripts/fuse_watchdog.sh --test`
   - Invalidation condition: Script hangs on `stat` without triggering lazy detachment.
3. **Smolagents Tool Ingestion:**
   - Command: `python3 -c "from seaweed_tools import check_raft_consensus, heal_fuse_mount; print(check_raft_consensus())"`
   - Invalidation condition: Import error or missing smolagents tool decorator metadata.
