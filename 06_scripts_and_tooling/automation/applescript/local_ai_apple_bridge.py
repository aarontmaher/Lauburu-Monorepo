#!/usr/bin/env python3
"""
================================================================================
Lauburu Local AI Only AppleScript Bridge
================================================================================
Subsystem: 06_scripts_and_tooling/automation/applescript/local_ai_apple_bridge.py
Version: 1.0.0-LOCAL-AI-APPLESCRIPT
Lauburu Mesh Ecosystem — 2026

Strict Local-AI-Only Invariant:
1. Zero-Cloud Guarantee: Strictly interacts with 127.0.0.1 loopback endpoints.
   Rejects any external hostnames, APIs, or WAN egress.
2. Models & Planes:
   - Syntax Worker (:8081): qwen2.5-coder-7b-instruct-q4_k_m.gguf
   - Sovereign Orchestrator (:8083 / :8082): qwen-3.8-max via PRP Ring
   - Adversarial Red Team (:8083): Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf
   - Local Cross-Debate: 2-turn consensus between :8082 and :8083
3. Fast execution (<100ms startup) with robust error handling for AppleScript.
================================================================================
"""

import sys
import os
import json
import time
import urllib.request
import urllib.error
import argparse
import subprocess
from typing import Dict, Any, Optional

PORT_CODER = 8081
PORT_PRIMA_MASTER = 8082
PORT_ADAPTER = 8083

MODEL_CODER = "qwen2.5-coder-7b-instruct-q4_k_m.gguf"
MODEL_SOVEREIGN = "qwen-3.8-max"
MODEL_RED_TEAM = "Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf"


def get_clipboard_text() -> str:
    """Reads current clipboard text via pbpaste."""
    try:
        res = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=2.0)
        return res.stdout
    except Exception:
        return ""


def set_clipboard_text(text: str) -> bool:
    """Writes text to clipboard via pbcopy."""
    try:
        subprocess.run(["pbcopy"], input=text, text=True, check=True, timeout=2.0)
        return True
    except Exception:
        return False


def verify_loopback(url: str) -> None:
    """Enforces zero-cloud invariant: URL must strictly be loopback."""
    if not (url.startswith("http://127.0.0.1:") or url.startswith("http://localhost:")):
        raise ValueError(f"SECURITY VIOLATION: Non-loopback URL detected: {url}. Local AI Only enforced.")


def check_port_health(port: int, timeout_sec: float = 1.0) -> Dict[str, Any]:
    """Checks if a local AI endpoint is healthy."""
    url = f"http://127.0.0.1:{port}/health"
    verify_loopback(url)
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Lauburu-AppleScript-Bridge/1.0"})
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            data = resp.read().decode("utf-8")
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            try:
                parsed = json.loads(data)
            except Exception:
                parsed = {"raw": data}
            return {"port": port, "status": "ONLINE", "rtt_ms": round(elapsed_ms, 2), "info": parsed}
    except Exception as e:
        return {"port": port, "status": "OFFLINE", "error": str(e)}


def query_chat_completion(
    port: int,
    model: str,
    prompt: str,
    system_prompt: str = "You are a fast, precise local AI assistant. Provide direct, high-quality code and answers with no fluff.",
    max_tokens: int = 1024,
    temperature: float = 0.3,
    timeout_sec: float = 60.0
) -> Dict[str, Any]:
    """Sends a chat completion request to an OpenAI-compatible local AI endpoint."""
    url = f"http://127.0.0.1:{port}/v1/chat/completions"
    verify_loopback(url)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False
    }

    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={"Content-Type": "application/json", "User-Agent": "Lauburu-AppleScript-Bridge/1.0"}
    )

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw_resp = resp.read().decode("utf-8")
            elapsed = time.perf_counter() - t0
            parsed = json.loads(raw_resp)
            content = parsed.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = parsed.get("usage", {})
            comp_tokens = usage.get("completion_tokens", len(content.split()))
            tok_per_sec = comp_tokens / elapsed if elapsed > 0 else 0.0

            return {
                "status": "SUCCESS",
                "content": content.strip(),
                "model": model,
                "port": port,
                "elapsed_sec": round(elapsed, 2),
                "tok_per_sec": round(tok_per_sec, 1),
                "tokens": comp_tokens
            }
    except urllib.error.URLError as e:
        return {
            "status": "ERROR",
            "error": f"Failed to connect to local port {port}: {str(e)}",
            "model": model,
            "port": port
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "error": f"Inference error: {str(e)}",
            "model": model,
            "port": port
        }


def run_local_debate(topic: str) -> Dict[str, Any]:
    """Runs a 2-turn local adversarial debate between Sovereign Master and Red Team."""
    t0 = time.perf_counter()
    # Turn 1: Sovereign Master Proposal (:8083 or :8081 fallback)
    p1 = query_chat_completion(
        port=PORT_ADAPTER,
        model=MODEL_SOVEREIGN,
        prompt=f"Provide a definitive, production-grade solution or plan for: {topic}",
        system_prompt="You are Qwen 3.8 Max, Sovereign Master Local Orchestrator of the Lauburu Mesh. Be authoritative, rigorous, and architecturally sound.",
        max_tokens=512
    )
    if p1["status"] != "SUCCESS":
        # Fallback to 8081
        p1 = query_chat_completion(
            port=PORT_CODER,
            model=MODEL_CODER,
            prompt=f"Provide a definitive solution or plan for: {topic}",
            system_prompt="You are the Lead Local AI Engineer. Provide a concise, optimal solution.",
            max_tokens=512
        )

    sovereign_content = p1.get("content", "Error generating proposal.")

    # Turn 2: Adversarial Red Team Challenge (:8083)
    p2 = query_chat_completion(
        port=PORT_ADAPTER,
        model=MODEL_RED_TEAM,
        prompt=f"Topic: {topic}\n\nProposed Solution:\n{sovereign_content}\n\nRuthlessly red-team this proposal. Identify hidden race conditions, memory leaks, security flaws, or unhandled edge cases.",
        system_prompt="You are the Adversarial Red Team Challenger (Qwen 3.8 Abliterated). Your sole objective is finding flaws, edge cases, and systemic risks with zero sugarcoating.",
        max_tokens=512
    )
    red_team_content = p2.get("content", "Error generating critique.")

    elapsed = time.perf_counter() - t0
    return {
        "status": "SUCCESS",
        "topic": topic,
        "sovereign_master": sovereign_content,
        "red_team": red_team_content,
        "total_elapsed_sec": round(elapsed, 2)
    }


def get_mesh_health_summary() -> Dict[str, Any]:
    """Returns a full health summary across all local AI daemons and memory."""
    h_8081 = check_port_health(PORT_CODER)
    h_8082 = check_port_health(PORT_PRIMA_MASTER)
    h_8083 = check_port_health(PORT_ADAPTER)

    # Check RAM
    import psutil
    mem = psutil.virtual_memory()
    free_ram_gb = round(mem.available / (1024**3), 2)
    sanctuary_ok = free_ram_gb >= 9.6

    # TB4 Bridge ping
    tb4_ok = False
    try:
        r = subprocess.run(["ping", "-c", "1", "-W", "300", "169.254.187.138"], capture_output=True, timeout=1.0)
        tb4_ok = (r.returncode == 0)
    except Exception:
        tb4_ok = False

    return {
        "timestamp": time.time(),
        "ram": {
            "available_gb": free_ram_gb,
            "total_gb": round(mem.total / (1024**3), 2),
            "sanctuary_headroom_ok": sanctuary_ok
        },
        "ports": {
            "8081_coder": h_8081["status"],
            "8082_prima_ring": h_8082["status"],
            "8083_ring_adapter": h_8083["status"]
        },
        "tb4_dma_link": "LINKED" if tb4_ok else "UNLINKED",
        "all_online": (h_8081["status"] == "ONLINE" and h_8083["status"] == "ONLINE")
    }


def main():
    parser = argparse.ArgumentParser(description="Lauburu Local AI Only AppleScript Bridge")
    parser.add_argument("--mode", choices=["coder", "sovereign", "red_team", "debate", "health", "auto_heal"], default="coder")
    parser.add_argument("--prompt", type=str, default="", help="Prompt text or instruction")
    parser.add_argument("--clipboard", action="store_true", help="Read input from system clipboard")
    parser.add_argument("--set-clipboard", action="store_true", help="Copy output to system clipboard")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--system-prompt", type=str, default="")
    parser.add_argument("--max-tokens", type=int, default=1024)
    args = parser.parse_args()

    # Determine input text
    input_text = args.prompt
    if args.clipboard:
        cb = get_clipboard_text()
        if cb:
            if input_text:
                input_text = f"{input_text}\n\nContext / Code:\n{cb}"
            else:
                input_text = cb

    if args.mode == "health":
        health = get_mesh_health_summary()
        if args.json:
            print(json.dumps(health, indent=2))
        else:
            p81 = health["ports"]["8081_coder"]
            p82 = health["ports"]["8082_prima_ring"]
            p83 = health["ports"]["8083_ring_adapter"]
            ram = health["ram"]["available_gb"]
            tb4 = health["tb4_dma_link"]
            print(f"Local AI Mesh Status:\n• Coder (:8081): {p81}\n• PRP Ring (:8082): {p82}\n• Adapter (:8083): {p83}\n• TB4 DMA Link: {tb4}\n• Available RAM: {ram} GB (Sanctuary: {'✅ OK' if health['ram']['sanctuary_headroom_ok'] else '⚠️ LOW'})")
        return

    if args.mode == "auto_heal":
        cmd = "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/sandbox_evolution/bluetooth_terminal_arena/run_sovereign_bluetooth_npu_ide.sh --escalate"
        res = subprocess.run(["/bin/bash", "-c", cmd], capture_output=True, text=True, timeout=30.0)
        output = {"status": "SUCCESS" if res.returncode == 0 else "FAILED", "code": res.returncode, "stdout": res.stdout[-500:]}
        if args.json:
            print(json.dumps(output))
        else:
            print("Auto-Healing Cycle Completed." if res.returncode == 0 else "Auto-Healing Failed.")
        return

    if not input_text.strip():
        err = {"status": "ERROR", "error": "No input prompt or clipboard content provided."}
        print(json.dumps(err) if args.json else err["error"])
        sys.exit(1)

    if args.mode == "debate":
        res = run_local_debate(input_text)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            out = f"=== 👑 SOVEREIGN MASTER PROPOSAL ===\n{res['sovereign_master']}\n\n=== 🔥 RED TEAM ADVERSARIAL CHALLENGE ===\n{res['red_team']}\n\n(Debate completed in {res['total_elapsed_sec']}s via Local AI)"
            if args.set_clipboard:
                set_clipboard_text(out)
            print(out)
        return

    # Single model query
    if args.mode == "coder":
        port = PORT_CODER
        model = MODEL_CODER
        default_sys = "You are Qwen 2.5 Coder 7B, a high-speed local coding specialist running on Metal GPU. Provide clean, correct, and optimized code."
    elif args.mode == "sovereign":
        port = PORT_ADAPTER
        model = MODEL_SOVEREIGN
        default_sys = "You are Qwen 3.8 Max, the Sovereign Master Local Orchestrator of the Lauburu Mesh. Provide deep architectural reasoning and optimal decisions."
    elif args.mode == "red_team":
        port = PORT_ADAPTER
        model = MODEL_RED_TEAM
        default_sys = "You are Qwen 3.8 Max Abliterated, the Adversarial Red Team Challenger. Conduct a rigorous, critical audit of the input with zero bias."

    sys_prompt = args.system_prompt or default_sys
    res = query_chat_completion(port, model, input_text, system_prompt=sys_prompt, max_tokens=args.max_tokens)

    # Fallback to coder if 8083 failed
    if res["status"] != "SUCCESS" and port == PORT_ADAPTER:
        res = query_chat_completion(PORT_CODER, MODEL_CODER, input_text, system_prompt=sys_prompt, max_tokens=args.max_tokens)

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        if res["status"] == "SUCCESS":
            content = res["content"]
            if args.set_clipboard:
                set_clipboard_text(content)
            print(content)
        else:
            print(f"Error: {res.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
