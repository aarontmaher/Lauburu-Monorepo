---
title: "Canonical Screen Lens & AI Development Historian Architecture Specification"
tags: [screen_lens, ai_historian, local_ai, ocr, macos, android, vision, tri_vault]
updated: "2026-09-01"
---

# 🔍 Canonical Screen Lens & Autonomous AI Historian Architecture

**Subsystem:** `01_apps/screen_lens/`  
**Governing Node:** Mac Mini M4 Pro (L1 Host) & Pixel 10 Pro XL (L6 Mobile Edge)  
**Related Notes:** [[Index]], [[CANONICAL_PROJECT_AND_STORAGE_RULE]], [[LIVE_DEVELOPMENT_LOG_2026]], [[CROSS_DEVICE_LENS_TELEMETRY]]

---

## 🏛️ 1. Subsystem Architecture Overview

The **Screen Lens & Autonomous AI Historian Subsystem** delivers continuous, zero-mock multimodal perception across macOS desktop and Android mobile touch interfaces, translating raw visual activity and source code diffs into structured chronological memory and 24/7 fine-tuning instruction datasets.

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                    DUAL-DEVICE SCREEN LENS & AI HISTORIAN SUBSYSTEM                         │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. L1 Host: Mac Mini M4 Pro (Swift 6)                                                       │
│    • Frame Capture: ScreenCaptureKit Hardware Acquisition (~294ms)                          │
│    • Vision Engine: Apple Vision Framework OCR on Apple Neural Engine (ANE, ~187ms)         │
│    • Storage: SQLite3 WAL + FTS5 Full-Text Search (~/.lauburu/screen_lens.sqlite)        │
│    • Network Server: Embedded Network.framework NWListener HTTP/SSE Server on Port :3035   │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. L6 Edge: Pixel 10 Pro XL (Android 15 / Termux)                                           │
│    • Frame Capture: Native Android Screencap / UI Automator (~310ms)                         │
│    • Vision Engine: On-Device Tesseract 5.5.2 LSTM Neural Network (~210ms)                 │
│    • Storage: Local SQLite3 WAL + FTS5 Database (~/.lauburu/screen_lens.sqlite)             │
│    • Transport: Port :3035 bridged via Tailscale WireGuard (100.73.38.87) & ADB TCP (:3036)│
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. Autonomous AI Development Historian (lauburu-dev-historian)                              │
│    • Continuous Poller: Multi-path polling of Mac (:3035) and Pixel (:3035/:3036)           │
│    • Reasoning Dispatcher: Local Model Fleet (prima.cpp on :8082, llama.cpp on :8083)       │
│    • Tri-Vault Synchronization:                                                             │
│      - Obsidian Vault: obsidian_vault/00_CHRONOLOGY/LIVE_DEVELOPMENT_LOG_2026.md            │
│      - PySpark Big Data Lake: 04_data_and_memory/lora_datasets/project_dev_history.jsonl    │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🧠 2. Local AI Integration & Deep Linkages

The system is tightly coupled with local AI at five distinct execution layers:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                               LOCAL AI INTEGRATION MATRIX                                   │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. Primary Reasoning Master: prima.cpp (Port :8082)                                         │
│    • Executes high-throughput Pipelined-Ring Parallelism across 10Gbps TB4 DMA Bridge.      │
│    • Synthesizes cross-device OCR streams, window titles, and git diffs into milestones.    │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. Resilient Fallback Model: llama.cpp (Port :8083)                                         │
│    • Pinned Model: Qwen 3.8 Max 27B Abliterated (16.0 GB GGUF, 47.07 TPS).                  │
│    • Provides zero-latency automatic failover if prima.cpp is offline or sharding.          │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. Apple Silicon Neural Engine (ANE) Vision OCR                                             │
│    • Hardware-accelerated VNRecognizeTextRequest (.fast / .accurate modes).                 │
│    • Zero cloud egress; extracts spatial text coordinates and window metadata in ~187ms.    │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. Mobile Edge Neural OCR (Tesseract 5.5.2 LSTM)                                            │
│    • Runs natively inside Android Termux on Google Tensor G5 CPU/NPU.                       │
│    • Real-time text extraction from active mobile application frames.                       │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ 5. Continuous LoRA Distillation Dataset Generator                                          │
│    • Formats development milestones into DPO preference and instruction tuning pairs.       │
│    • Appends 24/7 training streams to project_development_history.jsonl for local models.   │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📂 3. Canonical Codebase Directory Layout

```
01_apps/screen_lens/
├── README.md                           # Master subsystem documentation
├── build.sh                            # Native Swift 6 compiler runner
├── bin/
│   └── lauburu-lens                    # Compiled standalone ARM64 binary
├── src/                                # Native Swift macOS Engine
│   ├── main.swift                      # Argument parser & command dispatcher
│   ├── CaptureEngine.swift             # ScreenCaptureKit frame capture & perceptual hashing
│   ├── VisionOCR.swift                 # Apple Vision VNRecognizeTextRequest
│   ├── DatabaseManager.swift           # SQLite3 WAL + FTS5 full-text search
│   ├── HttpServer.swift                # Network.framework NWListener embedded REST API (:3035)
│   ├── WindowInspector.swift           # NSWorkspace window hierarchy inspector
│   └── DaemonManager.swift             # Background daemon lifecycle & PID management
├── android/                            # Android Mobile Edge Engine
│   ├── lauburu_lens_android.py         # Termux capture, Tesseract OCR & REST API daemon (:3035)
│   └── termux_keepalive_service.sh     # Android foreground keepalive & wake-lock script
├── ai_dev_noter/                       # Autonomous Development Historian
│   ├── lauburu_dev_historian.py        # Development synthesis engine with LLM fallback routing
│   └── dev_noter_daemon.sh             # Background daemon runner symlinked to lauburu-dev-historian
└── tests/                              # Automated Verification Suite
    ├── test_screen_lens_integration.sh # macOS native integration tests
    ├── test_screen_lens_android.py     # Android SQLite schema & multi-path tests
    └── test_dev_historian.py           # Historian synthesis & milestone parser tests
```

---

## 🛑 4. Zero-Mock & Rule #0 Invariant Enforcement

1. **No Simulated Frames or Metrics:** All OCR text, timestamps, window titles, and device metrics originate from authentic hardware streams (`ScreenCaptureKit`, Android screencap, git worktree diffs).
2. **Dynamic Storage Headroom Guard (Rule 6.3):** The Historian continuously verifies that free NVMe headroom is $\ge 5.0\text{ GB}$ before writing milestones, automatically healing transient caches if pressure is detected.
3. **Tri-Vault Knowledge Persistence:** Every milestone is atomically committed to the Obsidian Knowledge Graph and PySpark training lake.
