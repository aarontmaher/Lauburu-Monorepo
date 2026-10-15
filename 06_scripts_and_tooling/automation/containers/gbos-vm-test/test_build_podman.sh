#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== [1/5] Checking gbos-vm source repository ==="
if [ ! -d "gbos-vm" ]; then
    echo "Cloning gbos-vm repository..."
    git clone https://github.com/skylartaylor/gbos-vm.git
fi

echo "=== [2/5] Detecting Podman environment ==="
IS_REMOTE="$(podman info --format '{{.Host.ServiceIsRemote}}' 2>/dev/null || echo "false")"
CONN_URI="$(podman system connection list --format '{{if .Default}}{{.URI}}{{end}}' 2>/dev/null | grep -v '^$' | head -n1 || echo "")"

REMOTE_TARGET=""
REMOTE_WORKSPACE=""
HOST_MOUNT="$SCRIPT_DIR/gbos-vm"

if [ "$IS_REMOTE" = "true" ] && [ -n "$CONN_URI" ]; then
    REMOTE_HOST="$(echo "$CONN_URI" | sed -E 's|^ssh://([^/:]+).*|\1|')"
    HOST_ONLY="$(echo "$CONN_URI" | sed -E 's|^ssh://([^/@]+@)?([^/:]+).*|\2|')"

    if [ "$HOST_ONLY" != "127.0.0.1" ] && [ "$HOST_ONLY" != "localhost" ]; then
        REMOTE_TARGET="$REMOTE_HOST"
        echo "Podman is connected to remote daemon at: $REMOTE_TARGET"
        
        # Query remote home directory
        REMOTE_HOME="$(ssh "$REMOTE_TARGET" "echo \$HOME" 2>/dev/null || echo "/home/linuxmini")"
        REMOTE_WORKSPACE="$REMOTE_HOME/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/containers/gbos-vm-test"
        HOST_MOUNT="$REMOTE_WORKSPACE/gbos-vm"

        echo "Syncing local workspace to remote host ($REMOTE_TARGET:$REMOTE_WORKSPACE)..."
        ssh "$REMOTE_TARGET" "mkdir -p '$REMOTE_WORKSPACE'"
        rsync -avz --exclude="work" "$SCRIPT_DIR/" "$REMOTE_TARGET:$REMOTE_WORKSPACE/"
    else
        echo "Podman is using local Podman Machine VM ($CONN_URI)."
        IS_REMOTE="false"
    fi
else
    echo "Podman is running locally on $(uname -s)."
fi

echo "=== [3/5] Building gbos-vm-builder Podman image ==="
podman build -t gbos-vm-builder .

echo "=== [4/5] Executing guest build inside Podman container ==="
echo "Mounting: $HOST_MOUNT -> /workspace"
podman run --rm -v "$HOST_MOUNT:/workspace:Z" gbos-vm-builder

if [ "$IS_REMOTE" = "true" ] && [ -n "$REMOTE_TARGET" ]; then
    echo "Syncing build artifacts back to local host..."
    mkdir -p "$SCRIPT_DIR/gbos-vm/work"
    rsync -avz "$REMOTE_TARGET:$REMOTE_WORKSPACE/gbos-vm/work/" "$SCRIPT_DIR/gbos-vm/work/"
fi

echo "=== [5/5] Verifying built guest and host artifacts ==="
ARTIFACTS=(
    "gbos-vm/work/guest/mesa-runtime/libEGL_virgl.so"
    "gbos-vm/work/guest/mesa-runtime/libGLESv2_virgl.so"
    "gbos-vm/work/guest/libvulkan_virtio.so"
    "gbos-vm/work/guest/vm-input.jar"
    "gbos-vm/work/guest/guest-vulkan-probe"
    "gbos-vm/work/tools/guest_graphics_memfd_policy"
)

MISSING=0
for art in "${ARTIFACTS[@]}"; do
    if [ -s "$SCRIPT_DIR/$art" ]; then
        SIZE="$(du -h "$SCRIPT_DIR/$art" | cut -f1)"
        echo "  [PASS] $art ($SIZE)"
    else
        echo "  [FAIL] Missing or empty: $art"
        MISSING=$((MISSING + 1))
    fi
done

if [ "$MISSING" -eq 0 ]; then
    echo "=========================================================="
    echo "SUCCESS: All gbos-vm guest artifacts built and verified!"
    echo "=========================================================="
    exit 0
else
    echo "ERROR: $MISSING required artifact(s) failed to build." >&2
    exit 1
fi
