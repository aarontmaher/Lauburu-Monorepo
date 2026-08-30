#!/usr/bin/env bash
# =============================================================================
# deploy_prima_all_nodes.sh — Full mesh prima.cpp deployment + ring launch
# =============================================================================
set -euo pipefail

SSH_OPTS="-i $HOME/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=12 -o IdentitiesOnly=yes -o ServerAliveInterval=30"
ZMQ_CMD='brew install zeromq highs 2>/dev/null || true'
CLONE_CMD='[ -d ~/prima_cpp/.git ] || git clone --depth=1 https://gitee.com/zonghang-li/prima.cpp.git ~/prima_cpp'
BUILD_MAC_CMD='cd ~/prima_cpp && ZMQ_INC=$(brew --prefix zeromq)/include; ZMQ_LIB=$(brew --prefix zeromq)/lib; HIGHS_INC=$(brew --prefix highs)/include/highs; HIGHS_LIB=$(brew --prefix highs)/lib; CPPFLAGS="-I${ZMQ_INC}" LDFLAGS="-L${ZMQ_LIB} -lzmq -L${HIGHS_LIB} -lhighs" make USE_HIGHS=1 HIGHS_CPPFLAGS="-isystem ${HIGHS_INC}" HIGHS_LDFLAGS="-L${HIGHS_LIB} -lhighs" -j$(sysctl -n hw.logicalcpu) 2>&1 | tail -3 && mkdir -p ~/.local/bin && cp llama-server ~/.local/bin/prima-server && echo PRIMA_BUILT'
BUILD_LINUX_CMD='cd ~/prima_cpp && sudo apt-get install -y libzmq3-dev build-essential -qq 2>/dev/null; make -j$(nproc) 2>&1 | tail -3 && mkdir -p ~/.local/bin && cp llama-server ~/.local/bin/prima-server && echo PRIMA_BUILT'

log() { echo "[$(date '+%H:%M:%S')] $*"; }
do_ssh() { local h="$1" u="$2"; shift 2; ssh $SSH_OPTS "${u}@${h}" "$@" 2>&1; }

log "=== Parallel build across MacBook Pro + MacBook Air + Linux ==="
( do_ssh "100.103.212.21" "aaron" "${ZMQ_CMD}; ${CLONE_CMD}; ${BUILD_MAC_CMD}" && log "✅ MBP done" || log "⚠️  MBP failed" ) &
( do_ssh "100.93.158.96"  "aaron" "${ZMQ_CMD}; ${CLONE_CMD}; ${BUILD_MAC_CMD}" && log "✅ MBA done" || log "⚠️  MBA failed" ) &
( do_ssh "100.101.39.98"  "linux" "[ -f ~/prima_cpp/llama-server ] && mkdir -p ~/.local/bin && cp ~/prima_cpp/llama-server ~/.local/bin/prima-server && echo LINUX_READY || (${BUILD_LINUX_CMD})" && log "✅ Linux done" || log "⚠️  Linux failed" ) &
( do_ssh "100.81.92.125"  "user"  "[ -f /usr/bin/apt-get ] && sudo apt-get install -y libzmq3-dev build-essential -qq 2>/dev/null; ${CLONE_CMD}; ${BUILD_LINUX_CMD}" && log "✅ Tablet done" || log "⚠️  Tablet failed (optional)" ) &
wait && log "All builds complete"
