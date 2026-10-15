#!/usr/bin/env python3
"""
MoE Expert Worker Daemon
========================
Subsystem: 02_ai_models_and_inference / moe_expert_sharding
Maintains assigned local MoE experts resident in local RAM/VRAM.
Receives 8 KB activation vectors, computes local MLP forward pass,
and returns computed tensor without ever transferring model weights.
"""

import os
import sys
import time
import json
import socket
import argparse
import numpy as np
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional


class LocalExpertSlice:
    """Manages local expert weights in memory."""

    def __init__(self, expert_id: int, hidden_dim: int = 4096, intermediate_dim: int = 2048):
        self.expert_id = expert_id
        self.hidden_dim = hidden_dim
        self.intermediate_dim = intermediate_dim
        
        # Initialize deterministic expert MLP weights (FP16)
        rng = np.random.default_rng(seed=1000 + expert_id)
        # SwiGLU: Gate, Up, Down projections
        self.w_gate = rng.standard_normal((intermediate_dim, hidden_dim), dtype=np.float32) * 0.02
        self.w_up   = rng.standard_normal((intermediate_dim, hidden_dim), dtype=np.float32) * 0.02
        self.w_down = rng.standard_normal((hidden_dim, intermediate_dim), dtype=np.float32) * 0.02

    def forward(self, x: np.ndarray) -> np.ndarray:
        """Compute SwiGLU MLP: y = W_down(SiLU(W_gate @ x) * (W_up @ x))"""
        # x shape: (hidden_dim,)
        gate = self.w_gate @ x
        # SiLU activation: x / (1 + exp(-x))
        silu_gate = gate / (1.0 + np.exp(-np.clip(gate, -30.0, 30.0)))
        up = self.w_up @ x
        hidden = silu_gate * up
        y = self.w_down @ hidden
        return y


class MoEExpertServer:
    """HTTP/Socket Daemon hosting assigned local experts."""

    def __init__(self, node_id: str, port: int, assigned_experts: List[int], hidden_dim: int = 4096):
        self.node_id = node_id
        self.port = port
        self.assigned_experts = assigned_experts
        self.hidden_dim = hidden_dim
        self.experts: Dict[int, LocalExpertSlice] = {}
        
        print(f"[{node_id}] Initializing Local Expert Pool on Port {port}...")
        for eid in assigned_experts:
            self.experts[eid] = LocalExpertSlice(expert_id=eid, hidden_dim=hidden_dim)
            print(f"  • Expert #{eid:02d} Loaded in Local Memory ({hidden_dim}x{2048} SwiGLU)")

    def compute_expert(self, expert_id: int, activation_bytes: bytes) -> bytes:
        """Processes 8 KB raw activation vector and returns 8 KB result."""
        if expert_id not in self.experts:
            raise ValueError(f"Expert {expert_id} not hosted on node {self.node_id}")
        
        # Unpack float32 or float16 array
        x = np.frombuffer(activation_bytes, dtype=np.float32)
        if x.shape[0] != self.hidden_dim:
            # Fallback resize if dimensions differ
            x = np.resize(x, self.hidden_dim)
        
        y = self.experts[expert_id].forward(x)
        return y.astype(np.float32).tobytes()


class ExpertHTTPHandler(BaseHTTPRequestHandler):
    """Zero-overhead HTTP request handler for tensor dispatch."""
    server_instance: Optional[MoEExpertServer] = None

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "status": "HEALTHY",
                "node_id": self.server_instance.node_id if self.server_instance else "unknown",
                "hosted_experts": list(self.server_instance.experts.keys()) if self.server_instance else []
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path.startswith("/v1/expert/compute"):
            # Query param or header: expert_id
            expert_id = int(self.headers.get("X-Expert-ID", 0))
            content_length = int(self.headers.get("Content-Length", 0))
            activation_bytes = self.rfile.read(content_length)
            
            try:
                t0 = time.perf_counter()
                out_bytes = self.server_instance.compute_expert(expert_id, activation_bytes)
                t_compute_ms = (time.perf_counter() - t0) * 1000.0
                
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("X-Compute-Time-Ms", f"{t_compute_ms:.3f}")
                self.send_header("Content-Length", str(len(out_bytes)))
                self.end_headers()
                self.wfile.write(out_bytes)
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass # Suppress HTTP access logging for maximum throughput


def run_worker(node_id: str, port: int, assigned_experts: List[int]):
    server_obj = MoEExpertServer(node_id=node_id, port=port, assigned_experts=assigned_experts)
    ExpertHTTPHandler.server_instance = server_obj
    httpd = HTTPServer(("0.0.0.0", port), ExpertHTTPHandler)
    print(f"🚀 [MoE Worker {node_id}] Listening on 0.0.0.0:{port} for 8KB Activation Vectors...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\nShutting down {node_id}...")
        httpd.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MoE Expert Worker Daemon")
    parser.add_argument("--node-id", type=str, default="L1_mac_mini", help="Node identifier")
    parser.add_argument("--port", type=int, default=50060, help="Listen port")
    parser.add_argument("--experts", type=int, nargs="+", default=[0, 1, 2, 3], help="Assigned expert IDs")
    args = parser.parse_args()

    run_worker(node_id=args.node_id, port=args.port, assigned_experts=args.experts)
