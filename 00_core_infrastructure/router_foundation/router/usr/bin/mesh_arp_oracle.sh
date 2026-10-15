#!/bin/sh
# ==============================================================================
# Lauburu Mesh - ARP Link State Oracle Daemon (R3)
# Subsystem: 00_core_infrastructure/router_foundation
# Target: /usr/bin/mesh_arp_oracle.sh
#
# Monitors Linux kernel rtnetlink neighbor transitions on br-lan via
# `ip monitor neigh dev br-lan` and instantly transmits JSON events to the
# Mac Mini Presence Ingester on port 9100. Delivers sub-2ms presence updates
# without active network scanning or polling overhead.
# ==============================================================================

MAC_MINI_INGEST_IP="192.168.8.230"
MAC_MINI_INGEST_PORT="9100"
DEV_INTERFACE="br-lan"
LOGGER_TAG="mesh_arp_oracle"

cleanup() {
    logger -t "$LOGGER_TAG" "Received termination signal, shutting down..."
    exit 0
}

trap cleanup INT TERM HUP

send_event() {
    payload="$1"
    [ -n "$payload" ] || return 0
    # Sequential feed with 1s timeout, avoiding rapid background forks
    if [ -x /usr/bin/timeout ]; then
        echo "$payload" | timeout 1 nc "$MAC_MINI_INGEST_IP" "$MAC_MINI_INGEST_PORT" >/dev/null 2>&1 || true
    else
        echo "$payload" | nc "$MAC_MINI_INGEST_IP" "$MAC_MINI_INGEST_PORT" >/dev/null 2>&1 || true
    fi
}

build_neigh_json() {
    line="$1"
    [ -n "$line" ] || return 1

    # Parse whitespace-separated tokens
    set -- $line
    [ "$#" -ge 2 ] || return 1

    ip="$1"
    mac="00:00:00:00:00:00"
    state="UNKNOWN"

    shift
    while [ "$#" -gt 0 ]; do
        case "$1" in
            lladdr)
                shift
                if [ -n "$1" ]; then
                    mac="$(echo "$1" | tr '[:upper:]' '[:lower:]')"
                fi
                ;;
            REACHABLE|PERMANENT|FAILED|INCOMPLETE|STALE|DELAY|PROBE|NOARP)
                state="$1"
                ;;
        esac
        shift
    done

    # Map state to high-level Lauburu presence event
    case "$state" in
        REACHABLE|PERMANENT)
            event="NEIGH_UP"
            ;;
        FAILED|INCOMPLETE)
            event="NEIGH_DOWN"
            ;;
        STALE|DELAY|PROBE)
            event="NEIGH_STALE"
            ;;
        *)
            event="NEIGH_${state}"
            ;;
    esac

    timestamp="$(date +%s)"
    printf '{"timestamp":%s,"event":"%s","action":"%s","topic":"MESH.PRESENCE","source":"ARP","mac":"%s","ip":"%s","interface":"%s"}\n' \
        "$timestamp" "$event" "$state" "$mac" "$ip" "$DEV_INTERFACE"
    return 0
}

process_neigh_line() {
    line="$1"
    [ -n "$line" ] || return 0

    json="$(build_neigh_json "$line" || true)"
    [ -n "$json" ] || return 0

    logger -t "$LOGGER_TAG" "Neighbor transition: $json"
    send_event "$json"
}

dump_current_state() {
    logger -t "$LOGGER_TAG" "Dumping current neighbor table on $DEV_INTERFACE (batched NDJSON feed)..."
    batch_payload=""
    batch_count=0

    # Read current neighbor table and accumulate into single batched NDJSON payload
    while read -r line; do
        [ -n "$line" ] || continue
        item_json="$(build_neigh_json "$line" || true)"
        if [ -n "$item_json" ]; then
            batch_payload="${batch_payload}${item_json}"
            batch_count=$((batch_count + 1))
        fi
    done <<EOF
$(ip neigh show dev "$DEV_INTERFACE" 2>/dev/null)
EOF

    if [ "$batch_count" -gt 0 ]; then
        logger -t "$LOGGER_TAG" "Transmitting batched dump of $batch_count neighbor entries to $MAC_MINI_INGEST_IP:$MAC_MINI_INGEST_PORT"
        if [ -x /usr/bin/timeout ]; then
            printf "%s" "$batch_payload" | timeout 2 nc "$MAC_MINI_INGEST_IP" "$MAC_MINI_INGEST_PORT" >/dev/null 2>&1 || true
        else
            printf "%s" "$batch_payload" | nc "$MAC_MINI_INGEST_IP" "$MAC_MINI_INGEST_PORT" >/dev/null 2>&1 || true
        fi
    else
        logger -t "$LOGGER_TAG" "No neighbor entries found on $DEV_INTERFACE during dump."
    fi
}

monitor_loop() {
    logger -t "$LOGGER_TAG" "Starting kernel rtnetlink monitor loop on $DEV_INTERFACE..."
    
    # First sync existing neighbor table using batched feed
    dump_current_state

    # Persistent rtnetlink event loop with restart on failure
    while true; do
        ip monitor neigh dev "$DEV_INTERFACE" | while read -r line; do
            process_neigh_line "$line"
        done

        logger -t "$LOGGER_TAG" "ip monitor exited, restarting in 1s..."
        sleep 1
    done
}

case "$1" in
    --dump-current)
        dump_current_state
        ;;
    --daemon|"")
        monitor_loop
        ;;
    *)
        echo "Usage: $0 [--daemon | --dump-current]"
        exit 1
        ;;
esac
