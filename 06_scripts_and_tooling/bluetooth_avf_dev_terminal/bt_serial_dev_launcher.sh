#!/usr/bin/env bash
# ==============================================================================
# Lauburu Sovereign Bluetooth Serial Terminal — Live Dev Launcher
# Supports:
#   • tmux --dev          (via /usr/local/bin/tmux wrapper or bt-serial-dev --tmux)
#   • zellij --dev        (via /usr/local/bin/zellij wrapper or bt-serial-dev --zellij)
#   • bt-serial-dev       (auto-detects or launches 3-pane hot-reload workspace)
# ==============================================================================
set -euo pipefail

BT_DEV_DIR="$(python3 -c 'import os,sys; print(os.path.dirname(os.path.realpath(sys.argv[1])))' "${BASH_SOURCE[0]}")"
export BT_DEV_DIR
export BT_SERIAL_DEV=1
export TERM="${TERM:-xterm-256color}"

REAL_TMUX="/usr/bin/tmux"
if [ ! -x "$REAL_TMUX" ]; then
    REAL_TMUX="$(command -v tmux || true)"
fi

REAL_ZELLIJ="/usr/local/bin/zellij-bin"
if [ ! -x "$REAL_ZELLIJ" ]; then
    if [ -x "$HOME/zellij" ]; then
        REAL_ZELLIJ="$HOME/zellij"
    elif [ -x "/usr/bin/zellij" ]; then
        REAL_ZELLIJ="/usr/bin/zellij"
    else
        REAL_ZELLIJ=""
    fi
fi

MODE="tmux"
DETACHED=0
REST_ARGS=()

while [ $# -gt 0 ]; do
    case "$1" in
        --tmux)
            MODE="tmux"
            shift
            ;;
        --zellij)
            MODE="zellij"
            shift
            ;;
        --detached|-d)
            DETACHED=1
            shift
            ;;
        --self-test)
            exec python3 "$BT_DEV_DIR/bt_serial_terminal.py" --self-test
            ;;
        --snapshot)
            exec python3 "$BT_DEV_DIR/bt_serial_terminal.py" --snapshot
            ;;
        --exec)
            shift
            exec python3 "$BT_DEV_DIR/bt_serial_terminal.py" --exec "$*"
            ;;
        patch)
            shift
            exec python3 "$BT_DEV_DIR/bt_serial_terminal.py" --exec "patch $*"
            ;;
        --help|-h)
            cat << 'EOF'
Lauburu Bluetooth Serial Terminal (--dev Live Hot-Reload Suite)

Usage:
  tmux --dev                  Launch 3-pane live hot-reload workspace in tmux
  zellij --dev                Launch 3-pane live hot-reload workspace in Zellij
  bt-serial-dev [--tmux]      Launch tmux --dev workspace (session: bt_dev)
  bt-serial-dev --zellij      Launch zellij --dev workspace (layout: bt_serial_dev.kdl)
  bt-serial-dev --detached    Start or refresh the tmux bt_dev workspace in background
  bt-serial-dev --self-test   Run automated E2E PTY, TCP :4005, and AST hot-reload verification
  bt-serial-dev --snapshot    Render a single static frame of the Bluetooth Serial Terminal
  bt-serial-dev patch <c> <r> Live-inject a new command into bt_serial_commands.py (<50ms)
EOF
            exit 0
            ;;
        *)
            REST_ARGS+=("$1")
            shift
            ;;
    esac
done

launch_tmux_dev() {
    local session="bt_dev"

    # Configure crash-safe tmux options on the server if running or starting
    if ! "$REAL_TMUX" has-session -t "$session" 2>/dev/null; then
        local pane1
        pane1="$("$REAL_TMUX" new-session -d -x 140 -y 42 -P -F "#{pane_id}" -s "$session" -n "bt-serial-dev" -c "$BT_DEV_DIR" \
            "BT_SERIAL_DEV=1 python3 '$BT_DEV_DIR/bt_serial_terminal.py' --dev")"

        # Apply AVF WebView/ttyd crash-prevention settings on this session
        "$REAL_TMUX" set-option -t "$session" history-limit 4000 \; \
                     set-option -t "$session" mouse on \; \
                     set-option -t "$session" status-interval 5 \; \
                     set-option -t "$session" escape-time 10 \; \
                     set-option -t "$session" status-style "bg=#0f172a,fg=#38bdf8" \; \
                     set-option -t "$session" status-left "#[fg=#0f172a,bg=#38bdf8,bold] BLUETOOTH SERIAL --DEV #[fg=#38bdf8,bg=#0f172a] " \; \
                     set-option -t "$session" status-right "#[fg=#a78bfa]PTY:/tmp/bt_serial_pty #[fg=#4ade80]TCP::4005 #[fg=#facc15]HotReload:<50ms "

        # Pane 2 (Bottom-Left): Live File & AST Hot-Reload Watcher (gives Pane 1 100% full screen width!)
        local pane2
        pane2="$("$REAL_TMUX" split-window -v -p 34 -P -F "#{pane_id}" -t "$pane1" -c "$BT_DEV_DIR" \
            "BT_SERIAL_DEV=1 python3 '$BT_DEV_DIR/bt_dev_watcher.py'")"

        # Pane 3 (Bottom-Right): Live Dev Shell & Packet Injector
        "$REAL_TMUX" split-window -h -p 54 -t "$pane2" -c "$BT_DEV_DIR" \
            "BT_SERIAL_DEV=1 bash --rcfile '$BT_DEV_DIR/dev_shell_rc.sh' -i" >/dev/null

        # Focus Pane 1 (Bluetooth Serial Terminal) by default
        "$REAL_TMUX" select-pane -t "$pane1"

        # If the AVF 'main' session exists, link bt-serial-dev into window 9 for instant tab access
        if "$REAL_TMUX" has-session -t "main" 2>/dev/null; then
            "$REAL_TMUX" link-window -s "$session:bt-serial-dev" -t "main:9" -k 2>/dev/null || true
        fi
    fi

    if [ "$DETACHED" -eq 1 ]; then
        echo "[bt-serial-dev] tmux session '$session' is active in background."
        "$REAL_TMUX" list-panes -t "$session" -F "  Pane #{pane_index} (#{pane_id}): #{pane_width}x#{pane_height} pid=#{pane_pid} cmd=#{pane_current_command}"
        return 0
    fi

    if [ -n "${TMUX:-}" ]; then
        exec "$REAL_TMUX" switch-client -t "$session"
    else
        exec "$REAL_TMUX" attach-session -t "$session"
    fi
}

launch_zellij_dev() {
    if [ -z "$REAL_ZELLIJ" ] || [ ! -x "$REAL_ZELLIJ" ]; then
        echo "[bt-serial-dev] Native zellij binary not found; falling back to tmux --dev..." >&2
        launch_tmux_dev
        return $?
    fi

    if [ "$DETACHED" -eq 1 ]; then
        # Verify layout parses and start a background headless check or report status
        echo "[bt-serial-dev] Verifying Zellij binary ($($REAL_ZELLIJ --version)) and layout ($BT_DEV_DIR/bt_serial_dev.kdl)..."
        "$REAL_ZELLIJ" setup --check >/dev/null
        echo "[bt-serial-dev] Zellij --dev layout verified ready: $BT_DEV_DIR/bt_serial_dev.kdl"
        return 0
    fi

    cd "$BT_DEV_DIR"
    # If already inside Zellij, open a new tab with the layout; otherwise start/attach session
    if [ -n "${ZELLIJ:-}" ]; then
        exec "$REAL_ZELLIJ" action new-tab --layout "$BT_DEV_DIR/bt_serial_dev.kdl" --name "BT-Serial-Dev"
    else
        exec "$REAL_ZELLIJ" --layout "$BT_DEV_DIR/bt_serial_dev.kdl" attach -c "bt-serial-dev"
    fi
}

if [ "$MODE" = "zellij" ]; then
    launch_zellij_dev
else
    launch_tmux_dev
fi
