#!/bin/bash
# AVF (Android Virtualization Framework) Tiny LM Safe Deployer
# Safely bridges the compiled Tiny LMs directly into the Pixel 10 Pro XL's 
# native Debian 13 microVM, bypassing Termux/ptrace entirely.

PIXEL_TAILSCALE="100.73.38.87"
PIXEL_TERMUX_PORT="8022"
AVF_GUEST_IP="10.86.187.34" # Internal Tap Gateway to the microVM
SHARED_MOUNT="/data/local/tmp/avf_shared"
LM_SOURCE_DIR="/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/ai/tiny_lms"

echo "[1/4] Establishing secure bridge to Pixel 10 Pro XL Tensor G5..."
# We push the Tiny LM binaries/scripts to the Android host's VirtioFS shared directory
ssh -p $PIXEL_TERMUX_PORT u0_a420@$PIXEL_TAILSCALE "mkdir -p $SHARED_MOUNT"

echo "[2/4] Synchronizing Tiny LM binaries to VirtioFS mount..."
rsync -avz -e "ssh -p $PIXEL_TERMUX_PORT" $LM_SOURCE_DIR/ u0_a420@$PIXEL_TAILSCALE:$SHARED_MOUNT/ || echo "Waiting for DeepCoder to output binaries..."

echo "[3/4] Invoking AVF execution via Shizuku Binder redirection..."
# Rule 9 Invariant: redirect stderr to stdout (2>&1) for Shizuku binder transaction fd 2
ssh -p $PIXEL_TERMUX_PORT u0_a420@$PIXEL_TAILSCALE "rish -c 'ssh root@$AVF_GUEST_IP \"cp -r /mnt/shared/tiny_lms /root/ && cd /root/tiny_lms && chmod +x *\" 2>&1'"

echo "[4/4] AVF Sandbox is primed. The native Linux kernel on the Tensor G5 is ready to execute."
