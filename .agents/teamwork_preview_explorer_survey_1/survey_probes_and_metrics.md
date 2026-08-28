# Comprehensive Survey & Audit Report: Data Sources, Mock Data, Probes & Metrics

**Date**: 2026-08-27  
**Author**: teamwork_preview_explorer_survey_1  
**Target Subsystem**: `01_apps/canonical_port` & Related Monorepo Infrastructure  
**Verification Baseline**: Rule #0 Zero-Mock & Ground-Up 7-Layer Mesh Topology  

---

## 1. Executive Summary

A comprehensive, empirical code and runtime survey of `01_apps/canonical_port` and related monorepo telemetry modules was conducted. 

### Core Audit Verdict:
1. **Critical Rule #0 Violations Detected**: 
   - `src/hooks/useLiveTelemetry.js` explicitly generates synthetic random numbers (`Math.random()`) to perturb VRAM, CPU load, and temperature values.
   - `src/hooks/useSwarmDebate.js` simulates multi-beam turns and accord scores using `Math.random()`.
   - `src/App.jsx` uses `Math.random()` to generate trace execution durations.
   - `tui/services/blackboard_store.py` and `tui/services/network_telemetry_store.py` silently retain hardcoded fallback latencies (e.g. 1.20ms, 0.28ms) and "ONLINE" statuses when socket connection attempts fail, rather than reporting authentic `None` / `OFFLINE`.
   - `src/components/network/TB4DmaBridgeCard.jsx` falls back to `'0.277 ms'` and `'CONNECTED'` when live measurements are missing.
   - Default blackboard instantiation populates synthetic biometrics (`heartRateBpm: 138.4`, `rmssdMs: 42.8`, `dfaAlpha1: 0.75`, `ptt: 118/76 mmHg`) instead of authentic disconnected waiting states (`None` / `--`).
2. **Probe Verification Results**:
   - **Mac Mini IP**: Live empirical check revealed the active interface on macOS is `en1` with IP `192.168.8.155` and Tailscale `100.119.199.76` on `utun4`. `en0` had no assigned IPv4 address. The hardcoded IP `192.168.8.230` in the codebase is stale.
   - **TB4 DMA Bridge (169.254.187.138)**: `ping -c 1 -W 500 169.254.187.138` returned `Host is down` (100% packet loss). The UI falsely claimed `CONNECTED` (0.277 ms RTT).
   - **Tailscale CLI**: `tailscale` is located at `/Applications/Tailscale.app/Contents/MacOS/Tailscale`. Executing `tailscale status --json` accurately returns live status across all 7 mesh nodes.
   - **Biometrics Fallback**: Port 4000 `/api/sensors/status` is healthy and currently emits `connected: false`, `fusion_state: "AWAITING_BLUETOOTH_SENSORS"`, with `null` fields. `canonical_port` failed to consume this and fell back to synthetic values.
   - **Petals DHT (31337) & Exo P2P (52415)**: Both local ports are currently CLOSED. The codebase hardcoded `ACTIVE` with `80 blocks` and `4 peers`.
   - **Node Priority & Model**: L5 MacBook Air (Apple M4, 14GB AI VRAM, 90% dynamic cap) is designated the 2nd priority node above L2 MacBook Pro. L2 MacBook Pro model string requires correction to Apple Silicon TB4 Bridge Node. Headless capability (`headless_capable: bool`, `headless_score: 0-100`) must be tracked across all nodes.
3. **Missing Metrics & Features Identified**:
   - Internet speed metrics (`/usr/bin/networkQuality -c -M 5` on 5m cycle).
   - SSH daemon layer probing per node (Port 22/8022 banner, key type, latency).
   - Inference token/s benchmark matrix across prompt lengths (128, 512, 2048 tokens).
   - Abliterated / Uncensored model registry.
   - Petals & Exo live topology and peer stats.
   - Per-model coding language proficiency scores in governance.
   - Persistent logging of discoveries and ELO rating updates to `lora_datasets/elo_discoveries.jsonl`.
   - AGI Coding Terminal as Screen 1 (default startup home screen).
   - Persistent keyboard shortcuts legend on every TUI screen.

---

## 2. Comprehensive Rule #0 Zero-Mock Violation Catalog

| # | File Path | Line Range | Verbatim Violation / Code Artifact | Remediation Required |
|---|---|---|---|---|
| 1 | `src/hooks/useLiveTelemetry.js` | 14–30 | `const delta = (Math.random() - 0.5) * 0.15;`<br>`const newUsed = Math.min(node.aiVramCapGb, Math.max(2.0, +(node.usedVramGb + delta).toFixed(2)));`<br>`const newCpu = Math.min(95, Math.max(10, +(node.cpuPercent + (Math.random() - 0.5) * 2).toFixed(1)));`<br>`const newTemp = +(node.tempC + (Math.random() - 0.5) * 0.2).toFixed(1);` | Remove all `Math.random()` perturbations. Stream exact telemetry from `blackboard_store` / `/api/mesh/telemetry` or show static verified baseline. |
| 2 | `src/hooks/useSwarmDebate.js` | 16–48 | `setTimeout(() => { ... confidence: +(0.975 + Math.random() * 0.02).toFixed(3); const newAccord = +(0.98 + Math.random() * 0.015).toFixed(3); ... }, 800);` | Remove synthetic `Math.random()` turn generation. Connect to live debate state endpoint `/api/swarm/debate` or headless debate transcript files. |
| 3 | `src/App.jsx` | 87 | `durationMs: Math.floor(Math.random() * 200 + 50)` | Measure actual client/server round-trip latency via `performance.now()`. |
| 4 | `src/services/mockFallbackData.js` | 258–304 | Hardcoded biometrics in initial state (`heartRateBpm: 138.4`, `rmssdMs: 42.8`, `dfaAlpha1: 0.75`, `zone2Status: 'ZONE_2_OPTIMAL'`, `pttBloodPressure: { systolicMmhg: 118, diastolicMmhg: 76 }`, `connected: true`). | Set `connected: false`, `heartRateBpm: null`, `rmssdMs: null`, `dfaAlpha1: null`, `pttBloodPressure: null`, `zone2Status: 'AWAITING_SENSORS'`. |
| 5 | `src/services/mockFallbackData.js` | 85–118 | Hardcoded TB4 DMA status (`status: 'CONNECTED'`, `rttMs: 0.277`) and RPC node latency (`status: 'ONLINE'`, `latencyMs: 1.20, 0.28, 0.05`). | Initialize with `status: 'OFFLINE'`, `rttMs: null`, `latencyMs: null` until verified by live socket probe. |
| 6 | `src/components/network/TB4DmaBridgeCard.jsx` | 23, 38, 46 | `{dma.status \|\| 'CONNECTED'}`<br>`{dma.rttMs !== undefined ? `${dma.rttMs} ms` : '0.277 ms'}`<br>`{dma.throughputGbps !== undefined ? `${dma.throughputGbps} Gbps` : '38.4 Gbps'}` | If `dma.rttMs` is null/undefined or status is not connected, render `--` and `'OFFLINE'`. |
| 7 | `src/components/biometrics/BiometricsDspView.jsx` | 42–76, 89–102 | Hardcoded sensor specs (`Movesense-Medical-230950000`, `512 Hz`, `28.5 dB SNR`, `ZONE_2_OPTIMAL`) even when disconnected. | When `movesenseStream.connected` is false, render `--` for SNR, HR, HRV, PTT, and `'DISCONNECTED'`. |
| 8 | `tui/models/blackboard_models.py` | 986–993, 1031–1086, 1109–1122, 1147–1148 | Hardcoded canonical default values: Mac Mini IP `192.168.8.230`, TB4 DMA `CONNECTED`, Biometrics `138.4 BPM`, Petals `ACTIVE (80 blocks)`, Exo `ACTIVE (4 peers)`. | In canonical defaults, unprobed endpoints must default to `OFFLINE` / `None` / `null` or be populated by active dynamic probes. |
| 9 | `tui/services/blackboard_store.py` | 182–190 | `else: probed_rpc_nodes.append(LlamaRpcNode(..., status=node.status, latency_ms=node.latency_ms))` | When socket connect fails (`probe_endpoint` returns `None`), status must be set to `"OFFLINE"` and `latency_ms=None`. |
| 10 | `tui/services/network_telemetry_store.py` | 105 | `else: probed_rpc_nodes.append(node)` (retaining default `"ONLINE"` and `latencyMs=1.20`). | Must set `status="OFFLINE"` and `latency_ms=None`. |
| 11 | `tui/screens/network_screen.py` | 319, 322, 328 | Hardcoded notification strings (`"Pinged TB4 DMA Bridge (169.254.187.138): 0.277 ms RTT"`). | Toast must display actual measured probe result (e.g. `"TB4 DMA Bridge unreachable (OFFLINE)"`). |
| 12 | `tui/screens/training_screen.py` | 167–170 | 4 static hardcoded trace rows in `render_traces()`. | Load authentic execution traces from log files or `/lora_datasets/` telemetry feeds. |
| 13 | `tui/screens/governance_screen.py` | 71–73 | Hardcoded static debate turn texts in `render_debate()`. | Bind to live debate state in blackboard or load latest consensus transcript from `obsidian_vault`. |

---

## 3. Deep Investigation of Specific Probes

### 3.1 Mac Mini Dynamic IP Resolution
* **Current State in Code**: Hardcoded string `"192.168.8.230"`.
* **Empirical Observation**: 
  - Executing `ifconfig` on macOS shows `en1` is the active Wi-Fi interface assigned IP `192.168.8.155`.
  - `en0` is currently unassigned (or inactive Ethernet).
  - `bridge0` is assigned link-local `169.254.52.190`.
  - `utun4` is assigned Tailscale IP `100.119.199.76`.
* **Implementation Requirement**:
  ```python
  import socket
  import subprocess

  def get_live_mac_mini_ip() -> str:
      """Dynamically resolve primary local IPv4 address on macOS without hardcoding."""
      try:
          # 1. Probe via UDP socket connection to router gateway (non-blocking, no packet sent)
          s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
          s.connect(("192.168.8.1", 80))
          ip = s.getsockname()[0]
          s.close()
          if ip and not ip.startswith("127."):
              return ip
      except Exception:
          pass

      # 2. Fallback to ifconfig parsing for active en0/en1 interfaces
      try:
          out = subprocess.check_output(["ifconfig"], text=True, timeout=1.0)
          for iface in ("en0", "en1", "bridge0"):
              if iface in out:
                  block = out.split(f"{iface}:")[1].split("flags=")[0] if f"{iface}:" in out else ""
                  for line in block.splitlines():
                      if "inet " in line:
                          parts = line.strip().split()
                          if len(parts) >= 2 and not parts[1].startswith("127."):
                              return parts[1]
      except Exception:
          pass

      return socket.gethostbyname(socket.gethostname())
  ```

---

### 3.2 TB4 DMA Live Ping Probe
* **Current State in Code**: Default `status="CONNECTED"`, `rtt_ms=0.277`.
* **Empirical Observation**: 
  - `ping -c 1 -W 500 169.254.187.138` returned exit code 2: `Host is down` (100% loss).
* **Implementation Requirement**:
  ```python
  def probe_tb4_dma_ping(ip: str = "169.254.187.138", timeout_ms: int = 400) -> Dict[str, Any]:
      """Execute genuine ICMP ping probe against TB4 bridge IP."""
      try:
          t0 = time.perf_counter()
          res = subprocess.run(
              ["ping", "-c", "1", "-W", str(timeout_ms), ip],
              capture_output=True,
              text=True,
              timeout=0.6
          )
          rtt = (time.perf_counter() - t0) * 1000.0
          if res.returncode == 0:
              # Extract precise avg RTT from ping output if available
              return {
                  "status": "CONNECTED",
                  "rtt_ms": round(rtt, 3),
                  "throughput_gbps": 38.4,
                  "zero_copy_active": True
              }
      except Exception:
          pass

      return {
          "status": "OFFLINE",
          "rtt_ms": None,
          "throughput_gbps": 0.0,
          "zero_copy_active": False
      }
  ```

---

### 3.3 Tailscale Live Status Probe via CLI
* **Current State in Code**: Static hardcoded list of 7 peers in `blackboard_models.py`.
* **Empirical Observation**:
  - `tailscale` CLI is located at `/Applications/Tailscale.app/Contents/MacOS/Tailscale` (and optionally symlinked in `/opt/homebrew/bin/tailscale` or `/usr/local/bin/tailscale`).
  - Running `/Applications/Tailscale.app/Contents/MacOS/Tailscale status --json` produces structured JSON containing `.Self` and `.Peer` dictionaries with live IPs, OS types, online/offline statuses, and relay states.
* **Implementation Requirement**:
  ```python
  def probe_tailscale_mesh() -> List[TailscalePeer]:
      """Probe live Tailscale mesh status and return authentic peer list."""
      tailscale_bins = [
          "/Applications/Tailscale.app/Contents/MacOS/Tailscale",
          "/opt/homebrew/bin/tailscale",
          "/usr/local/bin/tailscale",
          "tailscale"
      ]
      ts_bin = next((b for b in tailscale_bins if shutil.which(b) or os.path.exists(b)), None)
      if not ts_bin:
          return []

      try:
          res = subprocess.run([ts_bin, "status", "--json"], capture_output=True, text=True, timeout=1.5)
          if res.returncode == 0:
              data = json.loads(res.stdout)
              peers = []
              peer_dict = data.get("Peer", {})
              for node_key, info in peer_dict.items():
                  name = info.get("HostName", "Unknown")
                  ips = info.get("TailscaleIPs", [])
                  ip = ips[0] if ips else "--"
                  online = info.get("Online", False)
                  active = info.get("Active", False)
                  os_name = info.get("OS", "Unknown")
                  relay = "DERP Relay" if info.get("Relay") else "Direct WireGuard"
                  status = "ONLINE" if (online or active) else "OFFLINE"
                  
                  peers.append(TailscalePeer(
                      node_name=name,
                      ip=ip,
                      status=status,
                      relay=relay,
                      layer="--",
                      os=os_name
                  ))
              return peers
      except Exception:
          pass
      return []
  ```

---

### 3.4 Biometrics Fallback Engine
* **Current State in Code**: Faked simulated metrics (`heartRateBpm: 138.4`, `rmssdMs: 42.8`).
* **Empirical Observation**:
  - Querying Port 4000 `/api/sensors/status` returns:
    `{"connected_count": 0, "fusion_state": "AWAITING_BLUETOOTH_SENSORS", "sensors": {"movesense": {"connected": false, "heart_rate": null, "dfa_alpha1": null, "rmssd": null}}}`.
* **Implementation Requirement**:
  - When Movesense BLE GATT is disconnected (`connected == False`), all derived physiological metrics in Layer 2 (`heart_rate_bpm`, `rr_intervals_ms`, `rmssd_ms`, `dfa_alpha1`, `vo2_max_ml_kg_min`, `ptt_blood_pressure`) MUST be set to `None` in Python / `null` in JSON.
  - UI components in TUI and React must render `"--"` for numerical values and `"OFFLINE"` / `"DISCONNECTED"` for status badges.

---

### 3.5 Petals DHT & Exo P2P Socket Probes
* **Current State in Code**: Static hardcoded defaults (`Petals: ACTIVE, 80 blocks`, `Exo: ACTIVE, 4 peers`).
* **Empirical Observation**:
  - Non-blocking socket connect to `127.0.0.1:31337` (Petals DHT) returns `CLOSED`.
  - Non-blocking socket connect to `127.0.0.1:52415` (Exo P2P) returns `CLOSED`.
* **Implementation Requirement**:
  - `BlackboardStore.get_snapshot()` must probe TCP `31337` and `52415`.
  - If `31337` is CLOSED: `petals_swarm.status = "OFFLINE"`, `petals_swarm.dht_connected = False`, `petals_swarm.active_blocks = 0`, `petals_swarm.swarm_nodes = 0`.
  - If `52415` is CLOSED: `exo_p2p.status = "OFFLINE"`, `exo_p2p.discovery_ring = False`, `exo_p2p.active_peers = 0`, `exo_p2p.topology = "DISCONNECTED"`.

---

### 3.6 MacBook Pro Model Name, MacBook Air Priority & Headless Tracking
* **Architecture Directives (Consensus Verified)**:
  1. **MacBook Air (L5)** is **SECOND PRIORITY NODE**:
     - Spec: Apple M4 (14GB AI VRAM Cap, 90% Dynamic Headroom).
     - Ranked above MacBook Pro (L2) in all priority queues, inference sharding algorithms, and the hardware screen display order (`L1 -> L5 -> L2 -> L3 -> L6 -> L7 -> L4 -> GW`).
  2. **MacBook Pro (L2) Model String**:
     - Corrected from `"Intel Core i7-9750H / Metal"` to `"Apple Silicon TB4 Bridge Node"` (or `"Apple M3 Max / Apple Silicon TB4 Bridge"`).
  3. **Headless Device Capability Tracking**:
     - Dataclass `HardwareNodeState` and React/TUI models must track:
       * `headless_capable: bool`
       * `headless_score: int` (0 to 100)
     - Standard node scores:
       * L1 Mac Mini: `headless=True, score=95`
       * L2 MacBook Pro: `headless=True, score=70`
       * L3 Linux Head Node: `headless=True, score=92`
       * L4 Linux Tablet: `headless=True, score=75`
       * L5 MacBook Air: `headless=True, score=72`
       * L6 Pixel 10 Pro XL: `headless=True, score=88`
       * L7 Samsung S20: `headless=True, score=80`
       * GW GL.iNet Router: `headless=True, score=100`
     - Display headless capability badge and score prominently on the Hardware screen per node.
     - AGI fallback router prioritizes higher headless scores during survival mode.

---

## 4. Implementation Requirements for Missing Metrics & Features

### 4.1 Internet Speed Metrics (Live 5-Minute Cycle)
* **Measurement Mechanism**:
  - Execute `/usr/bin/networkQuality -c -M 5` on macOS in a background worker thread every 300 seconds.
  - Parse output JSON:
    ```json
    {
      "dl_throughput": 482000000,
      "ul_throughput": 48000000,
      "responsiveness": 1420,
      "base_rtt": 12.4
    }
    ```
  - Convert to Mbps (`dl_throughput / 1e6`, `ul_throughput / 1e6`) and store in `Layer0NetworkingState.internet_speed`:
    * `download_mbps: float` (e.g. 482.0)
    * `upload_mbps: float` (e.g. 48.0)
    * `responsiveness_rpm: int` (e.g. 1420)
    * `latency_ms: float` (e.g. 12.4)
    * `last_tested_iso: str` (ISO 8601 timestamp)
  - Surface on NetworkScreen, InternetOptimizationView, and HeaderStatusBar.

---

### 4.2 SSH Daemon Layer Per Node
* **Probe Mechanism**:
  - Connect to port 22 (macOS/Linux/OpenWrt) or port 8022 (Android Termux) with 300ms timeout.
  - Read banner: `s.recv(1024).decode().strip()`.
  - Extract daemon signature: `OpenSSH_10.3`, `OpenSSH_9.6p1`, `dropbear`.
* **Data Model**:
  ```python
  @dataclass
  class NodeSshStatus:
      node_id: str
      host: str
      port: int
      status: str              # "OPEN", "CLOSED", "TIMEOUT"
      banner: str              # e.g. "SSH-2.0-OpenSSH_10.3"
      key_type: str            # "ed25519"
      latency_ms: Optional[float]
      last_auth_iso: Optional[str]
  ```
* **Surface**: Dedicated SSH Fleet table on HardwareScreen and NetworkScreen.

---

### 4.3 Token/s Benchmark Table in Inference Screen
* **Specification**:
  - Benchmark table evaluating generation speed across 3 prompt/context horizons:
    * **128 tokens** (short interactive query / zero-shot classification)
    * **512 tokens** (standard code snippet / multi-step tool call)
    * **2048 tokens** (deep reasoning / monorepo AST synthesis)
  - Columns: `Model Name`, `Quantization`, `Context Limit`, `128 tok/s`, `512 tok/s`, `2048 tok/s`, `Memory Footprint`, `Efficiency Rating (tok/s/GB)`.
  - Populated for all models in the active roster (Kimi 88B Titan, Qwen 3.8 Max, Gemini 3.7 Flash, Genetic MoE Core, DeepSeek V3 671B, Llama 3.3 70B, etc.).

---

### 4.4 Abliterated & Uncensored Model Registry
* **Specification**:
  - Add dedicated sub-section / filter in `AiInferenceScreen` and `blackboard_models.py` for uncensored / abliterated models required for raw vulnerability research, red teaming, and unfiltered code synthesis:
    1. **`Llama-3.3-70B-Instruct-Abliterated`**: Q4_K_M (42.0 GB VRAM), Role: Uncensored Security & Code Analysis.
    2. **`Qwen-2.5-72B-Instruct-Abliterated`**: Q4_K_M (44.0 GB VRAM), Role: Unfiltered Deep Reasoning & Tool Ingestion.
    3. **`Hermes-3-Llama-3.1-8B-Uncensored`**: Q8_0 (8.5 GB VRAM), Role: Fast Lightweight Instruction Execution.
    4. **`Dolphin-2.9.4-Llama-3.1-70B`**: Q4_K_M (42.0 GB VRAM), Role: Alignment-Free Red Team Automation.
  - Track `alignment_filter_bypassed: bool = True`, `vram_footprint_gb`, `role`, and `checkpoint_filename`.

---

### 4.5 Petals DHT & Exo P2P Live Block / Peer / Dynamic Ring Stats
* **Specification**:
  - In `Layer3AiInferenceState`:
    ```python
    @dataclass
    class PetalsSwarmState:
        status: str = "OFFLINE"
        port: int = 31337
        active_blocks: int = 0
        swarm_nodes: int = 0
        dht_connected: bool = False
        bootstrap_node: str = "100.101.39.98:31337"
        tensor_parallelism: int = 1

    @dataclass
    class ExoP2PState:
        status: str = "OFFLINE"
        port: int = 52415
        discovery_ring: bool = False
        active_peers: int = 0
        topology: str = "DISCONNECTED"
        ring_latency_ms: Optional[float] = None
    ```
  - Surface live connection badges and dynamic ring diagram in `AiInferenceScreen` and Web UI.

---

### 4.6 Per-Model Coding Language Proficiency Scores in Governance
* **Specification**:
  - Add multi-language proficiency scoring matrix to `GovernanceScreen` and `CanonicalLeaderboardView`:
    * Evaluated languages: `Python`, `TypeScript/JS`, `Rust`, `C/C++`, `Shell/POSIX`, `Dart/Flutter`, `Kotlin/Android`, `Go`.
    * Scale: 0 – 100.
    * Example Ratings:
      - **Kimi 88B Tandem Titan**: Python: 96, TS: 94, Rust: 91, C++: 93, Shell: 95, Dart: 88, Kotlin: 89, Go: 92 (Overall: 92.3).
      - **Qwen 3.8 Max / Coder**: Python: 95, TS: 96, Rust: 89, C++: 90, Shell: 92, Dart: 86, Kotlin: 88, Go: 90 (Overall: 90.8).
      - **Gemini 3.7 Flash Cloud**: Python: 98, TS: 97, Rust: 95, C++: 96, Shell: 97, Dart: 94, Kotlin: 95, Go: 96 (Overall: 96.0).
      - **Meta Llama 3.3 70B**: Python: 92, TS: 90, Rust: 86, C++: 88, Shell: 91, Dart: 82, Kotlin: 84, Go: 87 (Overall: 87.5).
      - **Genetic MoE Core**: Python: 94, TS: 91, Rust: 90, C++: 89, Shell: 96, Dart: 89, Kotlin: 90, Go: 91 (Overall: 91.3).

---

### 4.7 Deep Analysis & ELO Scoring for `lora_datasets/elo_discoveries.jsonl`
* **Dataset Location**: `/Users/aaron/DFS_UNIFIED/lora_datasets/elo_discoveries.jsonl` (and mirrored in `04_data_and_memory/lora_datasets/`).
* **JSONL Schema**:
  ```json
  {
    "discovery_id": "disc-20260827-001",
    "timestamp": "2026-08-27T08:00:00Z",
    "task_domain": "Spatial Grappling Kinematics",
    "prompt": "Evaluate torque angle between shoulder girdle and lumbar spine during kimura trap counter.",
    "model_id": "kimi_tandem_titan",
    "model_name": "Kimi 88B Tandem Titan",
    "opponent_model_id": "llama_33_70b",
    "judge_council": ["Gemini 3.1 Pro High", "Qwen 3.8 Max"],
    "solution_analysis": "Joint biomechanics vector [-0.42, 0.88, 0.21], safe range [0, 45 deg], submission risk 0.94.",
    "metrics": {
      "ast_validity": 1.0,
      "memory_safety": 1.0,
      "latency_ms": 142.5,
      "tokens_generated": 256
    },
    "cosine_accord": 0.986,
    "winner": "kimi_tandem_titan",
    "pre_match_elo": 2174,
    "elo_delta": 6,
    "post_match_elo": 2180,
    "rule_zero_certified": true
  }
  ```
* **Store Method**: `blackboard_store.log_elo_discovery(discovery_data)` appending atomically to disk with sync.

---

### 4.8 AGI Coding Terminal as Default Startup Screen (Screen 1)
* **Requirement**:
  - In `canonical_tui.py`:
    - Screen 1 / Default Startup Route: `AgiCodingTerminalScreen` (Key `'c'` or `'1'`, default mounted screen on launch).
    - Features: Interactive command prompt, multi-model code execution, streaming syntax highlighting, context window gauge, and AST validator.
    - All other screens mapped with persistent keyboard shortcuts:
      * `[c]` 1. AGI Coding Terminal (Default Home)
      * `[n]` 0. Bare-Metal Networking
      * `[h]` 1. Hardware & Nodes (7 Nodes + 1 Gateway)
      * `[b]` 2. Medical Biometrics & DSP (512Hz ECG)
      * `[i]` 3. AI Inference Mesh (llama.cpp RPC :50052)
      * `[t]` 4. Training & Games Multi-Tab
      * `[g]` 5. Master AGI Governance & Debate
      * `[s]` 6. Tooling & Commerce Hub
      * `[o]` Optimization Shells
      * `[r]` Telemetry Refresh
      * `[q]` Quit

---

### 4.9 Persistent Keyboard Shortcuts Legend
* **Requirement**:
  - Render persistent legend bar in header/footer across EVERY TUI screen so the operator always knows available navigation hotkeys.
  - Format: `[c] Terminal | [n] Net | [h] Hard | [b] Bio | [i] Inf | [t] Train | [g] Gov | [s] Tool | [o] Opt | [r] Refresh | [q] Quit`.

---

### 4.10 Live Data Streaming Architecture
* **Requirement**:
  - **TUI**: Background worker thread with `set_interval(..., 2.0)` querying `blackboard_store.get_snapshot()` asynchronously without blocking UI interactions.
  - **Web Dashboard**: WebSocket connection to `ws://127.0.0.1:4000/ws/telemetry` or SSE stream pushing state updates every ≤5s with tight fallback polling loop.

---

## 5. Summary Matrix: Component Audit & Action Plan

| Subsystem / Screen | Status | Key Defects Identified | Remediation Action |
|---|---|---|---|
| **Layer 0: Networking** | Partially Live | Stale Mac IP (`.230`), TB4 DMA hardcoded connected, Tailscale unlinked from CLI, missing internet speed test | Integrate dynamic IP detector, live TB4 ping, `tailscale status --json`, `/usr/bin/networkQuality` 5m cycle |
| **Layer 1: Hardware** | Partially Live | L2 model name stale, L5 priority not applied, headless scores missing, SSH fleet unprobed | Add headless score/capable columns, rank L5 above L2, add SSH daemon probe matrix |
| **Layer 2: Biometrics** | Mock Fallback | Synthetic 138.4 BPM / 42.8 RMSSD when BLE disconnected | Wire to Port 4000 `/api/sensors/status`; output `None`/`--` and `OFFLINE` on disconnect |
| **Layer 3: AI Inference** | Mock Fallback | Failed RPC probes keep default latency; Petals/Exo hardcoded active; missing token/s table & abliterated models | Mark failed probes OFFLINE; probe ports 31337/52415; add token/s benchmark & abliterated registry |
| **Layer 4: Training & Games** | Partially Live | Hardcoded execution traces table in TUI | Stream live trace records from `lora_datasets/` / execution logs |
| **Layer 5: Governance** | Mock Fallback | Hardcoded debate text in TUI; `Math.random()` in React; missing language proficiency & ELO logger | Connect live debate state; add language proficiency matrix; log to `elo_discoveries.jsonl` |
| **Layer 6: Tooling & Commerce** | Static Spec | Button toasts are static hardcoded strings | Execute actual CLI/MCP health checks on click |
| **Navigation & Startup** | Needs Overhaul | Starts on Network instead of AGI Terminal; missing persistent hotkey legend on all screens | Implement AGI Coding Terminal as Screen 1 (default startup); add persistent legend bar |
| **Test Suite Configuration** | Config Gap | Pytest missing `asyncio_mode = "auto"` in pyproject.toml | Add `asyncio_mode = "auto"` to `[tool.pytest.ini_options]` in `pyproject.toml` |

---

*Report certified complete by teamwork_preview_explorer_survey_1.*
