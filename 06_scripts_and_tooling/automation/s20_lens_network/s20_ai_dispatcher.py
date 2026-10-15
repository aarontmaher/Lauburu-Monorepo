#!/usr/bin/env python3
"""
s20_ai_dispatcher.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Lauburu Mesh - Multi-Model Intelligence Dispatcher for S20 Lens Network

Seamlessly routes tool-calling and conversational payloads between three
distinct AI backends based on availability, task complexity, and explicit toggles:
1. Local Sovereign AI: Qwen 3.8 Max on Port 8082 (with L3 Linux 100.101.39.98 fallback).
2. Free Cloud API: Google AI Studio Gemini / Groq free tiers.
3. OpenRouter API / MCP: High-density frontier and open-weight models.

Zero-Mock Invariant (Rule #0 / Cardinal Law #1):
All network requests make authentic socket/HTTP connections. In the absence
of live keys or offline endpoints, errors and diagnostics reflect genuine
system states rather than simulated fake text.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import sys
import json
import socket
import argparse
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

# ── Backend Configuration & Endpoints ─────────────────────────────────────────

LOCAL_PORT_PRIMARY = int(os.environ.get("LOCAL_AI_PORT", "8082"))
LOCAL_HOST_PRIMARY = os.environ.get("LOCAL_AI_HOST", "127.0.0.1")
LOCAL_HOST_LINUX   = os.environ.get("LOCAL_AI_LINUX_HOST", "100.101.39.98")

GEMINI_API_KEY     = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
GROQ_API_KEY       = os.environ.get("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

DEFAULT_LOCAL_MODEL      = "qwen_38_max_abliterated"
DEFAULT_GEMINI_MODEL     = "gemini-2.5-flash"
DEFAULT_OPENROUTER_MODEL = "google/gemini-2.5-flash"

def _is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Fast socket check to prevent long HTTP connection timeouts on offline hosts."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def _http_post_json(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None, timeout: float = 4.0) -> Dict[str, Any]:
    """Helper to perform standard zero-mock HTTP POST request without heavy dependencies."""
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
        
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data_bytes, headers=req_headers, method="POST")
    
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status_code = resp.getcode()
            body_bytes = resp.read()
            body_str = body_bytes.decode("utf-8", errors="replace")
            try:
                parsed_json = json.loads(body_str)
            except json.JSONDecodeError:
                parsed_json = {"raw_response": body_str}
            return {
                "success": 200 <= status_code < 300,
                "status_code": status_code,
                "data": parsed_json
            }
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {
            "success": False,
            "status_code": e.code,
            "error": f"HTTPError {e.code}: {e.reason}",
            "body": body
        }
    except urllib.error.URLError as e:
        return {
            "success": False,
            "status_code": -1,
            "error": f"URLError: {e.reason}"
        }
    except Exception as e:
        return {
            "success": False,
            "status_code": -1,
            "error": str(e)
        }

# ── Backend 1: Local Sovereign AI Engine ──────────────────────────────────────

def dispatch_to_local_ai(payload: Dict[str, Any], model: Optional[str] = None, timeout: float = 3.0) -> Dict[str, Any]:
    """
    Routes tool payload to Sovereign Local Qwen 3.8 Max (Port 8082).
    Falls back to L3 Linux Head Node (Rule 10) if host endpoint is unavailable.
    """
    model_name = model or DEFAULT_LOCAL_MODEL
    hosts = [
        (LOCAL_HOST_PRIMARY, LOCAL_PORT_PRIMARY),
        (LOCAL_HOST_LINUX, LOCAL_PORT_PRIMARY)
    ]
    
    req_payload = dict(payload)
    if "messages" not in req_payload:
        content = req_payload.get("prompt") or json.dumps(req_payload)
        req_payload["messages"] = [{"role": "user", "content": content}]
    if "model" not in req_payload:
        req_payload["model"] = model_name

    for host, port in hosts:
        if not _is_port_open(host, port, timeout=1.0):
            continue
            
        endpoint = f"http://{host}:{port}/v1/chat/completions"
        res = _http_post_json(endpoint, req_payload, timeout=timeout)
        if res.get("success"):
            return {
                "success": True,
                "backend": "local_qwen",
                "endpoint": endpoint,
                "model": model_name,
                "response": res["data"]
            }
            
    return {
        "success": False,
        "backend": "local_qwen",
        "error": "Local AI engines on Host (:8082) and Linux Mini (:8082) are offline or unreachable",
        "tested_endpoints": [f"http://{h}:{p}/v1/chat/completions" for h, p in hosts]
    }

# ── Backend 2: Free Cloud API Engine ──────────────────────────────────────────

def dispatch_to_free_cloud(payload: Dict[str, Any], model: Optional[str] = None, timeout: float = 2.5) -> Dict[str, Any]:
    """Routes to Google AI Studio Gemini API or Groq free tier with fast failover."""
    # 1. Try Gemini if API key is present
    if GEMINI_API_KEY:
        gemini_model = model or DEFAULT_GEMINI_MODEL
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={GEMINI_API_KEY}"
        
        prompt_text = ""
        if "messages" in payload:
            prompt_text = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in payload["messages"]])
        elif "prompt" in payload:
            prompt_text = str(payload["prompt"])
        else:
            prompt_text = json.dumps(payload)
            
        gemini_payload = {
            "contents": [{
                "parts": [{"text": prompt_text}]
            }]
        }
        
        res = _http_post_json(url, gemini_payload, timeout=timeout)
        if res.get("success"):
            return {
                "success": True,
                "backend": "free_cloud_gemini",
                "model": gemini_model,
                "response": res["data"]
            }
        else:
            gemini_error = res.get("error")
    else:
        gemini_error = "GEMINI_API_KEY not found in environment"

    # 2. Try Groq if API key is present
    if GROQ_API_KEY:
        groq_model = model or "llama-3.3-70b-versatile"
        groq_url = "https://api.groq.com/openai/v1/chat/completions"
        req_payload = dict(payload)
        req_payload["model"] = groq_model
        if "messages" not in req_payload:
            content = req_payload.get("prompt") or json.dumps(req_payload)
            req_payload["messages"] = [{"role": "user", "content": content}]
            
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        res = _http_post_json(groq_url, req_payload, headers=headers, timeout=timeout)
        if res.get("success"):
            return {
                "success": True,
                "backend": "free_cloud_groq",
                "model": groq_model,
                "response": res["data"]
            }
        else:
            groq_error = res.get("error")
    else:
        groq_error = "GROQ_API_KEY not found in environment"

    return {
        "success": False,
        "backend": "free_cloud",
        "error": f"Cloud dispatch unfulfilled. Gemini: ({gemini_error}), Groq: ({groq_error})"
    }

# ── Backend 3: OpenRouter API / MCP Engine ────────────────────────────────────

def dispatch_to_openrouter(payload: Dict[str, Any], model: Optional[str] = None, timeout: float = 3.0) -> Dict[str, Any]:
    """Routes to OpenRouter API with full tool-calling schema support."""
    if not OPENROUTER_API_KEY:
        return {
            "success": False,
            "backend": "openrouter",
            "error": "OPENROUTER_API_KEY not configured in environment"
        }
        
    url = "https://openrouter.ai/api/v1/chat/completions"
    or_model = model or DEFAULT_OPENROUTER_MODEL
    
    req_payload = dict(payload)
    req_payload["model"] = or_model
    if "messages" not in req_payload:
        content = req_payload.get("prompt") or json.dumps(req_payload)
        req_payload["messages"] = [{"role": "user", "content": content}]
        
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://lauburu.mesh",
        "X-Title": "Lauburu S20 Lens Network"
    }
    
    res = _http_post_json(url, req_payload, headers=headers, timeout=timeout)
    if res.get("success"):
        return {
            "success": True,
            "backend": "openrouter",
            "model": or_model,
            "response": res["data"]
        }
        
    return {
        "success": False,
        "backend": "openrouter",
        "model": or_model,
        "error": res.get("error", "OpenRouter request failed"),
        "body": res.get("body")
    }

# ── Unified Dispatcher with Programmatic Toggles ──────────────────────────────

def dispatch_payload(payload: Dict[str, Any], backend: str = "auto", model: Optional[str] = None, fallback: bool = True) -> Dict[str, Any]:
    """
    Programmatic entrypoint to route arbitrary JSON tool payloads.
    
    Toggles:
    - backend='local': strictly forces Local Qwen 3.8 Max.
    - backend='cloud': strictly forces Free Cloud (Gemini / Groq).
    - backend='openrouter': strictly forces OpenRouter.
    - backend='auto': tries Local -> Cloud -> OpenRouter in waterfall sequence.
    """
    b = backend.lower().strip()
    
    if b == "local":
        return dispatch_to_local_ai(payload, model=model)
    elif b == "cloud":
        return dispatch_to_free_cloud(payload, model=model)
    elif b == "openrouter":
        return dispatch_to_openrouter(payload, model=model)
    elif b == "auto":
        # 1. Attempt Local AI first (Rule #0 / Local First)
        local_res = dispatch_to_local_ai(payload, model=model)
        if local_res.get("success"):
            return local_res
            
        if not fallback:
            return local_res
            
        # 2. Attempt Free Cloud API next
        cloud_res = dispatch_to_free_cloud(payload, model=model)
        if cloud_res.get("success"):
            return cloud_res
            
        # 3. Attempt OpenRouter as final fallback
        or_res = dispatch_to_openrouter(payload, model=model)
        if or_res.get("success"):
            return or_res
            
        return {
            "success": False,
            "backend": "auto",
            "error": "All AI backends (Local, Cloud, OpenRouter) exhausted or unavailable",
            "details": {
                "local": local_res.get("error"),
                "cloud": cloud_res.get("error"),
                "openrouter": or_res.get("error")
            }
        }
    else:
        return {
            "success": False,
            "error": f"Invalid backend toggle: '{backend}'. Must be one of: 'local', 'cloud', 'openrouter', 'auto'"
        }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Model AI Dispatcher for S20 Lens Network")
    parser.add_argument("--backend", choices=["local", "cloud", "openrouter", "auto"], default="auto",
                        help="Backend selection toggle")
    parser.add_argument("--payload", type=str, required=True,
                        help="JSON payload string (or file path if prefixed with @)")
    parser.add_argument("--model", type=str, help="Override target model name")
    parser.add_argument("--no-fallback", action="store_true", help="Disable automatic backend fallback")
    args = parser.parse_args()
    
    payload_str = args.payload
    if payload_str.startswith("@"):
        file_path = payload_str[1:]
        try:
            with open(file_path, "r") as f:
                payload_data = json.load(f)
        except Exception as e:
            print(json.dumps({"success": False, "error": f"Failed to read payload file {file_path}: {e}"}))
            sys.exit(1)
    else:
        try:
            payload_data = json.loads(payload_str)
        except json.JSONDecodeError as e:
            print(json.dumps({"success": False, "error": f"Invalid JSON payload: {e}"}))
            sys.exit(1)
            
    result = dispatch_payload(
        payload=payload_data,
        backend=args.backend,
        model=args.model,
        fallback=not args.no_fallback
    )
    print(json.dumps(result, indent=2))
