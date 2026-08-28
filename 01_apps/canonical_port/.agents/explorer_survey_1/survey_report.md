# Comprehensive Investigation Report: Cloudflare AI Gateway Routing & Inference Bridges

**Target Workspace:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port`  
**Investigated Directory:** `tui/services/inference_bridges/` & `tui/services/`  
**Investigating Agent:** `explorer_survey_1`  
**Date:** 2026-08-28  

---

## 1. Executive Summary

A deep code-level audit of the inference bridges and Cloudflare AI Gateway routing implementation in `canonical_port` was conducted. The investigation evaluated all bridge modules (`gemini_bridge.py`, `cloudflare_bridge.py`, `julien_bridge.py`, `llama_bridge.py`, `exo_bridge.py`, `accelerate_bridge.py`, `petals_bridge.py`, and `base_bridge.py`), the central coordinator `UnifiedInferenceRouter` (`tui/services/inference_router.py`), background telemetry in `DynamicLatencyPoller` (`tui/services/latency_poller.py`), and TUI REPL integration.

### Key Findings Overview:
1. **Critical Syntax Errors & Test Collection Failure:** Recent patch scripts injected unescaped newlines into string literals in `gemini_bridge.py`, `cloudflare_bridge.py`, and `julien_bridge.py`, causing Python `SyntaxError: unterminated string literal` across all three files. This immediately breaks pytest collection for the entire test suite.
2. **Security Vulnerability (API Key in URL):** `gemini_bridge.py` passes `GEMINI_API_KEY` in the HTTP query string `?key={api_key}`. This causes the plain-text key to be logged in Cloudflare AI Gateway logs, proxy access logs, and un-sanitized `httpx` exception outputs rendered on the TUI screen.
3. **Zero Intra-Bridge Gateway Fallback:** None of the three bridges (`gemini`, `cloudflare`, `julien`) implement automatic failover to direct provider endpoints if Cloudflare AI Gateway experiences DNS outages, 5xx gateway errors, 429 rate limits, or connection timeouts. They fail fast and terminate the stream.
4. **Router Fallback Suppression Bug:** When Cloudflare AI Gateway fails, bridges catch their internal `httpx` exceptions and `yield` a Rich-formatted red error string instead of raising or returning cleanly. Because `UnifiedInferenceRouter` detects that a token was yielded (`token_yielded = True`), the router's automatic failover to local `llama_rpc` is completely bypassed, trapping the user with an error message instead of resilient local compute.
5. **Router Registration Inconsistencies:** `inference_router.py` does not include `cloudflare` and `julien` in `SUPPORTED_ENGINES`, `ENGINE_DISPLAY_NAMES`, or the default `self.bridges` map. Furthermore, `tui/services/inference_bridges/__init__.py` omits exports for `GeminiBridge`, `CloudflareBridge`, and `JulienBridge`.
6. **Task Cancellation / Barge-In Gap:** `gemini_bridge.py`, `cloudflare_bridge.py`, and `julien_bridge.py` fail to record `self._current_task = asyncio.current_task()`, preventing `BaseInferenceBridge.cancel_generation()` from cleanly cancelling active network requests during user speech barge-in.
7. **Fragile JSON Streaming:** `gemini_bridge.py` uses naive string splitting (`chunk.split('"text": "')`) over raw TCP chunks, causing dropped or corrupted tokens whenever JSON field boundaries or escaped characters are split across network packet buffers.

---

## 2. Bridge Implementations & Architecture Audit

### 2.1 Polymorphic Contract Compliance (`BaseInferenceBridge`)

All bridges inherit from `BaseInferenceBridge` (`tui/services/inference_bridges/base_bridge.py:25-245`). The base class defines the following contract methods:

| Method / Property | Contract Requirement | `llama_rpc` / `exo` / `accelerate` / `petals` | `gemini` | `cloudflare` | `julien` |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `get_engine_name()` | Return unique string ID | Compliant | Compliant (`"gemini"`) | Compliant (`"cloudflare"`) | Compliant (`"julien"`) |
| `get_display_name()` | Return human-readable label | Compliant | Compliant (`"Gemini (...)"`) | Compliant (`"Cloudflare AI (...)"`) | Compliant (`"Julien API (...)"`) |
| `is_connected()` | Return current connection status | Live probe state | Returns `True` (hardcoded) | Returns `True` (hardcoded) | Returns `True` (hardcoded) |
| `connect(timeout)` | Async socket/API verification | Performs live probe / socket check | Checks `bool(env)` only | Checks `bool(env)` only | Checks `bool(env)` only |
| `stream_generate()` | Async generator yielding tokens | Compliant with micro-yields & cancellation | Yields error strings on exception; contains syntax/indentation bugs | Yields error strings on exception; contains syntax/indentation bugs | Yields error strings on exception; contains syntax/indentation bugs |
| `get_status()` | Standardized telemetry dict | Returns full metric dict | Returns partial dict | Returns partial dict | Returns partial dict |
| `get_status_badge()` | UI HUD badge string | Compliant | Compliant | Compliant | Compliant |
| `_current_task` assignment | Required for instant sub-1ms task cancellation | Assigned in `stream_generate` | **Missing** | **Missing** | **Missing** |
| Constructor Callbacks | `on_token`, `on_complete`, `on_code_snippet`, `on_error`, `s2s_client`, `voice_io_manager` | Accepted and forwarded to `super().__init__()` | **Ignored** in `__init__` (only takes `model_name`) | **Ignored** in `__init__` (only takes `model_name`) | **Ignored** in `__init__` (only takes `model_name`) |

### 2.2 Package Exports (`__init__.py`)

In `tui/services/inference_bridges/__init__.py:1-26`:
```python
from .base_bridge import BaseInferenceBridge
from .llama_bridge import LlamaRpcInferenceBridge
from .exo_bridge import ExoInferenceBridge
from .accelerate_bridge import AccelerateInferenceBridge
from .petals_bridge import PetalsInferenceBridge

__all__ = [
    "BaseInferenceBridge",
    "LlamaRpcInferenceBridge",
    "ExoInferenceBridge",
    "AccelerateInferenceBridge",
    "PetalsInferenceBridge",
]
```
**Observation:** `GeminiBridge`, `CloudflareBridge`, and `JulienBridge` are completely omitted from `__init__.py` and `__all__`.

### 2.3 Router Registration & Fallback Imports (`inference_router.py`)

In `tui/services/inference_router.py`:
1. **Fallback Import Block (Lines 36-44):**
   ```python
   except ImportError:
       from tui.services.inference_bridges.base_bridge import BaseInferenceBridge
       from tui.services.inference_bridges.llama_bridge import LlamaRpcInferenceBridge
       from tui.services.inference_bridges.exo_bridge import ExoInferenceBridge
       from tui.services.inference_bridges.accelerate_bridge import AccelerateInferenceBridge
       from tui.services.inference_bridges.petals_bridge import PetalsInferenceBridge
       from tui.services.inference_bridges.gemini_bridge import GeminiBridge
       from tui.services.latency_poller import DynamicLatencyPoller, EngineLatencyMetric
   ```
   Notice `CloudflareBridge` and `JulienBridge` are omitted in the `except ImportError:` block.
2. **Supported Engines List (Lines 54-61):**
   `SUPPORTED_ENGINES = ["auto", "llama_rpc", "exo", "accelerate", "petals", "gemini"]`
   `cloudflare` and `julien` are missing.
3. **Display Names Map (Lines 63-69):**
   `ENGINE_DISPLAY_NAMES` contains only `auto`, `llama_rpc`, `exo`, `accelerate`, `petals`. `gemini`, `cloudflare`, and `julien` are missing.
4. **Default Bridge Instantiation (Lines 118-153):**
   `self.bridges` default dictionary instantiates `llama_rpc`, `exo`, `accelerate`, `petals`, and `gemini`. `cloudflare` and `julien` are missing.

---

## 3. Cloudflare AI Gateway Routing: Construction, Auth & Queries

### 3.1 Endpoint Construction Comparison

Each bridge switches dynamically based on the presence of `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_GATEWAY_ID`:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              CLOUDFLARE AI GATEWAY URL ROUTING                                  │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. Google Gemini Bridge (gemini_bridge.py:55-60)                                                │
│    • Gateway URL:                                                                               │
│      https://gateway.ai.cloudflare.com/v1/{cf_account}/{cf_gateway}/google-ai-studio/v1beta/   │
│      models/{model_name}:streamGenerateContent?key={api_key}                                    │
│    • Direct URL (when Gateway unset):                                                           │
│      https://generativelanguage.googleapis.com/v1beta/models/{model_name}:streamGenerateContent │
│      ?key={api_key}                                                                             │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. Cloudflare Workers AI Bridge (cloudflare_bridge.py:54-59)                                    │
│    • Gateway URL:                                                                               │
│      https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/workers-ai/{model_name}     │
│    • Direct URL (when Gateway unset):                                                           │
│      https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model_name}            │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. Julien OpenAI-Compatible Bridge (julien_bridge.py:55-60)                                     │
│    • Gateway URL:                                                                               │
│      https://gateway.ai.cloudflare.com/v1/{cf_account}/{cf_gateway}/openai/chat/completions     │
│    • Direct URL (when Gateway unset):                                                           │
│      https://api.julien.ai/v1/chat/completions                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Authentication & Request Payload Specification

| Bridge | Auth Mechanism | Headers | Request Payload Structure | Stream Mode |
| :--- | :--- | :--- | :--- | :--- |
| **Gemini** | URL query parameter `?key={api_key}` (**Security Risk**) | `{"Content-Type": "application/json"}` | `{"contents": [{"parts": [{"text": prompt}]}]}` | HTTP chunked transfer |
| **Cloudflare** | HTTP Bearer header `Authorization: Bearer {api_key}` | `{"Authorization": "Bearer ...", "Content-Type": "application/json"}` | `{"messages": [{"role": "user", "content": prompt}], "stream": True}` | Server-Sent Events (`text/event-stream`) |
| **Julien** | HTTP Bearer header `Authorization: Bearer {api_key}` | `{"Authorization": "Bearer ...", "Content-Type": "application/json"}` | `{"model": model_name, "messages": [{"role": "user", "content": prompt}], "stream": True}` | Server-Sent Events (`text/event-stream`) |

### 3.3 Required Environment Variables Matrix

| Environment Variable | Required For | Fallback / Alternative |
| :--- | :--- | :--- |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare Gateway routing across all 3 bridges; Workers AI direct API | Direct endpoint (for Gemini/Julien only) |
| `CLOUDFLARE_GATEWAY_ID` | Enables AI Gateway proxy routing (`gateway.ai.cloudflare.com`) | Routes directly to provider when unset |
| `CLOUDFLARE_API_KEY` | Authentication for Cloudflare Workers AI | Set via `/key_cf <key>` in TUI |
| `GEMINI_API_KEY` | Authentication for Google Gemini (Direct or Gateway) | Set via `/key <key>` in TUI |
| `JULIEN_API_KEY` | Authentication for Julien Ultra Plan | Set via `/key_julien <key>` in TUI |

---

## 4. Fallback Mechanisms & Resilience Analysis

### 4.1 Intra-Bridge Gateway Failure Handling (Gateway Down / 5xx / 429 / DNS)

When `CLOUDFLARE_GATEWAY_ID` is configured, all traffic routes through `https://gateway.ai.cloudflare.com/v1/...`.

#### Scenario 1: Cloudflare Gateway Outage (DNS Failure / Gateway 502 / 504 / 429 / Connection Timeout)
- **Observed Code Behavior:**
  - `gemini_bridge.py:67-86`: `response.raise_for_status()` triggers `httpx.HTTPStatusError` (or `httpx.ConnectError`). It is caught by `except Exception as e:` and yields:
    ```python
    yield f"\n[red]Gemini/Cloudflare Gateway API Error: {str(e)}[/red]"
    ```
  - `cloudflare_bridge.py:72-88`: `response.raise_for_status()` raises an exception, caught by `except Exception as e:` yielding:
    ```python
    yield f"\n[red]Cloudflare API Error: {str(e)}[/red]"
    ```
  - `julien_bridge.py:74-96`: Checks `if response.status_code != 200: yield ...; return`. General exceptions yield `[red]Julien API Error...[/red]`.
- **Verdict:** **NO intra-bridge fallback exists.** The bridge does NOT attempt to retry the request against the direct provider URL (`generativelanguage.googleapis.com`, `api.cloudflare.com`, `api.julien.ai`). It immediately aborts with a red error string.

### 4.2 Router-Level Auto-Fallback Dynamics & The "Suppression Bug"

In `tui/services/inference_router.py:298-333`, `stream_generate` implements automatic fallback for `"auto"` mode:
```python
if target_eng != "llama_rpc" and target_bridge is not None:
    token_yielded = False
    fallback_needed = False
    try:
        async for token in target_bridge.stream_generate(prompt, max_tokens=max_tokens, temperature=temperature):
            token_yielded = True
            yield token
    except asyncio.CancelledError:
        raise
    except Exception as e:
        if token_yielded:
            logger.warning(f"Auto-route stream from '{target_eng}' dropped mid-stream ({e})...")
        else:
            logger.warning(f"Auto-route to '{target_eng}' failed ({e})... Engaging instant offline fallback to llama_rpc.")
            fallback_needed = True

    if fallback_needed and not token_yielded:
        fallback_bridge = self.bridges.get("llama_rpc")
        if fallback_bridge:
            async for token in fallback_bridge.stream_generate(...):
                yield token
```

#### The Fallback Suppression Bug:
1. Because `gemini_bridge.py`, `cloudflare_bridge.py`, and `julien_bridge.py` **catch their own exceptions internally** and execute `yield "[red]...API Error...[/red]"`, `target_bridge.stream_generate` **does not raise an exception**.
2. The router's loop receives the error string as a normal token and sets `token_yielded = True`.
3. The `except Exception as e:` block in the router is never triggered.
4. `fallback_needed` remains `False`, and `not token_yielded` is `False`.
5. **Result:** The router **never triggers fallback to `llama_rpc`**. The user sees only the raw error message, defeating the zero-crash offline resilience guarantee of the Lauburu mesh.

### 4.3 Background Telemetry Poller Impact (`DynamicLatencyPoller`)

In `tui/services/latency_poller.py:110-184`, `measure_engine_ttft` probes engines every 3 seconds:
1. `bridge.is_connected()` returns `True` unconditionally for `gemini`, `cloudflare`, and `julien`.
2. `measure_engine_ttft` calls `bridge.stream_generate(prompt="ping", max_tokens=1)`.
3. When Cloudflare Gateway is down, `stream_generate` yields the error string `"\n[red]...API Error...[/red]"`.
4. `measure_engine_ttft` receives this chunk and marks `token_received = True`, calculating a valid TTFT (e.g. 150ms)!
5. The poller marks `is_available = True` with a low TTFT, causing the auto-router to continuously pick the broken engine as the "fastest" engine.

---

## 5. Token Streaming, Async Cancellation & Concurrency

### 5.1 Streaming Protocol & Parser Analysis

#### 1. Gemini Bridge (`gemini_bridge.py:69-81`):
```python
async for chunk in response.aiter_text():
    if self._generation_cancelled:
        break
    try:
        if '"text": "' in chunk:
            parts = chunk.split('"text": "')
            for p in parts[1:]:
                text_val = p.split('"')[0]
                text_val = text_val.replace('\\n', '\n').replace('\\"', '"')
                yield text_val
    except Exception:
        pass
```
**Defects Identified:**
- **TCP Chunk Boundary Fragmentation:** `httpx.aiter_text()` yields chunks based on TCP packet reception. If the boundary splits the delimiter (e.g. `..."te` in chunk 1, `xt": "hello"...` in chunk 2), the entire token is dropped.
- **Escaped Quote Corruption:** Splitting on `"` causes JSON strings containing escaped quotes (`\"`) to be truncated at the first escaped quote.
- **Unicode Escape Ignored:** `\u003c` or other JSON unicode escapes are not decoded.

#### 2. Cloudflare Bridge (`cloudflare_bridge.py:74-84`):
```python
async for line in response.aiter_lines():
    if self._generation_cancelled:
        break
    if line.startswith("data: ") and line != "data: [DONE]":
        try:
            data = json.loads(line[6:])
            if "response" in data:
                yield data["response"]
        except Exception:
            pass
```
**Assessment:**
- Correctly parses standard SSE lines.
- Omits handling for HTTP 200 error bodies (e.g. `{"success": false, "errors": [...]}`) which are not SSE formatted.

#### 3. Julien Bridge (`julien_bridge.py:81-92`):
```python
async for line in response.aiter_lines():
    if self._generation_cancelled:
        break
    if line.startswith("data: ") and line != "data: [DONE]":
        try:
            data = json.loads(line[6:])
            choices = data.get("choices", [])
            if choices and "delta" in choices[0] and "content" in choices[0]["delta"]:
                yield choices[0]["delta"]["content"]
        except Exception:
            pass
```
**Assessment:**
- Correctly parses OpenAI-compatible delta chunks.
- Line 77 calls `await response.aread()` inside an open stream context on non-200 status, which returns raw bytes representation `b'...'`.

### 5.2 Async Task Cancellation & Barge-In Audit

`BaseInferenceBridge.cancel_generation()` (`base_bridge.py:108-129`) provides sub-1ms stream cancellation:
```python
def cancel_generation(self) -> None:
    self._generation_cancelled = True
    ...
    if self._current_task and not self._current_task.done() and self._current_task is not cur_task:
        self._current_task.cancel()
        self._current_task = None
```
- In `llama_bridge.py:115`, `exo_bridge.py:111`, `accelerate_bridge.py:93`, and `petals_bridge.py:87`, `self._current_task = asyncio.current_task()` is explicitly set.
- In `gemini_bridge.py`, `cloudflare_bridge.py`, and `julien_bridge.py`, **`self._current_task` is NOT assigned**.
- **Impact:** When a user speaks (triggering STT voice barge-in) or switches engines in the TUI, `cancel_generation()` cannot abort the active `httpx` stream task. The task continues consuming network bandwidth and holding HTTP sockets open until the next chunk arrives or the socket times out.

### 5.3 HTTP Client Lifecycle & Connection Pooling

- In `gemini_bridge.py:66`, `cloudflare_bridge.py:71`, and `julien_bridge.py:73`, a new `httpx.AsyncClient()` is created for every single prompt request.
- No shared HTTP connection pool or keep-alive is reused across generation requests.
- No custom timeout is passed (`httpx.AsyncClient()` defaults to 5.0s timeouts). For slow inference streams or initial token latency > 5s, the request will fail with `httpx.ReadTimeout`.

---

## 6. Security & Vulnerability Analysis

### 6.1 API Key Exposure in URL Query Parameters (`GEMINI_API_KEY`)

In `gemini_bridge.py:60`:
```python
url = f"{base_url}/{self.model_name}:streamGenerateContent?key={api_key}"
```
**Security Vulnerabilities:**
1. **Cloudflare Gateway Analytics / Request Logs:** Cloudflare AI Gateway logs the complete request URL by default in its dashboard, exposing the user's plain-text `GEMINI_API_KEY` in Cloudflare's access logs.
2. **Intermediate HTTP Proxy Logs:** Any forward/reverse proxy, firewall, or NAT gateway logs full URLs including query strings.
3. **Exception Message Output:** When `httpx` raises an `HTTPStatusError` (e.g. 400 Bad Request), the default error message format includes the full URL: `Client error '400 Bad Request' for url 'https://gateway.ai.cloudflare.com/...:streamGenerateContent?key=AIzaSy...'.`
4. **TUI Output Leak:** Because `gemini_bridge.py:84-85` outputs `str(e)` to the TUI terminal log widget, the plain-text API key is printed directly on the user's screen.

**Remediation:**
Google AI Studio and Cloudflare AI Gateway support standard HTTP headers:
- Header: `x-goog-api-key: {api_key}`
- URL: `f"{base_url}/{self.model_name}:streamGenerateContent"` (no query parameter)

### 6.2 In-Memory Env Mutation in REPL Commands

In `tui/screens/agi_coding_terminal_screen.py` and `tui/views/agi_coding_terminal_view.py`:
- `/key <key>` executes `os.environ["GEMINI_API_KEY"] = parts[1]`
- `/key_cf <key>` executes `os.environ["CLOUDFLARE_API_KEY"] = parts[1]`
- `/account_cf <id>` executes `os.environ["CLOUDFLARE_ACCOUNT_ID"] = parts[1]`
- `/gateway_cf <id>` executes `os.environ["CLOUDFLARE_GATEWAY_ID"] = parts[1]`
- `/key_julien <key>` executes `os.environ["JULIEN_API_KEY"] = parts[1]`

**Assessment:**
- Mutating `os.environ` is volatile and process-local. It does not persist across restarts unless exported in the user's shell profile.
- Entering keys directly into terminal REPL logs them into `command_history` within the TUI session.

---

## 7. Syntax Errors, Dead Code & Regressions Catalog

The following table provides the exact line-by-line breakdown of defects preventing code execution and unit test passes:

| File | Line Numbers | Issue Description | Severity |
| :--- | :--- | :--- | :--- |
| `gemini_bridge.py` | 46-47 | `yield "SYSTEM: ...\n"` broken into multi-line string literal causing `SyntaxError: unterminated string literal` | **CRITICAL** |
| `gemini_bridge.py` | 77-78 | `text_val.replace('\n', '\n')` unescaped newline causing syntax error | **CRITICAL** |
| `gemini_bridge.py` | 84-85 | `yield f"\n[red]..."` unescaped newline causing syntax error | **CRITICAL** |
| `gemini_bridge.py` | 89 | `            return` indented 12 spaces (Indentation / Dead Code) | **HIGH** |
| `gemini_bridge.py` | 91-110 | Unreachable dead code trying to invoke `google.generativeai` | **MEDIUM** |
| `cloudflare_bridge.py` | 45-46 | `yield "SYSTEM: ...\n"` broken into multi-line string literal causing `SyntaxError` | **CRITICAL** |
| `cloudflare_bridge.py` | 86-87 | `yield f"\n[red]..."` unescaped newline causing syntax error | **CRITICAL** |
| `cloudflare_bridge.py` | 91 | `            return` indented 12 spaces (Indentation / Dead Code) | **HIGH** |
| `cloudflare_bridge.py` | 93-104 | Unreachable dead simulation code | **MEDIUM** |
| `julien_bridge.py` | 45-46 | `yield "SYSTEM: ...\n"` broken into multi-line string literal causing `SyntaxError` | **CRITICAL** |
| `julien_bridge.py` | 76-77 | `yield f"\n[red]..."` unescaped newline causing syntax error | **CRITICAL** |
| `julien_bridge.py` | 94-95 | `yield f"\n[red]..."` unescaped newline causing syntax error | **CRITICAL** |
| `julien_bridge.py` | 99 | `            return` indented 12 spaces (Indentation / Dead Code) | **HIGH** |
| `julien_bridge.py` | 101-111 | Unreachable dead simulation code | **MEDIUM** |
| `inference_router.py` | 54-61 | `SUPPORTED_ENGINES` omits `"cloudflare"`, `"julien"` | **MEDIUM** |
| `inference_router.py` | 63-69 | `ENGINE_DISPLAY_NAMES` omits `"gemini"`, `"cloudflare"`, `"julien"` | **MEDIUM** |
| `inference_router.py` | 118-153 | `self.bridges` default dict omits `"cloudflare"`, `"julien"` | **MEDIUM** |
| `__init__.py` | 13-25 | `__init__.py` does not export `GeminiBridge`, `CloudflareBridge`, `JulienBridge` | **LOW** |

---

## 8. Proposed Refactor & Remediation Plan

To bring the inference bridge subsystem to production-grade resilience and security, the following refactoring steps are proposed:

### 8.1 Proposed Implementation: Secure, Resilient `GeminiBridge`

```python
# PROPOSED REPLACEMENT: tui/services/inference_bridges/gemini_bridge.py
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

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        **kwargs
    ):
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

        api_key = os.getenv("GEMINI_API_KEY")
        cf_account = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        cf_gateway = os.getenv("CLOUDFLARE_GATEWAY_ID")

        if not api_key:
            yield "SYSTEM: To enable Gemini chat, export GEMINI_API_KEY or type /key <key>.\n"
            self._is_generating = False
            return

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens or 512,
                "temperature": temperature if temperature is not None else 0.7
            }
        }

        # Secure Auth Header (prevents API key leakage in URL query logs)
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        }

        urls_to_try = []
        if cf_account and cf_gateway:
            urls_to_try.append(f"https://gateway.ai.cloudflare.com/v1/{cf_account}/{cf_gateway}/google-ai-studio/v1beta/models/{self.model_name}:streamGenerateContent")
        # Direct Google AI Studio fallback
        urls_to_try.append(f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:streamGenerateContent")

        stream_success = False
        last_error = None

        timeout_cfg = httpx.Timeout(connect=5.0, read=30.0, write=5.0, pool=5.0)

        for target_url in urls_to_try:
            try:
                async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                    async with client.stream("POST", target_url, json=payload, headers=headers) as response:
                        response.raise_for_status()
                        async for chunk in response.aiter_text():
                            if self._generation_cancelled:
                                break
                            # Robust JSON buffer parsing
                            lines = chunk.strip().splitlines()
                            for line in lines:
                                line = line.strip().lstrip("[").rstrip(",").rstrip("]")
                                if not line:
                                    continue
                                try:
                                    obj = json.loads(line)
                                    candidates = obj.get("candidates", [])
                                    if candidates:
                                        parts = candidates[0].get("content", {}).get("parts", [])
                                        for p in parts:
                                            txt = p.get("text", "")
                                            if txt:
                                                stream_success = True
                                                yield txt
                                except Exception:
                                    # Fallback simple substring search for partial chunks
                                    if '"text":' in line:
                                        try:
                                            idx = line.find('"text":') + 7
                                            raw_val = json.loads(line[idx:].strip().rstrip("}"))
                                            if raw_val:
                                                stream_success = True
                                                yield raw_val
                                        except Exception:
                                            pass
                if stream_success:
                    break
            except Exception as e:
                last_error = e
                logger.warning(f"Gemini URL '{target_url}' failed: {e}. Trying next fallback...")

        if not stream_success and not self._generation_cancelled:
            self._is_generating = False
            # Re-raise to allow UnifiedInferenceRouter auto-fallback to engage
            raise RuntimeError(f"Gemini generation failed across all gateways: {last_error}")

        self.latency_ms = (time.perf_counter() - t0) * 1000.0
        self._is_generating = False

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
```

### 8.2 Summary of Proposed Architecture Fixes

1. **Fix Syntax & Indentation:** Clean all broken string literals and remove dead simulation code across `gemini_bridge.py`, `cloudflare_bridge.py`, and `julien_bridge.py`.
2. **Implement Dual-Stage Gateway Fallback:** In each bridge, construct a primary URL (Cloudflare Gateway) and a secondary direct provider URL. If the primary fails before yielding tokens, seamlessly retry on the direct provider.
3. **Re-raise on Total Failure:** If all endpoints fail before yielding tokens, raise `RuntimeError` rather than yielding an error string. This allows `UnifiedInferenceRouter` to catch the failure and immediately fallback to local `llama_rpc`.
4. **Header-Based Authentication:** Migrate Gemini API authentication from URL query strings `?key=` to `x-goog-api-key` header to eliminate key leakage in gateway and proxy logs.
5. **Set `_current_task`:** Ensure `self._current_task = asyncio.current_task()` is executed in all bridges for sub-1ms cancellation.
6. **Harmonize Router & Exports:** Update `SUPPORTED_ENGINES`, `ENGINE_DISPLAY_NAMES`, `self.bridges`, and `__init__.py` to fully support `gemini`, `cloudflare`, and `julien`.
