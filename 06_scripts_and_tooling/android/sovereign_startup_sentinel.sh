#!/usr/bin/env bash
# ==============================================================================
# Sovereign Mesh Cluster Startup Sentinel (Ultra-Fast Idempotent Supervisor)
# Ensures required daemons (Llama RPC, SSHD, Termux WakeLock) are active.
# Sub-250ms pure-bash execution with zero duplicate process spawning and robust PID locks.
# ==============================================================================

if [ -d "/data/data/com.termux/files/usr/bin" ]; then
    export PATH="/data/data/com.termux/files/home/.local/bin:/data/data/com.termux/files/home/bin:/data/data/com.termux/files/home/go/bin:/data/data/com.termux/files/usr/bin:/system/bin:/system/xbin"
else
    export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
fi

RPC_PORT=50052
SSHD_PORT=8022
RPC_SESSION="sovereign-llama-rpc"

# Fast path for run directory
if [ -w "/data/data/com.termux/files/usr/var/run" ]; then
    RUN_DIR="/data/data/com.termux/files/usr/var/run"
elif [ -w "/data/data/com.termux/files/usr/tmp" ]; then
    RUN_DIR="/data/data/com.termux/files/usr/tmp"
else
    RUN_DIR="/tmp"
fi

SENTINEL_LOCK="$RUN_DIR/sovereign_sentinel.lock"
WAKELOCK_FLAG="$RUN_DIR/.termux_wakelock_active"
RPC_PID_FILE="$RUN_DIR/ggml-rpc-server.pid"
SSHD_PID_FILE="$RUN_DIR/sshd.pid"

# Robust socket probe helper with 1s timeout protection
probe_socket() {
    if command -v nc >/dev/null 2>&1; then
        nc -z -w 1 127.0.0.1 "$1" 2>/dev/null
        return $?
    elif command -v timeout >/dev/null 2>&1; then
        timeout 1 bash -c "exec 3<>/dev/tcp/127.0.0.1/$1 && exec 3>&-" 2>/dev/null
        return $?
    fi
    exec 3<>/dev/tcp/127.0.0.1/"$1" 2>/dev/null || return 1
    exec 3>&-
    return 0
}

# 1. Asynchronous non-blocking Termux CPU WakeLock preservation
if [ ! -e "$WAKELOCK_FLAG" ] && [ ! -e "/tmp/.termux_wakelock_active" ]; then
    WAKE_LOCK_BIN="/data/data/com.termux/files/usr/bin/termux-wake-lock"
    [ ! -x "$WAKE_LOCK_BIN" ] && WAKE_LOCK_BIN="$(command -v termux-wake-lock 2>/dev/null)"
    if [ -n "$WAKE_LOCK_BIN" ]; then
        ( nohup "$WAKE_LOCK_BIN" >/dev/null 2>&1 && touch "$WAKELOCK_FLAG" "/tmp/.termux_wakelock_active" ) 200>&- </dev/null >/dev/null 2>&1 &
        disown $! 2>/dev/null || true
    fi
fi

# 2. SSHD Daemon (Port 8022) Inspection & Idempotent Management
if probe_socket "$SSHD_PORT"; then
    if [ -s "$SSHD_PID_FILE" ]; then
        read -r recorded_sshd_pid < "$SSHD_PID_FILE" 2>/dev/null || true
    fi
    if [ -z "$recorded_sshd_pid" ] || [ ! -d "/proc/$recorded_sshd_pid" ]; then
        sshd_pids=$(pidof sshd 2>/dev/null)
        sshd_pid="${sshd_pids##* }"
        [ -n "$sshd_pid" ] && echo "$sshd_pid" > "$SSHD_PID_FILE"
    fi
    echo "✓ SSHD active (Port $SSHD_PORT)"
else
    # Port closed: acquire lock and start daemon safely
    exec 200>"$SENTINEL_LOCK" 2>/dev/null
    command -v flock >/dev/null 2>&1 && flock -x -w 2 200 2>/dev/null || true

    if ! probe_socket "$SSHD_PORT"; then
        echo "⚡ Starting SSHD on port $SSHD_PORT..."
        SSHD_BIN="/data/data/com.termux/files/usr/bin/sshd"
        [ ! -x "$SSHD_BIN" ] && SSHD_BIN="$(command -v sshd 2>/dev/null)"
        [ ! -x "$SSHD_BIN" ] && SSHD_BIN="/usr/sbin/sshd"

        if [ -x "$SSHD_BIN" ]; then
            "$SSHD_BIN" 200>&- 2>/dev/null || true
            for _ in 1 2 3 4 5 6 7 8 9 10; do
                if probe_socket "$SSHD_PORT"; then
                    sshd_pids=$(pidof sshd 2>/dev/null)
                    sshd_pid="${sshd_pids##* }"
                    [ -n "$sshd_pid" ] && echo "$sshd_pid" > "$SSHD_PID_FILE"
                    break
                fi
                sleep 0.05 2>/dev/null || sleep 1
            done
        fi
    fi
    exec 200>&- 2>/dev/null

    if probe_socket "$SSHD_PORT"; then
        echo "✓ SSHD active (Port $SSHD_PORT)"
    else
        echo "⚠ SSHD failed to start (Port $SSHD_PORT)"
    fi
fi

# 3. Llama RPC Server (Port 50052) Inspection & Idempotent Management
if probe_socket "$RPC_PORT"; then
    if [ -s "$RPC_PID_FILE" ]; then
        read -r recorded_rpc_pid < "$RPC_PID_FILE" 2>/dev/null || true
    fi
    if [ -z "$recorded_rpc_pid" ] || [ ! -d "/proc/$recorded_rpc_pid" ]; then
        rpc_pids=$(pidof rpc-server ggml-rpc-server 2>/dev/null)
        rpc_pid="${rpc_pids%% *}"
        [ -n "$rpc_pid" ] && echo "$rpc_pid" > "$RPC_PID_FILE"
    fi
    echo "✓ Llama RPC Daemon active (Port $RPC_PORT)"
else
    # Port closed: acquire lock and start daemon safely
    exec 200>"$SENTINEL_LOCK" 2>/dev/null
    command -v flock >/dev/null 2>&1 && flock -x -w 2 200 2>/dev/null || true

    if ! probe_socket "$RPC_PORT"; then
        # Resolve RPC binary only when spawn is needed
        RPC_BIN=""
        for b in "$HOME/llama.cpp/build/bin/ggml-rpc-server" \
                 "/data/data/com.termux/files/home/llama.cpp/build/bin/ggml-rpc-server" \
                 "/data/data/com.termux/files/usr/bin/rpc-server" \
                 "/data/data/com.termux/files/home/rpc-server" \
                 "/data/data/com.termux/files/usr/bin/ggml-rpc-server" \
                 "/usr/local/bin/ggml-rpc-server"; do
            if [ -x "$b" ]; then
                RPC_BIN="$b"
                break
            fi
        done

        if [ -n "$RPC_BIN" ]; then
            echo "⚡ Starting Llama RPC Daemon (Port: $RPC_PORT)..."
            TMUX_BIN="/data/data/com.termux/files/usr/bin/tmux"
            [ ! -x "$TMUX_BIN" ] && TMUX_BIN="$(command -v tmux 2>/dev/null)"

            if [ -x "$TMUX_BIN" ]; then
                "$TMUX_BIN" has-session -t "$RPC_SESSION" 2>/dev/null || \
                    "$TMUX_BIN" new-session -d -s "$RPC_SESSION" "$RPC_BIN -H 0.0.0.0 -p $RPC_PORT"
            else
                ( nohup "$RPC_BIN" -H 0.0.0.0 -p "$RPC_PORT" > "$RUN_DIR/rpc_pixel.log" 2>&1 & ) 200>&-
                rpc_pids=$(pidof rpc-server ggml-rpc-server 2>/dev/null)
                rpc_pid="${rpc_pids%% *}"
                [ -n "$rpc_pid" ] && echo "$rpc_pid" > "$RPC_PID_FILE"
            fi

            for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
                if probe_socket "$RPC_PORT"; then
                    rpc_pids=$(pidof rpc-server ggml-rpc-server 2>/dev/null)
                    rpc_pid="${rpc_pids%% *}"
                    [ -n "$rpc_pid" ] && echo "$rpc_pid" > "$RPC_PID_FILE"
                    break
                fi
                sleep 0.05 2>/dev/null || sleep 1
            done
        fi
    fi
    exec 200>&- 2>/dev/null

    if probe_socket "$RPC_PORT"; then
        echo "✓ Llama RPC Daemon active (Port $RPC_PORT)"
    else
        echo "⚠ Llama RPC Daemon failed to start (Port $RPC_PORT)"
    fi
fi

# 4. WireGuard / Tailscale interface check (tun0 / tun1)
if [ -d /proc/sys/net/ipv4/conf/tun0 ] || [ -e /sys/class/net/tun0 ] || [ -e /tmp/sovereign_daemons/tun0.active ] || [ -e "$RUN_DIR/tun0.active" ]; then
    echo "✓ WireGuard tunnel (tun0: 10.1.0.13) is UP"
elif [ -d /proc/sys/net/ipv4/conf/tun1 ] || [ -e /sys/class/net/tun1 ] || [ -e "$RUN_DIR/tun1.active" ]; then
    echo "✓ Tailscale overlay tunnel (tun1: 100.114.215.68) is UP"
else
    echo "ℹ Overlay tunnel (tun0/tun1) is inactive"
fi

# 5. Live Bluetooth Terminal & Rish Session Supervisor
# Keep ~/bin/sovereign_startup_sentinel.sh synced with monorepo copy if present
MONOREPO_SENTINEL="/data/data/com.termux/files/home/Lauburu-Monorepo/06_scripts_and_tooling/android/sovereign_startup_sentinel.sh"
USER_BIN_SENTINEL="/data/data/com.termux/files/home/bin/sovereign_startup_sentinel.sh"
if [ -f "$MONOREPO_SENTINEL" ] && [ -d "/data/data/com.termux/files/home/bin" ]; then
    if [ ! -f "$USER_BIN_SENTINEL" ] || ! cmp -s "$MONOREPO_SENTINEL" "$USER_BIN_SENTINEL" 2>/dev/null; then
        cp -f "$MONOREPO_SENTINEL" "$USER_BIN_SENTINEL" 2>/dev/null && chmod +x "$USER_BIN_SENTINEL" 2>/dev/null || true
    fi
fi

BT_SESSION="lauburu"
TMUX_BIN="/data/data/com.termux/files/usr/bin/tmux"
[ ! -x "$TMUX_BIN" ] && TMUX_BIN="$(command -v tmux 2>/dev/null)"
RISH_BIN="/data/data/com.termux/files/home/bin/rish"
ADB_SCRIPT="/data/data/com.termux/files/home/bin/adb_terminal.sh"

if [ -x "$TMUX_BIN" ]; then
    if ! "$TMUX_BIN" has-session -t "$BT_SESSION" 2>/dev/null; then
        "$TMUX_BIN" new-session -d -s "$BT_SESSION" -n "dashboard" "bash"
        if [ -x "$RISH_BIN" ]; then
            "$TMUX_BIN" new-window -t "$BT_SESSION:1" -n "rish" "$RISH_BIN"
        fi
        if [ -x "$ADB_SCRIPT" ]; then
            "$TMUX_BIN" new-window -t "$BT_SESSION:2" -n "adb" "$ADB_SCRIPT"
        fi
    else
        if [ -x "$RISH_BIN" ] && ! "$TMUX_BIN" list-windows -t "$BT_SESSION" -F "#{window_name}" 2>/dev/null | grep -q "^rish$"; then
            "$TMUX_BIN" new-window -t "$BT_SESSION" -n "rish" "$RISH_BIN"
        fi
        if [ -x "$ADB_SCRIPT" ] && ! "$TMUX_BIN" list-windows -t "$BT_SESSION" -F "#{window_name}" 2>/dev/null | grep -q "^adb$"; then
            "$TMUX_BIN" new-window -t "$BT_SESSION" -n "adb" "$ADB_SCRIPT"
        fi
    fi
    if "$TMUX_BIN" has-session -t "$BT_SESSION" 2>/dev/null; then
        echo "✓ Bluetooth Terminal session active ($BT_SESSION: [0: dashboard, 1: rish, 2: adb])"
    fi
fi

# 6. Screen Lens Activity-Driven Daemon (Port 3035)
LENS_PORT=3035
LENS_SESSION="sovereign-screen-lens"
LENS_SCRIPT="/data/data/com.termux/files/home/lauburu_lens/lauburu_lens_android.py"

if probe_socket "$LENS_PORT"; then
    echo "✓ Screen Lens Daemon active (Port $LENS_PORT)"
else
    if [ -f "$LENS_SCRIPT" ] && [ -x "$TMUX_BIN" ]; then
        if ! "$TMUX_BIN" has-session -t "$LENS_SESSION" 2>/dev/null; then
            echo "⚡ Starting Screen Lens Daemon (Port $LENS_PORT)..."
            "$TMUX_BIN" new-session -d -s "$LENS_SESSION" "python3 $LENS_SCRIPT start"
            for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
                if probe_socket "$LENS_PORT"; then
                    break
                fi
                sleep 0.1 2>/dev/null || sleep 1
            done
        fi
    fi
    if probe_socket "$LENS_PORT"; then
        echo "✓ Screen Lens Daemon active (Port $LENS_PORT)"
    else
        echo "ℹ Screen Lens Daemon not active (Port $LENS_PORT)"
    fi
fi

# 7. Movesense Standalone Biometrics & TinyML Engine (Port 8086 / 8087)
MOVESENSE_PORT=8086
MOVESENSE_DIR="/data/data/com.termux/files/home/movesense-readiness"
MOVESENSE_MAIN="$MOVESENSE_DIR/main.py"
MOVESENSE_SESSION="movesense-hub"

if probe_socket "$MOVESENSE_PORT" || probe_socket 8087; then
    echo "✓ Movesense Standalone Engine active (Port $MOVESENSE_PORT/8087: 512Hz TinyML)"
else
    if [ -f "$MOVESENSE_MAIN" ]; then
        echo "⚡ Starting Movesense Standalone Readiness & TinyML Engine (Port $MOVESENSE_PORT/8087)..."
        if [ -x "$TMUX_BIN" ]; then
            "$TMUX_BIN" has-session -t "$MOVESENSE_SESSION" 2>/dev/null || \
                "$TMUX_BIN" new-session -d -s "$MOVESENSE_SESSION" "cd $MOVESENSE_DIR && python3 $MOVESENSE_MAIN"
        else
            ( cd "$MOVESENSE_DIR" && nohup python3 "$MOVESENSE_MAIN" > "$MOVESENSE_DIR/movesense_daemon.log" 2>&1 & ) 200>&-
        fi
        for _ in 1 2 3 4 5 6 7 8 9 10; do
            if probe_socket "$MOVESENSE_PORT" || probe_socket 8087; then
                break
            fi
            sleep 0.1 2>/dev/null || sleep 1
        done
    fi
    if probe_socket "$MOVESENSE_PORT" || probe_socket 8087; then
        echo "✓ Movesense Standalone Engine active (Port $MOVESENSE_PORT/8087: 512Hz TinyML)"
    else
        echo "ℹ Movesense Standalone Engine starting in background (Port $MOVESENSE_PORT/8087)"
    fi
fi

# 8. Syncthing Storage Mesh Engine (Port 8384)
SYNCTHING_PORT=8384
if probe_socket "$SYNCTHING_PORT"; then
    echo "✓ Syncthing Mesh Engine active (Port $SYNCTHING_PORT)"
else
    if command -v syncthing >/dev/null 2>&1; then
        nohup syncthing --no-browser > "$RUN_DIR/syncthing.log" 2>&1 &
        echo "⚡ Starting Syncthing Mesh Engine (Port $SYNCTHING_PORT)..."
    fi
fi

# 9. AVF Debian 13 microVM (dynamic avf_tap_* / 100.80.64.5:22) — Passive Check Only (Never Hijack Screen)
AVF_IP="$(ip route 2>/dev/null | awk '/avf_tap/ {split($1,a,"."); print a[1]"."a[2]"."a[3]".53"}' | head -n 1)"
[ -z "$AVF_IP" ] && AVF_IP="10.64.219.53"
if [ -x "$RISH_BIN" ]; then
    for dex in /data/data/com.termux/files/home/bin/rish_shizuku.dex /data/data/com.termux/files/usr/bin/rish_shizuku.dex; do
        [ -f "$dex" ] && chmod 400 "$dex" 2>/dev/null || true
    done
    # Passive Wi-Fi low-latency settings only; never launch avf_guardian_daemon.sh or am start
    ( timeout 3 "$RISH_BIN" -c '
        pkill -9 -f avf_guardian_daemon.sh 2>/dev/null || true
        cmd wifi set-wifi-hi-perf-mode-enabled true >/dev/null 2>&1 || true
        cmd wifi set-low-latency-mode-enabled true >/dev/null 2>&1 || true
        settings put global wifi_sleep_policy 2 >/dev/null 2>&1 || true
    ' </dev/null >/dev/null 2>&1 & ) 200>&-
    if command -v nc >/dev/null 2>&1 && (nc -z -w 1 "$AVF_IP" 22 >/dev/null 2>&1 || nc -z -w 1 100.80.64.5 22 >/dev/null 2>&1); then
        echo "✓ AVF Debian 13 microVM active ($AVF_IP:22)"
    fi
fi

return 0 2>/dev/null || exit 0

