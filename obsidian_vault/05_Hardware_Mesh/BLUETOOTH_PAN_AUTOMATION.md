---
truth_audited: true
audit_swarm_verified: "2026-09-04"
audit_swarm_engine: "local_llamacpp_rpc+polyglot_posix"
mesh_topology_version: "8-node-verified"
---

# 📶 Bluetooth PAN Automation (Zero-Infrastructure Mesh)

## Overview
The script `/06_scripts_and_tooling/mesh_transports/auto_bt_pan.sh` serves as the primary automation engine for the Tier 4/5 Bluetooth Personal Area Network (PAN) fallback routing. 

## Automated Setup Workflow
1. **OS Detection:** The script automatically branches execution based on the Host OS (`Darwin` vs `Linux`).
2. **Bluetooth Power Cycle:** `blueutil` ensures the Host controller is powered on.
3. **BNEP Pairing Connections:** The script automatically loops through the canonical hardware MAC addresses to establish BNEP tunnels.

## Live Verification Results (2026-09-04)
- **Pixel 10 Pro XL (`30-E0-44-6D-18-EC`):** ✅ Successfully Connected
- **Samsung S20+ (`5C-CB-99-05-81-41`):** ✅ Successfully Connected
- **MacBook Pro Vault (`2C-CA-16-08-C0-27`):** ✅ Successfully Connected
- **MacBook Air M2 (`CA-6B-75-9D-8E-92`):** ❌ Connection Failed (Node likely asleep or out of range)

## Notes on the USB Dongle Interface
On the Mac Mini host, the USB Bluetooth dongle maps to the standard Ethernet Adapter stack (e.g., `en5`, `en6`, `en7`) rather than the legacy `Bluetooth PAN` network service, depending on the kernel extension bridging the BNEP interface.
