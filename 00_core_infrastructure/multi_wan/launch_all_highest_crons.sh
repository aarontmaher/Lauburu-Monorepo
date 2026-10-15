#!/usr/bin/env bash
# ==============================================================================
# launch_all_highest_crons.sh
# ==============================================================================
# Master Launcher for the Canonical Monorepo Development & Restructuring Crons
#
# Suite:
# 1. cron_host_sanctuary_ram_governor   (Every 15m - zombie_daemon_reaper.sh)
# 2. cron_screen_lens_teacher_sweep     (Every 5m  - lens_project_teacher_sweep.py)
# 3. cron_multi_cloud_priority_council  (Every 10m - lens_multi_cloud_priority_council.py)
# 4. cron_autonomous_code_healer        (Every 15m - cron_autonomous_code_healer.py)
# 5. cron_tri_vault_git_sync            (Every 30m - tri_vault_git_sync.py)
# 6. cron_7_layer_mesh_bluetooth_healer (Every 15m - canonical_network_resurrection_engine.py)
# ==============================================================================

set -eo pipefail

REPO_ROOT="/Volumes/Lauburu-Monorepo"
LOG_DIR="${REPO_ROOT}/logs"
mkdir -p "${LOG_DIR}"

echo "========================================================================"
echo "🚀 Launching Lauburu Master Development & Restructuring Cron Automations"
echo "========================================================================"

# 1. Host Sanctuary & Prompt Cache Evictor (Handled via task-601 / schedule)
echo "✔ [1/6] Host RAM Sanctuary Watchdog: Active via task-601 (zombie_daemon_reaper.sh)"

# 2. Screen Lens Teacher Sweep Daemon (Interval 300s)
if pgrep -f "lens_project_teacher_sweep.py --daemon" >/dev/null; then
    echo "✔ [2/6] Screen Lens Teacher Sweep is already running (PID: $(pgrep -f "lens_project_teacher_sweep.py --daemon"))"
else
    echo "🚀 [2/6] Starting Screen Lens Teacher Sweep Daemon (300s interval)..."
    nohup python3 -u "${REPO_ROOT}/01_apps/screen_lens/src/lens_project_teacher_sweep.py" --daemon --interval 300.0 > "${LOG_DIR}/lens_teacher_sweep_daemon.log" 2>&1 &
    echo "   -> Active with PID: $!"
fi

# 3. Multi-Cloud Priority Council (Interval 600s)
if pgrep -f "lens_multi_cloud_priority_council.py" >/dev/null; then
    echo "✔ [3/6] Multi-Cloud Priority Council is already running (PID: $(pgrep -f "lens_multi_cloud_priority_council.py"))"
else
    echo "🚀 [3/6] Starting Multi-Cloud Priority Council Daemon (600s interval)..."
    nohup python3 -u -c "
import time, subprocess, sys
while True:
    try:
        subprocess.run([sys.executable, '${REPO_ROOT}/01_apps/screen_lens/src/lens_multi_cloud_priority_council.py'], check=False)
    except Exception as e:
        print(f'Council error: {e}')
    time.sleep(600.0)
" > "${LOG_DIR}/multi_cloud_priority_council_daemon.log" 2>&1 &
    echo "   -> Active with PID: $!"
fi

# 4. Autonomous Code Healer & Restructuring Engine (Interval 900s)
if pgrep -f "cron_autonomous_code_healer.py --daemon" >/dev/null; then
    echo "✔ [4/6] Autonomous Code Healer is already running (PID: $(pgrep -f "cron_autonomous_code_healer.py --daemon"))"
else
    echo "🚀 [4/6] Starting Autonomous Code Healer & Restructuring Daemon (900s interval)..."
    nohup python3 -u "${REPO_ROOT}/01_apps/screen_lens/src/cron_autonomous_code_healer.py" --daemon --interval 900.0 > "${LOG_DIR}/autonomous_code_healer_daemon.log" 2>&1 &
    echo "   -> Active with PID: $!"
fi

# 5. Tri-Vault Storage Synchronization (Interval 1800s)
if pgrep -f "tri_vault_git_sync.py --daemon" >/dev/null; then
    echo "✔ [5/6] Tri-Vault Storage Sync is already running (PID: $(pgrep -f "tri_vault_git_sync.py --daemon"))"
else
    echo "🚀 [5/6] Starting Tri-Vault Storage Sync Daemon (1800s interval)..."
    nohup python3 -u "${REPO_ROOT}/06_scripts_and_tooling/automation/tri_vault_git_sync.py" --daemon --interval 1800.0 > "${LOG_DIR}/tri_vault_git_sync_daemon.log" 2>&1 &
    echo "   -> Active with PID: $!"
fi

# 6. 7-Layer Mesh Bluetooth Network Healer (Interval 900s)
if pgrep -f "canonical_network_resurrection_engine.py --daemon" >/dev/null; then
    echo "✔ [6/7] Mesh Bluetooth Network Healer is already running (PID: $(pgrep -f "canonical_network_resurrection_engine.py --daemon"))"
else
    echo "🚀 [6/7] Starting Mesh Bluetooth Network Healer Daemon (900s interval)..."
    nohup python3 -u "${REPO_ROOT}/06_scripts_and_tooling/canonical_network_resurrection_engine.py" --daemon --interval 900.0 > "${LOG_DIR}/mesh_bluetooth_healer_daemon.log" 2>&1 &
    echo "   -> Active with PID: $!"
fi

# 7. NPU & Speculative AI Autonomous Optimizer (Interval 600s)
if pgrep -f "npu_speculative_cron_optimizer.py --daemon" >/dev/null; then
    echo "✔ [7/7] NPU & Speculative AI Optimizer is already running (PID: $(pgrep -f "npu_speculative_cron_optimizer.py --daemon"))"
else
    echo "🚀 [7/7] Starting NPU & Speculative AI Autonomous Optimizer Daemon (600s interval)..."
    nohup python3 -u "${REPO_ROOT}/00_core_infrastructure/crons/npu_speculative_cron_optimizer.py" --daemon --interval 600.0 > "${LOG_DIR}/npu_speculative_cron_optimizer.log" 2>&1 &
    echo "   -> Active with PID: $!"
fi

echo "========================================================================"
echo "✨ All 7 Master Development & Restructuring Automations Active!"
echo "========================================================================"
