# 00_core_infrastructure — Core Mesh Infrastructure & Containerization

## Scope & Responsibility
Houses all clustering, storage aggregation, network routing, and container definitions powering the 7-device mesh.

## Components
1. **SeaweedFS Cluster:** Master, Filer, and Volume servers aggregating NVMe and SSD storage across all nodes into `/mnt/dfs_unified` (1.701 TB).
2. **Samba Gateway (Containerized):** `dperson/samba` container providing SMB3 with Apple VFS Fruit extensions for macOS Finder and iOS clients.
3. **Tailscale Mesh Overlay:** Encrypted WireGuard overlay connecting all 7 devices across cellular, Wi-Fi, and Ethernet transports.
4. **Systemd Service Units:** Daemons for auto-mounting, keep-alives, and automatic crash recovery.
5. **Docker Compose Stacks:** Declarative container configurations for MinIO, Apache Ray, Portainer, and microservices.

## Key Ports & Endpoints
- SeaweedFS Master: `100.101.39.98:9333` (gRPC: `19333`)
- SeaweedFS Filer: `100.101.39.98:8888` (gRPC: `18888`)
- SeaweedFS Volume Server: `100.101.39.98:8080` (gRPC: `18080`)
- Samba SMB3: `100.101.39.98:445` & `139`


---
## 🤖 Assigned Subsystem Specialist AI
- **Specialist Agent:** `spec-00-core-infrastructure`
- **Assigned Model Tier:** `Qwen 2.5 Coder 32B (Q4_K_M) / Hermes 3 8B`
- **Skill Definition:** `05_agents_and_swarms/antigravity_skills/spec-00-core-infrastructure/SKILL.md`
- **Governance Mandate:** Continuous recursive optimization of this subsystem's documentation, contracts, and test integrity.
