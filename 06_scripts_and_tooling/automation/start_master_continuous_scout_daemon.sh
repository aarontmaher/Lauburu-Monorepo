#!/bin/bash
# ==============================================================================
# Master Continuous Scout, Benchmark & AI Training Daemon Launcher
# ==============================================================================

MONOREPO_ROOT="/Volumes/Lauburu-Monorepo"
cd "$MONOREPO_ROOT"

LOG_FILE="/tmp/master_scout_and_benchmark.log"

echo "======================================================================"
echo "🚀 STARTING 24/7 MASTER SCOUT, SHARDING BENCHMARK & TUI OPTIMIZER"
echo "======================================================================"

# Stop any old instances
pkill -f "master_continuous_scout_and_benchmark_cron.py" 2>/dev/null || true

# Start background daemon
nohup /Volumes/Lauburu-Monorepo/01_apps/canonical_port/.venv/bin/python \
  06_scripts_and_tooling/automation/master_continuous_scout_and_benchmark_cron.py \
  --interval 60 > "$LOG_FILE" 2>&1 &

DAEMON_PID=$!
echo "✅ Daemon started in background with PID: $DAEMON_PID"
echo "📋 Logs available at: $LOG_FILE"
