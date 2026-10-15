---
title: "GoodCloud Security Audit & AI Debate"
tags: [security, router, goodcloud, ai-debate]
---
# ☁️ GoodCloud Security Posture

## 1. Status
- **GoodCloud Service**: Active (`gl-cloud` bound to `gslb-eu.goodcloud.xyz`)
- **Remote SSH**: Enabled
- **Remote Web Access**: Enabled
- **Account**: `aaronmaher`

## 2. Tri-Orchestrator Verdict
The AI Debate swarm evaluated the GoodCloud integration:
- **Cloud Orchestrator**: Approved. Acts as a Layer -1 Out-of-Band fallback if the Tailscale daemon crashes.
- **Red Team**: Flagged as a critical risk. The router's root shell is protected solely by the password `goldfighting1`.
- **Master Local Orchestrator**: Mandated that since GoodCloud relies on web-based password auth, we cannot disable `PasswordAuth` in Dropbear without breaking GoodCloud. The firewall (`nftables`) was audited and confirmed that Port 22 is NOT exposed to the public WAN; it is exclusively proxied via the encrypted `gl-cloud` reverse tunnel.

## 3. Operational Invariants
- If Tailscale drops, use GoodCloud Web UI or Remote SSH to execute `/etc/init.d/tailscale restart`.
- Under no circumstances should `dropbear` be exposed to the `wan` firewall zone.
