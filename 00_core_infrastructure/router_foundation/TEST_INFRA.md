# Test Infrastructure & Test Philosophy: GL.iNet Router Bluetooth & Network Foundation
## Omni-Lens Sovereign Mesh

**Subsystem:** `00_core_infrastructure/router_foundation`  
**Governing Documents:** `PROJECT.md` & `ORIGINAL_REQUEST.md` (2026-09-16T23:53:45Z)  
**Author:** E2E Testing Specialist (`teamwork_preview_test_writer_e2e_suite`)  
**Standard:** Python Standard Library `unittest`, POSIX `/bin/sh`

---

## 1. 4-Tier Opaque-Box Test Philosophy

The GL.iNet Router Bluetooth & Network Foundation bridges the physical edge router (`192.168.8.1`, GL-BE14000) with the Mac Mini M4 Pro Host (`192.168.8.230`) across a dedicated 10GbE physical link (`0.20 ms` to `0.70 ms` RTT). To guarantee production stability, zero-mock fidelity, and autonomous self-healing, testing is structured into a rigorous **4-Tier Opaque-Box Verification Hierarchy**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       4-TIER TEST ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 1: UNIT & PROTOCOL ISOLATION                                           │
│ • Validates functional primitives, procd shell scripts, binary decoders,    │
│   DSP mathematical properties, and parser contracts in strict isolation.    │
│ • Deterministic, zero-network, sub-second execution.                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 2: BOUNDARY, RESILIENCY & PROTOCOL EDGE CASES                          │
│ • Stresses input boundaries, malformed packets, corrupted frames,           │
│   Kamath artifact clamping, TTL loop detection, ARP spoofing, memory leaks  │
│   (< 35 MB Host Sanctuary), and link flap hysteresis.                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 3: SUBSYSTEM INTEGRATION & STREAMING EMULATION                         │
│ • Spins up genuine AsyncIO TCP/UDP socket servers and clients on loopback,  │
│   pipes multi-mode streams (NDJSON, Binary TLV, HCI H4), and routes         │
│   multipart messages to ZeroMQ PUB sockets (:5550).                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 4: MASTER E2E & EMPIRICAL ACCEPTANCE VERIFICATION                      │
│ • Directly validates all 5 Acceptance Criteria (AC1-AC5) from ORIGINAL_     │
│   REQUEST.md, measuring sub-2s presence latency and live 10GbE sub-1ms RTT. │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Tier Details & Coverage Matrix

### Tier 1: Unit & Protocol Isolation Testing
- **Goal:** Verify that every component, script, and DSP algorithm implements the exact mathematical equations and protocol structures defined in the interface specifications.
- **Scope:**
  1. `test_router_bluetooth_hub.py`: Validates OpenWrt procd service structure (`START=95`, `USE_PROCD=1`, `start_service`, `stop_service`), `btmon` socket invocation parameters, and `socat TCP-LISTEN:9002,fork,reuseaddr UNIX-CONNECT:/tmp/btmon.sock` argument framing.
  2. `test_lens_10gbe_ingester.py`: Validates Bluetooth SIG GATT 0x2A37 decoding (flags byte, 8-bit vs 16-bit HR, RR-intervals in $1/1024\text{ s}$ resolution), Whoop 4.0 manufacturer payload extraction, and Samsung SmartTag 0x0075 beacon parsing.
  3. `test_presence_oracle.py`: Validates DHCP hotplug action handling (`add`, `del`, `old`), kernel rtnetlink neighbor line parsing (`ip monitor neigh dev br-lan`), and Canonical Mesh Registry mapping.
  4. `test_oob_wan_healer.py`: Validates the 6-state Finite State Machine (FSM) transitions, multi-target Layer 3 ICMP ping logic, and exact POSIX `ip route replace` command string generation.
  5. `test_edge_security_monitor.py`: Validates BPF filter parsing, rogue MAC lookup against Canonical Hardware Matrix, and TTL/ICMP Type 11 loop classification.

### Tier 2: Boundary, Resiliency & Protocol Edge Cases
- **Goal:** Exercise abnormal, adversarial, and edge condition behaviors without crashing or corrupting state.
- **Scope:**
  1. **Kamath 20% Clinical Filter**: Rejects physiological outliers ($<300\text{ ms}$ or $>2000\text{ ms}$), tests $\pm 20\%$ deviation clamping from 5-beat running median, and validates artifact counter increments.
  2. **HRV & DSP Math Invariants**: Verifies RMSSD calculation ($\sqrt{\frac{1}{N-1}\sum(\Delta RR)^2}$), DFA-$\alpha_1$ scaling slope, and PTT blood pressure clamping.
  3. **Log-Distance Path Loss**: Verifies RF distance calculations across extreme RSSI values ($-120\text{ dBm}$ to $0\text{ dBm}$) with calibrated TxPower.
  4. **Adversarial Network Packets**: Injects malformed JSON, truncated TLV buffers, out-of-order HCI fragments, duplicate IP IDs, and spoofed gateway ARPs.
  5. **Host Sanctuary Governance (Rule 3)**: Verifies memory footprint remains strictly $< 35\text{ MB}$ RSS.

### Tier 3: Subsystem Integration & Mock Streaming
- **Goal:** Verify end-to-end data pipeline across real local sockets, asynchronous event loops, and ZeroMQ brokers.
- **Scope:**
  1. **Real AsyncIO Sockets**: Binds actual TCP and UDP sockets on localhost with `TCP_NODELAY = 1` and 4MB buffers.
  2. **Multi-Mode Framer Slicing**: Streams NDJSON, Binary TLV, and HCI H4 simultaneously across the socket to test line buffering and frame extraction.
  3. **ZeroMQ Multi-Topic Dispatch**: Asserts messages are delivered to `tcp://127.0.0.1:5550` with multipart topics `MESH.STATE.*`, `MESH.TELEMETRY.*`, and `BLE.RAW.*`.
  4. **Sub-2s Propagation Timing**: Measures elapsed time from simulated DHCP/ARP event generation to receiver ingestion.

### Tier 4: Master E2E & Empirical Live Verification
- **Goal:** Verify all 5 Acceptance Criteria from `ORIGINAL_REQUEST.md`.
- **Scope:**
  1. **AC1: Router BLE Data Forwarding**: Verifies router socket forwarder transmits BLE packets to Mac Mini without requiring the Google Pixel 10 Pro XL or Android Termux daemon.
  2. **AC2: ZMQ Broker `MESH.STATE` Updates**: Verifies `MESH.STATE.ROUTER_FEED`, `MESH.STATE.BLE`, and `MESH.STATE.PRESENCE` topics receive live updates.
  3. **AC3: Sub-2s DHCP/ARP Propagation**: Empirical assertion that event-driven kernel triggers reflect state changes in $< 2.0\text{ seconds}$.
  4. **AC4: Autonomous Out-Of-Band NBN Failover**: Verifies the router's POSIX ash failover script executes `ip route replace default` without external orchestration or cloud dependency.
  5. **AC5: Sub-1ms 10GbE Bridge Latency**: Executes live ICMP probe across `192.168.8.1` verifying average RTT $\le 1.0\text{ ms}$ (nominal: $0.20\text{ ms} - 0.70\text{ ms}$).

---

## 3. Test Suite Inventory

| Test File | Governed Subsystem | Tier Coverage | Key Test Classes |
| :--- | :--- | :--- | :--- |
| `tests/test_router_bluetooth_hub.py` | R1: OpenWrt BLE Hub | Tier 1, Tier 2 | `TestRouterBluetoothHubProcd`, `TestSocatBridgingContracts`, `TestStreamFraming` |
| `tests/test_lens_10gbe_ingester.py` | R2: Mac Mini Ingester & DSP | Tier 1, Tier 2, Tier 3 | `TestMovesenseGATT2A37Parser`, `TestKamathAndHRVAlgorithms`, `TestWhoopNormalizer`, `TestSmartThingsParser`, `TestLens10GbEIngesterMultiMode`, `TestHostSanctuaryMemory` |
| `tests/test_presence_oracle.py` | R3: DHCP/ARP Presence Oracle | Tier 1, Tier 2, Tier 3 | `TestDHCPHotplugParsing`, `TestARPKernelNeighborParsing`, `TestCanonicalMeshRegistry`, `TestPresencePropagationLatency`, `TestPresenceOracleReceiver` |
| `tests/test_oob_wan_healer.py` | R4: Out-Of-Band Self-Healer | Tier 1, Tier 2 | `TestWANHealerFSMTransitions`, `TestMultiTargetICMPProbing`, `TestHysteresisAndFlapProtection`, `TestIPRouteCommandGeneration` |
| `tests/test_edge_security_monitor.py` | R5: Edge Security Red Team | Tier 1, Tier 2, Tier 3 | `TestRogueMACHunting`, `TestRoutingLoopDetection`, `TestARPSpoofingHunting`, `TestSYNScanAndFloodHunting`, `TestSecurityRadarJSONRendering` |
| `tests/test_e2e_router_foundation.py` | AC1–AC5 Master Acceptance Suite | Tier 4 (E2E) | `TestE2ERouterFoundation` (AC1, AC2, AC3, AC4, AC5) |

---

## 4. Test Execution & Verification

### Running the Full Test Suite:
```bash
# Automated bash test runner with colorized output and exit code status
bash 00_core_infrastructure/router_foundation/deploy/verify_router_foundation.sh

# Or invoke standard python unittest runner directly:
python3 -m unittest discover -s 00_core_infrastructure/router_foundation/tests -p "test_*.py" -v
```

### Expected Output Derivation:
- **Math & Physics**: Formulas derived directly from Bluetooth SIG GATT 0x2A37, Kamath (2004) ECG clinical filter, Task Force of the ESC and NASPE for HRV/RMSSD, and indoor log-distance path loss equation ($n=2.4$).
- **FSM Specifications**: Formally proven deterministic state machine transitions derived from `ORIGINAL_REQUEST.md` and Explorer 3 survey report.
- **Empirical Hardware Data**: Live network probes across `192.168.8.1` over the 10GbE physical link.
