#!/bin/bash
# smb_tb4_eviction_daemon.sh
# Lauburu AI Mesh - ACIO2 Coprocessor Protection Daemon
# Strictly forbids and aggressively evicts SMB file sharing over the 40Gbps Thunderbolt 4 bridge (169.254.x.x).

LOGFILE="/Volumes/Lauburu-Monorepo/obsidian_vault/APPS_AND_FEATURES/SCREEN_LENS_LIVE_OBSERVATIONS.md"

# Silent execution loop
while true; do
    # Find any SMB mounts that are using the 169.254.x.x link-local (Thunderbolt) IPs
    mount | grep smbfs | grep -E "169\.254\." | while read -r line; do
        # Extract the mount point accurately (handles spaces in volume names if quoted, but standard macOS usually mounts to /Volumes/X)
        MOUNT_POINT=$(echo "$line" | sed -n 's/.* on \(\/Volumes\/[^ ]*\) (.*/\1/p')
        
        if [ -n "$MOUNT_POINT" ]; then
            TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
            echo "$TIMESTAMP - 🛑 [ACIO2 EVICTION] Detected prohibited SMB over TB4 at $MOUNT_POINT. Forcefully unmounting to prevent kernel panic." >> "$LOGFILE"
            
            # Force unmount to save the coprocessor
            diskutil unmount force "$MOUNT_POINT" || umount -f "$MOUNT_POINT"
            
            echo "$TIMESTAMP - 🛡️ [ACIO2 REMEDIATION] SMB share $MOUNT_POINT evicted. Please remount using the Tailscale IP (100.x.x.x) or Wi-Fi IP (192.168.8.x) to safely bypass the TB4 coprocessor." >> "$LOGFILE"
        fi
    done
    sleep 5
done
