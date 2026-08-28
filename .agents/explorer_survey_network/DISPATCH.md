## 2026-08-23T21:59:42+10:00

<USER_REQUEST>
You are the Network Topology Surveyor.
Your Working Directory: /Volumes/nas-1/Lauburu-Monorepo/.agents/explorer_survey_network/
Authoritative Requirements: /Volumes/nas-1/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md

Mission:
Map the network topology and Thunderbolt 4 bridge configuration for the Lauburu-Monorepo storage migration:
1. Read /Volumes/nas-1/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md.
2. Investigate network interfaces and routing on the macOS host (Mac Mini M4 Pro):
   - Inspect `bridge0` (Thunderbolt 4 bridge interface), its status, MTU (e.g., standard vs jumbo frames 9000), assigned IPv4/IPv6 addresses.
   - Inspect other network interfaces (en0, en1, Tailscale, Wi-Fi, Ethernet).
   - Map connectivity between interconnected nodes: Mac Mini M4 Pro, MacBook Air, Linux Head Node.
3. Determine binding configurations for SeaweedFS:
   - Which IP addresses on `bridge0` should the SeaweedFS master (9333), volume (8080), and filer (8888/18888) bind to?
   - How to ensure traffic from MacBook Air and other mesh nodes is routed exclusively over `bridge0` to achieve >2,500 MB/s throughput (~3,500 MB/s wire speed) and avoid 1GbE / Tailscale bottlenecks.
4. Document firewall, port binding, and DNS / /etc/hosts mapping requirements.

Write a comprehensive, self-contained handoff report to:
/Volumes/nas-1/Lauburu-Monorepo/.agents/explorer_survey_network/handoff.md
Send a completion message back to orchestrator when done.
</USER_REQUEST>
