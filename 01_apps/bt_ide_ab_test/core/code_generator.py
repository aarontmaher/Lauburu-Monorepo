"""
Qwen 2.5 Coder Delegation Client for the Lauburu IDE Intelligence Architecture.

Delegates code generation, inline completion, and FIM (Fill-In-the-Middle)
to Qwen 2.5 Coder 7B on Port 8081, with automatic zero-latency fallback to
Port 8083 (Qwen 3.8 Max Master Orchestrator) if Port 8081 is unreachable.
Supports streaming SSE (Server-Sent Events) and non-streaming modes.
"""

import asyncio
from dataclasses import dataclass, field
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union
import httpx

logger = logging.getLogger("code_generator")

PORT_CODER_PRIMARY = 8081
PORT_CODER_FALLBACK = 8083

DEFAULT_PRIMARY_URL = f"http://127.0.0.1:{PORT_CODER_PRIMARY}"
DEFAULT_FALLBACK_URL = f"http://127.0.0.1:{PORT_CODER_FALLBACK}"

PRIMARY_MODEL_ID = "qwen2.5-coder-7b-instruct"
FALLBACK_MODEL_ID = "qwen_38_max_abliterated"


@dataclass
class CodeGenResult:
    """Standard result structure for code generation calls."""
    success: bool
    text: str
    raw_response: Dict[str, Any] = field(default_factory=dict)
    endpoint_used: str = ""
    error: Optional[str] = None


@dataclass
class CodeGenMetrics:
    """Live telemetry metrics for code generation requests."""
    total_requests: int = 0
    primary_success: int = 0
    fallback_success: int = 0
    total_failures: int = 0
    total_tokens_streamed: int = 0
    last_endpoint_used: str = ""
    last_error: Optional[str] = None


class CodeGenerator:
    """
    Client for Qwen 2.5 Coder code generation with Port 8081 -> 8083 fallback
    and Server-Sent Events (SSE) streaming support.
    """

    def __init__(
        self,
        primary_url: str = DEFAULT_PRIMARY_URL,
        fallback_url: str = DEFAULT_FALLBACK_URL,
        primary_model: str = PRIMARY_MODEL_ID,
        fallback_model: str = FALLBACK_MODEL_ID,
        connect_timeout: float = 2.0,
        read_timeout: float = 60.0,
    ):
        self.primary_url = primary_url.rstrip("/")
        self.fallback_url = fallback_url.rstrip("/")
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.metrics = CodeGenMetrics()

    def get_metrics(self) -> Dict[str, Any]:
        """Return snapshot of code generator telemetry."""
        return {
            "total_requests": self.metrics.total_requests,
            "primary_success": self.metrics.primary_success,
            "fallback_success": self.metrics.fallback_success,
            "total_failures": self.metrics.total_failures,
            "total_tokens_streamed": self.metrics.total_tokens_streamed,
            "last_endpoint_used": self.metrics.last_endpoint_used,
            "last_error": self.metrics.last_error,
        }

    @staticmethod
    def format_fim_prompt(prefix: str, suffix: str) -> str:
        """Format Fill-In-The-Middle (FIM) prompt for Qwen / CodeLlama syntax."""
        return f"<|fim_prefix|>{prefix}<|fim_suffix|>{suffix}<|fim_middle|>"

    def _prepare_payload(self, raw_payload: Dict[str, Any], target_model: str) -> Dict[str, Any]:
        """Prepare sanitized payload for target model, stripping tool definitions."""
        payload = dict(raw_payload)
        payload["model"] = target_model
        payload.pop("tools", None)
        payload.pop("functions", None)
        payload.pop("tool_choice", None)
        if "max_tokens" not in payload and "max_completion_tokens" not in payload:
            payload["max_tokens"] = 2048
        return payload

    async def generate_completion(
        self,
        prompt: Union[str, Dict[str, Any]],
        max_tokens: int = 2048,
        stream: bool = False,
        **kwargs
    ) -> CodeGenResult:
        """
        Dedicated single-string or payload completion interface returning CodeGenResult.
        Guarantees zero tool definitions are forwarded to the syntax worker (F2.5).
        """
        self.metrics.total_requests += 1

        if isinstance(prompt, dict):
            req_payload = dict(prompt)
        else:
            req_payload = {
                "prompt": str(prompt),
                "messages": [{"role": "user", "content": str(prompt)}],
                "max_tokens": max_tokens,
            }
        req_payload.update(kwargs)

        timeout = httpx.Timeout(self.read_timeout, connect=self.connect_timeout)

        # 1. Try Primary Endpoint (Port 8081)
        primary_endpoint = f"{self.primary_url}/v1/chat/completions"
        primary_payload = self._prepare_payload(req_payload, self.primary_model)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(primary_endpoint, json=primary_payload)
                if resp.status_code == 200:
                    self.metrics.primary_success += 1
                    self.metrics.last_endpoint_used = primary_endpoint
                    data = resp.json()
                    text = ""
                    choices = data.get("choices", [])
                    if choices:
                        c = choices[0]
                        if "message" in c:
                            text = c["message"].get("content", "")
                        elif "text" in c:
                            text = c.get("text", "")
                    return CodeGenResult(
                        success=True,
                        text=text,
                        raw_response=data,
                        endpoint_used=primary_endpoint,
                    )
        except Exception as e:
            logger.info(f"Primary code endpoint failed: {e}. Falling back to {self.fallback_url}")

        # 2. Fallback to Secondary Endpoint (Port 8083)
        fallback_endpoint = f"{self.fallback_url}/v1/chat/completions"
        fallback_payload = self._prepare_payload(req_payload, self.fallback_model)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(fallback_endpoint, json=fallback_payload)
                if resp.status_code == 200:
                    self.metrics.fallback_success += 1
                    self.metrics.last_endpoint_used = fallback_endpoint
                    data = resp.json()
                    text = ""
                    choices = data.get("choices", [])
                    if choices:
                        c = choices[0]
                        if "message" in c:
                            text = c["message"].get("content", "")
                        elif "text" in c:
                            text = c.get("text", "")
                    return CodeGenResult(
                        success=True,
                        text=text,
                        raw_response=data,
                        endpoint_used=fallback_endpoint,
                    )
                else:
                    self.metrics.total_failures += 1
                    return CodeGenResult(
                        success=False,
                        text="",
                        endpoint_used=fallback_endpoint,
                        error=f"HTTP {resp.status_code}: {resp.text}",
                    )
        except Exception as e:
            self.metrics.total_failures += 1
            self.metrics.last_error = str(e)
            return CodeGenResult(
                success=False,
                text="",
                error=str(e),
            )

    async def generate_chat_completion(
        self,
        payload: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncGenerator[str, None]]:
        """
        Execute chat completion with primary (8081) -> fallback (8083) delegation.
        Accepts dict payload or keyword arguments (e.g. messages=[...]).
        """
        self.metrics.total_requests += 1
        req_payload = dict(payload) if payload else {}
        req_payload.update(kwargs)

        if stream or req_payload.get("stream", False):
            return self._stream_chat_completion(req_payload)
        else:
            return await self._sync_chat_completion(req_payload)

    async def _sync_chat_completion(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Non-streaming chat completion execution."""
        primary_endpoint = f"{self.primary_url}/v1/chat/completions"
        primary_payload = self._prepare_payload(payload, self.primary_model)

        timeout = httpx.Timeout(self.read_timeout, connect=self.connect_timeout)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(primary_endpoint, json=primary_payload)
                if resp.status_code == 200:
                    self.metrics.primary_success += 1
                    self.metrics.last_endpoint_used = primary_endpoint
                    return resp.json()
        except Exception as e:
            logger.info(f"Primary code endpoint unavailable ({e}). Triggering fallback to Port 8083.")

        fallback_endpoint = f"{self.fallback_url}/v1/chat/completions"
        fallback_payload = self._prepare_payload(payload, self.fallback_model)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(fallback_endpoint, json=fallback_payload)
                if resp.status_code == 200:
                    self.metrics.fallback_success += 1
                    self.metrics.last_endpoint_used = fallback_endpoint
                    return resp.json()
                else:
                    error_msg = f"Fallback endpoint returned HTTP {resp.status_code}: {resp.text}"
                    self.metrics.total_failures += 1
                    self.metrics.last_error = error_msg
                    raise httpx.HTTPStatusError(error_msg, request=resp.request, response=resp)
        except Exception as e:
            self.metrics.total_failures += 1
            self.metrics.last_error = str(e)
            logger.error(f"Both primary and fallback endpoints failed: {e}")
            raise

    async def _stream_chat_completion(self, payload: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """Streaming chat completion yielding Server-Sent Events (SSE)."""
        payload = dict(payload)
        payload["stream"] = True

        timeout = httpx.Timeout(self.read_timeout, connect=self.connect_timeout)

        async def stream_from_endpoint(url: str, body: Dict[str, Any]) -> AsyncGenerator[str, None]:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", url, json=body) as response:
                    if response.status_code != 200:
                        err_content = await response.aread()
                        raise httpx.HTTPStatusError(
                            f"HTTP {response.status_code}: {err_content.decode('utf-8', errors='replace')}",
                            request=response.request,
                            response=response
                        )
                    async for line in response.aiter_lines():
                        if line:
                            yield f"{line}\n\n"
                            self.metrics.total_tokens_streamed += 1

        target_url = f"{self.primary_url}/v1/chat/completions"
        target_payload = self._prepare_payload(payload, self.primary_model)

        try:
            async for chunk in stream_from_endpoint(target_url, target_payload):
                yield chunk
            self.metrics.primary_success += 1
            self.metrics.last_endpoint_used = target_url
            return
        except Exception as primary_err:
            logger.warning(f"Streaming failed on primary ({primary_err}). Falling back to {self.fallback_url}")

        fallback_url = f"{self.fallback_url}/v1/chat/completions"
        fallback_payload = self._prepare_payload(payload, self.fallback_model)
        try:
            async for chunk in stream_from_endpoint(fallback_url, fallback_payload):
                yield chunk
            self.metrics.fallback_success += 1
            self.metrics.last_endpoint_used = fallback_url
        except Exception as fb_err:
            self.metrics.total_failures += 1
            self.metrics.last_error = str(fb_err)
            raise fb_err

    async def generate_legacy_completion(
        self,
        payload_or_prompt: Union[str, Dict[str, Any]],
        max_tokens: int = 512,
        stream: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncGenerator[str, None]]:
        """
        Execute /v1/completions (e.g. for FIM autocomplete or legacy tests).
        Tries primary endpoint first directly without pre-flight GET.
        """
        self.metrics.total_requests += 1
        endpoint_path = "/v1/completions"

        if isinstance(payload_or_prompt, str):
            payload = {"prompt": payload_or_prompt, "max_tokens": max_tokens}
        else:
            payload = dict(payload_or_prompt)
            if "max_tokens" not in payload:
                payload["max_tokens"] = max_tokens
        payload.update(kwargs)

        timeout = httpx.Timeout(self.read_timeout, connect=self.connect_timeout)

        # 1. Try primary endpoint first
        primary_endpoint = f"{self.primary_url}{endpoint_path}"
        primary_payload = self._prepare_payload(payload, self.primary_model)

        if stream:
            primary_payload["stream"] = True
            async def stream_legacy() -> AsyncGenerator[str, None]:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    async with client.stream("POST", primary_endpoint, json=primary_payload) as response:
                        if response.status_code != 200:
                            err_content = await response.aread()
                            raise httpx.HTTPStatusError(
                                f"HTTP {response.status_code}: {err_content.decode('utf-8')}",
                                request=response.request,
                                response=response
                            )
                        async for line in response.aiter_lines():
                            if line:
                                yield f"{line}\n\n"
                                self.metrics.total_tokens_streamed += 1
            return stream_legacy()
        else:
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(primary_endpoint, json=primary_payload)
                    if resp.status_code == 200:
                        self.metrics.primary_success += 1
                        self.metrics.last_endpoint_used = primary_endpoint
                        return resp.json()
            except Exception as e:
                logger.info(f"Primary endpoint {primary_endpoint} failed ({e}). Trying fallback.")

            # 2. Fallback to secondary endpoint
            fallback_endpoint = f"{self.fallback_url}{endpoint_path}"
            fallback_payload = self._prepare_payload(payload, self.fallback_model)

            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(fallback_endpoint, json=fallback_payload)
                    if resp.status_code == 200:
                        self.metrics.fallback_success += 1
                        self.metrics.last_endpoint_used = fallback_endpoint
                        return resp.json()
                    else:
                        chat_url = f"{self.fallback_url}/v1/chat/completions"
                        chat_payload = {
                            "model": self.fallback_model,
                            "messages": [{"role": "user", "content": str(fallback_payload.get("prompt", ""))}],
                            "max_tokens": fallback_payload.get("max_tokens", 512),
                        }
                        resp2 = await client.post(chat_url, json=chat_payload)
                        if resp2.status_code == 200:
                            self.metrics.fallback_success += 1
                            self.metrics.last_endpoint_used = chat_url
                            return resp2.json()
                        raise httpx.HTTPStatusError(f"HTTP {resp.status_code}: {resp.text}", request=resp.request, response=resp)
            except Exception as e:
                self.metrics.total_failures += 1
                self.metrics.last_error = str(e)
                raise
