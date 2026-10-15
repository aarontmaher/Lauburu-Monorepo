#!/usr/bin/env bash
# ==============================================================================
# LAUBURU MESH - SAMSUNG S20 SHIZUKU & ROUTER USB BOOTSTRAPPER
# Subsystem: 06_scripts_and_tooling/network_self_healing
# Target: GL.iNet Router (192.168.8.1) -> Samsung S20 (SM-G986B)
#         Also wakes Pixel 10 Pro XL via Router USB ADB
# ==============================================================================
set -euo pipefail

ROUTER_IP="${ROUTER_IP:-192.168.8.1}"
S20_ADB="${S20_ADB:-192.168.8.131:5555}"
PIXEL_USB_SERIAL="5B080DLCQ001LQ"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[⚠]${NC} $*"; }
fail()  { echo -e "${RED}[✗]${NC} $*"; }

echo "================================================================"
echo "  LAUBURU MESH — S20 SHIZUKU & ROUTER BOOTSTRAPPER"
echo "  $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "================================================================"

# ==============================================================================
# PHASE 1: S20 ADB CONNECTIVITY
# ==============================================================================
echo ""
echo "=== Phase 1: S20 ADB Connectivity ==="

# Try Wi-Fi ADB first
if adb -s "$S20_ADB" shell "echo OK" 2>/dev/null | grep -q OK; then
    info "S20 reachable via Wi-Fi ADB ($S20_ADB)"
else
    # Try connecting
    adb connect "$S20_ADB" 2>/dev/null || true
    sleep 1
    if adb -s "$S20_ADB" shell "echo OK" 2>/dev/null | grep -q OK; then
        info "S20 connected via Wi-Fi ADB ($S20_ADB)"
    else
        fail "Cannot reach S20 at $S20_ADB"
        echo "Trying via Router USB ADB..."
        ssh -o ConnectTimeout=3 root@"$ROUTER_IP" "adb devices -l" 2>&1
        exit 1
    fi
fi

# ==============================================================================
# PHASE 2: SHIZUKU BOOTSTRAP
# ==============================================================================
echo ""
echo "=== Phase 2: Shizuku Bootstrap ==="

# Enable wireless debugging
adb -s "$S20_ADB" shell "settings put global adb_wifi_enabled 1" 2>/dev/null
info "Wireless debugging enabled"

# Start Shizuku server
echo "Starting Shizuku server..."
adb -s "$S20_ADB" shell "sh /sdcard/Android/data/moe.shizuku.privileged.api/files/start.sh" 2>&1 | tail -3
sleep 2

# Verify rish
RISH_UID=$(adb -s "$S20_ADB" shell "export RISH_DEX=/data/local/tmp/rish_shizuku.dex; sh /data/local/tmp/rish -c 'id -u'" 2>/dev/null | tr -d '[:space:]')
if [ "$RISH_UID" = "2000" ]; then
    info "rish verified: UID 2000 (shell)"
else
    warn "rish UID mismatch: got '$RISH_UID'"
fi

# ==============================================================================
# PHASE 3: ANTI-DOZE & KEEPALIVE
# ==============================================================================
echo ""
echo "=== Phase 3: Anti-Doze & Keepalive ==="

adb -s "$S20_ADB" shell "dumpsys deviceidle whitelist +com.termux" 2>/dev/null | tail -1
adb -s "$S20_ADB" shell "dumpsys deviceidle whitelist +com.termux.boot" 2>/dev/null | tail -1
adb -s "$S20_ADB" shell "dumpsys deviceidle whitelist +com.tailscale.ipn" 2>/dev/null | tail -1
adb -s "$S20_ADB" shell "dumpsys deviceidle whitelist +moe.shizuku.privileged.api" 2>/dev/null | tail -1
adb -s "$S20_ADB" shell "dumpsys deviceidle whitelist +com.android.shell" 2>/dev/null | tail -1
adb -s "$S20_ADB" shell "settings put global settings_enable_monitor_phantom_procs false" 2>/dev/null
adb -s "$S20_ADB" shell "cmd appops set com.termux RUN_IN_BACKGROUND allow" 2>/dev/null
info "Anti-Doze whitelist and Phantom Process Killer disabled"

# ==============================================================================
# PHASE 4: S20 BATTERY TELEMETRY
# ==============================================================================
echo ""
echo "=== Phase 4: S20 Battery Telemetry ==="

adb -s "$S20_ADB" shell "dumpsys battery" 2>/dev/null | grep -iE 'level|temperature|USB powered|status|plugged'

# ==============================================================================
# PHASE 5: S20 NETWORK & WIREGUARD
# ==============================================================================
echo ""
echo "=== Phase 5: S20 Network & WireGuard ==="

adb -s "$S20_ADB" shell "export RISH_DEX=/data/local/tmp/rish_shizuku.dex; sh /data/local/tmp/rish -c '
echo \"WG app: \$(pm path com.wireguard.android >/dev/null 2>&1 && echo INSTALLED || echo MISSING)\"
echo \"Tailscale: \$(pm path com.tailscale.ipn >/dev/null 2>&1 && echo INSTALLED || echo MISSING)\"
echo \"WG tunnel: \$(ip addr show | grep -q 10.1.0 && echo ACTIVE || echo INACTIVE)\"
echo \"Tailscale tun: \$(ip addr show tun1 2>/dev/null | grep -q 100. && echo ACTIVE || echo INACTIVE)\"
echo \"Router ping: \$(ping -c 1 -W 2 192.168.8.1 >/dev/null 2>&1 && echo OK || echo FAIL)\"
echo \"WG subnet: \$(ping -c 1 -W 2 10.1.0.1 >/dev/null 2>&1 && echo OK || echo FAIL)\"
'" 2>&1

# ==============================================================================
# PHASE 6: PIXEL 10 WAKE (VIA ROUTER USB)
# ==============================================================================
echo ""
echo "=== Phase 6: Pixel 10 Pro XL Wake (Router USB ADB) ==="

ssh -o ConnectTimeout=3 root@"$ROUTER_IP" "
adb -s $PIXEL_USB_SERIAL shell input keyevent KEYCODE_WAKEUP 2>/dev/null
echo \"Pixel battery: \$(adb -s $PIXEL_USB_SERIAL shell dumpsys battery 2>/dev/null | grep level | tr -d ' ')\"
echo \"Pixel WG: \$(adb -s $PIXEL_USB_SERIAL shell ip addr show 2>/dev/null | grep -q '10.1.0' && echo ACTIVE || echo INACTIVE)\"
" 2>&1

# ==============================================================================
# PHASE 7: ROUTER HEALTH QUICK CHECK
# ==============================================================================
echo ""
echo "=== Phase 7: Router Quick Health ==="

ssh -o ConnectTimeout=3 root@"$ROUTER_IP" "
echo \"Uptime: \$(uptime | sed 's/.*up /up /' | sed 's/,.*//')\"
echo \"RAM: \$(free -m | awk '/Mem:/{printf \"%dMB/%dMB (%.0f%%)\", \$3, \$2, \$3/\$2*100}')\"
echo \"SWAP: \$(cat /proc/swaps | tail -1 | awk '{print \$1, \$3/1024\"MB used\"}')\"
echo \"Timer migration: \$(sysctl -n kernel.timer_migration 2>/dev/null)\"
echo \"WG peers: \$(wg show wgserver 2>/dev/null | grep -c 'peer:') in kernel\"
echo \"Conntrack: \$(conntrack -L 2>/dev/null | wc -l) entries\"
" 2>&1

echo ""
echo "================================================================"
echo "  BOOTSTRAP COMPLETE!"
echo "================================================================"
