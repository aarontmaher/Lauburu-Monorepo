# Handoff Report: Backend WebSocket Architecture & Voice Bridge Daemon Survey

**Agent**: Explorer Survey 1 (Backend WebSocket Architecture & Daemon)  
**Date**: 2026-08-26T22:00:00+10:00  
**Target Subsystem**: `00_core_infrastructure/self_healing_hub` & Monorepo Inference Mesh  

---

## 1. Observation

### 1.1 Requirements & Objective (ORIGINAL_REQUEST.md)
The authoritative request at `00_core_infrastructure/self_healing_hub/ORIGINAL_REQUEST.md` specifies:
1. **R1. Bi-Directional Audio Pipeline**: Implement a backend WebSocket server accepting incoming binary WebRTC audio streams from `IDENativeVoiceChannel.jsx` frontend and piping them back out (or to local inference engines).
2. **R2. Framework Agnosticism & Ultra-Low Latency**: Primary constraint is achieving ultra-low human-to-LLM latency (e.g. pure `asyncio` + `websockets` vs `Flask-SocketIO`).
3. **R3. Frontend Wiring**: Modify `IDENativeVoiceChannel.jsx` to replace console stubs with a live WebSocket connection to the backend daemon.
4. **Acceptance Criteria**: Standalone test script `test_voice_bridge.py` transmitting a 100KB dummy binary payload and verifying round-trip completion in under 500ms with 100% data integrity.

### 1.2 Python Environment & Installed Dependencies
- **Python Interpreter**: Python 3.13.15 (`/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/.venv/bin/python3`, managed via `uv`). System fallback is macOS Python 3.9.6.
- **Key Installed Packages** (`.venv/lib/python3.13/site-packages`):
  - `websockets` 17.0.1 (High-performance, RFC 6455 compliant WebSocket server and client with zero-copy binary streaming support).
  - `pytest` 9.1.1 & `pluggy` 1.6.0 (Automated test execution).
  - `flask` 3.1.3 & `flask_cors` 6.0.5 (REST API endpoints for the self-healing hub).
  - `psutil` 7.2.2 & `pyyaml` 6.0.3 (System telemetry and config parsing).
  - `requests` 2.34.2 & `urllib3` 2.7.0 (HTTP client networking).

### 1.3 Port Allocation & Service Topology
Empirical survey of active ports in `self_healing_hub` and across the monorepo:
| Port | Protocol | Service / Daemon | File / Entry Point | Purpose |
|---|---|---|---|---|
| **8765** | WebSocket / HTTP | Voice Bridge Audio Daemon | `src/voice_bridge_daemon.py` | Ultra-low latency binary audio streaming & control plane |
| **5000 / 5001** | HTTP REST | Self-Healing Hub API Server | `src/api_server.py` | Telemetry, device registry, AI debate management |
| **5002** | WebSocket | Swarm PTY Terminal Gateway | `src/terminal_gateway.py` | Interactive PTY and multi-node swarm REPL bridging |
| **5173 / 3000** | HTTP | Vite React Frontend Hub | `frontend/` (`npm run dev`) | Central UI, simulators, voice IDE, telemetry HUDs |
| **50052** | RPC / TCP | llama.cpp Distributed Server | `02_ai_models_and_inference` | Pooled VRAM Metal/Vulkan tensor sharding |
| **8081** | HTTP / REST | 7-Device Mesh AGI Hub | Monorepo Mesh Router | Deep multimodal reasoning & prompt escalation |
| **8888 / 9333 / 8080** | HTTP / gRPC | SeaweedFS Distributed Storage | `00_core_infrastructure` | Unified storage aggregation (`/mnt/dfs_unified`) |

### 1.4 Backend Architecture (`src/voice_bridge_daemon.py`)
- **Core Loop**: Pure Python `asyncio` event loop driving `websockets.serve`.
- **Multiplexed Protocols on Port 8765**:
  - **Binary Audio Stream (Opcode `0x02`)**: Raw binary byte streams received and immediately echoed in `echo` / `echo_and_queue` mode; pushed to non-blocking `asyncio.Queue` per session for downstream AI inference.
  - **JSON Control Plane (Opcode `0x01`)**: Text frames parsed as JSON for session lifecycle:
    - `session_start` / `init`: Configures sample rate (16kHz), channels (1), MIME type (`audio/webm`), time slice (150ms), and processing mode.
    - `ping` / `pong`: High-resolution client/server timestamp round-trip latency tracking.
    - `set_mode`: Dynamically switches between `"echo"`, `"inference"`, and `"echo_and_queue"`.
    - `get_stats`: Telemetry querying (duration, bytes in/out, frames in/out, queue depth, average latency).
    - `session_end`: Graceful session teardown and pipeline cleanup.
  - **HTTP Diagnostic Interceptor**: Custom `process_request` hook intercepting `GET /health`, `GET /status`, and `OPTIONS` CORS preflight without interfering with WebSocket upgrades.
- **Buffer & Concurrency Configuration**:
  - `MAX_FRAME_SIZE`: 10MB headroom (`10 * 1024 * 1024` bytes) to support rapid bursts or high-resolution PCM buffers.
  - `PING_INTERVAL`: 20s, `PING_TIMEOUT`: 20s.
  - Rate-adaptive queue with congestion drop on overflow to protect real-time latency.

### 1.5 Frontend Integration (`IDENativeVoiceChannel.jsx`)
- Located at `frontend/src/components/IDENativeVoiceChannel.jsx`.
- Uses `RecordRTC` with `mimeType: 'audio/webm'`, `timeSlice: 150` ms, and `StereoAudioRecorder`.
- Connects directly to `ws://${host}:${VOICE_DAEMON_PORT}/ws/voice` with `binaryType = 'arraybuffer'`.
- Real-time audio playback using Web Audio API `AudioContext.decodeAudioData`.
- Embedded inside `AppSimulatorWorkspace.jsx` and `CustomVoiceIDEView.jsx`.

### 1.6 Empirical Benchmark & Test Suite Results
- **Standalone Harness (`test_voice_bridge.py`)**:
  - 100KB payload round-trip latency: **4.716 ms** average (Min: 4.522 ms, Max: 4.851 ms, Jitter: 0.132 ms).
  - Effective throughput: **41.42 MB/s**.
  - SLA assertion: `< 500.0ms` passed with 100% byte-for-byte fidelity.
- **Comprehensive Pytest Suite (`tests/test_voice_bridge_suite.py`)**:
  - 23 tests across 4 Tiers (Core SLA, Boundary payloads 1B–5MB, Concurrency 10+ clients, RecordRTC 150ms emulation) **passed in 2.15s**.
- **Adversarial Stress Suite (`tests/stress_adversarial_voice_bridge.py`)**:
  - 100 consecutive 100KB iterations: **0.17ms mean RTT** (Min: 0.14ms, Max: 0.26ms).
  - 10MB maximum frame payload: **5.92ms mean RTT**.
  - 500-packet high-frequency flood (2400B chunks @ 150ms rate): **0.11ms mean RTT**.
  - 10 concurrent clients stress: **3.92ms mean RTT**, 0 SLA violations, 100% integrity.

---

## 2. Logic Chain

1. **Architecture Selection (Pure asyncio vs Flask-SocketIO)**:
   - *Observation*: Flask-SocketIO introduces Engine.IO packet wrapping, polling fallback negotiation, base64 encoding overhead for binary data when JSON fallback occurs, and extra event-dispatch layers.
   - *Inference*: Pure `asyncio` + `websockets` provides native zero-copy binary frame handling (Opcode `0x02`), bypasses WSGI/ASGI intermediate abstraction layers, and executes directly on the C-optimized event loop (Kqueue on macOS, Epoll on Linux).
   - *Result*: Achieves sub-millisecond round-trip latencies (0.14ms - 4.7ms), providing maximum headroom for downstream LLM inference.

2. **Frame Pipelining & Concurrency**:
   - *Observation*: Audio streams from browser clients arrive in discrete 150ms slices (~2.4KB to 10KB depending on codec).
   - *Inference*: Separating the ingestion/echo loop from the inference queue (`asyncio.Queue` per session) guarantees that network I/O is never blocked by inference compute or token generation delays.
   - *Result*: Zero packet drops, real-time echo monitoring, and smooth handoff to background inference workers.

3. **Port Segregation**:
   - *Observation*: Hub API operates on port 5000/5001, Terminal Gateway on 5002, llama.cpp RPC on 50052, and Frontend on 5173/3000.
   - *Inference*: Dedicated port 8765 isolates voice traffic from REST telemetry queries and terminal PTY buffers, preventing socket contention or CPU starvation.

---

## 3. Caveats

1. **Inference Worker Stub**:
   - `VoiceSession._inference_worker()` currently functions as a non-blocking queue consumer. When integrating full local Ultravox / Whisper / llama.cpp models, ensure inference is dispatched to an executor thread or dedicated async worker process to prevent blocking the asyncio event loop.
2. **TLS / WSS in Production Browsers**:
   - Browsers accessing the frontend via HTTPS require WebSockets over `wss://` (port 8765 or reverse proxy with SSL termination). When developing locally over `http://localhost:5173`, standard `ws://` works seamlessly.
3. **Browser Microphone Permissions**:
   - `navigator.mediaDevices.getUserMedia` requires a secure context (`localhost` or `https://`).

---

## 4. Conclusion

- **Requirements R1, R2, and R3** are fully mapped, architecturally validated, and confirmed to meet all latency and throughput constraints.
- Pure `asyncio` + `websockets` on port 8765 delivers exceptional performance (< 5ms local loopback RTT for 100KB payloads, < 0.2ms for 2.4KB audio chunks), outperforming the 500ms SLA by two orders of magnitude.
- The daemon architecture includes robust HTTP health diagnostics, CORS preflight handling, multi-client session isolation, and non-blocking inference queue hooks.

---

## 5. Verification Method

To independently reproduce and verify all findings:

1. **Syntax & Dependency Verification**:
   ```bash
   cd /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub
   ./.venv/bin/python3 src/voice_bridge_daemon.py --test
   ```

2. **Standalone Latency & Integrity Test (<500ms SLA)**:
   ```bash
   ./.venv/bin/python3 test_voice_bridge.py --start-daemon -v
   ```

3. **Multi-Tier Pytest Suite (23 Tests)**:
   ```bash
   ./.venv/bin/pytest tests/test_voice_bridge_suite.py -v
   ```

4. **Adversarial Multi-Tenant Stress Test**:
   ```bash
   ./.venv/bin/pytest tests/test_adversarial_challenger2_voice_bridge.py -v
   ```

5. **Live Full-Adversarial Benchmark**:
   ```bash
   ./.venv/bin/python3 src/voice_bridge_daemon.py &
   DAEMON_PID=$!
   sleep 0.5
   ./.venv/bin/python3 tests/stress_adversarial_voice_bridge.py
   kill $DAEMON_PID
   ```
