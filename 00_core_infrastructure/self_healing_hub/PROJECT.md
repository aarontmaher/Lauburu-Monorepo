# Project: High-Speed Voice Bridge Daemon & IDE Native Voice Integration

## Architecture
- **Backend Service**: Pure `asyncio` + `websockets` daemon on port `8765` (`src/voice_bridge_daemon.py`).
  - RFC 6455 compliant WebSocket server with zero-copy binary audio frame dispatch (Opcode `0x02`).
  - JSON control plane (Opcode `0x01`) handling session lifecycle, ping/pong RTT latency measurement, dynamic mode switching, and diagnostics.
  - Non-blocking `asyncio.Queue` per session for downstream llama.cpp / Ultravox inference dispatch.
  - HTTP diagnostics interceptor for `GET /`, `GET /health`, `GET /status`.
- **Frontend Integration**: React 19 component (`frontend/src/components/IDENativeVoiceChannel.jsx`).
  - Low-latency `RecordRTC` audio capture (16kHz mono, 150ms `timeSlice`).
  - Direct binary `ArrayBuffer` WebSocket streaming to `ws://<host>:8765/ws/voice`.
  - Web Audio API (`AudioContext.decodeAudioData`) inbound synthesized audio playback sink.
  - Continuous ping/pong heartbeat tracking live RTT latency in milliseconds.
- **Testing & Benchmarking Suite**: Standalone test harness (`test_voice_bridge.py`) and multi-tier Pytest suite (`tests/test_voice_bridge_suite.py`).
  - High-precision RTT measurement (<500ms SLA for 100KB payload; empirically ~4.3ms - 4.9ms).
  - 4-Tier test coverage (Unit, Boundary/Chaos, Multi-Client Concurrency, Real-World Acceptance).

## Feature Inventory
| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|--------|
| 1 | Bi-Directional Binary Audio Streaming | Low-latency binary audio frame ingestion and echo/inference routing over WebSocket (port 8765) | M1 | ORIGINAL_REQUEST §R1 | DONE |
| 2 | Pure Asyncio & WebSockets Backend | Framework-agnostic, zero-copy async architecture for ultra-low latency | M1 | ORIGINAL_REQUEST §R2 | DONE |
| 3 | JSON Control Plane & Lifecycle Management | Session handshake (`session_start`), ping/pong latency measurement, mode switching (`echo`, `inference`), teardown (`session_end`) | M1 | Survey 1 & 3 | DONE |
| 4 | HTTP Diagnostic Interceptors | Built-in HTTP handler for `GET /`, `GET /health`, `GET /status` | M1 | Survey 1 | DONE |
| 5 | Non-Blocking Inference Queue Hooks | Per-session async queue buffering audio frames for downstream Ultravox/llama.cpp inference workers | M1 | Survey 1 | DONE |
| 6 | Frontend Live WebSocket Audio Capture | `IDENativeVoiceChannel.jsx` capturing 16kHz mono audio via RecordRTC with 150ms slices and streaming binary buffers | M2 | ORIGINAL_REQUEST §R3 | DONE |
| 7 | Frontend Web Audio Playback & Demux | Demultiplexing incoming binary frames to `AudioContext` speaker output and JSON frames to UI state | M2 | Survey 2 | DONE |
| 8 | Frontend Lifecycle & Hardware Disposal | Complete cleanup of microphone tracks, intervals, and WebSocket connections on unmount | M2 | Survey 2 | DONE |
| 9 | Standalone Latency Test Harness | `test_voice_bridge.py` transmitting 100KB dummy binary payload and verifying <500ms round-trip latency | M3 | ORIGINAL_REQUEST §Acceptance | DONE |
| 10 | Multi-Tier Automated Test Suite | Comprehensive Pytest suite covering Unit, Boundary/Chaos (0B-10MB), Concurrency (10-25 clients), and Acceptance | M3 | Survey 3 | DONE |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Backend WebSocket Daemon | `src/voice_bridge_daemon.py` implementation with binary pipeline, JSON control, health probes, and session management | none | DONE |
| 2 | Frontend IDENativeVoiceChannel Integration | `frontend/src/components/IDENativeVoiceChannel.jsx` live WebSocket audio streaming and playback | M1 | DONE |
| 3 | E2E Latency Verification & Test Suite | `test_voice_bridge.py` standalone benchmark, multi-tier Pytest suite, and adversarial verification | M1, M2 | DONE |

## Interface Contracts
### Frontend `IDENativeVoiceChannel.jsx` ↔ Backend `voice_bridge_daemon.py`
- **WebSocket Endpoint**: `ws://<host>:8765/ws/voice`
- **Binary Audio Frame Format**: Raw binary chunks (WebM or uncompressed PCM), Opcode `0x02`, `ws.binaryType = 'arraybuffer'`.
- **JSON Control Frame Format**: Opcode `0x01`:
  - Client -> Server: `{"type": "session_start", "timeSliceMs": 150, "mimeType": "audio/webm"}`
  - Client -> Server: `{"type": "ping", "client_time": <performance.now()>}`
  - Server -> Client: `{"type": "pong", "client_time": <performance.now()>, "server_time": <timestamp>}`
  - Client -> Server: `{"type": "set_mode", "mode": "echo" | "inference" | "echo_and_queue"}`
  - Client -> Server: `{"type": "get_stats"}`
  - Server -> Client: `{"type": "stats", "session_id": "...", "bytes_in": ..., "bytes_out": ..., "avg_latency_ms": ...}`
  - Client -> Server: `{"type": "session_end"}`

### Test Harness `test_voice_bridge.py` ↔ Backend `voice_bridge_daemon.py`
- **Payload Verification**: 100KB random binary payload (`os.urandom(102400)`).
- **Latency SLA**: Round-trip time `rtt_ms < 500.0` (empirically ~4.3ms - 4.9ms).
- **Integrity**: Exact byte-for-byte matching and SHA-256 digest validation (100% MATCH).

## Code Layout
- `src/voice_bridge_daemon.py`: Backend high-speed WebSocket daemon
- `frontend/src/components/IDENativeVoiceChannel.jsx`: React voice IDE component
- `test_voice_bridge.py`: Standalone latency benchmark test harness
- `tests/test_voice_bridge_suite.py`: Multi-tier Pytest test suite (23 tests)
- `tests/stress_adversarial_voice_bridge.py`: High-throughput & adversarial stress tests
- `tests/test_adversarial_challenger2_voice_bridge.py`: Multi-client concurrency & chaos tests
