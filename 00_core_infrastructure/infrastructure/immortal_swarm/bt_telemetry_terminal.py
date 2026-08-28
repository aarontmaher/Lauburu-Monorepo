#!/usr/bin/env python3
import time
import os
import curses
import asyncio
import threading
from bleak import BleakScanner

# Global state for UI
sensor_state = {
    "status": "WAITING FOR SENSOR...",
    "hr": "--",
    "rr": "-- ms",
    "imu": "--",
    "logs": ["> Terminal initialized in Termux.", "> Listening for Bluetooth Broadcasts..."]
}

def log_msg(msg):
    sensor_state["logs"].append(f"> {msg}")
    if len(sensor_state["logs"]) > 5:
        sensor_state["logs"].pop(0)

async def scan_ble():
    log_msg("BLE Scanner started.")
    try:
        devices = await BleakScanner.discover(timeout=5.0)
        movesense_found = False
        for d in devices:
            if d.name and "Movesense" in d.name:
                log_msg(f"Found {d.name} [{d.address}]")
                sensor_state["status"] = f"CONNECTED ({d.name})"
                movesense_found = True
                # Future: BleakClient connection to subscribe to HR/IMU characteristics
                break
        
        if not movesense_found:
            log_msg("No Movesense sensors found nearby.")
    except Exception as e:
        log_msg(f"BLE Error: {e}")

def run_asyncio_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        loop.run_until_complete(scan_ble())
        time.sleep(10)

def draw_dashboard(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(1)
    
    # Start BLE thread
    ble_thread = threading.Thread(target=run_asyncio_loop, daemon=True)
    ble_thread.start()
    
    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        title = " LAUBURU BLUETOOTH PAN & TELEMETRY TERMINAL "
        stdscr.addstr(1, max(0, (width - len(title)) // 2), title, curses.A_BOLD | curses.A_REVERSE)
        
        # Node Status
        stdscr.addstr(3, 2, "[ NETWORK MESH STATUS ]", curses.A_BOLD)
        bnep_active = os.system("ip link show bnep0 > /dev/null 2>&1") == 0
        status_color = curses.A_BOLD if bnep_active else curses.A_DIM
        stdscr.addstr(5, 4, f"Bluetooth PAN (bnep0) : {'ACTIVE' if bnep_active else 'OFFLINE'}", status_color)
        stdscr.addstr(6, 4, f"Tailscale Fallback    : {'READY' if bnep_active else 'UNAVAILABLE'}", status_color)
        
        # Movesense Telemetry
        stdscr.addstr(9, 2, "[ MOVESENSE TELEMETRY ]", curses.A_BOLD)
        stdscr.addstr(11, 4, f"Sensor Status   : {sensor_state['status']}")
        stdscr.addstr(12, 4, f"Heart Rate (HR) : {sensor_state['hr']}")
        stdscr.addstr(13, 4, f"RR Intervals    : {sensor_state['rr']}")
        stdscr.addstr(14, 4, f"IMU 6-Axis      : {sensor_state['imu']}")
        
        # Log
        stdscr.addstr(17, 2, "[ SWARM ACTIVITY LOG ]", curses.A_BOLD)
        for i, log in enumerate(sensor_state["logs"]):
            stdscr.addstr(19 + i, 4, log)
        
        stdscr.refresh()
        
        q = stdscr.getch()
        if q == ord('q'):
            break
        
        time.sleep(1)

if __name__ == "__main__":
    try:
        curses.wrapper(draw_dashboard)
    except KeyboardInterrupt:
        pass
