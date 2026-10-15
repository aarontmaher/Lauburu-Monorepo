#!/bin/bash
# ==============================================================================
# 🚀 Sovereign Multi-Tab Mesh Monitoring Terminal Launcher
# Targets: MacBook Pro (L2) - Intel Core i7
# Creates a multi-window tmux session with live root & telemetry streams
# ==============================================================================

set -e

SESSION_NAME="mesh-monitor"
TMUX_BIN="/usr/local/bin/tmux"

if [ ! -x "$TMUX_BIN" ]; then
    TMUX_BIN=$(which tmux)
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Initializing Multi-Tab Mesh Monitor on MacBook Pro..."

# Kill existing session if present to apply fresh tab configurations
"$TMUX_BIN" kill-session -t "$SESSION_NAME" 2>/dev/null || true

# 1. Window 0: Live TUI Dashboard
"$TMUX_BIN" new-session -d -s "$SESSION_NAME" -n "Overview" \
    "python3 /Users/aaronmaher/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/monitoring/mesh_unified_dashboard.py"

# Configure sleek tmux status bar
"$TMUX_BIN" set-option -t "$SESSION_NAME" -g status on
"$TMUX_BIN" set-option -t "$SESSION_NAME" -g status-interval 2
"$TMUX_BIN" set-option -t "$SESSION_NAME" -g status-style "bg=#1e1e2e,fg=#cdd6f4"
"$TMUX_BIN" set-option -t "$SESSION_NAME" -g window-status-current-style "bg=#89b4fa,fg=#11111b,bold"
"$TMUX_BIN" set-option -t "$SESSION_NAME" -g status-left "#[fg=#a6e3a1,bold][Lauburu-Mesh] "
"$TMUX_BIN" set-option -t "$SESSION_NAME" -g status-right "#[fg=#f9e2af]%Y-%m-%d %H:%M:%S #[fg=#89dceb]MBP-L2"
"$TMUX_BIN" set-option -t "$SESSION_NAME" -g mouse on

# 2. Window 1: GL.iNet Gateway Router (Root Shell)
"$TMUX_BIN" new-window -t "$SESSION_NAME:1" -n "GW-Router-Root" \
    "ssh -o ConnectTimeout=3 -t root@100.70.123.123 'echo -e \"\033[1;32m[GL.iNet Sovereign Gateway - Root Shell]\033[0m\"; free; cat /proc/loadavg; /bin/ash'"

# 3. Window 2: Linux Mini Compute Hub (Root Shell)
"$TMUX_BIN" new-window -t "$SESSION_NAME:2" -n "Linux-L3-Root" \
    "ssh -o ConnectTimeout=3 -t linux 'echo -e \"\033[1;32m[Linux Mini Hub (L3) - Passwordless Root]\033[0m\"; sudo -i'"

# 4. Window 3: Mac Mini M4 Pro Host
"$TMUX_BIN" new-window -t "$SESSION_NAME:3" -n "MacHost-L1" \
    "ssh -o ConnectTimeout=3 -t macmini 'echo -e \"\033[1;34m[Mac Mini M4 Pro Host (L1) - Sovereign Master]\033[0m\"; sysctl -n vm.loadavg; vm_stat | head -n 6; /bin/zsh'"

# 5. Window 4: MacBook Air M4 (L5)
"$TMUX_BIN" new-window -t "$SESSION_NAME:4" -n "MacBookAir-L5" \
    "ssh -o ConnectTimeout=3 -t macbook 'echo -e \"\033[1;35m[MacBook Air M4 (L5) - Metal Worker]\033[0m\"; sysctl -n vm.loadavg; pmset -g batt | head -n 2; /bin/zsh'"

# 6. Window 5: Pixel 10 Pro XL (Shizuku & Android Telemetry Stream)
"$TMUX_BIN" new-window -t "$SESSION_NAME:5" -n "Pixel-L6-Shizuku" \
    "while true; do clear; echo -e \"\033[1;36m=== Pixel 10 Pro XL Live Shizuku Telemetry ===\033[0m\"; python3 -c \"
import json, urllib.request
try:
    with open('/Users/aaronmaher/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/mesh_telemetry_snapshot.json') as f:
        data = json.load(f)
        pixel = data.get('nodes', {}).get('L6_Pixel_10_Pro', {})
        print(f'Status:    {pixel.get(\\\"status\\\")}')
        print(f'RTT (Ping): {pixel.get(\\\"rtt\\\")}')
        print(f'Metrics:   {pixel.get(\\\"mem\\\")}')
        print(f'Telemetry: {pixel.get(\\\"extra\\\")}')
except Exception as e:
    print(f'Telemetry cache loading: {e}')
\"; echo ''; echo -e \"\033[0;33m[Probing KDE Connect Port 1716 on Pixel 100.114.215.68]...\033[0m\"; nc -zv -G 1 100.114.215.68 1716 2>&1; sleep 4; done"

# 7. Window 6: Continuous Live Inter-Node Latency Matrix
"$TMUX_BIN" new-window -t "$SESSION_NAME:6" -n "Mesh-PingMatrix" \
    "while true; do clear; echo -e \"\033[1;32m=== Lauburu Mesh Inter-Node Round-Trip Latency Matrix ===\033[0m\"; echo -e \"Timestamp: \$(date)\"; echo ''; for target in '100.119.199.76 MacMini-L1' '100.70.123.123 Router-GW' '100.101.39.98 Linux-L3' '100.121.202.34 MacBookAir-L5' '100.114.215.68 Pixel-L6'; do ip=\$(echo \$target | cut -d' ' -f1); name=\$(echo \$target | cut -d' ' -f2); printf '%-16s (%-14s): ' \"\$name\" \"\$ip\"; ping -c 1 -W 800 \$ip 2>&1 | awk -F'/' '/rtt/ {print \$5 \" ms\"} /100% packet loss/ {print \"TIMEOUT\"}'; done; sleep 3; done"

# Select overview tab by default
"$TMUX_BIN" select-window -t "$SESSION_NAME:0"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Multi-Tab Mesh Monitor session '$SESSION_NAME' successfully launched!"
echo "To attach, run on MacBook Pro: $TMUX_BIN attach -t $SESSION_NAME"
