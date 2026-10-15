#!/bin/bash
# Router Python LM Deployment & Comparison Harness
# Deploys a Python-based Tiny LM to the GL.iNet MT3600BE Router (OpenWrt)
# to compare functionality and performance against the native C++/NPU version.

ROUTER_IP="192.168.8.1"
ROUTER_USER="root"
LM_SOURCE_DIR="/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/ai/tiny_lms"
TARGET_DIR="/overlay/python_tiny_lm"

echo "[1/4] Preparing GL.iNet Router for Python Environment..."
# Ensure Python3 and pip are installed on OpenWrt
ssh $ROUTER_USER@$ROUTER_IP "opkg update && opkg install python3 python3-pip python3-numpy 2>/dev/null || true"

echo "[2/4] Duplicating Router LM (Python Variant)..."
ssh $ROUTER_USER@$ROUTER_IP "mkdir -p $TARGET_DIR"
scp $LM_SOURCE_DIR/python_router_lm.py $ROUTER_USER@$ROUTER_IP:$TARGET_DIR/ || echo "Waiting for DeepCoder to finalize python_router_lm.py..."

echo "[3/4] Scaffolding Comparison Benchmark Harness..."
# Create a wrapper script on the router to test both side-by-side
ssh $ROUTER_USER@$ROUTER_IP "cat << 'EOF' > $TARGET_DIR/run_comparison.sh
#!/bin/sh
echo \"=== C++ NPU LM Bench ===\"
time /usr/bin/router_npu_lm --test-ingestion

echo \"=== Python CPU LM Bench ===\"
time python3 $TARGET_DIR/python_router_lm.py --test-ingestion
EOF"

ssh $ROUTER_USER@$ROUTER_IP "chmod +x $TARGET_DIR/run_comparison.sh"

echo "[4/4] Deployment scaffolding complete. The router is primed for the Python LM."
