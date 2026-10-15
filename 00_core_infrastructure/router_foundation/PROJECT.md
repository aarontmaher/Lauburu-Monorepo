# Project: GL.iNet Router Bluetooth & Network Foundation (Omni-Lens Sovereign Mesh)

## Architecture
- Subsystems:
  1. OpenWrt Router Gateway (`192.168.8.1`, GL-BE14000 aarch64, 2GB RAM, Realtek RTL8761BU USB Dongle `hci0`).
  2. 10GbE Sub-Millisecond Transport (0.606ms - 0.889ms RTT between Router `eth2` and Mac Mini `en0` `192.168.8.230`).
  3. Mac Mini Ingestion & Lens Engine (L1 Mac Mini M4 Pro, AsyncIO TCP listener, multi-mode framer, DSP).
  4. Unified ZMQ Mesh Bus (XSUB `:5550`, XPUB `:5555`).
  5. Autonomous Resiliency & Self-Healing (POSIX `/bin/sh` procd service, multi-target Layer 3 ICMP ping, direct `ip route replace`).
  6. Edge Security & Screen Lens Radar (OpenWrt targeted `tcpdump`/conntrack, Mac Mini visual radar generator on Port 4003).

## Feature Inventory
| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|--------|
| 1 | Router Bluetooth Daemon | OpenWrt procd service running btmon + socat on port 9002 with BLE discovery | M1 | ORIGINAL_REQUEST §R1 | DONE |
| 2 | Mac Mini Ingestion Daemon | AsyncIO kqueue daemon on Mac Mini ingesting TCP:9002/19001 with TCP_NODELAY | M2 | ORIGINAL_REQUEST §R2 | DONE |
| 3 | Movesense GATT 0x2A37 DSP | Real-time Heart Rate, Kamath 20% filter, RMSSD, DFA-alpha1 parser | M2 | ORIGINAL_REQUEST §R2 | DONE |
| 4 | Whoop & SmartThings Parsers | OpenWearables normalization and Samsung 0x0075 beacon proximity parser | M2 | ORIGINAL_REQUEST §R2 | DONE |
| 5 | ZMQ Mesh Publisher | ZMQ PUB socket publishing MESH.STATE, MESH.TELEMETRY, BLE.RAW to port 5550 | M2 | ORIGINAL_REQUEST §R2 | DONE |
| 6 | DHCP Lease Oracle | OpenWrt /etc/hotplug.d/dhcp hook publishing lease updates in <50ms | M3 | ORIGINAL_REQUEST §R3 | DONE |
| 7 | ARP Link State Oracle | rtnetlink `ip monitor neigh dev br-lan` publishing neighbor changes in <2ms | M3 | ORIGINAL_REQUEST §R3 | DONE |
| 8 | Autonomous NBN Failover | OpenWrt POSIX /bin/sh 6-state FSM with L3 ICMP probing and `ip route` actuation | M4 | ORIGINAL_REQUEST §R4 | DONE |
| 9 | Targeted Edge Capture | OpenWrt tcpdump filter for SYN/RST/ARP/TTL<=1/ICMP streaming over 10GbE | M5 | ORIGINAL_REQUEST §R5 | DONE |
| 10| Visual Security Radar | Real-time network anomaly/loop/rogue MAC detection rendered to Port 4003 MJPEG | M5 | ORIGINAL_REQUEST §R5 | DONE |
| 11| Full E2E Test Suite | 5-Tier opaque-box test suite verifying all 5 Acceptance Criteria | E2E | ORIGINAL_REQUEST §AC | DONE |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Router-Native Bluetooth Hub | OpenWrt `/etc/init.d/router_bluetooth_hub` (btmon + socat on TCP:9002, BLE scan) | none | DONE |
| M2 | Mac Mini 10GbE Lens Ingester | `lens_10gbe_ingester.py` (AsyncIO listener, Movesense/Whoop/SmartThings DSP, ZMQ PUB) | M1 contract | DONE |
| M3 | DHCP/ARP Presence Oracle | `/etc/hotplug.d/dhcp/10-mesh_dhcp_oracle.sh` and `/usr/bin/mesh_arp_oracle.sh` | none | DONE |
| M4 | Out-Of-Band Self-Healer | `/usr/bin/lauburu_oob_wan_healer.sh` + procd service `/etc/init.d/wan_healer` | none | DONE |
| M5 | Edge Security Red Team | Router capture streamer + `lens_edge_security_monitor.py` with Screen Lens Radar | M1-M3 | DONE |
| M-Final | Dual-Track E2E Test Pass & Hardening | Automated verification of 5/5 Acceptance Criteria + Adversarial coverage | M1-M5 | DONE |

## Interface Contracts
### Router (M1) ↔ Mac Mini Ingester (M2)
- Protocol: TCP raw stream over 10GbE (`192.168.8.1:9002` or `0.0.0.0:19001`)
- Transport Options:
  1. Raw HCI H4 stream: `btmon -s /tmp/btmon.sock` forwarded via `socat TCP-LISTEN:9002,fork,reuseaddr UNIX-CONNECT:/tmp/btmon.sock`
  2. NDJSON stream: `{"timestamp": <float>, "type": "ADV_IND"|"GATT_VAL", "mac": "<str>", "rssi": <int>, "payload_hex": "<hex>"}\n`
  3. Binary TLV: `[2B Tag][2B Length][Value]`
- Error Handling: Auto-reconnect with exponential backoff, keepalive probes, non-blocking buffers.

### Presence Oracle (M3) ↔ ZMQ Mesh (M2 / Hub)
- Protocol: UDP or HTTP/TCP post to Mac Mini port 9100 / ZMQ `tcp://127.0.0.1:5550`
- Topic: `MESH.TELEMETRY.PRESENCE`
- Schema:
  `{"timestamp": <float>, "event": "LEASE_ADD"|"LEASE_DEL"|"NEIGH_UP"|"NEIGH_DOWN", "mac": "<MAC>", "ip": "<IP>", "hostname": "<str>", "interface": "br-lan", "latency_ms": <float>}`

### Out-Of-Band Failover (M4)
- Probing Targets: `1.1.1.1`, `8.8.8.8`, `9.9.9.9` bound to `eth1` (or WAN device)
- Actuation: Sub-millisecond direct kernel route replacement:
  `ip route replace default scope global via <backup_gw> dev <backup_dev> metric 10`
- Zero external dependencies: pure POSIX `/bin/sh` running as OpenWrt procd service.

### Edge Security (M5) ↔ Screen Lens (Port 4003)
- Capture Filter: `(tcp[tcpflags] & (tcp-syn|tcp-rst) != 0) or arp or (ip[8] <= 1) or (icmp[icmptype] == 11)`
- Stream: TCP port 9005 over 10GbE
- Radar: 2D matrix rendering anomaly alerts and rogue MAC warnings directly into `/stream.mjpg`.

## Code Layout
`00_core_infrastructure/router_foundation/`
├── `PROJECT.md`                       # Canonical architecture and milestone index
├── `TEST_INFRA.md`                     # E2E Test Suite infrastructure specification
├── `TEST_READY.md`                     # Test suite readiness indicator
├── `router/`
│   ├── `etc/init.d/router_bluetooth_hub`   # OpenWrt procd service for R1 (btmon + socat + ble_scanner)
│   ├── `etc/init.d/wan_healer`             # OpenWrt procd service for R4
│   ├── `etc/init.d/mesh_arp_oracle`        # OpenWrt procd service for R3
│   ├── `etc/init.d/edge_security_streamer` # OpenWrt procd service for R5
│   ├── `usr/bin/lauburu_oob_wan_healer.sh` # POSIX ash autonomous failover FSM
│   ├── `usr/bin/mesh_arp_oracle.sh`        # rtnetlink ip monitor neigh daemon for R3
│   ├── `etc/hotplug.d/dhcp/10-mesh_dhcp_oracle.sh` # Dnsmasq lease event hook for R3
│   └── `usr/bin/edge_security_streamer.sh` # Targeted tcpdump streamer for R5
├── `host/`
│   ├── `lens_10gbe_ingester.py`            # Mac Mini 10GbE AsyncIO Ingestion Daemon for R2
│   ├── `presence_oracle_receiver.py`       # Mac Mini Presence Ingester -> ZMQ for R3
│   ├── `lens_edge_security_monitor.py`     # Lens tcpdump analyzer & visual radar for R5
│   └── `parsers/`
│       ├── `movesense_parser.py`           # GATT 0x2A37, Kamath 20%, RMSSD, DFA-alpha1
│       ├── `whoop_parser.py`               # OpenWearables biometrics normalizer
│       └── `smartthings_parser.py`         # Samsung 0x0075 beacon proximity parser
├── `deploy/`
│   ├── `deploy_to_router.sh`               # Idempotent deployment script to GL.iNet router
│   └── `verify_router_foundation.sh`       # Live empirical probe & test runner (pipefail enforced)
└── `tests/`
    ├── `test_router_bluetooth_hub.py`      # Unit/Mock tests for R1
    ├── `test_lens_10gbe_ingester.py`       # Unit & DSP tests for R2
    ├── `test_presence_oracle.py`           # Unit & Latency tests for R3
    ├── `test_oob_wan_healer.py`            # FSM simulation & route logic tests for R4
    ├── `test_edge_security_monitor.py`     # BPF & anomaly detection tests for R5
    ├── `test_e2e_router_foundation.py`     # Master E2E Acceptance Criteria test suite
    ├── `test_adversarial_network_stress.py`# Challenger 1 network stress test suite
    ├── `test_adversarial_failover_and_security.py` # Challenger 2 failover/security test suite
    └── `test_router_remediation_regression.py` # Regression test suite for remediation
