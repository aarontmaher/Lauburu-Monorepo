#!/bin/sh
# ==============================================================================
# Lauburu Mesh - DHCP Presence Oracle Hotplug Hook (R3)
# Subsystem: 00_core_infrastructure/router_foundation
# Target: /etc/hotplug.d/dhcp/10-mesh_dhcp_oracle.sh
#
# Captures dnsmasq lease events (add, del/remove, old/update) directly inside the
# OpenWrt procd hotplug subsystem. Emits structured JSON to the Mac Mini
# Presence Ingester on port 9100 with sub-50ms latency.
# ==============================================================================

# Ensure an IP address is present
[ -n "$IPADDR" ] || exit 0

MAC_MINI_INGEST_IP="192.168.8.230"
MAC_MINI_INGEST_PORT="9100"
LOGGER_TAG="mesh_dhcp_oracle"

# Map dnsmasq hotplug action to standard Lauburu event type
case "$ACTION" in
    add)
        EVENT="LEASE_ADD"
        ;;
    del|remove)
        EVENT="LEASE_DEL"
        ;;
    old|update)
        EVENT="LEASE_UPDATE"
        ;;
    *)
        EVENT="LEASE_${ACTION:-UNKNOWN}"
        ;;
esac

# Sanitize hostname and provide fallback
CLEAN_HOSTNAME="$(echo "${HOSTNAME:-unknown}" | tr -d '\"\\\r\n')"
CLEAN_MAC="$(echo "${MACADDR:-00:00:00:00:00:00}" | tr '[:upper:]' '[:lower:]' | tr -d '\"\\\r\n')"
CLEAN_IP="$(echo "$IPADDR" | tr -d '\"\\\r\n')"
TIMESTAMP="$(date +%s)"

PAYLOAD="{\"timestamp\":$TIMESTAMP,\"event\":\"$EVENT\",\"action\":\"$ACTION\",\"topic\":\"MESH.PRESENCE\",\"source\":\"DHCP\",\"mac\":\"$CLEAN_MAC\",\"ip\":\"$CLEAN_IP\",\"hostname\":\"$CLEAN_HOSTNAME\",\"interface\":\"br-lan\"}"

# Log to syslog for auditability
logger -t "$LOGGER_TAG" "DHCP event $EVENT for IP=$CLEAN_IP MAC=$CLEAN_MAC host=$CLEAN_HOSTNAME"

# Transmit non-blockingly to Mac Mini ingestion port via BusyBox nc with 1s timeout
(
    if [ -x /usr/bin/timeout ]; then
        echo "$PAYLOAD" | timeout 1 nc "$MAC_MINI_INGEST_IP" "$MAC_MINI_INGEST_PORT" >/dev/null 2>&1
    else
        echo "$PAYLOAD" | nc "$MAC_MINI_INGEST_IP" "$MAC_MINI_INGEST_PORT" >/dev/null 2>&1
    fi
) &

exit 0
