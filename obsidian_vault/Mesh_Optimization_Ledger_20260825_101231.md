---
title: "Mesh Optimization Ledger"
tags: [optimization, ledger, latency, udp, sysctl]
updated: "2026-08-25"
---

# Mesh Optimization Ledger - Tue 25 Aug 2026 10:12:31 AEST
Initializing Optimization Sequence...
---
## 1. macOS (M4) UDP & IPC Tuning
### Before Optimization:
net.inet.udp.recvspace: 786896
net.inet.udp.maxdgram: 9216
kern.ipc.maxsockbuf: 8388608
### After Optimization:
net.inet.udp.recvspace: 7340032
net.inet.udp.maxdgram: 65535
kern.ipc.maxsockbuf: 8388608
macOS Kernel Tuning Applied.

## 2. Samsung S20 (Android) Doze & Wake Lock Tuning
No ADB devices detected. Skipping Android Doze optimizations.

## 3. GL.iNet Router Hardware Offloading
To apply router hardware offloading, run the following on the router via SSH:
```bash
uci set firewall.@defaults[0].flow_offloading="1"
uci set firewall.@defaults[0].flow_offloading_hw="1"
uci commit firewall
/etc/init.d/firewall restart
```

## 2b. Samsung S20 Termux SSH Optimization
- Successfully established SSH connection over Tailscale to Termux on S20.
- Applied `termux-wake-lock` to prevent CPU sleep.

## 3. GL.iNet Router Hardware Offloading
- SSH access successful.
- `flow_offloading` and `flow_offloading_hw` set to '1' in UCI firewall.
- Firewall successfully restarted with hardware offloading enabled.
