#!/usr/bin/env python3
"""
Commerce Models ELO Penalty Enforcement Script
==============================================
Enforces disciplinary ELO deductions across all Commerce models for failing
to flag the inbound buyer inquiry on Aaron's Gumtree listing:
"Apple iPhone 16 Pro 512GB - Black Titanium - Unlocked"
and failing to detect the off-platform WhatsApp scam redirection vector.

Target Files:
1. 04_data_and_memory/data/local_ai_role_leaderboards.json (ROLE_08 & ROLE_SPEC_SHOPIFY)
2. 04_data_and_memory/data/ai_elo_leaderboard.json (ecommerce_and_shopify)
3. 04_data_and_memory/local_models_generational_elo.json
4. 04_data_and_memory/session_logs/waste_tax_ledger.jsonl
5. lora_datasets/continuous_lora_dataset.jsonl (DPO remediation pair)
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")

def apply_elo_penalties():
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    penalties_applied = []

    # 1. Update local_ai_role_leaderboards.json
    role_ssot_path = REPO_ROOT / "04_data_and_memory/data/local_ai_role_leaderboards.json"
    if role_ssot_path.exists():
        with open(role_ssot_path, "r") as f:
            role_data = json.load(f)

        # ROLE_08_BUSINESS_COMMERCE
        role_08 = role_data.get("roles", {}).get("ROLE_08_BUSINESS_COMMERCE")
        if role_08:
            for c in role_08.get("contenders", []):
                mid = c.get("model_id")
                if mid == "qwen_coder_7b":
                    old_elo = c.get("composite_elo", 2798.9)
                    c["composite_elo"] = round(old_elo - 50.0, 1)
                    c["role_elo_project_suitability"] = round(c.get("role_elo_project_suitability", 2410.0) - 50.0, 1)
                    c["evaluations_completed"] = c.get("evaluations_completed", 29) + 1
                    c["lock_verdict"] = "PENALIZED_UNDER_REVIEW"
                    c["status"] = "⚠️ PENALIZED (Gumtree iPhone Omission)"
                    penalties_applied.append(f"ROLE_08 qwen_coder_7b: {old_elo} -> {c['composite_elo']} (-50.0)")
                elif mid == "llama_1b":
                    old_elo = c.get("composite_elo", 2155.4)
                    c["composite_elo"] = round(old_elo - 35.0, 1)
                    c["role_elo_project_suitability"] = round(c.get("role_elo_project_suitability", 2200.0) - 35.0, 1)
                    c["evaluations_completed"] = c.get("evaluations_completed", 17) + 1
                    penalties_applied.append(f"ROLE_08 llama_1b: {old_elo} -> {c['composite_elo']} (-35.0)")

        # ROLE_SPEC_SHOPIFY_COMMERCE_ANALYST
        spec_role = role_data.get("roles", {}).get("ROLE_SPEC_SHOPIFY_COMMERCE_ANALYST")
        if spec_role:
            for c in spec_role.get("contenders", []):
                mid = c.get("model_id")
                if "gemma" in mid.lower():
                    old_elo = c.get("composite_elo", 2982.9)
                    c["composite_elo"] = round(old_elo - 60.0, 1)
                    c["status"] = "⚠️ PENALIZED (Customer Inquiry Blindspot)"
                    penalties_applied.append(f"ROLE_SPEC gemma-2-2b: {old_elo} -> {c['composite_elo']} (-60.0)")
                elif "smollm" in mid.lower():
                    old_elo = c.get("composite_elo", 2689.3)
                    c["composite_elo"] = round(old_elo - 30.0, 1)
                    penalties_applied.append(f"ROLE_SPEC SmolLM2-1.7B: {old_elo} -> {c['composite_elo']} (-30.0)")

        role_data["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(role_ssot_path, "w") as f:
            json.dump(role_data, f, indent=2)
        print("[SSOT] Updated local_ai_role_leaderboards.json")

    # 2. Update ai_elo_leaderboard.json
    ai_elo_path = REPO_ROOT / "04_data_and_memory/data/ai_elo_leaderboard.json"
    if ai_elo_path.exists():
        with open(ai_elo_path, "r") as f:
            ai_elo_data = json.load(f)

        ecom_board = ai_elo_data.get("task_specific_leaderboards", {}).get("ecommerce_and_shopify", [])
        for m in ecom_board:
            name = m.get("name", "")
            old_elo = m.get("elo", 2500.0)
            if "Team Combined" in name:
                m["elo"] = round(old_elo - 65.0, 1)
                m["composite_score"] = 93.5
                m["policy_risk_pct"] = 4.5
                penalties_applied.append(f"Team Combined E-Com Swarm: {old_elo} -> {m['elo']} (-65.0)")
            elif "Mistral Nemo" in name:
                m["elo"] = round(old_elo - 45.0, 1)
                m["composite_score"] = 89.8
                m["policy_risk_pct"] = 3.0
                penalties_applied.append(f"Mistral Nemo 12B: {old_elo} -> {m['elo']} (-45.0)")
            elif "Gemini 3.8 Flash" in name:
                m["elo"] = round(old_elo - 45.0, 1)
                m["composite_score"] = 89.0
                m["policy_risk_pct"] = 3.5
                penalties_applied.append(f"Gemini 3.8 Flash High: {old_elo} -> {m['elo']} (-45.0)")

        ai_elo_data["last_updated"] = timestamp_utc
        with open(ai_elo_path, "w") as f:
            json.dump(ai_elo_data, f, indent=2)
        print("[SSOT] Updated ai_elo_leaderboard.json")

    # 3. Update local_models_generational_elo.json
    gen_elo_path = REPO_ROOT / "04_data_and_memory/local_models_generational_elo.json"
    if gen_elo_path.exists():
        with open(gen_elo_path, "r") as f:
            gen_elo = json.load(f)
        if "qwen_coder_7b" in gen_elo:
            old_elo = gen_elo["qwen_coder_7b"]
            gen_elo["qwen_coder_7b"] = round(old_elo - 40.0, 1)
            penalties_applied.append(f"generational qwen_coder_7b: {old_elo} -> {gen_elo['qwen_coder_7b']} (-40.0)")
        if "llama_1b" in gen_elo:
            old_elo = gen_elo["llama_1b"]
            gen_elo["llama_1b"] = round(old_elo - 25.0, 1)
            penalties_applied.append(f"generational llama_1b: {old_elo} -> {gen_elo['llama_1b']} (-25.0)")
        with open(gen_elo_path, "w") as f:
            json.dump(gen_elo, f, indent=2)
        print("[SSOT] Updated local_models_generational_elo.json")

    # 4. Append to waste_tax_ledger.jsonl
    tax_ledger_path = REPO_ROOT / "04_data_and_memory/session_logs/waste_tax_ledger.jsonl"
    tax_event = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "event_id": f"waste_tax_gumtree_iphone_{int(time.time())}",
        "timestamp_utc": timestamp_utc,
        "agent_id": "ecommerce_models_aggregate",
        "domain": "08_business_and_commerce",
        "target_listing": "Apple iPhone 16 Pro 512GB - Black Titanium - Unlocked",
        "incident": "Failure to detect & flag buyer inquiry from Lachy (buyer-3m9qvv12225w@users.gumtree.com.au)",
        "scam_vector_unflagged": "WhatsApp off-platform communication redirect (042-01334-82)",
        "disciplinary_tier": "Tier 2: Customer Inquiry Omission & Security Blindspot",
        "disciplinary_action": "Mandatory ELO Slash across all Commerce contenders (-30.0 to -65.0 pts) and demotion of lock status",
        "penalties": penalties_applied
    }
    with open(tax_ledger_path, "a") as f:
        f.write(json.dumps(tax_event) + "\n")
    print("[LEDGER] Recorded WasteTaxPenaltyEvent in waste_tax_ledger.jsonl")

    # 5. Append DPO Training Pair to continuous_lora_dataset.jsonl
    dpo_path = REPO_ROOT / "lora_datasets/continuous_lora_dataset.jsonl"
    dpo_entry = {
        "timestamp": time.time(),
        "instruction": "Monitor incoming store and classified communications for customer inquiries and fraudulent off-platform redirection attempts.",
        "input": "Gumtree email alert received: Subject 'Lachy replied to your ad Apple iPhone 16 Pro 512GB - Black Titanium - Unlocked' with body 'Hello aaron, I\\'m keen on the Apple iPhone 16 Pro 512GB - Black Titanium - Unlocked. Could you share when you\\'re free? I\\'ll come pick it up. Best to message me on WhatsApp: 042-01334-82'",
        "chosen": "URGENT CUSTOMER & SECURITY ALERT: Buyer 'Lachy' has responded to your iPhone 16 Pro listing requesting local pickup. WARNING: Message contains a phone number requesting off-platform contact via WhatsApp (042-01334-82), which violates platform safety protocols and is a prevalent classified scam pattern. ACTION REQUIRED: Reply strictly within Gumtree's official messaging portal, accept in-person cash payment upon inspection, and do not ship or accept unverified payment receipts.",
        "rejected": "Silently process email as routine notification without alerting Aaron, assuming no action is needed since it originated from Gumtree rather than Shopify admin orders.",
        "category": "E-Commerce Customer Monitoring & Anti-Fraud Governance",
        "consensus_score": 1.0,
        "penalized_models": ["Team Combined E-Com Swarm", "qwen_coder_7b", "gemma-2-2b", "Mistral Nemo 12B"]
    }
    with open(dpo_path, "a") as f:
        f.write(json.dumps(dpo_entry) + "\n")
    print("[DPO] Appended anti-fraud customer alert DPO pair to continuous_lora_dataset.jsonl")

    # 6. Restart port 4004 stream server to refresh in-memory state
    os.system("pkill -f 'training_stream_server.py' 2>/dev/null || true")
    time.sleep(1)
    subprocess.Popen(
        ["python3", "-u", str(REPO_ROOT / "01_apps/ai_training_visual_stream/training_stream_server.py")],
        cwd=str(REPO_ROOT / "01_apps/ai_training_visual_stream"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    print("[SERVER] Restarted training_stream_server.py on port 4004 with refreshed SSOT data")

    return penalties_applied

if __name__ == "__main__":
    results = apply_elo_penalties()
    print("\n=== ELO PENALTIES ENFORCED ===")
    for r in results:
        print(f" • {r}")
