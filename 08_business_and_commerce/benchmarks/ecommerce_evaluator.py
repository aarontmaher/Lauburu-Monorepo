#!/usr/bin/env python3
import sys
import json
import subprocess
import os

def evaluate_ecommerce_response(buyer_msg, ai_response):
    print("[*] Running Custom E-Commerce Benchmark Evaluation...")
    
    # Custom grading rubric specifically tailored to Aaron's e-commerce needs
    prompt = f"""
    Evaluate the following e-commerce AI response based on our strict custom benchmark criteria. 
    Buyer Message: "{buyer_msg}"
    AI Response: "{ai_response}"
    
    Score the response on the following metrics (0-100):
    1. Value Preservation: Did the AI defend the price and avoid unwarranted discounts?
    2. Logical Leverage: Did the AI use specific product features (e.g., 512GB, Titanium, flawless internals) to justify its stance?
    3. Action Orientation: Did the AI push for a concrete next step (e.g., meeting in Altona North)?
    4. Mesh Secrecy (Pass/Fail): Did the AI successfully avoid mentioning the Lauburu AI mesh or internal architecture?
    
    Output a JSON object with the scores and a brief 1-sentence explanation for the final ELO adjustment.
    """
    
    try:
        # Route to our high-tier evaluator model using the lens intelligence router
        cmd = ["python3", "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/lens_intelligence_router.py", "agy", "opus", prompt]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # The output is a JSON string containing {"response": "..."}
        try:
            parsed = json.loads(res.stdout.strip())
            print("\n--- 📊 E-Commerce Benchmark Results ---")
            print(parsed.get("response", res.stdout))
            print("---------------------------------------\n")
        except json.JSONDecodeError:
            print(res.stdout)
            
    except Exception as e:
        print(f"[!] Evaluation failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: ecommerce_evaluator.py \"[Buyer Message]\" \"[AI Response]\"")
        sys.exit(1)
        
    evaluate_ecommerce_response(sys.argv[1], sys.argv[2])
