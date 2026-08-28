#!/usr/bin/env python3
import argparse
import datetime
import json
import os
import subprocess
import sys
import time

# Write to router's /tmp if running on OpenWrt, otherwise DFS
if sys.platform.startswith('linux') and os.path.exists('/tmp') and not os.access("/Users/aaron/DFS_UNIFIED", os.W_OK):
    TRENDS_FILE = "/tmp/mesh_trends.json"
    DEFAULT_DELTA_URI = None
else:
    TRENDS_FILE = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/mesh_trends.json"
    DEFAULT_DELTA_URI = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/delta_tables/mesh_telemetry_stream"

NODES = {
    "L1_Mac_Node": "100.119.199.76",
    "L2_MacBook_Pro": "100.103.212.21",
    "L3_Linux_Head": "100.101.39.98",
    "L4_Linux_Tablet": "100.81.92.125",
    "L5_MacBook_Air": "100.93.158.96",
    "L6_Pixel_10_Pro": "100.73.38.87",
    "L7_Samsung_S20": "100.84.40.95",
    "GW_Router": "100.122.185.123"
}

# Optional import of Delta Engine for ACID streaming
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from delta_engine.schema import MESH_TELEMETRY_ARROW_SCHEMA
    from delta_engine.writer import DeltaDatasetWriter
    DELTA_ENGINE_AVAILABLE = True
except Exception:
    DELTA_ENGINE_AVAILABLE = False


def get_ping(ip):
    try:
        # Cross platform ping (macOS uses -W ms, OpenWrt busybox uses -W sec)
        if sys.platform == 'darwin':
            res = subprocess.run(["ping", "-c", "1", "-W", "500", ip], capture_output=True, text=True)
        else:
            res = subprocess.run(["ping", "-c", "1", "-W", "1", ip], capture_output=True, text=True)
            
        if res.returncode == 0:
            for line in res.stdout.split('\n'):
                if "time=" in line:
                    return float(line.split("time=")[1].split(" ")[0])
    except Exception:
        pass
    return None


def crawl_once(delta_writer=None):
    """Executes a single ping sweep across all nodes and records to JSON and Delta Lake."""
    current_time = time.time()
    dt_now = datetime.datetime.fromtimestamp(current_time, tz=datetime.timezone.utc)
    telemetry = {"timestamp": current_time, "nodes": {}}
    delta_records = []

    for name, ip in NODES.items():
        latency = get_ping(ip)
        is_online = latency is not None
        status = "ONLINE" if is_online else "OFFLINE"
        
        telemetry["nodes"][name] = {
            "ip": ip,
            "latency": latency if is_online else "--",
            "status": status
        }

        delta_records.append({
            "timestamp": dt_now,
            "node_name": name,
            "ip_address": ip,
            "latency_ms": latency if is_online else None,
            "status": status,
            "transport": "TAILSCALE" if ip.startswith("100.") else "LOCAL_LAN",
            "jitter_ms": 0.0,
            "packet_loss_pct": 0.0 if is_online else 100.0,
        })

    # Update legacy JSON file atomically
    tmp_file = TRENDS_FILE + ".tmp"
    with open(tmp_file, "w") as f:
        json.dump(telemetry, f, indent=2)
    os.rename(tmp_file, TRENDS_FILE)

    # Stream to Delta Lake table if writer active
    if delta_writer is not None:
        try:
            delta_writer.write(delta_records, mode="append")
        except Exception as e:
            print(f"[WARN] Failed to append to Delta Lake table: {e}", file=sys.stderr)

    return telemetry, delta_records


def run_crawler(delta_uri=DEFAULT_DELTA_URI, interval=2.0, once=False):
    print(f"Starting Mesh Telemetry Crawler... Writing to {TRENDS_FILE}")
    delta_writer = None
    if DELTA_ENGINE_AVAILABLE and delta_uri:
        try:
            delta_writer = DeltaDatasetWriter(
                table_uri=delta_uri,
                schema=MESH_TELEMETRY_ARROW_SCHEMA,
                mode="append",
                schema_mode="merge",
            )
            print(f"Streaming ACID telemetry to Delta Lake table at: {delta_uri}")
        except Exception as e:
            print(f"[WARN] Could not initialize DeltaDatasetWriter ({e}), continuing in JSON-only mode.")

    if once:
        telemetry, delta_records = crawl_once(delta_writer)
        print(f"Completed single crawl sweep: {len(telemetry['nodes'])} nodes surveyed.")
        return

    while True:
        crawl_once(delta_writer)
        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mesh Telemetry Crawler with Delta Lake streaming")
    parser.add_argument("--once", action="store_true", help="Run a single crawl sweep and exit")
    parser.add_argument("--interval", type=float, default=2.0, help="Sweep interval in seconds")
    parser.add_argument("--delta-table-uri", type=str, default=DEFAULT_DELTA_URI, help="Delta Lake table path")
    args = parser.parse_args()

    run_crawler(delta_uri=args.delta_table_uri, interval=args.interval, once=args.once)

