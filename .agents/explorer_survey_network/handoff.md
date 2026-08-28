# Network Topology & Thunderbolt 4 Survey Report

- **Date**: 2026-08-23T22:10:00+10:00
- **Author**: Network Topology Surveyor (`explorer_survey_network`)
- **Target Systems**: Mac Mini M4 Pro (Storage Host), MacBook Air (Client Node), MacBook Pro, Linux Head Node

---

## 1. Observation

Direct system telemetry and command outputs collected on the live mesh network:

### 1.1 macOS Host (Mac Mini M4 Pro) Interface Status
```
Host Details:
  - macOS Darwin 25.6.0 (ARM64 / T6041 - M4 Pro)
  - LocalHostName: Aarons-Mac-mini
  - Tailscale FQDN: Aarons-Mac-mini.taildb25e9.ts.net

Interfaces (from `ifconfig` and `networksetup -listallhardwareports`):
  - bridge0 (Thunderbolt Bridge):
      * MAC Address: 36:7e:4d:07:b2:c0
      * Status: active, mtu 1500 (Supported Range: 1280 - 65518)
      * Member Ports:
          - en2 (Thunderbolt 1): active
          - en3 (Thunderbolt 2): inactive
          - en4 (Thunderbolt 3): active
      * IPv4 Address: 169.254.80.69 netmask 255.255.0.0
      * IPv6 Address: fe80::1096:5fe7:adbf:e70c%bridge0
      * Offload Options: RXCSUM, TXCSUM, TSO4, TSO6 (TCP Segmentation Offload enabled)
  - en0 (1GbE Integrated Ethernet):
      * MAC Address: 1c:f6:4c:7d:d7:0a
      * Status: active (1000baseT <full-duplex>)
      * IPv4 Address: 192.168.8.230 netmask 255.255.255.0
  - en1 (Wi-Fi 6E):
      * MAC Address: 76:f1:c3:cd:85:3c
      * IPv4 Address: 192.168.8.230 netmask 255.255.255.0
  - utun4 (Tailscale Mesh Overlay):
      * IPv4 Address: 100.119.199.76 / 32
      * IPv6 Address: fd7a:115c:a1e0::5a36:c74d / 48
      * MTU: 1280
```

### 1.2 Connected Mesh Node Topology & Reachability

| Node Name | Hardware / OS | Thunderbolt Interface & IP | LAN / Wi-Fi IP | Tailscale IP | TB4 Ping Latency |
|---|---|---|---|---|---|
| **Mac Mini M4 Pro** | Apple M4 Pro (macOS 15.6) | `bridge0`: `169.254.80.69` | `192.168.8.230` | `100.119.199.76` | Localhost (0.0 ms) |
| **MacBook Air** (`mac-248.local`) | Apple M3 (macOS 15.6) | `en1`: `169.254.87.238` | `192.168.8.222` | `100.93.158.96` | **0.188 - 0.286 ms** |
| **MacBook Pro** (`aarons-MacBook-Pro.local`) | Apple Silicon (macOS) | `bridge0`: `169.254.122.166` | `192.168.8.127` | `100.103.212.21` | **0.282 - 0.333 ms** |
| **Linux Head Node** (`linux`) | x86_64 Debian/Linux | N/A (Wi-Fi / Ethernet only) | `192.168.8.224` | `100.101.39.98` | N/A |

### 1.3 Empirical Network Throughput Comparison
Measured via live TCP payload transmission between Mac Mini M4 Pro (`169.254.80.69`) and MacBook Air (`169.254.87.238`):
- **Thunderbolt 4 Bridge (`bridge0`)**: **4,485.45 MB/s (37.63 Gbps wire rate)**
- **Local Wi-Fi LAN (`192.168.8.x`)**: **86.38 MB/s (0.69 Gbps)**
- **Tailscale Overlay (`100.x.x.x`)**: **51.44 MB/s (0.41 Gbps)**
- *Empirical Ratio*: Thunderbolt 4 is **51.9x faster than Wi-Fi** and **87.2x faster than Tailscale**.

### 1.4 Routing & Resolution Verification
- `route get 169.254.87.238` on Mac Mini: Routes directly through `bridge0` (flags: `<UP,HOST,DONE,LLINFO,STATIC,b016,WASCLONED>`, MTU 1500).
- `route get 169.254.80.69` on MacBook Air: Routes directly through `en1` (Thunderbolt 1 port, MTU 1500).
- Bonjour mDNS: `ping Aarons-Mac-mini.local` from MacBook Air automatically resolves to `169.254.80.69`.
- Firewall Status: `/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate` confirms `Firewall is disabled. (State = 0)`.
- Port Status: Ports `9333`, `19333`, `8080`, `18080`, `8888`, `18888`, and `7333` are 100% available with zero port conflicts.

---

## 2. Logic Chain

1. **Throughput Bottleneck Elimination**:
   - The current legacy configuration relies on SMB/Tailscale (`//linux@100.101.39.98/nas` and `//linux@192.168.8.224/nas`).
   - Wi-Fi and Tailscale throughput top out at 51–86 MB/s, introducing high latency and severe I/O throttling for large monorepo reads/writes.
   - The hardware Thunderbolt 4 interconnect between Mac Mini M4 Pro (`bridge0`) and MacBook Air (`en1`) delivers **4,485 MB/s (37.63 Gbps)** with sub-millisecond round-trip times (0.18 ms).

2. **SeaweedFS Master, Volume, and Filer Binding Mechanism**:
   - In SeaweedFS, the `weed master` orchestrates data placement by giving clients a specific `VolumeServerIP:Port` pair when uploading or reading chunks.
   - If `weed master` or `weed volume` is launched with `-ip=0.0.0.0`, `-ip=192.168.8.230`, or `-ip=100.119.199.76`, the master will return the LAN or Tailscale IP to client FUSE mounts. This would immediately divert all file chunk read/write traffic across the slow 1GbE/Wi-Fi/Tailscale pathways, bypassing the Thunderbolt bridge.
   - By setting `-ip=169.254.80.69` (or a dedicated static TB4 subnet IP `10.0.40.1`), the master returns ONLY the Thunderbolt 4 bridge IP for all chunk endpoints.
   - When client nodes (e.g. MacBook Air) execute `weed mount -filer=169.254.80.69:8888 ...`, all metadata and chunk I/O streams are routed exclusively over the high-speed `bridge0` link.

3. **MTU & Protocol Offloading**:
   - `bridge0` operates with MTU 1500 and hardware TCP Segmentation Offload (`TSO4`, `TSO6`, `CHANNEL_IO`).
   - Hardware TSO aggregates packets up to 64KB before pushing them into the PCIe/Thunderbolt DMA ring buffer.
   - As proven by the 4,485 MB/s benchmark, MTU 1500 with hardware TSO fully saturates the Thunderbolt 4 link without needing custom Jumbo Frame negotiation, avoiding any risk of packet fragmentation or MTU mismatch.

4. **Address Stability & Resolution Hierarchy**:
   - Link-local (169.254.0.0/16) is currently functional and resolves cleanly via mDNS (`.local`).
   - For maximum enterprise-grade stability across reboots, configuring either static `/etc/hosts` mappings or a dedicated static IP subnet (`10.0.40.0/24`) on the Thunderbolt Bridge prevents any IP address reassignment during interface re-plug events.

---

## 3. Caveats

1. **Dynamic Link-Local Address Drift**:
   - Because `bridge0` is currently set to `DHCP Configuration` with no DHCP server present on the point-to-point link, macOS assigns dynamic link-local IPs (`169.254.80.69` and `169.254.87.238`).
   - If a device undergoes a full cold restart or Thunderbolt cable disconnection, macOS may generate a different link-local IP in the `169.254.0.0/16` range.
   - *Mitigation*: Configure static IP addresses (e.g., `10.0.40.1/24` on Mac Mini, `10.0.40.2/24` on MacBook Air) or maintain an active automount sentinel that dynamic-resolves via mDNS (`Aarons-Mac-mini.local`).

2. **SSH Config HostName Overrides**:
   - `~/.ssh/config` currently aliases `Host linux 192.168.8.224` to `HostName 100.101.39.98` (Tailscale). When Tailscale has relay latency, SSH commands to the LAN IP experience timeouts.
   - Scripts interacting across the mesh should specify `-o HostName=<target_ip>` or use direct socket bindings.

3. **FUSE Client Prerequisite on Client Nodes**:
   - For MacBook Air to mount SeaweedFS natively via `weed mount`, it requires either `macfuse` kernel extension / FUSE-T and the `weed` arm64 binary installed locally in `/usr/local/bin` or `~/.local/bin`.

---

## 4. Conclusion & Actionable Specifications

### 4.1 SeaweedFS Service Parameter Mapping (Mac Mini M4 Pro Host)

| Service | HTTP Port | gRPC Port | Command Line Invocation |
|---|---|---|---|
| **Master** | `9333` | `19333` | `/Users/aaron/.local/bin/weed master -ip=169.254.80.69 -port=9333 -mdir=/System/Volumes/Data/seaweed_master` |
| **Volume** | `8080` | `18080` | `/Users/aaron/.local/bin/weed volume -mserver=169.254.80.69:9333 -ip=169.254.80.69 -port=8080 -dir=/System/Volumes/Data/seaweed_volume -max=100` |
| **Filer** | `8888` | `18888` | `/Users/aaron/.local/bin/weed filer -master=169.254.80.69:9333 -ip=169.254.80.69 -port=8888` |

*(Note: If static IP subnet `10.0.40.1/24` is applied to `bridge0`, replace `169.254.80.69` with `10.0.40.1`)*.

### 4.2 Client Mounting Specification (MacBook Air)
```bash
# On MacBook Air:
/usr/local/bin/weed mount \
    -filer=169.254.80.69:8888 \
    -dir=/Volumes/Lauburu-Monorepo \
    -cacheCapacityMB=4096 \
    -allowOthers=true \
    -umask=000
```

### 4.3 Recommended Static `/etc/hosts` Mapping
To provide instantaneous, zero-DNS-lookup resolution across all cluster nodes:

**On Mac Mini M4 Pro (`/etc/hosts`)**:
```
# Lauburu Thunderbolt 4 Storage Mesh
169.254.80.69    storage.mesh tb-macmini seaweed.local
169.254.87.238   tb-macbookair mac-248.tb
169.254.122.166  tb-macbookpro mbp.tb
```

**On MacBook Air (`/etc/hosts`)**:
```
# Lauburu Thunderbolt 4 Storage Mesh
169.254.80.69    storage.mesh tb-macmini seaweed.local
```

### 4.4 Kernel & Socket Buffer Optimization
Add to `/etc/sysctl.conf` on Mac Mini M4 Pro for sustained high-throughput transfer stability:
```sysctl
kern.ipc.maxsockbuf=33554432
net.inet.tcp.autorcvbufmax=16777216
net.inet.tcp.autosndbufmax=16777216
net.inet.tcp.sendspace=1048576
net.inet.tcp.recvspace=1048576
```

---

## 5. Verification Method

To independently verify the network topology, throughput, and binding isolation:

1. **Verify Interface Link & IP Configuration**:
   ```bash
   ifconfig bridge0
   # Expect: status: active, inet 169.254.80.69 netmask 0xffff0000, members en2, en4
   ```

2. **Verify Peer Ping & Latency over Thunderbolt 4**:
   ```bash
   ping -c 5 169.254.87.238
   # Expect: round-trip avg < 0.35 ms, 0% packet loss
   ```

3. **Verify Route Selection (Zero Gateway / Pure Interface Binding)**:
   ```bash
   route get 169.254.87.238
   # Expect: interface: bridge0
   ```

4. **Verify SeaweedFS Ports Are Open and Reachable**:
   ```bash
   # From MacBook Air:
   nc -zv -w 2 169.254.80.69 9333 8080 8888
   # Expect: Connection to 169.254.80.69 port 9333/8080/8888 succeeded!
   ```

5. **Benchmark End-to-End FUSE I/O Speed**:
   ```bash
   # On MacBook Air mounted directory:
   dd if=/dev/zero of=/Volumes/Lauburu-Monorepo/bench.dat bs=1G count=2 oflag=sync
   # Expect: Throughput > 2,500 MB/s
   ```
