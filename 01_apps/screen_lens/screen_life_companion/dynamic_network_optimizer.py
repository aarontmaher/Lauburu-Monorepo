import time
import subprocess
import sqlite3
import json
import logging
import socket
from pathlib import Path
import random
import os
import shutil

logging.basicConfig(level=logging.INFO, format='%(asctime)s [NetOptimizer] %(levelname)s: %(message)s')

DB_PATH = "/Users/aaron/.lauburu/screen_life_companion.sqlite"
STATE_FILE = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/network_state.json")
LORA_DATASET = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl")
BT_PORT = 4005

# Genetic / Self-Evolving Parameters
PARAMS = {
    "ping_timeout_ms": 1000,
    "rtt_threshold_tb4_ms": 5.0,
    "rtt_threshold_lan_ms": 15.0,
    "rtt_threshold_ts_ms": 100.0,
}

# Active Tailscale Overlay Mesh IPs (Zero-Mock empirical resolution)
ACTIVE_TAILSCALE_NODES = {
    "L2_MacBook_Pro": "100.103.212.21",
    "L5_MacBook_Air": "100.121.202.34",
    "L3_Linux_Head": "100.101.39.98",
    "L4_Linux_Tablet": "100.118.79.63",
    "L6_Pixel_10": "100.114.215.68",
    "L7_Samsung": "100.69.56.102"
}

def resolve_mesh_nodes():
    """Dynamically resolves mesh node IPs from local Tailscale status or active overlay map."""
    resolved = dict(ACTIVE_TAILSCALE_NODES)
    ts_bin = shutil.which("tailscale") or "/Applications/Tailscale.app/Contents/MacOS/Tailscale"
    if os.path.exists(ts_bin) or shutil.which("tailscale"):
        try:
            res = subprocess.run([ts_bin, "status", "--json"], capture_output=True, text=True, timeout=2.0)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                peers = data.get("Peer", {})
                for peer in peers.values():
                    h = peer.get("HostName", "").lower()
                    ips = [ip for ip in peer.get("TailscaleIPs", []) if ":" not in ip]
                    if not ips:
                        continue
                    ip = ips[0]
                    if "pixel" in h:
                        resolved["L6_Pixel_10"] = ip
                    elif "tablet" in h:
                        resolved["L4_Linux_Tablet"] = ip
                    elif "samsung" in h:
                        resolved["L7_Samsung"] = ip
                    elif "mac-pro" in h:
                        resolved["L2_MacBook_Pro"] = ip
                    elif "macbook" in h:
                        resolved["L5_MacBook_Air"] = ip
                    elif "debian" in h or "linux" in h:
                        resolved["L3_Linux_Head"] = ip
        except Exception:
            pass
    return resolved

MESH_NODES = resolve_mesh_nodes()

def inject_roi_insight(content: str, context: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO life_memories (category, content, context, importance, timestamp)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, ("roi_insight", content, context, "high"))
        task_id = c.lastrowid
        conn.commit()
        conn.close()
        logging.info(f"Injected ROI Insight: {content}")
        
        # Trigger Autonomous Handoff immediately for urgent network repairs
        if "ROI:" in content:
            try:
                roi_val = int(content.split("ROI:")[1].split("/")[0].strip())
                if roi_val >= 90:
                    subprocess.Popen(["python3", "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/bt_ai_handoff_worker.py", str(task_id), content], start_new_session=True)
            except: pass
    except Exception as e:
        logging.error(f"Failed to inject insight: {e}")

def get_bluetooth_control_plane_status():
    """Queries the primary BT management daemon for topology."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect(("127.0.0.1", BT_PORT))
        s.sendall(b"status\n")
        response = b""
        start_t = time.time()
        while time.time() - start_t < 1.0:
            try:
                chunk = s.recv(4096)
                if not chunk: break
                response += chunk
            except socket.timeout:
                break
        s.close()
        return response.decode("utf-8", errors="ignore")
    except Exception as e:
        logging.error(f"BT Control Plane offline: {e}")
        return ""

def evolve_parameters(rtt_results):
    global PARAMS
    for node, rtt in rtt_results.items():
        if rtt is None:
            PARAMS["ping_timeout_ms"] = min(3000, int(PARAMS["ping_timeout_ms"] * 1.1))
        else:
            if "TB4" in node or "MacBook" in node:
                PARAMS["rtt_threshold_tb4_ms"] = (PARAMS["rtt_threshold_tb4_ms"] * 0.9) + (rtt * 0.1)
    try:
        STATE_FILE.write_text(json.dumps(PARAMS, indent=2))
    except: pass

def run_network_loop():
    logging.info("Starting Self-Evolving BT-DEFAULT Network Optimization Monitor...")
    global PARAMS
    if STATE_FILE.exists():
        try: PARAMS = json.loads(STATE_FILE.read_text())
        except: pass
        
    while True:
        # STEP 1: Always check the Bluetooth Control Plane FIRST
        bt_status = get_bluetooth_control_plane_status()
        bt_responsive = len(bt_status) > 10
        
        rtt_results = {}
        dead_ip_nodes = []
        bottleneck_nodes = []
        
        # STEP 2: Evaluate high-speed data plane (IP/TB4)
        for node, ip in resolve_mesh_nodes().items():
            try:
                cmd = ["ping", "-c", "1", "-W", str(PARAMS["ping_timeout_ms"]), ip]
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode == 0:
                    time_line = [l for l in res.stdout.split('\n') if 'time=' in l]
                    if time_line:
                        rtt = float(time_line[0].split('time=')[1].split(' ')[0])
                        rtt_results[node] = rtt
                        if "MacBook" in node: threshold = PARAMS["rtt_threshold_tb4_ms"]
                        elif ip.startswith("192.168."): threshold = PARAMS["rtt_threshold_lan_ms"]
                        else: threshold = PARAMS["rtt_threshold_ts_ms"]
                        if rtt > threshold * 2.0:
                            bottleneck_nodes.append((node, rtt, threshold))
                else:
                    rtt_results[node] = None
                    dead_ip_nodes.append(node)
            except Exception:
                rtt_results[node] = None
                dead_ip_nodes.append(node)
                
        evolve_parameters(rtt_results)
        
        # STEP 3: Actuation via BT Default Paradigm
        if dead_ip_nodes:
            # Reframe logic: They are not "Dead". They are "Sleeping on IP", managed by BT.
            insight = f"[ROI: 99/100] [Network] IP Asleep, executing BT-Heal on {len(dead_ip_nodes)} Nodes: {', '.join(dead_ip_nodes)}"
            context = f"Assignee: AI Swarm. High-speed IP plane offline. Defaulting to Tier-1 Bluetooth PAN / RFCOMM management link to ping and re-awaken."
            inject_roi_insight(insight, context)
            
        for b_node, rtt, thresh in bottleneck_nodes:
            insight = f"[ROI: 85/100] [Network] Reroute IP traffic away from {b_node}"
            context = f"Assignee: AI Swarm. {b_node} IP latency is {rtt:.1f}ms. Shifting back to BT Control Plane state table."
            inject_roi_insight(insight, context)
            
        # Log to LoRA
        try:
            with open(LORA_DATASET, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "timestamp": time.time(),
                    "paradigm": "BT_CONTROL_PLANE_DEFAULT",
                    "bt_control_active": bt_responsive,
                    "ip_telemetry": rtt_results,
                    "mutated_params": PARAMS,
                    "ip_sleeping": dead_ip_nodes
                }) + "\n")
        except: pass
        
        # Check rule #3 / goal exit logic
        if Path("/Users/aaron/.lauburu/GOAL_STOP").exists():
            break
            
        time.sleep(30)

if __name__ == "__main__":
    run_network_loop()
