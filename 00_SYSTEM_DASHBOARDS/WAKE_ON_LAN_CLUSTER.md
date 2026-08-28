# ⚡ Lauburu Fleet Wake-on-LAN & Distributed Compute Dashboard
> **Last Synced:** `2026-08-25 10:59:44`  
> **Active Subnet:** `192.168.8.0/24` | **Tailscale Mesh:** `100.x.x.x` | **Magic Port:** `UDP 9 / 7`

---

## 🎯 Device Registry & Instant Wake Controls

| Device | Role | Hardware MAC | Local LAN IP | Tailscale IP | Quick Wake Command |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 💻 **MacBook Pro M1 Max Vault** | `Storage & Compute Vault (32 GB Unified RAM)` | `a4:83:e7:d1:7c:82` | `192.168.8.127` | `100.103.212.21` | `wol wake macbook_pro_vault` |
| 🐧 **Linux Head Node (AMD Ryzen 7)** | `Continuous AI Training & LoRA Harvest (16 Threads)` | `00:41:0e:14:28:43` | `192.168.8.224` | `100.101.39.98` | `wol wake linux_head_node` |
| 🍏 **MacBook Air M2 Node** | `Mobile AI Agent Worker (8 Cores)` | `66:74:75:d8:16:fb` | `192.168.8.222` | `100.93.158.96` | `wol wake macbook_air` |
| 🖥️ **Host Mac Mini M4** | `Master Orchestrator & Neural Engine Hub` | `1c:f6:4c:7d:d7:0a` | `192.168.8.230` | `100.119.199.76` | `wol wake mac_mini_host` |
| 🛰️ **GL.iNet Travel Router (GL-MT3600BE)** | `Wi-Fi 7 Multi-WAN Gateway & TP-Link Bridge` | `94:83:c4:d3:4a:10` | `192.168.8.1` | `100.122.185.123` | `wol wake gl_travel_router` |

---

## 🚀 Quick Execution Triggers

- **Wake All Sleeping Nodes:**
  ```bash
  python3 /Users/aaron/06_scripts_and_tooling/mesh/wol_manager.py --wake-all
  ```
- **Wake MacBook Pro Vault:**
  ```bash
  python3 /Users/aaron/06_scripts_and_tooling/mesh/wol_manager.py --wake macbook_pro_vault
  ```
- **Wake Linux Head Node:**
  ```bash
  python3 /Users/aaron/06_scripts_and_tooling/mesh/wol_manager.py --wake linux_head_node
  ```

---

## 🌐 Web API & Localhost 3000 Integration

The WoL service exposes an HTTP API for the Localhost 3000 Web UI:
- **Endpoint:** `GET /api/wol/wake?device=<device_key>`
- **Endpoint:** `GET /api/wol/wake-all`
- **Status:** `GET /api/wol/status`

> [!NOTE]
> Last Woken Device: **None**
