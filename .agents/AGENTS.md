
## GL.iNet Router Network Healing & Nomad Logging Rule (MANDATORY)
- **Centralized Healing Ledger:** Any autonomous network healing, node resurrection (e.g., Wake-on-LAN), or fallback route toggling executed by the Nomad Courier or AI agents MUST be explicitly logged via a centralized healing script residing on the **GL.iNet Core Gateway Router (GW Node: 192.168.8.1 / 100.122.185.123)**. 
- Agents must execute `ssh root@192.168.8.1 "/root/mesh_heal_logger.sh '<ACTION>' '<TARGET_IP>'"` before and after attempting to recover a dropped connection.
