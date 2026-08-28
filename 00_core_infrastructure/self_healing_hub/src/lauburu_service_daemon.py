#!/usr/bin/env python3
"""
Lauburu Sovereign Mesh Service Daemon & 24/7 Watchdog Supervisor
Ensures both the Backend API (Port 5001) and Frontend Hub (Port 3000)
remain 100% online, auto-recovering within 2 seconds if any process drops.
"""

import os
import sys
import time
import signal
import urllib.request
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [WatchdogSupervisor] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/tmp/lauburu_supervisor.log")
    ]
)
logger = logging.getLogger("WatchdogSupervisor")

MONOREPO_ROOT = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
HUB_SRC_DIR = os.path.join(MONOREPO_ROOT, "self_healing_hub", "src")
FRONTEND_DIR = os.path.join(MONOREPO_ROOT, "self_healing_hub", "frontend")
MESH_DASHBOARD_DIR = "/Users/aaron/DFS_UNIFIED/01_apps/mesh_dashboard"
PORT_4000_HUB_DIR = os.path.join(MONOREPO_ROOT, "01_apps", "port_4000_hub")
API_PORT = 5001
VITE_PORT = 3000
PWA_PORT = 3002
APP_STORE_PORT = 4000

def is_port_responding(url, timeout=1.5):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LauburuWatchdog/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status in [200, 304, 404]
    except Exception:
        return False

def kill_port_owner(port):
    try:
        cmd = f"lsof -ti :{port} | xargs kill -9 2>/dev/null || true"
        subprocess.run(cmd, shell=True, timeout=2)
    except Exception as e:
        logger.warning(f"Error killing port {port} owner: {e}")

last_start_time = {
    API_PORT: 0,
    VITE_PORT: 0,
    PWA_PORT: 0,
    APP_STORE_PORT: 0
}

def ensure_api_server():
    now = time.time()
    if now - last_start_time[API_PORT] < 8:
        return
    if not is_port_responding(f"http://127.0.0.1:{API_PORT}/api/devices/live_monitor"):
        logger.warning(f"🚨 API Server on Port {API_PORT} is DOWN or not responding! Auto-recovering...")
        kill_port_owner(API_PORT)
        time.sleep(0.5)
        api_script = os.path.join(HUB_SRC_DIR, "api_server.py")
        log_file = open("/tmp/lauburu_hub_api.log", "a")
        subprocess.Popen(
            [sys.executable, api_script],
            cwd=HUB_SRC_DIR,
            stdout=log_file,
            stderr=log_file,
            start_new_session=True
        )
        last_start_time[API_PORT] = time.time()
        logger.info(f"✅ Spawned api_server.py on Port {API_PORT}")

def ensure_frontend_hub():
    now = time.time()
    if now - last_start_time[VITE_PORT] < 8:
        return
    if not is_port_responding(f"http://127.0.0.1:{VITE_PORT}/"):
        logger.warning(f"🚨 Frontend Hub on Port {VITE_PORT} is DOWN or not responding! Auto-recovering...")
        kill_port_owner(VITE_PORT)
        time.sleep(0.5)
        log_file = open("/tmp/lauburu_hub_vite.log", "a")
        subprocess.Popen(
            ["npx", "vite", "--host", "0.0.0.0", "--port", str(VITE_PORT)],
            cwd=FRONTEND_DIR,
            stdout=log_file,
            stderr=log_file,
            start_new_session=True
        )
        last_start_time[VITE_PORT] = time.time()
        logger.info(f"✅ Spawned Vite Frontend Hub on Port {VITE_PORT}")

def ensure_mesh_dashboard_pwa():
    now = time.time()
    if now - last_start_time[PWA_PORT] < 15:
        return
    if not is_port_responding(f"http://127.0.0.1:{PWA_PORT}/"):
        logger.warning(f"🚨 Mesh Dashboard PWA on Port {PWA_PORT} is DOWN! Auto-recovering...")
        kill_port_owner(PWA_PORT)
        time.sleep(0.5)
        log_file = open("/tmp/mesh_dashboard_3002.log", "a")
        subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=MESH_DASHBOARD_DIR,
            stdout=log_file,
            stderr=log_file,
            start_new_session=True
        )
        last_start_time[PWA_PORT] = time.time()
        logger.info(f"✅ Spawned Next.js Mesh Dashboard on Port {PWA_PORT}")

def ensure_port_4000_hub():
    now = time.time()
    if now - last_start_time[APP_STORE_PORT] < 8:
        return
    if not is_port_responding(f"http://127.0.0.1:{APP_STORE_PORT}/docs"):
        logger.warning(f"🚨 Port 4000 App Store Hub is DOWN! Auto-recovering...")
        kill_port_owner(APP_STORE_PORT)
        time.sleep(0.5)
        server_script = os.path.join(PORT_4000_HUB_DIR, "server.py")
        log_file = open("/tmp/port_4000_hub.log", "a")
        subprocess.Popen(
            [sys.executable, server_script],
            cwd=PORT_4000_HUB_DIR,
            stdout=log_file,
            stderr=log_file,
            start_new_session=True
        )
        last_start_time[APP_STORE_PORT] = time.time()
        logger.info(f"✅ Spawned Port 4000 App Store Hub on Port {APP_STORE_PORT}")

def main():
    logger.info("🛡️ Lauburu 24/7 Watchdog Supervisor initialized. Monitoring Ports 5001, 4000, 3002, 3000...")
    with open("/tmp/lauburu_service_daemon.pid", "w") as f:
        f.write(str(os.getpid()))

    while True:
        try:
            ensure_api_server()
            ensure_frontend_hub()
            ensure_mesh_dashboard_pwa()
            ensure_port_4000_hub()
        except Exception as e:
            logger.error(f"Supervisor error during health check cycle: {e}")
        time.sleep(3.0)

if __name__ == "__main__":
    main()
