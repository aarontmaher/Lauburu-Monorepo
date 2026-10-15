#!/usr/bin/env bash
# Canonical Dispatcher: train_tiny_lms_across_mesh.sh
# Triggers Tiny LM training across the 7-Layer Lauburu Mesh (L1, L3, L6)
# Follows Rule 9 for Shizuku execution and Rule 1/10 for node selection.

set -e

DIR="/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/ai/tiny_lms"
MESH_PING="python3 /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/network/mesh_ping.py"

echo "=== [L1] Compiling and Executing on Mac Mini Host ==="
cd "$DIR"
gcc -O3 -o tiny_lm_c tiny_lm.c -lm
g++ -O3 -o tiny_lm_cpp tiny_lm.cpp
./tiny_lm_c
./tiny_lm_cpp
uv run tiny_lm.py
echo "[L1] Execution Complete."
echo ""

echo "=== [L3] Deploying to Linux Hub (AMD Ryzen) ==="
# Retrieve IP dynamically using mesh_ping.py (Rule 9)
L3_JSON=$( $MESH_PING L3_Linux_Hub 22 --json || true )
L3_ENDPOINT=$(echo "$L3_JSON" | python3 -c "import sys, json; data=json.load(sys.stdin) if sys.stdin.read().strip() else {}; print(data.get('endpoint', ''))" 2>/dev/null || true)

if [ -z "$L3_ENDPOINT" ]; then
    echo "Warning: Could not resolve L3_Linux_Hub. Skipping L3."
else
    L3_IP="${L3_ENDPOINT%:*}"
    L3_PORT="${L3_ENDPOINT##*:}"

    ssh -p "$L3_PORT" "linux@$L3_IP" "mkdir -p ~/tiny_lms"
    scp -P "$L3_PORT" tiny_lm.c tiny_lm.cpp tiny_lm.py ai_training_analysis_tinyml.py "linux@$L3_IP:~/tiny_lms/"
    ssh -p "$L3_PORT" "linux@$L3_IP" "cd ~/tiny_lms && gcc -O3 -o tiny_lm_c tiny_lm.c -lm && g++ -O3 -o tiny_lm_cpp tiny_lm.cpp && ./tiny_lm_c && ./tiny_lm_cpp"
    echo "[L3] Execution Complete."
fi
echo ""

echo "=== [L6] Deploying to Pixel 10 Pro XL AVF Linux Container ==="
L6_JSON=$( $MESH_PING L6_Pixel_10_Edge 8022 --json || true )
L6_ENDPOINT=$(echo "$L6_JSON" | python3 -c "import sys, json; data=json.load(sys.stdin) if sys.stdin.read().strip() else {}; print(data.get('endpoint', ''))" 2>/dev/null || true)

if [ -z "$L6_ENDPOINT" ]; then
    echo "Warning: Could not resolve L6_Pixel_10_Edge. Skipping L6."
else
    L6_TERMUX_IP="${L6_ENDPOINT%:*}"
    L6_TERMUX_PORT="${L6_ENDPOINT##*:}"

    # We push the Tiny LM binaries/scripts to the Android host's VirtioFS shared directory first
    SHARED_MOUNT="/data/local/tmp/avf_shared/tiny_lms"
    AVF_GUEST_IP="10.86.187.34"

    # Using termux wake lock to adhere to Rule 0 (Android 24/7 Keepalive)
    ssh -p "$L6_TERMUX_PORT" "u0_a363@$L6_TERMUX_IP" "termux-wake-lock && mkdir -p $SHARED_MOUNT"
    scp -P "$L6_TERMUX_PORT" tiny_lm.c tiny_lm.cpp tiny_lm.py ai_training_analysis_tinyml.py "u0_a363@$L6_TERMUX_IP:$SHARED_MOUNT/"

    # Compile with ARM64 NEON optimizations for Google Tensor G5 via rish inside the AVF Debian 13 microVM
    ssh -p "$L6_TERMUX_PORT" "u0_a363@$L6_TERMUX_IP" "rish -c 'ssh root@$AVF_GUEST_IP \"cd /mnt/shared/tiny_lms && gcc -O3 -march=armv8-a+crypto+simd -o tiny_lm_c tiny_lm.c -lm 2>&1 && g++ -O3 -march=armv8-a+crypto+simd -o tiny_lm_cpp tiny_lm.cpp 2>&1 && ./tiny_lm_c 2>&1 && ./tiny_lm_cpp 2>&1\" 2>&1'"
    echo "[L6] Execution Complete."
fi
echo ""

echo "Mesh Training Dispatch Completed Successfully."
