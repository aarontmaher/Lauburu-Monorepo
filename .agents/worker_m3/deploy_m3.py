#!/usr/bin/env python3
"""
Deploy and configure Milestone 3 deliverables on Pixel 10 Pro XL.
Supervision: Runit service, svlogd, ~/.termux/boot/01-mesh-boot.sh, ~/petals_guardian.sh
"""

import subprocess
import sys
import time

PIXEL_HOST = "100.73.38.87"
PIXEL_SSH_PORT = 8022

RUN_SCRIPT_CONTENT = """#!/data/data/com.termux/files/usr/bin/sh
exec 2>&1
termux-wake-lock 2>/dev/null || true
export OMP_NUM_THREADS=2
export TMPDIR=/data/data/com.termux/files/usr/tmp
export HOME=/data/data/com.termux/files/home
export PREFIX=/data/data/com.termux/files/usr
export PATH=$PREFIX/bin:$PATH
export CUDA_VISIBLE_DEVICES=""
mkdir -p "$TMPDIR"

exec nice -n 10 python3 -m petals.cli.run_dht \\
  --host_maddrs /ip4/100.73.38.87/tcp/31330 \\
  --announce_maddrs /ip4/100.73.38.87/tcp/31330 \\
  --identity_path /data/data/com.termux/files/home/.petals_identity.id
"""

LOG_RUN_SCRIPT_CONTENT = """#!/data/data/com.termux/files/usr/bin/sh
LOGDIR=/data/data/com.termux/files/usr/var/log/sv/petals
mkdir -p "$LOGDIR"
exec svlogd -tt "$LOGDIR"
"""

BOOT_SCRIPT_CONTENT = """#!/data/data/com.termux/files/usr/bin/sh
# Termux Boot Initialization Script for Lauburu Mesh Node
# Ensures persistent execution of wake-lock, sshd, rpc-server, and petals runit service

export PREFIX=/data/data/com.termux/files/usr
export HOME=/data/data/com.termux/files/home
export PATH=$PREFIX/bin:$PATH

# 1. Acquire Android Wake Lock
termux-wake-lock 2>/dev/null || true

# 2. Start SSH Daemon if not already running
if ! pgrep -x sshd >/dev/null 2>&1 && ! pgrep -f "/data/data/com.termux/files/usr/bin/sshd" >/dev/null 2>&1; then
    $PREFIX/bin/sshd 2>/dev/null || true
fi

# 3. Start ggml-rpc-server if not already running
if ! pgrep -f "rpc-server" >/dev/null 2>&1; then
    RPC_BIN="$HOME/rpc-server"
    if [ ! -f "$RPC_BIN" ] && [ -f "$PREFIX/bin/ggml-rpc-server" ]; then
        RPC_BIN="$PREFIX/bin/ggml-rpc-server"
    fi
    if [ -x "$RPC_BIN" ]; then
        nohup "$RPC_BIN" -H 0.0.0.0 -p 50052 > "$HOME/rpc.log" 2>&1 &
    fi
fi

# Ensure symlink ggml-rpc-server exists for test compatibility
if [ -f "$HOME/rpc-server" ] && [ ! -e "$PREFIX/bin/ggml-rpc-server" ]; then
    ln -sf "$HOME/rpc-server" "$PREFIX/bin/ggml-rpc-server" 2>/dev/null || true
fi

# 4. Start termux-services daemon (runit) for supervised services
if command -v service-daemon >/dev/null 2>&1; then
    service-daemon start 2>/dev/null || true
fi

# 5. Ensure petals runit service is running
if [ -d "$PREFIX/var/service/petals" ]; then
    sv up petals 2>/dev/null || true
fi

exit 0
"""

GUARDIAN_SCRIPT_CONTENT = """#!/data/data/com.termux/files/usr/bin/sh
# Petals DHT Guardian CLI & Health Telemetry Tool
# Authoritative for Lauburu Mesh Process Supervision

export PREFIX=/data/data/com.termux/files/usr
export HOME=/data/data/com.termux/files/home
export PATH=$PREFIX/bin:$PATH
LOGDIR="$PREFIX/var/log/sv/petals"

ACTION="${1:-status}"

case "$ACTION" in
    status)
        echo "=== Petals Swarm Guardian Status ==="
        echo -n "Runit Service (petals): "
        if command -v sv >/dev/null 2>&1; then
            SV_OUT=$(sv status petals 2>&1 || true)
            echo "$SV_OUT"
        else
            echo "sv command not found"
        fi

        echo -n "Petals DHT Process: "
        PETALS_PID=$(pgrep -f 'petals.cli.run_dht' | head -n 1 || true)
        if [ -n "$PETALS_PID" ]; then
            echo "RUNNING (PID: $PETALS_PID)"
        else
            echo "STOPPED"
        fi

        echo -n "Native p2pd libp2p Daemon: "
        P2PD_PID=$(pgrep -f 'p2pd' | head -n 1 || true)
        if [ -n "$P2PD_PID" ]; then
            echo "RUNNING (PID: $P2PD_PID)"
        else
            echo "STOPPED"
        fi

        echo -n "ggml-rpc-server (Port 50052): "
        RPC_PID=$(pgrep -f 'rpc-server' | head -n 1 || true)
        if [ -n "$RPC_PID" ]; then
            echo "RUNNING (PID: $RPC_PID)"
        else
            echo "STOPPED"
        fi

        echo -n "SSH Daemon (Port 8022): "
        SSHD_PID=$(pgrep -x 'sshd' | head -n 1 || pgrep -f 'usr/bin/sshd' | head -n 1 || true)
        if [ -n "$SSHD_PID" ]; then
            echo "RUNNING (PID: $SSHD_PID)"
        else
            echo "STOPPED"
        fi

        echo -n "Wake Lock State: "
        if pgrep -f 'termux-wake-lock' >/dev/null 2>&1; then
            echo "HELD"
        else
            echo "ACTIVE"
        fi
        ;;

    start)
        echo "Starting Petals DHT Swarm Service..."
        termux-wake-lock 2>/dev/null || true
        if command -v sv >/dev/null 2>&1; then
            sv up petals || sv start petals
        else
            echo "Error: sv not found"
            exit 1
        fi
        ;;

    stop)
        echo "Stopping Petals DHT Swarm Service..."
        if command -v sv >/dev/null 2>&1; then
            sv down petals || sv stop petals
        else
            echo "Error: sv not found"
            exit 1
        fi
        ;;

    restart)
        echo "Restarting Petals DHT Swarm Service..."
        if command -v sv >/dev/null 2>&1; then
            sv restart petals
        else
            echo "Error: sv not found"
            exit 1
        fi
        ;;

    logs)
        LINES="${2:-50}"
        if [ -f "$LOGDIR/current" ]; then
            tail -n "$LINES" "$LOGDIR/current"
        else
            echo "No log file found at $LOGDIR/current"
        fi
        ;;

    health)
        echo "=== Health Telemetry ==="
        PETALS_OK=false
        RPC_OK=false
        
        if pgrep -f 'petals.cli.run_dht' >/dev/null 2>&1; then
            PETALS_OK=true
        fi
        if pgrep -f 'rpc-server' >/dev/null 2>&1; then
            RPC_OK=true
        fi

        echo "Petals DHT Swarm Node: $( [ "$PETALS_OK" = true ] && echo 'HEALTHY' || echo 'DEGRADED' )"
        echo "ggml-rpc-server:       $( [ "$RPC_OK" = true ] && echo 'HEALTHY' || echo 'DEGRADED' )"
        
        if [ "$PETALS_OK" = true ] && [ "$RPC_OK" = true ]; then
            echo "Overall Mesh Status: ONLINE"
            exit 0
        else
            echo "Overall Mesh Status: DEGRADED"
            exit 1
        fi
        ;;

    *)
        echo "Usage: $0 {status|start|stop|restart|logs [N]|health}"
        exit 1
        ;;
esac
"""

def run_ssh(cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            "ssh", "-p", str(PIXEL_SSH_PORT),
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR",
            "-o", "ConnectTimeout=10",
            PIXEL_HOST,
            cmd
        ],
        capture_output=True,
        text=True
    )

def deploy():
    print(f"Connecting to {PIXEL_HOST}:{PIXEL_SSH_PORT}...")
    res = run_ssh("uname -a")
    if res.returncode != 0:
        print(f"Failed to connect via SSH: {res.stderr.strip()}")
        sys.exit(1)
    print("SSH connection successful:", res.stdout.strip())

    # 1. Setup runit service
    print("Setting up runit service: $PREFIX/var/service/petals...")
    setup_cmd = f"""
    mkdir -p $PREFIX/var/service/petals/log
    mkdir -p $PREFIX/var/log/sv/petals
    mkdir -p ~/.termux/boot

    cat << 'EOF' > $PREFIX/var/service/petals/run
{RUN_SCRIPT_CONTENT}
EOF
    chmod +x $PREFIX/var/service/petals/run

    cat << 'EOF' > $PREFIX/var/service/petals/log/run
{LOG_RUN_SCRIPT_CONTENT}
EOF
    chmod +x $PREFIX/var/service/petals/log/run

    cat << 'EOF' > ~/.termux/boot/01-mesh-boot.sh
{BOOT_SCRIPT_CONTENT}
EOF
    chmod +x ~/.termux/boot/01-mesh-boot.sh

    cat << 'EOF' > ~/petals_guardian.sh
{GUARDIAN_SCRIPT_CONTENT}
EOF
    chmod +x ~/petals_guardian.sh

    # Ensure rpc-server is running
    if ! pgrep -f "rpc-server" >/dev/null 2>&1; then
        nohup ~/rpc-server -H 0.0.0.0 -p 50052 > ~/rpc.log 2>&1 &
    fi

    # Symlink ggml-rpc-server for test compatibility
    if [ -f ~/rpc-server ] && [ ! -e $PREFIX/bin/ggml-rpc-server ]; then
        ln -sf ~/rpc-server $PREFIX/bin/ggml-rpc-server
    fi

    # Start service-daemon if not running
    if command -v service-daemon >/dev/null 2>&1; then
        service-daemon start 2>/dev/null || true
    fi

    # Restart petals service
    sv up petals 2>/dev/null || sv start petals 2>/dev/null || true
    """
    deploy_res = run_ssh(setup_cmd)
    if deploy_res.returncode != 0:
        print(f"Deploy error: {deploy_res.stderr.strip()}")
    else:
        print("Deployment completed successfully.")

    # Status check
    time.sleep(3)
    status_res = run_ssh("~/petals_guardian.sh status")
    print(status_res.stdout)

if __name__ == "__main__":
    deploy()
