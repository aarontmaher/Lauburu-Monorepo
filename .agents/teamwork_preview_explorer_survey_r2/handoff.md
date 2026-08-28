# Survey Explorer 2: Handoff Report — API & Web Telemetry Audit (Requirement R2)

## 1. Observation

A systematic static and dynamic code audit across the Lauburu Monorepo localhost web services, backend APIs (`self_healing_hub/src`, `00_core_infrastructure/self_healing_hub/src`), and React frontend components (`self_healing_hub/frontend/src`) revealed the following exact file paths, line numbers, and code snippets containing hardcoded legacy limits, obsolete 5-device profiles, incorrect Tailscale IPs, and metric hallucinations:

---

### A. Device Registry & Hardware Profiles (`devices.json`)

**File Path**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/self_healing_hub/src/devices.json` (and `00_core_infrastructure/self_healing_hub/src/devices.json`)

* **Lines 2–16 (`Mac_Node`)**:
  ```json
  "Mac_Node": {
    "use_ssh": true,
    "device_id": "Mac_Node",
    "name": "M4 Mac Mini Host",
    "layer": 1,
    "role": "SWARM_ORCHESTRATOR",
    "ssh_host": "127.0.0.1",
    "tailscale_ip": "100.119.199.76",
    ...
  }
  ```
  *Observed*: Host model is Apple M4 Pro Mac Mini (24GB RAM).
* **Lines 65–79 (`Mac_Mini` Misattribution)**:
  ```json
  "Mac_Mini": {
    "use_ssh": true,
    "device_id": "Mac_Mini",
    "name": "Mac Mini Compute Node",
    "layer": 5,
    "role": "METAL_GPU_COMPUTE_NODE",
    "ssh_host": "100.93.158.96",
    "tailscale_ip": "100.93.158.96",
    "lan_ip": "192.168.8.222",
    "ssh_port": 22,
    "rpc_port": 50052,
    "ssh_user": "aaronmaher",
    "ssh_key": "/Users/aaron/.ssh/id_ed25519",
    "current_tier": 1
  }
  ```
  *Observed*: Node at `100.93.158.96` is labeled as `"Mac_Mini"` / `"Mac Mini Compute Node"`. Ground truth hardware for `100.93.158.96` is the **Apple M4 MacBook Air** (`MacBook_Air`, 16.0 GB RAM).

---

### B. Obsidian Knowledge Vault Syncer (`obsidian_swarm_syncer.py`)

**File Path**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/self_healing_hub/src/obsidian_swarm_syncer.py` (and `00_core_infrastructure/self_healing_hub/src/obsidian_swarm_syncer.py`)

* **Lines 56, 62, 112, 178–179**:
  * Line 56: `- [[swarm]] — **5-Layer Hardware Mesh & Autonomous Lineage** (62.8 GB pooled VRAM, RPC sharding, and 24/7 LoRA distillation).`
  * Line 62: `- **Hardware Pooled Headroom:** 62.8 GB Usable AI VRAM across 7 physical layers.`
  * Line 112: `The **Master Swarm Engine** pools compute across 7 physical devices into a unified 62.8 GB AI VRAM runtime...`
  * Lines 114–122:
    ```markdown
    ## 🖥️ 5-Layer Physical Topology
    | Layer | Node | Network IP / Interconnect | Safe AI VRAM Cap | Priority Fill Rank |
    | :--- | :--- | :--- | :--- | :--- |
    | **Layer 1** | `Mac_Node` (M4 Max) | `127.0.0.1` (Host Orchestrator & Local Vision VLM) | **13.5 GB** | Rank 4 (Fills Last) |
    | **Layer 2** | `MacBook_Pro` | `100.93.158.96` (TB4 10Gbps Direct Link) | **14.0 GB** | Rank 1 (Fills First) |
    | **Layer 3** | `Linux_Head_Node` | `192.168.8.119` (AMD Ryzen 7 + 1TB NVMe) | **13.8 GB** | Rank 2 (Fills Second) |
    | **Layer 4** | `Pixel_10_Pro_XL` | `100.73.38.87` (Tensor G5 Edge TPU) | **12.5 GB** | Rank 5 (Battery Regulated) |
    | **Layer 5** | `Samsung_S20` | `R3CN40CJJ1R` (Router USB ADB / 24/7 Power) | **9.0 GB** | Rank 3 (Fills Third) |
    ```
  * Line 178–179: `2. **Local AI Orchestrator (DeepSeek-R1-32B & Qwen 2.5 on 5-Layer Mesh):** - Provisions 62.8 GB pooled VRAM over 10Gbps Thunderbolt 4 RPC.`

*Observed*: `obsidian_swarm_syncer.py` is invoked via `/api/obsidian/sync` and regenerates markdown notes in `obsidian_vault/`. Every invocation overwrites `Index.md`, `swarm.md`, and `gemini-pro-triad-deliberation.md` with legacy `62.8 GB`, `M4 Max`, and outdated 5-device tables where `MacBook_Pro` is wrongly given IP `100.93.158.96` (which belongs to MacBook Air) and omits Layer 4 Linux Tablet and Layer 5 MacBook Air.

---

### C. Live Device Sentinel & Topology Daemon (`live_device_sentinel.py`)

**File Path**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/self_healing_hub/src/live_device_sentinel.py`

* **Lines 4–7**: `Continuously scans 5-layer hardware mesh (Host Mac, Layer 2 Mac, Linux Node, Pixel 10 Pro XL, Samsung S20, and physical Thunderbolt 4 buses).`
* **Lines 23–112 (`DEVICES_CONFIG`)**:
  * Lines 25–35 (`layer1_host_mac`):
    ```python
    "id": "layer1_host_mac",
    "name": "Host Mac (Layer 1 M4 Mini)",
    "role": "Primary Orchestrator & Memory Governor",
    "layer": 1,
    "tailscale_ip": "100.119.199.76",
    "vram_gb": 13.5,
    "is_host": True
    ```
  * Lines 75–85 (`layer5_mac_mini`):
    ```python
    "id": "layer5_mac_mini",
    "name": "Mac Mini Compute Node (Layer 5)",
    "role": "Secondary High-Speed Metal Node",
    "layer": 5,
    "tailscale_name": "mac-mini",
    "tailscale_ip": "100.93.158.96",
    "lan_ip": "192.168.8.222",
    "rpc_port": 50052,
    "vram_gb": 13.5,
    "ssh_user": "aaronmaher"
    ```
    *Observed*: Node ID `layer5_mac_mini` with IP `100.93.158.96` is the Apple M4 MacBook Air (16GB RAM). Total pooled VRAM sum across all 7 items in `DEVICES_CONFIG` is `13.5 + 14.0 + 13.8 + 6.5 + 13.5 + 12.5 + 9.0 = 82.8 GB`.

---

### D. Petals & llama.cpp RPC Coordinator (`petals_mesh_sharding_coordinator.py`)

**File Path**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/self_healing_hub/src/petals_mesh_sharding_coordinator.py`

* **Lines 60–80 (`layer_1_mac_host`)**:
  ```python
  "layer_1_mac_host": {
      "layer": 1,
      "node_id": "Mac_Node",
      "name": "M4 Mac Mini Host Coordinator",
      "ram_total_gb": 16.0,
      "usable_vram_gb": 13.5,
      "tailscale_ip": "100.93.158.96",   # <-- BUG: 100.93.158.96 is MacBook Air! Host is 100.119.199.76
      "lan_ip": "127.0.0.1",
      ...
  }
  ```
* **Lines 144–164 (`layer_5_mac_mini`)**:
  ```python
  "layer_5_mac_mini": {
      "layer": 5,
      "node_id": "Mac_Mini",
      "name": "Mac Mini Metal Node",
      "ram_total_gb": 16.0,
      "usable_vram_gb": 13.5,
      "tailscale_ip": "100.93.158.96",
      ...
  }
  ```
  *Observed*: `layer_1_mac_host` has an erroneous Tailscale IP collision (`100.93.158.96` instead of `100.119.199.76`), and `ram_total_gb` is listed as 16.0 GB instead of 24.0 GB. `layer_5_mac_mini` should be identified as `layer_5_macbook_air` / `Apple M4 MacBook Air`.

---

### E. Mesh RAM Autoscaler Governor (`ram_autoscaler_governor.py`)

**File Path**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/self_healing_hub/src/ram_autoscaler_governor.py`

* **Line 4**: `Protects host stability, IDE processes (Antigravity Chat), and 5-layer mesh workers.`
* **Lines 40–59 (`HEADROOM_THRESHOLDS_GB` & `HEADROOM_REQUIREMENTS`)**:
  * `Mac_Node` / `mac_host`: `total_gb: 16.0` (Real Host is 24.0 GB).
  * Missing entries for `MacBook_Air` (`100.93.158.96`, 16.0 GB) and `Linux_Tablet` (`100.81.92.125`, 8.0 GB).
* **Line 324**:
  ```python
  "mesh_status": "5-Layer Pooled Mesh (55.58 GB Usable VRAM)"
  ```
  *Observed*: Obsolete 5-layer string and 55.58 GB metric. Real capacity is 7-Device Mesh (82.8 GB Usable AI VRAM / 100+ GB RAM).

---

### F. Central API Server Routes (`api_server.py`)

**File Path**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/self_healing_hub/src/api_server.py`

* **Line 3717**:
  ```python
  @app.route("/api/mesh/dynamic_allocation", methods=["GET", "POST"])
  def get_mesh_dynamic_allocation():
      """Serves the live battery-aware 5-layer mesh allocation, elevated AI cap (62.8 GB), and priority fill order."""
  ```
* **Line 3909–3918 (`/api/device/adaptive_hardware_profile`)**:
  ```python
  @app.route("/api/device/adaptive_hardware_profile", methods=["GET"])
  def get_adaptive_hardware_profile():
      """Returns dynamic, context-aware AI resource allocation caps (NPU, RAM, CPU) based on human activity state."""
      try:
          from adaptive_device_hardware_governor import get_adaptive_hardware_governor
          gov = get_adaptive_hardware_governor()
          return jsonify(gov.compute_adaptive_hardware_profile())
      except Exception as e:
          return jsonify({"error": str(e)}), 500
  ```
  *Observed*: `adaptive_device_hardware_governor.py` is implemented cleanly and queries real `psutil.virtual_memory()` and macOS `ioreg` idle timers.
* **Line 3940**: `"""Performs live scan across 5-layer mesh and returns real-time hardware status & alerts."""`
* **Line 4058**: `"""Attempts 5-layer manual recovery for Layer 2 MacBook Pro (TB4 / Tailscale)."""`
* **Line 4140**:
  ```python
  @app.route("/", methods=["GET"])
  def api_server_root_health():
      return jsonify({
          "status": "ONLINE",
          "service": "Lauburu Central REST & Sensor API",
          "port": 5001,
          "active_mesh_layers": 5   # <-- Legacy 5 instead of 7
      })
  ```

---

### G. Tri-Orchestrator Swarm Arena (`tri_orchestrator_swarm_arena.py`)

**File Path**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/self_healing_hub/src/tri_orchestrator_swarm_arena.py`

* **Line 112**:
  ```python
  "vram_allocated_gb": 62.8,
  ```
  *Observed*: Hardcoded legacy `62.8` instead of `82.8` GB.

---

### H. Multi-Transport Sharding Engine (`unorthodox_multi_transport_sharding_engine.py`)

**File Path**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/self_healing_hub/src/unorthodox_multi_transport_sharding_engine.py`

* **Line 82**:
  ```python
  "notes": "Zero-copy anonymous mmap buffer passing on local host M4 Max memory bus."
  ```
  *Observed*: Hallucinated `"M4 Max"` instead of `"Apple M4 Pro Mac Mini"`.

---

### I. Frontend React Components

1. **`AITrainingGameArenaView.jsx`** (`self_healing_hub/frontend/src/AITrainingGameArenaView.jsx`):
   * Line 1131: `{zeroCostPlan?.hardware_vram_pool_gb || 62.8} GB`
   * Line 1134: `5 Physical Layers Sharded over llama.cpp RPC`
   * Line 1157: `Curated to replace all cloud API dependencies across the 5 hardware mesh layers`
   * Line 1161: `62.8 GB Total VRAM Pool`
   * Lines 658, 856, 926, 1047: `5-layer` references.

2. **`ExpandedAIMeshGameView.jsx`** (`self_healing_hub/frontend/src/ExpandedAIMeshGameView.jsx`):
   * Line 53: `useState('Mac_Node (Host M4 Max)')`
   * Line 2611: `<option value="Mac_Node (Host M4 Max)">Layer 1: Mac_Node (Apple M4 Max Host - 16GB RAM)</option>`
   * Line 2702: `<option value="Mac_Node (Host M4 Max)">Layer 1: Mac_Node (Apple M4 Max Host - 16GB RAM)</option>`
   * Lines 2611–2615 & 2702–2706: Dropdown options only list 5 legacy layers, omitting Layer 4 (Debian Linux Tablet) and Layer 5 (Apple M4 MacBook Air).
   * Line 2584: `Infiltrate remote hardware nodes across the 5-layer mesh...`

3. **`LiveDeviceSentinelHUD.jsx`** (`self_healing_hub/frontend/src/LiveDeviceSentinelHUD.jsx`):
   * Line 23: `'You will receive immediate alerts whenever any 5-layer mesh node is switched off, disconnected, or falls asleep.'`
   * Line 141: `const meshSummary = sentinelData?.mesh_summary || { online_count: 4, total_devices: 5, total_vram_online_gb: 42.65, health_percentage: 80 };`
   * Line 327: `🖥️ Layer 1 Host Mac`
   * Line 434: `🖥️ Layer 5 Mac Mini` (should be `💻 Layer 5 MacBook Air`).

4. **`CanonicalAILeaderboard.jsx`** (`self_healing_hub/frontend/src/CanonicalAILeaderboard.jsx`):
   * Line 142: `<div style={{ fontSize: '0.65rem', color: '#94a3b8', textTransform: 'uppercase' }}>5-Layer AI VRAM</div>`

5. **`App.jsx`** (`self_healing_hub/frontend/src/App.jsx`):
   * Line 172: `{/* 🛰️ 5-LAYER LIVE DEVICE SENTINEL & DISCONNECTION MONITOR */}`

---

## 2. Logic Chain

1. **Root Cause of Markdown Regressions**: Observation B shows that `obsidian_swarm_syncer.py` generates hardcoded markdown content for `Index.md`, `swarm.md`, and `gemini-pro-triad-deliberation.md` with string literals `62.8 GB`, `5-Layer Hardware Mesh`, and `Mac_Node (M4 Max)`. Whenever the syncer executes (on startup or via `/api/obsidian/sync`), it repopulates the Obsidian vault with these hallucinations. Correcting the templates inside `obsidian_swarm_syncer.py` eliminates the source of truth drift.
2. **Device Mislabeling & IP Inconsistencies**: Observation A, C, and D demonstrate that while 7 nodes are configured, Layer 5 is persistently labeled as `Mac_Mini` with name `"Mac Mini Compute Node"`, even though its Tailscale IP `100.93.158.96` is the Apple M4 MacBook Air. Additionally, in `petals_mesh_sharding_coordinator.py`, `layer_1_mac_host` erroneously shares IP `100.93.158.96` with Layer 5 rather than its authentic Host IP `100.119.199.76`.
3. **RAM & Headroom Scaling Integrity**: Observation E shows that `ram_autoscaler_governor.py` tracks only 4 nodes with an assumed 16GB Host total, omitting Layer 4 (Debian Linux Tablet, 8GB) and Layer 5 (Apple M4 MacBook Air, 16GB). Updating `HEADROOM_THRESHOLDS_GB` and `HEADROOM_REQUIREMENTS` to reflect the 7 nodes and the 24GB Host ensures accurate headroom enforcement and prevents false OOM alerts.
4. **Zero-Mock & Telemetry Authenticity**: Observation F and inspection of `metric_pollers.py` and `adaptive_device_hardware_governor.py` confirm that the underlying telemetry collection mechanisms execute authentic live system calls (`ioreg`, `psutil`, `pmset -g batt`, `dumpsys battery`, `termux-battery-status`, `cat /proc/meminfo`). The endpoints are authentic; only the static fallback values, docstrings, and UI layer labels require alignment.

---

## 3. Caveats

1. **Dual Directory Structure**: Both `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/self_healing_hub` and `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub` exist in the monorepo. Modifications should be synchronized to both paths to prevent discrepancies depending on the active service execution working directory.
2. **Localhost Port Mapping**: The Web UI runs on Port 3000 (Vite) / Port 4000 (Hub), and the API server runs on Port 5001 (or Port 4000 depending on environment variable `PORT`). `API_BASE` configurations should remain relative or dynamically resolve `window.location.hostname`.

---

## 4. Conclusion

All localhost web services, REST endpoints, and UI components can be brought into 100% compliance with Requirement R2 and Zero-Mock integrity by applying the targeted modifications detailed in the inventory below:

### Inventory of Required Code Changes

| Component / Target File | Target Lines | Current State | Required Modification |
| :--- | :--- | :--- | :--- |
| `self_healing_hub/src/devices.json` & `00_core_infrastructure/...` | 2–16, 65–79 | Layer 1 has generic name; Layer 5 is `Mac_Mini` with IP `100.93.158.96` | Update Layer 1 to `Apple M4 Pro Mac Mini Host` (24GB); update Layer 5 to `MacBook_Air` (`Headless Apple M4 MacBook Air`, 16GB, `100.93.158.96`). |
| `self_healing_hub/src/obsidian_swarm_syncer.py` & `00_core_infrastructure/...` | 11, 56, 62, 112–122, 178–179 | Hardcoded `62.8 GB`, `5-Layer`, `M4 Max`, wrong IPs in table | Replace all references with `100+ GB RAM / 82.8 GB Usable AI VRAM Headroom`, `7-Device Hardware Mesh`, `Apple M4 Pro Mac Mini (24GB)`, and accurate 7-layer IP table. |
| `self_healing_hub/src/live_device_sentinel.py` | 4–7, 26, 75–85, 389 | `5-layer`, `Host Mac (Layer 1 M4 Mini)`, `layer5_mac_mini` | Update docstrings and alerts to `7-device mesh`; rename `layer5_mac_mini` -> `layer5_macbook_air` (`Headless MacBook Air`); update Layer 1 name to `Apple M4 Pro Mac Mini`. |
| `self_healing_hub/src/petals_mesh_sharding_coordinator.py` | 60–80, 144–164 | `layer_1_mac_host` IP is `100.93.158.96` (collision); Layer 1 RAM is 16GB; Layer 5 is `layer_5_mac_mini` | Set `layer_1_mac_host.tailscale_ip` = `"100.119.199.76"`, `ram_total_gb` = `24.0`; update `layer_5_mac_mini` -> `layer_5_macbook_air` (`Apple M4 MacBook Air`). |
| `self_healing_hub/src/ram_autoscaler_governor.py` | 4, 40–59, 324 | `5-layer`, 16GB host, missing Layer 4 & Layer 5 in dicts, `55.58 GB` status | Update Host RAM to 24.0 GB; add `MacBook_Air` (16GB, 90% cap) and `Linux_Tablet` (8GB, 75% cap); update `mesh_status` to `7-Device Pooled Mesh (82.8 GB Usable AI VRAM Headroom / 100+ GB RAM)`. |
| `self_healing_hub/src/api_server.py` & `00_core_infrastructure/...` | 3717, 3940, 4058, 4140 | `5-layer`, `62.8 GB`, `"active_mesh_layers": 5` | Update docstrings to `7-device mesh (82.8 GB AI Headroom)`; update root health endpoint line 4140 to `"active_mesh_layers": 7`. |
| `self_healing_hub/src/tri_orchestrator_swarm_arena.py` | 112 | `"vram_allocated_gb": 62.8` | Change to `"vram_allocated_gb": 82.8`. |
| `self_healing_hub/src/unorthodox_multi_transport_sharding_engine.py` | 82 | `"host M4 Max memory bus"` | Change to `"host Apple M4 Pro Mac Mini memory bus"`. |
| `self_healing_hub/frontend/src/AITrainingGameArenaView.jsx` | 1131, 1134, 1157, 1161, 658, 856, 926, 1047 | `62.8 GB`, `5 Physical Layers`, `5-layer` | Change `62.8` fallback to `82.8` GB; update `5 Physical Layers` -> `7 Physical Layers`; replace `5-layer` with `7-device / 7-layer`. |
| `self_healing_hub/frontend/src/ExpandedAIMeshGameView.jsx` | 53, 2584, 2611–2615, 2702–2706 | `M4 Max 16GB`, 5-device dropdowns | Update Layer 1 to `Apple M4 Pro Mac Mini Host (24GB RAM)`; populate full 7 physical layers in dropdowns. |
| `self_healing_hub/frontend/src/LiveDeviceSentinelHUD.jsx` | 23, 141, 327, 434 | `5-layer`, `total_devices: 5`, `42.65` fallback, `Layer 5 Mac Mini` | Update notifications to `7-device mesh`; set fallback default to `total_devices: 7`, `total_vram_online_gb: 82.8`; update Layer 5 label to `💻 Layer 5 MacBook Air`. |
| `self_healing_hub/frontend/src/CanonicalAILeaderboard.jsx` | 142 | `5-Layer AI VRAM` | Change to `7-Device AI VRAM`. |
| `self_healing_hub/frontend/src/App.jsx` | 172 | `5-LAYER LIVE DEVICE SENTINEL` | Change to `7-Layer Live Device Sentinel`. |

---

## 5. Verification Method

1. **Static Pattern Audit**:
   Execute regex scans across `self_healing_hub` and `00_core_infrastructure`:
   ```bash
   python3 -c "
   import os, re
   patterns = [r'\b62\.8\s*GB\b', r'\bM4\s*Max\b', r'active_mesh_layers\":\s*5\b']
   for root, _, files in os.walk('self_healing_hub'):
       for f in files:
           if f.endswith(('.py', '.jsx', '.json', '.md')) and not f.startswith('.'):
               p = os.path.join(root, f)
               content = open(p, errors='ignore').read()
               for pat in patterns:
                   if re.search(pat, content):
                       print(f'Match {pat} in {p}')
   "
   ```
   *Pass Condition*: Zero matches returned for active source code and config files.

2. **Adaptive Hardware Profile API Verification**:
   Execute:
   ```bash
   python3 self_healing_hub/src/adaptive_device_hardware_governor.py
   ```
   *Pass Condition*: JSON output reports `total_ram_gb` = `24.0` (or actual host RAM), dynamic `max_ai_usable_ram_gb`, `ui_badge`, and authentic human activity state without error.

3. **Live Device Sentinel & Topology Verification**:
   Execute:
   ```bash
   python3 self_healing_hub/src/live_device_sentinel.py
   ```
   *Pass Condition*: Summary reports `total_devices`: 7, `total_vram_mesh_gb`: 82.8, and verifies connectivity status for all 7 physical layers.

4. **Petals Coordinator Sharding Verification**:
   Execute:
   ```bash
   python3 self_healing_hub/src/petals_mesh_sharding_coordinator.py
   ```
   *Pass Condition*: Sharding plan distributes all 28 layers across 7 nodes with `total_pooled_vram_gb`: 82.8, and `layer_1_mac_host` reports IP `100.119.199.76` (no IP collision with MacBook Air).
