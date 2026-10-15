# Test Infrastructure Architecture: WhatCable & Shark Wire E2E Test Suite (Port 4007)

## 1. Overview & Testing Philosophy

The Network Cable Analyzer E2E Test Suite provides rigorous, requirement-driven, opaque-box verification for the native **WhatCable Hardware & E-Marker Inspector** (R1) and the **Shark Wire Live Packet Capture & Streaming Engine** (R2 & R3).

In accordance with Cardinal Rule 1 (**Zero-Mock & Truth Verification Rule**) and Rule 8 (**Pre-Flight Network Telemetry Gate**), this test infrastructure is strictly grounded in authentic empirical hardware and network data:
1. **Zero Simulated Telemetry**: Cable parameters, E-marker vendor identifiers, and DisplayPort Alt Mode capabilities originate from authentic Darwin IOKit (`ioreg -r -c IOPort -l`), `system_profiler SPThunderboltDataType`, and live `whatcable --json --raw` binary probes.
2. **Binary Frame Fidelity**: Packet capture and dissection tests operate on RFC-compliant binary frames and authentic libpcap 2.4 captures (`tests/fixtures/mesh_traffic.pcap`), verifying byte offsets, endianness, checksums, and zero-copy slicing.
3. **Opaque-Box Verification**: Tests validate interfaces, schemas, mathematical boundaries, and operational error paths without coupling to private implementation internals.

---

## 2. Feature Inventory & Coverage Plan

| # | Feature Code | Feature Description | Requirement Source | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|--------------|---------------------|-------------------|:------:|:------:|:------:|:------:|
| 1 | **F1.1** | **E-Marker Chip Parameter Parsing**: Vendor ID/name, chip ID, 40G/20G/10G/480M bandwidth, 240W EPR / 100W / 60W profiles, PPS | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 2 | **F1.2** | **DisplayPort Alt Mode Capabilities**: Signaling rate (HBR3, DP 1.4/2.1), lanes, delivered vs needed Gbps, margin | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 3 | **F1.3** | **Cable Bottleneck Detection Rules**: Throttling, charge-only alert, generation downgrade, severities CRITICAL/WARNING/INFO/OPTIMAL | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 4 | **F1.4** | **Dual-Engine Probing & Resilience**: Direct Darwin IOKit fallback when `whatcable` CLI binary is absent or empty | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 5 | **F1.5** | **WhatCable REST API Endpoint**: `GET /api/whatcable/details` responding HTTP 200 with schema compliance | ORIGINAL_REQUEST §Acceptance | 5 | 5 | ✓ | ✓ |
| 6 | **F2.1** | **Interface Discovery**: Detection of `en0` 10GbE, `en1` Wi-Fi 7, `bridge0` 40G TB4, `utun3`/`utun4`, virtual `any` multiplexer | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 7 | **F2.2** | **Ring Buffer & PCAP Export**: Bounded 5,000-packet ring buffer, FIFO eviction, pause/resume/clear, libpcap 2.4 binary export | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 8 | **F2.3** | **Display Filter Engine**: AST tokenizer, parser, and compiled evaluator for protocol, IP, port, length, boolean logic | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 9 | **F2.4** | **Shark Wire REST & Streaming Endpoints**: `/api/packets/interfaces`, `/api/packets/stream` (SSE), `/filter`, `/control`, `/export_pcap` | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 10 | **F3.1** | **WireGuard Overlay Dissection**: Handshake Init (148B), Handshake Resp (92B), Cookie Reply (64B), Data (>=32B) on UDP 41641 | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 11 | **F3.2** | **Local AI RPC Dissection**: HTTP/1.1 requests, JSON payloads, SSE stream delta tokens, HTTP/2 frames on Ports 8081–8084 | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 12 | **F3.3** | **Darwin Loopback & utun Dissection**: DLT_NULL 4-byte AF family headers and raw IP frames without Ethernet headers | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 13 | **F3.4** | **Layer 2–4 Standard Dissection**: Ethernet II, IPv4, IPv6, TCP flags/seq/ack/options, UDP, ICMP | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |

---

## 3. 4-Tier Test Methodology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    4-TIER OPAQUE-BOX TEST METHODOLOGY                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 1: FEATURE COVERAGE (>=5 tests per major feature)                      │
│ • Primary happy paths, interface contracts, and schema invariants.          │
│ • Total Cases: 65                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 2: BOUNDARY & CORNER CASES (>=5 tests per major feature)               │
│ • Zero values, overflows, truncated buffers, extreme bandwidths, AST fuzz.  │
│ • Total Cases: 40                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 3: CROSS-FEATURE INTERACTIONS (Pairwise Combinations)                  │
│ • Hardware probe -> bottleneck evaluation -> API delivery.                  │
│ • Packet capture -> ring buffer -> AST filter -> PCAP export round-trip.   │
│ • Total Cases: 10                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 4: REAL-WORLD APPLICATION SCENARIOS (Operational Workflows)             │
│ • M4 Pro Mac Mini Host live hardware validation.                            │
│ • Live WireGuard mesh key exchange & 40Gbps TB4 Local AI RPC stream.       │
│ • Total Cases: 6                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Tier 1: Feature Coverage (Primary Behavior)
- **WhatCable Hardware Inspector (`test_whatcable_integration.py`)**:
  - `test_t1_whatcable_iokit_ioport_probing`: Verifies direct extraction of `IOPort` components from Darwin IOKit.
  - `test_t1_whatcable_cli_execution`: Verifies `/Users/aaron/.local/bin/whatcable --json --raw` parsing.
  - `test_t1_emarker_vendor_lintes`: Verifies mapping of Vendor ID `11037` (`0x2B1D`) to `"Lintes Technology Co., Ltd."`.
  - `test_t1_emarker_vendor_tankya`: Verifies mapping of Vendor ID `11564` (`0x2D2C`) to `"Tankya Developing Co., Limited"`.
  - `test_t1_emarker_power_delivery_240w_epr`: Verifies parsing of 50V, 5A, 240W Extended Power Range rating with PPS support.
  - `test_t1_emarker_bandwidth_ratings`: Verifies 40 Gbps, 20 Gbps, 10 Gbps, and 480 Mbps speed ratings.
  - `test_t1_dp_alt_mode_signaling_hbr3`: Verifies 8.1 Gbps HBR3 signaling rate across 4 lanes.
  - `test_t1_dp_alt_mode_bandwidth_math`: Verifies delivered (25.92 Gbps) vs needed (8.16 Gbps) and headroom calculation (+17.76 Gbps).
  - `test_t1_dp_alt_mode_monitor_identity`: Verifies detection of `MP245 E14VL` display.
  - `test_t1_bottleneck_critical_rule`: Verifies high-speed peer throttled to $\le 480\text{ Mbps}$ triggers `CRITICAL`.
  - `test_t1_bottleneck_warning_charge_only`: Verifies SuperSpeed device on charge-only cable triggers `WARNING`.
  - `test_t1_bottleneck_info_headroom`: Verifies 40 Gbps cable on 80 Gbps TB5 port triggers `INFO`.
  - `test_t1_bottleneck_optimal_rule`: Verifies matching cable and line rate triggers `OPTIMAL`.
  - `test_t1_api_whatcable_details_status`: Verifies `GET /api/whatcable/details` returns HTTP 200.
  - `test_t1_api_whatcable_details_schema`: Verifies response schema (`status`, `engine`, `summary`, `ports`, `display_ports`).

- **Shark Wire Packet Engine (`test_shark_wire_packet_engine.py`)**:
  - `test_t1_interface_discovery_en0_bridge0`: Verifies discovery of active physical interfaces (`en0`, `bridge0`, `en1`).
  - `test_t1_interface_discovery_utun`: Verifies discovery of dynamic VPN interfaces (`utun3`, `utun4`).
  - `test_t1_interface_discovery_virtual_any`: Verifies Darwin virtual multiplexer pseudo-interface `any`.
  - `test_t1_ring_buffer_capacity_5000`: Verifies maximum queue length is bounded at exactly 5,000 packets.
  - `test_t1_ring_buffer_fifo_eviction`: Verifies FIFO eviction when adding beyond 5,000 packets.
  - `test_t1_ring_buffer_pause_resume`: Verifies packet ingestion pause and resume state toggle.
  - `test_t1_ring_buffer_clear`: Verifies clearing buffer empties deque and updates epoch.
  - `test_t1_ring_buffer_pcap_export`: Verifies binary export produces valid libpcap 2.4 header (`0xA1B2C3D4`).
  - `test_t1_dissect_ethernet_ii`: Verifies destination MAC, source MAC, and EtherType parsing.
  - `test_t1_dissect_ipv4_and_flags`: Verifies IP addresses, TTL, protocol, and DF/MF flag dissection.
  - `test_t1_dissect_ipv6`: Verifies 40-byte fixed header, flow label, and 128-bit IPv6 addresses.
  - `test_t1_dissect_tcp_flags_options`: Verifies SYN, ACK, PSH, FIN flags and MSS/Window Scale options.
  - `test_t1_dissect_udp_and_icmp`: Verifies UDP ports and ICMP Echo Request/Reply headers.
  - `test_t1_dissect_wireguard_handshake_init`: Verifies Type 1 (148 bytes, sender index, ephemeral key, MACs).
  - `test_t1_dissect_wireguard_handshake_resp`: Verifies Type 2 (92 bytes, sender & receiver index, MACs).
  - `test_t1_dissect_wireguard_transport_data`: Verifies Type 4 (receiver index, 64-bit counter, payload).
  - `test_t1_dissect_local_ai_rpc_http11`: Verifies `POST /v1/chat/completions` on Port 8082 with model parameter.
  - `test_t1_dissect_local_ai_rpc_sse_chunks`: Verifies parsing of SSE delta chunks (`data: {"choices":[...]}`).
  - `test_t1_dissect_darwin_utun_dlt_null`: Verifies 4-byte AF family header (AF_INET = 2) and byte alignment.
  - `test_t1_filter_ast_parsing`: Verifies parsing of Wireshark syntax (`ip.addr == ... && tcp.port == ...`).
  - `test_t1_filter_evaluation`: Verifies compiled evaluator matches target packets accurately.
  - `test_t1_api_packets_endpoints`: Verifies HTTP 200 on `/api/packets/interfaces`, `/stream`, `/filter`, `/control`.

### 3.2 Tier 2: Boundary & Corner Cases
- **Boundary Cable Bandwidths**: Exact validation of 480 Mbps (USB 2.0), 5 Gbps (USB 3.2 Gen 1), 10 Gbps (USB 3.2 Gen 2), 20 Gbps (USB4 Gen 2 / TB3), 40 Gbps (USB4 Gen 3 / TB4), and 80/120 Gbps (TB5).
- **Boundary Power Profiles**: 0W (passive unpowered), 15W (standard 5V/3A), 60W (20V/3A non-E-marked), 100W (20V/5A SPR), 140W (28V/5A EPR), and 240W (48V-50V/5A EPR).
- **DisplayPort Headroom Boundaries**:
  - Exact zero headroom (`delivered_gbps == needed_gbps`).
  - Bandwidth deficit (`delivered_gbps < needed_gbps` -> triggers resolution downscale alert).
  - High refresh margin (`delivered_gbps >> needed_gbps`).
- **Resilience to Missing Tools**:
  - Missing `whatcable` CLI binary -> clean fallback to `ioreg` without exception.
  - Empty CLI output (`""`) -> fallback to `ioreg`.
  - Empty `ioreg` output -> returns empty list with valid schema.
  - Corrupted JSON from CLI -> graceful parse error handling.
- **Packet Engine Boundaries**:
  - 0 packets in ring buffer (export produces valid empty PCAP file).
  - Rapid flood of 10,000 packets (verifies buffer strictly preserves latest 5,000 without memory leak).
  - Truncated packet frames (< 14 bytes Ethernet, < 20 bytes IPv4).
  - WireGuard packets with unknown message types or malformed lengths.
  - Display filter code injection attempt (verifies AST parser rejects `__import__`, `eval`, or arbitrary Python without executing).

### 3.3 Tier 3: Cross-Feature Interactions
1. **IOKit Hardware Probing to Bottleneck Evaluation**: Probes live ports and verifies bottleneck evaluator processes real vendor ID and link speed into actionable remedies.
2. **DisplayPort Resolution to Bandwidth Headroom**: Correlates reported display mode (`1920x1080 @ 144Hz 8-bit`) with calculated pixel clock and link signaling rate.
3. **Packet Capture to Live SSE Streaming**: Ingests packets into ring buffer and verifies SSE stream broadcaster formats valid event chunks (`initial_batch`, `packet`, `stats`).
4. **AST Filter Compilation to In-Memory Query**: Compiles complex boolean filters (`(tcp.port == 8082 || udp.port == 41641) && len > 100`) and evaluates against 100 packets in $< 100\mu\text{s}$.
5. **Ring Buffer to Libpcap Round-Trip**: Appends packets to `SharkWireRingBuffer`, exports to binary PCAP, parses back via `struct`, and asserts 100% byte fidelity.

### 3.4 Tier 4: Real-World Operational Scenarios
1. **Mac Mini M4 Pro Host Hardware Audit**: Probes live ports on the host system, verifying active Lintes 240W TB4 cable on Port 1, Tankya 240W cable on Port 3, and MP245 display on Port-HDMI.
2. **Lauburu Mesh WireGuard Tunnel Handshake Exchange**: Dissects a 4-packet WireGuard session: Handshake Initiation $\to$ Handshake Response $\to$ Transport Data $\to$ Transport Data.
3. **Local AI Model Inference Session on Port 8082**: Dissects a complete `Qwen 3.8 Max 27B Abliterated` streaming session: HTTP/1.1 POST request $\to$ 10 SSE delta chunks $\to$ `data: [DONE]`.
4. **Simulated Charge-Only Cable Throttle Remedy**: Simulates a high-speed external drive attached via a 480 Mbps charge-only cable; asserts system surfaces `WARNING` severity with specific replacement advice.

---

## 4. Test Runner & Verification Commands

### 4.1 Running All WhatCable Integration Tests
```bash
pytest tests/test_whatcable_integration.py -v
```

### 4.2 Running All Shark Wire Packet Engine Tests
```bash
pytest tests/test_shark_wire_packet_engine.py -v
```

### 4.3 Running Specific Tiers
```bash
# Tier 1 Feature Coverage
pytest tests/test_whatcable_integration.py -k "t1" -v
pytest tests/test_shark_wire_packet_engine.py -k "t1" -v

# Tier 2 Boundary & Corner Cases
pytest tests/test_whatcable_integration.py -k "t2" -v
pytest tests/test_shark_wire_packet_engine.py -k "t2" -v

# Tier 3 Cross-Feature Interactions
pytest tests/test_whatcable_integration.py -k "t3" -v
pytest tests/test_shark_wire_packet_engine.py -k "t3" -v

# Tier 4 Real-World Application Scenarios
pytest tests/test_whatcable_integration.py -k "t4" -v
pytest tests/test_shark_wire_packet_engine.py -k "t4" -v
```

### 4.4 Automated Multi-Suite Execution
```bash
pytest tests/test_whatcable_integration.py tests/test_shark_wire_packet_engine.py -v --tb=short
```

---

## 5. Directory Layout & Test Artifacts

```
01_apps/network_cable_analyzer/
├── TEST_INFRA.md                          # Master Test Infrastructure Architecture (this document)
├── TEST_READY.md                          # Test Suite Publication & Execution Status
├── tests/
│   ├── test_whatcable_integration.py      # 4-Tier WhatCable E-Marker & Hardware Test Suite
│   ├── test_shark_wire_packet_engine.py   # 4-Tier Shark Wire Packet Engine Test Suite
│   ├── test_probes.py                     # Existing baseline probe tests
│   ├── test_network_cable_analyzer_mesh_integrations.py
│   └── fixtures/
│       ├── packet_samples.py              # RFC-compliant binary packet & PCAP generator
│       ├── mesh_traffic.pcap              # Authentic libpcap 2.4 capture (30 packets)
│       ├── whatcable_authentic_dump.json  # Authentic dump from whatcable 1.4.0 CLI
│       └── ioreg_ioport_dump.txt          # Authentic dump from Darwin IOKit IOPort probe
```
