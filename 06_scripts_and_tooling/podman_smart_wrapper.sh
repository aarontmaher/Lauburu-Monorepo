#!/usr/bin/env bash
# ==============================================================================
# Lauburu Sovereign Podman Smart Wrapper
# 1. Auto-detects when `podman run <CONTAINER_ID>` is given an existing
#    Container ID (from `podman ps`) instead of an Image ID (`podman images`).
# 2. Ensures SSH local port forwards from mac-air-4 (L5 localhost) to L8/L3
#    are active so http://localhost:8084, :8089, :9223, :8888, :8443, :8889,
#    and :7681 load immediately in Chrome.
# ==============================================================================
set -euo pipefail

REAL_PODMAN="/opt/homebrew/opt/podman/bin/podman-remote"
if [[ ! -x "$REAL_PODMAN" ]]; then
  REAL_PODMAN="/opt/homebrew/bin/podman-remote"
fi

ensure_mesh_port_forwards() {
  if ! lsof -nP -iTCP:8084 -sTCP:LISTEN >/dev/null 2>&1; then
    ssh -f -N \
      -o ConnectTimeout=3 \
      -o ExitOnForwardFailure=no \
      -o ServerAliveInterval=30 \
      -o ServerAliveCountMax=3 \
      -L 8084:127.0.0.1:8084 \
      -L 8089:127.0.0.1:8089 \
      -L 9223:127.0.0.1:9223 \
      -L 8888:127.0.0.1:8888 \
      linuxmini@100.121.247.8 2>/dev/null || true
  fi
  if ! lsof -nP -iTCP:8443 -sTCP:LISTEN >/dev/null 2>&1; then
    ssh -f -N \
      -o ConnectTimeout=3 \
      -o ExitOnForwardFailure=no \
      -o ServerAliveInterval=30 \
      -o ServerAliveCountMax=3 \
      -L 8443:127.0.0.1:8443 \
      -L 8889:127.0.0.1:8889 \
      -L 7681:127.0.0.1:7681 \
      linux@100.101.39.98 2>/dev/null || true
  fi
}

if [[ "${1:-}" == "run" && $# -eq 2 && "${2:-}" != -* ]]; then
  TARGET="$2"
  ensure_mesh_port_forwards
  if ! "$REAL_PODMAN" image exists "$TARGET" 2>/dev/null; then
    if "$REAL_PODMAN" container exists "$TARGET" 2>/dev/null; then
      C_NAME="$("$REAL_PODMAN" inspect "$TARGET" --format '{{.Name}}' 2>/dev/null || echo "$TARGET")"
      C_STATE="$("$REAL_PODMAN" inspect "$TARGET" --format '{{.State.Status}}' 2>/dev/null || echo "unknown")"
      C_IMG="$("$REAL_PODMAN" inspect "$TARGET" --format '{{.ImageName}}' 2>/dev/null || echo "unknown")"
      C_IMG_ID="$("$REAL_PODMAN" inspect "$TARGET" --format '{{slice .Image 0 12}}' 2>/dev/null || echo "unknown")"
      echo "ℹ️  [Lauburu Podman] '$TARGET' is an existing CONTAINER (Name: $C_NAME | Image: $C_IMG [$C_IMG_ID] | Status: $C_STATE)."
      case "$C_NAME" in
        *go-gatt-browser*)
          echo "🌐 Web UI Bridged -> http://localhost:8084  (Direct L8: http://100.121.247.8:8084)"
          ;;
        *serial-rfcomm*)
          echo "🌐 Web UI Bridged -> http://localhost:8089  (Direct L8: http://100.121.247.8:8089)"
          ;;
        *chromium-web-bluetooth*)
          echo "🌐 Web UI Bridged -> http://localhost:9223  (Direct L8: http://100.121.247.8:9223 | CDP: :9222)"
          ;;
      esac
      if [[ "$C_STATE" == "running" ]]; then
        echo "✅ Container '$C_NAME' ($TARGET) is already running. Showing recent logs:"
        echo "--------------------------------------------------------------------------------"
        "$REAL_PODMAN" logs --tail 20 "$TARGET"
        exit 0
      else
        echo "🚀 Starting existing container '$C_NAME' ($TARGET) via 'podman start -a $TARGET'..."
        exec "$REAL_PODMAN" start -a "$TARGET"
      fi
    fi
  fi
fi

exec "$REAL_PODMAN" "$@"
