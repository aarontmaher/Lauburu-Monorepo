# Milestone 1: SeaweedFS 3-Node Raft Cluster Deployment & Multi-Node Architecture Report

**Explorer:** Explorer M1 1  
**Working Directory:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/explorer_m1_1`  
**Target Subsystem:** `00_core_infrastructure/seaweedfs` & `00_core_infrastructure/docker`  
**Milestone:** M1 — SeaweedFS 3-Node Raft Cluster Deployment  
**Date:** 2026-08-26  
**Status:** COMPLETE (Authoritative Architectural Design & Deployment Specification)

---

## 1. Executive Summary

This investigation provides the complete architectural design, container compose definitions, port matrices, health check strategies, and multi-node deployment configurations to transition SeaweedFS from a vulnerable single-master topology to an enterprise-grade **3-Node Raft Consensus High Availability (HA) Cluster** across the 7-node Lauburu Tailscale mesh.

### Core Architectural Upgrades in Milestone 1:
1. **Single-Point-of-Failure (SPOF) Elimination:** Master operations are distributed across 3 independent physical host nodes (Mac Mini Host, MacBook Pro Vault, and Linux Head Node), requiring a 2-node quorum for cluster consensus. Any single host outage or network flap causes zero write interruptions or metadata corruption.
2. **Sub-Second Raft Failover:** With `-electionTimeout=2s` and `-heartbeatInterval=200ms`, leader failover completes within ~2.0–2.5 seconds, automatically notifying all distributed volume servers and filers.
3. **gRPC Offset Port Integration:** Explicitly maps and opens the `+10000` gRPC companion ports (`19333`, `18888`, `18080`) across Docker containers and Tailscale ACLs to prevent socket timeouts during Raft consensus synchronization.
4. **Correction of Network IP Drift:** Fixes the historical configuration drift where `Mac_Node` was erroneously referenced as `100.84.87.3`, establishing the true Tailscale IP `100.119.199.76`.
5. **Preservation of 1.701 TB Additive Pool:** Maintains pure non-mirrored (`replication=000`) additive storage aggregation across all 4 storage bricks (Linux: 848GB, Mac Host: 368GB, MacBook Vault: 285GB, Mac Mini: 200GB).

---

## 2. 7-Node Tailscale Mesh Topology & Role Matrix

The cluster spans the encrypted WireGuard overlay (`100.x.y.z`) backed by physical 2.5GbE LAN (`192.168.8.x`) and 40Gbps Thunderbolt 4 DMA (`169.254.x.x`).

| Node Identifier | Device Description | Tailscale IP (`100.x`) | Local / TB4 IP | SeaweedFS Raft & Storage Role | Brick Path & Capacity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`Mac_Node`** | Apple M4 Pro Mac Mini (24GB) | `100.119.199.76` | `192.168.8.230` / TB4 `169.254.87.238` | **Master Peer 1 (Raft)**, Filer 1, Volume 1 (max=25) | `/Volumes/Lauburu-Monorepo/data/dfs_bricks` (368 GB) |
| **`MacBook_Pro`** | Headless MacBook Pro Vault (16GB) | `100.103.212.21` | `192.168.8.127` / TB4 `169.254.122.166` | **Master Peer 2 (Raft)**, Filer 2, Volume 2 (max=20) | `/Volumes/Lauburu-Monorepo/data/dfs_bricks` (285 GB) |
| **`Linux_Head_Node`**| AMD Ryzen 7 5700U Laptop (16GB) | `100.101.39.98` | `192.168.8.224` | **Master Peer 3 (Raft)**, Filer 3, Volume 3 (max=50), Samba Gateway | `/mnt/ssd_1tb/dfs_bricks` (848 GB) |
| **`MacBook_Air`** | Apple M4 MacBook Air / Compute | `100.93.158.96` | `192.168.8.222` | Volume 4 (max=15) | `/Volumes/Lauburu-Monorepo/data/dfs_bricks` (200 GB) |
| **`Linux_Tablet`** | Bedside Linux Tablet | `100.81.92.125` | `192.168.8.173` | Stateless Client (FUSE / WebDAV) | N/A (Client Consumer) |
| **`Pixel_10_Pro_XL`**| Google Pixel 10 Pro XL | `100.73.38.87` | `192.168.8.160` (ADB `:5555`) | Reflex Arc Healer Agent Node | N/A (Client Consumer) |
| **`Samsung_S20`** | Samsung Galaxy S20+ | `100.84.40.95` | `192.168.8.158` (ADB `:5555`) | Automated UI / Watchdog Node | N/A (Client Consumer) |

**Total Unified Storage Pool:** **1.701 TB** (Replication `000`, 110 max volume allocation slots).

---

## 3. SeaweedFS Port Mechanics & gRPC Offset Specification

SeaweedFS derives companion gRPC sockets by adding **10,000** to the HTTP listening port. Both ports must be published and routable:

| Service Subsystem | Base HTTP / REST Port | Derived gRPC Port (`+10000`) | Explicit CLI Override | Protocol / Transport | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Master Server** | `9333` | `19333` | `-port.grpc=19333` | HTTP REST / gRPC Raft | Raft log replication, leader election, volume directory |
| **Filer Server** | `8888` | `18888` | `-port.grpc=18888` | HTTP REST / gRPC | POSIX directory tree metadata, LevelDB / SQL backend |
| **Volume Server** | `8080` | `18080` | `-port.grpc=18080` | HTTP / gRPC Sync | Chunk / needle binary streaming, master heartbeat streams |
| **Samba Gateway** | `445`, `139` | N/A | N/A | SMB3 + Apple VFS Fruit | Native macOS Finder & iOS file sharing export |
| **WebDAV Gateway** | `7333` | N/A | N/A | HTTP WebDAV | Client WebDAV mounting |
| **S3 Gateway** | `8333` | `18333` | `-s3.port.grpc=18333` | HTTP S3 / gRPC | Amazon S3 API emulation layer |

---

## 4. Raft Quorum Mathematics & Timing Parameters

### 4.1 Quorum Formula
For an $N$-node cluster:
$$\text{Quorum} = \left\lfloor \frac{N}{2} \right\rfloor + 1$$
For $N = 3$:
$$\text{Quorum} = \left\lfloor \frac{3}{2} \right\rfloor + 1 = 2 \text{ nodes}$$
$$\text{Fault Tolerance} = \left\lfloor \frac{N - 1}{2} \right\rfloor = 1 \text{ node failure}$$

### 4.2 Liveness & Election Timing
- **`-heartbeatInterval=200ms`**: Raft leader sends heartbeat packets every 200ms (randomized $\times [1.0, 1.25)$).
- **`-electionTimeout=2s`**: If a follower misses heartbeats for 2 seconds, it triggers a new election round.
- **Failover Latency:** ~2.0s to 2.5s to elect a new leader and update volume server heartbeats.

### 4.3 Quorum Scenarios
1. **3/3 Nodes Active:** Full read/write capability across all volumes and metadata.
2. **2/3 Nodes Active (1 Master Crashed/Unreachable):** Quorum maintained ($2 \ge 2$). Leader continues processing reads/writes without disruption.
3. **1/3 Nodes Active (2 Masters Down):** Quorum lost ($1 < 2$). Remaining node converts to follower/read-only mode. Volume and filer operations block modifications until quorum is restored.

---

## 5. Exact Specification 1: `00_core_infrastructure/docker/docker-compose.dfs-ha.yml`

This manifest defines the multi-host high-availability cluster blueprint. It models the entire 3-node Raft master cluster, multi-master filers, distributed volume bricks, and the Samba gateway.

```yaml
version: '3.8'

# ==============================================================================
# LAUBURU DISTRIBUTED FILE SYSTEM (DFS) — 3-NODE RAFT HIGH AVAILABILITY CLUSTER
# Target Mesh: 7-Node Tailscale WireGuard Overlay (100.x.y.z)
# Quorum: 2/3 Masters Required (100.119.199.76, 100.103.212.21, 100.101.39.98)
# Storage: 1.701 TB Additive Pool Across 4 Core Nodes (Replication: 000)
# ==============================================================================

x-seaweed-defaults: &seaweed-defaults
  image: chrislusf/seaweedfs:latest
  restart: unless-stopped
  network_mode: "host"
  logging:
    driver: "json-file"
    options:
      max-size: "20m"
      max-file: "3"

services:
  # ============================================================================
  # MASTER NODE 1: MAC MINI HOST (100.119.199.76)
  # ============================================================================
  dfs_master_node1:
    <<: *seaweed-defaults
    container_name: lauburu_dfs_master_node1
    hostname: mac-mini-dfs-master
    environment:
      - WEED_MASTER_PORT=9333
      - WEED_MASTER_PORT_GRPC=19333
      - WEED_MASTER_PEERS=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333
      - WEED_MASTER_ELECTIONTIMEOUT=2s
      - WEED_MASTER_HEARTBEATINTERVAL=200ms
    volumes:
      - /Volumes/Lauburu-Monorepo/data/dfs_master:/data/dfs_master:rw
    command: >
      weed master
      -ip=100.119.199.76
      -ip.bind=0.0.0.0
      -port=9333
      -port.grpc=19333
      -mdir=/data/dfs_master
      -volumeSizeLimitMB=1024
      -defaultReplication=000
      -peers=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333
      -electionTimeout=2s
      -heartbeatInterval=200ms
      -telemetry=false
    mem_limit: 256m
    memswap_limit: 256m
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '1.0'
        reservations:
          memory: 64M
    labels:
      com.lauburu.dfs.service: "dfs-master"
      com.lauburu.dfs.node: "Mac_Node"
      com.lauburu.dfs.raft_peer: "1"
      com.lauburu.dfs.ip: "100.119.199.76"
    healthcheck:
      test: ["CMD-SHELL", "wget -q -O- http://127.0.0.1:9333/dir/status || exit 1"]
      interval: 10s
      timeout: 3s
      retries: 3
      start_period: 5s

  # ============================================================================
  # MASTER NODE 2: MACBOOK PRO VAULT (100.103.212.21)
  # ============================================================================
  dfs_master_node2:
    <<: *seaweed-defaults
    container_name: lauburu_dfs_master_node2
    hostname: macbook-vault-dfs-master
    environment:
      - WEED_MASTER_PORT=9333
      - WEED_MASTER_PORT_GRPC=19333
      - WEED_MASTER_PEERS=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333
      - WEED_MASTER_ELECTIONTIMEOUT=2s
      - WEED_MASTER_HEARTBEATINTERVAL=200ms
    volumes:
      - /Volumes/Lauburu-Monorepo/data/dfs_master:/data/dfs_master:rw
    command: >
      weed master
      -ip=100.103.212.21
      -ip.bind=0.0.0.0
      -port=9333
      -port.grpc=19333
      -mdir=/data/dfs_master
      -volumeSizeLimitMB=1024
      -defaultReplication=000
      -peers=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333
      -electionTimeout=2s
      -heartbeatInterval=200ms
      -telemetry=false
    mem_limit: 256m
    memswap_limit: 256m
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '1.0'
        reservations:
          memory: 64M
    labels:
      com.lauburu.dfs.service: "dfs-master"
      com.lauburu.dfs.node: "MacBook_Pro"
      com.lauburu.dfs.raft_peer: "2"
      com.lauburu.dfs.ip: "100.103.212.21"
    healthcheck:
      test: ["CMD-SHELL", "wget -q -O- http://127.0.0.1:9333/dir/status || exit 1"]
      interval: 10s
      timeout: 3s
      retries: 3
      start_period: 5s

  # ============================================================================
  # MASTER NODE 3: LINUX HEAD NODE (100.101.39.98)
  # ============================================================================
  dfs_master_node3:
    <<: *seaweed-defaults
    container_name: lauburu_dfs_master_node3
    hostname: linux-head-dfs-master
    environment:
      - WEED_MASTER_PORT=9333
      - WEED_MASTER_PORT_GRPC=19333
      - WEED_MASTER_PEERS=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333
      - WEED_MASTER_ELECTIONTIMEOUT=2s
      - WEED_MASTER_HEARTBEATINTERVAL=200ms
    volumes:
      - /mnt/ssd_1tb/dfs_master:/data/dfs_master:rw
    command: >
      weed master
      -ip=100.101.39.98
      -ip.bind=0.0.0.0
      -port=9333
      -port.grpc=19333
      -mdir=/data/dfs_master
      -volumeSizeLimitMB=1024
      -defaultReplication=000
      -peers=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333
      -electionTimeout=2s
      -heartbeatInterval=200ms
      -telemetry=false
    mem_limit: 256m
    memswap_limit: 256m
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '1.0'
        reservations:
          memory: 64M
    labels:
      com.lauburu.dfs.service: "dfs-master"
      com.lauburu.dfs.node: "Linux_Head_Node"
      com.lauburu.dfs.raft_peer: "3"
      com.lauburu.dfs.ip: "100.101.39.98"
    healthcheck:
      test: ["CMD-SHELL", "wget -q -O- http://127.0.0.1:9333/dir/status || exit 1"]
      interval: 10s
      timeout: 3s
      retries: 3
      start_period: 5s

  # ============================================================================
  # LINUX HEAD NODE: DFS FILER
  # ============================================================================
  dfs_filer_node3:
    <<: *seaweed-defaults
    container_name: lauburu_dfs_filer_node3
    hostname: linux-head-dfs-filer
    depends_on:
      - dfs_master_node3
    volumes:
      - /mnt/ssd_1tb/dfs_filer:/data/dfs_filer:rw
    command: >
      weed filer
      -ip=100.101.39.98
      -ip.bind=0.0.0.0
      -port=8888
      -port.grpc=18888
      -master=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333
      -defaultReplicaPlacement=000
    mem_limit: 256m
    memswap_limit: 256m
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '1.0'
        reservations:
          memory: 64M
    labels:
      com.lauburu.dfs.service: "dfs-filer"
      com.lauburu.dfs.node: "Linux_Head_Node"
    healthcheck:
      test: ["CMD-SHELL", "wget -q -O- http://127.0.0.1:8888/ || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s

  # ============================================================================
  # VOLUME SERVER 1: LINUX HEAD NODE (848 GB NVMe)
  # ============================================================================
  dfs_volume_linux:
    <<: *seaweed-defaults
    container_name: lauburu_dfs_volume_linux
    hostname: linux-head-dfs-volume
    depends_on:
      - dfs_master_node3
    volumes:
      - /mnt/ssd_1tb/dfs_bricks:/data/dfs_bricks:rw
    command: >
      weed volume
      -ip=100.101.39.98
      -ip.bind=0.0.0.0
      -port=8080
      -port.grpc=18080
      -dir=/data/dfs_bricks
      -max=50
      -minFreeSpacePercent=5
      -dataCenter=WiFi
      -master=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333
      -publicUrl=100.101.39.98:8080
    mem_limit: 128m
    memswap_limit: 128m
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '1.0'
        reservations:
          memory: 32M
    labels:
      com.lauburu.dfs.service: "volume-brick"
      com.lauburu.dfs.node: "Linux_Head_Node"
      com.lauburu.dfs.capacity_gb: "848"
    healthcheck:
      test: ["CMD-SHELL", "wget -q -O- http://127.0.0.1:8080/status || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s

  # ============================================================================
  # VOLUME SERVER 2: M4 MAC MINI HOST (368 GB NVMe)
  # ============================================================================
  dfs_volume_mac_host:
    <<: *seaweed-defaults
    container_name: lauburu_dfs_volume_mac_host
    hostname: mac-host-dfs-volume
    volumes:
      - /Volumes/Lauburu-Monorepo/data/dfs_bricks:/data/dfs_bricks:rw
    command: >
      weed volume
      -ip=100.119.199.76
      -ip.bind=0.0.0.0
      -port=8080
      -port.grpc=18080
      -dir=/data/dfs_bricks
      -max=25
      -minFreeSpacePercent=5
      -dataCenter=Thunderbolt
      -master=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333
      -publicUrl=100.119.199.76:8080
    mem_limit: 256m
    memswap_limit: 256m
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '1.0'
        reservations:
          memory: 64M
    labels:
      com.lauburu.dfs.service: "volume-brick"
      com.lauburu.dfs.node: "Mac_Node"
      com.lauburu.dfs.capacity_gb: "368"
    healthcheck:
      test: ["CMD-SHELL", "wget -q -O- http://127.0.0.1:8080/status || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s

  # ============================================================================
  # VOLUME SERVER 3: MACBOOK PRO VAULT (285 GB SSD)
  # ============================================================================
  dfs_volume_macbook_vault:
    <<: *seaweed-defaults
    container_name: lauburu_dfs_volume_macbook_vault
    hostname: macbook-vault-dfs-volume
    volumes:
      - /Volumes/Lauburu-Monorepo/data/dfs_bricks:/data/dfs_bricks:rw
    command: >
      weed volume
      -ip=100.103.212.21
      -ip.bind=0.0.0.0
      -port=8080
      -port.grpc=18080
      -dir=/data/dfs_bricks
      -max=20
      -minFreeSpacePercent=5
      -dataCenter=Thunderbolt
      -master=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333
      -publicUrl=100.103.212.21:8080
    mem_limit: 256m
    memswap_limit: 256m
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '1.0'
        reservations:
          memory: 64M
    labels:
      com.lauburu.dfs.service: "volume-brick"
      com.lauburu.dfs.node: "MacBook_Pro"
      com.lauburu.dfs.capacity_gb: "285"
    healthcheck:
      test: ["CMD-SHELL", "wget -q -O- http://127.0.0.1:8080/status || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s

  # ============================================================================
  # VOLUME SERVER 4: MAC MINI COMPUTE (200 GB NVMe)
  # ============================================================================
  dfs_volume_mac_mini:
    <<: *seaweed-defaults
    container_name: lauburu_dfs_volume_mac_mini
    hostname: mac-mini-dfs-volume
    volumes:
      - /Volumes/Lauburu-Monorepo/data/dfs_bricks:/data/dfs_bricks:rw
    command: >
      weed volume
      -ip=100.93.158.96
      -ip.bind=0.0.0.0
      -port=8080
      -port.grpc=18080
      -dir=/data/dfs_bricks
      -max=15
      -minFreeSpacePercent=5
      -master=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333
      -publicUrl=100.93.158.96:8080
    mem_limit: 256m
    memswap_limit: 256m
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '1.0'
        reservations:
          memory: 64M
    labels:
      com.lauburu.dfs.service: "volume-brick"
      com.lauburu.dfs.node: "Mac_Mini"
      com.lauburu.dfs.capacity_gb: "200"
    healthcheck:
      test: ["CMD-SHELL", "wget -q -O- http://127.0.0.1:8080/status || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s

  # ============================================================================
  # SAMBA SMB3 NAS GATEWAY
  # ============================================================================
  dfs_samba_gateway:
    image: dperson/samba:latest
    container_name: lauburu_samba_gateway
    hostname: lauburu-samba-gateway
    restart: unless-stopped
    network_mode: "host"
    environment:
      - TZ=Australia/Sydney
      - WORKGROUP=WORKGROUP
      - SERVERSTRING=Lauburu 1.701TB Unified DFS NAS
      - NMBD=true
    volumes:
      - /mnt/dfs_unified:/mnt/nas:rw
      - /Volumes/Lauburu-Monorepo/smb_pool_config.conf:/etc/samba/smb.conf:ro
    mem_limit: 256m
    memswap_limit: 256m
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '1.0'
        reservations:
          memory: 64M
    labels:
      com.lauburu.dfs.service: "samba-smb3-gateway"
      com.lauburu.dfs.node: "Linux_Head_Node"
    healthcheck:
      test: ["CMD-SHELL", "nc -z 127.0.0.1 445 || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
```

---

## 6. Exact Specification 2: `00_core_infrastructure/seaweedfs/docker-compose.yml`

This manifest provides the standalone and parameterized node stack for deployment within the `00_core_infrastructure/seaweedfs` module. It uses environment variable interpolation so any node can run its local Master, Filer, and Volume container while maintaining Raft synchronization across the mesh.

```yaml
version: '3.8'

# ==============================================================================
# LAUBURU SEAWEEDFS LOCAL NODE STACK (Milestone 1 Production Definition)
# Directory: 00_core_infrastructure/seaweedfs/docker-compose.yml
# Raft Quorum: 3-Node Consensus Cluster (2/3 majority required)
# ==============================================================================

services:
  seaweed_master:
    image: chrislusf/seaweedfs:latest
    container_name: lauburu_seaweed_master
    hostname: ${NODE_HOSTNAME:-seaweed-master-node}
    restart: unless-stopped
    network_mode: "host"
    environment:
      - WEED_MASTER_PORT=9333
      - WEED_MASTER_PORT_GRPC=19333
      - WEED_MASTER_PEERS=${DFS_MASTER_PEERS:-100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333}
      - WEED_MASTER_ELECTIONTIMEOUT=2s
      - WEED_MASTER_HEARTBEATINTERVAL=200ms
    volumes:
      - ${DFS_MASTER_DATA_DIR:-/mnt/storage/seaweedfs/master}:/data/master:rw
    command: >
      weed master
      -ip=${NODE_IP:-100.101.39.98}
      -ip.bind=0.0.0.0
      -port=9333
      -port.grpc=19333
      -mdir=/data/master
      -volumeSizeLimitMB=1024
      -defaultReplication=000
      -peers=${DFS_MASTER_PEERS:-100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333}
      -electionTimeout=2s
      -heartbeatInterval=200ms
      -telemetry=false
    mem_limit: 256m
    memswap_limit: 256m
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '1.0'
        reservations:
          memory: 64M
    labels:
      com.lauburu.dfs.service: "seaweed-master"
      com.lauburu.dfs.cluster: "3-node-raft-ha"
    healthcheck:
      test: ["CMD-SHELL", "wget -q -O- http://127.0.0.1:9333/dir/status || exit 1"]
      interval: 10s
      timeout: 3s
      retries: 3
      start_period: 5s

  seaweed_filer:
    image: chrislusf/seaweedfs:latest
    container_name: lauburu_seaweed_filer
    hostname: ${NODE_HOSTNAME:-seaweed-filer-node}
    restart: unless-stopped
    network_mode: "host"
    depends_on:
      - seaweed_master
    environment:
      - WEED_FILER_PORT=8888
      - WEED_FILER_PORT_GRPC=18888
    volumes:
      - ${DFS_FILER_DATA_DIR:-/mnt/storage/seaweedfs/filerldb2}:/data/filerldb2:rw
    command: >
      weed filer
      -ip=${NODE_IP:-100.101.39.98}
      -ip.bind=0.0.0.0
      -port=8888
      -port.grpc=18888
      -master=${DFS_MASTER_PEERS:-100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333}
      -defaultReplicaPlacement=000
      -defaultStoreDir=/data/filerldb2
    mem_limit: 256m
    memswap_limit: 256m
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '1.0'
        reservations:
          memory: 64M
    labels:
      com.lauburu.dfs.service: "seaweed-filer"
      com.lauburu.dfs.cluster: "3-node-raft-ha"
    healthcheck:
      test: ["CMD-SHELL", "wget -q -O- http://127.0.0.1:8888/ || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s

  seaweed_volume:
    image: chrislusf/seaweedfs:latest
    container_name: lauburu_seaweed_volume
    hostname: ${NODE_HOSTNAME:-seaweed-volume-node}
    restart: unless-stopped
    network_mode: "host"
    depends_on:
      - seaweed_master
    environment:
      - WEED_VOLUME_PORT=8080
      - WEED_VOLUME_PORT_GRPC=18080
    volumes:
      - ${DFS_VOLUME_DATA_DIR:-/mnt/storage/seaweedfs/volume}:/data/volume:rw
    command: >
      weed volume
      -ip=${NODE_IP:-100.101.39.98}
      -ip.bind=0.0.0.0
      -port=8080
      -port.grpc=18080
      -dir=/data/volume
      -max=${MAX_VOLUMES:-30}
      -minFreeSpacePercent=5
      -dataCenter=${DATACENTER:-WiFi}
      -master=${DFS_MASTER_PEERS:-100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333}
      -publicUrl=${NODE_IP:-100.101.39.98}:8080
    mem_limit: 256m
    memswap_limit: 256m
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '1.0'
        reservations:
          memory: 64M
    labels:
      com.lauburu.dfs.service: "seaweed-volume"
      com.lauburu.dfs.cluster: "3-node-raft-ha"
    healthcheck:
      test: ["CMD-SHELL", "wget -q -O- http://127.0.0.1:8080/status || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s
```

---

## 7. Per-Node Compose Definitions for `00_core_infrastructure/docker/`

To maintain clean backwards-compatible execution on each specific host, the individual compose files in `00_core_infrastructure/docker/` must be updated with the 3-node Raft peers:

### 7.1 Linux Head Node (`docker-compose.dfs.linux-head.yml`)
- **Master Command:** `weed master -ip=100.101.39.98 -port=9333 -port.grpc=19333 -peers=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333 -electionTimeout=2s -heartbeatInterval=200ms -mdir=/data/dfs_master`
- **Filer Command:** `weed filer -master=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333 -ip=100.101.39.98 -port=8888 -port.grpc=18888`
- **Volume Command:** `weed volume -master=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333 -ip=100.101.39.98 -port=8080 -port.grpc=18080 -dir=/data/dfs_bricks -max=50`

### 7.2 M4 Mac Mini Host (`docker-compose.dfs.m4-mini.yml`)
- **Correction:** Fix `-ip` to `100.119.199.76` (was `100.84.87.3`).
- **Volume Command:** `weed volume -master=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333 -ip=100.119.199.76 -port=8080 -port.grpc=18080 -dir=/data/dfs_bricks -max=25 -publicUrl=100.119.199.76:8080`

### 7.3 MacBook Pro Vault (`docker-compose.dfs.macbook-pro.yml`)
- **Volume Command:** `weed volume -master=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333 -ip=100.103.212.21 -port=8080 -port.grpc=18080 -dir=/data/dfs_bricks -max=20 -publicUrl=100.103.212.21:8080`

### 7.4 Mac Mini Compute (`docker-compose.dfs.mac-mini.yml`)
- **Volume Command:** `weed volume -master=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333 -ip=100.93.158.96 -port=8080 -port.grpc=18080 -dir=/data/dfs_bricks -max=15 -publicUrl=100.93.158.96:8080`

---

## 8. Verification & Live Test Procedures

The implementer and victory auditor should use the following commands to verify the 3-Node Raft cluster:

### Step 1: Query Cluster Raft Status
```bash
curl -s http://100.101.39.98:9333/cluster/status | jq .
```
**Expected Output:**
```json
{
  "IsLeader": true,
  "Leader": "100.101.39.98:9333.19333",
  "Peers": [
    "100.119.199.76:9333.19333",
    "100.103.212.21:9333.19333"
  ]
}
```

### Step 2: Query Master Topology & Volume Allocation
```bash
curl -s http://100.101.39.98:9333/dir/status | jq .
```
**Verification Points:**
- `Topology.DataCenters` shows active DataCenters (`Thunderbolt`, `WiFi`).
- `Free` volumes reflect the sum of all active volume slots ($25 + 20 + 50 + 15 = 110$).

### Step 3: Verify Failover Simulation
1. Simulate dropping leader node (e.g. `SIGSTOP` or stopping Master 3).
2. Within 2.5 seconds, query Master 1 (`curl -s http://100.119.199.76:9333/cluster/status`).
3. Verify `IsLeader` is true on either Node 1 or Node 2, and volume heartbeats have transferred over.
4. Resume Master 3 and verify it rejoins Raft cluster as a follower.

---

## 9. Recommendations for Worker M1

1. Create directory `00_core_infrastructure/seaweedfs` if not present.
2. Write the authoritative `00_core_infrastructure/docker/docker-compose.dfs-ha.yml` and `00_core_infrastructure/seaweedfs/docker-compose.yml` as defined above.
3. Update `docker-compose.dfs-unified.yml` and the per-node compose files (`docker-compose.dfs.linux-head.yml`, `docker-compose.dfs.m4-mini.yml`, etc.) to point to the 3-node master list.
4. Verify port mappings and environment variable overrides.
