#!/usr/bin/env python3
"""
Lauburu Unified AI Proxy — Port 8080
OpenAI-compatible single-port router for all local models + free cloud APIs.

Routes:
  model=local/qwen      → llama-server :8083 (Qwen2.5-Coder-7B, always live)
  model=local/gpt-oss   → llama-server :8081 (GPT-OSS 20B, needs warm-up)
  model=local/kimi      → llama-server :8084
  model=local/deepseek  → llama-server :8085
  model=cf/llama        → Cloudflare Workers AI @cf/meta/llama-3.1-8b-instruct (free)
  model=cf/qwen         → Cloudflare Workers AI @cf/qwen/qwen1.5-14b-chat-awq (free)
  model=auto            → First live local port, fallback to Cloudflare

Usage:
  python3 lauburu_ai_proxy.py
  # Then use http://127.0.0.1:8080/v1/chat/completions everywhere
"""

import os
import json
import asyncio
import logging
import httpx
from pathlib import Path
from typing import AsyncGenerator, Optional

# Load .env files (prefer ~/.env, then monorepo .env)
def _load_env():
    for p in [Path.home() / ".env", Path(__file__).parents[1] / ".env"]:
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    v = v.strip().strip('"').strip("'")  # Strip surrounding quotes
                    os.environ.setdefault(k.strip(), v)

_load_env()

try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.responses import StreamingResponse, JSONResponse
    import uvicorn
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn[standard]", "httpx", "-q"])
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.responses import StreamingResponse, JSONResponse
    import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("LauburuAIProxy")

app = FastAPI(title="Lauburu Unified AI Proxy", version="1.0.0")

# ─────────────────────────────────────────────────────────────────────────────
# Model routing table
# ─────────────────────────────────────────────────────────────────────────────

LOCAL_MODELS: dict = {
    # ── Local llama-server ports (Mac Mini) ──────────────────────────────────
    "local/qwen":        {"host": "127.0.0.1", "port": 8083, "display": "Qwen2.5-Coder-7B Q4_K_M"},
    "local/mistral":     {"host": "127.0.0.1", "port": 8082, "display": "Mistral-Nemo-12B Q4_K_M"},
    "local/nemotron":    {"host": "127.0.0.1", "port": 8084, "display": "Nemotron-70B Q4_K_M (RPC)"},
    "local/qwen27b":     {"host": "127.0.0.1", "port": 8085, "display": "Qwen3.8-27B Abliterated Q4_K_XL"},
    "local/gpt-oss":     {"host": "127.0.0.1", "port": 8081, "display": "GPT-OSS 20B MXFP4"},
    # ── Pixel 10 Pro (Tailscale 100.73.38.87) remote model ──────────────────
    "local/pixel":       {"host": "100.73.38.87", "port": 8087, "display": "Pixel Qwen2.5-Coder-14B Q3 (Tensor G5)"},
    "pixel":             {"host": "100.73.38.87", "port": 8087, "display": "Pixel Qwen2.5-14B"},
    # ── Short aliases ────────────────────────────────────────────────────────
    "qwen":          {"host": "127.0.0.1", "port": 8083, "display": "Qwen2.5-Coder-7B"},
    "mistral":       {"host": "127.0.0.1", "port": 8082, "display": "Mistral-Nemo-12B"},
    "nemotron":      {"host": "127.0.0.1", "port": 8084, "display": "Nemotron-70B"},
    "qwen27b":       {"host": "127.0.0.1", "port": 8085, "display": "Qwen3.8-27B Abliterated"},
    "coder":         {"host": "127.0.0.1", "port": 8083, "display": "Qwen2.5-Coder-7B"},
}

CF_MODELS: dict = {
    # ── Cloudflare Workers AI (free tier, 10K req/day) ───────────────────────
    "cf/llama":      "@cf/meta/llama-3.1-8b-instruct",
    "cf/llama70":    "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    "cf/qwen":       "@cf/qwen/qwen1.5-14b-chat-awq",
    "cf/mistral":    "@cf/mistral/mistral-7b-instruct-v0.2",
    "cf/deepseek":   "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b",
    "cloudflare":    "@cf/meta/llama-3.1-8b-instruct",
}

# ── HuggingFace Inference API (free tier, ~1K req/day) ───────────────────────
HF_MODELS: dict = {
    "hf/qwen":       "Qwen/Qwen2.5-72B-Instruct",
    "hf/mistral":    "mistralai/Mistral-7B-Instruct-v0.3",
    "hf/llama":      "meta-llama/Meta-Llama-3.1-8B-Instruct",
    "hf/deepseek":   "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
    "hf/phi":        "microsoft/Phi-3.5-mini-instruct",
}

# ── Google Gemini (free tier: 15 RPM / 1M tokens/day on Flash) ───────────────
GEMINI_MODELS: dict = {
    "gemini/flash":  "gemini-2.0-flash",
    "gemini/flash8": "gemini-2.0-flash-8b",       # cheapest / fastest
    "gemini/pro":    "gemini-2.5-pro",
    "gemini":        "gemini-2.0-flash",            # default alias
}

TIMEOUT = httpx.Timeout(connect=3.0, read=60.0, write=10.0, pool=10.0)


# ─────────────────────────────────────────────────────────────────────────────
# Health probe
# ─────────────────────────────────────────────────────────────────────────────

async def _probe_local(host: str, port: int) -> bool:
    """Non-blocking TCP port probe."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=0.5
        )
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False


async def _get_live_local_port() -> Optional[dict]:
    """Return the first healthy local model config."""
    priority = ["local/qwen", "local/gpt-oss", "local/kimi", "local/deepseek"]
    for key in priority:
        cfg = LOCAL_MODELS.get(key)
        if cfg and await _probe_local(cfg["host"], cfg["port"]):
            # Also confirm it's ready (not loading)
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(1.0)) as c:
                    r = await c.get(f"http://{cfg['host']}:{cfg['port']}/health")
                    if r.status_code == 200 and r.json().get("status") == "ok":
                        return {**cfg, "model_key": key}
            except Exception:
                pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Local llama-server streaming proxy
# ─────────────────────────────────────────────────────────────────────────────

async def _stream_local(host: str, port: int, body: dict) -> AsyncGenerator[bytes, None]:
    """Proxy SSE stream from local llama-server."""
    url = f"http://{host}:{port}/v1/chat/completions"
    body["stream"] = True
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        async with client.stream("POST", url, json=body) as resp:
            if resp.status_code != 200:
                error_body = await resp.aread()
                raise HTTPException(status_code=resp.status_code, detail=error_body.decode())
            async for line in resp.aiter_lines():
                if line:
                    yield (line + "\n\n").encode()


async def _complete_local(host: str, port: int, body: dict) -> dict:
    """Non-streaming completion from local llama-server."""
    url = f"http://{host}:{port}/v1/chat/completions"
    body["stream"] = False
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(url, json=body)
        r.raise_for_status()
        return r.json()


# ─────────────────────────────────────────────────────────────────────────────
# Cloudflare Workers AI streaming proxy
# ─────────────────────────────────────────────────────────────────────────────

async def _stream_cloudflare(cf_model: str, body: dict) -> AsyncGenerator[bytes, None]:
    """Stream from Cloudflare Workers AI free tier."""
    api_key = os.getenv("CLOUDFLARE_API_KEY", "")
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
    gateway_id = os.getenv("CLOUDFLARE_GATEWAY_ID", "")
    email = os.getenv("CLOUDFLARE_EMAIL", os.getenv("CF_EMAIL", ""))

    if not api_key or not account_id:
        err = json.dumps({"error": {"message": "CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_KEY not set in ~/.env", "type": "auth_error", "code": 401}})
        yield f"data: {err}\n\ndata: [DONE]\n\n".encode()
        return

    # Detect auth mode:
    # Global API Key = 37-char hex, requires X-Auth-Email + X-Auth-Key
    # API Token      = longer alphanumeric, uses Bearer
    is_global_key = len(api_key) == 37 or (len(api_key) == 64 and api_key.isalnum() and api_key == api_key.lower())
    if is_global_key and email:
        headers = {
            "X-Auth-Email": email,
            "X-Auth-Key": api_key,
            "Content-Type": "application/json",
        }
    else:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    # Use AI Gateway if available (has caching & analytics), else direct
    if gateway_id:
        url = f"https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/workers-ai/{cf_model}"
    else:
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{cf_model}"

    messages = body.get("messages", [])
    cf_payload = {
        "messages": messages,
        "stream": True,
        "max_tokens": body.get("max_tokens", 512),
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        async with client.stream("POST", url, json=cf_payload, headers=headers) as resp:
            if resp.status_code != 200:
                err_body = await resp.aread()
                try:
                    err_json = json.loads(err_body)
                    detail = err_json.get("errors", [{"message": err_body.decode()}])[0]
                except Exception:
                    detail = {"message": err_body.decode()}
                err = json.dumps({"error": {"message": detail.get("message", "CF error"), "type": "cf_error", "code": resp.status_code}})
                yield f"data: {err}\n\ndata: [DONE]\n\n".encode()
                return

            # Cloudflare streams SSE data: {...} lines
            # Convert to OpenAI-compatible SSE format
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    raw = line[6:].strip()
                    if raw == "[DONE]":
                        yield b"data: [DONE]\n\n"
                        return
                    try:
                        cf_chunk = json.loads(raw)
                        # CF format: {"response": "token"}  or {"choices": [...]}
                        if "response" in cf_chunk:
                            token = cf_chunk["response"]
                        elif "choices" in cf_chunk:
                            token = cf_chunk["choices"][0].get("delta", {}).get("content", "")
                        else:
                            continue
                        # Wrap in OpenAI SSE format
                        oai_chunk = {
                            "id": "cf-proxy",
                            "object": "chat.completion.chunk",
                            "choices": [{"delta": {"content": token}, "index": 0, "finish_reason": None}]
                        }
                        yield f"data: {json.dumps(oai_chunk)}\n\n".encode()
                    except Exception:
                        continue

    yield b"data: [DONE]\n\n"


# ─────────────────────────────────────────────────────────────────────────────
# HuggingFace Inference API (free tier)
# ─────────────────────────────────────────────────────────────────────────────

async def _stream_huggingface(hf_model: str, body: dict) -> AsyncGenerator[bytes, None]:
    """Stream from HuggingFace Inference API free tier (OpenAI-compatible endpoint)."""
    hf_token = os.getenv("HUGGINGFACE_TOKEN", os.getenv("HF_TOKEN", ""))
    url = f"https://api-inference.huggingface.co/models/{hf_model}/v1/chat/completions"

    headers = {"Content-Type": "application/json"}
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    payload = {
        "model": hf_model,
        "messages": body.get("messages", []),
        "stream": True,
        "max_tokens": body.get("max_tokens", 512),
        "temperature": body.get("temperature", 0.7),
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                if resp.status_code == 401:
                    err = json.dumps({"error": {"message": "HF_TOKEN not set or invalid. Set HUGGINGFACE_TOKEN in ~/.env", "type": "auth_error", "code": 401}})
                    yield f"data: {err}\n\ndata: [DONE]\n\n".encode()
                    return
                if resp.status_code != 200:
                    err_body = await resp.aread()
                    err = json.dumps({"error": {"message": err_body.decode()[:200], "type": "hf_error", "code": resp.status_code}})
                    yield f"data: {err}\n\ndata: [DONE]\n\n".encode()
                    return
                # HF returns OpenAI-compatible SSE — pass through directly
                async for line in resp.aiter_lines():
                    if line:
                        yield (line + "\n\n").encode()
        except Exception as e:
            err = json.dumps({"error": {"message": str(e), "type": "hf_connection_error"}})
            yield f"data: {err}\n\ndata: [DONE]\n\n".encode()

    yield b"data: [DONE]\n\n"


# ─────────────────────────────────────────────────────────────────────────────
# Google Gemini API (free tier: 15 RPM / 1M TPD on Flash)
# ─────────────────────────────────────────────────────────────────────────────

async def _stream_gemini(gemini_model: str, body: dict) -> AsyncGenerator[bytes, None]:
    """Stream from Google Gemini API using the OpenAI-compatible endpoint."""
    gemini_key = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    if not gemini_key:
        err = json.dumps({"error": {"message": "GEMINI_API_KEY not set in ~/.env", "type": "auth_error", "code": 401}})
        yield f"data: {err}\n\ndata: [DONE]\n\n".encode()
        return

    # Gemini OpenAI-compat endpoint
    url = f"https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    headers = {
        "Authorization": f"Bearer {gemini_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": gemini_model,
        "messages": body.get("messages", []),
        "stream": True,
        "max_tokens": body.get("max_tokens", 512),
        "temperature": body.get("temperature", 0.7),
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    err_body = await resp.aread()
                    err = json.dumps({"error": {"message": err_body.decode()[:200], "type": "gemini_error", "code": resp.status_code}})
                    yield f"data: {err}\n\ndata: [DONE]\n\n".encode()
                    return
                # Gemini OpenAI-compat SSE — pass through directly
                async for line in resp.aiter_lines():
                    if line:
                        yield (line + "\n\n").encode()
        except Exception as e:
            err = json.dumps({"error": {"message": str(e), "type": "gemini_connection_error"}})
            yield f"data: {err}\n\ndata: [DONE]\n\n".encode()

    yield b"data: [DONE]\n\n"


# ─────────────────────────────────────────────────────────────────────────────
# Route resolver
# ─────────────────────────────────────────────────────────────────────────────

async def _resolve_route(model: str) -> dict:
    """Return routing dict: {type: 'local'|'cf'|'hf'|'gemini', ...config}"""
    model = (model or "auto").lower().strip()

    if model == "auto":
        # Priority: local qwen27b → local qwen → local mistral → hf/phi (no token needed) → cf/llama
        priority = ["local/qwen27b", "local/qwen", "local/mistral", "local/nemotron"]
        for key in priority:
            cfg = LOCAL_MODELS.get(key)
            if cfg and await _probe_local(cfg["host"], cfg["port"]):
                try:
                    async with httpx.AsyncClient(timeout=httpx.Timeout(1.0)) as c:
                        r = await c.get(f"http://{cfg['host']}:{cfg['port']}/health")
                        if r.status_code == 200 and r.json().get("status") == "ok":
                            return {"type": "local", **cfg, "model_key": key}
                except Exception:
                    pass
        # Try Gemini free tier
        if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
            return {"type": "gemini", "gemini_model": "gemini-2.0-flash", "display": "Gemini 2.0 Flash (free)"}
        # Try HF free tier
        if os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HF_TOKEN"):
            return {"type": "hf", "hf_model": HF_MODELS["hf/phi"], "display": "HF Phi-3.5-mini (free)"}
        # Final fallback: Cloudflare
        return {"type": "cf", "cf_model": CF_MODELS["cf/llama"], "display": "Cloudflare Llama-3.1-8B (free)"}

    if model in LOCAL_MODELS:
        cfg = LOCAL_MODELS[model]
        if await _probe_local(cfg["host"], cfg["port"]):
            return {"type": "local", **cfg, "model_key": model}
        raise HTTPException(status_code=503, detail=f"Local model '{model}' not ready on :{cfg['port']}")

    if model in CF_MODELS:
        return {"type": "cf", "cf_model": CF_MODELS[model], "display": f"Cloudflare {model}"}

    if model in HF_MODELS:
        return {"type": "hf", "hf_model": HF_MODELS[model], "display": f"HuggingFace {model}"}

    if model in GEMINI_MODELS:
        return {"type": "gemini", "gemini_model": GEMINI_MODELS[model], "display": f"Gemini {model}"}

    raise HTTPException(
        status_code=400,
        detail=f"Unknown model '{model}'. Valid: {list(LOCAL_MODELS.keys()) + list(CF_MODELS.keys()) + list(HF_MODELS.keys()) + list(GEMINI_MODELS.keys()) + ['auto']}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "lauburu-ai-proxy", "port": 8080}


@app.get("/v1/models")
async def list_models():
    """Return all available models, flagging which local ones are live."""
    models = []
    for key, cfg in LOCAL_MODELS.items():
        if key.startswith("local/"):
            live = await _probe_local(cfg["host"], cfg["port"])
            models.append({
                "id": key,
                "object": "model",
                "owned_by": "local-llama-server",
                "status": "ready" if live else "loading",
                "display": cfg["display"],
                "port": cfg["port"],
            })
    for key, cf_model in CF_MODELS.items():
        if "/" in key:
            models.append({"id": key, "object": "model", "owned_by": "cloudflare-workers-ai",
                           "status": "ready", "display": f"CF: {cf_model}"})
    for key, hf_model in HF_MODELS.items():
        models.append({"id": key, "object": "model", "owned_by": "huggingface-inference-api",
                       "status": "ready", "display": f"HF: {hf_model}"})
    for key, g_model in GEMINI_MODELS.items():
        if "/" in key:
            models.append({"id": key, "object": "model", "owned_by": "google-gemini",
                           "status": "ready", "display": f"Gemini: {g_model}"})
    return {"object": "list", "data": models}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    model = body.get("model", "auto")
    stream = body.get("stream", False)

    route = await _resolve_route(model)
    logger.info(f"Routing '{model}' → {route['type']}: {route.get('display', '')}")

    if route["type"] == "local":
        host, port = route["host"], route["port"]
        if stream:
            return StreamingResponse(
                _stream_local(host, port, body),
                media_type="text/event-stream",
                headers={"X-Routed-To": f"local:{port}", "X-Model": route.get("display", "")}
            )
        result = await _complete_local(host, port, body)
        return JSONResponse(result)

    elif route["type"] == "cf":
        return StreamingResponse(
            _stream_cloudflare(route["cf_model"], body),
            media_type="text/event-stream",
            headers={"X-Routed-To": "cloudflare-workers-ai", "X-Model": route["cf_model"]}
        )

    elif route["type"] == "hf":
        return StreamingResponse(
            _stream_huggingface(route["hf_model"], body),
            media_type="text/event-stream",
            headers={"X-Routed-To": "huggingface-inference-api", "X-Model": route["hf_model"]}
        )

    elif route["type"] == "gemini":
        gemini_model = route["gemini_model"]
        return StreamingResponse(
            _stream_gemini(gemini_model, body),
            media_type="text/event-stream",
            headers={"X-Routed-To": "google-gemini", "X-Model": gemini_model}
        )

    raise HTTPException(status_code=500, detail=f"Unhandled route type: {route.get('type')}")


@app.get("/v1/proxy/status")
async def proxy_status():
    """Live status of all backends."""
    status = {}
    for key, cfg in LOCAL_MODELS.items():
        if key.startswith("local/"):
            live = await _probe_local(cfg["host"], cfg["port"])
            if live:
                try:
                    async with httpx.AsyncClient(timeout=httpx.Timeout(1.0)) as c:
                        r = await c.get(f"http://{cfg['host']}:{cfg['port']}/health")
                        ready = r.json().get("status") == "ok"
                except Exception:
                    ready = False
            else:
                ready = False
            status[key] = {"live": live, "ready": ready, "port": cfg["port"], "display": cfg["display"]}

    cf_ok = bool(os.getenv("CLOUDFLARE_ACCOUNT_ID") and os.getenv("CLOUDFLARE_API_KEY"))
    for key in CF_MODELS:
        if "/" in key:
            status[key] = {"live": cf_ok, "ready": cf_ok, "type": "cloud-cf"}

    hf_ok = bool(os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HF_TOKEN"))
    for key in HF_MODELS:
        status[key] = {"live": hf_ok, "ready": hf_ok, "type": "cloud-hf-free",
                       "note": "~1K req/day free tier"}

    gemini_ok = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    for key in GEMINI_MODELS:
        if "/" in key:
            status[key] = {"live": gemini_ok, "ready": gemini_ok, "type": "cloud-gemini-free",
                           "note": "15 RPM / 1M TPD free tier"}

    return status


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 Lauburu Unified AI Proxy — http://127.0.0.1:8080")
    print("   /v1/chat/completions  — OpenAI-compatible, use model= to select:")
    print("   local/qwen   → Qwen2.5-Coder-7B (port 8083)")
    print("   local/gpt-oss→ GPT-OSS 20B      (port 8081)")
    print("   cf/llama     → Cloudflare Llama-3.1-8B (free)")
    print("   auto         → Best available local, fallback to CF")
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")
