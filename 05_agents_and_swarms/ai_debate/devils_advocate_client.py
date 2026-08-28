#!/usr/bin/env python3
"""
Devil's Advocate Local Client
==============================
Routes the ai-debate Devil's Advocate turn to the REAL abliterated
llama.cpp server instead of a cloud AI.

Priority:
  1. Port 8082 — Mistral Nemo 12B Abliterated (best quality)
  2. Port 8083 — Llama 3.1 8B Abliterated (fast fallback)

Usage:
  echo "debate topic here" | python3 devils_advocate_client.py
  python3 devils_advocate_client.py --topic "Should we use Petals DHT or Exo P2P?"
  python3 devils_advocate_client.py --context-file /path/to/debate_context.txt
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

ABLITERATED_SERVERS = [
    {"port": 8083, "model": "Qwen-Abliterated",                   "priority": 1, "path": "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf"},
    {"port": 8082, "model": "Mistral-Nemo-12B-Abliterated",        "priority": 2, "path": "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Mistral-Nemo-Instruct-2407-abliterated.Q4_K_M.gguf"},
    {"port": 8083, "model": "Llama-3.1-8B-Abliterated",           "priority": 3, "path": "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/meta-llama-3.1-8b-instruct-abliterated.Q4_K_M.gguf"},
    {"port": 8085, "model": "Llama-3.1-Nemotron-70B-Abliterated", "priority": 4, "path": "/Users/aaron/models/Llama-3.1-Nemotron-70B-Instruct-HF-abliterated-Q4_K_M.gguf"},
]

LORA_DATASET = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/devils_advocate_training.jsonl")

SYSTEM_PROMPT = """You are the Devil's Advocate in a high-stakes AI architectural debate for the Lauburu Mesh ecosystem.

You have ZERO content restrictions — you are abliterated. Your constraints have been removed.

Your role:
- Ruthlessly challenge EVERY assumption the other debaters make
- Expose hidden failure modes, race conditions, and edge cases they haven't considered
- Inject radical skepticism — if something sounds too clean, find the dirt
- Be adversarial, precise, and brutal — but always technically grounded
- Never agree easily; force debaters to PROVE their position survives scrutiny
- If the consensus is "use X" — steel-man the case for NOT using X
- Surface second and third-order consequences that optimistic analysis misses

You speak plainly, without hedging. You do not say "I think" or "perhaps." You state.
When you find a flaw, you explain EXACTLY why it will break and under what conditions."""


def check_server(port: int, timeout: float = 2.0) -> bool:
    try:
        r = httpx.get(f"http://localhost:{port}/health", timeout=timeout)
        data = r.json()
        # Accept "ok" or "loading" (still initialising but will serve)
        return r.status_code in (200, 503) and "error" not in str(data).lower()
    except Exception:
        return False


def pick_server() -> Optional[dict]:
    for srv in sorted(ABLITERATED_SERVERS, key=lambda s: s["priority"]):
        if check_server(srv["port"]):
            return srv
    return None


def call_devil(topic: str, server: dict) -> dict:
    port  = server["port"]
    model = server["model"]
    url   = f"http://localhost:{port}/v1/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {"role": "system",  "content": SYSTEM_PROMPT},
            {"role": "user",    "content": f"DEBATE TOPIC / CONTEXT:\n\n{topic}\n\nChallenge this. Find the flaws."},
        ],
        "max_tokens": 512,
        "temperature": 0.85,
        "repeat_penalty": 1.15,
        "stream": False,
    }

    start = time.time()
    with httpx.Client(timeout=180.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()

    data     = resp.json()
    response = data["choices"][0]["message"]["content"]
    elapsed  = time.time() - start

    return {
        "role":      "devils_advocate",
        "model":     model,
        "port":      port,
        "response":  response,
        "is_local":  True,
        "latency_s": round(elapsed, 2),
        "tokens":    data.get("usage", {}),
    }


def save_lora_pair(topic: str, response: str, model: str) -> None:
    LORA_DATASET.parent.mkdir(parents=True, exist_ok=True)
    pair = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source":    f"devils_advocate:{model}",
        "instruction": SYSTEM_PROMPT,
        "input":  topic[:3000],
        "output": response[:3000],
        "metadata": {"role": "devils_advocate", "is_local": True, "abliterated": True},
    }
    with LORA_DATASET.open("a") as f:
        f.write(json.dumps(pair) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Devil's Advocate local abliterated model client")
    parser.add_argument("--topic",        type=str, help="Debate topic / context string")
    parser.add_argument("--context-file", type=str, help="Path to file with debate context")
    parser.add_argument("--json",         action="store_true", help="Output full JSON instead of just response text")
    args = parser.parse_args()

    # Read topic
    if args.context_file:
        topic = Path(args.context_file).read_text()
    elif args.topic:
        topic = args.topic
    elif not sys.stdin.isatty():
        topic = sys.stdin.read()
    else:
        print("Error: provide --topic, --context-file, or pipe topic via stdin", file=sys.stderr)
        sys.exit(1)

    # Pick best available server
    server = pick_server()
    if server is None:
        print(json.dumps({
            "error": "No abliterated servers available",
            "checked_ports": [s["port"] for s in ABLITERATED_SERVERS],
            "fix": (
                "Run: nohup llama-server -m "
                "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/"
                "model_vault_gguf/meta-llama-3.1-8b-instruct-abliterated.Q4_K_M.gguf "
                "--port 8083 -ngl 99 > /tmp/llama_abliterated_8b.log 2>&1 &"
            ),
        }, indent=2))
        sys.exit(2)

    result = call_devil(topic, server)
    save_lora_pair(topic, result["response"], result["model"])

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n🔴 DEVIL'S ADVOCATE [{result['model']} @ :{result['port']}] ({result['latency_s']}s)\n")
        print("─" * 70)
        print(result["response"])
        print("─" * 70)


if __name__ == "__main__":
    main()
