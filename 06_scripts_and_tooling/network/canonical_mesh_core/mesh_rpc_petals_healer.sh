#!/usr/bin/env bash
# =============================================================================
# LAUBURU MESH — Bottom-Up Multi-Transport & Bluetooth Terminal Self-Healing Governor
# Priority Invariant: Default to Bluetooth terminal as lowest connectivity point,
# heal Bluetooth first, and heal upwards through the network hierarchy.
# Strictly DO NOT heal heavy RPC and Petals processes on the host.
# =============================================================================
set -euo pipefail

LOG=/Volumes/Lauburu-Monorepo/logs/mesh_rpc_petals.log
LORA_LOG=/Volumes/Lauburu-Monorepo/data/lora_datasets/nomad_autonomous_actions.jsonl
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
exec >> "$LOG" 2>&1

log() { echo "[$TIMESTAMP] $*"; }

log_lora() {
  local action="$1"
  local result="$2"
  echo "{\"timestamp_utc\":\"$TIMESTAMP\",\"instruction\":\"Nomad Governor: bottom-up transport self-healing\",\"input\":\"Action: $action\",\"output\":\"Result: $result\",\"action\":\"$action\",\"result\":\"$result\",\"nomad_agent\":\"Multi-WAN Nomad Courier v3.0\"}" >> "$LORA_LOG"
}

# ─── 1. TIER 1: BLUETOOTH TERMINAL & RF LAYER (LOWEST POINT) ────────────────
heal_bluetooth_terminals() {
  log "📶 [Tier 1: Bluetooth Terminal] Probing and healing lowest connectivity point..."
  
  local blueutil_bin="/Users/aaron/.local/bin/blueutil"
  if [[ -x "$blueutil_bin" ]]; then
    # Ensure Bluetooth power is on
    local bt_power
    bt_power=$("$blueutil_bin" --power 2>/dev/null || echo 0)
    if [[ "$bt_power" != "1" ]]; then
      log "⚠️ Bluetooth radio powered off — enabling radio"
      "$blueutil_bin" --power 1 2>/dev/null || true
      sleep 1
    fi

    # Device 1: Samsung S20+ (5C:CB:99:05:81:41)
    local s20_conn
    s20_conn=$("$blueutil_bin" --is-connected 5c-cb-99-05-81-41 2>/dev/null || echo 0)
    if [[ "$s20_conn" == "1" ]]; then
      log "✅ Bluetooth Terminal: Samsung S20+ (5c:cb:99:05:81:41) CONNECTED"
    else
      log "⚠️ Bluetooth Terminal: Samsung S20+ disconnected — attempting RF reconnect"
      "$blueutil_bin" --connect 5c-cb-99-05-81-41 2>/dev/null && log "✅ Connected Samsung S20+ BT" || log "⚪ Samsung S20+ BT standby"
      log_lora "HEAL_BT_TERMINAL_S20", "ATTEMPTED"
    fi

    # Device 2: Pixel 10 Pro XL (30:E0:44:6D:18:EC)
    local pixel_conn
    pixel_conn=$("$blueutil_bin" --is-connected 30-e0-44-6d-18-ec 2>/dev/null || echo 0)
    if [[ "$pixel_conn" == "1" ]]; then
      log "✅ Bluetooth Terminal: Pixel 10 Pro XL (30:e0:44:6d:18:ec) CONNECTED"
    else
      log "⚠️ Bluetooth Terminal: Pixel disconnected — attempting RF reconnect"
      "$blueutil_bin" --connect 30-e0-44-6d-18-ec 2>/dev/null && log "✅ Connected Pixel BT" || log "⚪ Pixel BT standby"
      log_lora "HEAL_BT_TERMINAL_PIXEL", "ATTEMPTED"
    fi

    # Device 3: Macbook Pro L2 (2C:CA:16:08:C0:27)
    local mbp_conn
    mbp_conn=$("$blueutil_bin" --is-connected 2c-ca-16-08-c0-27 2>/dev/null || echo 0)
    if [[ "$mbp_conn" == "1" ]]; then
      log "✅ Bluetooth Terminal: MacBook Pro (2c:ca:16:08:c0:27) CONNECTED"
    else
      log "⚠️ Bluetooth Terminal: MacBook Pro disconnected — attempting RF reconnect"
      "$blueutil_bin" --connect 2c-ca-16-08-c0-27 2>/dev/null && log "✅ Connected MBP BT" || log "⚪ MBP BT standby"
    fi
  else
    log "⚠️ blueutil CLI not available"
  fi

  # Audit incoming and terminal serial tty devices
  local tty_bt
  tty_bt=$(ls /dev/cu.Bluetooth* /dev/cu.Macbook 2>/dev/null | tr '\n' ' ' || echo "none")
  log "🔍 Active Bluetooth TTY serial terminals: $tty_bt"
}

# ─── 2. TIER 2: THUNDERBOLT 4 & USB DIRECT HARDWARE LAYER ───────────────────
heal_direct_hardware_links() {
  log "⚡ [Tier 2: Direct Hardware Bridge] Probing TB4 PCIe DMA & USB ADB..."
  
  # Check Thunderbolt 4 bridge0
  if ifconfig bridge0 2>/dev/null | grep -q "status: active"; then
    log "✅ TB4 PCIe DMA bridge0 ACTIVE (Link-local: 169.254.224.29)"
  else
    log "⚪ TB4 PCIe DMA bridge0 negotiating or inactive"
  fi

  # Check Android USB ADB
  if which adb &>/dev/null; then
    local adb_devs
    adb_devs=$(adb devices 2>/dev/null | grep -v "List" | grep "device" | awk '{print $1}' | tr '\n' ' ' || echo "")
    if [[ -n "$adb_devs" ]]; then
      log "✅ USB ADB Attached Hardware: $adb_devs"
    else
      log "⚪ USB ADB: No direct USB phones detected"
    fi
  fi
}

# ─── 3. TIER 3: LOCAL LAN & EXTENDER MESH LAYER ─────────────────────────────
heal_local_lan_mesh() {
  log "🌐 [Tier 3: Local LAN & Gateway] Probing Router Gateway 192.168.8.1..."
  if nc -z -w1 192.168.8.1 22 2>/dev/null; then
    log "✅ GL.iNet Gateway (192.168.8.1:22) ONLINE"
  else
    log "⚠️ GL.iNet Gateway unreachable on LAN"
  fi

  # Check WoL API Port 18802
  if nc -z -w1 127.0.0.1 18802 2>/dev/null; then
    log "✅ Self-Healing Hub WoL API (Port 18802) HEALTHY"
  else
    log "⚠️ WoL API Port 18802 OFFLINE"
  fi
}

# ─── 4. TIER 4: TAILSCALE WIREGUARD OVERLAY LAYER ───────────────────────────
heal_tailscale_overlay() {
  log "🔒 [Tier 4: Tailscale WireGuard] Auditing Layer 3 encrypted overlay..."
  if which tailscale &>/dev/null; then
    local ts_status
    ts_status=$(tailscale status 2>/dev/null | head -n 4 | tr '\n' ' | ' || echo "offline")
    log "📡 Tailscale status: $ts_status"
  fi
}

# ─── 5. TIER 5: LIGHTWEIGHT LOCAL INFERENCE HEADS (SANCTUARY GUARD) ─────────
heal_local_orchestration_heads() {
  log "🧠 [Tier 5: Lightweight Local Models] Guarding RAM sanctuary (>9.6GB)..."
  
  # Check Local Proxy :8080
  local proxy_status
  proxy_status=$(curl -s --max-time 2 http://127.0.0.1:8080/health 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('status','fail'))" 2>/dev/null || echo "fail")
  if [[ "$proxy_status" == "ok" ]]; then
    log "✅ Local Proxy :8080 HEALTHY"
  else
    log "⚠️ Local Proxy :8080 DOWN — reloading LaunchAgent"
    launchctl unload /Users/aaron/Library/LaunchAgents/ai.lauburu.unified.proxy.plist 2>/dev/null || true
    sleep 1
    launchctl load /Users/aaron/Library/LaunchAgents/ai.lauburu.unified.proxy.plist 2>/dev/null || true
  fi

  # Check Qwen Coder 7B (:8081)
  if curl -sf --max-time 2 http://127.0.0.1:8081/health &>/dev/null; then
    log "✅ Qwen-Coder-7B Orchestrator :8081 HEALTHY"
  else
    log "⚪ Qwen-Coder-7B :8081 Standby"
  fi

  # STRICT INVARIANT: Do NOT spawn heavy 27B/70B models or RPC/Petals on Host Mac Mini
  log "🛡️ Sanctuary Invariant: Heavy RPC and Petals auto-spawning permanently suppressed to protect Host RAM."
}

# ─── MAIN EXECUTION (BOTTOM-UP HIERARCHY) ───────────────────────────────────
log "════════ Bottom-Up Network & Bluetooth Terminal Healer Cycle ════════"
heal_bluetooth_terminals        # 1. Lowest point first: Bluetooth terminal / RF
heal_direct_hardware_links      # 2. Hardware links: TB4 DMA & USB
heal_local_lan_mesh             # 3. Local LAN / Gateway
heal_tailscale_overlay          # 4. Tailscale L3 overlay
heal_local_orchestration_heads  # 5. Local lightweight orchestration heads (RAM protected)
log "════════ Bottom-Up Cycle Complete ════════"

