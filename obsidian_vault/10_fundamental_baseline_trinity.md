---
trigger: always_on
---

# 🛡️ Rule 10: The Fundamental Baseline Trinity Invariant

## 1. The Core Stability Doctrine
Through extensive empirical testing across the 7-Layer hardware mesh, three specific subsystems have proven to be the **most stable, zero-mock, and fault-tolerant**. They are hereby codified as the **Fundamental Baseline Trinity** of the Lauburu Project. 

Under no circumstances may any AI Agent, Orchestrator, or Sandbox Evolution test attempt to deprecate, replace, or overwrite these three foundational pillars. They are the bedrock upon which the rest of the mesh is built.

## 2. Pillar I: Local Master Orchestrator Engine (Target: `prima.cpp`; Runtime: Port 8082 Proxy)
- **Role:** The Sovereign Engine target for Local Orchestration.
- **Topology:** Intended target operates across Unified Memory and Thunderbolt fabric (where L1 links to L8 `lauburu`, L1b Mac mini M2 Pro, and L2 MacBook Pro over three 40 Gb/s TB buses on `bridge0`).
- **Runtime Reality & Invariant:** While full `prima.cpp` ring sharding is an architectural target, Port 8082 currently runs `decentralized_prima_daemon.py` proxying to local inference endpoints (Port 8089 serving `qwen2.5-0.5b-instruct-q4_k_m.gguf` for rapid micro-tasks and Port 8085 serving `Hermes-3-Llama-3.1-8B.Q4_K_M.gguf` for 8B local execution). It is strictly prohibited to replace local orchestration with cloud dependencies when local endpoints are healthy.

## 3. Pillar II: The Network Healer Daemons
- **Role:** The autonomous guardians of mesh connectivity.
- **Components:** `mesh_unhealable_notifier_daemon.py`, `nomad_courier_self_healer.py`, and `active_en0_healer.sh`.
- **Invariant:** These self-healing network monitors must remain perpetually active as native silent background loops. They ensure that Tailscale IP routing, Wi-Fi 7 handshakes, and 1GbE interfaces instantly self-recover during broadband failures. They are never to be paused.

## 4. Pillar III: Omnipresent Bluetooth Full-Mesh Graph (Layer 0)
- **Role:** The ultimate zero-infrastructure, IP-less control plane and resurrection layer.
- **Components:** Bluetooth PAN, BLE magic packets, and RFCOMM/L2CAP IP-less serial bridging.
- **Invariant:** All 7 physical layers of the Lauburu mesh (L1 through L7) MUST maintain persistent, IP-less Bluetooth serial pairings with **each other** in a full-mesh topology. This is not limited to Android edges. The Mac Mini (L1) and MacBook Pro (L2) must be permanently bonded over Bluetooth. When Wi-Fi/Tailscale collapses, this omnipresent graph is used to transmit OOB magic packets, WoL, and Screen Lens VLA control payloads.
