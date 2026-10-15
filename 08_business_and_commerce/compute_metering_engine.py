#!/usr/bin/env python3
"""
Lauburu Mesh — Pay by Compute Functional Metering & Solvency Engine
Implements the Sovereign Break-Even & Zero-Out-Of-Pocket Invariant:
- Virtual software and local AI compute are 100% redeemable via compute tokens.
- Physical assets with hard COGS (Movesense hardware, supplements, post fees)
  can NEVER be redeemed at Aaron's expense. They strictly require settled fiat cash
  from external paying clients covering 100% of wholesale COGS + shipping.
"""

import os
import sys
import time
import json
from datetime import datetime

DATABASE_PATH = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/compute_billing_db.json"

PRICING_TABLE = {
    "qwen_38_max_local": {
        "node": "Mac_Mini_M4_Pro_L1 (40Gbps TB4 DMA)",
        "input_price_per_1m_aud": 0.20,
        "output_price_per_1m_aud": 0.80,
        "min_charge_aud": 0.0001
    },
    "qwen_38_max_abliterated": {
        "node": "Linux_Mini_L3 (AMD Ryzen 7 5700U)",
        "input_price_per_1m_aud": 0.15,
        "output_price_per_1m_aud": 0.60,
        "min_charge_aud": 0.0001
    },
    "pan_tompkins_ecg_stream": {
        "node": "Port 4000 DSP Kernel",
        "price_per_hour_aud": 1.50,
        "min_charge_aud": 0.05
    }
}

COMMERCE_CATALOG = {
    "movesense_medical_sensor": {
        "name": "Movesense MD+ Sensor Hardware",
        "category": "HARD_PHYSICAL_ASSET",
        "price_aud": 170.0,
        "hard_cogs_aud": 110.0, # Wholesale invoice from Movesense Oy (Finland)
        "shipping_aud": 15.0,   # Insured Express AusPost
        "description": "Physical medical ECG hardware. Requires real fiat settlement."
    },
    "custom_bicep_band": {
        "name": "Custom Movesense Bicep ECG Band",
        "category": "HARD_PHYSICAL_ASSET",
        "price_aud": 59.0,
        "hard_cogs_aud": 12.0,  # Physical manufacturing BOM
        "shipping_aud": 9.95,
        "description": "Physical silver-electrode compression band."
    },
    "combat_preworkout_tub": {
        "name": "Combat Preworkout Supplement (30 Serves)",
        "category": "HARD_PHYSICAL_ASSET",
        "price_aud": 64.95,
        "hard_cogs_aud": 15.50, # Contract blending & packaging COGS
        "shipping_aud": 9.95,
        "description": "Physical 360g powder tub (FSANZ Standard 2.9.4)."
    },
    "movesense_hub_pro_saas": {
        "name": "Movesense Hub 512Hz SaaS (Monthly)",
        "category": "VIRTUAL_SOFTWARE",
        "price_aud": 14.99,
        "hard_cogs_aud": 0.0,   # Zero out-of-pocket expense
        "shipping_aud": 0.0,
        "description": "Pure software license. 100% redeemable via compute tokens."
    },
    "spatial_grappling_3d_tier": {
        "name": "Spatial Grappling 3D Academy Portal (Monthly)",
        "category": "VIRTUAL_SOFTWARE",
        "price_aud": 49.99,
        "hard_cogs_aud": 0.0,
        "shipping_aud": 0.0,
        "description": "Pure software license. 100% redeemable via compute tokens."
    },
    "openrouter_mcp_credits": {
        "name": "Frontier API Token Queries (OpenRouter)",
        "category": "VIRTUAL_SOFTWARE",
        "price_aud": 10.0,
        "hard_cogs_aud": 0.0,
        "shipping_aud": 0.0,
        "description": "Digital intelligence compute."
    }
}

def load_db():
    if os.path.exists(DATABASE_PATH):
        try:
            with open(DATABASE_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "total_revenue_aud": 0.0,
        "settled_fiat_reserve_aud": 0.0, # Real collected cash from external clients
        "total_tokens_served": 0,
        "active_accounts": {
            "lauburu_internal": {"compute_token_balance_aud": 500.0, "settled_fiat_balance_aud": 0.0, "total_usage_aud": 0.0},
            "external_test_client": {"compute_token_balance_aud": 50.0, "settled_fiat_balance_aud": 50.0, "total_usage_aud": 0.0}
        },
        "metering_events": [],
        "redemption_history": []
    }

def save_db(db):
    with open(DATABASE_PATH, "w") as f:
        json.dump(db, f, indent=2)

def meter_inference(account_id, model_key, prompt_tokens, completion_tokens, latency_sec):
    db = load_db()
    if account_id not in db["active_accounts"]:
        db["active_accounts"][account_id] = {"compute_token_balance_aud": 10.0, "settled_fiat_balance_aud": 0.0, "total_usage_aud": 0.0}
        
    rates = PRICING_TABLE.get(model_key, PRICING_TABLE["qwen_38_max_local"])
    cost_in = (prompt_tokens / 1_000_000) * rates["input_price_per_1m_aud"]
    cost_out = (completion_tokens / 1_000_000) * rates["output_price_per_1m_aud"]
    total_cost = round(max(rates["min_charge_aud"], cost_in + cost_out), 6)
    
    account = db["active_accounts"][account_id]
    if account["compute_token_balance_aud"] < total_cost:
        print(f"[🚨] INSUFFICIENT COMPUTE CREDITS: Account {account_id} balance (${account['compute_token_balance_aud']:.4f}) < cost (${total_cost:.4f}).")
        return {"authorized": False, "required_topup": total_cost - account["compute_token_balance_aud"]}
        
    account["compute_token_balance_aud"] -= total_cost
    account["total_usage_aud"] += total_cost
    db["total_revenue_aud"] += total_cost
    db["total_tokens_served"] += (prompt_tokens + completion_tokens)
    
    event = {
        "timestamp": datetime.now().isoformat(),
        "account_id": account_id,
        "model": model_key,
        "node": rates["node"],
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "throughput_tok_s": round(completion_tokens / max(0.001, latency_sec), 2),
        "billed_aud": total_cost,
        "remaining_balance_aud": round(account["compute_token_balance_aud"], 4)
    }
    
    db["metering_events"].append(event)
    save_db(db)
    return {"authorized": True, "event": event}

def create_topup_intent(account_id, amount_aud):
    """
    Simulates real fiat collection via Stripe (settled cash reserve).
    """
    db = load_db()
    if account_id not in db["active_accounts"]:
        db["active_accounts"][account_id] = {"compute_token_balance_aud": 0.0, "settled_fiat_balance_aud": 0.0, "total_usage_aud": 0.0}
        
    db["active_accounts"][account_id]["compute_token_balance_aud"] += amount_aud
    db["active_accounts"][account_id]["settled_fiat_balance_aud"] += amount_aud
    db["settled_fiat_reserve_aud"] += amount_aud
    save_db(db)
    print(f"[+] FIAT SETTLEMENT CONFIRMED: ${amount_aud:.2f} AUD deposited to {account_id}.")
    print(f"    -> Compute Credits: ${db['active_accounts'][account_id]['compute_token_balance_aud']:.2f}")
    print(f"    -> Settled Fiat Reserve: ${db['settled_fiat_reserve_aud']:.2f} AUD")
    return {"status": "succeeded", "new_balance": db["active_accounts"][account_id]["compute_token_balance_aud"]}

def redeem_item_with_compute(account_id, catalog_item_id):
    """
    STRICT SOLVENCY & BREAK-EVEN GATE:
    - Pure software is 100% redeemable with compute credits.
    - Physical assets with hard COGS strictly require settled fiat cash to cover 100%
      of wholesale COGS + shipping. Aaron must NEVER be out of pocket!
    """
    if catalog_item_id not in COMMERCE_CATALOG:
        print(f"[!] Unknown catalog item: {catalog_item_id}")
        return False
        
    item = COMMERCE_CATALOG[catalog_item_id]
    item_name = item["name"]
    category = item["category"]
    price = item["price_aud"]
    hard_cogs = item["hard_cogs_aud"] + item["shipping_aud"]
    
    db = load_db()
    if account_id not in db["active_accounts"]:
        print(f"[!] Account {account_id} not found.")
        return False
        
    account = db["active_accounts"][account_id]
    compute_bal = account.get("compute_token_balance_aud", 0.0)
    settled_fiat = account.get("settled_fiat_balance_aud", 0.0)
    
    print("=================================================================")
    print(f"🛍️ Compute Redemption Request: {item_name}")
    print("=================================================================")
    print(f"[*] Account: {account_id}")
    print(f"[*] Category: {category}")
    print(f"[*] Retail Price: ${price:.2f} AUD | Hard COGS + Shipping: ${hard_cogs:.2f} AUD")
    print(f"[*] Account Balances: Compute Tokens: ${compute_bal:.2f} | Settled Fiat: ${settled_fiat:.2f}")
    
    # 1. Check if account has enough compute tokens to cover retail price
    if compute_bal < price:
        print(f"[🚨 DENIED]: Insufficient compute tokens (${compute_bal:.2f} < ${price:.2f} AUD).")
        return False
        
    # 2. THE HARD COGS & SOLVENCY GATE
    if category == "HARD_PHYSICAL_ASSET":
        # Check if real settled fiat covers 100% of hard COGS + shipping
        if settled_fiat < hard_cogs:
            print("-----------------------------------------------------------------")
            print("🛑 [HARD BREAK-EVEN INVARIANT VIOLATED]: REDEMPTION BLOCKED!")
            print(f"   Physical item '{item_name}' incurs a REAL out-of-pocket invoice:")
            print(f"   - Wholesale Factory/Supplier Invoice: ${item['hard_cogs_aud']:.2f} AUD")
            print(f"   - Australia Post Insured Freight:    ${item['shipping_aud']:.2f} AUD")
            print(f"   - Total Hard Cash Required:          ${hard_cogs:.2f} AUD")
            print(f"   - Settled Fiat in Account:           ${settled_fiat:.2f} AUD")
            print("   RULE: Aaron must NEVER pay out of pocket for compute token redemptions.")
            print("   Compute tokens cannot purchase physical goods unless backed by settled")
            print("   client cash covering 100% of physical manufacturing and freight costs.")
            print("-----------------------------------------------------------------")
            return False
        else:
            # Deduct hard COGS from settled fiat, deduct retail price from compute tokens
            account["settled_fiat_balance_aud"] -= hard_cogs
            db["settled_fiat_reserve_aud"] -= hard_cogs
            print(f"[✓] BREAK-EVEN VERIFIED: Hard COGS (${hard_cogs:.2f} AUD) covered by settled client cash.")
            
    # Deduct compute tokens
    account["compute_token_balance_aud"] -= price
    
    record = {
        "timestamp": datetime.now().isoformat(),
        "account_id": account_id,
        "item_id": catalog_item_id,
        "item_name": item_name,
        "category": category,
        "tokens_burned_aud": price,
        "hard_cogs_cleared_aud": hard_cogs,
        "remaining_compute_tokens_aud": account["compute_token_balance_aud"],
        "remaining_settled_fiat_aud": account["settled_fiat_balance_aud"],
        "solvency_status": "BREAK_EVEN_GUARANTEED"
    }
    
    db["redemption_history"].append(record)
    save_db(db)
    
    print(f"[🎉 APPROVED]: {item_name} successfully redeemed.")
    print(f"    -> Remaining Compute Tokens: ${account['compute_token_balance_aud']:.2f} AUD")
    print(f"    -> Remaining Settled Fiat:   ${account['settled_fiat_balance_aud']:.2f} AUD")
    print("=================================================================\n")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "redeem":
        # redeem <account_id> <catalog_item_id>
        redeem_item_with_compute(sys.argv[2], sys.argv[3])
    elif len(sys.argv) > 2 and sys.argv[1] == "topup":
        # topup <account_id> <amount_aud>
        create_topup_intent(sys.argv[2], float(sys.argv[3]))
    else:
        # Self-test: 
        # Test 1: Try redeeming Movesense hardware with purely virtual tokens (must fail)
        print("[TEST 1]: Attempting Movesense hardware redemption without fiat backing...")
        redeem_item_with_compute("lauburu_internal", "movesense_medical_sensor")
        
        # Test 2: Redeem virtual software (must succeed)
        print("[TEST 2]: Attempting Virtual SaaS redemption...")
        redeem_item_with_compute("lauburu_internal", "movesense_hub_pro_saas")
