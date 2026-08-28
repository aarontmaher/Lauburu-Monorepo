#!/bin/sh
# GL.iNet OpenWrt Thermal Watchdog for softflowd
# This script runs on the router via cron.

THERMAL_FILE="/sys/class/thermal/thermal_zone0/temp"
WARN_TEMP=75000  # 75.0 C
CRIT_TEMP=85000  # 85.0 C

if [ ! -f "$THERMAL_FILE" ]; then
    echo "Thermal sensor not found."
    exit 1
fi

TEMP=$(cat $THERMAL_FILE)

if [ "$TEMP" -ge "$CRIT_TEMP" ]; then
    echo "[CRITICAL] Temp is ${TEMP}. Executing Thermal Scram!"
    # 1. Kill the NetFlow daemon
    /etc/init.d/softflowd stop
    # 2. Re-enable hardware flow offloading to save the CPU
    uci set firewall.@defaults[0].flow_offloading='1'
    uci set firewall.@defaults[0].flow_offloading_hw='1'
    uci commit firewall
    /etc/init.d/firewall restart
    # 3. Alert the mesh (Mac Mini) via UDP broadcast or webhook
    # echo "ROUTER_THERMAL_CRITICAL" | nc -w 1 -u 192.168.8.230 18802
elif [ "$TEMP" -ge "$WARN_TEMP" ]; then
    echo "[WARNING] Temp is ${TEMP}. Reducing softflowd sampling rate."
    # Change sampling rate to 1:100 to reduce CPU load
    uci set softflowd.cfg.sampling_rate='100'
    uci commit softflowd
    /etc/init.d/softflowd restart
else
    echo "[NOMINAL] Temp is ${TEMP}. Hardware offload OFF, NetFlow 1:1 Active."
    # Ensure optimal deep packet inspection is running
    uci set firewall.@defaults[0].flow_offloading='0'
    uci set firewall.@defaults[0].flow_offloading_hw='0'
    uci set softflowd.cfg.sampling_rate='1'
    uci commit firewall
    uci commit softflowd
    # (Commented out restart to prevent constant bouncing in dry-run)
    # /etc/init.d/firewall restart
    # /etc/init.d/softflowd restart
fi
