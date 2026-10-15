
### Audit: 2026-10-12 14:57:04 AEST
- **Container Status**: `RUNNING`
- **Dependencies**: `FAILED`
- **Peers**: 3 registered
  - `10.42.0.2/32`: IDLE
  - `10.42.0.6/32`: IDLE
  - `10.42.0.7/32`: IDLE

### Audit: 2026-10-12 15:00:29 AEST
- **Container Status**: `RUNNING`
- **Dependencies**: `FAILED`
- **Peers**: 3 registered
  - `10.42.0.2/32`: IDLE
  - `10.42.0.6/32`: IDLE
  - `10.42.0.7/32`: IDLE

### Audit: 2026-10-13 05:02:54 AEST
- **Container Status**: `RUNNING`
- **Dependencies**: `FAILED`
- **Peers**: 3 registered
  - `10.42.0.2/32`: IDLE
  - `10.42.0.6/32`: IDLE
  - `10.42.0.7/32`: IDLE

### Audit: 2026-10-13 05:04:37 AEST
- **Container Status**: `RUNNING`
- **Dependencies**: `FAILED`
- **Peers**: 3 registered
  - `10.42.0.2/32`: IDLE
  - `10.42.0.6/32`: IDLE
  - `10.42.0.7/32`: IDLE

### Audit: 2026-10-13 05:05:34 AEST
- **Container Status**: `RUNNING`
- **Dependencies**: `FAILED`
- **Peers**: 3 registered
  - `10.42.0.2/32`: IDLE
  - `10.42.0.6/32`: IDLE
  - `10.42.0.7/32`: IDLE

### Audit: 2026-10-14 23:43:04 AEST
- **Container Status**: `RUNNING`
- **Dependencies**: `FAILED`
- **Peers**: 3 registered
  - `10.42.0.2/32`: IDLE
  - `10.42.0.6/32`: IDLE
  - `10.42.0.7/32`: IDLE

### Audit: 2026-10-15 12:10:04 AEST
- **Container Status**: `RUNNING`
- **Dependencies**: `PASSED`
- **Peers**: 3 registered
  - `10.42.0.2/32`: IDLE
  - `10.42.0.6/32`: IDLE
  - `10.42.0.7/32`: IDLE

### Audit: 2026-10-15 12:12:53 AEST
- **Container Status**: `RUNNING`
- **Dependencies**: `PASSED`
- **Peers**: 3 registered
  - `10.42.0.2/32`: ACTIVE
  - `10.42.0.6/32`: IDLE
  - `10.42.0.7/32`: IDLE

### Sovereign WireGuard & Podman Mesh Audit: 2026-10-15 12:13:58 AEDT
> **Governing Rule:** [[00_Overview/Hardware_Topology]], [[01_zero_mock_truth_rule]], [[LIGHTWEIGHT_WIREGUARD_DERP_MESH_SPEC]]
> **Host Sanctuary:** Offloaded compute to L8 (`lauburu` Apple `Macmini8,1` 32GB RAM) per [[10_linux_mini_first_offload_rule]].

#### 1. Hardware Control Plane & 40Gbps TB4 Transport
| Parameter | Empirical Value | Status |
|:---|:---|:---:|
| **Target Node** | L8 (`lauburu` / Intel i7-8700B 6C/12T, 32GB DDR4) | 🟢 ONLINE |
| **Active Transport** | `40Gbps Thunderbolt 4 (Bus 0 / bridge0)` (`10.0.0.8`) | 🟢 ACTIVE |
| **Measured RTT** | `14.823 ms` | 🟢 LOW-LATENCY |
| **Container Runtime** | Podman (rootful netavark) on Ubuntu 24.04.1 | 🟢 HEALTHY |
| **Direct SSH Port 2222** | `root@10.0.0.8:2222` | 🟢 ACCESSIBLE |
| **Container ID** | `bcce966ce742` | 🟢 RUNNING |
| **Container Memory RSS** | `2.871MB / 33.49GB` | 🟢 SPARING HOST VRAM |

#### 2. Sovereign WireGuard Overlay (`10.42.0.0/24`) Peer Handshakes
| Node | Role & Hardware | Overlay IP | Endpoint | Handshake Age | Rx / Tx | Handshake Status |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| **L1** | Mac Mini M4 Pro (Host / Governor) | `10.42.0.2/32` | `10.0.0.2:63182` | 89s ago | 660B / 476B | 🟢 ACTIVE |
| **L6** | Pixel 10 Pro XL (Termux Edge) | `10.42.0.6/32` | `(none)` | Never | 0B / 0B | ⚪ IDLE / READY |
| **L6-AVF** | Pixel 10 Pro XL (AVF Debian 13 microVM) | `10.42.0.7/32` | `(none)` | Never | 0B / 0B | ⚪ IDLE / READY |

#### 3. Container Project Dependency Audit (Python 3.14 Standalone Parity)
- **Runtime Environment**: `3.14.8 (x86_64)` in isolated Podman venv
- **Verification Status**: `🟢 PASSED (16/16 Modules)` in `1.521s`
- **DSP Math Engine**: `🟢 512-Sample Wave Synthesized & Verified`
- **Cryptographic Core**: `🟢 AES-256-CBC Verified`

| Module Category | Installed & Verified Packages |
|:---|:---|
| **Web & Networking** | `fastapi`, `uvicorn`, `pydantic`, `psutil`, `httpx`, `aiohttp`, `websockets` |
| **DSP & Hardware Telemetry** | `numpy`, `scipy`, `bleak` |
| **Storage & Cryptography** | `cryptography`, `pyyaml`, `pyarrow`, `pandas` |
| **Testing & Terminal TUI** | `pytest`, `rich` |

#### 4. 7-Layer Mesh Overlay Connectivity Snapshot
| Node Hostname | Overlay IP | Direct Transport Path | Status |
|:---|:---:|:---|:---:|
| **Pixel 10 Pro XL** | `100.114.215.68` | `192.168.8.213:47501` | 🟢 DIRECT |
| **tailscale-termux** | `100.124.199.15` | `192.168.8.101:48556` | 🟢 DIRECT |
| **localhost** | `100.116.111.43` | `DERP (syd)` | 🟡 RELAY |
| **Aaron's S20+** | `100.69.56.102` | `DERP (syd)` | 🟡 RELAY |
| **lauburu** | `100.121.247.8` | `192.168.8.242:41641` | 🟢 DIRECT |
| **Aaron’s Mac mini (6)** | `100.104.128.34` | `DERP (syd)` | 🟡 RELAY |
| **linux** | `100.101.39.98` | `192.168.8.225:41641` | 🟢 DIRECT |
| **localhost** | `100.113.82.81` | `DERP (syd)` | 🟡 RELAY |
| **Macbook (603)** | `100.121.202.34` | `192.168.8.172:41641` | 🟢 DIRECT |
| **mac-pro** | `100.103.212.21` | `192.168.8.127:41641` | 🟢 DIRECT |
| **GL-BE14000** | `100.70.123.123` | `DERP (syd)` | 🟡 RELAY |
| **debian** | `100.80.64.5` | `192.168.8.213:41641` | 🟢 DIRECT |
| **tablet** | `100.118.79.63` | `DERP (syd)` | 🟡 RELAY |

