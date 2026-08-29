---
title: "Split Architecture: Headless Linux Daemon vs. OS-Specific Native Frontends"
date: "2026-08-29"
author: "Antigravity Swarm Architect"
tags: [ai_debate, architecture, daemon, linux, macos, windows, tui, websocket]
---

# 🏛️ Split Architecture: Headless Linux Backend Daemon + OS-Specific Frontends

## 1. Executive Consensus

The Tri-Orchestrator AI Debate council reached unanimous consensus (**Score: 0.988**) that decoupling the **Headless Linux Compute Daemon** from **OS-Specific Native Frontends** represents the optimal architectural model for the Lauburu 7-Layer Mesh.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               DISTRIBUTED HEADLESS LINUX DAEMON + OS-SPECIFIC FRONTENDS                │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. HEADLESS LINUX BACKEND DAEMON (Linux Head Node / AMD Ryzen / Docker Hub / Server)   │
│    • 24/7 Persistent Ingestion: Movesense BLE gateway, Open Wearables Celery sync     │
│    • High-Throughput Storage: PySpark / Delta Lake indexing, PostgreSQL, Redis PubSub  │
│    • Local AI Cluster Hub: Petals DHT, llama.cpp RPC sharding (Ports 8081-8085)        │
│    • Network / Self-Healing: Nomad Courier 6-Tier Watchdog, Tailscale Subnet Router    │
│    • Telemetry State Server: gRPC / WebSocket / SSE State Broadcaster (:4000, :8088)  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. ZERO-OVERHEAD OS-SPECIFIC FRONTENDS (Thin Clients / Cockpits)                       │
│    ┌──────────────────────────┬──────────────────────────┬──────────────────────────┐  │
│    │ macOS (Apple Silicon)    │ Windows Workstation      │ Mobile (Android / iOS)   │  │
│    │ • Native Textual / Rust  │ • Windows Terminal /     │ • Flutter BLoC Client    │  │
│    │   Ratatui (0% VM draw)   │   Native Win32 Ratatui   │ • Kotlin / Swift UI      │  │
│    │ • Direct Metal Shaders   │ • Zero WSL2 RAM penalty  │ • Ultra-low battery draw │  │
│    │ • Sub-millisecond TTY    │ • Direct ConPTY socket   │ • Push notifications     │  │
│    └──────────────────────────┴──────────────────────────┴──────────────────────────┘  │
│ 3. TRANSPORT PROTOCOLS                                                                 │
│    • LAN / Thunderbolt 4: Direct gRPC / Protobuf streams (0.27ms latency)              │
│    • WireGuard Overlay: Encrypted Tailscale WebSocket state synchronization            │
│    • Fallback HTTP/SSE: Port 4000 JSON REST & Port 8088 Web-TUI browser bridge         │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---
