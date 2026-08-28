"""
multi_wan/main.py - Entrypoint for Multi-WAN Aggregation & Device-to-Device Connectivity System.

Launches:
- Dynamic Interface Tracker & Device Connectivity Optimizer
- Accumulative Bonding Proxy Server on Port 8888
- Dashboard HTTP Server & REST API on Port 5050
- Local AGI Bridge & Proactive Storage Manager
- Pixel Nano Local AGI Telemetry Link
"""

import argparse
import asyncio
import logging
import os
import sys
import time
import subprocess
import signal

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from multi_wan import (
    BondingProxyServer,
    DashboardServer,
    DeviceConnectivityOptimizer,
    InterfaceTracker,
    LocalAGIBridge,
    PixelNanoBridge,
    StorageManager,
    ServiceKeepAliveManager,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("multi_wan.main")

MONOREPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

async def async_main():
    parser = argparse.ArgumentParser(description="Lauburu Multi-WAN Aggregation & Device-to-Device Connectivity Daemon")
    parser.add_argument("--dashboard-port", type=int, default=5050, help="Dashboard HTTP server port (default: 5050)")
    parser.add_argument("--proxy-port", type=int, default=8888, help="Multiplexing proxy server port (default: 8888)")
    parser.add_argument("--check-interval", type=float, default=3.0, help="Interface probe interval in seconds")
    args = parser.parse_args()

    print("\n╔════════════════════════════════════════════════════════════════════════════╗")
    print("║  🌀 LAUBURU MULTI-WAN AGGREGATION & DEVICE CONNECTIVITY SYSTEM             ║")
    print("║  Real-Time Accumulative Bandwidth Pooling & Multi-Transport Optimizer      ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝\n")

    # 1. Initialize core components
    tracker = InterfaceTracker(check_interval=args.check_interval)
    optimizer = DeviceConnectivityOptimizer()
    agi_bridge = LocalAGIBridge()
    storage_manager = StorageManager(agi_bridge=agi_bridge)
    pixel_nano = PixelNanoBridge()
    keepalive_mgr = ServiceKeepAliveManager(monorepo_dir=MONOREPO_DIR, check_interval=args.check_interval)

    # 1.5 Start external daemons (adb_bridge, mesh_transport_daemon)
    logger.info("Starting ADB Bridge Daemon on Port 8089...")
    adb_process = subprocess.Popen([sys.executable, os.path.join(MONOREPO_DIR, "Installed_Apps", "Core_Mesh", "adb_bridge.py")])
    
    logger.info("Starting Mesh Transport Daemon on Port 9010...")
    mesh_process = subprocess.Popen([sys.executable, os.path.join(MONOREPO_DIR, "Installed_Apps", "Core_Mesh", "mesh_transport_daemon.py")])

    # 2. Start Proxy Server (Port 8888)
    proxy_server = BondingProxyServer(host="0.0.0.0", port=args.proxy_port, tracker=tracker)
    await proxy_server.start()

    # 3. Start Dashboard Server (Port 5050)
    dashboard_server = DashboardServer(
        host="0.0.0.0",
        port=args.dashboard_port,
        proxy_server=proxy_server,
        tracker=tracker,
        agi_bridge=agi_bridge,
        storage_manager=storage_manager,
        pixel_nano=pixel_nano,
    )
    dashboard_server.optimizer = optimizer
    dashboard_server.keepalive_mgr = keepalive_mgr
    await dashboard_server.start()

    # 4. Start background monitoring loops
    tracker.start_monitoring()
    asyncio.create_task(keepalive_mgr.start_monitoring_loop())

    async def auto_heal_loop():
        logger.info("Starting Auto-Heal connection enforcement loop...")
        while True:
            try:
                optimizer.enforce_connections()
            except Exception as e:
                logger.debug(f"Auto-heal error: {e}")
            await asyncio.sleep(15)

    asyncio.create_task(auto_heal_loop())

    logger.info(f"Multi-WAN Proxy running on http://0.0.0.0:{args.proxy_port}")
    logger.info(f"Control Center Dashboard running on http://0.0.0.0:{args.dashboard_port}/")
    logger.info("24/7 Service Keep-Alive active (maintaining Ollama, lmlink, Gemini AI, Bridge daemons).")
    print(f"\n✅ SYSTEM ACTIVE: Access Control Center at http://localhost:{args.dashboard_port}/")
    print(f"✅ 24/7 SERVICE KEEP-ALIVE ACTIVE: Maintaining Ollama, LM Studio / lmlink, Gemini AI Service")
    print(f"✅ SOCKS5/HTTP PROXY ACTIVE: Proxy listening at 0.0.0.0:{args.proxy_port}\n")

    try:
        while True:
            await asyncio.sleep(10)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutdown signal received. Stopping servers...")
    finally:
        tracker.stop_monitoring()
        keepalive_mgr.stop_monitoring()
        await dashboard_server.stop()
        await proxy_server.stop()
        logger.info("Stopping external daemons...")
        adb_process.terminate()
        mesh_process.terminate()
        logger.info("All Multi-WAN services stopped.")


def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
