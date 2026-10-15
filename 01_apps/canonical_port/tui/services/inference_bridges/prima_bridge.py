"""
prima.cpp Pipelined-Ring Parallelism (PRP) Inference Bridge
Version: 3.1.0-CANONICAL-DEFAULT
Subsystem: 01_apps/canonical_port/tui/services/inference_bridges/prima_bridge.py

Canonical Default AI Sharding Engine Bridge over 10Gbps Thunderbolt 4 DMA.
Routes to the Triumvirate Models:
- Port 8082: Qwen 3.8 Max (Sovereign Master Local Orchestrator)
- Port 8083: Qwen 3.8 Max 27B Abliterated (Devil's Advocate / Red Team)
- Port 8085: Kimi Tandem Titan (Context & Multimodal Specialist)
- Port 8081: Qwen 2.5 Coder 7B (Subordinate Syntax Fallback)
"""

import os
import time
import json
import socket
import logging
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Callable, Dict, Any, List, Optional, Tuple

try:
    from .base_bridge import BaseInferenceBridge
except ImportError:
    from tui.services.inference_bridges.base_bridge import BaseInferenceBridge

logger = logging.getLogger("PrimaInferenceBridge")


class PrimaInferenceBridge(BaseInferenceBridge):
    """
    Canonical Default Distributed AI Sharding Bridge using prima.cpp
    Pipelined-Ring Parallelism (PRP) over 10Gbps Thunderbolt 4 DMA.
    """

    PRIMA_TRIUMVIRATE = [
        ("127.0.0.1", 8082, "qwen_38_max", "Master Orchestrator"),
        ("127.0.0.1", 8083, "qwen_38_max_abliterated", "Devil's Advocate"),
        ("127.0.0.1", 8085, "kimi_tandem_titan", "Context Specialist"),
    ]
    FALLBACK_RPC = ("127.0.0.1", 8081, "qwen2.5-coder-7b", "Syntax Subordinate")

    def __init__(
        self,
        master_host: str = "127.0.0.1",
        master_port: int = 8082,
        tb4_bridge_ip: str = "169.254.187.138",
        s2s_client: Optional[Any] = None,
        voice_io_manager: Optional[Any] = None,
        on_token: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[str], None]] = None,
        on_code_snippet: Optional[Callable[[str, str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(
            s2s_client=s2s_client,
            voice_io_manager=voice_io_manager,
            on_token=on_token,
            on_complete=on_complete,
            on_code_snippet=on_code_snippet,
            on_error=on_error,
        )
        self.master_host = master_host
        self.master_port = master_port
        self.tb4_bridge_ip = tb4_bridge_ip
        self.tb4_rtt_ms = 0.28
        self._target_model = "qwen_38_max"
        self._connected: bool = False
        self.latency_ms: float = 0.0
        self._active_endpoint: Optional[Tuple[str, int, str, str]] = None

    def get_engine_name(self) -> str:
        return "prima"

    def get_display_name(self) -> str:
        if self._active_endpoint:
            return f"⚡ PRIMA.CPP ({self._active_endpoint[2]} :{self._active_endpoint[1]})"
        return "⚡ PRIMA.CPP (PRP Ring Master)"

    def is_connected(self) -> bool:
        return self._connected

    def set_target_model(self, model_name: str) -> None:
        self._target_model = model_name

    def _probe_port_sync(self, host: str, port: int, timeout: float = 0.4) -> bool:
        """TCP connect probe with fast timeout."""
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (OSError, ConnectionRefusedError, socket.timeout):
            return False

    async def _probe_port(self, host: str, port: int, timeout: float = 0.4) -> bool:
        """Async TCP probe."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def _find_live_endpoint(self) -> Optional[Tuple[str, int, str, str]]:
        """
        Probe triumvirate endpoints in order of priority:
        1. Target model if specified
        2. Qwen 3.8 Max (8082)
        3. Qwen 3.8 Max Abliterated (8083)
        4. Kimi Tandem Titan (8085)
        5. Fallback Qwen 2.5 Coder (8081)
        """
        candidates = list(self.PRIMA_TRIUMVIRATE)
        if "abliterated" in self._target_model.lower():
            candidates = [c for c in self.PRIMA_TRIUMVIRATE if c[1] == 8083] + [c for c in self.PRIMA_TRIUMVIRATE if c[1] != 8083]
        elif "kimi" in self._target_model.lower():
            candidates = [c for c in self.PRIMA_TRIUMVIRATE if c[1] == 8085] + [c for c in self.PRIMA_TRIUMVIRATE if c[1] != 8085]

        for host, port, m_id, role in candidates:
            if await self._probe_port(host, port):
                return (host, port, m_id, role)

        if await self._probe_port(self.FALLBACK_RPC[0], self.FALLBACK_RPC[1]):
            return (self.FALLBACK_RPC[0], self.FALLBACK_RPC[1], self.FALLBACK_RPC[2], self.FALLBACK_RPC[3])

        return None

    async def connect(self, timeout: Optional[float] = None) -> bool:
        t0 = time.perf_counter()
        ep = await self._find_live_endpoint()
        self._connected = ep is not None
        self._active_endpoint = ep
        self.latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        if ep:
            logger.info(f"PrimaInferenceBridge connected → {ep[0]}:{ep[1]} model={ep[2]} role={ep[3]} ({self.latency_ms}ms)")
        else:
            logger.info("PrimaInferenceBridge: Standby state (no live local PRP socket currently listening)")
        return self._connected

    def check_health(self) -> Dict[str, Any]:
        """Probes live health across all prima.cpp triumvirate ports."""
        t0 = time.perf_counter()
        triumvirate_status = {}
        any_online = False

        for host, port, m_id, role in self.PRIMA_TRIUMVIRATE:
            online = self._probe_port_sync(host, port)
            if online:
                any_online = True
            triumvirate_status[m_id] = {
                "port": port,
                "role": role,
                "online": online
            }

        fallback_online = self._probe_port_sync(self.FALLBACK_RPC[0], self.FALLBACK_RPC[1])
        rtt_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "status": "HEALTHY" if any_online else ("DEGRADED" if fallback_online else "STANDBY"),
            "engine": "prima.cpp Pipelined-Ring Parallelism (PRP)",
            "is_default_sharding_engine": True,
            "tb4_bridge_ip": self.tb4_bridge_ip,
            "tb4_rtt_ms": self.tb4_rtt_ms,
            "triumvirate": triumvirate_status,
            "fallback_rpc_8081": fallback_online,
            "probe_latency_ms": round(rtt_ms, 2)
        }

    async def stream_generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream tokens from live local prima.cpp PRP ring.
        """
        self._is_generating = True
        self._generation_cancelled = False
        self._current_task = asyncio.current_task()
        t0 = time.perf_counter()
        token_count = 0

        try:
            if not self._active_endpoint:
                ep = await self._find_live_endpoint()
                self._active_endpoint = ep
                self._connected = ep is not None

            if not self._connected or not self._active_endpoint:
                yield "⚠️ [prima.cpp PRP: Standby mode - waiting for triumvirate runtime]"
                return

            host, port, model_id, _ = self._active_endpoint
            url = f"http://{host}:{port}/v1/chat/completions"
            payload = {
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens or 512,
                "temperature": temperature if temperature is not None else 0.2,
                "stream": True,
            }

            try:
                import httpx
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream("POST", url, json=payload) as resp:
                        if resp.status_code != 200:
                            yield f"⚠️ [prima.cpp error {resp.status_code} on port {port}]"
                            return
                        async for line in resp.aiter_lines():
                            if self._generation_cancelled:
                                break
                            if line.startswith("data: "):
                                chunk_data = line[6:].strip()
                                if chunk_data == "[DONE]":
                                    break
                                try:
                                    d = json.loads(chunk_data)
                                    delta = d["choices"][0]["delta"].get("content", "")
                                    if delta:
                                        token_count += 1
                                        self.total_tokens_generated += 1
                                        if self.on_token:
                                            self.on_token(delta)
                                        yield delta
                                        await asyncio.sleep(0.002)
                                except Exception:
                                    continue
            except asyncio.CancelledError:
                self._generation_cancelled = True
                logger.info("PrimaInferenceBridge: stream cancelled")
                raise
            except Exception as e:
                err_msg = f"⚠️ [prima.cpp connection error on port {port}: {e}]"
                if self.on_error:
                    self.on_error(err_msg)
                yield err_msg
        finally:
            self._is_generating = False
            self.last_generation_time_ms = (time.perf_counter() - t0) * 1000.0

    def get_status(self) -> Dict[str, Any]:
        ep = self._active_endpoint
        return {
            "engine_name": self.get_engine_name(),
            "display_name": self.get_display_name(),
            "is_connected": self._connected,
            "is_default_sharding_engine": True,
            "active_endpoint": f"{ep[0]}:{ep[1]}" if ep else "none",
            "active_model": ep[2] if ep else "none",
            "active_role": ep[3] if ep else "none",
            "master_port": self.master_port,
            "tb4_bridge_ip": self.tb4_bridge_ip,
            "tb4_rtt_ms": self.tb4_rtt_ms,
            "latency_ms": self.latency_ms,
            "status_badge": self.get_status_badge(),
            "total_tokens_generated": self.total_tokens_generated,
            "last_generation_time_ms": round(self.last_generation_time_ms, 2),
        }

    def get_status_badge(self) -> str:
        if self._connected and self._active_endpoint:
            h, p, m, role = self._active_endpoint
            return f"[PRIMA:{p} {m.upper()}]"
        return "[PRIMA: PRP STANDBY]"
