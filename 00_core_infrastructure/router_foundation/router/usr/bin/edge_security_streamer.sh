#!/bin/sh
# ==============================================================================
# Lauburu Mesh - Edge Security Packet Streamer (R5)
# Subsystem: 00_core_infrastructure/router_foundation
# Target: /usr/bin/edge_security_streamer.sh
#
# Streams targeted link-layer frames (TCP SYN/RST scans, ARP activity, TTL<=1 loops,
# ICMP TTL exceeded) from `br-lan` over TCP:9005 to the Mac Mini Screen Lens
# Security Radar. Bypasses general full-packet capture overhead while exposing
# authentic security anomalies in real-time.
# ==============================================================================

DEV_INTERFACE="${DEV_INTERFACE:-br-lan}"
TCP_PORT="${TCP_PORT:-9005}"
BPF_FILTER="(tcp[tcpflags] & (tcp-syn|tcp-rst) != 0) or arp or (ip[8] <= 1) or (icmp[icmptype] == 11)"
TCPDUMP_BIN="/usr/sbin/tcpdump"
SOCAT_BIN="/usr/bin/socat"
LOGGER_TAG="edge_security_streamer"

check_dependencies() {
    if [ ! -x "$TCPDUMP_BIN" ]; then
        logger -t "$LOGGER_TAG" "ERROR: $TCPDUMP_BIN not found or not executable."
        echo "ERROR: tcpdump is missing at $TCPDUMP_BIN" >&2
        return 1
    fi

    if [ ! -x "$SOCAT_BIN" ]; then
        logger -t "$LOGGER_TAG" "ERROR: $SOCAT_BIN not found or not executable."
        echo "ERROR: socat is missing at $SOCAT_BIN" >&2
        return 1
    fi

    if ! ip link show dev "$DEV_INTERFACE" >/dev/null 2>&1; then
        logger -t "$LOGGER_TAG" "ERROR: interface $DEV_INTERFACE does not exist."
        echo "ERROR: interface $DEV_INTERFACE does not exist" >&2
        return 1
    fi

    return 0
}

cleanup() {
    logger -t "$LOGGER_TAG" "Received termination signal, shutting down streamer on port $TCP_PORT..."
    # Target only socat listener bound to TCP_PORT to protect router_bluetooth_hub on port 9002
    TARGET_PIDS=$(pgrep -f "socat.*$TCP_PORT" 2>/dev/null || true)
    if [ -n "$TARGET_PIDS" ]; then
        kill -TERM $TARGET_PIDS 2>/dev/null || true
        sleep 0.5
        kill -9 $TARGET_PIDS 2>/dev/null || true
    fi
    exit 0
}

trap cleanup INT TERM HUP

stop_streamer() {
    logger -t "$LOGGER_TAG" "Stopping Edge Security Streamer on port $TCP_PORT..."
    TARGET_PIDS=$(pgrep -f "socat.*$TCP_PORT" 2>/dev/null || true)
    if [ -n "$TARGET_PIDS" ]; then
        kill -TERM $TARGET_PIDS 2>/dev/null || true
        sleep 0.5
        kill -9 $TARGET_PIDS 2>/dev/null || true
        echo "Stopped streamer processes: $TARGET_PIDS"
    else
        echo "No streamer process found for port $TCP_PORT."
    fi
}

run_test() {
    echo "Testing targeted BPF capture on $DEV_INTERFACE for 3 seconds..."
    $TCPDUMP_BIN -i "$DEV_INTERFACE" -nn -l -e -tt "$BPF_FILTER" &
    PID=$!
    sleep 3
    kill $PID 2>/dev/null || true
    wait $PID 2>/dev/null || true
    echo "Test completed."
}

run_streamer() {
    check_dependencies || exit 1

    logger -t "$LOGGER_TAG" "Starting Edge Security Streamer on $DEV_INTERFACE -> TCP:$TCP_PORT"
    
    # Launch socat TCP listener executing tcpdump on-demand per client connection
    exec "$SOCAT_BIN" -u \
        EXEC:"$TCPDUMP_BIN -i $DEV_INTERFACE -nn -l -e -tt '$BPF_FILTER'",stderr \
        "TCP-LISTEN:$TCP_PORT,reuseaddr,fork"
}

case "$1" in
    --test)
        run_test
        ;;
    --check)
        if check_dependencies; then
            echo "Dependencies and interface verified OK."
            exit 0
        else
            exit 1
        fi
        ;;
    --stop)
        stop_streamer
        ;;
    --daemon|"")
        run_streamer
        ;;
    *)
        echo "Usage: $0 [--daemon | --test | --check | --stop]"
        exit 1
        ;;
esac
