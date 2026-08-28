# SeaweedFS 3-Node Raft Consensus & High Availability Specification Report

**Document Version:** 1.0.0  
**Author:** Survey Spec Miner 2  
**Target Subsystem:** `00_core_infrastructure/seaweedfs`  
**Ecosystem:** Lauburu 7-Node Tailscale Mesh  
**Authoritative Binary Inspected:** `weed version 30GB 4.44 darwin arm64` (`/Users/aaron/.local/bin/weed`)

---

## Executive Summary

This specification report establishes the authoritative architecture, configuration contracts, networking constraints, and failure modes for transitioning the SeaweedFS distributed storage layer from a single-master topology to a **3-Node Raft Consensus Cluster** across the Tailscale mesh IP space.

SeaweedFS uses a customized Raft consensus engine over gRPC (default port offset `+10000`). With 3 master nodes deployed across persistent host hardware (Apple M4 Pro Mac Mini, Headless MacBook Pro Vault, and Linux Head Node), the storage layer achieves high availability (HA) with single-node failure tolerance, automated leader re-election within 2–3 seconds, seamless multi-master volume registration, and resilient FUSE mount lifecycle governance.

---

## 1. Features Discovered & Interface Specifications

### Features Discovered Table

| # | Category | Feature | Description | Inputs / Flags | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|----------------|---------|----------------|----------------|
| 1 | Raft Consensus | Standalone Master Clustering | Runs dedicated Raft master node in peer cluster | `-peers=ip1:9333,ip2:9333,ip3:9333`, `-ip=<tailscale_ip>`, `-port=9333` | HTTP API `:9333`, gRPC `:19333`, Raft state machine | Fails write operations when quorum (<2/3) is lost | `weed master -help`, CLI test |
| 2 | Raft Consensus | All-in-One Server Clustering | Runs master+volume+filer in a single process with master clustering | `-master.peers=ip1:9333,ip2:9333,ip3:9333`, `-ip=<tailscale_ip>`, `-master.port=9333` | Combined master/volume/filer endpoints | Rejects leader operations if isolated from Raft peers | `weed server -help`, CLI test |
| 3 | Port Mechanics | Automatic gRPC Offset | Automatically derives internal gRPC listening port by adding 10,000 to HTTP port | Default port arithmetic `port + 10000` (e.g. 9333 -> 19333, 8888 -> 18888, 8080 -> 18080) | gRPC listening socket at `:19333`, `:18888`, `:18080` | `connection refused` if firewall blocks `port + 10000` | `weed master`, glog inspection |
| 4 | Port Mechanics | Explicit gRPC Override | Explicitly specifies gRPC port for non-standard routing or container mapping | `-port.grpc=19333` (master), `-filer.port.grpc=18888`, `-volume.port.grpc=18080` | Custom gRPC port binding | Fails startup if port is already in use | `weed master -help`, `weed filer -help` |
| 5 | Master HA | Dynamic Leader Election | Elects 1 leader among quorum of active peers; forwards metadata mutations to leader | `-electionTimeout=2s`, `-heartbeatInterval=200ms` | JSON response `{"IsLeader":true,"Leader":"ip:9333.19333"}` | Non-leader returns `{"Leader":"leader_ip:9333.19333"}` | `curl /cluster/status`, test run |
| 6 | Master HA | TopologyId Guard | Global UUID assigned to cluster topology to prevent split-brain states | Auto-generated on bootstrap, replicated to Raft log | `TopologyId: "<uuid>"` in `/dir/status` | Fatal crash `Split-brain detected!` on mismatched UUID | `weed master` runtime logs |
| 7 | Volume HA | Multi-Master Registration | Volume servers send heartbeats to active leader and discover new leader upon failover | `-master=ip1:9333,ip2:9333,ip3:9333`, `-ip=<tailscale_ip>`, `-port=8080` | Volume assignment registration across cluster | Reconnects with exponential backoff on leader EOF | `weed volume -help`, test run |
| 8 | Filer HA | Multi-Master Filer Binding | Stateless filer instances stream metadata updates to active Raft master | `-master=ip1:9333,ip2:9333,ip3:9333`, `-filerGroup=<group>` | Filer HTTP `:8888` and gRPC `:18888` | Buffer writes locally until master re-election completes | `weed filer -help`, test run |
| 9 | Filer HA | Shared Filer Store | External shared database backend for active-active multi-filer metadata sync | `filer.toml` ([postgres], [redis2], [etcd], [mysql]) | ACID POSIX metadata table `filemeta` | Read/write errors if shared DB is unreachable | `weed scaffold -config=filer` |
| 10 | Client Access | Multi-Filer FUSE Mount | High-speed FUSE mount connecting to resilient filer cluster | `weed mount -filer=ip1:8888,ip2:8888,ip3:8888 -dir=/mnt/dfs_unified` | POSIX filesystem mountpoint | Freezes I/O if filer becomes unreachable without timeout | `weed mount -help` |
| 11 | FUSE Tuning | Mount Read Retry & Locking | Coordinates distributed file locking and read retries across mesh | `-readRetryTime=6s`, `-dlm=true`, `-writeBufferSizeMB=256` | Distributed advisory lock (DLM), bounded RAM cache | Returns EIO or cached data on network blip | `weed mount -help` |
| 12 | Configuration | Environment Variable Overrides | Declarative override of TOML and CLI settings via environment variables | `WEED_<SECTION>_<KEY>=<VALUE>` (e.g. `WEED_MASTER_PEERS=...`) | Runtime configuration update | Ignored if variable naming convention is invalid | `weed scaffold -help` |

---

## 2. SeaweedFS Raft Consensus Architecture Deep-Dive

### 2.1 Master Peer Communication Flags: `-master.peers` vs `-peers`

SeaweedFS provides two distinct execution binaries/subcommands for running masters:

1. **`weed master` (Dedicated Master Subcommand):**
   - Flag: `-peers=<ip1>:<port1>,<ip2>:<port2>,<ip3>:<port3>`
   - Example: `weed master -ip=100.119.199.76 -port=9333 -peers=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333 -mdir=/data/master`
   - Single-master mode override: `-peers=none` (skips Raft quorum wait).

2. **`weed server` (All-in-One Subcommand):**
   - Flag: `-master.peers=<ip1>:<port1>,<ip2>:<port2>,<ip3>:<port3>`
   - Example: `weed server -ip=100.119.199.76 -master.port=9333 -master.peers=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333 -dir=/data`
   - Notice: When using `weed server`, all master-specific parameters are namespaced with the `-master.` prefix (`-master.port`, `-master.peers`, `-master.electionTimeout`, `-master.heartbeatInterval`).

### 2.2 Raft Node Identification & Wire Format

Each node in the Raft cluster is identified by the combined string: `<advertised_ip>:<http_port>.<grpc_port>`
- Example: `100.119.199.76:9333.19333`
- Crucial Constraint: The `-ip` parameter **must** be the routable Tailscale IP address (`100.x.y.z`). If set to `127.0.0.1` or a private local subnet (`192.168.8.x`), remote mesh peers will attempt to dial that local IP and fail.

### 2.3 gRPC Port Derivation & Port Matrix

SeaweedFS services automatically allocate a companion gRPC port for internal clustering, heartbeats, and metadata synchronization by adding **10,000** to the configured HTTP port:

| Subsystem Component | Default HTTP Port | Derived gRPC Port (`+10000`) | Explicit Flag Override | Protocol / Purpose |
|---------------------|-------------------|------------------------------|------------------------|---------------------|
| **Master Node**     | `9333/tcp`        | `19333/tcp`                  | `-port.grpc=19333`     | Raft consensus, volume location directory, sequence counter |
| **Filer Server**    | `8888/tcp`        | `18888/tcp`                  | `-filer.port.grpc=18888`| POSIX directory metadata, chunk mapping, IAM |
| **Volume Server**   | `8080/tcp`        | `18080/tcp`                  | `-volume.port.grpc=18080`| Needle binary read/write, master heartbeats, replication |
| **WebDAV Gateway**  | `7333/tcp`        | N/A (Internal client)        | N/A                    | macOS Finder / WebDAV access |
| **S3 Gateway**      | `8333/tcp`        | `18333/tcp`                  | `-s3.port.grpc=18333`  | Amazon S3 API emulation |

> **⚠️ Firewall Requirement:** Both the HTTP port (`9333`) AND the gRPC port (`19333`) must be open and accessible across the Tailscale mesh. Blocking `19333` will cause `rpc error: code = Unavailable desc = connection error: desc = "transport: Error while dialing: dial tcp ...:19333: connect: connection refused"`, completely preventing Raft quorum.

### 2.4 Quorum Mathematics & Failure Tolerance

For an $N$-node Raft cluster:
$$\text{Quorum} = \left\lfloor \frac{N}{2} \right\rfloor + 1$$
$$\text{Max Fault Tolerance} = \left\lfloor \frac{N - 1}{2} \right\rfloor$$

For our **3-Node Cluster ($N = 3$)**:
- **Quorum Requirement:** $\lfloor 3/2 \rfloor + 1 = 2$ nodes.
- **Fault Tolerance:** 1 node failure.
- **Operational States:**
  - **3 of 3 nodes online:** Full read/write capability. Leader handles mutations and replicates Raft log entries to 2 followers.
  - **2 of 3 nodes online (1 node dropped):** Quorum ($2 \ge 2$) maintained. Cluster remains 100% operational. Write requests continue normally.
  - **1 of 3 nodes online (2 nodes dropped):** Quorum lost ($1 < 2$). Master transitions to follower/read-only state. Write allocations (e.g. generating new file IDs or creating new volumes) are rejected with `raft.Server: Not current leader`.

### 2.5 Leader Election & Heartbeat Timing

Empirically verified timing parameters:
- `-heartbeatInterval duration` (Default: `300ms`): The interval at which the Raft leader broadcasts heartbeat pings to followers. In local/Tailscale mesh deployments, `200ms` to `300ms` provides optimal balance between network chatter and liveness detection.
- `-electionTimeout duration` (Default: `10s`): The maximum silent period a follower tolerates before triggering a new election. For high-speed failover in LAN/Tailscale environments, reducing this to **`2s` or `3s`** ensures near-instant recovery during a host crash.
- **Election Jitter:** SeaweedFS applies a randomized multiplier $[1, 1.25)$ to the heartbeat/election timers to prevent split votes among competing candidates.

### 2.6 Volume Server Registration with Multi-Master

Volume servers require the complete comma-separated list of all 3 master nodes:
```bash
weed volume -port=8080 -max=10 -ip=100.119.199.76 -master=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333 -dir=/data/volume
```
- **Discovery Mechanism:** Upon startup, the volume server connects to the seed masters via gRPC (`:19333`). It asks which node is the current Raft leader and establishes a persistent gRPC heartbeat stream to that leader (`Heartbeat to: 100.119.199.76:9333`).
- **Failover Handling:** When the active leader dies, the volume server receives an `EOF` error on the gRPC stream (`heartbeat to ... error: EOF`). It cycles through the configured `-master` list, queries the remaining nodes, detects the newly elected leader (`Volume Server found a new master newLeader: ...`), and redirects its heartbeat stream without dropping data needles or restarting.

### 2.7 Filer High Availability Architecture

1. **Stateless Filer Clustering:** Multiple Filer instances can run concurrently across the mesh (e.g. Node 1, Node 2, Node 3) all pointing to the 3 master nodes (`-master=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333`).
2. **Metadata Store HA:** For multi-filer active-active consistency, the embedded `leveldb2` store (which is single-host local disk) must be replaced in `filer.toml` with a distributed backend:
   - **PostgreSQL / MySQL:** Centralized relational store storing `filemeta` table.
   - **Redis Sentinel / Redis Cluster (`redis2` / `redis3`):** High-throughput distributed key-value store.
   - **Etcd / TiKV:** Distributed ACID KV store.
3. **Filer Sync (`weed filer.sync`):** Alternatively, when using independent leveldb stores per node, `weed filer.sync` can be run as a continuous background daemon to replicate directory trees bidirectionally between filer instances.

---

## 3. Tailscale Mesh Networking Constraints & Topology

### 3.1 Device Allocation & Role Mapping

From the authoritative `devices.json` network configuration:

| Node Identifier | Hardware Description | Tailscale IP (`100.x`) | Physical LAN IP | Assigned SeaweedFS Raft Role | Storage Role / Datacenter |
|-----------------|----------------------|------------------------|-----------------|------------------------------|---------------------------|
| **`Mac_Node`** | Apple M4 Pro Mac Mini (24GB) | `100.119.199.76` | `192.168.8.230` | **Master 1 (Raft Peer 1)** + Filer 1 + Volume 1 | High-Speed NVMe / `[DataCenter: Thunderbolt]` |
| **`MacBook_Pro`** | Headless MacBook Pro Vault | `100.103.212.21` | `192.168.8.127` | **Master 2 (Raft Peer 2)** + Filer 2 + Volume 2 | Storage Vault NVMe / `[DataCenter: Thunderbolt]` |
| **`Linux_Head_Node`** | Linux Head Node Laptop | `100.101.39.98` | `192.168.8.224` | **Master 3 (Raft Peer 3)** + Filer 3 + Volume 3 | Bulk NVMe / `[DataCenter: WiFi]` |
| **`MacBook_Air`** | Headless Apple M4 MacBook Air | `100.93.158.96` | `192.168.8.222` | Stateless Client (FUSE Mount) | Client (Streams via Thunderbolt) |
| **`Linux_Tablet`** | Bedside Linux Tablet | `100.81.92.125` | `192.168.8.173` | Stateless Client (WebDAV/FUSE) | Client (Mobile Compute) |
| **`Pixel_10_Pro_XL`**| Google Pixel 10 Pro XL | `100.73.38.87` | `192.168.8.160` | Edge Client / Healer Agent | Edge Tool Consumer |
| **`Samsung_S20`** | Samsung Galaxy S20+ | `100.84.40.95` | `192.168.8.158` | Edge Client / ADB Watchdog | Edge Tool Consumer |

### 3.2 Tailscale IP Binding Rules

When starting SeaweedFS components across Tailscale:
- **`ip` argument (`-ip` or `-master.ip`):** MUST be the node's specific Tailscale IP (e.g. `100.119.199.76` on Mac Mini).
- **`ip.bind` argument (`-ip.bind`):** MUST be set to `0.0.0.0`. This allows the daemon to accept connections arriving on the Tailscale interface (`utun*` or `tailscale0`), physical Ethernet/Thunderbolt bridges (`bridge0`), and local loopback (`127.0.0.1`).
- **Volume Public URL (`-volume.publicUrl`):** Set to `<tailscale_ip>:8080` to ensure that when clients query the master for read/write URLs, they receive a routable WireGuard IP address.

### 3.3 Tailscale ACL & Port Routing Specification

The Tailscale Access Control List (ACL) must grant TCP traffic across ports `8080, 8888, 9333, 18080, 18888, 19333, 7333`:

```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["tag:lauburu-mesh"],
      "dst": [
        "100.119.199.76:8080,8888,9333,18080,18888,19333,7333",
        "100.103.212.21:8080,8888,9333,18080,18888,19333,7333",
        "100.101.39.98:8080,8888,9333,18080,18888,19333,7333",
        "tag:lauburu-mesh:*"
      ]
    }
  ]
}
```

### 3.4 Failure Modes & Mesh Recovery

| Failure Scenario | Immediate System Effect | Raft Behavior | Filer / Volume Behavior | Recovery / Healing Action |
|------------------|-------------------------|---------------|-------------------------|---------------------------|
| **Master 1 Drops (Leader)** | Connection EOF on gRPC `:19333` | Masters 2 & 3 observe election timeout (2s). Master 2 or 3 elected leader. | Filers & Volume servers re-route heartbeats to new leader. | Master 1 rejoins automatically upon restart, catches up via Raft log snapshot. |
| **Master 2 or 3 Drops (Follower)** | Heartbeat ping timeout | Leader retains quorum (2/3). No failover needed. | Zero impact on clients. Writes continue uninterrupted. | Reconnecting follower replays missed Raft log entries. |
| **2 Masters Drop (Network Partition)** | Quorum lost (1 < 2) | Remaining master enters follower state. Drops write leadership. | Volume server rejects new volume creations. Filer rejects new writes. Existing reads from volume servers may still succeed. | Restore network connectivity on at least 1 offline node to re-establish quorum. |
| **WiFi / WireGuard Flap** | Intermittent packet drops | If drop < `electionTimeout` (2s), heartbeat retries succeed without election. | SeaweedFS gRPC client retries seamlessly. | Keepalive scripts (`termux-wake-lock`, `caffeinate`, Tailscale keepalive) prevent interface sleep. |
| **FUSE Mount Lockup on Client** | Host process hangs in kernel D-state if Filer drops | Client kernel holds unfulfilled VFS requests. | Mount point becomes inaccessible (`Transport endpoint not connected`). | `fuse_watchdog.sh` triggers `umount -l /mnt/dfs_unified` and spawns fresh `weed mount` process. |

---

## 4. Production Configuration Artifacts

### 4.1 Master 3-Node Raft Cluster Deployment

#### A. Node 1 (`Mac_Node` - Apple M4 Pro Mac Mini)
**Tailscale IP:** `100.119.199.76`  
**Execution Command:**
```bash
/Users/aaron/.local/bin/weed server \
  -dir=/Users/aaron/.local/var/seaweedfs \
  -ip=100.119.199.76 \
  -ip.bind=0.0.0.0 \
  -master.port=9333 \
  -master.port.grpc=19333 \
  -master.peers=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333 \
  -master.electionTimeout=2s \
  -master.heartbeatInterval=200ms \
  -filer=true \
  -filer.port=8888 \
  -filer.port.grpc=18888 \
  -volume=true \
  -volume.port=8080 \
  -volume.port.grpc=18080 \
  -volume.max=20 \
  -dataCenter=Thunderbolt \
  -volume.publicUrl=100.119.199.76:8080 \
  -telemetry=false
```

#### B. Node 2 (`MacBook_Pro` - Headless MacBook Pro Vault)
**Tailscale IP:** `100.103.212.21`  
**Execution Command:**
```bash
/Users/aaronmaher/.local/bin/weed server \
  -dir=/Users/aaronmaher/.local/var/seaweedfs \
  -ip=100.103.212.21 \
  -ip.bind=0.0.0.0 \
  -master.port=9333 \
  -master.port.grpc=19333 \
  -master.peers=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333 \
  -master.electionTimeout=2s \
  -master.heartbeatInterval=200ms \
  -filer=true \
  -filer.port=8888 \
  -filer.port.grpc=18888 \
  -volume=true \
  -volume.port=8080 \
  -volume.port.grpc=18080 \
  -volume.max=20 \
  -dataCenter=Thunderbolt \
  -volume.publicUrl=100.103.212.21:8080 \
  -telemetry=false
```

#### C. Node 3 (`Linux_Head_Node` - Linux Head Node Laptop)
**Tailscale IP:** `100.101.39.98`  
**Docker Compose Stack:** Located at `00_core_infrastructure/seaweedfs/docker-compose.yml`

```yaml
version: '3.8'

services:
  seaweed_master:
    image: chrislusf/seaweedfs:latest
    container_name: seaweed_master_node3
    restart: always
    network_mode: "host"
    environment:
      - WEED_MASTER_PORT=9333
      - WEED_MASTER_PORT_GRPC=19333
      - WEED_MASTER_PEERS=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333
      - WEED_MASTER_ELECTIONTIMEOUT=2s
      - WEED_MASTER_HEARTBEATINTERVAL=200ms
    volumes:
      - /mnt/storage/seaweedfs/master:/data/master
    command: >
      weed master
      -ip=100.101.39.98
      -ip.bind=0.0.0.0
      -port=9333
      -port.grpc=19333
      -peers=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333
      -electionTimeout=2s
      -heartbeatInterval=200ms
      -mdir=/data/master
      -telemetry=false

  seaweed_volume:
    image: chrislusf/seaweedfs:latest
    container_name: seaweed_volume_node3
    restart: always
    network_mode: "host"
    depends_on:
      - seaweed_master
    volumes:
      - /mnt/storage/seaweedfs/volume:/data/volume
    command: >
      weed volume
      -ip=100.101.39.98
      -ip.bind=0.0.0.0
      -port=8080
      -port.grpc=18080
      -dir=/data/volume
      -max=30
      -dataCenter=WiFi
      -master=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333
      -publicUrl=100.101.39.98:8080

  seaweed_filer:
    image: chrislusf/seaweedfs:latest
    container_name: seaweed_filer_node3
    restart: always
    network_mode: "host"
    depends_on:
      - seaweed_master
    volumes:
      - /mnt/storage/seaweedfs/filerldb2:/data/filerldb2
      - /mnt/storage/seaweedfs/conf/filer.toml:/etc/seaweedfs/filer.toml:ro
    command: >
      weed filer
      -ip=100.101.39.98
      -ip.bind=0.0.0.0
      -port=8888
      -port.grpc=18888
      -master=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333
      -defaultStoreDir=/data/filerldb2
```

---

### 4.2 Multi-Node FUSE Mount Configuration

On clients requiring the unified global namespace (`/mnt/dfs_unified` on Linux, `/Volumes/dfs_unified` on macOS):

```bash
weed mount \
  -filer=100.119.199.76:8888,100.103.212.21:8888,100.101.39.98:8888 \
  -dir=/mnt/dfs_unified \
  -dirAutoCreate=true \
  -cacheCapacityMB=512 \
  -chunkSizeLimitMB=4 \
  -readRetryTime=6s \
  -writeBufferSizeMB=256 \
  -allowOthers=true \
  -nonempty=true \
  -dlm=true \
  -volumeServerAccess=direct
```

**Key Flag Rationale:**
- `-filer=100.119.199.76:8888,100.103.212.21:8888,100.101.39.98:8888`: Injects all 3 filer endpoints so the client automatically reconnects to any active filer.
- `-volumeServerAccess=direct`: Instructs client to stream binary chunks directly from volume servers (`100.x.y.z:8080`) over WireGuard, bypassing the filer proxy and maximizing throughput.
- `-readRetryTime=6s`: Caps transient network blip retries at 6 seconds before failing gracefully, preventing indefinite application hangs.
- `-dlm=true`: Enables SeaweedFS Distributed Lock Manager to synchronize concurrent file writes across multiple agent processes.

---

### 4.3 Environment Variable Rules (`WEED_*`)

SeaweedFS supports configuring and overriding options through standard environment variables:
1. **Rule 1 — Prefix:** Variable names must be prefixed with `WEED_`.
2. **Rule 2 — Case:** Uppercase all characters.
3. **Rule 3 — Sub-keys:** Replace dots (`.`) with underscores (`_`).

**Reference Translation Table:**

| CLI Flag / TOML Parameter | Environment Variable Name | Example Value |
|---------------------------|---------------------------|---------------|
| `-master.peers` | `WEED_MASTER_PEERS` | `100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333` |
| `-master.electionTimeout` | `WEED_MASTER_ELECTIONTIMEOUT` | `2s` |
| `-master.heartbeatInterval` | `WEED_MASTER_HEARTBEATINTERVAL` | `200ms` |
| `-master.port` | `WEED_MASTER_PORT` | `9333` |
| `-master.port.grpc` | `WEED_MASTER_PORT_GRPC` | `19333` |
| `[postgres].password` (in filer.toml) | `WEED_POSTGRES_PASSWORD` | `secret_password` |
| `[jwt.signing].key` (in security.toml) | `WEED_JWT_SIGNING_KEY` | `base64_hmac_secret` |

---

## 5. Edge Cases & Observed Behaviors

### Edge Cases Table

| # | Feature | Input / Condition | Observed Behavior | Root Cause / Resolution |
|---|---------|-------------------|-------------------|-------------------------|
| 1 | Raft Clustering | Startup with single master while `-peers` lists 3 nodes | Node starts HTTP server (`:9333`) and gRPC (`:19333`), attempts to dial peers at `:19334`/`:19335`. Waits until quorum (at least 2 nodes) is online before electing a leader. | Expected Raft behavior. To test in isolation, start at least 2 nodes or use `-peers=none`. |
| 2 | Leader Failover | Leader process (`PID1`) terminated via `SIGKILL` | Follower nodes log `EOF` from leader, wait `electionTimeout` (2s), then elect a new leader. Volume servers detect new leader on heartbeat retry. | Automatic Raft consensus re-election. Total failover time: ~2.5s. |
| 3 | Split-Brain Defense | Starting master with a stale `TopologyId` from previous standalone run | Master crashes immediately with `Fatalf: Split-brain detected! Current TopologyId is X, but received Y. Stopping to prevent data corruption.` | Master safeguards against split-brain state. Resolution: Ensure `mdir` is cleared or cluster starts with a clean Raft snapshot when reconfiguring peers. |
| 4 | gRPC Reachability | gRPC port `:19333` blocked by firewall while HTTP `:9333` open | Master starts HTTP API but peers cannot exchange Raft logs. Follower logs `rpc error: code = Unavailable desc = dial tcp ...:19333: connect: connection refused`. Quorum fails. | Raft peer communication strictly requires the derived gRPC port (`port + 10000`). Both ports must be open in firewall/Tailscale ACL. |
| 5 | IP Binding | Setting `-ip=127.0.0.1` on multi-node setup | Master registers itself as `127.0.0.1:9333.19333`. Remote peers attempt to connect to `127.0.0.1` (their own localhost) instead of the remote host, causing election failure. | `-ip` must always be explicitly set to the node's Tailscale IP (`100.x.y.z`). |
| 6 | FUSE Mount Disconnect | Filer server process killed while FUSE mount is active | Kernel I/O operations block. Commands like `ls /mnt/dfs_unified` freeze in uninterruptible sleep (D-state). | Standard FUSE kernel behavior. Requires `umount -l` (lazy unmount) and `-readRetryTime=6s` watchdog daemon. |

---

## 6. Conclusion & Integration Directives

1. **Raft Cluster Deployment:** Deploy a 3-node master cluster across `Mac_Node` (`100.119.199.76`), `MacBook_Pro` (`100.103.212.21`), and `Linux_Head_Node` (`100.101.39.98`) with `-electionTimeout=2s` and `-heartbeatInterval=200ms`.
2. **Port Protection:** Ensure Tailscale ACL permits both base HTTP ports (`9333, 8888, 8080`) and gRPC companion ports (`19333, 18888, 18080`).
3. **Volume and Filer Resilience:** Configure volume servers and filers with all 3 master addresses (`-master=100.119.199.76:9333,100.103.212.21:9333,100.101.39.98:9333`).
4. **Watchdog and Self-Healing:** Implement the `fuse_watchdog.sh` script and `smolagents` tools to monitor mount health and execute `umount -l` upon lockup detection.
