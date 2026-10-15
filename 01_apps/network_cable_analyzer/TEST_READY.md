# E2E Test Suite Ready: WhatCable & Shark Wire Integration (Port 4007)

## 1. Master Test Runners

Execute all tests from the project root (`01_apps/network_cable_analyzer`):

```bash
# Run both test suites simultaneously
pytest tests/test_whatcable_integration.py tests/test_shark_wire_packet_engine.py -v

# Run WhatCable Hardware & E-Marker Inspector test suite
pytest tests/test_whatcable_integration.py -v

# Run Shark Wire Live Packet Engine test suite
pytest tests/test_shark_wire_packet_engine.py -v
```

### Running Specific Tiers
```bash
# Tier 1: Feature Coverage
pytest tests/test_whatcable_integration.py tests/test_shark_wire_packet_engine.py -k "t1" -v

# Tier 2: Boundary & Corner Cases
pytest tests/test_whatcable_integration.py tests/test_shark_wire_packet_engine.py -k "t2" -v

# Tier 3: Cross-Feature Interactions
pytest tests/test_whatcable_integration.py tests/test_shark_wire_packet_engine.py -k "t3" -v

# Tier 4: Real-World Application Scenarios
pytest tests/test_whatcable_integration.py tests/test_shark_wire_packet_engine.py -k "t4" -v
```

---

## 2. Current Execution Status & Baseline Results

- **Environment**: macOS Darwin (Mac Mini M4 Pro L1 Host), Python 3.13.15, pytest 9.1.1
- **Exit Code**: `0`
- **Total Test Cases**: `78`
- **Execution Summary**: **73 PASSED, 5 SKIPPED** in `0.49s`
- **Zero Failures**: 0 errors, 0 regressions against existing test suites (`test_probes.py` passing).
- **Skipped Test Rationale**: The 5 skipped tests represent the 5 Shark Wire FastAPI endpoints scheduled for implementation in Milestone M2:
  1. `GET /api/packets/interfaces` (Milestone M2)
  2. `POST /api/packets/filter` (Milestone M2)
  3. `POST /api/packets/control` (Milestone M2)
  4. `GET /api/packets/stream` (Milestone M2)
  5. `GET /api/packets/export_pcap` (Milestone M2)

Note: `GET /api/whatcable/details` (Milestone M1) is already implemented and PASSED schema validation!
As each Milestone M2 endpoint is registered in `backend/server.py`, the corresponding test activates automatically and validates HTTP 200, headers, and schema compliance.

---

## 3. Coverage Summary by Tier

| Tier | Tests | Focus Area | Status |
|------|:-----:|------------|:------:|
| **Tier 1: Feature Coverage** | 45 | Direct Darwin IOKit probing, whatcable CLI execution, E-marker vendor IDs (Lintes 11037 / Tankya 11564), 240W EPR / 100W / 60W power profiles, DP Alt Mode HBR3 4-lane math (25.92 Gbps delivered vs 8.16 Gbps needed), bottleneck rules (CRITICAL, WARNING, INFO, OPTIMAL), interface discovery (`en0`, `bridge0`, `utun3`/`utun4`, `any`), ring buffer capacity (5,000), FIFO eviction, pause/resume/clear, libpcap 2.4 export, L2-L4 protocol dissection, WireGuard Types 1–4 on UDP 41641, Local AI RPC HTTP/1.1 & SSE delta stream chunks on Port 8082, Darwin utun DLT_NULL / raw IP byte alignment, filter AST parser & evaluator, FastAPI endpoints | 40 Passed, 5 Pending M2 Endpoints |
| **Tier 2: Boundary & Corner Cases** | 22 | Extreme bandwidth ratings (480M to 80G TB5), power boundaries (0W to 240W EPR), DisplayPort exact zero headroom & negative deficit, missing CLI binary fallback, empty CLI output fallback, corrupted JSON recovery, unknown vendor ID (0xFFFF), ring buffer zero packets export, exact 5,000 packet limit, 10,000 rapid packet flood stress, truncated frames (Ethernet <14B, IPv4 <20B, WireGuard <4B), filter code injection attack rejection (`__import__`, `eval`), unknown WireGuard message types | 22 Passed (100%) |
| **Tier 3: Cross-Feature Interactions** | 5 | Hardware probe to bottleneck evaluator data flow, DisplayPort refresh rate to bandwidth headroom correlation, packet ingestion to ring buffer and AST filter evaluation, binary PCAP export round-trip byte fidelity | 5 Passed (100%) |
| **Tier 4: Real-World Scenarios** | 6 | Mac Mini M4 Pro host hardware audit, simulated USB-C charge-only cable throttling diagnosis & remediation, complete WireGuard handshake and encrypted data exchange session, Local AI inference streaming session (`Qwen 3.8 Max 27B Abliterated` prompt $\to$ SSE chunks $\to$ `[DONE]`) | 6 Passed (100%) |
| **Total** | **78** | **Comprehensive 4-Tier Opaque-Box Coverage** | **Exit Code 0** |

---

## 4. Feature Checklist & Requirements Mapping

| Feature | Requirement Source | Tier 1 | Tier 2 | Tier 3 | Tier 4 | Implementation Target |
|---------|-------------------|:------:|:------:|:------:|:------:|:---------------------:|
| **F1.1 E-Marker Chip Parsing** | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ | `backend/probes/whatcable_inspector.py` (M1) |
| **F1.2 DisplayPort Alt Mode** | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ | `backend/probes/whatcable_inspector.py` (M1) |
| **F1.3 Cable Bottleneck Rules** | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ | `backend/probes/whatcable_inspector.py` (M1) |
| **F1.4 Dual-Engine Probing** | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ | `backend/probes/whatcable_inspector.py` (M1) |
| **F1.5 WhatCable API (`/details`)** | ORIGINAL_REQUEST §Acceptance | 1 | 1 | ✓ | ✓ | `backend/server.py` (M1) |
| **F2.1 Interface Discovery** | ORIGINAL_REQUEST §R2 | 5 | 2 | ✓ | ✓ | `backend/probes/shark_wire/interfaces.py` (M2) |
| **F2.2 Ring Buffer & PCAP Export** | ORIGINAL_REQUEST §R2 | 5 | 3 | ✓ | ✓ | `backend/probes/shark_wire/ring_buffer.py` (M2) |
| **F2.3 Display Filter AST Engine** | ORIGINAL_REQUEST §R2 | 3 | 2 | ✓ | ✓ | `backend/probes/shark_wire/filter.py` (M2) |
| **F2.4 Shark Wire Endpoints** | ORIGINAL_REQUEST §R2 | 5 | 1 | ✓ | ✓ | `backend/server.py` (M2) |
| **F3.1 WireGuard Dissection** | ORIGINAL_REQUEST §R3 | 5 | 2 | ✓ | ✓ | `backend/probes/shark_wire/dissector.py` (M2) |
| **F3.2 Local AI RPC Dissection** | ORIGINAL_REQUEST §R3 | 5 | 2 | ✓ | ✓ | `backend/probes/shark_wire/dissector.py` (M2) |
| **F3.3 Darwin utun Dissection** | ORIGINAL_REQUEST §R3 | 2 | 2 | ✓ | ✓ | `backend/probes/shark_wire/dissector.py` (M2) |
| **F3.4 Layer 2–4 Dissection** | ORIGINAL_REQUEST §R3 | 5 | 2 | ✓ | ✓ | `backend/probes/shark_wire/dissector.py` (M2) |

---

## 5. Authentic Test Fixtures Inventory

Located under `tests/fixtures/`:
1. `tests/fixtures/whatcable_authentic_dump.json`: Authentic 26 KB JSON dump captured directly from `/Users/aaron/.local/bin/whatcable --json --raw` on the Darwin host, featuring Lintes 240W E-marker, Tankya 240W E-marker, and MSI MP245 E14VL display.
2. `tests/fixtures/ioreg_ioport_dump.txt`: Authentic 43 KB raw text dump from Darwin `ioreg -r -c IOPort -l` verifying class `IOPortTransportComponentCCUSBPDSOPp` and vendor properties.
3. `tests/fixtures/mesh_traffic.pcap`: Valid libpcap 2.4 binary capture file (30 frames) containing authentic WireGuard Handshake Initiation (148B), Handshake Response (92B), Transport Data, and Local AI RPC HTTP/1.1 & SSE streaming frames on Port 8082. Verified using `tcpdump -r`.
4. `tests/fixtures/packet_samples.py`: Python module providing byte-exact binary frame generators for RFC-compliant Ethernet II, IPv4, IPv6, TCP, UDP, ICMP, WireGuard, Local AI RPC, and Darwin `utun` frames.
