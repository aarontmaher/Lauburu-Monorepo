"""
02_ai_models_and_inference/sharding_daemon/prima_ring_adapter.py
================================================================
OpenAI-compatible proxy that routes /v1/chat/completions to:
  - Port 8082: prima.cpp PRP ring (primary — Halda ILP, ~13× faster)
  - Port 8081: legacy llama.cpp RPC (fallback — preserved, zero disruption)

Health checks prima.cpp ring on startup and every 30s. Automatically
falls back to port 8081 if the prima ring is unhealthy or unresponsive.
Zero-mock: all health state comes from live HTTP probes.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger("PrimaRingAdapter")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")

# ─── Configuration ────────────────────────────────────────────────────────────

PRIMA_RING_URL    = "http://127.0.0.1:8082"   # prima.cpp PRP master
LEGACY_RPC_URL    = "http://127.0.0.1:8081"   # llama.cpp GGML-RPC
HEALTH_CHECK_SEC  = 30.0
REQUEST_TIMEOUT   = 300.0   # 5 min for long 70B generations
PROXY_PORT        = 8083    # This adapter listens here

# ─── State ───────────────────────────────────────────────────────────────────

class RingState:
    prima_healthy: bool = False
    legacy_healthy: bool = False
    last_check: float = 0.0
    prima_failures: int = 0
    legacy_failures: int = 0
    prima_latency_ms: float = 0.0

_state = RingState()

# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Lauburu prima.cpp Ring Adapter",
    description="OpenAI-compat proxy: prima.cpp PRP (8082) with llama.cpp RPC fallback (8081)",
    version="1.0.0",
)

# ─── Health Checker ───────────────────────────────────────────────────────────

async def probe_endpoint(url: str, timeout: float = 5.0) -> tuple[bool, float]:
    """Probe /health on an endpoint. Returns (is_healthy, latency_ms)."""
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(f"{url}/health")
            latency_ms = (time.monotonic() - t0) * 1000
            if r.status_code == 200:
                return True, latency_ms
            return False, latency_ms
    except Exception as e:
        logger.debug(f"Probe failed for {url}: {e}")
        return False, (time.monotonic() - t0) * 1000


async def health_loop():
    """Background coroutine: probe both endpoints every HEALTH_CHECK_SEC."""
    while True:
        prima_ok, prima_ms = await probe_endpoint(PRIMA_RING_URL)
        legacy_ok, _ = await probe_endpoint(LEGACY_RPC_URL)

        if prima_ok != _state.prima_healthy:
            status = "UP" if prima_ok else "DOWN"
            logger.info(f"prima.cpp ring (8082): {status} (latency={prima_ms:.0f}ms, failures={_state.prima_failures})")

        _state.prima_healthy = prima_ok
        _state.legacy_healthy = legacy_ok
        _state.prima_latency_ms = prima_ms
        _state.last_check = time.time()

        if not prima_ok:
            _state.prima_failures += 1
        else:
            _state.prima_failures = 0

        await asyncio.sleep(HEALTH_CHECK_SEC)


@app.on_event("startup")
async def startup():
    asyncio.create_task(health_loop())
    # Warm probe on startup
    prima_ok, ms = await probe_endpoint(PRIMA_RING_URL, timeout=3.0)
    legacy_ok, _ = await probe_endpoint(LEGACY_RPC_URL, timeout=3.0)
    _state.prima_healthy = prima_ok
    _state.legacy_healthy = legacy_ok
    _state.prima_latency_ms = ms
    _state.last_check = time.time()

    route = "prima.cpp PRP (8082)" if prima_ok else "llama.cpp RPC fallback (8081)"
    logger.info(f"PrimaRingAdapter started. Active route: {route}")
    if prima_ok:
        logger.info(f"prima.cpp ring latency: {ms:.0f}ms")


# ─── Status Endpoint ─────────────────────────────────────────────────────────

@app.get("/prima/status")
async def status():
    """Show current ring health and routing decision."""
    return {
        "prima_ring_healthy": _state.prima_healthy,
        "prima_ring_latency_ms": round(_state.prima_latency_ms, 1),
        "prima_ring_failures": _state.prima_failures,
        "legacy_rpc_healthy": _state.legacy_healthy,
        "active_route": "prima_cpp_8082" if _state.prima_healthy else "llama_cpp_rpc_8081",
        "last_health_check_ago_s": round(time.time() - _state.last_check, 1),
    }


# ─── Proxy Logic ──────────────────────────────────────────────────────────────

def _select_backend() -> str:
    """Route to prima.cpp if healthy, else fall back to legacy llama.cpp RPC."""
    if _state.prima_healthy:
        return PRIMA_RING_URL
    if _state.legacy_healthy:
        logger.warning("prima.cpp ring DOWN — routing to legacy llama.cpp RPC (8081)")
        return LEGACY_RPC_URL
    raise HTTPException(status_code=503, detail="All inference backends unavailable")


async def _proxy_stream(backend_url: str, path: str, body: bytes, headers: dict):
    """Stream-proxy a request to the selected backend."""
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        async with client.stream(
            "POST",
            f"{backend_url}{path}",
            content=body,
            headers={k: v for k, v in headers.items()
                     if k.lower() not in ("host", "content-length")},
        ) as resp:
            async for chunk in resp.aiter_bytes():
                yield chunk


@app.api_route("/v1/{path:path}", methods=["GET", "POST", "DELETE", "PUT"])
async def proxy(path: str, request: Request):
    """Transparent proxy for all OpenAI-compatible endpoints."""
    backend = _select_backend()
    body = await request.body()
    headers = dict(request.headers)

    # For non-streaming requests, return directly
    try:
        body_json = json.loads(body) if body else {}
    except Exception:
        body_json = {}

    is_streaming = body_json.get("stream", False)

    if is_streaming:
        return StreamingResponse(
            _proxy_stream(backend, f"/v1/{path}", body, headers),
            media_type="text/event-stream",
            headers={"X-Prima-Backend": backend, "X-Prima-Healthy": str(_state.prima_healthy)},
        )
    else:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.request(
                method=request.method,
                url=f"{backend}/v1/{path}",
                content=body,
                headers={k: v for k, v in headers.items()
                         if k.lower() not in ("host", "content-length")},
            )
        from fastapi.responses import Response
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            media_type=resp.headers.get("content-type", "application/json"),
            headers={"X-Prima-Backend": backend, "X-Prima-Healthy": str(_state.prima_healthy)},
        )


# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting PrimaRingAdapter on port {PROXY_PORT}")
    logger.info(f"  prima.cpp PRP ring: {PRIMA_RING_URL}")
    logger.info(f"  legacy llama.cpp:   {LEGACY_RPC_URL}")
    uvicorn.run(app, host="0.0.0.0", port=PROXY_PORT, log_level="info")
