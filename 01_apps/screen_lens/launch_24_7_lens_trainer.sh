#!/usr/bin/env bash
# ==============================================================================
# Lauburu Lens AI: 24/7 Continuous Training & Multi-Cloud Fleet Daemon Control
# Subsystem: 01_apps/screen_lens/launch_24_7_lens_trainer.sh
# Lauburu Mesh Ecosystem — 2026
# ==============================================================================

set -euo pipefail

REPO_ROOT="/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
DIR="$REPO_ROOT/01_apps/screen_lens/src"
TRAINER_SCRIPT="$DIR/lens_continuous_training_daemon.py"
AUDITOR_SCRIPT="$DIR/lens_flawless_auditor.py"
SWEEP_SCRIPT="$DIR/lens_project_teacher_sweep.py"
COUNCIL_SCRIPT="$DIR/lens_multi_cloud_priority_council.py"
DEEP_RESEARCH_SCRIPT="$DIR/lens_continuous_deep_research_daemon.py"

PID_DIR="$HOME/.lauburu"
TRAINER_PID="$PID_DIR/lens_24_7_trainer.pid"
AUDITOR_PID="$PID_DIR/lens_flawless_auditor.pid"
SWEEP_PID="$PID_DIR/lens_teacher_sweep.pid"
COUNCIL_PID="$PID_DIR/lens_cloud_council.pid"
RESEARCH_PID="$PID_DIR/lens_deep_research.pid"

LOG_DIR="$REPO_ROOT/logs"
TRAINER_LOG="$LOG_DIR/lens_continuous_training.log"
AUDITOR_LOG="$LOG_DIR/lens_flawless_auditor.log"
SWEEP_LOG="$LOG_DIR/lens_teacher_sweep.log"
COUNCIL_LOG="$LOG_DIR/lens_cloud_council.log"
RESEARCH_LOG="$LOG_DIR/lens_continuous_deep_research.log"

mkdir -p "$PID_DIR" "$LOG_DIR"

case "${1:-status}" in
    start)
        echo "========================================================================"
        echo "🚀 Starting Lauburu Lens 24/7 Training & Multi-Cloud Fleet Daemons..."
        echo "========================================================================"
        
        # 1. Start Flawless Code & Visual Auditor Daemon (Audits every 300s)
        if [ -f "$AUDITOR_PID" ] && kill -0 $(cat "$AUDITOR_PID") 2>/dev/null; then
            echo "ℹ️  Flawless Auditor is already running (PID: $(cat "$AUDITOR_PID"))"
        else
            nohup python3 -u "$AUDITOR_SCRIPT" --daemon --interval 300.0 > "$AUDITOR_LOG" 2>&1 &
            echo $! > "$AUDITOR_PID"
            echo "✅ Started Flawless Auditor Daemon (PID: $(cat "$AUDITOR_PID"))"
            echo "   Log: $AUDITOR_LOG"
        fi

        # 2. Start MLX Metal QLoRA Continuous Training Daemon (Checks every 30s)
        if [ -f "$TRAINER_PID" ] && kill -0 $(cat "$TRAINER_PID") 2>/dev/null; then
            echo "ℹ️  Lens 24/7 Trainer is already running (PID: $(cat "$TRAINER_PID"))"
        else
            nohup python3 -u "$TRAINER_SCRIPT" --interval 30.0 > "$TRAINER_LOG" 2>&1 &
            echo $! > "$TRAINER_PID"
            echo "✅ Started 24/7 MLX Metal Trainer Daemon (PID: $(cat "$TRAINER_PID"))"
            echo "   Log: $TRAINER_LOG"
        fi

        # 3. Start Gemini 3.8 Flash Full-Project Looping Sweep Daemon (Sweeps every 300s)
        if [ -f "$SWEEP_PID" ] && kill -0 $(cat "$SWEEP_PID") 2>/dev/null; then
            echo "ℹ️  Teacher Sweep is already running (PID: $(cat "$SWEEP_PID"))"
        else
            nohup python3 -u "$SWEEP_SCRIPT" --daemon --interval 300.0 > "$SWEEP_LOG" 2>&1 &
            echo $! > "$SWEEP_PID"
            echo "✅ Started Gemini 3.8 Flash Teacher Sweep Daemon (PID: $(cat "$SWEEP_PID"))"
            echo "   Log: $SWEEP_LOG"
        fi

        # 4. Start Multi-Cloud Priority Council Daemon (Evaluates priorities every 600s)
        if [ -f "$COUNCIL_PID" ] && kill -0 $(cat "$COUNCIL_PID") 2>/dev/null; then
            echo "ℹ️  Multi-Cloud Council is already running (PID: $(cat "$COUNCIL_PID"))"
        else
            nohup python3 -u -c "
import time, subprocess, sys
while True:
    try:
        subprocess.run([sys.executable, '$COUNCIL_SCRIPT'], check=False)
    except Exception as e:
        print(f'Council error: {e}')
    time.sleep(600.0)
" > "$COUNCIL_LOG" 2>&1 &
            echo $! > "$COUNCIL_PID"
            echo "✅ Started Multi-Cloud Priority Council Daemon (PID: $(cat "$COUNCIL_PID"))"
            echo "   Log: $COUNCIL_LOG"
        fi

        # 5. Start Continuous Deep Research Daemon (CodeClash, SWE-Bench, Local Protocols every 1800s)
        if [ -f "$RESEARCH_PID" ] && kill -0 $(cat "$RESEARCH_PID") 2>/dev/null; then
            echo "ℹ️  Continuous Deep Research is already running (PID: $(cat "$RESEARCH_PID"))"
        else
            nohup python3 -u "$DEEP_RESEARCH_SCRIPT" --interval 1800.0 > "$RESEARCH_LOG" 2>&1 &
            echo $! > "$RESEARCH_PID"
            echo "✅ Started Continuous Deep Research Daemon (PID: $(cat "$RESEARCH_PID"))"
            echo "   Log: $RESEARCH_LOG"
        fi
        ;;

    stop)
        echo "🛑 Stopping Lauburu Lens 24/7 Daemons..."
        if [ -f "$TRAINER_PID" ]; then
            kill $(cat "$TRAINER_PID") 2>/dev/null || true
            rm -f "$TRAINER_PID"
            echo "✅ Stopped Lens Trainer Daemon."
        fi
        if [ -f "$AUDITOR_PID" ]; then
            kill $(cat "$AUDITOR_PID") 2>/dev/null || true
            rm -f "$AUDITOR_PID"
            echo "✅ Stopped Flawless Auditor Daemon."
        fi
        if [ -f "$SWEEP_PID" ]; then
            kill $(cat "$SWEEP_PID") 2>/dev/null || true
            rm -f "$SWEEP_PID"
            echo "✅ Stopped Gemini Teacher Sweep Daemon."
        fi
        if [ -f "$COUNCIL_PID" ]; then
            kill $(cat "$COUNCIL_PID") 2>/dev/null || true
            rm -f "$COUNCIL_PID"
            echo "✅ Stopped Multi-Cloud Council Daemon."
        fi
        if [ -f "$RESEARCH_PID" ]; then
            kill $(cat "$RESEARCH_PID") 2>/dev/null || true
            rm -f "$RESEARCH_PID"
            echo "✅ Stopped Continuous Deep Research Daemon."
        fi
        ;;

    status)
        echo "========================================================================"
        echo "📊 Lauburu Lens 24/7 Fleet Daemons Status"
        echo "========================================================================"
        if [ -f "$TRAINER_PID" ] && kill -0 $(cat "$TRAINER_PID") 2>/dev/null; then
            echo "🟢 24/7 Lens MLX Metal Trainer: RUNNING (PID: $(cat "$TRAINER_PID"))"
        else
            echo "🔴 24/7 Lens MLX Metal Trainer: STOPPED"
        fi

        if [ -f "$AUDITOR_PID" ] && kill -0 $(cat "$AUDITOR_PID") 2>/dev/null; then
            echo "🟢 Flawless Code & Visual Auditor: RUNNING (PID: $(cat "$AUDITOR_PID"))"
        else
            echo "🔴 Flawless Code & Visual Auditor: STOPPED"
        fi

        if [ -f "$SWEEP_PID" ] && kill -0 $(cat "$SWEEP_PID") 2>/dev/null; then
            echo "🟢 Gemini 3.8 Flash Teacher Sweep: RUNNING (PID: $(cat "$SWEEP_PID"))"
        else
            echo "🔴 Gemini 3.8 Flash Teacher Sweep: STOPPED"
        fi

        if [ -f "$COUNCIL_PID" ] && kill -0 $(cat "$COUNCIL_PID") 2>/dev/null; then
            echo "🟢 Multi-Cloud Priority Council: RUNNING (PID: $(cat "$COUNCIL_PID"))"
        else
            echo "🔴 Multi-Cloud Priority Council: STOPPED"
        fi

        if [ -f "$RESEARCH_PID" ] && kill -0 $(cat "$RESEARCH_PID") 2>/dev/null; then
            echo "🟢 Continuous Deep Research Daemon: RUNNING (PID: $(cat "$RESEARCH_PID"))"
        else
            echo "🔴 Continuous Deep Research Daemon: STOPPED"
        fi
        echo "========================================================================"
        ;;

    restart)
        $0 stop
        sleep 1
        $0 start
        ;;

    once)
        echo "⚡ Executing single immediate pass..."
        python3 "$DEEP_RESEARCH_SCRIPT" --once
        python3 "$AUDITOR_SCRIPT" --once
        python3 "$SWEEP_SCRIPT" --once
        python3 "$COUNCIL_SCRIPT"
        python3 "$TRAINER_SCRIPT" --once --steps 30
        ;;

    *)
        echo "Usage: $0 {start|stop|status|restart|once}"
        exit 1
        ;;
esac
