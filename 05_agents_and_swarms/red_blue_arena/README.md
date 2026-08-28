# ⚔️ Red/Blue Team Adversarial Arena

**Autonomous Security Hardening, Devil's Advocate Exploitation & Sovereign AGI Crown Arena**  
**Subsystem:** `05_agents_and_swarms/red_blue_arena`  
**Governing Rules:** Canonical Tri-Vault Storage Rule • Swarm Truth Audit Rule #0  

---

## 📖 1. Overview

The **Red/Blue Team Adversarial Arena** is a continuous, closed-loop AI security and evolutionary intelligence framework built for the Lauburu 7-layer physical mesh. It pits an uncensored **Red Team (Abiliterated Llama / Devil's Advocate)** against a hardened **Blue Team (Defensive Shield & Sentinel)**, governed by multi-objective HuggingFace reward loops (`trl.DPOTrainer`) and the **Sovereign AGI Crown AI Debate Tournament**.

```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                          RED/BLUE ADVERSARIAL ARENA ARCHITECTURE                          │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│  [RED TEAM: Abiliterated Llama]                      [BLUE TEAM: Defensive Shield]        │
│  • Refusal Representation Ablated                    • Ed25519 Multiplexed SSH Engine     │
│  • Constructive Destruction Directive                • 5-Tier Zero-Trust Failover         │
│  • Automated Vulnerability & PoC Discovery           • Mesh Tripwire Sentinel Daemon      │
│                     │                                             │                       │
│                     ▼                                             ▼                       │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                    4-TURN ADVERSARIAL AI DEBATE ARENA                               │  │
│  │  Turn 1: Red Attack Proof & Exploitation Analysis                                   │  │
│  │  Turn 2: Blue Defense Remediation & Cryptographic Patch                             │  │
│  │  Turn 3: Cloud Frontier CoT (Gemini 3.7 / 3.1 Pro) Cross-Audit                      │  │
│  │  Turn 4: Council Consensus Accord & Merkle State Transition                         │  │
│  └─────────────────────────────────────────────────────────────────────────────────────┘  │
│                     │                                             │                       │
│                     ▼                                             ▼                       │
│  ┌───────────────────────────────────────────┐  ┌──────────────────────────────────────┐  │
│  │   HUGGINGFACE TRL / DPO REWARD PIPELINE   │  │   CANONICAL ELO LEADERBOARD ENGINE   │  │
│  │   • Multi-Objective CVSS Scoring ($R_{Red}$) │  │   • Dynamic K-Factor Scaling ($K$)   │  │
│  │   • MTTR & Zero-Regression Reward ($R_{Blue}$)│  │   • Sovereign AGI Crown Award        │  │
│  │   • SFT-Anchored DPO Regularizer          │  │   • Champion Deployment Sync         │  │
│  └───────────────────────────────────────────┘  └──────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛡️ 2. Blue Team Defense Components

Located in `blue_team/`:
- **`blue_team_ssh_shield.py`**: Production-grade multi-transport SSH execution engine.
  - 100% passwordless Ed25519 authentication (zero plaintext passwords).
  - Safe parameterized execution (`shell=False`) preventing command injection.
  - Unix domain socket multiplexing (`ControlMaster auto`, `ControlPersist 10m`) for <3ms latency.
  - Automated 5-tier failover: `TB4 DMA` $\to$ `Headscale WireGuard` $\to$ `Local LAN` $\to$ `USB ADB` $\to$ `WoL Resurrection`.
- **`mesh_tripwire_sentinel.py`**: Cryptographic configuration integrity and port audit daemon.
  - Maintains SHA-256 baselines of `~/.ssh/authorized_keys`, `/etc/ssh/sshd_config`, Headscale ACLs.
  - Detects unauthorized modifications, deleted configs, and rogue listening ports.
  - Emits structured JSONL telemetry to `04_data_and_memory/lora_datasets/security_audit_logs.jsonl`.
- **`configs/sshd_config.hardened`**: Hardened OpenSSH daemon configuration with modern curve25519/chacha20 cipher suites.
- **`configs/ssh_config.client`**: High-speed client configuration with socket pooling for all 8 mesh layers.

---

## ⚡ 3. Quickstart & Usage

### 3.1 Initialize and Check Connection Health
```python
from blue_team.blue_team_ssh_shield import BlueTeamSSHShield

shield = BlueTeamSSHShield()

# Check node health & active transport tier
status = shield.check_connection_health("macbook-pro")
print(f"Node: {status.node}, Reachable: {status.is_reachable}, Tier: {status.active_transport}")

# Execute parameterized command safely
result = shield.execute_command("linux", ["uname", "-a"], timeout_s=5.0)
print(f"Execution Output: {result.stdout} (Latency: {result.latency_ms}ms)")
```

### 3.2 Run Tripwire Sentinel Audit
```python
from blue_team.mesh_tripwire_sentinel import MeshTripwireSentinel

sentinel = MeshTripwireSentinel()
report = sentinel.run_audit_cycle()
print(f"Audit Clean: {not report.is_compromised}, Monitored Files: {report.total_monitored}")
```

---

## 🧪 4. Testing & Verification

Execute the test suite to verify Blue Team security invariants, parameterization, and socket multiplexing:
```bash
# Run unit & security invariant tests
pytest tests/ -v
```

---

## 📚 5. Architecture Documentation
For complete mathematical formulations, system prompts, and tournament rules, see:
- [`red_blue_arena_specification.md`](./red_blue_arena_specification.md)
- [`PROJECT.md`](./PROJECT.md)
