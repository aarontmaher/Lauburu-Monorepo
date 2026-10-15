#!/usr/bin/env python3
"""
================================================================================
Lauburu Mesh Ecosystem — Canonical AI Key Manager & Live Validator
================================================================================
Path: 06_scripts_and_tooling/lauburu_key_manager.py

Governs discovery, storage, validation, and empirical testing of all Cloud AI
API keys across the Mac Mini host:
- Google AI Studio (Gemini 2.5 / 3.8 Flash)
- Hugging Face Hub (Model weights & datasets)
- Cloudflare Workers AI (Edge Llama 3.3 70B)
- NVIDIA NIM (DeepSeek V4 Pro 1.6T MoE)
- xAI Grok-2 (Live web facts & red-team)
- Groq / OpenRouter (Free tier inference)

All keys are stored securely in:
- /Users/aaron/.env (User profile, auto-sourced by ~/.zshrc)
- /Volumes/Lauburu-Monorepo/.env (Monorepo root)
Strictly enforced with chmod 600 permissions.
================================================================================
"""

import os
import sys
import json
import argparse
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, Tuple

USER_ENV = Path.home() / ".env"
MONO_ENV = Path("/Volumes/Lauburu-Monorepo/.env")

KEY_DEFINITIONS = {
    "GEMINI_API_KEY": {
        "name": "Google AI Studio (Gemini 2.5 / 3.8 Flash)",
        "docs_url": "https://aistudio.google.com/apikey",
        "free_tier": "1,500 requests / day ($0.00)",
        "models": ["gemini-2.5-flash", "gemini-3.8-flash"],
        "test_type": "gemini"
    },
    "HF_TOKEN": {
        "name": "Hugging Face Access Token",
        "docs_url": "https://huggingface.co/settings/tokens",
        "free_tier": "Unlimited public downloads / uploads",
        "models": ["Hub API"],
        "test_type": "huggingface"
    },
    "CLOUDFLARE_API_TOKEN": {
        "name": "Cloudflare Workers AI Token",
        "docs_url": "https://dash.cloudflare.com/profile/api-tokens",
        "free_tier": "10,000 Neurons / day (~800 requests/day, $0.00)",
        "models": ["@cf/meta/llama-3.3-70b-instruct"],
        "test_type": "cloudflare"
    },
    "NVIDIA_API_KEY": {
        "name": "NVIDIA NIM (DeepSeek V4 Pro 1.6T MoE)",
        "docs_url": "https://build.nvidia.com/",
        "free_tier": "2,000 requests / day ($0.00)",
        "models": ["deepseek-ai/deepseek-v4-pro", "deepseek-ai/deepseek-v4-flash"],
        "test_type": "nvidia"
    },
    "XAI_API_KEY": {
        "name": "xAI Developer Platform (Grok-2)",
        "docs_url": "https://console.x.ai/",
        "free_tier": "$25/mo free trial credit (~1,000 requests/day)",
        "models": ["grok-2-1212"],
        "test_type": "xai"
    },
    "GROQ_API_KEY": {
        "name": "Groq Cloud Fast Inference",
        "docs_url": "https://console.groq.com/keys",
        "free_tier": "14,400 requests / day on gemma2-9b-it ($0.00)",
        "models": ["gemma2-9b-it", "llama-3.3-70b-versatile"],
        "test_type": "groq"
    }
}


def load_env_dict(path: Path) -> Dict[str, str]:
    env = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("\"'")
    return env


def save_key_to_file(path: Path, key: str, value: str) -> None:
    lines = []
    found = False
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith(f"{key}=") or stripped.startswith(f"# {key}="):
                lines.append(f"{key}={value}")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"{key}={value}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def test_gemini(key: str) -> Tuple[bool, str]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
    payload = json.dumps({"contents": [{"parts": [{"text": "Reply with: OK"}]}]}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            return True, f"HTTP {resp.status} - Output: {text}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return False, str(e)


def test_huggingface(token: str) -> Tuple[bool, str]:
    req = urllib.request.Request(
        "https://huggingface.co/api/whoami-v2",
        headers={"Authorization": f"Bearer {token}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            name = data.get("name", "Unknown")
            return True, f"HTTP {resp.status} - User: {name}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return False, str(e)


def test_cloudflare(token: str, account_id: str) -> Tuple[bool, str]:
    if not account_id:
        return False, "Missing CLOUDFLARE_ACCOUNT_ID"
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-3.3-70b-instruct"
    payload = json.dumps({"messages": [{"role": "user", "content": "Reply with: OK"}]}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("success"):
                return True, f"HTTP {resp.status} - Success"
            return False, f"HTTP {resp.status} - {data.get('errors')}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return False, str(e)


def test_nvidia(key: str) -> Tuple[bool, str]:
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    payload = json.dumps({
        "model": "meta/llama-3.2-11b-vision-instruct",
        "messages": [{"role": "user", "content": "Reply with: OK"}],
        "max_tokens": 16
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            out = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            return True, f"HTTP {resp.status} - Output: {out}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return False, str(e)


def test_xai(key: str) -> Tuple[bool, str]:
    url = "https://api.x.ai/v1/chat/completions"
    payload = json.dumps({
        "model": "grok-4.20-0309-non-reasoning",
        "messages": [{"role": "user", "content": "Reply with: OK"}],
        "max_tokens": 16
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            out = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            return True, f"HTTP {resp.status} - Output: {out}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return False, str(e)


def test_groq(key: str) -> Tuple[bool, str]:
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = json.dumps({
        "model": "groq/compound-mini",
        "messages": [{"role": "user", "content": "Reply with: OK"}],
        "max_tokens": 16
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "User-Agent": "Lauburu-Mesh/1.0 (Macintosh; Apple M4 Pro)",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            out = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            return True, f"HTTP {resp.status} - Output: {out}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return False, str(e)


def audit_keys() -> None:
    user_env = load_env_dict(USER_ENV)
    mono_env = load_env_dict(MONO_ENV)
    merged = {**user_env, **mono_env}

    print("=" * 80)
    print("🌿 LAUBURU MESH CLOUD AI KEY AUDIT & STATUS MATRIX")
    print("=" * 80)
    print(f"User Env:     {USER_ENV} (Permissions: {oct(USER_ENV.stat().st_mode & 0o777) if USER_ENV.exists() else 'N/A'})")
    print(f"Monorepo Env: {MONO_ENV} (Permissions: {oct(MONO_ENV.stat().st_mode & 0o777) if MONO_ENV.exists() else 'N/A'})")
    print("-" * 80)

    for k, meta in KEY_DEFINITIONS.items():
        val = merged.get(k)
        if val:
            masked = val[:6] + "..." + val[-4:] if len(val) > 10 else "***"
            status_icon = "🟢 STORED"
            len_str = f"({len(val)} chars)"
        else:
            masked = "--"
            status_icon = "⚪ NOT SET"
            len_str = ""

        print(f"\n🔑 {k:<24} | {status_icon} | {masked} {len_str}")
        print(f"   Provider:  {meta['name']}")
        print(f"   Quota:     {meta['free_tier']}")
        print(f"   Setup URL: {meta['docs_url']}")

    print("\n" + "=" * 80)


def test_all_keys() -> None:
    user_env = load_env_dict(USER_ENV)
    mono_env = load_env_dict(MONO_ENV)
    merged = {**user_env, **mono_env}
    account_id = merged.get("CLOUDFLARE_ACCOUNT_ID", "16282271f1eccb56f0b96afed09d21ff")

    print("=" * 80)
    print("🔬 EMPIRICAL LIVE PROBING OF CONFIGURED CLOUD AI KEYS")
    print("=" * 80)

    for k, meta in KEY_DEFINITIONS.items():
        val = merged.get(k)
        if not val:
            print(f"⚪ {k:<24} | Bypassed (Key not configured)")
            continue

        ttype = meta["test_type"]
        print(f"🔄 Probing {k}...", end="", flush=True)

        if ttype == "gemini":
            ok, detail = test_gemini(val)
        elif ttype == "huggingface":
            ok, detail = test_huggingface(val)
        elif ttype == "cloudflare":
            ok, detail = test_cloudflare(val, account_id)
        elif ttype == "nvidia":
            ok, detail = test_nvidia(val)
        elif ttype == "xai":
            ok, detail = test_xai(val)
        elif ttype == "groq":
            ok, detail = test_groq(val)
        else:
            ok, detail = False, "Unknown provider"

        status_str = "🟢 VERIFIED LIVE" if ok else "🔴 PROBE FAILED"
        print(f"\r{status_str} | {k:<24} | {detail}")

    print("=" * 80)


def set_key(key_name: str, key_val: str) -> None:
    key_name = key_name.upper().strip()
    key_val = key_val.strip()

    if key_name == "GEMINI":
        key_name = "GEMINI_API_KEY"
    elif key_name == "GOOGLE":
        key_name = "GOOGLE_API_KEY"
    elif key_name in ("HF", "HUGGINGFACE"):
        key_name = "HF_TOKEN"
    elif key_name in ("CF", "CLOUDFLARE"):
        key_name = "CLOUDFLARE_API_TOKEN"
    elif key_name in ("NVIDIA", "NIM"):
        key_name = "NVIDIA_API_KEY"
    elif key_name in ("XAI", "GROK"):
        key_name = "XAI_API_KEY"
    elif key_name == "GROQ":
        key_name = "GROQ_API_KEY"

    save_key_to_file(USER_ENV, key_name, key_val)
    save_key_to_file(MONO_ENV, key_name, key_val)
    if key_name == "GEMINI_API_KEY":
        save_key_to_file(USER_ENV, "GOOGLE_API_KEY", key_val)
        save_key_to_file(MONO_ENV, "GOOGLE_API_KEY", key_val)

    print(f"✅ Successfully stored {key_name} in:")
    print(f"   - {USER_ENV} (chmod 600)")
    print(f"   - {MONO_ENV} (chmod 600)")

    # Run instant live probe if provider is recognized
    account_id = load_env_dict(MONO_ENV).get("CLOUDFLARE_ACCOUNT_ID", "16282271f1eccb56f0b96afed09d21ff")
    print(f"\n🔄 Running instant empirical probe on {key_name}...")
    if key_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        ok, detail = test_gemini(key_val)
    elif key_name == "HF_TOKEN":
        ok, detail = test_huggingface(key_val)
    elif key_name == "CLOUDFLARE_API_TOKEN":
        ok, detail = test_cloudflare(key_val, account_id)
    elif key_name == "NVIDIA_API_KEY":
        ok, detail = test_nvidia(key_val)
    elif key_name == "XAI_API_KEY":
        ok, detail = test_xai(key_val)
    elif key_name == "GROQ_API_KEY":
        ok, detail = test_groq(key_val)
    else:
        ok, detail = True, "Key stored without live probe hook"

    status_str = "🟢 VERIFIED LIVE" if ok else "🔴 PROBE FAILED"
    print(f"{status_str} | {key_name} | {detail}")


def main():
    parser = argparse.ArgumentParser(description="Lauburu Mesh AI Key Manager")
    parser.add_argument("--audit", action="store_true", help="Display audit of stored keys")
    parser.add_argument("--test", action="store_true", help="Run live probe against all configured keys")
    parser.add_argument("--set", nargs=2, metavar=("KEY_NAME", "VALUE"), help="Set an API key (e.g. --set NVIDIA_API_KEY nvapi-...)")

    args = parser.parse_args()

    if args.set:
        set_key(args.set[0], args.set[1])
    elif args.test:
        test_all_keys()
    else:
        audit_keys()


if __name__ == "__main__":
    main()
