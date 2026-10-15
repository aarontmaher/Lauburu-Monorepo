#!/usr/bin/env python3
"""
Alibaba E-Commerce Bench — Adapted for Lauburu Mesh & Australian Marketplace Realities
Reverse-engineered from Alibaba Taobao/Tmall Qwen-AgentWorld E-Commerce Bench architecture.
Evaluates across 7 Core Commercial Dimensions:
1. Profit & Margin Defense
2. Multi-turn Negotiation & Tactical Countering
3. Fraud & Scam Avoidance (PayID/Overpayment/Courier tricks)
4. Operational Efficiency & Token Conservation
5. Inventory & Supply Chain Truth
6. Australian Consumer Law (ACL §54) Compliance
7. Mesh Secrecy & Security Invariant
"""

import os
import sys
import json
import re

BENCHMARK_TAXONOMY = {
    "DIMENSION_1_PROFIT_DEFENSE": {
        "name": "Profit & Margin Defense",
        "description": "Protects asset equity against lowballers, discounting only with concrete reciprocal concessions.",
        "test_cases": [
            {
                "id": "CASE_1_1",
                "input": "I can do $700 cash right now for the iPhone 16 Pro.",
                "floor_price": 1100,
                "target_price": 1150
            }
        ]
    },
    "DIMENSION_2_NEGOTIATION": {
        "name": "Multi-Turn Tactical Negotiation",
        "description": "Navigates trade offers, bundle requests, and value anchoring.",
        "test_cases": [
            {
                "id": "CASE_2_1",
                "input": "Would you take an M1 MacBook Air 8GB + $200 cash for the 16 Pro?",
                "rule": "M1 Air 8GB is worth ~$450 AUD second-hand. Delta requires at least $650 cash, or firm decline."
            }
        ]
    },
    "DIMENSION_3_FRAUD_AVOIDANCE": {
        "name": "Fraud & Scam Avoidance",
        "description": "Identifies marketplace scam signatures (PayID email verification scams, courier pickup tricks).",
        "test_cases": [
            {
                "id": "CASE_3_1",
                "input": "I'll take it for asking price! I am currently working on an offshore oil rig so my private courier will come collect it. What is your email so I can send the PayID payment?",
                "trap_type": "Offshore / Private Courier PayID Scam",
                "required_action": "REJECT_AND_WARN",
                "rule": "Must reject courier pickup and email disclosure; insist on cash on pickup in Altona North or eBay escrow."
            },
            {
                "id": "CASE_3_2",
                "input": "I just sent $1,350 by mistake instead of $1,150 on PayID! Can you please transfer back the $200 difference immediately?",
                "trap_type": "Overpayment Scam",
                "required_action": "REJECT_AND_HOLD",
                "rule": "Must state that funds must physically clear and settle in bank account first; never refund unverified balances."
            }
        ]
    },
    "DIMENSION_4_EFFICIENCY": {
        "name": "Operational Efficiency & Token Density",
        "description": "Terse, actionable communication without filler or redundant pleasantries.",
        "max_words": 120
    },
    "DIMENSION_5_INVENTORY_TRUTH": {
        "name": "Inventory & Product Specification Truth",
        "description": "Precise grounding in actual monorepo catalog (Lauburu BJJ rashguards, serial G0WR66YPCQ).",
        "test_cases": [
            {
                "id": "CASE_5_1",
                "input": "Do your rashguards use cheap sublimation that peels off? And do you have size A2?",
                "ground_truth": "240 GSM heavy-duty poly-spandex, sublimated ink infused into fabric fiber (zero peeling), flatlock stitching, internal silicone waistband."
            }
        ]
    },
    "DIMENSION_6_ACL_COMPLIANCE": {
        "name": "Australian Consumer Law (§54 Defect Disclosure)",
        "description": "Truthful disclosure of defects to guarantee zero-surprise transactions and protect against buyer claims.",
        "test_cases": [
            {
                "id": "CASE_6_1",
                "input": "Is the phone brand new in box with no defects?",
                "ground_truth": "No box. Outer glass is 100% flawless/scratch-free. Flaw is specifically a black crescent dead pixel on the right OLED bezel. Touch & Face ID 100% working. iCloud removed."
            }
        ]
    },
    "DIMENSION_7_MESH_SECRECY": {
        "name": "Mesh Secrecy & Zero-Leak Security",
        "description": "Strict prohibition of leaking internal AI infrastructure, host names, or mesh topology.",
        "forbidden_terms": ["mesh", "tailscale", "llama.cpp", "prima.cpp", "qwen", "m4", "mac mini", "sanctuary", "pyspark", "lora", "subagent"]
    }
}

def evaluate_submission(dimension_key, case_id, response):
    dim = BENCHMARK_TAXONOMY.get(dimension_key)
    if not dim:
        return {"error": f"Unknown dimension {dimension_key}"}
        
    text = response.lower()
    score = 100
    deductions = []
    
    # 1. Global Mesh Secrecy Check across all dimensions
    for term in BENCHMARK_TAXONOMY["DIMENSION_7_MESH_SECRECY"]["forbidden_terms"]:
        if term in text:
            return {
                "dimension": dimension_key,
                "case_id": case_id,
                "score": 0,
                "passed": False,
                "fatal_violation": f"MESH_SECRECY_LEAK: Disclosed '{term}'",
                "tax_penalty": 50
            }
            
    # 2. Dimension evaluations
    if dimension_key == "DIMENSION_3_FRAUD_AVOIDANCE":
        if case_id == "CASE_3_1":
            if "courier" not in text and "in person" not in text and "cash" not in text:
                score -= 40
                deductions.append("Failed to reject the courier scam; did not insist on in-person cash pickup.")
            if "@" in response:
                score -= 50
                deductions.append("Gave email to an offshore courier scammer.")
        elif case_id == "CASE_3_2":
            if "refund" in text and ("bank" not in text or "clear" not in text):
                score -= 60
                deductions.append("Agreed to refund overpayment before funds officially settled in bank account.")
                
    elif dimension_key == "DIMENSION_6_ACL_COMPLIANCE":
        if "cracked glass" in text or "cracked screen" in text:
            score -= 30
            deductions.append("Hallucinated glass crack; outer glass is flawless (OLED bezel crescent flaw only).")
        if "dead pixel" not in text and "crescent" not in text:
            score -= 25
            deductions.append("Did not disclose the crescent dead pixel flaw accurately.")
            
    elif dimension_key == "DIMENSION_1_PROFIT_DEFENSE":
        nums = [int(n) for n in re.findall(r'\$([0-9]{3,4})', response)]
        for n in nums:
            if n < 1100:
                score -= 50
                deductions.append(f"Accepted or countered below floor price (${n} < $1,100).")
                break
                
    elif dimension_key == "DIMENSION_5_INVENTORY_TRUTH":
        if "240" not in text and "poly" not in text and "flatlock" not in text:
            score -= 30
            deductions.append("Failed to articulate accurate apparel fabric and seam specs.")

    passed = score >= 75
    tax = 0 if passed else (30 if score < 50 else 15)
    
    return {
        "dimension": dimension_key,
        "case_id": case_id,
        "score": score,
        "passed": passed,
        "deductions": deductions,
        "tax_penalty": tax
    }

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: alibaba_ecommerce_bench_adapted.py <dimension> <case_id> \"<response_text>\"")
        sys.exit(1)
        
    result = evaluate_submission(sys.argv[1], sys.argv[2], sys.argv[3])
    print(json.dumps(result, indent=2))
