#!/usr/bin/env python3
"""
Lauburu AI Gateway Budget Proxy & Multi-Tier Free API Router
============================================================
Intercepts AI API calls across Cloud & Local providers:
1. Prioritizes Zero-Cost Free Tiers:
   - Google Gemini API Free Tier (Gemini 2.0 Flash / 1.5 Pro)
   - Cloudflare Workers AI Free Tier (10k Neurons/day)
   - Julien / Hugging Face Serverless Inference API
   - Local Hardware Mesh (llama.cpp RPC on Ports 8081-8084)
2. Enforces a hard $1.00 kill-switch for paid fallback endpoints.
3. Automatically falls back to Local Mesh on rate limits (429) or upstream errors.
4. Harvests all interactions into LoRA dataset for continuous 24/7 learning.

Run: uv run python budget_proxy.py
Status: curl http://localhost:9000/status
"""

import asyncio
import json
import os
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
try:
    import tiktoken
except ImportError:
    tiktoken = None
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

# ── Config ────────────────────────────────────────────────────────────────────
BUDGET_LIMIT      = float(os.getenv("BUDGET_LIMIT", "1.00"))
LEDGER_PATH       = Path(__file__).parent / "spend_ledger.json"
LORA_DATASET      = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/api_interactions.jsonl")
CF_ACCOUNT_ID     = os.getenv("CLOUDFLARE_ACCOUNT_ID", "16282271f1eccb56f0b96afed09d21ff")
CF_GATEWAY_SLUG   = os.getenv("CLOUDFLARE_GATEWAY_SLUG", "lauburu-ai-gateway")
CF_GW_BASE        = f"https://gateway.ai.cloudflare.com/v1/{CF_ACCOUNT_ID}/{CF_GATEWAY_SLUG}"
ADMIN_KEY         = os.getenv("ADMIN_KEY", "lauburu-admin-2026")
LOCAL_MESH_URL    = os.getenv("LOCAL_MESH_URL", "http://127.0.0.1:8081/v1")
LOCAL_DEVIL_URL   = os.getenv("LOCAL_DEVIL_URL", "http://127.0.0.1:8083/v1")

# Free Tier Identifiers
FREE_PROVIDERS = {
    "google", "gemini", "cloudflare", "workers-ai", "huggingface", "julien",
    "groq", "openrouter", "mistral", "jina", "pollinations", "cohere",
    "local", "mesh"
}

# Free Tier Models (Calculated as $0.00 cost)
FREE_MODELS_PREFIXES = (
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "@cf/",
    "cf/",
    "hf/",
    "julien/",
    "groq/",
    "openrouter/",
    "mistral/",
    "pollinations/",
    ":free",
    "local/",
    "mesh/",
    "kimi-",
    "qwen-",
    "mistral-nemo",
    "meta-llama-3.1-8b",
    "gpt-oss-20b",
)

# ── Pricing table (per 1M tokens) for Paid Cloud APIs ─────────────────────────
PRICING: dict[str, dict[str, float]] = {
    # Free Tiers ($0.00)
    "gemini-2.0-flash-free":       {"input": 0.00,  "output": 0.00},
    "gemini-1.5-flash-free":       {"input": 0.00,  "output": 0.00},
    "gemini-1.5-pro-free":         {"input": 0.00,  "output": 0.00},
    "cloudflare-free":             {"input": 0.00,  "output": 0.00},
    "huggingface-free":            {"input": 0.00,  "output": 0.00},
    "groq-free":                   {"input": 0.00,  "output": 0.00},
    "openrouter-free":             {"input": 0.00,  "output": 0.00},
    "mistral-free":                {"input": 0.00,  "output": 0.00},
    "pollinations-free":           {"input": 0.00,  "output": 0.00},
    "local-mesh":                  {"input": 0.00,  "output": 0.00},
    # Claude (Paid Fallback)
    "claude-3-5-sonnet-20241022":  {"input": 3.00,  "output": 15.00},
    "claude-3-5-sonnet":           {"input": 3.00,  "output": 15.00},
    "claude-3-5-haiku-20241022":   {"input": 0.80,  "output": 4.00},
    "claude-3-haiku-20240307":     {"input": 0.25,  "output": 1.25},
    "claude-3-opus-20240229":      {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-5":           {"input": 3.00,  "output": 15.00},
    # OpenAI (Paid Fallback)
    "gpt-4o":                      {"input": 2.50,  "output": 10.00},
    "gpt-4o-mini":                 {"input": 0.15,  "output": 0.60},
    "gpt-4-turbo":                 {"input": 10.00, "output": 30.00},
    "o1":                          {"input": 15.00, "output": 60.00},
    "o1-mini":                     {"input": 3.00,  "output": 12.00},
    # Gemini Paid Tier
    "gemini-1.5-pro":              {"input": 1.25,  "output": 5.00},
    "gemini-1.5-flash":            {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash":            {"input": 0.10,  "output": 0.40},
    "gemini-2.5-pro":              {"input": 1.25,  "output": 10.00},
    # Default fallback
    "_default":                    {"input": 5.00,  "output": 20.00},
}

# ── Provider route mapping ─────────────────────────────────────────────────────
PROVIDER_ROUTES: dict[str, str] = {
    "anthropic":    "https://api.anthropic.com",
    "openai":       "https://api.openai.com",
    "google":       "https://generativelanguage.googleapis.com",
    "gemini":       "https://generativelanguage.googleapis.com",
    "cloudflare":   f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai",
    "workers-ai":   f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai",
    "huggingface":  "https://router.huggingface.co/hf-inference/v1",
    "julien":       "https://router.huggingface.co/hf-inference/v1",
    "groq":         "https://api.groq.com/openai/v1",
    "openrouter":   "https://openrouter.ai/api/v1",
    "mistral":      "https://api.mistral.ai/v1",
    "jina":         "https://api.jina.ai/v1",
    "pollinations": "https://gen.pollinations.ai/v1",
    "cohere":       "https://api.cohere.com/v2",
    "local":        LOCAL_MESH_URL,
    "mesh":         LOCAL_MESH_URL,
}

app = FastAPI(title="Lauburu AI Budget Proxy & Free Router", version="2.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def is_free_tier(provider: str, model: str) -> bool:
    """Returns True if the request qualifies for zero-cost execution."""
    if provider.lower() in ("local", "mesh", "julien", "huggingface", "workers-ai"):
        return True
    if any(model.lower().startswith(p) for p in FREE_MODELS_PREFIXES):
        return True
    if provider.lower() in ("google", "gemini") and "-free" in model.lower():
        return True
    return False


# ── Ledger helpers ─────────────────────────────────────────────────────────────
def load_ledger() -> dict:
    if LEDGER_PATH.exists():
        try:
            return json.loads(LEDGER_PATH.read_text())
        except Exception:
            pass
    return {
        "budget_limit": BUDGET_LIMIT,
        "current_spend": 0.0,
        "period_start": datetime.utcnow().date().isoformat(),
        "free_tier_calls": 0,
        "paid_tier_calls": 0,
        "transactions": [],
    }


def save_ledger(ledger: dict) -> None:
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2))


def estimate_cost(model: str, input_tokens: int, output_tokens: int = 0, is_free: bool = False) -> float:
    if is_free:
        return 0.0
    pricing = PRICING.get(model, PRICING["_default"])
    return (input_tokens / 1_000_000 * pricing["input"] +
            output_tokens / 1_000_000 * pricing["output"])


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    try:
        enc = tiktoken.encoding_for_model(model if "gpt" in model else "gpt-4o")
        return len(enc.encode(text))
    except Exception:
        return len(text.split()) * 4 // 3  # rough fallback


def log_transaction(ledger: dict, model: str, provider: str,
                    input_tokens: int, output_tokens: int, cost: float,
                    prompt: str, response: str, is_free: bool) -> None:
    tx = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "model": model,
        "provider": provider,
        "is_free": is_free,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 6),
    }
    if is_free:
        ledger["free_tier_calls"] = ledger.get("free_tier_calls", 0) + 1
    else:
        ledger["paid_tier_calls"] = ledger.get("paid_tier_calls", 0) + 1
        ledger["current_spend"] = round(ledger["current_spend"] + cost, 6)

    # Maintain last 500 transactions
    if "transactions" not in ledger:
        ledger["transactions"] = []
    ledger["transactions"].append(tx)
    if len(ledger["transactions"]) > 500:
        ledger["transactions"] = ledger["transactions"][-500:]

    save_ledger(ledger)

    # Harvest into continuous LoRA training dataset
    try:
        LORA_DATASET.parent.mkdir(parents=True, exist_ok=True)
        pair = {
            "timestamp": tx["timestamp"],
            "source": f"api_router:{provider}:{model}",
            "instruction": "Respond as an expert AI specialist in the Lauburu Mesh ecosystem.",
            "input": prompt[:4000],
            "output": response[:4000],
            "metadata": {
                "cost_usd": cost,
                "model": model,
                "provider": provider,
                "is_free": is_free,
            },
        }
        with LORA_DATASET.open("a", encoding="utf-8") as f:
            f.write(json.dumps(pair) + "\n")
    except Exception as e:
        print(f"Warning: Failed to append to LoRA dataset: {e}")


LOCAL_ENDPOINTS = [
    os.getenv("LOCAL_MESH_URL", "http://127.0.0.1:8081/v1"),
    os.getenv("LOCAL_DEVIL_URL", "http://127.0.0.1:8083/v1"),
    "http://127.0.0.1:8082/v1",
]


async def get_live_local_base() -> str:
    """Returns the first responsive local llama.cpp endpoint."""
    for base in LOCAL_ENDPOINTS:
        try:
            health_url = base.replace("/v1", "/health")
            async with httpx.AsyncClient(timeout=0.8) as client:
                r = await client.get(health_url)
                if r.status_code in (200, 503):
                    return base
        except Exception:
            continue
    return LOCAL_MESH_URL


# ── Local Mesh Fallback Helper ────────────────────────────────────────────────
async def try_local_fallback(body: dict, headers: dict) -> Optional[Response]:
    """Attempts to route request to local llama.cpp mesh when upstream fails or 429s."""
    for base in LOCAL_ENDPOINTS:
        url = f"{base}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=body, headers={"Content-Type": "application/json"})
                if resp.status_code == 200:
                    resp_headers = dict(resp.headers)
                    resp_headers["X-Lauburu-Fallback"] = "local-mesh"
                    resp_headers["X-Lauburu-Tier"] = "free-mesh"
                    resp_headers["X-Lauburu-Cost-USD"] = "0.000000"
                    return Response(
                        content=resp.content,
                        status_code=resp.status_code,
                        headers=resp_headers,
                    )
        except Exception:
            continue
    return None


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/health")
@app.get("/status")
async def status():
    ledger = load_ledger()
    remaining = max(0.0, ledger["budget_limit"] - ledger["current_spend"])

    # Test local mesh status
    local_mesh_live = False
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            r = await client.get("http://127.0.0.1:8081/health")
            local_mesh_live = r.status_code in (200, 503)
    except Exception:
        local_mesh_live = False

    local_devil_live = False
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            r = await client.get("http://127.0.0.1:8083/health")
            local_devil_live = r.status_code in (200, 503)
    except Exception:
        local_devil_live = False

    return {
        "status": "healthy",
        "budget_limit": ledger["budget_limit"],
        "current_spend": round(ledger["current_spend"], 6),
        "remaining": round(remaining, 6),
        "free_tier_calls": ledger.get("free_tier_calls", 0),
        "paid_tier_calls": ledger.get("paid_tier_calls", 0),
        "kill_switch_engaged": remaining <= 0,
        "local_mesh_8081": "LIVE" if local_mesh_live else "OFFLINE",
        "local_devil_8083": "LIVE" if local_devil_live else "OFFLINE",
        "supported_free_providers": list(FREE_PROVIDERS),
        "cloudflare_gateway": CF_GW_BASE,
    }


@app.post("/reset")
async def reset_spend(request: Request):
    body = await request.json()
    if body.get("admin_key") != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key. User authorization required.")
    new_limit = float(body.get("new_limit", BUDGET_LIMIT))
    ledger = load_ledger()
    ledger["current_spend"] = 0.0
    ledger["budget_limit"] = new_limit
    ledger["period_start"] = datetime.utcnow().date().isoformat()
    ledger["transactions"] = []
    save_ledger(ledger)
    return {"status": "reset", "new_limit": new_limit}


@app.post("/v1/chat/completions")
async def unified_chat_completions(request: Request):
    """
    Unified OpenAI-compatible chat completions endpoint.
    Auto-routes based on model name prefix:
      gemini/* or google/*     -> Gemini Free Tier
      cf/* or @cf/*           -> Cloudflare Workers AI Free Tier
      hf/* or julien/*        -> Hugging Face Serverless Free Tier
      local/* or mesh/*       -> Local llama.cpp Mesh (Port 8081/8083)
      claude/* or anthropic/* -> Claude API (Budget Proxy Protected)
      gpt/* or openai/*       -> OpenAI API (Budget Proxy Protected)
    """
    body_bytes = await request.body()
    try:
        body = json.loads(body_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    raw_model = body.get("model", "gemini-2.0-flash")
    model_lower = raw_model.lower()

    # Determine provider and stripped model
    if model_lower.startswith(("gemini/", "google/")):
        provider = "google"
        target_model = raw_model.split("/", 1)[1]
    elif model_lower.startswith(("@cf/", "cf/", "cloudflare/")):
        provider = "cloudflare"
        target_model = raw_model.replace("cf/", "@cf/") if not raw_model.startswith("@cf/") else raw_model
    elif model_lower.startswith(("hf/", "julien/", "huggingface/")):
        provider = "huggingface"
        target_model = raw_model.split("/", 1)[1]
    elif model_lower.startswith("groq/"):
        provider = "groq"
        target_model = raw_model.split("/", 1)[1]
    elif model_lower.startswith("openrouter/"):
        provider = "openrouter"
        target_model = raw_model.split("/", 1)[1]
    elif model_lower.startswith("mistral/"):
        provider = "mistral"
        target_model = raw_model.split("/", 1)[1]
    elif model_lower.startswith("pollinations/"):
        provider = "pollinations"
        target_model = raw_model.split("/", 1)[1]
    elif model_lower.startswith("cohere/"):
        provider = "cohere"
        target_model = raw_model.split("/", 1)[1]
    elif model_lower.startswith(("local/", "mesh/")):
        provider = "local"
        target_model = raw_model.split("/", 1)[1]
    elif model_lower.startswith(("claude/", "anthropic/")):
        provider = "anthropic"
        target_model = raw_model.split("/", 1)[1]
    elif model_lower.startswith(("openai/", "gpt/", "o1/")):
        provider = "openai"
        target_model = raw_model.split("/", 1)[1] if "/" in raw_model else raw_model
    else:
        # Auto-match by standard prefixes
        if "gemini" in model_lower:
            provider = "google"
            target_model = raw_model
        elif "@cf/" in model_lower:
            provider = "cloudflare"
            target_model = raw_model
        elif "groq" in model_lower:
            provider = "groq"
            target_model = raw_model
        elif "claude" in model_lower:
            provider = "anthropic"
            target_model = raw_model
        elif "gpt" in model_lower or "o1" in model_lower:
            provider = "openai"
            target_model = raw_model
        else:
            provider = "local"
            target_model = raw_model

    body["model"] = target_model
    return await proxy_request(provider=provider, path="chat/completions", request=request, override_body=body)


@app.post("/v1/{provider}/v1/{path:path}")
@app.post("/v1/{provider}/{path:path}")
async def proxy_request(provider: str, path: str, request: Request, override_body: Optional[dict] = None):
    """
    Direct provider proxy with zero-cost free-tier acceleration and budget governor.
    """
    ledger = load_ledger()
    if override_body is not None:
        body = override_body
        body_bytes = json.dumps(body).encode("utf-8")
    else:
        body_bytes = await request.body()
        try:
            body = json.loads(body_bytes)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON body")

    model = body.get("model", "_default")
    is_free = is_free_tier(provider, model)

    # Extract prompt text for token calculation
    messages = body.get("messages", body.get("prompt", body.get("contents", [])))
    prompt_text = ""
    if isinstance(messages, list):
        for m in messages:
            if isinstance(m, dict):
                content = m.get("content", m.get("parts", ""))
                if isinstance(content, str):
                    prompt_text += content + " "
                elif isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict):
                            prompt_text += c.get("text", "") + " "
                        elif isinstance(c, str):
                            prompt_text += c + " "
    elif isinstance(messages, str):
        prompt_text = messages

    input_tokens = count_tokens(prompt_text, model)
    max_output = body.get("max_tokens", body.get("max_completion_tokens", 2048))
    estimated_cost = estimate_cost(model, input_tokens, int(max_output), is_free=is_free)

    current_spend = ledger["current_spend"]
    budget_limit  = ledger["budget_limit"]

    # ── KILL SWITCH (For Paid APIs Only) ──────────────────────────────────────
    if not is_free and (current_spend + estimated_cost > budget_limit):
        # Attempt fallback to free local mesh before rejecting
        fallback_resp = await try_local_fallback(body, dict(request.headers))
        if fallback_resp:
            return fallback_resp

        return JSONResponse(status_code=429, content={
            "error": "BudgetExceeded",
            "kill_switch": True,
            "current_spend_usd": round(current_spend, 6),
            "estimated_cost_usd": round(estimated_cost, 6),
            "budget_limit_usd": budget_limit,
            "shortfall_usd": round((current_spend + estimated_cost) - budget_limit, 6),
            "message": (
                f"🛑 Kill-switch engaged. Spent ${current_spend:.4f} of ${budget_limit:.2f} budget. "
                f"Use local mesh models (Port 8081/8083) or free tier APIs (Gemini Free, Cloudflare 10k Neurons) "
                "or POST /reset with admin_key to authorize additional spend."
            ),
        })

    # ── TARGET URL RESOLUTION ────────────────────────────────────────────────
    prov_key = provider.lower()
    if prov_key not in PROVIDER_ROUTES:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}. Valid: {list(PROVIDER_ROUTES)}")

    if prov_key in ("local", "mesh"):
        local_base = await get_live_local_base()
        target_url = f"{local_base}/{path}"
    else:
        # Route through Cloudflare AI Gateway
        target_base = f"{CF_GW_BASE}/{prov_key}"
        target_url  = f"{target_base}/{path}"

    # Forward headers
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in {"host", "content-length", "transfer-encoding"}}

    # Inject default API Keys if missing and available in environment
    if prov_key in ("google", "gemini") and "x-goog-api-key" not in headers and "authorization" not in headers:
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            headers["x-goog-api-key"] = gemini_key

    if prov_key in ("huggingface", "julien") and "authorization" not in headers:
        hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
        if hf_token:
            headers["authorization"] = f"Bearer {hf_token}"

    if prov_key in ("cloudflare", "workers-ai") and "authorization" not in headers:
        cf_token = os.getenv("CLOUDFLARE_API_TOKEN")
        if cf_token:
            headers["authorization"] = f"Bearer {cf_token}"

    if prov_key == "groq" and "authorization" not in headers:
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            headers["authorization"] = f"Bearer {groq_key}"

    if prov_key == "openrouter" and "authorization" not in headers:
        or_key = os.getenv("OPENROUTER_API_KEY")
        if or_key:
            headers["authorization"] = f"Bearer {or_key}"

    if prov_key == "mistral" and "authorization" not in headers:
        mistral_key = os.getenv("MISTRAL_API_KEY")
        if mistral_key:
            headers["authorization"] = f"Bearer {mistral_key}"

    if prov_key == "jina" and "authorization" not in headers:
        jina_key = os.getenv("JINA_API_KEY")
        if jina_key:
            headers["authorization"] = f"Bearer {jina_key}"

    if prov_key == "cohere" and "authorization" not in headers:
        cohere_key = os.getenv("COHERE_API_KEY")
        if cohere_key:
            headers["authorization"] = f"Bearer {cohere_key}"

    start = time.time()
    resp = None
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(target_url, content=body_bytes, headers=headers)
    except Exception as e:
        print(f"Upstream request to {target_url} failed: {e}. Attempting local fallback...")
        fallback_resp = await try_local_fallback(body, headers)
        if fallback_resp:
            return fallback_resp
        raise HTTPException(status_code=502, detail=f"Gateway error: {e}")

    # If error or rate limited on Free Tier / Local, auto-fallback to alternate local mesh
    if resp.status_code in (429, 500, 502, 503, 504) and is_free:
        print(f"⚠️ Upstream {target_url} returned {resp.status_code}. Automatically falling back to alternate local mesh...")
        fallback_resp = await try_local_fallback(body, headers)
        if fallback_resp:
            return fallback_resp

    elapsed = time.time() - start

    # Parse response tokens and extract text for LoRA dataset
    output_tokens = 0
    response_text = ""
    try:
        resp_json = resp.json()
        usage = resp_json.get("usage", {})
        output_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))
        choices = resp_json.get("choices", resp_json.get("content", resp_json.get("candidates", [])))
        if choices and isinstance(choices, list):
            first = choices[0]
            if isinstance(first, dict):
                response_text = (first.get("message", {}).get("content", "")
                                 or first.get("text", "")
                                 or str(first.get("content", "")))
    except Exception:
        output_tokens = max_output // 4

    actual_cost = 0.0 if is_free else estimate_cost(model, input_tokens, output_tokens or int(max_output) // 2)
    log_transaction(ledger, model, provider, input_tokens, output_tokens, actual_cost,
                    prompt_text[:4000], response_text[:4000], is_free=is_free)

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers={
            "X-Lauburu-Tier": "free-tier" if is_free else "paid-gateway",
            "X-Lauburu-Cost-USD": str(round(actual_cost, 6)),
            "X-Lauburu-Spend-Total": str(round(ledger["current_spend"], 6)),
            "X-Lauburu-Remaining": str(round(budget_limit - ledger["current_spend"], 6)),
            "X-Lauburu-Latency-Ms": str(round(elapsed * 1000)),
            "Access-Control-Allow-Origin": "*",
            "Content-Type": resp.headers.get("content-type", "application/json"),
        },
    )


if __name__ == "__main__":
    import uvicorn
    print("🛡️  Lauburu AI Budget Proxy & Free Router v2.0")
    print(f"   Budget limit: ${BUDGET_LIMIT:.2f}")
    print(f"   Ledger: {LEDGER_PATH}")
    print(f"   CF Gateway: {CF_GW_BASE}")
    print(f"   Local Mesh: {LOCAL_MESH_URL}")
    print("   Free Providers: Google Gemini Free, Cloudflare 10k Neurons, HF/Julien, Local Mesh")
    print("   Listening on http://0.0.0.0:9000")
    uvicorn.run(app, host="0.0.0.0", port=9000, log_level="info")

