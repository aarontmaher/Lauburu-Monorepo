import asyncio
import os
import time
import json
import logging
import httpx
from typing import AsyncGenerator, Dict, Any, Optional

from .base_bridge import BaseInferenceBridge

logger = logging.getLogger("JulienBridge")


class JulienBridge(BaseInferenceBridge):
    """Bridge for Julien Ultra Plan API."""

    def __init__(self, model_name: str = "julien-ultra-300", **kwargs):
        super().__init__(**kwargs)
        self.model_name = model_name
        self._connected: bool = False
        self.latency_ms: float = 0.0

    def get_engine_name(self) -> str:
        return "julien"

    def get_display_name(self) -> str:
        return f"Julien API ({self.model_name})"

    def is_connected(self) -> bool:
        return bool(os.getenv("JULIEN_API_KEY"))

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

        api_key = os.getenv("JULIEN_API_KEY")
        cf_account = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        cf_gateway = os.getenv("CLOUDFLARE_GATEWAY_ID")

        if not api_key:
            yield "SYSTEM: To use Julien Ultra Plan, please type /key_julien <your_api_key>.\n"
            self._is_generating = False
            return

        endpoints = []
        if cf_account and cf_gateway:
            endpoints.append(f"https://gateway.ai.cloudflare.com/v1/{cf_account}/{cf_gateway}/openai/chat/completions")
        endpoints.append("https://api.julien.ai/v1/chat/completions")

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "max_tokens": max_tokens or 512,
            "temperature": temperature if temperature is not None else 0.7,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
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
                                    choices = data.get("choices", [])
                                    if choices and "delta" in choices[0] and "content" in choices[0]["delta"]:
                                        content = choices[0]["delta"]["content"]
                                        if content:
                                            token_emitted = True
                                            yield content
                                except Exception:
                                    pass
                break
            except Exception as e:
                last_exception = e
                if token_emitted:
                    logger.warning(f"Julien stream interrupted mid-stream on {url}: {e}")
                    break
                logger.info(f"Julien endpoint {url} failed ({e}), attempting failover...")

        self.latency_ms = (time.perf_counter() - t0) * 1000.0
        self._is_generating = False

        if not token_emitted and last_exception is not None and not self._generation_cancelled:
            yield f"\n[red]Julien API Error: {str(last_exception)}[/red]"

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
        return f"[JULIEN: ACTIVE ({self.model_name})]"
