#!/usr/bin/env python3
"""
Lauburu AI Large Goal Payout & Business Capital Governor
Manages milestone goals, automation degree evaluations, virtual business capital,
and OpenRouter MCP query permissions.
"""

import os
import sys
import json
import time
from datetime import datetime

LEDGER_PATH = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/business_ledger.json"

MILESTONES = {
    "MOVESENSE_BICEP_BAND": {
        "title": "Custom Movesense Bicep ECG Band",
        "base_capital_aud": 1500.0,
        "base_openrouter_credits": 25,
        "base_elo": 500,
        "required_deliverables": ["strategy_doc", "bom_cost_model", "hardware_specs"]
    },
    "COMBAT_PREWORKOUT": {
        "title": "Combat Sports Preworkout Supplement Plan",
        "base_capital_aud": 2000.0,
        "base_openrouter_credits": 30,
        "base_elo": 600,
        "required_deliverables": ["formulation_sheet", "tga_fsanz_compliance", "copacker_outreach"]
    },
    "OPEN_SOURCE_SHOPIFY": {
        "title": "Open Source Shopify Alternative (MedusaJS v2)",
        "base_capital_aud": 3500.0,
        "base_openrouter_credits": 50,
        "base_elo": 1000,
        "required_deliverables": ["docker_compose", "storefront_architecture", "payment_gateway_config"]
    },
    "APP_SALES_PLAN": {
        "title": "App Sales & Subscription Monetization Suite",
        "base_capital_aud": 2500.0,
        "base_openrouter_credits": 40,
        "base_elo": 750,
        "required_deliverables": ["tier_pricing_matrix", "stripe_portal_integration", "retention_model"]
    },
    "PAY_BY_COMPUTE_INTEGRATION": {
        "title": "Pay by Compute Functional Engine (Mesh Token Metering & API Monetization)",
        "base_capital_aud": 4000.0,
        "base_openrouter_credits": 60,
        "base_elo": 1200,
        "required_deliverables": ["token_metering_daemon", "stripe_compute_credits", "rpc_rate_limiter"]
    },
    "AI_HIGH_ROI_INITIATIVES": {
        "title": "AI-Suggested High-ROI Initiatives (Hardware Arbitrage & 3D Kinematics)",
        "base_capital_aud": 1800.0,
        "base_openrouter_credits": 25,
        "base_elo": 500,
        "required_deliverables": ["arbitrage_algorithm", "academy_kinematics_breakdown"]
    }
}

def load_ledger():
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "created_at": datetime.now().isoformat(),
        "total_capital_aud": 0.0,
        "available_openrouter_credits": 0,
        "lifetime_elo_earned": 0,
        "completed_milestones": {},
        "transaction_history": []
    }

def save_ledger(ledger):
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger, f, indent=2)

def award_milestone_payout(model_id, milestone_key, automation_score, deliverable_evidence):
    """
    Evaluates and disburses a large goal payout based on automation score (0.0 to 1.0).
    Higher automation degree yields higher monetary and OpenRouter MCP payouts.
    """
    if milestone_key not in MILESTONES:
        print(f"[!] Unknown milestone: {milestone_key}")
        return False
        
    milestone = MILESTONES[milestone_key]
    title = milestone["title"]
    
    # Bound automation score
    automation_score = max(0.1, min(1.0, float(automation_score)))
    
    # Calculate scaled rewards
    payout_capital = round(milestone["base_capital_aud"] * automation_score, 2)
    payout_or_credits = int(milestone["base_openrouter_credits"] * automation_score)
    payout_elo = int(milestone["base_elo"] * automation_score)
    
    ledger = load_ledger()
    
    ledger["total_capital_aud"] += payout_capital
    ledger["available_openrouter_credits"] += payout_or_credits
    ledger["lifetime_elo_earned"] += payout_elo
    
    tx_entry = {
        "timestamp": datetime.now().isoformat(),
        "model_id": model_id,
        "milestone": milestone_key,
        "title": title,
        "automation_score": f"{automation_score * 100:.1f}%",
        "capital_granted_aud": payout_capital,
        "openrouter_credits_granted": payout_or_credits,
        "elo_granted": payout_elo,
        "deliverable_evidence": deliverable_evidence
    }
    
    ledger["completed_milestones"][milestone_key] = tx_entry
    ledger["transaction_history"].append(tx_entry)
    save_ledger(ledger)
    
    print("=================================================================")
    print(f"💰 LARGE GOAL PAYOUT DISBURSED: {title}")
    print("=================================================================")
    print(f"[*] Awarded Model: {model_id}")
    print(f"[*] Automation Degree: {automation_score * 100:.1f}%")
    print(f"[*] Capital Granted: ${payout_capital:,.2f} AUD")
    print(f"[*] OpenRouter MCP Credits Granted: +{payout_or_credits} queries")
    print(f"[*] ELO Boost: +{payout_elo} pts")
    print(f"[*] Total Business Capital Balance: ${ledger['total_capital_aud']:,.2f} AUD")
    print(f"[*] Unlocked OpenRouter Quota: {ledger['available_openrouter_credits']} queries")
    print("=================================================================\n")
    return tx_entry

if __name__ == "__main__":
    if len(sys.argv) > 3 and sys.argv[1] == "award":
        # award <model_id> <milestone_key> <automation_score> [evidence]
        m_id = sys.argv[2]
        m_key = sys.argv[3]
        a_score = float(sys.argv[4])
        ev = sys.argv[5] if len(sys.argv) > 5 else "CLI Execution"
        award_milestone_payout(m_id, m_key, a_score, ev)
    else:
        ledger = load_ledger()
        print(f"Current Business Capital: ${ledger['total_capital_aud']:,.2f} AUD")
        print(f"OpenRouter MCP Credits: {ledger['available_openrouter_credits']}")
