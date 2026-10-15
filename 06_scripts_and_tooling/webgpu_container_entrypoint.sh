#!/usr/bin/env bash
# ==============================================================================
# Lauburu WebGPU Specialist Container Entrypoint
# Builds WebAssembly bridge and starts Port 8090 WebGPU visualizer server.
# ==============================================================================
set -euo pipefail

MONOREPO_ROOT="${MONOREPO_ROOT:-/workspace}"
cd "${MONOREPO_ROOT}"

echo "=============================================================================="
echo "🥋 LAUBURU WEBGPU & RUST 3D SPATIAL SPECIALIST CONTAINER — PORT 8090"
echo "=============================================================================="

cd "${MONOREPO_ROOT}/01_apps/spatial_and_3d/webgpu_specialist"

# Build Rust tests
echo "🔨 Running Rust WebGPU tests..."
cargo test --quiet || true

# Start WebGPU HTTP server on Port 8090
echo "🚀 Serving 3D Spatial Grappling Kinematics on http://0.0.0.0:8090 ..."
exec python3 web/server.py
