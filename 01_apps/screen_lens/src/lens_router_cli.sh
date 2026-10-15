#!/usr/bin/env bash
# ==============================================================================
# lens_router_cli.sh
# ==============================================================================
# Screen Lens Sovereign — GL.iNet & LuCI Router Management CLI
# Wraps SSH connection to GL.iNet Sovereign Gateway (192.168.8.1)
# Governed by Rule #0 (Zero-Mock Empirical Truth) & Router Skill Invariants.
# ==============================================================================

set -eo pipefail

ROUTER_IP="${ROUTER_IP:-192.168.8.1}"
ROUTER_USER="${ROUTER_USER:-root}"
SSH_TIMEOUT="${SSH_TIMEOUT:-5}"
SSH_OPTS=(-o BatchMode=yes -o "ConnectTimeout=${SSH_TIMEOUT}" -o StrictHostKeyChecking=no)

run_remote() {
    ssh "${SSH_OPTS[@]}" "${ROUTER_USER}@${ROUTER_IP}" "$@"
}

usage() {
    cat << EOF
🌐 Screen Lens Router CLI (GL.iNet BE14000 @ ${ROUTER_IP})

Usage: $(basename "$0") <command> [arguments...]

Commands:
  luci <args...>        Execute LuCI / UCI configuration commands on router
  glinet <args...>      Execute GL.iNet CLI commands (status, wg-status, peers, check-routing, fix-routing)
  status                Display router uptime, memory, swap, and CPU load
  wireguard             Display active WireGuard server status and peer telemetry
  routes                Display kernel routing table and IP policy rules
  subnet-safety         Audit subnet safety (192.168.8.x, timer_migration, swap, blackholes)
  exec <cmd...>         Execute an arbitrary shell command on the router
  help                  Display this help message

Examples:
  $(basename "$0") luci show network.lan
  $(basename "$0") glinet peers
  $(basename "$0") subnet-safety
  $(basename "$0") wireguard
EOF
}

cmd="${1:-help}"
shift || true

case "$cmd" in
    luci)
        if [ $# -eq 0 ]; then
            run_remote "/usr/bin/luci"
        else
            run_remote "/usr/bin/luci" "$@"
        fi
        ;;

    glinet)
        if [ $# -eq 0 ]; then
            run_remote "/usr/bin/glinet"
        else
            run_remote "/usr/bin/glinet" "$@"
        fi
        ;;

    status)
        echo "=== GL.iNet Sovereign Gateway Status ==="
        run_remote "uptime; echo '--- Memory & Swap ---'; free -m; echo '--- Load Average ---'; cat /proc/loadavg"
        ;;

    wireguard)
        echo "=== WireGuard Backbone Telemetry ==="
        run_remote "wg show wgserver; echo '--- UCI WireGuard Server Config ---'; uci show wireguard_server.main_server 2>/dev/null || true"
        ;;

    routes)
        echo "=== Kernel Routing Table & Policy Rules ==="
        run_remote "ip route show; echo '--- IP Policy Rules ---'; ip rule show"
        ;;

    subnet-safety)
        echo "=== Subnet Safety & Stability Audit ==="
        run_remote "
            echo -n '[1/4] MediaTek Timer Migration sysctl: '
            TM=\$(sysctl -n kernel.timer_migration 2>/dev/null || echo 'unknown')
            if [ \"\$TM\" = '0' ]; then
                echo \"PASS (kernel.timer_migration = 0)\"
            else
                echo \"WARN (kernel.timer_migration = \$TM)\"
            fi

            echo -n '[2/4] Swapfile Integrity: '
            if grep -q 'swapfile' /proc/swaps 2>/dev/null; then
                SWAP_SZ=\$(grep 'swapfile' /proc/swaps | awk '{print \$3}')
                echo \"PASS (active swapfile: \${SWAP_SZ} KB)\"
            else
                echo 'FAIL (no active swapfile in /proc/swaps)'
            fi

            echo -n '[3/4] Routing Blackhole Check: '
            if ip rule | grep -q 'wgserver.*blackhole'; then
                echo 'WARN (blackhole rule active on wgserver)'
            else
                echo 'PASS (no blackhole on wgserver)'
            fi

            echo -n '[4/4] Subnet Gateway Verification: '
            LAN_IP=\$(uci -q get network.lan.ipaddr || echo 'unknown')
            if [ \"\$LAN_IP\" = '192.168.8.1' ]; then
                echo \"PASS (LAN Gateway is 192.168.8.1)\"
            else
                echo \"WARN (LAN Gateway is \$LAN_IP)\"
            fi
        "
        ;;

    exec)
        if [ $# -eq 0 ]; then
            echo "Error: No command specified for exec." >&2
            exit 1
        fi
        run_remote "$@"
        ;;

    help|--help|-h)
        usage
        ;;

    *)
        echo "Unknown command: $cmd" >&2
        usage
        exit 1
        ;;
esac
