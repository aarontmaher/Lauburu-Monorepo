import asyncio
import os
import time
import json
import logging
import httpx
from typing import AsyncGenerator, Dict, Any, Optional

from .base_bridge import BaseInferenceBridge

logger = logging.getLogger("CloudflareBridge")


class CloudflareBridge(BaseInferenceBridge):
    """Bridge for Cloudflare Workers AI API."""

    def __init__(self, model_name: str = "@cf/meta/llama-3-8b-instruct", **kwargs):
        super().__init__(**kwargs)
        self.model_name = model_name
        self._connected: bool = False
        self.latency_ms: float = 0.0

    def get_engine_name(self) -> str:
        return "cloudflare"

    def get_display_name(self) -> str:
        return f"Cloudflare AI ({self.model_name})"

    def is_connected(self) -> bool:
        return bool(os.getenv("CLOUDFLARE_API_KEY") and os.getenv("CLOUDFLARE_ACCOUNT_ID"))

    async def connect(self, timeout: Optional[float] = 2.0) -> bool:
        self._connected = self.is_connected()
        return self._connected

    async def stream_generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        self._is_generating = True
        self._generation_cancelled = False
        self._current_task = asyncio.current_task()
        t0 = time.perf_counter()
        token_emitted = False

        api_key = os.getenv("CLOUDFLARE_API_KEY")
        account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        gateway_id = os.getenv("CLOUDFLARE_GATEWAY_ID")

        if not api_key or not account_id:
            yield "SYSTEM: To use Cloudflare Workers AI, please type /key_cf <your_api_key> and /account_cf <account_id>.\n"
            self._is_generating = False
            return

        endpoints = []
        if gateway_id:
            endpoints.append(f"https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/workers-ai/{self.model_name}")
        endpoints.append(f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{self.model_name}")

        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "max_tokens": max_tokens or 512,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        last_exception = None
        timeout_cfg = httpx.Timeout(connect=3.0, read=30.0, write=5.0, pool=5.0)

        for url in endpoints:
            try:
                async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                    async with client.stream("POST", url, json=payload, headers=headers) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if self._generation_cancelled:
                                break
                            line = line.strip()
                            if line.startswith("data: ") and line != "data: [DONE]":
                                try:
                                    data = json.loads(line[6:])
                                    if "response" in data and data["response"]:
                                        token_emitted = True
                                        yield data["response"]
                                except Exception:
                                    pass
                break
            except Exception as e:
                last_exception = e
                if token_emitted:
                    logger.warning(f"Cloudflare stream interrupted mid-stream on {url}: {e}")
                    break
                logger.info(f"Cloudflare endpoint {url} failed ({e}), attempting failover...")

        self.latency_ms = (time.perf_counter() - t0) * 1000.0
        self._is_generating = False

        if not token_emitted and last_exception is not None and not self._generation_cancelled:
            yield f"\n[red]Cloudflare API Error: {str(last_exception)}[/red]"

    def get_status(self) -> Dict[str, Any]:
        return {
            "engine_name": self.get_engine_name(),
            "display_name": self.get_display_name(),
            "is_connected": self.is_connected(),
            "model_name": self.model_name,
            "latency_ms": round(self.latency_ms, 2),
            "status_badge": self.get_status_badge(),
        }

    def get_status_badge(self) -> str:
        return f"[CLOUDFLARE: ACTIVE ({self.model_name})]"
