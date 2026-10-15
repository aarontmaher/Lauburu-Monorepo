#!/bin/bash
# Launches mesh daemons in tmux on Linux Mini

# Detect Python runtime
if [ -f "/home/linux/mesh_venv/bin/python" ]; then
    VENV="/home/linux/mesh_venv/bin/python"
elif [ -f "/home/linux/exo_env/bin/python" ]; then
    VENV="/home/linux/exo_env/bin/python"
elif [ -f "/home/linuxmini/mesh_venv/bin/python" ]; then
    VENV="/home/linuxmini/mesh_venv/bin/python"
else
    VENV="$(which python3)"
fi

# Detect monorepo path
if [ -d "/Volumes/Lauburu-Monorepo" ]; then
    REPO="/Volumes/Lauburu-Monorepo"
elif [ -d "/home/linux/DFS_UNIFIED/Lauburu-Monorepo" ]; then
    REPO="/home/linux/DFS_UNIFIED/Lauburu-Monorepo"
elif [ -d "/home/linux/teamwork_projects/Lauburu-Monorepo" ]; then
    REPO="/home/linux/teamwork_projects/Lauburu-Monorepo"
else
    REPO="/home/linux"
fi

SESSION="mesh_daemons"

tmux new-session -d -s $SESSION -n "quota" "$VENV $REPO/06_scripts_and_tooling/automation/cloud_quota_harvester_daemon.py"
tmux new-window -t $SESSION:1 -n "orchestrator" "$VENV $REPO/05_agents_and_swarms/tri_orchestrator_sweeping_review_daemon.py --daemon --interval 300"
tmux new-window -t $SESSION:2 -n "samsung" "$VENV $REPO/06_scripts_and_tooling/automation/samsung_s20_auto_revert_daemon.py"
tmux new-window -t $SESSION:3 -n "vl_champ" "$VENV $REPO/01_apps/screen_lens/src/continuous_vl_championship_daemon.py --daemon --interval 120.0"
tmux new-window -t $SESSION:4 -n "npu_sentinel" "$VENV $REPO/01_apps/screen_lens/sandbox_evolution/npu_sentinel/npu_metric_sentinel_daemon.py"
tmux new-window -t $SESSION:5 -n "prima_adapter" "$VENV $REPO/02_ai_models_and_inference/sharding_daemon/prima_ring_adapter.py"
tmux new-window -t $SESSION:6 -n "decentralized_prima" "$VENV $REPO/02_ai_models_and_inference/decentralized_prima_daemon.py"
tmux new-window -t $SESSION:7 -n "nomad_courier" "$VENV $REPO/06_scripts_and_tooling/network/nomad_courier_self_healer.py --daemon"
tmux new-window -t $SESSION:8 -n "npu_optimizer" "$VENV $REPO/00_core_infrastructure/crons/npu_speculative_cron_optimizer.py --daemon --interval 600"
tmux new-window -t $SESSION:9 -n "pixel_movesense" "$VENV $REPO/06_scripts_and_tooling/mesh/pixel_movesense_bridge.py --daemon --interval 1.0"
tmux new-window -t $SESSION:10 -n "hardware_scout" "$VENV $REPO/06_scripts_and_tooling/hardware_scout_pipeline.py --daemon"

echo "Launched $SESSION on tmux"
