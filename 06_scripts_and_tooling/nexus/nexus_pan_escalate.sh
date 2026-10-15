#!/usr/bin/env bash
# Nexus Escalate Bluetooth PAN Directive
set -euo pipefail

echo "📡 Disagreeing with Wi-Fi drop: Escalating to Layer 0/1 Bluetooth PAN..."
nexus dispatch --target all --directive ENABLE_PAN || {
    echo "Fallback to local adb/shizuku PAN command:"
    python3 /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/network/canonical_network_resurrection_engine.py --pan || true
}
