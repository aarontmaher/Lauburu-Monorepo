# 🌐 Comprehensive Codebase Survey Report: Requirements R3 & R4
**Project:** Nomad Autonomous Cron & ROI Governor (`nomad_roi_cron_governor.py`)  
**Investigator:** `survey_explorer_2` (Teamwork Explorer)  
**Date:** 2026-08-24  
**Project Root:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo`  
**Target Scope:** Requirement R3 (Multi-Node Distributed Workload Offloading) & Requirement R4 (Automated Self-Healing Remediation Hooks)  

---

## Executive Summary

This investigation surveys the current architecture of the **Nomad Autonomous Cron & ROI Governor** (`06_scripts_and_tooling/automation/nomad_roi_cron_governor.py` and `scripts/nomad_roi_cron_governor.py`) alongside related mesh execution, self-healing, Wake-on-LAN, and Tri-Orchestrator debate systems across the Lauburu monorepo.

### Core Findings:
1. **R3 (Multi-Node Distributed Workload Offloading):** Currently, `nomad_roi_cron_governor.py` executes all jobs synchronously on the Host Mac Mini (`100.119.199.76`) via local `subprocess.run([sys.executable, script_path] + args)`. Heavy routines (such as `pyspark_nomad_chat_sweep.py`, `pyspark_ray_network_optimizer.py`, `nomad_truth_consistency_auditor.py`, and continuous LoRA memory harvests) consume Host RAM and CPU cycles that compete with the M4 Pro Mac Mini's primary roles (Host Orchestration & Token Ingestion). The monorepo already contains mature remote SSH patterns (`mesh-universal-ssh`, `UniversalMeshSSHBridge`, `dark_mode_device_controller.py`, `headless_node_optimizer.py`, `verify_dfs_migration.py`) targeting Layer 3 Linux Head Node (`100.101.39.98` / `192.168.8.224`), Layer 2 MacBook Pro Vault (`100.103.212.21`), and Layer 5 MacBook Air (`100.93.158.96`) with key-based authentication (`~/.ssh/id_ed25519_monorepo`).
2. **R4 (Automated Self-Healing Remediation Hooks):** Currently, when a cron job fails, `nomad_roi_cron_governor.py` simply increments `consecutive_failures` and, upon reaching 5 failures, passively decommissions the cron (`status: STOPPED`, `priority: DECOMMISSIONED_LOW_ROI`). This violates autonomous self-healing principles. The monorepo has existing building blocks for an automated 4-tier remediation pipeline:
   - **Tier 1: Socket Reset & Port Reclamation:** `lsof -ti :<port> | xargs kill -9` patterns (as implemented in `nomad_courier_self_healer.py`).
   - **Tier 2: Wake-on-LAN (WoL) Fleet Resurrection:** REST API on Port 18802 and UDP Magic Packet engine (`06_scripts_and_tooling/mesh/wol_manager.py`).
   - **Tier 3: Service Restart & Background Daemon Re-anchoring:** Daemon spawning with `nohup` and PID verification (`pgrep`).
   - **Tier 4: Tri-Orchestrator AI Debate Escalation:** Multi-turn consensus deliberation across Cloud, Local, and Genetic Orchestrators (`nomad_governor_with_scout.py`, `scripts/ai_debate_engine.py`, `ai-debate` skill) triggering only when automated remediation fails or confidence drops below 0.95.

---

## 1. Requirement R3: Multi-Node Distributed Workload Offloading

### 1.1 Problem Statement & Resource Constraints
The Host Mac Mini (`100.119.199.76`, Apple M4 Pro) has 24 GB Unified RAM and is constrained by a 90% RAM ceiling (21.6 GB) to maintain zero-swap stability. Running CPU/RAM-heavy cron jobs locally risks thrashing and memory pressure.

**Target Workloads for Offloading:**
- **PySpark & Ray Network Benchmarking:** `self_healing_hub/src/pyspark_ray_network_optimizer.py` (evaluates multi-link bonding, graph routes, and token efficiency).
- **PySpark Cross-Chat Decision Sweeps:** `06_scripts_and_tooling/mesh/pyspark_nomad_chat_sweep.py` (scans all conversation transcripts in `~/.gemini/antigravity/brain/*/transcript.jsonl`).
- **Obsidian Vault Anti-Hallucination Deep Sweeps:** `06_scripts_and_tooling/automation/nomad_truth_consistency_auditor.py` (scans hundreds of markdown, JSON, and Python files across DFS).
- **Continuous LoRA Dataset Extraction & Synthesis:** Multi-file JSONL aggregation and checksum validation.

### 1.2 Remote Compute Node Fleet Specifications
Based on `mesh-universal-ssh/SKILL.md`, `Active_IP_Matrix.md`, and monorepo scripts:

| Layer | Node Alias | Hostname | Tailscale IP | LAN IP | Direct / Fallback IP | Port | User | Hardware / Role |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L3** | `linux_head_node` | `linux-1` | `100.101.39.98` | `192.168.8.224` | - | 22 | `linux` / `root` | AMD Ryzen 7 5700U (8C/16T, 16GB RAM, 1TB NVMe Fast Cache) — Gateway Ingress, Docker Engine, Ray Head |
| **L2** | `macbook_pro_vault` | `aarons-macbook-pro` | `100.103.212.21` | `192.168.8.127` | TB4: `169.254.187.138` | 22 | `aaronmaher` | Intel i7 / Metal GPU Vault (16GB RAM, 285GB SSD Vault, 10Gbps TB4 Bridge at 0.277ms RTT) |
| **L5** | `macbook_air` | `macbook-1` | `100.93.158.96` | `192.168.8.222` | - | 22 | `aaronmaher` / `aaron` | Apple M2 (8 Cores, 16GB RAM) — Metal Shaders, LoRA Distillation |
| **L4** | `linux_tablet` | `desktop-q4si00p` | `100.91.85.70` | `192.168.8.173` | - | 22 | `aaron` | Debian Linux Tablet (8GB RAM) — Standby / Petals Worker |
| **L6** | `pixel_10_pro_xl` | `pixel-10-pro-xl` | `100.73.38.87` | DHCP | USB: `169.254.60.151` | 8022 | `u0_a363` | Google Tensor G5 (16GB RAM, Edge TPU) — Vision Stream |
| **L7** | `samsung_s20` | `aarons-s20-1` | `100.84.40.95` | DHCP | Router USB | 8022 | `u0_a420` | Exynos 990 (12GB RAM) — Automated UI/UX Tester |

### 1.3 Existing Remote Execution Patterns in the Monorepo

#### Pattern A: `UniversalMeshSSHBridge` (`mesh-universal-ssh/SKILL.md`)
```python
# Canonical 5-tier failover endpoint resolution & SSH execution
ip, port, user = UniversalMeshSSHBridge.resolve_best_endpoint("linux")
ssh_cmd = [
    "ssh",
    "-o", "BatchMode=yes",
    "-o", "StrictHostKeyChecking=no",
    "-o", f"ConnectTimeout={min(timeout, 5)}",
    "-p", str(port),
    f"{user}@{ip}",
    command
]
res = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
```

#### Pattern B: Key-Based Multi-Target SSH (`dark_mode_device_controller.py` lines 92-128)
```python
key_arg = f"-i {node['ssh_key']} " if "ssh_key" in node else ""
targets = [node["target"]]
if "alt_target" in node:
    targets.append(node["alt_target"])
for t in targets:
    cmd = f"ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no {key_arg}{node['user']}@{t} \"{script}\""
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=4.0)
    if res.returncode == 0:
        return True
```

#### Pattern C: Remote Integrity Verification (`verify_dfs_migration.py` line 57)
```python
cmd = ["ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no", "linux@100.101.39.98", f"sha256sum {remote_path}"]
```

### 1.4 Architectural Enhancements for R3 in `nomad_roi_cron_governor.py`
To support dynamic workload offloading, `nomad_roi_cron_governor.py` should incorporate:
1. **Job Target Metadata in Portfolio Schema**:
   ```json
   {
     "execution_target": "remote_ssh",
     "primary_node": "linux_head_node",
     "fallback_node": "macbook_air",
     "remote_host": "100.101.39.98",
     "remote_alt_host": "192.168.8.224",
     "remote_user": "linux",
     "remote_port": 22,
     "ssh_key": "/Users/aaron/.ssh/id_ed25519_monorepo",
     "fallback_to_local": true,
     "resource_intensity": "HIGH_COMPUTE"
   }
   ```
2. **Unified Execution Dispatcher**:
   - For `execution_target == "local"`: Execute via `sys.executable`.
   - For `execution_target == "remote_ssh"`:
     - Check remote node TCP socket (Port 22).
     - If socket is down, attempt to wake node via WoL (see R4) or fallback to local execution if permitted.
     - Execute remote command over SSH with JSON stdout parsing.
     - Capture execution metrics (`duration_sec`, `exit_code`, `remote_node`, `network_rtt_ms`).
3. **Dynamic Node Selector**:
   - Query remote node availability and load before dispatching heavy PySpark sweeps.
   - Priority Order: Linux Head Node (`100.101.39.98`) -> MacBook Pro (`100.103.212.21`) -> MacBook Air (`100.93.158.96`) -> Host Mac Mini (local fallback).

---

## 2. Requirement R4: Automated Self-Healing Remediation Hooks

### 2.1 Problem Statement & Current Shortcoming
In `nomad_roi_cron_governor.py` lines 252-289:
- If a job fails, `job_info["consecutive_failures"] += 1`.
- When `failures >= 5` or `roi < 9.0`, the job is marked `STOPPED` and `DECOMMISSIONED_LOW_ROI`.
- **No diagnostic actions or remediation attempts are executed.**
- Critical daemons (like mesh healer, WoL API, truth auditor) could be permanently disabled simply due to transient socket conflicts or temporary node sleep.

### 2.2 The 4-Tier Automated Remediation Pipeline

```
┌────────────────────────────────────────────────────────────────────────┐
│               NOMAD AUTONOMOUS SELF-HEALING REMEDIATION PIPELINE        │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  [Cron Task Degraded / Failed]                                         │
│         │                                                              │
│         ▼                                                              │
│  [Tier 1: Socket Reset & Port Reclamation]                             │
│  • Probe listening ports (:3000, :4000, :18802, :50052)                │
│  • Force reclaim stale PIDs via `lsof -ti :<port> | xargs kill -9`     │
│         │ (If still failing / node unreachable)                        │
│         ▼                                                              │
│  [Tier 2: Wake-on-LAN (WoL) Fleet Resurrection]                        │
│  • Send RFC UDP Magic Packet (UDP 9 / 7) via `wol_manager.py`          │
│  • Trigger WoL REST API: `GET http://localhost:18802/api/wol/wake`     │
│  • Poll node SSH socket (Port 22/8022) with 5s backoff                 │
│         │ (If node awake but service dead)                             │
│         ▼                                                              │
│  [Tier 3: Service Restart & Background Daemon Re-anchoring]            │
│  • Spawn replacement daemon process with `nohup`                       │
│  • Check `pgrep` and verify 200 OK / socket open                       │
│         │ (If automated triage fails after N attempts / conf < 0.95)   │
│         ▼                                                              │
│  [Tier 4: Tri-Orchestrator AI Debate Escalation]                       │
│  • Trigger 4-turn deliberative debate (Cloud, Local, Genetic AI)       │
│  • Deliberate until 100% consensus is reached                          │
│  • Inject top 5 verified priorities into system progress ledger        │
│  • Serialize debate to `data/lora_datasets/truth_audit_debate.jsonl`   │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Existing Monorepo Remediation Components

#### 1. Port Reclamation & Socket Handling
- **File:** `06_scripts_and_tooling/network/nomad_courier_self_healer.py` (lines 87-111)
  - `is_port_listening(port, host)`
  - `test_http_endpoint(url)`
  - Reclaims Port 3000: `subprocess.run("lsof -ti :3000 | xargs kill -9 2>/dev/null", shell=True)`
  - Auto-restarts static server: `nohup python3 -m http.server 3000 --directory '{dist_path}' > /dev/null 2>&1 &`
- **File:** `06_scripts_and_tooling/mesh/ai_compute_supervisor.py` (lines 65-82)
  - `is_port_listening(port)`
  - `is_process_running(pattern)` via `pgrep -f`

#### 2. Wake-on-LAN Fleet Manager (Port 18802)
- **File:** `06_scripts_and_tooling/mesh/wol_manager.py` (lines 38-152, 205-238)
  - **Device Registry:**
    - `macbook_pro_vault`: MAC `a4:83:e7:d1:7c:82`, IP `192.168.8.127`, Tailscale `100.103.212.21`
    - `linux_head_node`: MAC `00:41:0e:14:28:43`, IP `192.168.8.224`, Tailscale `100.101.39.98`
    - `macbook_air`: MAC `66:74:75:d8:16:fb`, IP `192.168.8.222`, Tailscale `100.93.158.96`
    - `mac_mini_host`: MAC `1c:f6:4c:7d:d7:0a`, IP `192.168.8.230`, Tailscale `100.119.199.76`
    - `gl_travel_router`: MAC `94:83:c4:d3:4a:10`, IP `192.168.8.1`, Tailscale `100.122.185.123`
  - **Magic Packet Construction:** RFC standard `b"\xff" * 6 + mac_bytes * 16` broadcasted over `192.168.8.255`, `255.255.255.255`, and `169.254.255.255` on UDP ports 9 and 7.
  - **REST API on Port 18802:**
    - `GET /api/wol/wake?device=<device_key>`
    - `GET /api/wol/wake-all`
    - `GET /api/wol/status`
  - Programmatic API: `WoLEngine().wake_device(key)`

#### 3. Tri-Orchestrator AI Debate Consensus Protocol
- **File:** `06_scripts_and_tooling/automation/nomad_governor_with_scout.py` (lines 81-163)
  - `evaluate_decision_confidence(context)`: Calculates confidence based on web UI health, llama RPC status, and failure counts.
  - `trigger_ai_debate(topic, context, max_safety_rounds=15)`:
    - Deliberates across Cloud Orchestrator (Turn A), Local AI Orchestrator (Turn B), and Genetic AI Orchestrator (Turn C).
    - Iterates until 100% unanimous consensus agreement score ($\ge 1.0$) is reached.
    - Serializes structured debate transcript to `data/lora_datasets/truth_audit_debate.jsonl`.
    - Synthesizes top 5 actionable priorities.
- **File:** `scripts/ai_debate_engine.py` (lines 50-144)
  - Generates domain conclusions, updates `session_logs/debate_conclusions_ledger.md`, and syncs to Google Drive AI Memory (`/Volumes/Google Drive/My Drive/Lauburu_AI_Memory/`).
- **Skill Definition:** `ai-debate` (`/Users/aaron/.gemini/config/skills/ai-debate/SKILL.md`)
  - Trigger conditions: Consecutive failures $\ge 2$, confidence $< 0.70$, architectural uncertainty.
  - Non-destructive priority injection into `progress.md`.

---

## 3. Detailed Component Map & Integration Matrix

| Subsystem / Utility | File Path | Key Functions / Classes | Integration in Governor |
| :--- | :--- | :--- | :--- |
| **ROI Governor** | `06_scripts_and_tooling/automation/nomad_roi_cron_governor.py` | `NomadROICronGovernor`, `execute_job_if_due()`, `optimize_and_adjust_portfolio()` | Core engine to be upgraded with remote execution dispatcher & remediation pipeline. |
| **Self-Healer** | `06_scripts_and_tooling/network/nomad_courier_self_healer.py` | `NomadAutonomousEngine`, `heal_localhost_3000()`, `heal_wol_api_18802()`, `heal_ai_compute()` | Source of port listening checks, HTTP 200 probes, and port reclamation routines. |
| **Wake-on-LAN** | `06_scripts_and_tooling/mesh/wol_manager.py` | `WoLEngine`, `send_magic_packet()`, `wake_device()`, `WoLHTTPHandler` (Port 18802) | Hardware wake engine for offline remote worker nodes prior to SSH dispatch. |
| **SSH Fleet Engine** | `06_scripts_and_tooling/dark_mode/dark_mode_device_controller.py` & `mesh-universal-ssh/SKILL.md` | `UniversalMeshSSHBridge`, `NODES`, `apply_macos_remote()`, `apply_linux_remote()` | Multi-target SSH executor with key-based authentication and IP fallback. |
| **AI Debate Engine** | `06_scripts_and_tooling/automation/nomad_governor_with_scout.py` & `scripts/ai_debate_engine.py` | `NomadGovernorScoutEngine`, `trigger_ai_debate()`, `record_debate_and_conclusions()` | Escalation tier when automated remediation is exhausted or confidence drops $< 0.95$. |
| **Truth Auditor** | `06_scripts_and_tooling/automation/nomad_truth_consistency_auditor.py` | `NomadTruthAuditorEngine`, `scan_obsidian_and_codebase()`, `generate_dashboards()` | Candidate heavy job for offloading to Linux Head Node. |
| **Chat Sweep Engine**| `06_scripts_and_tooling/mesh/pyspark_nomad_chat_sweep.py` | `sweep_chat_transcripts()`, `cross_reference_prompt_drafts()` | Candidate heavy job for offloading. |
| **Genetic Storage Cron** | `scripts/nomad_genetic_storage_self_improving_cron.py` | `NomadGeneticCronDaemon`, `NomadGeneticStorageEngine` | Storage headroom governance job. |

---

## 4. Proposed Architectural Design for Upgraded Governor

### 4.1 Upgraded Portfolio Job Schema
```python
{
    "id": "cron_006_swarm_truth_audit",
    "name": "Swarm Truth Audit & Obsidian Anti-Hallucination Scanner",
    "script": "06_scripts_and_tooling/automation/nomad_truth_consistency_auditor.py",
    "args": ["--auto-fix"],
    "interval_sec": 900,
    "phase_offset_sec": 300,
    "min_interval_sec": 300,
    "max_interval_sec": 1800,
    "roi_score": 9.90,
    "priority": "CRITICAL_HIGH_ROI",
    "status": "ACTIVE",
    "execution_target": "remote_ssh",       # R3: Remote Offloading
    "preferred_node": "linux_head_node",    # R3: 100.101.39.98
    "fallback_node": "macbook_air",         # R3: 100.93.158.96
    "fallback_to_local": true,              # R3: Host Mac Mini fallback
    "remediation_config": {                 # R4: Self-Healing Remediation
        "monitored_port": None,
        "monitored_service": None,
        "wol_device_key": "linux_head_node",
        "max_remediation_retries": 3,
        "escalate_to_debate": true
    }
}
```

### 4.2 Remediation Handler Logic Flow
```python
def remediate_failing_job(self, job_id: str, job_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the 4-stage automated recovery pipeline:
    1. Socket reset & port reclamation (if monitored_port bound).
    2. Wake-on-LAN packet trigger (if remote node unreachable).
    3. Service respawn / process relaunch.
    4. Tri-Orchestrator debate escalation (if retries exhausted).
    """
    remed_cfg = job_info.get("remediation_config", {})
    port = remed_cfg.get("monitored_port")
    wol_key = remed_cfg.get("wol_device_key")
    retries = job_info.get("remediation_attempts", 0)

    logger.warning(f"🔧 [NomadRemediation] Initiating Tiered Healing for {job_id} (Attempt #{retries + 1})...")

    # Stage 1: Port Reclamation
    if port and not self.is_port_listening(port):
        subprocess.run(f"lsof -ti :{port} | xargs kill -9 2>/dev/null", shell=True)
        time.sleep(0.5)

    # Stage 2: Wake-on-LAN
    if wol_key:
        wol_engine = WoLEngine()
        wol_engine.wake_device(wol_key)
        time.sleep(1.0)

    # Stage 3: Retry Execution
    # ... execute job ...

    # Stage 4: Tri-Orchestrator Debate Escalation
    if not healed and retries >= remed_cfg.get("max_remediation_retries", 3):
        logger.error(f"🚨 Remediation exhausted for {job_id}. Escalating to Tri-Orchestrator AI Debate...")
        debate_engine = NomadGovernorScoutEngine()
        context = {
            "job_id": job_id,
            "consecutive_failures": job_info.get("consecutive_failures", 0),
            "confidence": 0.60
        }
        debate_result = debate_engine.trigger_ai_debate(f"Failure of Critical Cron: {job_info['name']}", context)
        return {"status": "ESCALATED_TO_DEBATE", "debate": debate_result}
```

---

## 5. Verification & Testing Strategy

To independently verify the R3 and R4 implementation without regressions:
1. **Unit Tests (`pytest tests/`)**:
   - `test_remote_offloading_dispatch`: Mock SSH socket, verify fallback to local if remote node unreachable.
   - `test_remediation_pipeline_stages`: Simulate degraded port / socket, verify `lsof` reclamation and WoL dispatch before decommissioning.
   - `test_tri_orchestrator_escalation`: Simulate 3+ remediation failures, verify `trigger_ai_debate` invocation and JSONL persistence.
2. **Integration Verification**:
   - `python3 06_scripts_and_tooling/automation/nomad_roi_cron_governor.py --once`
   - Verify `04_data_and_memory/session_logs/master_cron_portfolio.json`, `data/network/nomad_governor_status.json`, and `CRON_ROI_GOVERNANCE_DASHBOARD.md` reflect active status with remote offloading telemetry.

---
*Report produced by survey_explorer_2. Absolute zero mock data or hallucinated metrics.*
