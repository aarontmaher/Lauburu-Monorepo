import asyncio
import os
import time
import json
import logging
import httpx
from typing import AsyncGenerator, Dict, Any, Optional

from .base_bridge import BaseInferenceBridge

logger = logging.getLogger("GeminiBridge")


class GeminiBridge(BaseInferenceBridge):
    """Bridge for Google Gemini API with Cloudflare AI Gateway routing and direct failover."""

    def __init__(self, model_name: str = "gemini-2.5-flash", **kwargs):
        super().__init__(**kwargs)
        self.model_name = model_name
        self._connected: bool = False
        self.latency_ms: float = 0.0

    def get_engine_name(self) -> str:
        return "gemini"

    def get_display_name(self) -> str:
        return f"Gemini ({self.model_name})"

    def is_connected(self) -> bool:
        return bool(os.getenv("GEMINI_API_KEY"))

    async def connect(self, timeout: Optional[float] = 2.0) -> bool:
        self._connected = bool(os.getenv("GEMINI_API_KEY"))
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

        api_key = os.getenv("GEMINI_API_KEY")
        cf_account = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        cf_gateway = os.getenv("CLOUDFLARE_GATEWAY_ID")

        if not api_key:
            yield "SYSTEM: To use Google Gemini API, please type /key <your_api_key>.\n"
            self._is_generating = False
            return

        # Stage 1: Cloudflare AI Gateway Proxy -> Stage 2: Direct Google AI Studio Fallback
        endpoints = []
        if cf_account and cf_gateway:
            endpoints.append(f"https://gateway.ai.cloudflare.com/v1/{cf_account}/{cf_gateway}/google-ai-studio/v1beta/models/{self.model_name}:streamGenerateContent")
        endpoints.append(f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:streamGenerateContent")

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,  # Secure header auth prevents query param leaks
        }
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens or 512,
                "temperature": temperature if temperature is not None else 0.7
            }
        }

        last_exception = None
        timeout_cfg = httpx.Timeout(connect=3.0, read=30.0, write=5.0, pool=5.0)

        for endpoint_url in endpoints:
            try:
                async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                    async with client.stream("POST", endpoint_url, json=payload, headers=headers) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if self._generation_cancelled:
                                break
                            line = line.strip()
                            if not line or line in ("[", "]", ","):
                                continue
                            if line.startswith(","):
                                line = line[1:].strip()
                            try:
                                data = json.loads(line)
                                for cand in data.get("candidates", []):
                                    for part in cand.get("content", {}).get("parts", []):
                                        txt = part.get("text", "")
                                        if txt:
                                            token_emitted = True
                                            yield txt
                            except json.JSONDecodeError:
                                continue
                # Successful stream completion
                break
            except Exception as e:
                last_exception = e
                if token_emitted:
                    logger.warning(f"Gemini stream interrupted mid-stream on {endpoint_url}: {e}")
                    break
                logger.info(f"Gemini endpoint {endpoint_url} failed ({e}), attempting secondary failover...")

        self.latency_ms = (time.perf_counter() - t0) * 1000.0
        self._is_generating = False

        if not token_emitted and last_exception is not None and not self._generation_cancelled:
            yield f"\n[red]Gemini API Error: {str(last_exception)}[/red]"

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
        return f"[GEMINI: ACTIVE ({self.model_name})]"
