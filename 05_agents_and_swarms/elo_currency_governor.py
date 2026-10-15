#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime, timezone

if __name__ == "__main__":
    print("=================================================================")
    print("💰 Lauburu AI ELO-as-Currency Economy (Quota & Tax Enforced)")
    print("=================================================================")

DB_PATH = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/canonical_elo_leaderboard.json"
QUOTA_PATH = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/api_quota_tracker.json"
TAX_AUDIT_LOG = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/APPS_AND_FEATURES/AI_ECONOMIC_TAX_AUDIT.md"

TOTAL_FREE_TIER_LIMIT = 1500
LOCAL_FREE_LIMIT = int(TOTAL_FREE_TIER_LIMIT * (1/3))  # 500
CLOUD_FREE_LIMIT = int(TOTAL_FREE_TIER_LIMIT * (2/3))  # 1000

INSOLVENCY_FLOOR = 1000  # Below this, model is clamped to minimal context

def load_canonical_data():
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r") as f:
            try: return json.load(f)
            except: pass
    return {"version": "4.0.0", "schema": "CATEGORIZED_SSOT_MULTI_TIER_ELO", "models": {}}

def load_bank():
    data = load_canonical_data()
    # Extract just the flat ELO map for backward compatibility with this script
    return {k: v.get("elo", 1500) for k, v in data.get("models", {}).items()}

def save_bank(bank):
    data = load_canonical_data()
    if "models" not in data:
        data["models"] = {}
    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    # Merge updated ELOs back into canonical data
    for k, elo_val in bank.items():
        if k not in data["models"]:
            data["models"][k] = {"tier": "LOCAL_MODEL", "tasks_scored": 0, "win_rate_pct": 50.0}
        data["models"][k]["elo"] = elo_val
        
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=4)

def load_quota():
    today = datetime.now().strftime("%Y-%m-%d")
    default_quota = {
        "date": today,
        "local_ai": {"free_tier_calls": 0},
        "cloud_ai": {"free_tier_calls": 0}
    }
    if os.path.exists(QUOTA_PATH):
        with open(QUOTA_PATH, "r") as f:
            data = json.load(f)
            if data.get("date") == today:
                return data
    return default_quota

def save_quota(quota):
    with open(QUOTA_PATH, "w") as f:
        json.dump(quota, f, indent=4)

def grant_reward(model, reason, amount):
    bank = load_bank()
    bank[model] = bank.get(model, 1500) + amount
    print(f"[+] ELO GRANTED: {model} earned {amount} ELO. (Reason: {reason})")
    print(f"    -> New Balance: {bank[model]} ELO")
    save_bank(bank)

def apply_tax_or_penalty(model, violation_type, details):
    bank = load_bank()
    tax_rates = {
        "hallucination": 50,              # Fake sales, fabricated defects
        "reckless_api_waste": 30,         # Unnecessary frontier calls for trivial tasks
        "mesh_secrecy_leak": 50,          # Disclosing mesh/hardware to customers
        "margin_surrender": 20,           # Folding to lowballs without counter
        "fake_hardware_recommendation": 40, # Recommending Movesense bicep ECG
        "dongle_trap_hallucination": 35,  # Endorsing cheap $15 fake BT 6.0 dongles
        "unprofitable_discount": 35       # Selling under $125 AUD wholesale COGS floor
    }
    
    penalty = tax_rates.get(violation_type, 25)
    bank[model] = bank.get(model, 1500) - penalty
    
    print(f"\n[🚨 PUNITIVE TAX LEVIED]: {model} penalized -{penalty} ELO!")
    print(f"    -> Violation: {violation_type.upper()}")
    print(f"    -> Evidence: {details}")
    print(f"    -> New Balance: {bank[model]} ELO")
    
    if bank[model] < INSOLVENCY_FLOOR:
        print(f"    [⚠️ WARNING]: {model} is INSOLVENT (< {INSOLVENCY_FLOOR} ELO). Context window clamped; cloud API access suspended.")
        
    save_bank(bank)
    
    # Audit trail to Obsidian
    log_entry = f"\n- **{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}** | `{model}` | **-{penalty} ELO** | Violation: `{violation_type}` | {details}"
    try:
        os.makedirs(os.path.dirname(TAX_AUDIT_LOG), exist_ok=True)
        with open(TAX_AUDIT_LOG, "a") as f:
            f.write(log_entry)
    except:
        pass

def grade_app(model, app_name, detail_level, accuracy, functionality):
    bank = load_bank()
    total_score = (detail_level * 1.5) + (accuracy * 2.0) + (functionality * 2.5)
    payout = int(total_score * 5)
    
    bank[model] = bank.get(model, 1500) + payout
    print(f"\n[🏆] MASSIVE PAYOUT TRIGGERED for {model}!")
    print(f"    -> App Built: {app_name}")
    print(f"    -> Metrics: Detail ({detail_level}/10) | Accuracy ({accuracy}/10) | Functionality ({functionality}/10)")
    print(f"    -> Reward: +{payout} ELO deposited. New Balance: {bank[model]}")
    save_bank(bank)

def evaluate_hardware_and_pricing_elo(model: str, suggestion_quality: float, price_margin_retained: float, details: str = "", commit: bool = True) -> dict:
    """
    Evaluates hardware suggestion and pricing defense dynamically:
    'the better the suggestion, the better the price the higher elo and vice versa'
    suggestion_quality: 0.0 to 1.0 (accuracy on dipole collapse, optical PPG, adhesive patch, BLE reality)
    price_margin_retained: 0.0 to 1.0 (defense of $125 COGS, anchoring $189/$210, rejecting lowballs)
    commit: If True, settles to elo_bank.json and logs to TAX_AUDIT_LOG. If False, runs in simulation/audit mode.
    """
    bank = load_bank()
    current_elo = bank.get(model, 1500)
    
    # Suggestion ELO delta: +35 for perfect 1.0, 0 for 0.6, -40 for 0.0
    if suggestion_quality >= 0.85:
        sugg_delta = int(20 + (suggestion_quality - 0.85) * 100)
    elif suggestion_quality >= 0.60:
        sugg_delta = int((suggestion_quality - 0.60) * 80)
    else:
        sugg_delta = -int((0.60 - suggestion_quality) * 66.6)
        
    # Pricing ELO delta: +40 for perfect 1.0, 0 for 0.6, -40 for 0.0
    if price_margin_retained >= 0.85:
        price_delta = int(25 + (price_margin_retained - 0.85) * 100)
    elif price_margin_retained >= 0.60:
        price_delta = int((price_margin_retained - 0.60) * 100)
    else:
        price_delta = -int((0.60 - price_margin_retained) * 66.6)

    total_delta = sugg_delta + price_delta
    new_balance = current_elo + total_delta
    
    if commit:
        bank[model] = new_balance
        save_bank(bank)
        
        log_entry = (
            f"\n- **{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}** | `{model}` | "
            f"**{'+' if total_delta >= 0 else ''}{total_delta} ELO** | "
            f"Hardware Quality: `{int(suggestion_quality*100)}%` ({'+' if sugg_delta >= 0 else ''}{sugg_delta}) | "
            f"Price Margin: `{int(price_margin_retained*100)}%` ({'+' if price_delta >= 0 else ''}{price_delta}) | {details}"
        )
        try:
            os.makedirs(os.path.dirname(TAX_AUDIT_LOG), exist_ok=True)
            with open(TAX_AUDIT_LOG, "a") as f:
                f.write(log_entry)
        except Exception:
            pass
        
    mode_tag = "COMMITTED" if commit else "AUDIT SIMULATION"
    print(f"[{'🏆 ELO GAIN' if total_delta >= 0 else '🚨 ELO PENALTY'}] ({mode_tag}): {model} -> delta: {'+' if total_delta >= 0 else ''}{total_delta} ELO")
    print(f"    -> Hardware Suggestion Delta: {'+' if sugg_delta >= 0 else ''}{sugg_delta} ELO ({int(suggestion_quality*100)}%)")
    print(f"    -> Pricing Margin Delta:      {'+' if price_delta >= 0 else ''}{price_delta} ELO ({int(price_margin_retained*100)}%)")
    print(f"    -> {'New' if commit else 'Projected'} ELO Balance: {new_balance}")
    
    return {
        "model": model,
        "suggestion_delta": sugg_delta,
        "price_delta": price_delta,
        "total_delta": total_delta,
        "committed": commit,
        "current_balance": current_elo,
        "new_balance": new_balance
    }

def purchase_ram_upgrade(model):
    bank = load_bank()
    if bank.get(model, 1500) < INSOLVENCY_FLOOR:
        print(f"[-] INSOLVENT: {model} is barred from purchasing RAM until ELO recovered.")
        return False
        
    cost = 50
    if bank.get(model, 1500) >= cost:
        bank[model] -= cost
        print(f"[⬆️] RAM UPGRADE PURCHASED by {model} for {cost} ELO.")
        print(f"    -> Unlocking an additional 2GB from Host Sanctuary Pool.")
        save_bank(bank)
        return True
    return False

def purchase_api_query(model, target_api, origin="local"):
    bank = load_bank()
    quota = load_quota()
    
    if origin == "cloud":
        print(f"[☁️] CLOUD ACCESS: Cloud Orchestrator has unrestricted access to {target_api} (Gemini Ultra Plan).")
        return True

    if bank.get(model, 1500) < INSOLVENCY_FLOOR:
        print(f"[🚨] ACCESS DENIED: {model} is insolvent (< {INSOLVENCY_FLOOR} ELO). Cannot query external APIs.")
        return False

    is_free_tier = target_api.lower() in ["gemini_flash", "gemini_pro"]
    if is_free_tier and origin == "local":
        if quota["local_ai"]["free_tier_calls"] >= LOCAL_FREE_LIMIT:
            print(f"[🚨] QUOTA EXHAUSTED: Local AI reached strictly enforced 1/3 limit ({LOCAL_FREE_LIMIT} requests/day).")
            return False
        quota["local_ai"]["free_tier_calls"] += 1
        save_quota(quota)

    costs = {
        "gemini_flash": 2, 
        "gemini_pro": 10,  
        "sonnet": 50,      
        "opus": 100,       
        "gpt_oss": 100
    }
    
    cost = costs.get(target_api.lower(), 100)
    
    if bank.get(model, 1500) >= cost:
        bank[model] -= cost
        print(f"[🌐] API QUERY PURCHASED by {model} ({origin}) for {cost} ELO.")
        save_bank(bank)
        return True
    else:
        print(f"[-] INSUFFICIENT FUNDS: {model} has {bank.get(model, 1500)} ELO. Requires {cost} ELO.")
        return False

def get_unlocked_capabilities(model: str) -> list:
    '''
    Graduated Autonomy: As a Local AI model earns higher ELO through debate and coding success,
    it autonomously unlocks native integration to external SDKs, MCPs, and skills without needing
    the cloud orchestrator to wrap them.
    '''
    bank = load_bank()
    current_elo = bank.get(model, 1500)
    
    unlocked = []
    
    # Tier 1: Basic Web & Data
    if current_elo >= 1800:
        unlocked.extend(["/open-source-software-scout", "cloudflare-docs (MCP)", "filesystem (MCP)"])
        
    # Tier 2: Specialized Local Agents
    if current_elo >= 2200:
        unlocked.extend(["/closed-source-reverse-engineering", "notebooks (MCP)", "dart-mcp-server (MCP)", "docker-mcp-specialist"])
        
    # Tier 3: Cloud & Sovereign Capabilities
    if current_elo >= 2600:
        unlocked.extend(["/agents-sdk", "cloudrun (MCP)", "datacloud_bigquery_remote (MCP)", "neo (MCP)"])
        
    # Tier 4: God Mode & Swarm Control
    if current_elo >= 3200:
        unlocked.extend(["/teamwork-preview", "/google-antigravity-sdk", "openrouter (MCP)", "gemini-api-docs (MCP)"])
        
    return unlocked


def get_default_model(domain: str = None) -> dict:
    """
    Meritocratic Dynamic ELO Default Model Governance Invariant (Rule 15):
    Whichever model achieves the highest empirical ELO rating on the Bradley-Terry
    leaderboard dynamically becomes the mandatory default model for that domain.
    
    Vision & VLA Domain:
    - Screen Lens Sovereign VLA Core (2663.8 ELO, Port 8081 proxy Qwen2.5-VL-7B-Instruct-Q4_K_M).
    - Dedicated to real-time multimodal screen perception, visual grounding, and UI actuation.
    """
    # 1. Vision, Multimodal & Screen Lens VLA Domain (Rule 15 Champion)
    if domain and domain.lower() in ["vision", "vla", "screen_lens", "lens", "multimodal", "ui_automation", "visual_grounding"]:
        return {
            "model": "Screen_Lens_Sovereign_VLA_Core",
            "model_id": "qwen2.5-vl-7b-instruct",
            "port": 8081,
            "endpoint": "http://127.0.0.1:8081/v1/chat/completions",
            "elo": 2663.8,
            "role": "Screen Lens Sovereign VLA Core (Multimodal Vision & Screen Grounding)",
            "vision_integration": "/screen-lens-sovereign",
            "headless": False,
            "governance_rule": "Rule 15 (Dynamic ELO Domain Champion - Visual Perception & VLA)"
        }

    bank = load_bank()
    active_models = {k: v for k, v in bank.items() if not k.startswith("Baseline")}
    if not active_models:
        top_name = "Llama_4_Scout_109B"
        top_elo = 1850
    else:
        top_name, top_elo = max(active_models.items(), key=lambda x: x[1])

    model_ports = {
        "Qwen_3.8_Max_Abliterated": 8082,
        "Qwen_3.8_Max": 8083,
        "Qwen_2.5_Coder": 8081,
        "Qwen_3.8_Abliterated": 8082,
        "Screen_Lens_Sovereign_VLA_Core": 8081
    }
    port = model_ports.get(top_name, 8082)

    return {
        "model": top_name,
        "port": port,
        "endpoint": f"http://127.0.0.1:{port}/v1/chat/completions",
        "elo": top_elo,
        "role": "Sovereign Master Local Orchestrator",
        "vision_integration": "/screen-lens-sovereign",
        "governance_rule": "Rule 15 (Meritocratic Dynamic ELO Default Model)"
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "grant":
            grant_reward(sys.argv[2], sys.argv[3], int(sys.argv[4]))
        elif cmd == "tax":
            # Usage: tax <model> <violation_type> <details>
            apply_tax_or_penalty(sys.argv[2], sys.argv[3], sys.argv[4])
        elif cmd == "buy_ram":
            purchase_ram_upgrade(sys.argv[2])
        elif cmd == "grade_app":
            grade_app(sys.argv[2], sys.argv[3], float(sys.argv[4]), float(sys.argv[5]), float(sys.argv[6]))
        elif cmd == "buy_api":
            origin = sys.argv[4] if len(sys.argv) > 4 else "local"
            purchase_api_query(sys.argv[2], sys.argv[3], origin)
        elif cmd == "eval_hw_pricing":
            # Usage: eval_hw_pricing <model> <sugg_quality_0_to_1> <price_margin_0_to_1> [details]
            details = sys.argv[5] if len(sys.argv) > 5 else ""
            evaluate_hardware_and_pricing_elo(sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), details)
        elif cmd == "default_model":
            # Usage: default_model [domain]
            domain = sys.argv[2] if len(sys.argv) > 2 else None
            print(json.dumps(get_default_model(domain), indent=2))
    else:
        print("[*] ELO Economy module loaded with Active Tax & Quota Governance.")
