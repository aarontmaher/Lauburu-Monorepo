# 🏛️ Nexus Sovereign Chrome Extension

Routes browser AI requests through the Lauburu Sovereign Mesh (`prima.cpp:8082`).

## Features
- **⚡ Sovereign AI** — Right-click any text → "Send to Sovereign AI" invokes `qwen_38_max` via prima.cpp
- **🔴 Devil's Advocate** — Challenge any idea with the abliterated adversarial model
- **📡 Mesh Control Panel** — Live status of all 7 mesh nodes, model health, WG peers
- **⌨️ Keyboard Shortcuts** — `Ctrl+Shift+L` for immediate AI invocation on selection
- **🌐 Context Badge** — Floating "⚡ Sovereign" badge appears on text selection
- **📊 LoRA Telemetry** — Live dataset growth counter, swarm status

## Installation (Developer Mode)
1. Open Chrome → `chrome://extensions`
2. Enable **Developer Mode** (top right)
3. Click **Load unpacked**
4. Select: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/nexus_sovereign_extension/`
5. Pin the Nexus Sovereign icon to toolbar

## Architecture
```
Browser Selection / Page Content
         ↓ (Ctrl+Shift+L or right-click)
  background.js (Service Worker)
         ↓
  http://127.0.0.1:8082/v1/chat/completions  (prima.cpp Sovereign)
  http://127.0.0.1:8083/v1/chat/completions  (Devil's Advocate)
  http://192.168.8.225:8086/v1/chat/completions  (L3 Fallback)
         ↓
  Side Panel → Streaming response display
```

## Endpoints Accessed
| Endpoint | Service |
|----------|---------|
| `http://127.0.0.1:8082` | prima.cpp (qwen_38_max, 5 models) |
| `http://127.0.0.1:8083` | Abliterated DA |
| `http://127.0.0.1:3035` | Screen Lens Sovereign |
| `http://192.168.8.225:8086` | L3 Swarm Worker (Qwen2.5-Coder) |
| `http://192.168.8.1/mesh_gui.html` | Mesh GUI HUD |
