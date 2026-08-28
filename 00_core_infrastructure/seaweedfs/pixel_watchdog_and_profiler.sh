#!/data/data/com.termux/files/usr/bin/bash
# 00_core_infrastructure/seaweedfs/pixel_watchdog_and_profiler.sh

# --- 1. Self-Healing Watchdog ---
start_watchdog() {
    echo "[*] Acquiring Android Wake-Lock..."
    termux-wake-lock

    echo "[*] Starting SeaweedFS Volume Watchdog..."
    while true; do
        if ! pgrep -f "weed volume" > /dev/null; then
            echo "[!] weed volume crash detected! Restarting..."
            # Execute the daemon script we built previously
            bash /data/data/com.termux/files/home/Lauburu-Monorepo/00_core_infrastructure/seaweedfs/pixel_volume_daemon.sh &
        fi
        sleep 60
    done
}

# --- 2. Hardware Profiling (Thermals, CPU, Battery) ---
run_diagnostics() {
    echo "=========================================="
    echo "   PIXEL 10 PRO XL - SEAWEEDFS PROFILER   "
    echo "=========================================="
    
    echo -e "\n[+] BATTERY & THERMAL STATE:"
    # Extracts battery level and temperature (divide by 10 for Celsius)
    dumpsys battery | grep -E "level|temperature" | awk '{print $1, $2}'
    
    echo -e "\n[+] SoC THERMAL ZONES (Tensor G5):"
    for zone in /sys/class/thermal/thermal_zone*/temp; do
        temp=$(cat "$zone" 2>/dev/null)
        if [ "$temp" -gt 0 ] 2>/dev/null; then
            # Convert millidegrees to degrees
            deg=$(echo "scale=1; $temp / 1000" | bc)
            echo "$zone: $deg °C"
        fi
    done | sort -nr -k2 | head -n 5

    echo -e "\n[+] CPU & RAM OVERHEAD:"
    top -n 1 -m 5 | grep -E "weed|Mem"
    
    echo -e "\n[+] STORAGE I/O:"
    cat /proc/diskstats | grep -E "sda|mmcblk" | head -n 2
    echo "=========================================="
}

if [ "$1" == "--profile" ]; then
    run_diagnostics
else
    start_watchdog
fi
