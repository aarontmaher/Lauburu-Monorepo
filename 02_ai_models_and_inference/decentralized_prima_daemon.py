# -*- coding: utf-8 -*-
"""
Decentralized prima.cpp Self-Healing Mesh Daemon
================================================
Subsystem: 02_ai_models_and_inference/decentralized_prima_daemon.py
Lauburu Mesh Ecosystem — 2026

Runs as the primary Pipelined-Ring Parallelism (PRP) coordinator & self-healing
REST server on Port 8082 on L1 (Mac Mini M4 Pro) and can be executed across all peers.
Provides:
- GET /health -> Live 7-device mesh status & leader lease
- GET /v1/ring_status -> Pipelined-Ring Parallelism link telemetry
- POST /v1/heal -> Autonomous multi-pathway network self-healing
- POST /v1/heartbeat -> Peer heartbeat registration
"""

from __future__ import annotations

import json
import logging
import os
import socket
import sys
import threading
import time
import urllib.request
import urllib.error
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from pathlib import Path
from typing import Any, Dict, Optional


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP server enabling concurrent request execution without deadlocks."""
    daemon_threads = True
    allow_reuse_address = True

# Add subsystem directory to path
_curr_dir = Path(__file__).resolve().parent
if str(_curr_dir) not in sys.path:
    sys.path.insert(0, str(_curr_dir))

from decentralized_prima_mesh_coordinator import DecentralizedPrimaMeshCoordinator
from distributed_mesh_consensus import DistributedMeshConsensus
from decentralized_mesh_healer import DecentralizedMeshHealer
from ipless_rfcomm_ai_shard_bridge import IPLessAIShardOrchestrator

logger = logging.getLogger("DecentralizedPrimaDaemon")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class MeshHealingContext:
    def __init__(self, node_id: str = "L1"):
        self.node_id = node_id
        self.coordinator = DecentralizedPrimaMeshCoordinator()
        self.consensus = DistributedMeshConsensus(current_node_id=node_id)
        self.healer = DecentralizedMeshHealer(current_node_id=node_id)
        self.ipless_orchestrator = IPLessAIShardOrchestrator()
        self.is_running = True


_GLOBAL_CONTEXT = MeshHealingContext(node_id="L1")


class PrimaMeshHTTPHandler(BaseHTTPRequestHandler):
    def address_string(self):
        """Prevent slow DNS PTR lookup for localhost requests."""
        return self.client_address[0]

    def _send_json(self, status: int, data: Dict[str, Any]):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        ctx = _GLOBAL_CONTEXT
        now = time.time()

        if self.path in ("/health", "/"):
            lease = ctx.consensus.acquire_or_renew_lease(current_time=now)
            wan_up = ctx.ipless_orchestrator.is_wan_online()
            tb4_ll_up = ctx.ipless_orchestrator.probe_tb4_link_local("fe80::1082:a3ff:fe9e:ae71%bridge0", 18083)
            data = {
                "service": "Decentralized prima.cpp Self-Healing Mesh Daemon",
                "status": "ONLINE",
                "current_node_id": ctx.node_id,
                "current_leader": lease.leader_node_id,
                "leader_priority": lease.leader_priority,
                "lease_expires_in_sec": round(lease.lease_expires_at - now, 2),
                "pooled_vram_gb": ctx.coordinator.pooled_vram_gb,
                "pooled_cpu_ram_gb": getattr(ctx.coordinator, "pooled_cpu_ram_gb", 0.0),
                "total_ram_gb": ctx.coordinator.total_ram_gb,
                "mesh_nodes_count": len(ctx.coordinator.MESH_TOPOLOGY),
                "wan_gateway_online": wan_up,
                "ipless_tb4_ipv6_link_local_online": tb4_ll_up,
                "internet_drop_resilient": True,
                "timestamp": now,
            }
            self._send_json(200, data)

        elif self.path in ("/v1/ipless/status", "/ipless/status"):
            wan_up = ctx.ipless_orchestrator.is_wan_online()
            tb4_ll_18083 = ctx.ipless_orchestrator.probe_tb4_link_local("fe80::1082:a3ff:fe9e:ae71%bridge0", 18083)
            tb4_ll_50053 = ctx.ipless_orchestrator.probe_tb4_link_local("fe80::1082:a3ff:fe9e:ae71%bridge0", 50053)
            data = {
                "status": "ONLINE",
                "internet_drop_stability_mode": "ACTIVE" if not wan_up else "STANDBY_READY",
                "wan_gateway_192_168_8_1_online": wan_up,
                "tier1_tb4_ipv6_link_local": {
                    "interface": "bridge0",
                    "peer_node": "L8_lauburu",
                    "ipv6_link_local": "fe80::1082:a3ff:fe9e:ae71%bridge0",
                    "shard_inference_port_18083_online": tb4_ll_18083,
                    "ggml_rpc_port_50053_online": tb4_ll_50053,
                    "requires_router_or_dhcp": False,
                },
                "tier2_bluetooth_rfcomm_layer0": {
                    "rfcomm_login_channel": 1,
                    "rfcomm_ai_shard_channel": 2,
                    "l8_bt_mac": "3C:22:FB:4E:9F:BB",
                    "l3_bt_mac": "00:41:0E:14:28:44",
                    "l6_pixel_bt_mac": "30:E0:44:6D:18:EC",
                    "requires_ip_stack": False,
                },
                "tier3_local_metal_sanctuary": {
                    "ports": [8089, 8085],
                    "models": ["qwen2.5-0.5b-instruct-q4_k_m.gguf", "Hermes-3-Llama-3.1-8B.Q4_K_M.gguf"],
                },
                "timestamp": now,
            }
            self._send_json(200, data)

        elif self.path == "/v1/context/ring_buffer_status":
            free_ram = ctx.coordinator.get_host_free_ram_gb()
            data = {
                "active_chunks_in_queue": 0,
                "max_queue_capacity": 8,
                "host_free_ram_gb": round(free_ram, 2),
                "is_sanctuary_safe": free_ram >= 4.8,
                "backpressure_active": free_ram < 4.8,
                "timestamp": now,
            }
            self._send_json(200, data)

        elif self.path == "/v1/ring_status":
            links = ctx.coordinator.compute_ring_topology()
            heavy_sharding = ctx.coordinator.compute_prp_sharded_inference_plan()
            data = {
                "ring_topology": [asdict(l) if hasattr(l, "__dataclass_fields__") else l.__dict__ for l in links],
                "heavy_sharding_plan": heavy_sharding,
                "timestamp": now,
            }
            self._send_json(200, data)

        elif self.path == "/v1/model_distribution":
            dist = ctx.coordinator.compute_self_healing_model_distribution()
            self._send_json(200, dist)

        elif self.path == "/v1/context/shard":
            plan = ctx.coordinator.compute_1b_context_sharding_plan()
            data = {
                "status": "OK",
                "sharding_plan": plan,
                "timestamp": now,
            }
            self._send_json(200, data)

        elif self.path in ("/v1/models", "/models"):
            # Query upstream llama-server for authentic loaded GGUF model properties
            active_model = "qwen2.5-0.5b-instruct-q4_k_m.gguf"
            for port in (8089, 8085, 8090):
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/props", timeout=1.0) as resp:
                        if resp.status == 200:
                            props = json.loads(resp.read().decode("utf-8"))
                            model_path = props.get("default_generation_settings", {}).get("model", "") or props.get("model_path", "")
                            if model_path:
                                active_model = os.path.basename(model_path)
                                break
                except Exception:
                    continue

            models_data = {
                "object": "list",
                "data": [
                    {
                        "id": "mesh-local-proxy",
                        "object": "model",
                        "created": int(now),
                        "owned_by": "lauburu-proxy",
                        "root": active_model,
                        "parent": None,
                        "permission": [],
                        "description": f"Local Inference Proxy (Serving {active_model} via ports 8089/8085 + IP-less TB4/BT Shard)",
                        "architecture": "llama-server Metal Proxy / IP-less Mesh",
                        "context_length": 16384,
                        "ports": [8082, 8089, 8085, 18083],
                    },
                    {
                        "id": active_model,
                        "object": "model",
                        "created": int(now),
                        "owned_by": "llama-server",
                        "root": active_model,
                        "parent": None,
                        "permission": [],
                        "description": f"Active Local GGUF Model ({active_model})",
                        "architecture": "llama-server Metal GPU / Mesh",
                        "context_length": 16384,
                        "ports": [8089, 8085],
                    }
                ]
            }
            self._send_json(200, models_data)

        else:
            self._send_json(404, {"error": "Not Found", "path": self.path})

    def do_POST(self):
        ctx = _GLOBAL_CONTEXT
        now = time.time()
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            payload = {}

        if self.path in ("/v1/ipless/shard", "/ipless/shard"):
            messages = payload.get("messages") or [{"role": "user", "content": payload.get("prompt", "Reply OK.")}]
            max_tokens = int(payload.get("max_tokens", 64))
            simulate_blackout = bool(payload.get("simulate_wan_blackout", True))
            force_tier = payload.get("force_tier")
            res = ctx.ipless_orchestrator.execute_sharded_inference(
                messages=messages,
                max_tokens=max_tokens,
                simulate_wan_blackout=simulate_blackout,
                force_tier=force_tier,
            )
            self._send_json(200 if "choices" in res else 503, res)

        elif self.path in ("/v1/ipless/blackout_test", "/ipless/blackout_test"):
            prompt = str(payload.get("prompt", "Confirm IP-less AI sharding stability across WAN blackout."))
            res = ctx.ipless_orchestrator.run_internet_blackout_stability_benchmark(prompt=prompt)
            self._send_json(200, res)

        elif self.path in ("/v1/context/shard", "/v1/context/stream_chunk"):
            total_tokens = payload.get("total_tokens", 1_000_000_000)
            chunk_size = payload.get("chunk_size", 65536)
            context_chunk = payload.get("context_chunk", "") or payload.get("chunk_data", "")
            chunk_index = payload.get("chunk_index") if payload.get("chunk_index") is not None else payload.get("chunk_id", 0)

            plan = ctx.coordinator.compute_1b_context_sharding_plan(total_tokens=total_tokens, chunk_size=chunk_size)

            data = {
                "status": "ACCEPTED",
                "chunk_index": chunk_index,
                "chunk_id": chunk_index,
                "context_chunk_bytes": len(context_chunk.encode("utf-8")),
                "sharding_plan": plan,
                "timestamp": now,
            }
            self._send_json(200, data)

        elif self.path == "/v1/heal":
            target_node = payload.get("target_node_id", "GW")
            anomaly = payload.get("anomaly_type", "GENERIC_LINK_DEGRADATION")
            metrics = payload.get("metrics", {})

            event = ctx.healer.evaluate_and_heal_anomaly(
                target_node_id=target_node,
                anomaly_type=anomaly,
                metrics=metrics,
            )
            data = {
                "status": "HEALED",
                "event_id": event.event_id,
                "initiator": event.initiating_node_id,
                "target": event.target_node_id,
                "chosen_pathway": event.chosen_pathway,
                "command": event.command_executed,
                "latency_ms": event.inference_latency_ms,
                "lora_recorded": event.lora_recorded,
            }
            self._send_json(200, data)

        elif self.path == "/v1/heartbeat":
            peer_id = payload.get("node_id", "UNKNOWN")
            is_online = payload.get("is_online", True)
            ctx.consensus.record_heartbeat(node_id=peer_id, is_online=is_online)
            self._send_json(200, {"status": "ACK", "node_id": peer_id, "leader": ctx.consensus.elect_leader()})

        elif self.path in ("/v1/chat/completions", "/chat/completions"):
            model_req = str(payload.get("model", "ai")).strip().lower()
            messages = payload.get("messages", [])

            # Explicit IP-less / RFCOMM / TB4 Link-Local request routes directly through IPLessAIShardOrchestrator
            if any(k in model_req for k in ["ipless", "rfcomm", "tb4_ll", "blackout"]):
                force_tier = "bt_rfcomm" if "rfcomm" in model_req else ("tb4_ipv6_ll" if "tb4" in model_req else None)
                res = ctx.ipless_orchestrator.execute_sharded_inference(
                    messages=messages,
                    max_tokens=int(payload.get("max_tokens", 128)),
                    simulate_wan_blackout=True,
                    force_tier=force_tier,
                )
                self._send_json(200 if "choices" in res else 503, res)
                return

            # Universal alias "ai", "default", "master", or empty maps to Sovereign Master Qwen 3.8 Max Abliterated
            if not model_req or model_req in ("ai", "default", "master", "orchestrator"):
                model_req = "ai"

            # 1. Gemma 4 31B (Adversarial Red Team & Dialectic Challenger — excludes overloaded L1a node)
            if any(k in model_req for k in ["gemma", "gemma4", "gemma-4", "gemma_4"]):
                target_model_name = "gemma-4-31b-it"
                candidate_endpoints = [
                    "http://127.0.0.1:8083/v1/chat/completions",
                    "http://10.0.0.8:8083/v1/chat/completions",
                    "http://[fe80::1082:a3ff:fe9e:ae71%bridge0]:18083/v1/chat/completions",
                    "http://192.168.8.127:8083/v1/chat/completions",
                    "http://100.103.212.21:8083/v1/chat/completions",
                    "http://100.101.39.98:8083/v1/chat/completions",
                    "http://127.0.0.1:8085/v1/chat/completions",
                    "http://127.0.0.1:8089/v1/chat/completions",
                ]

            # 2. Subordinate Syntax & Coder Worker
            elif any(k in model_req for k in ["coder", "syntax", "8081", "vl", "qwen-vl"]):
                target_model_name = "qwen2.5-coder-7b"
                candidate_endpoints = [
                    "http://127.0.0.1:8081/v1/chat/completions",
                    "http://127.0.0.1:8089/v1/chat/completions",
                    "http://127.0.0.1:8085/v1/chat/completions",
                    "http://[fe80::1082:a3ff:fe9e:ae71%bridge0]:18083/v1/chat/completions",
                    "http://192.168.8.127:8081/v1/chat/completions",
                    "http://100.103.212.21:8081/v1/chat/completions",
                    "http://100.101.39.98:8081/v1/chat/completions",
                ]

            # 3. Clinical & Biometrics Specialist (:8094 BioMistral-7B, :8092 Gemma 2 2B ECG service on L8)
            elif any(k in model_req for k in ["biomistral", "biometrics", "clinical", "ecg"]):
                target_model_name = "BioMistral-7B.Q4_K_M.gguf"
                candidate_endpoints = [
                    "http://10.0.0.8:8094/v1/chat/completions",
                    "http://10.0.0.8:8092/v1/chat/completions",
                    "http://127.0.0.1:8085/v1/chat/completions",
                    "http://127.0.0.1:8089/v1/chat/completions",
                ]

            # 4. Deliberative Reasoning & Dialectic Debate (DeepSeek-R1 Distill 14B/8B, Qwen 3.8 Max)
            elif any(k in model_req for k in ["deepseek-r1", "r1", "reasoning", "debate", "deliberative"]):
                target_model_name = "DeepSeek-R1-Distill-Llama-8B-Q4_K_M.gguf"
                candidate_endpoints = [
                    "http://10.0.0.8:8093/v1/chat/completions",
                    "http://127.0.0.1:8083/v1/chat/completions",
                    "http://10.0.0.8:8083/v1/chat/completions",
                    "http://127.0.0.1:8085/v1/chat/completions",
                    "http://127.0.0.1:8089/v1/chat/completions",
                ]

            # 5. Edge Function Calling & Structured Tool Routing (Nemotron-Mini 4B SLM)
            elif any(k in model_req for k in ["nemotron", "edge-tool", "tool", "function"]):
                target_model_name = "Nemotron-Mini-4B-Instruct-Q4_K_M.gguf"
                candidate_endpoints = [
                    "http://127.0.0.1:8085/v1/chat/completions",
                    "http://10.0.0.8:8091/v1/chat/completions",
                    "http://127.0.0.1:8089/v1/chat/completions",
                ]

            # 6. E-Commerce & Shopify Merchandising (Llama 3.2 3B / Qwen 2.5 7B)
            elif any(k in model_req for k in ["ecommerce", "shopify", "commerce", "store"]):
                target_model_name = "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
                candidate_endpoints = [
                    "http://10.0.0.8:8083/v1/chat/completions",
                    "http://127.0.0.1:8082/v1/chat/completions",
                    "http://127.0.0.1:8085/v1/chat/completions",
                ]

            # 7. Explicit Edge 8B Local Endpoint (:8085 Hermes-3-Llama-3.1-8B.Q4_K_M.gguf with :8089/:8090 fallback)
            elif any(k in model_req for k in ["hermes", "8085", "8b"]):
                target_model_name = "Hermes-3-Llama-3.1-8B.Q4_K_M.gguf"
                candidate_endpoints = [
                    "http://127.0.0.1:8085/v1/chat/completions",
                    "http://127.0.0.1:8089/v1/chat/completions",
                    "http://[fe80::1082:a3ff:fe9e:ae71%bridge0]:18083/v1/chat/completions",
                    "http://127.0.0.1:8090/v1/chat/completions",
                ]

            # 8. Active Tiny & Edge Local Endpoints (:8089 Qwen2.5-0.5B primary, :8085 Hermes-3-8B failover, TB4 IPv6 LL fallback)
            else:
                target_model_name = "qwen2.5-0.5b-instruct-q4_k_m.gguf"
                candidate_endpoints = [
                    "http://127.0.0.1:8089/v1/chat/completions",
                    "http://127.0.0.1:8085/v1/chat/completions",
                    "http://[fe80::1082:a3ff:fe9e:ae71%bridge0]:18083/v1/chat/completions",
                    "http://127.0.0.1:8090/v1/chat/completions",
                ]

            skip_port = str(self.headers.get("X-Prima-Skip-Port", "")).strip()
            if skip_port and skip_port.isdigit():
                candidate_endpoints = [ep for ep in candidate_endpoints if f":{skip_port}/" not in ep]

            t0 = time.perf_counter()
            forwarded_response = None
            attempted_endpoints = []

            for ep in candidate_endpoints:
                attempted_endpoints.append(ep)
                try:
                    if "[fe80::" in ep:
                        # Use curl -g for scoped IPv6 Link-Local on macOS
                        res = ctx.ipless_orchestrator.dispatch_tb4_link_local(
                            messages=messages,
                            max_tokens=int(payload.get("max_tokens", 128)),
                            temperature=float(payload.get("temperature", 0.2)),
                        )
                        if res and "choices" in res:
                            forwarded_response = res
                            forwarded_response["attempted_endpoints"] = attempted_endpoints
                            break
                        continue

                    ep_default_model = (
                        "qwen2.5-0.5b-instruct-q4_k_m.gguf"
                        if ":8089" in ep
                        else (
                            "Hermes-3-Llama-3.1-8B.Q4_K_M.gguf"
                            if ":8085" in ep
                            else target_model_name
                        )
                    )
                    forwarded_payload = dict(payload)
                    forwarded_payload["model"] = ep_default_model
                    req_data = json.dumps(forwarded_payload).encode("utf-8")
                    req = urllib.request.Request(
                        ep,
                        data=req_data,
                        headers={
                            "Content-Type": "application/json",
                            "Connection": "close",
                            "X-Prima-Forwarded": "true"
                        }
                    )
                    with urllib.request.urlopen(req, timeout=35.0) as resp:
                        if resp.status == 200:
                            raw_body = resp.read().decode("utf-8")
                            forwarded_response = json.loads(raw_body)
                            if forwarded_response and "choices" in forwarded_response:
                                # Return authentic upstream model name without masking (Rule 1 §9)
                                upstream_model = os.path.basename(str(forwarded_response.get("model") or ep_default_model))
                                forwarded_response["model"] = upstream_model
                                forwarded_response["routed_model"] = upstream_model
                                forwarded_response["routed_endpoint"] = ep
                                forwarded_response["attempted_endpoints"] = attempted_endpoints
                                break
                except Exception:
                    continue

            if not (forwarded_response and "choices" in forwarded_response):
                # Final automatic fallback to IP-less Orchestrator (TB4 Link-Local -> BT RFCOMM Ch2 -> Local Sanctuary)
                ipless_res = ctx.ipless_orchestrator.execute_sharded_inference(
                    messages=messages,
                    max_tokens=int(payload.get("max_tokens", 128)),
                    simulate_wan_blackout=True,
                )
                if ipless_res and "choices" in ipless_res:
                    forwarded_response = ipless_res
                    forwarded_response["attempted_endpoints"] = attempted_endpoints + ipless_res.get("attempted_tiers", [])

            if forwarded_response and "choices" in forwarded_response:
                self._send_json(200, forwarded_response)
                return

            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            self._send_json(503, {
                "error": {
                    "message": f"Inference failed: All candidate backend workers for model '{target_model_name}' were unavailable.",
                    "type": "upstream_unavailable",
                    "elapsed_ms": elapsed_ms,
                    "target_model": target_model_name,
                    "attempted_endpoints": attempted_endpoints
                }
            })

        else:
            self._send_json(404, {"error": "Endpoint Not Found", "path": self.path})

    def log_message(self, format, *args):
        # Silent logger for high throughput
        pass


def run_background_watchdog(ctx: MeshHealingContext):
    """Background active maintenance watchdog monitoring router, TB4 IPv6 Link-Local, and Layer-0 BT peers."""
    logger.info("🛡️ Decentralized Mesh Watchdog loop started (WAN-Outage & IP-less Resilient)...")
    while ctx.is_running:
        try:
            wan_up = ctx.ipless_orchestrator.is_wan_online(timeout_s=0.4)
            ctx.consensus.record_heartbeat("GW", is_online=wan_up)
            tb4_ll_up = ctx.ipless_orchestrator.probe_tb4_link_local("fe80::1082:a3ff:fe9e:ae71%bridge0", 18083, timeout_s=0.5)
            ctx.consensus.record_heartbeat("L8", is_online=tb4_ll_up)
            ctx.consensus.record_heartbeat("L1", is_online=True)
            ctx.consensus.acquire_or_renew_lease()
        except Exception as e:
            logger.warning(f"Watchdog exception: {e}")
        time.sleep(3.0)


def start_server(port: int = 8082, node_id: str = "L1"):
    _GLOBAL_CONTEXT.node_id = node_id
    server_address = ("", port)
    httpd = ThreadedHTTPServer(server_address, PrimaMeshHTTPHandler)
    logger.info(f"⚡ Decentralized prima.cpp Self-Healing Mesh Daemon listening on Port {port} (Node: {node_id})")

    # Start background watchdog thread
    watchdog_thread = threading.Thread(target=run_background_watchdog, args=(_GLOBAL_CONTEXT,), daemon=True)
    watchdog_thread.start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        _GLOBAL_CONTEXT.is_running = False
        httpd.server_close()
        logger.info("Daemon stopped.")


if __name__ == "__main__":
    node = sys.argv[1] if len(sys.argv) > 1 else "L1"
    port_num = int(sys.argv[2]) if len(sys.argv) > 2 else 8082
    start_server(port=port_num, node_id=node)

