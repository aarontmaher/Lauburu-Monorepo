# Lauburu Mesh: Chrome Web Store & DevTools AI Architecture Specification
**Document Version:** 1.0.0  
**Target Path:** `07_docs_and_architecture/CHROME_WEB_STORE_AND_DEVTOOLS_SPEC.md`  
**Status:** Approved Technical Architecture  

---

## 1. Executive Summary

This specification defines the architecture, protocol design, and operational requirements for packaging the **Lauburu Mesh Monitoring Engine** and **Screen Lens HUD** into a high-performance Chrome Web App and Manifest V3 (MV3) Chrome Extension. It covers:
1. **Chrome Web Store (CWS) Developer Dashboard Requirements & MV3 Runtime Architecture**: Service workers, native messaging, offscreen documents, WebRTC DataChannels, and persistent WebSockets.
2. **Chrome DevTools Performance & Console AI Assistance**: Integration with the built-in Gemini AI model in DevTools, structured trace emission, custom DevTools panels, and CDP telemetry feeds.
3. **Packaging & Deployment Recommendations**: Native Go daemon integration, zero-overhead HUD rendering via Shadow DOM/WebGPU, and enterprise distribution strategies.

---

## 2. Chrome Web Store Developer Dashboard & Manifest V3 Architecture

### 2.1 CWS Developer Dashboard Requirements
- **Account Registration & Identity**:
  - One-time registration fee ($5 USD) via Google Account.
  - Mandatory 2-Factor Authentication (2FA) on the developer Google account.
  - Organization verification required for enterprise publisher entities.
- **Single-Purpose Policy**:
  - The extension must have a single, clearly defined user-facing utility (e.g., "Lauburu Mesh Network Telemetry & Screen Lens HUD").
- **Permission Justification & Least Privilege**:
  - All declared permissions in `manifest.json` must be justified during review.
  - Permissions required:
    - `"storage"`: Caching mesh topology, auth tokens, and HUD layout state.
    - `"offscreen"`: Maintaining WebRTC DataChannel / WebSocket connections outside the ephemeral service worker.
    - `"nativeMessaging"`: High-bandwidth communication with the local Lauburu Go node daemon.
    - `"activeTab"` / `"scripting"`: Injecting Screen Lens HUD on user request without broad host permissions.
- **Privacy Policy & User Data Disclosures**:
  - Required privacy policy hosting explaining data collection (mesh telemetry, node IDs, performance metrics).
  - Explicit declaration whether any PII or screen contents are collected (Screen Lens runs client-side with zero telemetry exfiltration).

### 2.2 Manifest V3 Architecture & Component Topology

```
+---------------------------------------------------------------------------------+
|                               Google Chrome Browser                             |
|                                                                                 |
|  +--------------------+     chrome.runtime      +----------------------------+  |
|  |   Background       |<----------------------->|   Offscreen Document       |  |
|  |   Service Worker   |   (Message Channel)     |   (Persistent Lifecycle)   |  |
|  |  (Ephemeral, MV3)  |                         |  - WebRTC PeerConnections  |  |
|  +---------+----------+                         |  - Persistent WebSockets   |  |
|            |                                    |  - Audio/Video/WebCodecs   |  |
|            | nativeMessaging                    +-------------+--------------+  |
|            |                                                  |                 |
|            v                                                  | WebRTC Data     |
|  +--------------------+                                       v                 |
|  | Local Lauburu Node |                         +----------------------------+  |
|  | (Go/Rust Binary)   |                         |  Lauburu P2P Mesh Network  |  |
|  +--------------------+                         +----------------------------+  |
|                                                                                 |
|  +---------------------------------------------------------------------------+  |
|  | Active Tab / Web Page                                                     |  |
|  |  +---------------------------------------------------------------------+  |  |
|  |  | Content Script (Isolated World)                                     |  |  |
|  |  |  +---------------------------------------------------------------+  |  |  |
|  |  |  | Screen Lens HUD (Closed Shadow DOM Root)                      |  |  |  |
|  |  |  | - Canvas / WebGL2 / WebGPU Hardware Overlay                  |  |  |  |
|  |  |  | - Realtime Mesh Topology & Latency Visualizer                |  |  |  |
|  |  |  +---------------------------------------------------------------+  |  |  |
|  |  +---------------------------------------------------------------------+  |  |
|  +---------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------+
```

### 2.3 Manifest V3 Specification (`manifest.json`)

```json
{
  "manifest_version": 3,
  "name": "Lauburu Mesh Lens",
  "version": "1.0.0",
  "description": "High-performance mesh telemetry, Screen Lens HUD, and DevTools AI integration for the Lauburu distributed network.",
  "permissions": [
    "storage",
    "offscreen",
    "nativeMessaging",
    "scripting",
    "activeTab"
  ],
  "background": {
    "service_worker": "dist/background.bundle.js",
    "type": "module"
  },
  "action": {
    "default_title": "Toggle Lauburu Screen Lens HUD",
    "default_icon": {
      "16": "icons/icon-16.png",
      "48": "icons/icon-48.png",
      "128": "icons/icon-128.png"
    }
  },
  "devtools_page": "devtools/devtools.html",
  "web_accessible_resources": [
    {
      "resources": ["hud/lens-frame.html", "hud/assets/*"],
      "matches": ["<all_urls>"]
    }
  ],
  "minimum_chrome_version": "116"
}
```

### 2.4 Service Worker vs. Offscreen Document Strategy
- **Service Worker Lifecycle Constraints**:
  - Chrome MV3 terminates background service workers after **30 seconds of inactivity** or after **5 minutes of continuous task execution**.
  - Service workers **cannot** maintain open WebRTC `RTCPeerConnection` or continuous WebSocket connections across sleeps.
  - State must be persisted to `chrome.storage.session` (in-memory, survives worker restarts) or `chrome.storage.local`.
- **Offscreen Documents (`chrome.offscreen`)**:
  - Created specifically to host DOM-dependent APIs and continuous network sockets:
    ```typescript
    await chrome.offscreen.createDocument({
      url: 'offscreen.html',
      reasons: [chrome.offscreen.Reason.WEBRTC, chrome.offscreen.Reason.WEB_SOCKETS],
      justification: 'Maintaining persistent WebRTC DataChannel mesh connections and streaming telemetry.'
    });
    ```
  - The Offscreen Document maintains:
    1. Active `RTCPeerConnection` instances participating in the Lauburu browser mesh.
    2. Zero-latency binary WebSockets to edge telemetry gateways.
    3. Bidirectional communication with the background worker via `chrome.runtime.sendMessage` and `chrome.runtime.connect`.

### 2.5 Native Messaging Bridge (Chrome <-> Local Lauburu Daemon)
- **Protocol Definition**:
  - Standard Chrome Native Messaging over OS standard input/output (`stdin`/`stdout`).
  - Messages are prefixed with a 32-bit integer indicating payload length in native byte order, followed by UTF-8 encoded JSON.
  - Maximum message size: 1 MB.
- **Go Host Implementation**:
  ```go
  // native_messaging_host.go
  package main

  import (
      "encoding/binary"
      "encoding/json"
      "io"
      "os"
  )

  type TelemetryMessage struct {
      Type    string                 `json:"type"`
      Payload map[string]interface{} `json:"payload"`
  }

  func ReadMessage() (*TelemetryMessage, error) {
      var length uint32
      if err := binary.Read(os.Stdin, binary.LittleEndian, &length); err != nil {
          return nil, err
      }
      buf := make([]byte, length)
      if _, err := io.ReadFull(os.Stdin, buf); err != nil {
          return nil, err
      }
      var msg TelemetryMessage
      err := json.Unmarshal(buf, &msg)
      return &msg, err
  }

  func WriteMessage(msg *TelemetryMessage) error {
      data, err := json.Marshal(msg)
      if err != nil {
          return err
      }
      length := uint32(len(data))
      if err := binary.Write(os.Stdout, binary.LittleEndian, length); err != nil {
          return err
      }
      _, err = os.Stdout.Write(data)
      return err
  }
  ```
- **Native Host Manifest (`com.lauburu.mesh.json`)**:
  - Path on macOS: `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.lauburu.mesh.json`
  - Manifest specifies `path` to the compiled binary and `allowed_origins` matching the extension ID (`chrome-extension://<EXTENSION_ID>/`).

---

## 3. Chrome DevTools Performance & Console AI Assistance Integration

Chrome DevTools integrates **Gemini in DevTools** (Console Insights and Performance Insights). The Lauburu architecture establishes clean hooks so developers and automated agents can leverage built-in AI assistance.

### 3.1 Feeding Structured Metrics into Chrome DevTools Insights
1. **User Timing API Level 3 (`performance.mark` & `performance.measure`)**:
   - DevTools Performance Panel and AI analysis recognize User Timing marks with structured detail payloads:
   ```typescript
   // Mark mesh packet reception
   performance.mark("lauburu:packet:received", {
     detail: {
       nodeId: "node-us-west-44",
       hopCount: 3,
       payloadBytes: 1024,
       rttMs: 14.2
     }
   });

   // Measure consensus validation duration
   performance.measure("lauburu:consensus:validation", {
     start: "lauburu:packet:received",
     detail: {
       algorithm: "raft-quic",
       quoromAchieved: true,
       peersResponded: 5
     }
   });
   ```
2. **Console Error Formatting for Gemini Console Insights**:
   - DevTools Gemini AI reads console errors, call stacks, and contextual network traces.
   - Lauburu errors are emitted with structured contextual metadata and standardized error schemas:
   ```typescript
   console.error(new Error("LauburuMeshConsensusTimeout: Peer quorum dropped below threshold (received 2/5 acks within 250ms). Check node route 'node-eu-central-12' latency."), {
     subsystem: "consensus_engine",
     activePeers: ["node-us-east-1", "node-us-west-2"],
     failedPeers: ["node-eu-central-12", "node-ap-southeast-1"],
     remediation: "Verify TURN relay connectivity or ping heartbeat on UDP port 41641."
   });
   ```
   - When a developer clicks the **"Ask Gemini" / "Understand this error"** badge next to the error, the structured context enables Gemini to diagnose network partitioning and STUN/TURN traversal issues directly.

### 3.2 Custom DevTools Panel (`Lauburu Mesh Inspector`)
- Registered via `devtools_page` in `manifest.json`:
  ```javascript
  // devtools/devtools.js
  chrome.devtools.panels.create(
    "Lauburu Mesh",
    "icons/icon-16.png",
    "devtools/panel.html",
    (panel) => {
      // Panel created - connect to background port
      const port = chrome.runtime.connect({ name: "lauburu-devtools" });
      port.onMessage.addListener((telemetry) => {
        // Update live topology graph and performance watermarks
      });
    }
  );
  ```
- **Chrome DevTools Protocol (CDP) Telemetry Feeding**:
  - Extensions with debugging permissions or external automation agents can use CDP domains:
    - `Tracing.start` / `Tracing.end`: Capture unified CPU, GPU, and User Timing traces.
    - `Performance.getMetrics`: Read layout duration, JS heap usage, and event latency.
    - `Audits.getEncodedResponse`: Check compression and mesh payload efficiency.

---

## 4. Packaging Recommendations: Lauburu Monitoring & Screen Lens HUD

### 4.1 Screen Lens HUD: Rendering & Isolation Architecture
To ensure the HUD never impacts host web page styles or performance:
1. **Closed Shadow DOM**:
   - The HUD is injected inside a host container with a closed shadow root (`attachShadow({ mode: 'closed' })`).
   - Global page CSS and frameworks (Tailwind, Bootstrap) cannot bleed into or mutate the HUD.
2. **Hardware-Accelerated WebGL2 / WebGPU Canvas**:
   - Node topology graphs, packet particle animations, and latency heatmaps are rendered onto an `OffscreenCanvas` via WebGL2/WebGPU.
   - Zero DOM reflows or repaints on high-frequency telemetry updates (60-120 FPS).
3. **Draggable & Dockable Viewport Layout**:
   - Positioned as a floating heads-up display (`pointer-events: none` on transparent canvas regions, `pointer-events: auto` on interactive control widgets).

### 4.2 High-Performance Hybrid Model: Extension + Native Daemon

| Feature | Chrome Extension (MV3) | Native Lauburu Daemon (Go) | Combined Hybrid Architecture |
| :--- | :--- | :--- | :--- |
| **P2P Transport** | WebRTC DataChannels | Raw TCP, UDP, QUIC, WireGuard | Extension handles browser peers; Daemon handles high-speed datacenter mesh |
| **Screen Lens HUD** | Injected in-page overlay | N/A (Headless) | Extension renders UI; Daemon streams metrics over Native Messaging |
| **DevTools AI** | Direct User Timing & Console hooks | Emits to local debug socket | Extension relays daemon telemetry into DevTools performance marks |
| **System Footprint** | Micro-client (DOM & Canvas) | Heavy crypto & consensus routing | Optimal memory separation & CPU affinity |

### 4.3 Deployment & Distribution Roadmap
1. **Developer / Internal Testing**:
   - Packaged as an unpacked extension loaded via `chrome://extensions` with Developer Mode.
   - Automated end-to-end integration tests using Chrome DevTools Protocol (`mcp_chrome_devtools` / Puppeteer).
2. **Enterprise Unlisted Deployment**:
   - Published on Chrome Web Store as **Unlisted** or deployed via Google Workspace Enterprise Policy (`ExtensionInstallForcelist`).
   - Native Messaging host registered via standard installer script (`install_host.sh` / `install_host.ps1`).
3. **Public Chrome Web Store Release**:
   - Automated zip generation and release artifact creation in GitHub Actions / CI pipeline.
   - Upload via Chrome Web Store API (`v1.1`) with automated OAuth2 refresh tokens.

---

## 5. Implementation Action Plan

1. **Phase 1: Manifest V3 Skeleton & Offscreen Document**:
   - Scaffold `apps/chrome-extension` in `Lauburu-Monorepo`.
   - Setup Webpack/Vite bundler producing MV3 service worker and offscreen WebRTC coordinator.
2. **Phase 2: Native Messaging Bridge**:
   - Implement `cmd/lauburu-native-bridge` in Go using the 32-bit length-prefixed JSON protocol.
   - Configure native host manifest installer for macOS and Linux.
3. **Phase 3: Screen Lens HUD Injection**:
   - Build closed Shadow DOM HUD with WebGL2 node topology graph.
4. **Phase 4: DevTools Panel & AI Instrumentation**:
   - Implement `devtools_page` and integrate structured User Timing marks (`lauburu:*`) for Gemini in DevTools.
