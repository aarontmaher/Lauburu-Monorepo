# Original User Request

## 2026-09-17T05:36:55Z

Build a production-grade native WhatCable E-marker inspector and a full-featured web-based Wireshark packet analyzer ("Shark Wire") directly into the Port 4007 Cable & Mesh Analyzer dashboard.

Working directory: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/network_cable_analyzer`
Integrity mode: development

## Requirements

### R1. Native WhatCable Hardware & E-Marker Inspector
Embed comprehensive USB-C and Thunderbolt cable intelligence into the app backend:
- Parse and display live E-marker chip parameters (vendor, chip ID, max bandwidth 40G/20G/10G/480M, USB-PD power delivery wattage, voltage, and PPS profiles).
- Display DisplayPort Alt Mode capabilities (HBR3, DP 1.4/2.1, lanes, current mode vs. max capability, delivered vs. needed Gbps).
- Surface cable bottleneck alerts directly in the UI when a cable or port is negotiating below its rated speed.
- Support both direct Darwin IOKit/system probing and fallback to the local `whatcable --json` CLI engine.

### R2. Live Packet Capture & Streaming Engine ("Shark Wire")
Implement a high-throughput, low-latency packet capture engine on the primary host interfaces (`en0` 10GbE, `en1` Wi-Fi 7, `bridge0` 40Gbps TB4 DMA, `utun3` WireGuard):
- Stream live packets over Server-Sent Events (SSE) or WebSockets to the web frontend with negligible CPU overhead.
- Include a configurable ring buffer (e.g. 5,000 packets) with ring-buffer management and pause/resume capture controls.
- Implement live filtering expressions by protocol, IP address, port, and packet length.

### R3. Mesh Protocol Dissection & Inspection
Decode and display packet headers with specialized decoders for Lauburu mesh traffic:
- **WireGuard Overlay:** Decodes WireGuard handshake initiation, response, and encrypted data frames on UDP 41641.
- **Local AI RPC & Inference:** Decodes HTTP/1.1 and HTTP/2 requests and SSE streams across Ports 8081–8084 (Prima PRP ring, Qwen 3.8 Max, Devil's Advocate).
- **Control Plane & Diagnostics:** Decodes SSH (ports 22/8022), Bluetooth SPP terminal streams, and DNS queries.
- **Layer 3 / 4 Standard Protocols:** Full dissection of Ethernet, IPv4/IPv6, TCP (flags, sequence, ACK, window), UDP, ICMP.

### R4. Wireshark-Grade Frontend UI (Port 4007)
Add two dedicated dashboard views or tabs to the frontend:
1. **"🔌 WhatCable" Tab:**
   - Visual cable port schematic showing port receptacles, attached cables, E-marker chip vendor badges, power delivery ratings, and DisplayPort Alt Mode bandwidth meters.
2. **"🦈 Shark Wire" Tab:**
   - **Packet Grid:** Live-scrolling virtualized packet table with columns: `No.`, `Time`, `Source`, `Destination`, `Protocol`, `Length`, `Info`.
   - **Live Display Filter Bar:** Colorized syntax filter bar (e.g., `ip.addr == 100.119.199.76 && tcp.port == 8082`).
   - **Packet Details Tree:** Interactive collapsible protocol tree (Frame, Ethernet, IP, TCP/UDP, Application Layer).
   - **Hex / ASCII Dump View:** Synchronized byte inspector with raw hex and printable ASCII.
   - **Controls Bar:** Start/Stop capture, interface selector (`en0`, `en1`, `bridge0`, `utun3`, `any`), clear buffer, export PCAP.

## Acceptance Criteria

### Automated Verification
- [ ] Automated test suite (`pytest tests/test_whatcable_integration.py`) verifies WhatCable E-marker parsing and endpoint schemas with Exit Code 0.
- [ ] Automated test suite (`pytest tests/test_shark_wire_packet_engine.py`) verifies packet capture, dissection of WireGuard/TCP/UDP/HTTP frames, and filter evaluation with Exit Code 0.
- [ ] REST & streaming endpoints respond with HTTP 200:
  - `GET /api/whatcable/details`
  - `GET /api/packets/interfaces`
  - `GET /api/packets/stream` (SSE/WebSocket streaming valid packet JSON objects)
  - `POST /api/packets/filter`

### Live Dashboard & Visual Verification
- [ ] Port 4007 frontend loads WhatCable and Shark Wire tabs cleanly with zero console errors.
- [ ] Shark Wire displays live scrolling packet traffic on active interfaces with interactive protocol tree inspection and hex dump.
- [ ] Screen Lens visual screenshot (`take_screenshot`) confirms pixel-perfect rendering of the new tabs on Port 4007.
