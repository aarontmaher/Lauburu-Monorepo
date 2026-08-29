"""
llama.cpp GGML-RPC & REST Inference Bridge
Version: 2.0.0-LIVE-PROXY

Routes through the Lauburu Unified AI Proxy on port 8080.
Falls back to direct port 8083 (Qwen2.5-Coder-7B) if proxy is down.
NO mock token generation — honest error reporting only.
"""

import os
import time
import json
import socket
import logging
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Callable, Dict, Any, List, Optional

from .base_bridge import BaseInferenceBridge

logger = logging.getLogger("LlamaRpcInferenceBridge")


def _load_env_once():
    """Load ~/.env and monorepo .env if not already loaded."""
    for p in [Path.home() / ".env", Path(__file__).parents[4] / ".env"]:
        try:
            if p.exists():
                for line in p.read_text().splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, _, v = line.partition("=")
                        os.environ.setdefault(k.strip(), v.strip())
        except Exception:
            pass

_load_env_once()


class LlamaRpcInferenceBridge(BaseInferenceBridge):
    """
    Inference Bridge for llama.cpp models via the Lauburu Unified AI Proxy.

    Primary:  http://127.0.0.1:8080/v1/chat/completions  (proxy, model=auto)
    Fallback: http://127.0.0.1:8083/v1/chat/completions  (Qwen2.5-Coder-7B direct)
    """

    PRIMARY_PROXY = ("127.0.0.1", 8080, "auto")
    DIRECT_FALLBACKS = [
        ("127.0.0.1", 8085, "local/qwen-abliterated"),
        ("127.0.0.1", 8083, "local/qwen"),
        ("127.0.0.1", 8082, "local/mistral"),
    ]

    def __init__(
        self,
        master_host: str = "127.0.0.1",
        master_port: int = 8080,
        rpc_port: int = 50052,
        sharding_strategy: str = "-ts 28,28,24",
        model_name: str = "auto",
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
        self.rpc_port = rpc_port
        self.sharding_strategy = sharding_strategy
        self.model_name = model_name
        self._connected: bool = False
        self.latency_ms: float = 0.0
        self._active_endpoint: Optional[tuple] = None  # (host, port, model)

    def get_engine_name(self) -> str:
        return "llama_rpc"

    def get_display_name(self) -> str:
        if self._active_endpoint:
            return f"🦙 LOCAL ({self._active_endpoint[2]} :{self._active_endpoint[1]})"
        return "🦙 LOCAL (auto)"

    def is_connected(self) -> bool:
        return self._connected

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

    async def _find_live_endpoint(self) -> Optional[tuple]:
        """
        Try proxy first, then direct fallbacks.
        Returns (host, port, model_id) for the first healthy endpoint.
        """
        ph, pp, pm = self.PRIMARY_PROXY
        if await self._probe_port(ph, pp):
            # Verify proxy is serving (not just port open)
            try:
                import httpx
                async with httpx.AsyncClient(timeout=httpx.Timeout(1.0)) as c:
                    r = await c.get(f"http://{ph}:{pp}/health")
                    if r.status_code == 200:
                        return (ph, pp, pm)
            except Exception:
                pass

        # Proxy down — try direct llama-server ports
        for host, port, model in self.DIRECT_FALLBACKS:
            if await self._probe_port(host, port):
                try:
                    import httpx
                    async with httpx.AsyncClient(timeout=httpx.Timeout(1.0)) as c:
                        r = await c.get(f"http://{host}:{port}/health")
                        if r.status_code == 200 and r.json().get("status") == "ok":
                            return (host, port, model)
                except Exception:
                    pass

        return None

    async def connect(self, timeout: Optional[float] = None) -> bool:
        t0 = time.perf_counter()
        ep = await self._find_live_endpoint()
        self._connected = ep is not None
        self._active_endpoint = ep
        self.latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        if ep:
            logger.info(f"LlamaRpcBridge connected → {ep[0]}:{ep[1]} model={ep[2]} ({self.latency_ms}ms)")
        else:
            logger.warning("LlamaRpcBridge: no live local endpoint found")
        return self._connected

    async def stream_generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream tokens from live local model via proxy or direct endpoint.
        No mock fallback — if no model is live, yields a clear status message.
        """
        self._is_generating = True
        self._generation_cancelled = False
        self._current_task = asyncio.current_task()
        t0 = time.perf_counter()
        token_count = 0

        try:
            import httpx

            # Find live endpoint (cached from last connect, or re-probe)
            if not self._active_endpoint:
                ep = await self._find_live_endpoint()
                self._active_endpoint = ep
                self._connected = ep is not None

            if not self._active_endpoint:
                yield "⚠️  No local model is live. Start llama-server or switch to [cf/llama] (Cloudflare free).\n"
                yield "    Run: /Users/aaron/.local/bin/llama-server -m /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/qwen2.5-coder-7b-instruct-q4_k_m.gguf --port 8083 -ngl 99 -c 8192\n"
                return

            host, port, model_id = self._active_endpoint

            # If a specific model has been selected via /model command, use it
            # Otherwise fall back to the endpoint's auto-routed model
            resolved_model = self.model_name if self.model_name not in ("auto", "kimi_tandem_titan") else model_id

            url = f"http://{host}:{port}/v1/chat/completions"
            payload = {
                "model": resolved_model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
                "max_tokens": max_tokens or 512,
                "temperature": temperature if temperature is not None else 0.7,
            }

            timeout_cfg = httpx.Timeout(connect=3.0, read=60.0, write=5.0, pool=5.0)
            async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                async with client.stream("POST", url, json=payload) as resp:
                    if resp.status_code == 503:
                        # Model still loading
                        yield f"⏳ Model loading on :{port}... Try [cf/llama] in the meantime.\n"
                        self._active_endpoint = None  # Re-probe next time
                        return
                    if resp.status_code != 200:
                        err = await resp.aread()
                        yield f"❌ Endpoint {url} returned {resp.status_code}: {err.decode()[:200]}\n"
                        return

                    async for line in resp.aiter_lines():
                        if self._generation_cancelled:
                            break
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                # Handle both OpenAI format and error chunks
                                if "error" in chunk:
                                    yield f"❌ {chunk['error'].get('message', str(chunk['error']))}\n"
                                    return
                                content = chunk["choices"][0]["delta"].get("content", "")
                                if content:
                                    token_count += 1
                                    self.total_tokens_generated += 1
                                    yield content
                                    await asyncio.sleep(0.005)  # Micro-yield for smooth UI
                            except (KeyError, json.JSONDecodeError):
                                continue

        except asyncio.CancelledError:
            self._generation_cancelled = True
            logger.info("LlamaRpcInferenceBridge: stream cancelled")
            raise
        except Exception as e:
            logger.error(f"LlamaRpcInferenceBridge stream error: {e}")
            yield f"\n❌ Stream error: {e}\n"
        finally:
            self._is_generating = False
            self.last_generation_time_ms = (time.perf_counter() - t0) * 1000.0

    def get_status(self) -> Dict[str, Any]:
        ep = self._active_endpoint
        return {
            "engine_name": self.get_engine_name(),
            "display_name": self.get_display_name(),
            "is_connected": self._connected,
            "active_endpoint": f"{ep[0]}:{ep[1]}" if ep else "none",
            "active_model": ep[2] if ep else "none",
            "master_port": self.master_port,
            "rpc_port": self.rpc_port,
            "sharding_strategy": self.sharding_strategy,
            "latency_ms": self.latency_ms,
            "status_badge": self.get_status_badge(),
            "total_tokens_generated": self.total_tokens_generated,
            "last_generation_time_ms": round(self.last_generation_time_ms, 2),
        }

    def get_status_badge(self) -> str:
        if self._connected and self._active_endpoint:
            h, p, m = self._active_endpoint
            return f"[LOCAL:{p} {m.upper()}]"
        return "[LOCAL: OFFLINE]"
