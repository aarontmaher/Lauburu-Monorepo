# Project: WhatCable & Shark Wire Integration for Network Cable Analyzer (Port 4007)

## Architecture
- **Host**: Mac Mini M4 Pro (L1 Host), macOS Darwin
- **Backend**: FastAPI (Python 3.13) on Port 4007 (`01_apps/network_cable_analyzer/backend/server.py`)
- **Probes**:
  - `backend/probes/whatcable_inspector.py`: Native Darwin IOKit + `whatcable --json --raw` fallback E-marker and DisplayPort inspector. [DONE - M1]
  - `backend/probes/shark_wire/`: High-throughput, low-CPU packet capture engine (`engine.py`), zero-copy dissector (`dissector.py`), in-memory ring buffer (`ring_buffer.py`), live filter AST parser (`filter.py`), Darwin interface discovery (`interfaces.py`), and authentic test fixtures (`fixtures.py`). [DONE - M2]
- **Frontend**: Single-Page Application on Port 4007 (`frontend/index.html`, `frontend/app.js`, `frontend/styles.css`) [DONE - M3]
  - Top-Level Navigation Switcher (`[🌐 Mesh Topology]`, `[🔌 WhatCable]`, `[🦈 Shark Wire]`).
  - "🔌 WhatCable" Tab: Visual chassis schematic, port receptacles, E-marker badges, USB-PD power meters, DP Alt Mode bandwidth meters, bottleneck alerts.
  - "🦈 Shark Wire" Tab: 3-pane packet analyzer with virtualized packet grid, colorized display filter bar, collapsible protocol tree, and synchronized hex/ASCII dump inspector.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | F1.1 E-Marker Parsing | Vendor ID/name, chip ID, 40G/20G/10G/480M bandwidth, 240W EPR / 100W / 60W power profiles, PPS | M1 | DONE |
| 2 | F1.2 DP Alt Mode | Signaling rate (HBR3, DP 1.4/2.1), lanes, delivered vs needed Gbps, margin, sink display info | M1 | DONE |
| 3 | F1.3 Bottleneck Alerts | Cable down-negotiation, charge-only cable alert, headroom warning, severities CRITICAL/WARNING/INFO/OPTIMAL | M1 | DONE |
| 4 | F1.4 Dual-Engine Probing | Darwin IOKit (`ioreg -r -c IOPort -l`, `SPThunderboltDataType`) with fallback to `whatcable --json --raw` CLI | M1 | DONE |
| 5 | F1.5 WhatCable API | REST endpoint `GET /api/whatcable/details` responding HTTP 200 with structured hardware details | M1 | DONE |
| 6 | F2.1 Interface Discovery | Interface capture capabilities (`en0`, `en1`, `bridge0`, `utun3`/`utun4`, virtual `any` multiplexer) | M2 | DONE |
| 7 | F2.2 Low-CPU Capture Engine | Asynchronous binary PCAP stream, zero-copy memoryview parsing, dual-mode live/authentic replay | M2 | DONE |
| 8 | F2.3 Ring Buffer Engine | In-memory 5,000 packet ring buffer (`collections.deque`), FIFO eviction, pause/resume, clear, binary PCAP export | M2 | DONE |
| 9 | F2.4 Live Filter Engine | Tokenizer + AST parser + compiled evaluator supporting Wireshark filter syntax without eval() | M2 | DONE |
| 10 | F2.5 Packet Endpoints | `GET /api/packets/interfaces`, `GET /api/packets/stream` (SSE), `POST /api/packets/filter`, `POST /api/packets/control`, `GET /api/packets/export_pcap` | M2 | DONE |
| 11 | F3.1 WireGuard Dissection | Dissection of WireGuard UDP 41641 (Handshake Init, Handshake Resp, Cookie Reply, Transport Data) | M2 | DONE |
| 12 | F3.2 Local AI RPC Dissection | Dissection of Ports 8081-8084 (HTTP/1.1 requests, JSON payloads, SSE stream delta tokens, HTTP/2 frames) | M2 | DONE |
| 13 | F3.3 Control Plane Dissection | Dissection of SSH (ports 22/8022), Bluetooth SPP terminal streams, DNS (UDP/TCP 53) | M2 | DONE |
| 14 | F3.4 Layer 2-4 Dissection | Ethernet II, Darwin loopback/tun (DLT_NULL/raw IP), IPv4, IPv6, TCP (flags/seq/ack/win/options), UDP, ICMP | M2 | DONE |
| 15 | F3.5 Canonical Packet Schema | Unified JSON packet schema with layers, collapsible tree hierarchy, byte offset ranges, and hex dump | M2 | DONE |
| 16 | F4.1 View Switcher | Top-level view toggle (`[🌐 Mesh Topology]`, `[🔌 WhatCable]`, `[🦈 Shark Wire]`) in header and sidebar | M3 | DONE |
| 17 | F4.2 WhatCable UI | Visual chassis schematic, port receptacles with LED indicators, E-marker badges, PD meters, DP Alt meters, bottleneck cards | M3 | DONE |
| 18 | F4.3 Shark Wire Controls | Controls bar (interface selector, start/stop toggle, clear buffer, export PCAP, counters, ring buffer gauge) | M3 | DONE |
| 19 | F4.4 Shark Wire Filter Bar | Real-time syntax-validated filter bar with colorized feedback and quick filter chips | M3 | DONE |
| 20 | F4.5 Packet Grid View | Virtualized 60 FPS scrolling packet table with Wireshark color coding and auto-scroll | M3 | DONE |
| 21 | F4.6 Protocol Details Tree | Interactive collapsible protocol tree with disclosure chevrons and byte slice binding | M3 | DONE |
| 22 | F4.7 Hex & ASCII Dump View | Synchronized 16-byte hex and ASCII dump inspector with bidirectional hover/selection highlighting | M3 | DONE |
| 23 | F5.1 E2E WhatCable Test | Automated test suite `pytest tests/test_whatcable_integration.py` passing with Exit Code 0 | E2E_Track / M4 | DONE (33 passed) |
| 24 | F5.2 E2E Shark Wire Test | Automated test suite `pytest tests/test_shark_wire_packet_engine.py` passing with Exit Code 0 | E2E_Track / M4 | DONE (45 passed) |
| 25 | F5.3 Live REST & SSE Check | All REST and streaming endpoints verified HTTP 200 with live packet streaming | M4 | DONE |
| 26 | F5.4 UI & Visual Verification | Port 4007 loads cleanly with zero console errors and Screen Lens screenshot confirmed | M4 | DONE (3 screenshots) |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Track | Comprehensive requirement-driven opaque-box test suite (Tiers 1-4) creating `TEST_INFRA.md` & `TEST_READY.md` | Survey | DONE (`TEST_READY.md` published, 78 tests) |
| M1 | WhatCable Hardware Inspector Engine | `backend/probes/whatcable_inspector.py`, `backend/server.py` (`GET /api/whatcable/details`), unit tests | Survey | DONE (142 tests passing across integration, stress, and concurrency) |
| M2 | Shark Wire Packet Capture & Dissection Engine | `backend/probes/shark_wire/` (engine, dissector, ring_buffer, filter, interfaces), `backend/server.py` (`/api/packets/*`) | Survey | DONE (45/45 tests passing in `test_shark_wire_packet_engine.py`, 5 endpoints mounted) |
| M3 | Wireshark-Grade Frontend UI on Port 4007 | `frontend/index.html`, `frontend/app.js`, `frontend/styles.css` ("🔌 WhatCable" and "🦈 Shark Wire" views) | M1, M2 | DONE (View switcher, chassis schematic, 3-pane Shark Wire layout, 0 JS errors) |
| M4 | Final Integration, 100% E2E Pass & Coverage Hardening | Pass 100% of E2E tests (`test_whatcable_integration.py`, `test_shark_wire_packet_engine.py`), Tier 5 adversarial hardening, visual verification on Port 4007 | E2E, M1, M2, M3 | DONE (332 passed, 144 Tier 5 tests, 3 visual screenshots, Master Audit CLEAN) |

## Interface Contracts

### 1. WhatCable Inspector ↔ Server (`GET /api/whatcable/details`)
- Signature: `probe_whatcable_hardware_details(force: bool = False) -> Dict[str, Any]`
- Response schema:
  - `status`: `"success"`
  - `engine`: `"whatcable_native_hybrid"`
  - `engine_source`: `"whatcable_cli_and_darwin_iokit"`
  - `summary`: `{"total_ports": int, "active_ports": int, "cables_detected": int, "emarkers_detected": int, "bottlenecks_detected": int, "max_negotiated_speed_gbps": float, "max_power_rating_watts": int}`
  - `ports`: List of port objects with `port_id`, `receptacle`, `status`, `cable` (e_marker, vendor_name, vendor_id, speed_rating, max_bandwidth_gbps, max_watts, power_delivery), `data_link`, `bottleneck` (`is_bottleneck`, `severity`, `summary`, `detail`, `remedy`).
  - `display_ports`: List of display port objects with `displays` (`monitor_name`, `rate`, `lanes`, `delivered_gbps`, `needed_gbps`, `headroom_gbps`, `bottleneck`).

### 2. Shark Wire Engine ↔ Server (`/api/packets/*`)
- `GET /api/packets/interfaces`: Returns list of interfaces (`id`, `name`, `type`, `mac`, `ips`, `status`, `mesh_role`).
- `GET /api/packets/stream?interface=<id>&filter=<expr>`: Server-Sent Events stream:
  - Event `initial_batch`: Initial JSON array of recent matching packets from ring buffer.
  - Event `packet`: Real-time packet JSON object.
  - Event `stats`: Capture statistics (`captured_count`, `displayed_count`, `rate_pps`, `buffer_utilization_pct`, `drop_count`).
- `POST /api/packets/filter`: Body `{"filter": "<expression>"}`. Returns `{"valid": bool, "matched_count": int, "error": Optional[str]}`.
- `POST /api/packets/control`: Body `{"action": "start|stop|pause|resume|clear", "interface": Optional[str]}`. Returns `{"status": "ok", "state": str}`.
- `GET /api/packets/export_pcap`: Returns binary `application/vnd.tcpdump.pcap` with `Content-Disposition: attachment; filename="shark_wire_capture.pcap"`.

### 3. Backend ↔ Frontend Data Contract
- Packet JSON schema:
  - `index`: int
  - `timestamp`: float
  - `time_str`: str
  - `delta_time`: float
  - `interface`: str
  - `length`: int
  - `protocol`: str (`WireGuard`, `HTTP`, `HTTP/2`, `AI-RPC`, `AI-SSE`, `SSH`, `DNS`, `TCP`, `UDP`, `ICMP`)
  - `source`: str
  - `destination`: str
  - `source_name`: Optional[str]
  - `destination_name`: Optional[str]
  - `info`: str
  - `layers`: List[str]
  - `tree`: List[Dict[str, Any]] (layer name, expanded, fields with `label`, `value`, `start`, `end`)
  - `hex_dump`: str (formatted 16-byte offset lines)
  - `raw_bytes_base64`: Optional[str]

## Code Layout
- `01_apps/network_cable_analyzer/backend/probes/whatcable_inspector.py` (M1 - DONE)
- `01_apps/network_cable_analyzer/backend/probes/shark_wire/` (M2 - DONE)
  - `__init__.py`
  - `engine.py`
  - `dissector.py`
  - `ring_buffer.py`
  - `filter.py`
  - `interfaces.py`
  - `fixtures.py`
- `01_apps/network_cable_analyzer/backend/server.py` (M1, M2 route registrations - DONE)
- `01_apps/network_cable_analyzer/frontend/index.html` (M3 - DONE)
- `01_apps/network_cable_analyzer/frontend/app.js` (M3 - DONE)
- `01_apps/network_cable_analyzer/frontend/styles.css` (M3 - DONE)
- `01_apps/network_cable_analyzer/tests/test_whatcable_integration.py` (E2E / M4 - DONE: 33 passed)
- `01_apps/network_cable_analyzer/tests/test_shark_wire_packet_engine.py` (E2E / M4 - DONE: 45 passed)
- `01_apps/network_cable_analyzer/tests/test_tier5_adversarial_coverage.py` (M4 - DONE: 144 passed)
