# App Name: Cable & Mesh Analyzer Lauburu (Stitch 2.0 Pro Edition)

## 1. Global Theming & Design Tokens (Google Stitch 2.0 Standard)
- **Primary Palette:**
  - Dark Void Background: `#07090e` / `#0c1017`
  - Cyber Emerald Accent: `#10b981` (Online, Optimal, Line-Rate)
  - Neon Cyan Link Glow: `#06b6d4` (Thunderbolt 40Gbps, Active Bridge)
  - Amber Warning: `#f59e0b` (Throttled, USB 2.0 fallback, Bottleneck)
  - Rose Critical: `#f43f5e` (Link Down, Packet Drop, VRAM pressure)
  - Glass Surface: `rgba(18, 24, 38, 0.72)` with `backdrop-filter: blur(16px)`
  - Surface Border: `rgba(255, 255, 255, 0.08)` / active `rgba(16, 185, 129, 0.3)`
- **Typography:**
  - Primary UI: `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
  - Monospace Telemetry: `'JetBrains Mono', 'Fira Code', ui-monospace, monospace`
- **Component Standard:**
  - Multi-Framework: Standalone Interactive HTML5/Tailwind + React 18 TSX + Flutter Widget + Shopify OS 2.0 Liquid Section
  - Responsive Grid: Mobile-first 1-col -> Tablet 2-col -> Desktop 3/4-col Infinite Canvas

## 2. Commercial Conversion Heuristics (Stitch 2.0 E-Commerce Mandate)
- **Above-The-Fold Value Proposition:** Instant diagnostic clarity + estimated hourly network downtime cost averted ($1,240/hr enterprise benchmark).
- **Interactive ROI Calculator:** Sliders for node count (1-100) and link speed to calculate throughput optimization yield.
- **Tiered Commercial Packaging:**
  - **Community Free ($0 AUD):** Single-host Darwin Mach kernel memory, whatcable E-marker inspection, local ping.
  - **Pro Engineer ($29 AUD / mo):** 7-Layer Mesh Topology, 5,000-packet Shark Wire ring buffer, WireGuard/RPC dissecting, BT serial lifeline.
  - **Enterprise NOC ($199 AUD / mo):** 24/7 Omniscient Mesh Sentinel, Automated swconfig self-healing, multi-node RPC tensor sharding, SLA watchdog.
  - **Physical Hardware Diagnostic Kit ($349 AUD):** Certified TB4 40Gbps E-marked cable, 2.5GbE USB-C dongle, Nordic BLE UART dongle, ruggedized travel case.
- **High-Contrast Primary CTAs:** "Deploy Enterprise Sentinel" / "Upgrade to Pro Suite" with 1-click checkout modal.
- **Zero-Mock Empirical Grounding:** All metrics bind to authentic host endpoints (`/api/topology`, `/api/whatcable/details`, `/api/packets/interfaces`).

## 3. Multi-Screen Flow & Infinite Canvas Architecture

### Screen 1: Executive Telemetry & Cable Inspector (`/` & `/stitch`)
- **Route:** `http://127.0.0.1:4007/stitch`
- **Purpose:** Consolidated, high-fidelity diagnostic dashboard merging WhatCable, Shark Wire, and 7-Node Mesh Topology with commercial conversion cues.
- **State / Props:**
  - `meshSummary`: Online node count (7/12), total pooled RAM (148.1 GB), active cables (9), TB4 DMA latency (0.27ms).
  - `cableMatrix`: Verified physical cable inventory (TB4 40G, Cat6 10G, Cat5e 2.5G, USB-C ADB).
  - `packetThroughput`: Live `netstat` byte counters per interface (`en0`, `en1`, `bridge0`).
  - `commercialState`: Active plan tier, upgrade trigger, ROI calculator inputs.
- **Layout:**
  - **Header:** Brand icon, title, live SSE heartbeat pulse, active node badges, commercial plan badge ("Pro Engineer Active"), "Upgrade to NOC" CTA.
  - **Hero Metric Banner:** 4 high-density stat cards (Pooled AI RAM, TB4 DMA Latency, Active Cable Throughput, Network Uptime SLA).
  - **Main Canvas (Split Grid):**
    - Left Column: Interactive Cable Port Schematic (E-marker chips, USB-PD contracts, DP Alt Mode, Bottleneck alerts).
    - Right Column: Live Shark Wire Packet Stream preview + Activity Monitor Darwin Mach Memory Pressure gauge.
  - **Commercial Conversion Card:** Enterprise Mesh Sentinel Callout, Interactive Downtime Savings Estimator, Tier Comparison Drawer.
  - **Footer:** Zero-Mock Truth Audit watermark, live Bluetooth terminal status, Tri-Vault sync indicators.

### Screen 2: WhatCable E-Marker Studio (`#whatcable`)
- **Route:** `/stitch#whatcable`
- **Purpose:** Deep-dive physical cable and transceiver validator with commercial certified cable store.

### Screen 3: Shark Wire Packet Dissector (`#sharkwire`)
- **Route:** `/stitch#sharkwire`
- **Purpose:** Virtualized live packet capture table with protocol trees, hex view, and BPF filters.
