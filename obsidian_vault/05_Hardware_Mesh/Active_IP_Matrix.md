---
truth_audited: true
audit_swarm_verified: "2026-09-04"
audit_swarm_engine: "local_llamacpp_rpc+cloud_frontier"
mesh_topology_version: "8-node-verified"
canonical_source: true
---

# 🌐 Active IP & Hardware Routing Matrix

## Thunderbolt 4 PCIe DMA Bridge (`bridge0`)
- **Status:** ACTIVE
- **MTU:** 1500 (Needs scaling to 9000 for jumbo frames)
- **Host Link-Local IP:** `169.254.224.29`
- **Known Peers in Address Cache:** 
  - `36:90:11:cc:f:40` (en4 - MacBook Pro M1 Max)
  - `36:90:11:cc:f:44` (en2)
  - `82:e6:6d:c0:a4:1` (en4 - TB Peer 2)

## Bluetooth PAN / BNEP
- **Status:** SCANNING / PENDING DISCOVERY (No active `bt-pan` connections populated in macOS `networksetup` query currently).

## 🚨 Dynamic RAM Governance Status
- **Current Free/Inactive RAM:** **5.28 GB** (⚠️ VIOLATION OF 9.6 GB SANCTUARY RULE)
- **Swarm Action Required:** Compute tasks MUST be offloaded to the L2 Vault over the active TB4 bridge immediately.
