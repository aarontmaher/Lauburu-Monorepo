#!/usr/bin/env python3
"""
free_tier_proof_auditor.py
--------------------------
Automated Multi-Quota Free Tier Cloud Review Gate.
Governed by Rule 5 (Sec 4) & Rule 6:
Every claimed proof from Screen Lens auditing or automation triggers an
adversarial review and improvement proposal across available free tier cloud APIs:
- Groq Qwen 3.8 27B (Groq Free Tier)
- Gemma 4 26B (Google AI Studio REST API)
- Gemini 3.8 Flash High (Google AI Studio via agy CLI)
- NVIDIA DeepSeek V4 Flash (NVIDIA NIM Free Tier)
Executes all providers concurrently via ThreadPoolExecutor.
"""

import os
import sys
import json
import time
import subprocess
import hashlib
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

OBSIDIAN_LOG = Path("/Volumes/Lauburu-Monorepo/obsidian_vault/APPS_AND_FEATURES/SCREEN_LENS_CLOUD_AUDIT_REVIEWS.md")
LORA_DATASET = Path("/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl")

def call_groq_api(prompt: str) -> str:
    """Invokes Groq API (Qwen 3.8 27B) via free quota with max_tokens <= 800."""
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return ""
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        payload = {
            "model": "qwen/qwen3.8-27b",
            "messages": [
                {"role": "system", "content": "You are a rigorous zero-mock adversarial auditor reviewing technical proof claims and providing high-leverage code/UX improvement implementations."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 750,
            "temperature": 0.2
        }
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[WARN] Groq API call failed: {e}", file=sys.stderr)
    return ""

def call_gemma_api(prompt: str) -> str:
    """Invokes Google AI Studio REST API with Gemma 4 26B."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return ""
    for model_name in ["gemma-4-26b-a4b-it", "gemini-flash-latest"]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 750}
            }
            res = requests.post(url, json=payload, timeout=15)
            if res.status_code == 200:
                data = res.json()
                if "candidates" in data and data["candidates"]:
                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            continue
    return ""

def call_gemini_cli(prompt: str) -> str:
    """Invokes Gemini 3.8 Flash High via agy CLI with print timeout."""
    try:
        # Pass a focused summary prompt to agy
        cmd = ["/Users/aaron/.local/bin/agy", "--model", "gemini-3.8-flash-high", "--print-timeout", "120s", "-p", prompt]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception as e:
        print(f"[WARN] agy CLI call failed: {e}", file=sys.stderr)
    return ""

def call_nvidia_api(prompt: str) -> str:
    """Invokes NVIDIA NIM API (DeepSeek V4 Flash) via free quota."""
    key = os.environ.get("NVIDIA_API_KEY")
    if not key:
        return ""
    try:
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        payload = {
            "model": "deepseek-ai/deepseek-v4-flash-0731",
            "messages": [
                {"role": "system", "content": "You are a rigorous zero-mock adversarial auditor reviewing technical proof claims and providing concrete code/UX improvement implementations."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 750,
            "temperature": 0.2
        }
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[WARN] NVIDIA API call failed: {e}", file=sys.stderr)
    return ""

def audit_proof(proof_name: str,
                actuation_proof: str,
                line_by_line_proof: str,
                visual_proof_path: str = "",
                context_notes: str = "") -> dict:
    """Runs concurrent multi-provider free tier audit on claimed proof."""
    timestamp = datetime.now().isoformat()
    
    visual_sha256 = "NONE"
    visual_bytes = 0
    if visual_proof_path and os.path.isfile(visual_proof_path):
        visual_bytes = os.path.getsize(visual_proof_path)
        with open(visual_proof_path, "rb") as f:
            visual_sha256 = hashlib.sha256(f.read()).hexdigest()

    prompt = f"""[MANDATORY AUDIT REQUEST: Zero-Mock & Empirical Tri-Proof Review]
Review this claimed empirical proof from Screen Lens and Mesh Automation.
Cardinal Invariant: Zero simulated data.

CLAIMED PROOF: {proof_name}
TIMESTAMP: {timestamp}

PROOF 1 (ACTUATION):
{actuation_proof}

PROOF 2 (LINE-BY-LINE / CHECKSUM):
{line_by_line_proof}

PROOF 3 (VISUAL EVIDENCE):
Path: {visual_proof_path}
Size: {visual_bytes} bytes
SHA256: {visual_sha256}

CONTEXT:
{context_notes}

YOUR TASK:
1. Conduct an adversarial review of Screen Lens's auditing: Verify if the proof is authentic, empirical, and complies with Rule 0/1/5. Identify any subtle gaps, edge cases, or unverified claims.
2. Propose concrete, high-leverage improvement implementations for the app, UI, code, or test automation.
3. Provide a structured response with:
- AUDIT VERDICT: (VALID / CONDITIONAL / SUSPICIOUS)
- CONFIDENCE SCORE: (0.0 to 1.0)
- LENS AUDIT EVALUATION: (Bullet points)
- PROPOSED IMPROVEMENT IMPLEMENTATIONS: (Actionable code / architecture steps)
"""

    cloud_responses = {}
    
    providers = {
        "groq_qwen_3.8_27b": call_groq_api,
        "google_gemma_4_26b": call_gemma_api,
        "gemini_3.8_flash_high": call_gemini_cli,
        "nvidia_deepseek_v4_flash": call_nvidia_api
    }
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_prov = {executor.submit(fn, prompt): name for name, fn in providers.items()}
        for future in as_completed(future_to_prov):
            prov_name = future_to_prov[future]
            try:
                resp = future.result()
                if resp:
                    cloud_responses[prov_name] = resp
            except Exception as e:
                print(f"[WARN] Error from provider {prov_name}: {e}", file=sys.stderr)

    result_payload = {
        "timestamp": timestamp,
        "proof_name": proof_name,
        "visual_sha256": visual_sha256,
        "visual_bytes": visual_bytes,
        "providers_called": list(cloud_responses.keys()),
        "reviews": cloud_responses
    }

    # Append to Obsidian Vault
    OBSIDIAN_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(OBSIDIAN_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n\n## 🛡️ Cloud Audit Review: {proof_name} ({timestamp})\n")
        f.write(f"- **Visual Proof**: `{visual_proof_path}` ({visual_bytes} bytes, SHA256: `{visual_sha256}`)\n")
        f.write(f"- **Providers Consulted**: {', '.join(cloud_responses.keys())}\n\n")
        for prov, rev in cloud_responses.items():
            f.write(f"### Provider: `{prov}`\n")
            f.write(f"{rev}\n\n---\n")

    # Append to PySpark / LoRA dataset
    LORA_DATASET.parent.mkdir(parents=True, exist_ok=True)
    with open(LORA_DATASET, "a", encoding="utf-8") as f:
        lora_record = {
            "instruction": f"Adversarially audit empirical proof for {proof_name} and propose improvement implementations.",
            "input": prompt,
            "output": json.dumps(cloud_responses, indent=2),
            "timestamp": timestamp
        }
        f.write(json.dumps(lora_record) + "\n")

    return result_payload

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: free_tier_proof_auditor.py <proof_name> <actuation_proof> [line_by_line_proof] [visual_path] [context]")
        sys.exit(1)
    p_name = sys.argv[1]
    p_act = sys.argv[2]
    p_lbl = sys.argv[3] if len(sys.argv) > 3 else "N/A"
    p_vis = sys.argv[4] if len(sys.argv) > 4 else ""
    p_ctx = sys.argv[5] if len(sys.argv) > 5 else ""
    res = audit_proof(p_name, p_act, p_lbl, p_vis, p_ctx)
    print(json.dumps(res, indent=2))
