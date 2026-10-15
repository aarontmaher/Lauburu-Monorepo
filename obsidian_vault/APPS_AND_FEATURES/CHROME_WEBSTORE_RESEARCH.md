# Chrome Web Store Deep Research — Lauburu Mesh / Screen Lens

**Generated:** 2026-09-20 | **Scope:** Lens, Mesh Network, AI Agents, Biometrics, Developer Tools

---

## 🏆 TIER 1 — Immediately Install (Direct Lens Integration)

### 1. Ui.Vision RPA — Visual Automation Engine
- **Store URL:** chromewebstore.google.com/detail/uivision-rpa/...
- **GitHub:** github.com/A9T9/RPA (AGPL open-source)
- **Relevance:** Computer-vision automation — image recognition, OCR, screen capture commands
- **Lens Integration:** Replace manual `uiautomator dump` with Ui.Vision macros callable via CDP
- **Key APIs:** `captureEntirePageScreenshot`, `captureDesktopScreenshot`, `xtype`, `xclick`
- **MV3:** Yes. Local-first — macros stored on device, zero cloud leakage
- **Action:** Wire to `lens_automation_hub.py → browser_evaluate()` to trigger Ui.Vision macros via JS

### 2. Chrome DevTools MCP (Already installed ✅)
- **WS Port:** `ws://localhost:9222`
- **Status:** ACTIVE — `Chrome/153.0.8010.52`
- **Lens Integration:** `CDPClient` in `lens_automation_hub.py` already wraps this
- **Expand:** Use `Target.setAutoAttach` with `flatten=true` to capture OOPIFs and service workers

### 3. WebSocket DevTools
- **Store:** chromewebstore.google.com — WebSocket DevTools by law-chain-hot
- **GitHub:** github.com/law-chain-hot/websocket-devtools
- **Relevance:** Real-time WS frame monitoring for mesh node communication debugging
- **Lens Integration:** Monitor `wg show wgserver` WebSocket feeds, ADB forwarded streams
- **Action:** Load via CDP `Target.createTarget` and attach debugger to inspect WS frames

### 4. Requestly — HTTP Interceptor + Mock
- **Relevance:** Intercept/modify network requests to local AI endpoints (port 8082/8083)
- **Lens Integration:** Mock responses from `prima.cpp` for training data generation
- **Key feature:** Session recording with console + network logs → export to LoRA dataset
- **MV3:** Yes. Open-source friendly

---

## 🔬 TIER 2 — High-Value for Network + AI Features

### 5. Copyfish OCR
- **Store:** chromewebstore.google.com/detail/copyfish-free-ocr-softwar/eenjdnjdenmhpnlgcpogkndnclghmglp
- **Relevance:** Extract text from any screen region → feed to Lens VLA pipeline
- **Lens Integration:** Trigger via CDP `Runtime.evaluate` + extension messaging

### 6. Wappalyzer
- **Relevance:** Tech stack detection on Shopify storefronts, competitor sites
- **Lens Integration:** Automate via CDP — navigate to target URL, evaluate Wappalyzer data

### 7. mcp-chrome (Open Source)
- **GitHub:** github.com/hangwin/mcp-chrome
- **Relevance:** Chrome extension as full MCP server — AI agents control browser locally
- **Lens Integration:** Alternative/complement to existing `chrome-devtools-mcp`
- **Key Advantage:** Bidirectional — extension can push events TO the AI agent

### 8. JSON Viewer Pro
- **Relevance:** Visualize prima.cpp / llama.cpp API responses at `localhost:8082`
- **Lens Integration:** Auto-format API responses when navigating to local endpoints

---

## 🌐 TIER 3 — Network Mesh & DevOps

### 9. WireGuardExt (Browser-scoped WireGuard)
- **Relevance:** Route ONLY Chrome traffic through Lauburu WireGuard tunnel
- **Companion:** `wireproxy` (open-source) as userspace WireGuard
- **Use Case:** Test geo-fenced Shopify storefronts through the mesh without OS-level VPN

### 10. Octotree — GitHub File Tree
- **Relevance:** Navigate the 435K+ LOC Lauburu-Monorepo faster on GitHub
- **Key feature:** Deep file tree sidebar for large repos

### 11. React Developer Tools
- **Relevance:** Debug Port 4000 Hub UI, Zone 2 Lauburu React components
- **Lens Integration:** CDP `DOM.getDocument` + React DevTools together for component inspection

---

## 🤖 TIER 4 — AI Agent + Computer Use

### 12. Autopilot (Solving.AI) — Agentic Browser Control
- **Relevance:** Natural language → browser actions, reads active tab layout
- **Lens Integration:** Alternative to manual CDP navigation for complex flows
- **Local Mode:** Configurable to use local LLM endpoints (port 8082)

### 13. Screenshot to AI
- **Relevance:** One-click screen region → AI analysis via Gemini/Claude/local
- **Lens Integration:** Trigger programmatically via CDP extension messaging API

---

## 🔧 CUSTOM CHROME EXTENSION TO BUILD (Lens Native)

### `lens-mesh-bridge` (MV3 Chrome Extension)

**Architecture:**
```
Manifest V3 Service Worker
  ├── WebSocket client → ws://localhost:8082 (prima.cpp)
  ├── chrome.tabCapture → MJPEG stream → Port 4003
  ├── chrome.debugger → CDP Fetch domain → intercept/modify AI API calls
  ├── Native Messaging Host → lens_automation_hub.py
  └── Offscreen Document → persistent WebSocket (Service Worker workaround)
```

**Key Capabilities:**
- `getDisplayMedia()` → stream Mac screen to Port 4003 as WebRTC offer
- `chrome.debugger.attach()` → intercept all XHR to `localhost:808*`
- `chrome.runtime.connectNative("com.lauburu.lens")` → trigger Python automations
- Side panel UI showing: WG peer status, RAM headroom, ADB device list

**Manifest permissions needed:**
```json
["debugger", "tabCapture", "nativeMessaging", "storage", "offscreen",
 "activeTab", "scripting", "webRequest", "declarativeNetRequest"]
```

**Files to create:**
- `06_scripts_and_tooling/chrome_extension/manifest.json`
- `06_scripts_and_tooling/chrome_extension/background.js` (Service Worker)
- `06_scripts_and_tooling/chrome_extension/offscreen.html` (persistent WS)
- `06_scripts_and_tooling/chrome_extension/side_panel.html`
- `06_scripts_and_tooling/chrome_extension/native_host/com.lauburu.lens.json`
- `06_scripts_and_tooling/chrome_extension/native_host/lens_native_host.py`

---

## 📊 Reverse Engineering Notes (Closed-Source Extensions)

Per `/closed-source-reverse-engineering` skill — sandbox analysis targets:

| Extension | Target | Method | Sandbox Path |
|---|---|---|---|
| Ui.Vision RPA | Command dispatcher JS | `jscodeshift` de-obfuscation | `sandbox_evolution/reverse_engineering/targets/uivision/` |
| Autopilot | Element detection model | `mitmproxy` HTTPS intercept | `sandbox_evolution/reverse_engineering/targets/autopilot/` |
| Screenshot to AI | Vision API routing | `chrome.debugger` Network capture | `sandbox_evolution/reverse_engineering/targets/screenshot_ai/` |

---

## ✅ Implementation Priority Queue

1. **Install Ui.Vision** → wire to `lens_automation_hub.py`
2. **Build `lens-mesh-bridge` extension** → Native messaging host + CDP intercept
3. **Install WebSocket DevTools** → debug WG + prima.cpp streams
4. **Install Requestly** → mock/log AI API calls
5. **Push `mcp-chrome` as alternative MCP** → bidirectional agent control

---

*Saved to Obsidian: `obsidian_vault/APPS_AND_FEATURES/CHROME_WEBSTORE_RESEARCH.md`*
*LoRA pairs: `lora_datasets/continuous_lora_dataset.jsonl`*
