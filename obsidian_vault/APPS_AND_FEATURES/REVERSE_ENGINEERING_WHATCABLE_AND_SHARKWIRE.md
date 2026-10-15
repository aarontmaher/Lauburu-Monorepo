---
title: "Reverse Engineering WhatCable & Shark Wire — Local AI Training Curriculum & Cable Analyzer Architecture"
tags: [lauburu, reverse_engineering, whatcable, sharkwire, usb_c, wire_health, clean_room, lora]
created: 2026-09-11
---

# 🕵️‍♂️ Reverse Engineering WhatCable & Shark Wire: Local AI Training Curriculum & Wire Health Architecture

## 🏛️ 1. Strategic Rationale & Feature Value-Add

The **Lauburu Cable & Mesh Analyzer** on **Port 4007** (`http://localhost:4007`) currently monitors physical link negotiations, Bluetooth foundation anchors, and bandwidth bottlenecks across the 7-layer physical mesh. 

To maximize the diagnostic depth and eliminate external dependencies, **WhatCable** and **Shark Wire** have been officially integrated into the **Local AI Training Curriculum** (`05_agents_and_swarms/reverse_engineering_training_harness.py`) and **Track 2 Clean-Room Reverse Engineering Benchmark** (`05_agents_and_swarms/ai_training_games/tracks/track2_clean_room_reverse_engineering.py`).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│          REVERSE ENGINEERING WHATCABLE & SHARK WIRE FEATURE PIPELINE        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. WHATCABLE: USB-C SOP' VDM E-MARKER DECODER (TASK-RE-04 / RE_06)          │
│    • Current Baseline: Spawns external `/Users/aaron/.local/bin/whatcable`  │
│      binary (~180ms latency per probe, macOS only).                         │
│    • Reverse-Engineered Goal: Clean-room C11/Rust in-process decoder        │
│      interrogating Darwin `IOKit` (`AppleTypeCPhy`) & Linux `sysfs`         │
│      (`/sys/class/typec`) directly in < 2.0ms.                              │
│    • Value Added: Extends cable E-marker auditing to Linux Head Node (L3),  │
│      Linux Tablet (L4), Pixel 10 (L6), and Samsung S20+ (L7).               │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. SHARK WIRE: WIRE LINK FRAME & USB PACKET DISSECTOR (TASK-RE-05 / RE_07)   │
│    • Current Baseline: Reports static link negotiation speeds (e.g. 480M,   │
│      5G, 40G) from kernel interfaces.                                       │
│    • Reverse-Engineered Goal: Clean-room Rust/C11 wire frame dissector      │
│      using BPF and `usbmon` to inspect USB packets and Ethernet frames      │
│      within a 50µs budget.                                                  │
│    • Value Added: Real-time physical wire health — computes live CRC32      │
│      error rates, frame retries, and jitter to catch damaged pins, dirty    │
│      contacts, and intermittent cable signal degradation on the wire.       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🧬 2. Two-Tier Clean-Room Model Assignment & Protocol Matrix

Adhering strictly to **[[SKILL_CLOSED_SOURCE_REVERSE_ENGINEERING]]**:

| Target ID | Product Name | Tier A: Abliterated Spec Model | Tier B: Clean-Room Implementer | Red Team Challenger | Clean-Room Spec Target |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`TASK-RE-04`** (`RE_06`) | **WhatCable** (USB-PD SOP' VDM Decoder) | **Qwen 3.8 Max** (`:8082`) | **Qwen 2.5 Coder 7B** (`:8081`) | **Huihui 27B Abliterated** (`:8083`) | Zero-dependency C11/Rust SOP' VDM & E-Marker decoder (< 2ms) |
| **`TASK-RE-05`** (`RE_07`) | **Shark Wire / WireShark** (Wire Frame & CRC Sniffer) | **Huihui 27B Abliterated** (`:8083`) | **Qwen 2.5 Coder 7B** (`:8081`) | **Qwen 3.8 Max** (`:8082`) | Low-latency wire frame capture and CRC32/jitter error counter (50µs) |

---

## ⚡ 3. Subprotocol Deep Dive

### 3.1 WhatCable SOP' VDM Protocol Decoding
1. **SOP' Discover Identity Request:** Sent over the Type-C Configuration Channel (CC line) to interrogate the cable's internal E-Marker microchip:
   - Header: `0x4180` (Standard SOP' VDM Message)
   - Command: `0x8001` (Discover Identity ACK)
2. **Vendor Defined Object (VDO) Parsing:**
   - **ID Header VDO:** Extracts 16-bit Vendor ID (VID), Product ID (PID), and Active vs. Passive Cable flag.
   - **Passive/Active Cable VDO:** Extracts USB SuperSpeed signaling support:
     - `0x0`: USB 2.0 Only (480 Mbps)
     - `0x1`: USB 3.2 Gen 1 (5 Gbps)
     - `0x2`: USB 3.2 Gen 2 (10 Gbps)
     - `0x3`: USB4 Gen 3x2 / Thunderbolt 4 (40 Gbps)
   - **EPR Cable VDO (USB-PD 3.1):** Identifies 240W EPR (48V / 5A) vs standard 100W SPR (20V / 5A) or 60W (20V / 3A).
   - **Authenticity Audit:** Detects counterfeit E-markers where vendor strings claim 240W/40Gbps but VDO bits encode 60W USB 2.0.

### 3.2 Shark Wire / WireShark Wire Health & CRC Sniffing
1. **Physical Link Frame Ingestion:** Captures raw wire packets via BSD Packet Filter (`/dev/bpf*`) on macOS and `/dev/usbmon*` on Linux.
2. **Wire Health Metrics:**
   - **CRC16 / CRC32 Frame Check Sequence (FCS):** Bit errors on the wire indicate damaged conductors, bent pins, or RF interference.
   - **Frame Retransmission Rate:** Correlates packet drops with link latency spikes.
   - **Microsecond Wire Jitter:** Evaluates packet arrival variance to detect thermal throttling in cable controller ICs.

---

## 🛠️ 4. Live Endpoints & Dataset Ingestion

- **Curriculum Harness:** `05_agents_and_swarms/reverse_engineering_training_harness.py` (5 active challenges)
- **Track 2 Benchmark:** `05_agents_and_swarms/ai_training_games/tracks/track2_clean_room_reverse_engineering.py` (7 real products, 98.8 composite score)
- **Live Cable Analyzer Endpoint:** `GET http://localhost:4007/api/reverse_engineering/targets`
- **LoRA Dataset Lake:** `/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_reverse_engineering_training.jsonl`

---

## 🔗 5. Canonical Wikilinks
- [[Index]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[SKILL_CLOSED_SOURCE_REVERSE_ENGINEERING]]
- [[LAUBURU_CABLE_MESH_ANALYZER_ARCHITECTURE]]
- [[APPS_AND_FEATURES/DEVICE_AUTO_IDENTIFICATION_AND_BOTTLENECK_DETECTION]]
- [[BLUETOOTH_RECONNECT_CABLE_ANALYZER]]
