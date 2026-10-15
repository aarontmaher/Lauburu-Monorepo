#!/usr/bin/env bash
# ==============================================================================
# 🛡️ Ephemeral Docker Sandbox Runner (Tier C - Rule 4 Invariant)
# Runs untrusted code, SWE-bench evals, or model mutations in hermetic isolation.
# Guarantees zero dangling containers, strict RAM/CPU caps, and host protection.
# ==============================================================================

set -euo pipefail

IMAGE="${SANDBOX_IMAGE:-python:3.12-slim}"
MEM_LIMIT="${SANDBOX_MEM:-2g}"
CPU_LIMIT="${SANDBOX_CPUS:-2}"
NETWORK="${SANDBOX_NETWORK:-none}" # Default hermetic: no WAN access
TIMEOUT_SEC="${SANDBOX_TIMEOUT:-120}"

function show_usage() {
    echo "Usage: $0 [options] <command-or-script> [args...]"
    echo ""
    echo "Options:"
    echo "  -i, --image <image>     Docker image (default: python:3.12-slim)"
    echo "  -m, --memory <limit>    Memory cap (default: 2g)"
    echo "  -c, --cpus <count>      CPU cap (default: 2)"
    echo "  -n, --network <mode>    Network mode: none | bridge (default: none)"
    echo "  -v, --volume <src:dst>  Mount host directory into sandbox"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 python3 -c 'import math; print(math.sqrt(1764))'"
    echo "  $0 -n bridge -v \$(pwd):/workspace python3 /workspace/test_script.py"
    exit 0
}

VOLUMES=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        -i|--image)
            IMAGE="$2"
            shift 2
            ;;
        -m|--memory)
            MEM_LIMIT="$2"
            shift 2
            ;;
        -c|--cpus)
            CPU_LIMIT="$2"
            shift 2
            ;;
        -n|--network)
            NETWORK="$2"
            shift 2
            ;;
        -v|--volume)
            VOLUMES+=("-v" "$2")
            shift 2
            ;;
        -h|--help)
            show_usage
            ;;
        *)
            break
            ;;
    esac
done

if [[ $# -eq 0 ]]; then
    show_usage
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Docker CLI not found on host." >&2
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker daemon is not running." >&2
    exit 1
fi

START_TIME=$(date +%s)
echo "🚀 Spawning ephemeral sandbox container ($IMAGE)..."
echo "   Resources: Memory=$MEM_LIMIT, CPUs=$CPU_LIMIT, Network=$NETWORK"

# Execute with --rm, memory limits, and tmpfs scratch space
EXIT_CODE=0
docker run --rm \
    --memory="$MEM_LIMIT" \
    --cpus="$CPU_LIMIT" \
    --network="$NETWORK" \
    --tmpfs /tmp:rw,nosuid,size=512m \
    --pids-limit 100 \
    "${VOLUMES[@]}" \
    "$IMAGE" \
    "$@" || EXIT_CODE=$?

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo "✅ Ephemeral sandbox terminated cleanly in ${ELAPSED}s (Exit Code: $EXIT_CODE)."
exit $EXIT_CODE
