#!/bin/bash

# Lauburu Mesh - Settings Optimization & Logging Script
# This script applies system-level optimizations and logs the before/after effects to Obsidian.

OBSIDIAN_LOG="$HOME/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/Mesh_Optimization_Ledger_$(date +%Y%m%d_%H%M%S).md"

echo "# Mesh Optimization Ledger - $(date)" > "$OBSIDIAN_LOG"
echo "Initializing Optimization Sequence..." | tee -a "$OBSIDIAN_LOG"
echo "---" >> "$OBSIDIAN_LOG"

# 1. macOS Tuning (Requires Sudo)
echo "## 1. macOS (M4) UDP & IPC Tuning" | tee -a "$OBSIDIAN_LOG"
echo "### Before Optimization:" >> "$OBSIDIAN_LOG"
sysctl net.inet.udp.recvspace net.inet.udp.maxdgram kern.ipc.maxsockbuf >> "$OBSIDIAN_LOG"

echo "Applying macOS UDP Buffer expansions..."
sudo sysctl -w net.inet.udp.recvspace=7340032
sudo sysctl -w net.inet.udp.maxdgram=65535
sudo sysctl -w kern.ipc.maxsockbuf=8388608

echo "### After Optimization:" >> "$OBSIDIAN_LOG"
sysctl net.inet.udp.recvspace net.inet.udp.maxdgram kern.ipc.maxsockbuf >> "$OBSIDIAN_LOG"
echo "macOS Kernel Tuning Applied." | tee -a "$OBSIDIAN_LOG"

# 2. Android (Samsung S20) Tuning (Requires ADB over TCP or USB)
echo -e "\n## 2. Samsung S20 (Android) Doze & Wake Lock Tuning" | tee -a "$OBSIDIAN_LOG"
echo "Checking for attached ADB devices..."
ADB_DEVS=$(adb devices | grep -w "device")
if [ -z "$ADB_DEVS" ]; then
    echo "No ADB devices detected. Skipping Android Doze optimizations." | tee -a "$OBSIDIAN_LOG"
else
    echo "Applying Doze mode bypasses..." | tee -a "$OBSIDIAN_LOG"
    adb shell dumpsys deviceidle whitelist +com.termux >> "$OBSIDIAN_LOG"
    adb shell dumpsys deviceidle whitelist +com.tailscale.ipn >> "$OBSIDIAN_LOG"
    # Note: Disabling deviceidle entirely may require resetting on reboot
    adb shell dumpsys deviceidle disable >> "$OBSIDIAN_LOG"
    echo "Android Doze Bypasses Applied." | tee -a "$OBSIDIAN_LOG"
fi

# 3. GL.iNet Router Hardware Acceleration (Requires SSH access)
echo -e "\n## 3. GL.iNet Router Hardware Offloading" | tee -a "$OBSIDIAN_LOG"
echo "To apply router hardware offloading, run the following on the router via SSH:" | tee -a "$OBSIDIAN_LOG"
echo '```bash
uci set firewall.@defaults[0].flow_offloading="1"
uci set firewall.@defaults[0].flow_offloading_hw="1"
uci commit firewall
/etc/init.d/firewall restart
```' >> "$OBSIDIAN_LOG"

echo "Optimization script complete. Results logged to $OBSIDIAN_LOG"
