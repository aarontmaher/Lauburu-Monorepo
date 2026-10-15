#!/bin/sh
# ==============================================================================
# Lauburu Mesh - Out-Of-Band WAN Self-Healer (R4)
# Subsystem: 00_core_infrastructure/router_foundation
# Target: /usr/bin/lauburu_oob_wan_healer.sh
#
# Autonomous 6-state POSIX FSM checking primary NBN health via Layer 3 ICMP
# pings to 1.1.1.1, 8.8.8.8, 9.9.9.9, and executing instant sub-second
# `ip route replace default` failover to backup gateway (cellular / tethering)
# without Mac Mini, mesh overlay, or cloud dependency.
# ==============================================================================

LOGGER_TAG="lauburu_wan_healer"
STATE_FILE="/tmp/wan_healer_state.json"
WWW_STATE_FILE="/www/wan_state.json"
CHECK_INTERVAL=2
FAILOVER_THRESHOLD=3
FAILBACK_THRESHOLD=5
PROBE_TARGETS="1.1.1.1 8.8.8.8 9.9.9.9"

# Initial state variables
CURRENT_STATE="PRIMARY_ONLINE"
FAIL_COUNT=0
SUCCESS_COUNT=0
PRIMARY_DEV=""
PRIMARY_GW=""
BACKUP_DEV=""
BACKUP_GW=""
LAST_PROBE_STATUS="UNKNOWN"

log_info() {
    logger -t "$LOGGER_TAG" "[INFO] $1"
}

log_warn() {
    logger -t "$LOGGER_TAG" "[WARN] $1"
}

log_alert() {
    logger -t "$LOGGER_TAG" "[ALERT] $1"
}

resolve_interfaces() {
    # 1. Resolve Primary WAN interface and gateway
    if [ -x /usr/bin/jsonfilter ] && command -v ubus >/dev/null 2>&1; then
        PRIMARY_DEV="$(ubus call network.interface.wan status 2>/dev/null | jsonfilter -e '@.l3_device' 2>/dev/null)"
        PRIMARY_GW="$(ubus call network.interface.wan status 2>/dev/null | jsonfilter -e '@.route[0].nexthop' 2>/dev/null)"
    fi

    # Fallback to parsing kernel routing table if ubus failed
    if [ -z "$PRIMARY_DEV" ] || [ -z "$PRIMARY_GW" ]; then
        PRIMARY_GW="$(ip route show default 2>/dev/null | grep 'dev eth1' | head -n 1 | awk '{print $3}')"
        PRIMARY_DEV="$(ip route show default 2>/dev/null | grep 'dev eth1' | head -n 1 | awk '{print $5}')"
    fi

    # Defaults for GL-BE14000 NBN WAN if still empty
    PRIMARY_DEV="${PRIMARY_DEV:-eth1.3}"
    PRIMARY_GW="${PRIMARY_GW:-100.90.8.1}"

    # 2. Resolve Backup WAN (tethering usb0, secondwan, or repeater wwan)
    if [ -x /usr/bin/jsonfilter ] && command -v ubus >/dev/null 2>&1; then
        for iface_name in tethering secondwan wwan; do
            b_dev="$(ubus call network.interface.${iface_name} status 2>/dev/null | jsonfilter -e '@.l3_device' 2>/dev/null)"
            b_gw="$(ubus call network.interface.${iface_name} status 2>/dev/null | jsonfilter -e '@.route[0].nexthop' 2>/dev/null)"
            if [ -n "$b_dev" ] && [ -n "$b_gw" ]; then
                BACKUP_DEV="$b_dev"
                BACKUP_GW="$b_gw"
                break
            fi
        done
    fi

    # Fallback to parsing kernel routing table for usb / wwan default route
    if [ -z "$BACKUP_DEV" ] || [ -z "$BACKUP_GW" ]; then
        BACKUP_GW="$(ip route show default 2>/dev/null | grep -E 'dev (usb|apcli|wlan)' | head -n 1 | awk '{print $3}')"
        BACKUP_DEV="$(ip route show default 2>/dev/null | grep -E 'dev (usb|apcli|wlan)' | head -n 1 | awk '{print $5}')"
    fi

    # Sane defaults for GL-BE14000 tethering if still empty
    BACKUP_DEV="${BACKUP_DEV:-usb0}"
    BACKUP_GW="${BACKUP_GW:-10.178.49.221}"
}

probe_wan() {
    dev="$1"
    [ -n "$dev" ] || return 1

    # Multi-target Layer 3 ICMP ping bound strictly to the target interface
    for target in $PROBE_TARGETS; do
        if ping -c 1 -W 1 -I "$dev" "$target" >/dev/null 2>&1; then
            return 0
        fi
    done

    return 1
}

get_active_default_dev() {
    ip route show default 2>/dev/null | head -n 1 | awk '{print $5}'
}

save_state() {
    local now
    now="$(date +%s)"
    local active_dev
    active_dev="$(get_active_default_dev)"

    local json
    json="{\"timestamp\":$now,\"state\":\"$CURRENT_STATE\",\"primary_dev\":\"$PRIMARY_DEV\",\"primary_gw\":\"$PRIMARY_GW\",\"backup_dev\":\"$BACKUP_DEV\",\"backup_gw\":\"$BACKUP_GW\",\"fail_count\":$FAIL_COUNT,\"success_count\":$SUCCESS_COUNT,\"last_probe_status\":\"$LAST_PROBE_STATUS\",\"active_default_dev\":\"$active_dev\"}"

    echo "$json" > "$STATE_FILE" 2>/dev/null || true
    if [ -d /www ]; then
        echo "$json" > "$WWW_STATE_FILE" 2>/dev/null || true
    fi
}

actuate_failover() {
    log_alert "ACTUATING FAILOVER: default route -> $BACKUP_DEV via $BACKUP_GW (metric 10)"
    
    # Sub-millisecond atomic kernel routing table switch
    if [ -n "$BACKUP_GW" ] && [ -n "$BACKUP_DEV" ]; then
        ip route replace default scope global via "$BACKUP_GW" dev "$BACKUP_DEV" metric 10 2>/dev/null || true
    fi

    # Demote primary WAN route metric
    if [ -n "$PRIMARY_GW" ] && [ -n "$PRIMARY_DEV" ]; then
        ip route replace default scope global via "$PRIMARY_GW" dev "$PRIMARY_DEV" metric 100 2>/dev/null || true
    fi

    # Flush kernel route cache
    ip route flush cache 2>/dev/null || true

    # Optional UCI persistence
    if command -v uci >/dev/null 2>&1; then
        uci set network.wan.metric='100' 2>/dev/null || true
        uci set network.tethering.metric='10' 2>/dev/null || true
        uci commit network 2>/dev/null || true
    fi

    log_alert "FAILOVER COMPLETE: traffic migrated to $BACKUP_DEV"
}

actuate_failback() {
    log_alert "ACTUATING FAILBACK: default route -> $PRIMARY_DEV via $PRIMARY_GW (metric 1)"

    # Sub-millisecond atomic kernel routing table switch back to primary
    if [ -n "$PRIMARY_GW" ] && [ -n "$PRIMARY_DEV" ]; then
        ip route replace default scope global via "$PRIMARY_GW" dev "$PRIMARY_DEV" metric 1 2>/dev/null || true
    fi

    # Demote backup WAN route metric
    if [ -n "$BACKUP_GW" ] && [ -n "$BACKUP_DEV" ]; then
        ip route replace default scope global via "$BACKUP_GW" dev "$BACKUP_DEV" metric 2 2>/dev/null || true
    fi

    # Flush kernel route cache
    ip route flush cache 2>/dev/null || true

    # Optional UCI persistence
    if command -v uci >/dev/null 2>&1; then
        uci set network.wan.metric='1' 2>/dev/null || true
        uci set network.tethering.metric='2' 2>/dev/null || true
        uci commit network 2>/dev/null || true
    fi

    log_alert "FAILBACK COMPLETE: traffic restored to primary $PRIMARY_DEV"
}

fsm_step() {
    resolve_interfaces

    case "$CURRENT_STATE" in
        PRIMARY_ONLINE)
            if probe_wan "$PRIMARY_DEV"; then
                FAIL_COUNT=0
                LAST_PROBE_STATUS="OK"
            else
                FAIL_COUNT=$((FAIL_COUNT + 1))
                LAST_PROBE_STATUS="FAILED"
                CURRENT_STATE="PROBING_DEGRADED"
                log_warn "Primary WAN probe failed ($FAIL_COUNT/$FAILOVER_THRESHOLD). State -> PROBING_DEGRADED"
            fi
            ;;

        PROBING_DEGRADED)
            if probe_wan "$PRIMARY_DEV"; then
                FAIL_COUNT=0
                LAST_PROBE_STATUS="OK"
                CURRENT_STATE="PRIMARY_ONLINE"
                log_info "Primary WAN probe recovered. State -> PRIMARY_ONLINE"
            else
                FAIL_COUNT=$((FAIL_COUNT + 1))
                LAST_PROBE_STATUS="FAILED"
                log_warn "Primary WAN probe failed ($FAIL_COUNT/$FAILOVER_THRESHOLD)"
                if [ "$FAIL_COUNT" -ge "$FAILOVER_THRESHOLD" ]; then
                    CURRENT_STATE="FAILOVER_TRIGGERED"
                    log_alert "Failure threshold reached. State -> FAILOVER_TRIGGERED"
                fi
            fi
            ;;

        FAILOVER_TRIGGERED)
            actuate_failover
            SUCCESS_COUNT=0
            CURRENT_STATE="BACKUP_ONLINE"
            log_alert "State -> BACKUP_ONLINE"
            ;;

        BACKUP_ONLINE)
            # Actively route on backup while probing primary in the background
            if probe_wan "$PRIMARY_DEV"; then
                SUCCESS_COUNT=1
                LAST_PROBE_STATUS="PRIMARY_RESPONDING"
                CURRENT_STATE="FAILBACK_PROBING"
                log_info "Primary WAN responded ($SUCCESS_COUNT/$FAILBACK_THRESHOLD). State -> FAILBACK_PROBING"
            else
                SUCCESS_COUNT=0
                LAST_PROBE_STATUS="PRIMARY_DOWN"
            fi
            ;;

        FAILBACK_PROBING)
            if probe_wan "$PRIMARY_DEV"; then
                SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
                LAST_PROBE_STATUS="PRIMARY_STABLE"
                log_info "Primary WAN stable probe ($SUCCESS_COUNT/$FAILBACK_THRESHOLD)"
                if [ "$SUCCESS_COUNT" -ge "$FAILBACK_THRESHOLD" ]; then
                    CURRENT_STATE="FAILBACK_TRIGGERED"
                    log_alert "Primary stability threshold met. State -> FAILBACK_TRIGGERED"
                fi
            else
                SUCCESS_COUNT=0
                LAST_PROBE_STATUS="PRIMARY_FLAPPING"
                CURRENT_STATE="BACKUP_ONLINE"
                log_warn "Primary WAN probe failed during recovery probing. State -> BACKUP_ONLINE"
            fi
            ;;

        FAILBACK_TRIGGERED)
            actuate_failback
            FAIL_COUNT=0
            SUCCESS_COUNT=0
            CURRENT_STATE="PRIMARY_ONLINE"
            log_info "State -> PRIMARY_ONLINE"
            ;;

        *)
            CURRENT_STATE="PRIMARY_ONLINE"
            FAIL_COUNT=0
            SUCCESS_COUNT=0
            ;;
    esac

    save_state
}

run_daemon() {
    log_info "Starting Out-Of-Band WAN Healer FSM daemon (interval=${CHECK_INTERVAL}s)..."
    resolve_interfaces
    save_state

    while true; do
        fsm_step
        sleep "$CHECK_INTERVAL"
    done
}

print_status() {
    resolve_interfaces
    if [ -f "$STATE_FILE" ]; then
        cat "$STATE_FILE"
        echo ""
    else
        save_state
        cat "$STATE_FILE"
        echo ""
    fi
}

cleanup() {
    log_info "Stopping Out-Of-Band WAN Healer daemon..."
    exit 0
}

trap cleanup INT TERM HUP

case "$1" in
    --daemon|"")
        run_daemon
        ;;
    --check-once)
        fsm_step
        print_status
        ;;
    --status)
        print_status
        ;;
    --failover)
        resolve_interfaces
        CURRENT_STATE="FAILOVER_TRIGGERED"
        fsm_step
        print_status
        ;;
    --failback)
        resolve_interfaces
        CURRENT_STATE="FAILBACK_TRIGGERED"
        fsm_step
        print_status
        ;;
    *)
        echo "Usage: $0 [--daemon | --check-once | --status | --failover | --failback]"
        exit 1
        ;;
esac
