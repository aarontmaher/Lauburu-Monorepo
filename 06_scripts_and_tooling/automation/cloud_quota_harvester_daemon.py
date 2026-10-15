#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import os
import json
import httpx
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [QuotaHarvester] %(levelname)s: %(message)s")
log = logging.getLogger("QuotaHarvester")

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
LORA_FILE = Path("/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl")
LORA_FILE.parent.mkdir(parents=True, exist_ok=True)

ENV_FILE = REPO_ROOT / ".env"
if ENV_FILE.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(ENV_FILE)
    except:
        with open(ENV_FILE, "r") as f:
            for line in f:
                if line.strip() and not line.startswith("#") and "=" in line:
                    key, val = line.strip().split("=", 1)
                    os.environ[key.strip()] = val.strip().strip("\"'")

def query_gemini_api(prompt: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key: return "ERROR: GEMINI_API_KEY not set."
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        r = httpx.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=45.0)
        if r.status_code == 200: return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return f"API ERROR: {r.status_code} - {r.text}"
    except Exception as e: return f"EXCEPTION: {str(e)}"

def score_frontier_model(m_id: str) -> float:
    """Scores a model ID to mathematically determine the 'Frontier' model available."""
    score = 0.0
    lower_id = m_id.lower()
    
    # 1. Extract Parameter Counts (The ultimate frontier metric)
    # Check for Trillion parameters (e.g., 1.5t, 1t)
    t_match = re.search(r'(\d+(?:\.\d+)?)\s*t', lower_id)
    if t_match: score += float(t_match.group(1)) * 10000  # 1.5t -> 15000 points
        
    # Check for MoE parameters (e.g., 8x22b)
    moe_match = re.search(r'(\d+)x(\d+(?:\.\d+)?)\s*b', lower_id)
    if moe_match: score += (float(moe_match.group(1)) * float(moe_match.group(2))) * 10  # 8x22 -> 1760 points
        
    # Check for Billion parameters (e.g., 405b, 70b, 72b)
    b_match = re.search(r'(?<!x)(\d+(?:\.\d+)?)\s*b', lower_id)
    if b_match: score += float(b_match.group(1)) * 10  # 405b -> 4050 points
        
    # 2. Add Context/Capability Weighting
    if "nemotron" in lower_id: score += 2000 # High quality synthetic generation
    if "deepseek" in lower_id: score += 1500
    if "grok-2" in lower_id or "grok-3" in lower_id: score += 1500
    if "pro" in lower_id: score += 500
    if "ultra" in lower_id: score += 600
    if "instruct" in lower_id: score += 100
    if "chat" in lower_id: score += 50
    
    return score

def fetch_available_model(base_url: str, api_key: str, exclude_models: list = []) -> str:
    models_url = base_url.replace("/chat/completions", "/models")
    try:
        r = httpx.get(models_url, headers={"Authorization": f"Bearer {api_key}"}, timeout=10.0)
        if r.status_code == 200:
            models = r.json().get("data", [])
            valid_models = []
            
            for m in models:
                m_id = m.get("id", "")
                lower_id = m_id.lower()
                if m_id in exclude_models: continue
                
                # HARD REJECTION: Non-text generating models
                if any(bad in lower_id for bad in ["vision", "audio", "embed", "nemoguard", "safety", "guard", "moderation", "tts", "stt", "whisper"]): 
                    continue
                valid_models.append(m_id)
                
            if not valid_models: return None
            
            # Sort valid models descending by the calculated Frontier Score
            valid_models.sort(key=lambda x: score_frontier_model(x), reverse=True)
            
            best_model = valid_models[0]
            log.info(f"Frontier Scoring Result: Selected {best_model} (Score: {score_frontier_model(best_model)}) from {len(valid_models)} candidates.")
            return best_model
                
    except Exception as e: 
        log.error(f"Failed to fetch models from {models_url}: {e}")
    return None

def query_openai_compat_api(prompt: str, provider_info: dict) -> str:
    api_key = provider_info["api_key"]
    if not api_key: return "ERROR: API_KEY not set."
    url = provider_info["url"]
    model = provider_info["model"]
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    try:
        r = httpx.post(url, json=payload, headers=headers, timeout=45.0)
        if r.status_code == 200: 
            return r.json()["choices"][0]["message"]["content"]
        return f"API ERROR: {r.status_code} - {r.text}"
    except Exception as e: 
        return f"EXCEPTION: {str(e)}"

def harvest_intelligence_loop():
    log.info("☁️ Quota Harvester initialized with Mathematical Frontier Scoring Algorithm.")
    
    providers = {
        "GOOGLE_GEMINI": {"active": True, "model": "gemini-3.8-flash", "bad_models": []},
        "NVIDIA_NIM": {"active": True, "url": "https://integrate.api.nvidia.com/v1/chat/completions", "api_key": os.environ.get("NVIDIA_API_KEY"), "model": "TRIGGER_HEAL", "bad_models": []},
        "XAI_GROK": {"active": True, "url": "https://api.x.ai/v1/chat/completions", "api_key": os.environ.get("XAI_API_KEY"), "model": "TRIGGER_HEAL", "bad_models": []},
        "GROQ": {"active": True, "url": "https://api.groq.com/openai/v1/chat/completions", "api_key": os.environ.get("GROQ_API_KEY"), "model": "TRIGGER_HEAL", "bad_models": []},
        "SAMBANOVA": {"active": True, "url": "https://api.sambanova.ai/v1/chat/completions", "api_key": os.environ.get("SAMBANOVA_API_KEY"), "model": "Meta-Llama-3.1-70B-Instruct", "bad_models": []},
        "CEREBRAS": {"active": True, "url": "https://api.cerebras.ai/v1/chat/completions", "api_key": os.environ.get("CEREBRAS_API_KEY"), "model": "qwen-3.8-27b", "bad_models": []}
    }
    
    while True:
        timestamp = datetime.now(timezone.utc).isoformat()
        prompt = "You are a Master Architect AI. Provide an advanced, step-by-step reasoning trace for orchestrating heterogeneous AI swarm tasks over a high-latency (5ms) but high-throughput mesh network using Python and gRPC. Emphasize low VRAM overhead and zero-mock constraints."
        
        for name, p_info in providers.items():
            if not p_info["active"]: continue
                
            log.info(f"📡 Dispatching to {name} (Model: {p_info['model']})...")
            
            # Initial run force-heal if set to TRIGGER_HEAL to automatically find absolute best on startup
            if p_info["model"] == "TRIGGER_HEAL":
                res = "API ERROR: 404 Force Heal"
            else:
                res = query_gemini_api(prompt) if name == "GOOGLE_GEMINI" else query_openai_compat_api(prompt, p_info)
                
            if "API ERROR: 402" in res:
                log.warning(f"Failed to harvest {name}: Out of Credits (402). 🛑 Self-Healing: Quarantining provider.")
                p_info["active"] = False
            elif any(e in res for e in ["API ERROR: 404", "API ERROR: 410", "API ERROR: 400", "API ERROR: 429"]):
                log.warning(f"Failed {name} on {p_info['model']}. 🛑 Auto-Healing to Absolute Frontier...")
                if p_info["model"] != "TRIGGER_HEAL":
                    p_info["bad_models"].append(p_info["model"])
                
                new_model = fetch_available_model(p_info["url"], p_info["api_key"], p_info["bad_models"])
                if new_model:
                    log.info(f"✨ Auto-Healed {name}! Locked absolute frontier model: {new_model}")
                    p_info["model"] = new_model
                else:
                    log.warning(f"Failed to discover new model. Quarantining {name}.")
                    p_info["active"] = False
            elif "ERROR:" in res or "EXCEPTION:" in res:
                log.warning(f"Failed to harvest {name}: {res[:150]}")
            else:
                log.info(f"✅ Harvested {name}. Appending to continuous_lora_dataset.jsonl")
                record = {"interaction_type": "CLOUD_HARVESTED_COT", "timestamp": timestamp, "provider": name, "prompt": prompt, "reasoning_trace": res}
                with open(LORA_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")
                
                # --- GCP FREE TIER REPLENISHABLE INTEGRATION ---
                # Mirroring the dataset directly to BigQuery
                try:
                    from google.cloud import bigquery
                    bq_client = bigquery.Client(project="acoustic-welder-508220-n7")
                    table_ref = "acoustic-welder-508220-n7.lauburu_mesh.continuous_lora_dataset"
                    errors = bq_client.insert_rows_json(table_ref, [record])
                    if errors:
                        log.warning(f"Failed BigQuery push (table might not exist yet): {errors}")
                    else:
                        log.info(f"✅ Replicated LoRA row to BigQuery {table_ref} (Free Tier 1TB/mo)")
                except ImportError:
                    pass
                except Exception as e:
                    # Catch authentication/permissions errors transparently without crashing the daemon
                    log.warning(f"BigQuery ADC Auth pending. Error: {str(e)[:100]}")
                # -----------------------------------------------
        
        time.sleep(60.0)

if __name__ == "__main__":
    harvest_intelligence_loop()
