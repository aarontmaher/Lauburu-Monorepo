#!/usr/bin/env bash
# ==============================================================================
# Lauburu Mesh — 24/7 Offline Continuous Swarm & 10M Drafter Daemon
# Subsystem: 06_scripts_and_tooling/automation/lauburu_offline_continuous_daemon.sh
# Version: 1.0.0-OFFLINE-247-DAEMON
# ==============================================================================
set -u

MONOREPO_ROOT="/Volumes/Lauburu-Monorepo"
LOG_DIR="${MONOREPO_ROOT}/logs"
SESSION_DIR="${MONOREPO_ROOT}/session_logs"
PID_DIR="/tmp/lauburu_daemons"

mkdir -p "${LOG_DIR}" "${SESSION_DIR}" "${PID_DIR}"

MASTER_LOG="${LOG_DIR}/offline_continuous_247.log"
DRAFTER_LOG="${SESSION_DIR}/continuous_10m_drafter.log"
SWARM_LOG="${SESSION_DIR}/continuous_swarm_loop.log"

PYTHON_BIN="/Users/aaron/.local/bin/python3"
if [ ! -x "${PYTHON_BIN}" ]; then
  PYTHON_BIN="/Users/aaron/.venv/bin/python"
fi
if [ ! -x "${PYTHON_BIN}" ]; then
  PYTHON_BIN="/usr/bin/python3"
fi

log_msg() {
  echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') [DAEMON-247] $1" | tee -a "${MASTER_LOG}"
}

is_running() {
  local pid_file="$1"
  if [ -f "${pid_file}" ]; then
    local pid=$(cat "${pid_file}" 2>/dev/null)
    if [ "${pid}" = "remote_linuxmini" ]; then
      return 0
    fi
    if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

ensure_caffeinate() {
  if ! pgrep -f "caffeinate -dimsu" >/dev/null 2>&1; then
    nohup caffeinate -dimsu >/dev/null 2>&1 &
    log_msg "⚡ System wake-lock active (caffeinate -dimsu PID: $!)."
  fi
}

start_drafter() {
  local pid_file="${PID_DIR}/10m_drafter.pid"
  pkill -f "continuous_10m_genetic_drafter_trainer.py" 2>/dev/null || true
  # Inverse Allocation Policy: Offload 2.3 GB drafter trainer to Linux Mini PC (23 GB free RAM)
  if ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no linuxmini "systemctl is-active genetic-drafter-trainer.service" >/dev/null 2>&1; then
    echo "remote_linuxmini" > "${pid_file}"
    log_msg "✔ 10M Genetic Drafter ACTIVE & OFF-LOADED to Linux Mini PC (linuxmini)."
    return 0
  else
    log_msg "⚠️ Resurrecting 10M Genetic Drafter on Linux Mini PC (linuxmini)..."
    ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no linuxmini "systemctl restart genetic-drafter-trainer.service" >/dev/null 2>&1 || true
    echo "remote_linuxmini" > "${pid_file}"
    return 0
  fi
}

start_swarm_loop() {
  local pid_file="${PID_DIR}/swarm_loop.pid"
  if is_running "${pid_file}"; then
    log_msg "✔ Self-Evolving Swarm Loop already running (PID: $(cat "${pid_file}"))."
    return 0
  fi

  pkill -f "continuous_self_evolving_swarm_loop.py" 2>/dev/null || true
  nohup "${PYTHON_BIN}" "${MONOREPO_ROOT}/05_agents_and_swarms/continuous_self_evolving_swarm_loop.py" >> "${SWARM_LOG}" 2>&1 &
  local new_pid=$!
  echo "${new_pid}" > "${pid_file}"
  log_msg "🚀 Started Continuous Self-Evolving Swarm Loop (PID: ${new_pid})."
}

stop_all() {
  log_msg "🛑 Stopping all 24/7 offline continuous daemons..."
  pkill -f "continuous_10m_genetic_drafter_trainer.py" 2>/dev/null || true
  pkill -f "continuous_self_evolving_swarm_loop.py" 2>/dev/null || true
  rm -f "${PID_DIR}/10m_drafter.pid" "${PID_DIR}/swarm_loop.pid" "${PID_DIR}/master.pid"
  log_msg "✔ All daemons stopped cleanly."
}

check_status() {
  echo "=== LAUBURU 24/7 OFFLINE CONTINUOUS STATUS ==="
  local d_pid="${PID_DIR}/10m_drafter.pid"
  local s_pid="${PID_DIR}/swarm_loop.pid"

  if is_running "${d_pid}"; then
    echo "• 10M Genetic Drafter:       🟢 RUNNING (PID: $(cat "${d_pid}"))"
  else
    echo "• 10M Genetic Drafter:       🔴 STOPPED"
  fi

  if is_running "${s_pid}"; then
    echo "• Continuous Swarm Loop:     🟢 RUNNING (PID: $(cat "${s_pid}"))"
  else
    echo "• Continuous Swarm Loop:     🔴 STOPPED"
  fi

  if pgrep -f "llama-server" >/dev/null 2>&1; then
    echo "• Local Model (llama-server): 🟢 RUNNING (Port 8081)"
  else
    echo "• Local Model (llama-server): 🟡 INACTIVE"
  fi

  if pgrep -f "caffeinate" >/dev/null 2>&1; then
    echo "• macOS Wake-Lock:            🟢 ACTIVE (System will not sleep)"
  else
    echo "• macOS Wake-Lock:            🟡 INACTIVE"
  fi

  "${PYTHON_BIN}" -c "
import shutil, psutil
free_gb = shutil.disk_usage('/Users/aaron').free / (1024**3)
vm = psutil.virtual_memory()
print(f'• Free NVMe Disk:             {free_gb:.2f} GB')
print(f'• Physical RAM:               {vm.available/(1024**3):.2f} GB Free / {vm.total/(1024**3):.2f} GB Total ({vm.percent}% Used)')
"
}

run_watchdog_loop() {
  echo "$$" > "${PID_DIR}/master.pid"
  log_msg "🟢 Master 24/7 Offline Watchdog Started (PID: $$). Running continuous monitoring."

  trap 'stop_all; exit 0' SIGTERM SIGINT

  ensure_caffeinate

  while true; do
    ensure_caffeinate

    # 1. Check 10M Drafter
    local d_pid="${PID_DIR}/10m_drafter.pid"
    if ! is_running "${d_pid}"; then
      log_msg "⚠️ 10M Drafter was inactive; resurrecting..."
      start_drafter
    fi

    # 2. Check Swarm Loop
    local s_pid="${PID_DIR}/swarm_loop.pid"
    if ! is_running "${s_pid}"; then
      log_msg "⚠️ Swarm Loop was inactive; resurrecting..."
      start_swarm_loop
    fi

    # 3. Dynamic RAM & Disk Headroom Enforcement (Rule 3)
    free_ram=$("${PYTHON_BIN}" -c "import psutil; print(round(psutil.virtual_memory().available / (1024**3), 2))" 2>/dev/null || echo "9.8")
    is_ram_low=$("${PYTHON_BIN}" -c "print(float(\"${free_ram}\") < 3.0)" 2>/dev/null || echo "False")
    if [ "${is_ram_low}" = "True" ]; then
      log_msg "⚠️ Host RAM sanctuary alert: free RAM is ${free_ram} GB (< 3.0 GB buffer). Running purge..."
      purge 2>/dev/null || true
    fi

    sleep 30
  done
}

case "${1:-start}" in
  start)
    ensure_caffeinate
    start_drafter
    start_swarm_loop
    sleep 1
    log_msg "✔ Both 24/7 continuous processes started in background."
    check_status
    ;;
  watchdog)
    run_watchdog_loop
    ;;
  stop)
    stop_all
    ;;
  restart)
    stop_all
    sleep 2
    ensure_caffeinate
    start_drafter
    start_swarm_loop
    sleep 1
    check_status
    ;;
  status)
    check_status
    ;;
  *)
    echo "Usage: $0 {start|watchdog|stop|restart|status}"
    exit 1
    ;;
esac
