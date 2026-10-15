#!/usr/bin/env python3
"""
================================================================================
Antigravity ◄───► Local Qwen AI Bi-Directional Bridge Server (Port 18803) (2026)
================================================================================
Subsystem: 05_agents_and_swarms/antigravity_qwen_bridge_server.py
Lauburu Mesh Ecosystem — Inter-Agent Co-Programming & Shared Memory Daemon

Enables:
  1. Continue / Copilot / Qwen AI to call Antigravity directly via HTTP REST.
  2. Antigravity to query local Qwen MoE 80B / 3.8 Max on :8083 without chat lag.
  3. Shared file-based IPC (.agents/state/inbox/ & .agents/state/outbox/).
  4. 24/7 LoRA recording of all inter-agent co-programming decisions.
================================================================================
"""

import os
import sys
import json
import time
import socket
import urllib.request
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

REPO = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
INBOX_DIR = REPO / ".agents/state/inbox"
OUTBOX_DIR = REPO / ".agents/state/outbox"
SHARED_MEM_FILE = REPO / ".agents/state/shared_memory.json"
LORA_FILE = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl")

INBOX_DIR.mkdir(parents=True, exist_ok=True)
OUTBOX_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [Antigravity-Qwen-Bridge] %(message)s")
log = logging.getLogger("AntigravityQwenBridge")

PORT = 18803
LOCAL_QWEN_URL = "http://127.0.0.1:8083/v1/chat/completions"

class BridgeHTTPHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, data: Dict[str, Any]):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        now = time.time()
        if self.path in ("/health", "/"):
            # Check Qwen :8083 status
            qwen_online = False
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.2)
                qwen_online = (s.connect_ex(('127.0.0.1', 8083)) == 0)
                s.close()
            except Exception:
                pass

            data = {
                "service": "Antigravity ◄───► Local Qwen Co-Programming Bridge",
                "status": "ONLINE",
                "port": PORT,
                "qwen_moe_80b_endpoint": "http://127.0.0.1:8083/v1",
                "qwen_online": qwen_online,
                "inbox_tasks_count": len(list(INBOX_DIR.glob("*.json"))),
                "outbox_results_count": len(list(OUTBOX_DIR.glob("*.json"))),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            self._send_json(200, data)

        elif self.path.startswith("/api/antigravity/poll_results"):
            # Return recent outbox results
            results = []
            for f in sorted(OUTBOX_DIR.glob("*.json"), reverse=True)[:10]:
                try:
                    with open(f) as fp:
                        results.append(json.load(fp))
                except Exception:
                    continue
            self._send_json(200, {"results": results, "count": len(results)})

        else:
            self._send_json(404, {"error": "Not Found", "path": self.path})

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8")
        try:
            payload = json.loads(body) if body else {}
        except Exception:
            payload = {"raw_text": body}

        if self.path == "/api/antigravity/dispatch_task":
            # Task from Qwen/Continue -> Antigravity Inbox
            task_id = f"task_{int(time.time()*1000)}"
            task_data = {
                "task_id": task_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "sender": payload.get("sender", "Local_Qwen_Copilot"),
                "task": payload.get("task", ""),
                "priority": payload.get("priority", "HIGH"),
                "context": payload.get("context", {}),
                "status": "QUEUED"
            }
            
            task_file = INBOX_DIR / f"{task_id}.json"
            with open(task_file, "w") as fp:
                json.dump(task_data, fp, indent=2)

            log.info(f"📥 Received task from Qwen: '{task_data['task'][:60]}...' -> {task_file.name}")
            
            # Record to LoRA
            with open(LORA_FILE, "a") as fp:
                fp.write(json.dumps({"timestamp": task_data["timestamp"], "category": "inter_agent_task_dispatch", "data": task_data}) + "\n")

            self._send_json(200, {
                "success": True,
                "task_id": task_id,
                "message": "Task queued in Antigravity inbox successfully",
                "inbox_path": str(task_file)
            })

        elif self.path == "/api/qwen/query":
            # Query local Qwen models with plane partition awareness
            plane = payload.get("plane", "normal").strip().lower()
            prompt = payload.get("prompt", "")
            requested_model = payload.get("model", "")
            
            # Plane determination and target endpoint
            if plane == "abliterated":
                target_url = "http://127.0.0.1:8083/v1/chat/completions"
                model_name = requested_model or "Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf"
                default_system = "You are the Local Qwen 3.8 Max Abliterated Adversarial Red Team Lead."
            else:
                plane = "normal"
                # If specifically targeting MoE ring, port 8082; otherwise master orchestrator port 8081
                if "moe" in requested_model.lower() or "prima" in requested_model.lower():
                    target_url = "http://127.0.0.1:8082/v1/chat/completions"
                    model_name = requested_model or "Qwen_Qwen3-Next-80B-A3B-Instruct"
                else:
                    target_url = "http://127.0.0.1:8081/v1/chat/completions"
                    model_name = requested_model or "qwen2.5-coder-7b-instruct-q4_k_m.gguf"
                default_system = "You are the Local Qwen 3.8 Standard Master AI Orchestrator."

            qwen_payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": payload.get("system", default_system)},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": payload.get("max_tokens", 512),
                "temperature": payload.get("temperature", 0.2)
            }
            try:
                req = urllib.request.Request(target_url, data=json.dumps(qwen_payload).encode("utf-8"), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    data["plane"] = plane
                    data["target_url"] = target_url
                    self._send_json(200, data)
            except Exception as e:
                self._send_json(500, {"error": str(e), "plane": plane, "target_url": target_url, "hint": f"Ensure server is running on {target_url}"})

        else:
            self._send_json(404, {"error": "Endpoint not found", "path": self.path})

def run_server():
    server = HTTPServer(("0.0.0.0", PORT), BridgeHTTPHandler)
    log.info(f"🚀 Antigravity ◄───► Qwen Bridge Daemon running on http://127.0.0.1:{PORT}")
    server.serve_forever()

if __name__ == "__main__":
    run_server()
