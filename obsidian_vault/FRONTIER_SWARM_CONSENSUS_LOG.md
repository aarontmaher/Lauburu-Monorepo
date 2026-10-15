
## 2026-09-19 — Ethernet Serial vs USB Serial (6-Vector Evaluation)

**Verdict:** Ethernet Serial wins **6/6**. USB-Serial has zero mesh viability.

| Vector | Ethernet | USB-Serial | Winner |
|---|---|---|---|
| Bandwidth | 1–40 Gbps | ≤12 Mbps | 🏆 Ethernet |
| Latency/Jitter | 0.143ms / 0.017ms | 1–8ms / 0.5–4ms | 🏆 Ethernet |
| Driver Overhead | ~1µs DMA | ~8–25µs, 4 kernel layers | 🏆 Ethernet |
| Multi-Port Bonding | LACP/MPTCP/ECMP | None | 🏆 Ethernet |
| Hardware Failover | <500ms automated | Manual, no daemon | 🏆 Ethernet |
| Topology Fit | 100% — all protocols | 0% (Movesense UART niche only) | 🏆 Ethernet |

**Live telemetry:** bridge0 RTT 0.159ms avg · en0 1000baseT confirmed · USB-Serial bus empty on L1.

Tags: [[frontier_swarm_consensus]] [[mesh_topology]] [[load_balancing]] [[ethernet_serial]]
