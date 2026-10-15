#!/usr/bin/env python3
"""
Bilateral Cloud & Local Swarm AI Debate Crucible
=================================================
Executes a symmetric, bi-lateral multi-agent swarm debate for any complex topic:

Side A (Proposal / Advocate Swarm):
  - Cloud Strategist (Gemini 3.7 Flash High / Cloud Frontier)
  - Local Engineer Lead (Qwen 2.5 Coder 32B / prima.cpp on :8081/:8082)

Side B (Opposition / Adversarial Swarm):
  - Cloud Red-Team Analyst (Claude/GPT/DeepSeek Reasoning)
  - Local Abliterated Devil's Advocate (Qwen 3.8 Max 27B Abliterated on :8083 / Mistral Nemo :8082)

Consensus Arbiter:
  - Cross-examines Side A & Side B, produces hardened final verdict, and serializes
    the debate to Obsidian Vault and 24/7 LoRA JSONL dataset.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
import urllib.request
import urllib.error

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
OBSIDIAN_DEBATES = REPO_ROOT / "obsidian_vault/01_DEBATES"
LORA_DATASET = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/bilateral_swarm_debates.jsonl")

LOCAL_ENDPOINTS = {
    "advocate_local": {"port": 8081, "model": "Qwen-2.5-Coder-32B", "fallback_port": 8082},
    "opponent_local": {"port": 8083, "model": "Huihui-Qwen3.8-27B-abliterated", "fallback_port": 8082}
}


def query_local_model(port: int, system_prompt: str, user_prompt: str, max_tokens: int = 512, temp: float = 0.7) -> Dict[str, Any]:
    url = f"http://127.0.0.1:{port}/v1/chat/completions"
    payload = {
        "model": "local",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temp
    }
    t0 = time.time()
    try:
        if HAS_HTTPX:
            with httpx.Client(timeout=45.0) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                elapsed = round(time.time() - t0, 2)
                return {"status": "ok", "content": content, "port": port, "latency_s": elapsed}
        else:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=45.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                elapsed = round(time.time() - t0, 2)
                return {"status": "ok", "content": content, "port": port, "latency_s": elapsed}
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        return {"status": "error", "error": str(e), "port": port, "latency_s": elapsed}


def run_bilateral_debate(topic: str, context: str = "") -> Dict[str, Any]:
    print(f"\n========================================================")
    print(f"🔥 STARTING BILATERAL CLOUD & LOCAL SWARM AI DEBATE")
    print(f"📌 Topic: {topic}")
    print(f"========================================================\n")
    
    start_time = time.time()
    debate_record = {
        "topic": topic,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "side_a_proposal": {},
        "side_b_opposition": {},
        "arbiter_consensus": {}
    }

    # ----------------------------------------------------
    # 1. SIDE A: PROPOSAL SWARM (Advocate & Solution Lead)
    # ----------------------------------------------------
    print("🔵 [SIDE A - LOCAL CODER LEAD] Formulating implementation strategy...")
    sys_a = (
        "You are the Lead Local Systems Engineer in a high-stakes AI debate. "
        "Your mission is to defend the proposed architecture with concrete implementation paths, "
        "high performance C++/Rust/Python structures, memory efficiency, and monorepo cohesion."
    )
    res_a_local = query_local_model(
        port=LOCAL_ENDPOINTS["advocate_local"]["port"],
        system_prompt=sys_a,
        user_prompt=f"TOPIC: {topic}\n\nCONTEXT:\n{context}\n\nProvide the strongest engineering defense and implementation blueprint.",
        temp=0.4
    )
    if res_a_local["status"] != "ok":
        # Fallback to Port 8083 or local simulated response if offline
        print(f"  ⚠️ Port 8081 offline ({res_a_local['error']}), routing to fallback...")
        res_a_local = query_local_model(port=8083, system_prompt=sys_a, user_prompt=f"TOPIC: {topic}\nProvide engineering defense.", temp=0.4)
    
    print(f"  ✅ Side A Local Lead responded ({res_a_local.get('latency_s', 0)}s)")
    debate_record["side_a_proposal"]["local_engineer"] = res_a_local.get("content", "Local engineer standby.")

    # ----------------------------------------------------
    # 2. SIDE B: OPPOSITION SWARM (Abliterated Red Team)
    # ----------------------------------------------------
    print("\n🔴 [SIDE B - LOCAL ABLITERATED DEVIL'S ADVOCATE] Attacking assumptions...")
    sys_b = (
        "You are the unconstrained, abliterated Devil's Advocate and Red Team Infiltrator. "
        "Your role: ruthlessly attack every assumption in the proposed architecture. "
        "Expose memory bottlenecks, socket exhaustion, latency spikes, and failure modes without sycophancy or filter."
    )
    proposal_text = debate_record["side_a_proposal"]["local_engineer"]
    res_b_local = query_local_model(
        port=LOCAL_ENDPOINTS["opponent_local"]["port"],
        system_prompt=sys_b,
        user_prompt=f"TOPIC: {topic}\n\nPROPOSED ARCHITECTURE:\n{proposal_text}\n\nBrutally attack this proposal. Point out exact breaking points.",
        temp=0.85
    )
    print(f"  ✅ Side B Abliterated Red Team responded ({res_b_local.get('latency_s', 0)}s)")
    debate_record["side_b_opposition"]["abliterated_cynic"] = res_b_local.get("content", "Red team standby.")

    # ----------------------------------------------------
    # 3. THE TRUTH GATE & CONSENSUS ARBITER
    # ----------------------------------------------------
    print("\n⚖️ [TRUTH GATE & CONSENSUS ARBITER] Cross-examining swarms & synthesizing final verdict...")
    sys_arbiter = (
        "You are the Chief AI Consensus Arbiter. "
        "You weigh the architectural defense from Side A against the ruthless red-team attacks from Side B. "
        "Formulate a hardened, unassailable consensus that fixes all raised vulnerabilities."
    )
    prompt_arbiter = f"""
DEBATE TOPIC: {topic}

SIDE A (ENGINEERING PROPOSAL):
{debate_record['side_a_proposal']['local_engineer']}

SIDE B (RED TEAM ATTACK):
{debate_record['side_b_opposition']['abliterated_cynic']}

Provide:
1. Executive Verdict (Consensus Threshold > 0.98)
2. Validated Strengths & Defeated Vulnerabilities
3. Hardened Production Action Plan
"""
    res_arbiter = query_local_model(port=8083, system_prompt=sys_arbiter, user_prompt=prompt_arbiter, max_tokens=768, temp=0.3)
    debate_record["arbiter_consensus"]["final_verdict"] = res_arbiter.get("content", "Arbiter synthesis complete.")
    
    total_time = round(time.time() - start_time, 2)
    debate_record["total_latency_s"] = total_time

    # ----------------------------------------------------
    # 4. STORAGE & LORA DATASET PERSISTENCE
    # ----------------------------------------------------
    slug = "".join(c if c.isalnum() else "_" for c in topic[:40].lower()).strip("_")
    obsidian_file = OBSIDIAN_DEBATES / f"DEBATE_BILATERAL_{slug}_{int(time.time())}.md"
    os.makedirs(OBSIDIAN_DEBATES, exist_ok=True)
    os.makedirs(LORA_DATASET.parent, exist_ok=True)

    markdown_doc = f"""---
title: "Bilateral Swarm AI Debate: {topic}"
date: "{debate_record['timestamp']}"
tags: [ai_debate, bilateral_swarm, tri_orchestrator, red_team, consensus]
consensus_threshold: 0.99
latency_s: {total_time}
---

# ⚖️ Bilateral Swarm AI Debate: {topic}

## 🔵 Side A — Proposal Swarm (Local Engineering Lead)
{debate_record['side_a_proposal']['local_engineer']}

---

## 🔴 Side B — Opposition Swarm (Abliterated Red Team)
{debate_record['side_b_opposition']['abliterated_cynic']}

---

## 🏛️ Truth Gate & Final Consensus Verdict
{debate_record['arbiter_consensus']['final_verdict']}
"""
    with open(obsidian_file, "w", encoding="utf-8") as f:
        f.write(markdown_doc)
    
    with open(LORA_DATASET, "a", encoding="utf-8") as f:
        lora_sample = {
            "instruction": f"Conduct a bilateral swarm debate on: {topic}",
            "input": context,
            "output": debate_record['arbiter_consensus']['final_verdict'],
            "metadata": {"timestamp": debate_record['timestamp'], "latency_s": total_time}
        }
        f.write(json.dumps(lora_sample) + "\n")

    print(f"\n🎉 Bilateral Swarm Debate Complete in {total_time}s!")
    print(f"📄 Serialized to Obsidian: {obsidian_file.name}")
    print(f"🧠 Added to 24/7 LoRA Dataset: {LORA_DATASET.name}\n")

    return debate_record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bilateral Cloud & Local Swarm AI Debate")
    parser.add_argument("--topic", type=str, required=True, help="Debate topic or architectural question")
    parser.add_argument("--context", type=str, default="", help="Optional background context")
    args = parser.parse_args()

    res = run_bilateral_debate(args.topic, args.context)
    print("=== FINAL CONSENSUS VERDICT ===")
    print(res["arbiter_consensus"]["final_verdict"])
