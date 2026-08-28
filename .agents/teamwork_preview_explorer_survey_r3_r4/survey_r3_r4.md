# Comprehensive Survey & Architectural Blueprint: Requirement 3 (R3) & Requirement 4 (R4)

**Surveyor:** `teamwork_preview_explorer`  
**Date:** 2026-08-26  
**Status:** Ground-Truth Certified (Rule #0 Zero-Mock Standard Enforced)  
**Target Super-App Integration:** Unified Pitch-Black Sovereign Monochromatic Shell  

---

## Executive Summary

This investigation surveys all existing assets, engines, mathematical models, UI components, and transport pipelines for:
1. **Requirement 3 (R3): 3D Spatial Grappling Kinematics & WebGPU Tension Net**
2. **Requirement 4 (R4): Hands-Free Voice IDE & Side-by-Side CoT Reasoning AST Diff Viewer**

All source code across `01_apps/spatial_grappling_3d`, `00_core_infrastructure/self_healing_hub`, `10_spatial_grappling_kinematics`, and `04_data_and_memory` was analyzed down to exact file paths, class definitions, WebGPU shaders, and event streams.

---

## Part 1: Requirement 3 (R3) — 3D Spatial Grappling Kinematics & WebGPU Tension Net

### 1.1 Architectural Topology & Component Inventory

| Subsystem Component | File Path | Key Technologies | Function / Capabilities |
|---|---|---|---|
| **Tatami Arena Host** | `00_core_infrastructure/self_healing_hub/frontend/src/UnifiedGenieTatamiArenaView.jsx` | React, WebGPU, Recharts, SVG | Multi-tab command center hosting 3D Genie 2 world model, 1v1 autonomous duels, 7-layer edge fleet manager, and WebGPU WGSL compute benchmark. |
| **WebGPU Compute Engine** | `00_core_infrastructure/self_healing_hub/frontend/src/WebGPUComputeEngine.js` | WebGPU API, WGSL, Float32Array | In-browser WGSL compute shader execution for parallel General Matrix Multiplication (GEMM: $C = A \times B$), 120 FPS particle kinematics, and zero-copy GPU storage buffer mapping. |
| **WebGPU Tension Net Visualizer** | `00_core_infrastructure/self_healing_hub/frontend/src/WebGPUVisualizer.jsx` | HTML5 Canvas, WebGPU / Metal fallback, RequestAnimationFrame | 120 FPS real-time particle tension net with dynamic velocity integration, boundary reflection, neon cyan/emerald palette, and distance-based alpha-blended tension lines ($d < 110\text{px}$). |
| **3D Spatial Radar & Hologram** | `00_core_infrastructure/self_healing_hub/frontend/src/Spatial3DMapView.jsx` | SVG 3D Isometric Projection, CSS animation | Renders 8m × 8m spatial arena, UWB $\pm 2.5\text{cm}$ spatial anchor coordinates, animated laser beams / optical mesh links, and VLM optical raycast cone angles. |
| **3D Spatial Map & LoRA Engine** | `00_core_infrastructure/self_healing_hub/src/spatial_grappling_map_engine.py` | Python 3, JSON, Math | Ground-truth engine managing 31 OPML positional states, 57 biomechanical transition vectors with joint torque ($\text{Nm}$), execution time windows ($\text{s}$), and automated 24/7 LoRA Alpaca instruction dataset export (`3d_spatial_instructional_map_lora.jsonl`). |
| **Spatial Map Editor & Sandbox** | `00_core_infrastructure/self_healing_hub/frontend/src/SpatialGrapplingMapEditorView.jsx` | React, SVG Interactive Canvas, REST API | 4-tab interactive sandbox: (1) 8m × 8m Tatami Plane Canvas, (2) Technique & Node 3D Editor, (3) Transition & Vector Linker, (4) Attack Flow Simulator (e.g. Berimbolo to RNC, Shin-to-Shin to Heel Hook). |
| **OPML MindMap Parser** | `00_core_infrastructure/self_healing_hub/src/opml_grappling_parser.py` | Python `xml.etree.ElementTree` | Parses structured XML/OPML mindmap files (`canonical_final_copy_mindmap.opml.locked`, `final_copy_grappling_mindmap.opml`) into hierarchical position trees and flat technique records with deterministic difficulty scoring. |
| **Vision-Inertial Fusion Engine** | `00_core_infrastructure/self_healing_hub/src/vision_inertial_fusion_engine.py` | Python, Extended Kalman Filter (EKF), NPU Orchestrator | Fuses MediaPipe 33 3D optical keypoints with Movesense 128Hz IMU (accel/gyro) via 3D EKF ($[x, y, z, v_x, v_y, v_z]$). When optical visibility $< 0.35$ (severe occlusion), automatically transitions to IMU dead-reckoning. NPU prioritized ($\le 1.2\text{W}$). |
| **Joint Safety & Biometrics Radar** | `00_core_infrastructure/self_healing_hub/frontend/src/GrapplingVisionBiometricsView.jsx` | React, REST polling, SVG progress gauges | Displays optical-inertial joint angles (Elbow Extension for Armbar risk, Shoulder Torsion for Kimura risk, Knee Flexion) alongside live Movesense 128Hz telemetry (HR BPM, scramble G-force, DFA-$\alpha_1$ aerobic threshold, Shopify subscription validation). |
| **App Level Manifest** | `01_apps/spatial_grappling_3d/README.md` & `10_spatial_grappling_kinematics/README.md` | Markdown Manifests | Declares 9-DoF IMU fusion, Pixel 10 Pro XL UWB spatial anchors, 955-node OPML spatial tree governance, and Genetic MoE SLM / Qwen 2.5 Coder 32B model tier. |

---

### 1.2 Mathematical & Kinematic Models

#### 1. 3D Joint Angle Calculation (Spatial Keypoint Vector Geometry)
Given three 3D landmark points $P_1, P_2, P_3 \in \mathbb{R}^3$ where $P_2$ is the joint vertex:
$$\vec{v}_1 = P_1 - P_2, \quad \vec{v}_2 = P_3 - P_2$$
$$\theta = \arccos\left(\frac{\vec{v}_1 \cdot \vec{v}_2}{\|\vec{v}_1\| \|\vec{v}_2\|}\right) \times \frac{180^\circ}{\pi}$$
- **Elbow Extension (Armbar Risk):** Evaluated across Shoulder $\to$ Elbow $\to$ Wrist. Angles exceeding $165^\circ$ trigger `CRITICAL HYPEREXTENSION LOCK`.
- **Shoulder Internal Rotation (Kimura Risk):** Evaluated across Chest Fulcrum $\to$ Shoulder $\to$ Elbow/Wrist. Angles exceeding $85^\circ$ trigger `CRITICAL ROTATIONAL TORSION`.

#### 2. Extended Kalman Filter (EKF) 3D Dead-Reckoning under Occlusion
State vector: $\mathbf{x} = [x, y, z, v_x, v_y, v_z]^T$
- **Prediction Step (Movesense 128Hz IMU):**
  $$\mathbf{x}_{k|k-1} = \mathbf{F} \mathbf{x}_{k-1|k-1} + \mathbf{B} \mathbf{a}_k$$
  where $\mathbf{a}_k = [a_x, a_y, a_z - g]^T$ (gravity bias compensated).
- **Measurement Update (Optical Keypoints):**
  If optical confidence $c_k \ge 0.35$:
  $$R_{\text{eff}} = \frac{R_{\text{vision}}}{\max(0.01, c_k)}, \quad K_k = \frac{P_k}{P_k + R_{\text{eff}}}$$
  $$\mathbf{x}_{k|k} = \mathbf{x}_{k|k-1} + K_k (z_k - \mathbf{x}_{k|k-1})$$
  If $c_k < 0.35$, skip optical update and retain pure IMU integration.

#### 3. WebGPU GEMM WGSL Shader Architecture
Dispatches parallel $16 \times 16$ compute workgroups:
```wgsl
@compute @workgroup_size(16, 16)
fn main(@builtin(global_invocation_id) global_id : vec3<u32>) {
  let row = global_id.y;
  let col = global_id.x;
  let n = 256u;
  if (row >= n || col >= n) { return; }
  var sum = 0.0;
  for (var k = 0u; k < n; k = k + 1u) {
    sum = sum + firstMatrix.data[row * n + k] * secondMatrix.data[k * n + col];
  }
  resultMatrix.data[row * n + col] = sum;
}
```

---

## Part 2: Requirement 4 (R4) — Hands-Free Voice IDE & Side-by-Side CoT Reasoning AST Diff Viewer

### 2.1 Architectural Topology & Component Inventory

| Subsystem Component | File Path | Key Technologies | Function / Capabilities |
|---|---|---|---|
| **Custom Voice IDE View** | `00_core_infrastructure/self_healing_hub/frontend/src/CustomVoiceIDEView.jsx` | React 3-Column Split Layout | Tri-column pairing IDE: (Left) AI Fabric Chat & Voice, (Center) Device Workspace Simulator, (Right) Multi-Daemon Streaming Logs. |
| **IDE Native Voice Channel** | `00_core_infrastructure/self_healing_hub/frontend/src/components/IDENativeVoiceChannel.jsx` | Web MediaDevices API, RecordRTC, StereoAudioRecorder | Ultravox V0.7 / Web Speech voice interface capturing raw audio streams (`audio/webm`), chunked into 1000ms buffers for real-time speech-to-text transmission and bidirectional synthesized audio playback. |
| **Multi-Agent Live Chat Room** | `00_core_infrastructure/self_healing_hub/frontend/src/TriOrchestratorLiveChatView.jsx` | React, REST API, Slash Command Parser | Full multi-agent interaction console routing to Gemini 3.7 Flash, DeepSeek-R1, and Genetic MoE with instant commands (`/multi_beam`, `/debate`, `/obsidian`, `/audit`, `/duel`, `/ping`). |
| **App Simulator Workspace** | `00_core_infrastructure/self_healing_hub/frontend/src/AppSimulatorWorkspace.jsx` | React, CSS Frame Simulation | Multi-device interactive frame simulator supporting Google Pixel 10 Pro XL ($412 \times 890$), iPhone 16 Pro ($393 \times 852$), and MacBook Pro ($1180 \times 740$) with integrated Voice IDE header. |
| **CoT Reasoning & AST Diff Panel** | `00_core_infrastructure/self_healing_hub/frontend/src/MetaTrainingGameDashboardView.jsx` & `AITrainingGameArenaView.jsx` | React, Monospace Pre-wrap, AST Gate | Expandable Chain-of-Thought inspection drawer displaying model reasoning steps, security invariant passes, memory governor bounds ($\le 75\%$), and unified AST syntax diff previews. |
| **PySpark Distributed AST Engine** | `00_core_infrastructure/self_healing_hub/src/pyspark_ray_network_optimizer.py` & `pyspark_ast_index.json` | Apache PySpark 3.5, Python `ast`, Ray Core | Scans 5,483 codebase files in parallel, generating AST syntax trees, identifying compute bottlenecks, and formulating diff refactorings. |
| **Interactive Terminal Gateway** | `00_core_infrastructure/self_healing_hub/frontend/src/TerminalManager.jsx` | `@xterm/xterm`, `@xterm/addon-fit`, `@xterm/addon-web-links`, WebSocket | Multi-tab xterm.js terminal manager connecting directly to PySpark REPL, Swarm REPL, and SSH/ADB sessions across all 7 nodes. |
| **Backend Daemon SSE Streamer** | `00_core_infrastructure/self_healing_hub/frontend/src/components/BackendTerminal.jsx` | `@xterm/xterm`, EventSource (SSE) | Lightweight read-only terminal streaming real-time daemon logs from `/api/logs/exo`, `/api/logs/llamacpp`, and `/api/logs/petals` with zero CPU overhead. |
| **Universal Self-Healing Daemon** | `00_core_infrastructure/self_healing_hub/src/universal_mesh_healer.py` & `api_server.py` | Python `asyncio`, REST/SSE Gateway | Continuous port listener monitoring WoL (18802), RPC (50052), Dark Fleet PWA (3005), and Voice App (3000) with automatic restart triggers upon process failure. |

---

### 2.2 Data Flow & Event Pipelines

```
[ Operator Voice Input ] 
       │ (Microphone 48kHz PCM)
       ▼
[ IDENativeVoiceChannel (RecordRTC) ] 
       │ (1000ms Audio Blob / Web Speech STT)
       ▼
[ TriOrchestratorLiveChatService (:5001) ] ──► [ Slash Command Parser (/debate, /multi_beam) ]
       │                                                      │
       ▼                                                      ▼
[ Multi-Model Inference (Gemini / DeepSeek / MoE) ]   [ PySpark Distributed AST Slicer ]
       │                                                      │
       ├──────────────────────────────────────────────────────┘
       ▼
[ CoT Reasoning Synthesis & AST Visual Diff Viewer ]
       │ (Zero-Mock Verified Code Replacement)
       ▼
[ TerminalManager / BackendTerminal ] ──► [ Universal Mesh Self-Healing Loop (:3000 / :5001) ]
```

---

## Part 3: Pitch-Black Super-App Integration Strategy

To fulfill the requirements of the Sovereign Pitch-Black Super-App:
1. **Color & Styling Standardization:**
   - Base canvas: `#000000` (Pure OLED pitch-black, 0% chroma background).
   - Accents: Emerald (`#10b981`) for kinematics/verified streams, Cyan (`#38bdf8`) for WebGPU tensors, Purple (`#a855f7`) for AI reasoning/MoE, and Amber (`#f59e0b`) for hardware warnings.
   - Text & Contrast: `#f8fafc` primary headers (21:1 AAA contrast), `#94a3b8` secondary text, `tabular-nums` for all telemetry.
2. **Sub-View Fusion:**
   - **Kinematics Sub-View:** Merge `SpatialGrapplingMapEditorView.jsx`, `WebGPUVisualizer.jsx`, and `GrapplingVisionBiometricsView.jsx` into a unified 3D Tatami Kinematics Suite with 60–120 FPS WebGPU acceleration.
   - **Voice IDE Sub-View:** Merge `CustomVoiceIDEView.jsx`, `TriOrchestratorLiveChatView.jsx`, `IDENativeVoiceChannel.jsx`, and `TerminalManager.jsx` into a side-by-side Voice Pair-Programming Workspace with AST diff viewers and live self-healing daemon logs.
3. **Strict Rule #0 Compliance:**
   - Zero mock data: Ensure all endpoints query live backend services (`/api/spatial/grappling_map`, `/api/grappling/fusion_stream`, `/api/hardware/npu_vram_status`, `/api/chat/messages`, and `/api/telemetry`).

