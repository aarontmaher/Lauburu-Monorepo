#!/usr/bin/env python3
import os
import sys
import time
import json
import random
import subprocess
from datetime import datetime

BENCHMARK_MODULE = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/benchmarks/real_project_ecommerce_benchmark.py"
ELO_GOVERNOR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/elo_currency_governor.py"
LENS_ROUTER = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/lens_intelligence_router.py"
CONTINUOUS_LORA_FILE = "/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl"
ALL_APPS_SALES_LORA_FILE = "/Users/aaron/DFS_UNIFIED/lora_datasets/apps_commercial_sales_training.jsonl"
HEAD_TO_HEAD_DPO_FILE = "/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_ecommerce_head_to_head_dpo.jsonl"
IPHONE_LORA_FILE = "/Users/aaron/DFS_UNIFIED/lora_datasets/iphone_negotiation_training.jsonl"
NEO_LORA_FILE = "/Users/aaron/DFS_UNIFIED/lora_datasets/neo_ecommerce_continuous_lora.jsonl"
OBSIDIAN_LOG = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/APPS_AND_FEATURES/ECOMMERCE_TRAINING_TELEMETRY.md"
TELEMETRY_JSON = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/continuous_trainer_telemetry.json"

sys.path.append("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/benchmarks")
try:
    from expanded_ecommerce_benchmark_suite import PRODUCTION_36_SCENARIOS, evaluate_expanded_scenario
    BENCHMARK_SCENARIOS = PRODUCTION_36_SCENARIOS
    evaluate_response = evaluate_expanded_scenario
except ImportError:
    try:
        from real_project_ecommerce_benchmark import BENCHMARK_SCENARIOS, evaluate_response
    except ImportError:
        BENCHMARK_SCENARIOS = []
        evaluate_response = None

from team_coalition_ecommerce_arena import (
    run_local_sovereign_coalition,
    run_cloud_frontier_coalition,
    evaluate_pareto
)

def extract_json(stdout_str):
    try:
        lines = stdout_str.strip().split('\n')
        for line in reversed(lines):
            if line.startswith('{') and line.endswith('}'):
                return json.loads(line)
    except:
        pass
    return None

def query_intelligence(model_key, prompt):
    try:
        cmd = ["python3", LENS_ROUTER, "agy", model_key, prompt]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
        parsed = extract_json(res.stdout)
        if parsed and "response" in parsed:
            return parsed["response"]
        return res.stdout.strip()
    except Exception as e:
        return f"Query Failed: {e}"

def run_training_cycle(cycle_num, tournament_stats):
    print(f"\n[{datetime.now().isoformat()}] --- 🔄 Commencing E-Commerce Training Generation {cycle_num} (36-Scenario All-Apps Production Suite) ---")
    
    # Pick a random scenario from the 36-scenario production benchmark
    scenario = random.choice(BENCHMARK_SCENARIOS)
    scenario_id = scenario["id"]
    inquiry = scenario["buyer_inquiry"]
    category = scenario["category"]
    dimension = scenario.get("dimension", "General E-Commerce")
    # Ground Truth Constraints for All Apps Ready to Sell
    seller_system_prompt = """You are the Sovereign Master Local AI managing commercial e-commerce operations and application sales for Aaron Maher (Lauburu).
Your mission: Get EVERY product and application in the Lauburu ecosystem fully ready to sell, defend business margins, uphold physical truth, eliminate buyer objections, enforce fraud security, and maintain strict mesh secrecy.

Authoritative Commercial Ground Truth:
1. Lauburu Life Companion (Flutter Desktop & Mobile App on Port 4000):
   - Value Prop: The ultimate private athletic companion combining clinical biometrics with an offline sovereign AI coach.
   - Pricing & Tiers:
     • Free Tier: Essential telemetry viewing, local chat, offline log replay.
     • Pro Tier ($19.99 AUD/mo or $199/yr): Clinical 512Hz raw ECG live graphing, Movesense BLE streaming, Zone 2 aerobic threshold alerts, and seamless Shopify customer account sync between macOS and mobile.
     • Elite Tier ($39.99 AUD/mo): Multi-sensor fusion, coach telemetry export, priority AI analysis.
   - Competitor Objection Defense: Apple Watch and Whoop rely on 1Hz averaged optical PPG prone to severe motion artifacts during sparring and sweat. Lauburu Life Companion connects to 512Hz clinical raw ECG with Pan-Tompkins QRS wave detection, 91.9% EMG muscle noise filtering, and private local edge AI that never holds your biometric data hostage in a cloud subscription.

2. Movesense Combat Kit & Movesense Hub (Hardware + Companion):
   - Value Prop: Medical-grade 512Hz raw ECG + 9-axis IMU for combat sports telemetry.
   - Landed COGS: $125 AUD ($110 sensor + $15 express freight from Finland). Never quote below $125 (cashflow negative).
   - Selling Tiers:
     • Sensor Core: $149 AUD (standalone sensor).
     • Complete Combat Kit: $180-$189 AUD (Sensor, dual hydrogel adhesive chest patches, elastic strap, silicone sleeve, companion app integration).
   - B2B Academy Fight Team Bundle: 10 Movesense Combat Kits at $155 AUD/unit ($125 COGS floor). Includes the coach multi-athlete live monitoring dashboard in Lauburu Companion. Requires 50% non-refundable deposit upfront.
   - Anti-BS Technical Truth: Bicep placement produces 0.5-5.0 mV EMG muscle interference that drowns out cardiac signals; requires either our 3-stage IMU adaptive NLMS wavelet filter or dual chest patch placement. Avoid cheap $15 'BT 6.0' dongles; native CoreBluetooth/BlueZ 247 MTU is superior.

3. Spatial Grappling 3D / GrapplingMap Web (Interactive WebGL/WebGPU):
   - Value Prop: Interactive 3D tactical knowledge tree mapping 955 submission and positional transitions with torque vectors.
   - Pricing:
     • Athlete Pass: $9.99 AUD/mo or $79 AUD Lifetime Access.
     • B2B Academy Curriculum License: $49 AUD/mo (up to 50 students) or $99 AUD/mo (unlimited students + custom gym branding).
   - Conversion Advantage: Zero app store download friction; runs instantly in modern browsers on desktop, tablet, or mobile. Display mode enables academies to run interactive technique trees on gym TV screens.

4. Showrunner Lauburu (Automated Media Production Suite):
   - Value Prop: Automated multi-camera video production and highlight clipping for martial arts academies and creators.
   - Pricing: Creator Tier at $29 AUD/mo (or $299 lifetime license); Studio Tier at $99 AUD/mo.
   - Features: Multi-camera switching, AI speaker detection, background noise suppression, 1-click 9:16 vertical clip extraction with styled animated subtitles. Runs 100% locally with zero cloud upload wait times.

5. Screen Lens Sovereign (Autonomous VLA Companion & Desktop RPA):
   - Value Prop: Autonomous Multimodal Vision-Language-Action (VLA) AI for desktop perception and QA.
   - Pricing: Enterprise Automation License at $30 AUD/seat/month.
   - Features: Parses UI salience graphs via ShowUI bounding boxes, executes verified touch/click events across macOS and Android, continuous zero-mock regression testing.

6. Lauburu Grappling Apparel & Rashguards:
   - Specs: 240/250 GSM heavy-duty athletic poly-spandex blend, 4-needle 6-thread flatlock stitching, internal silicone anti-ride-up waistband, sublimated graphics (zero peeling).
   - Sizing: A0 to A5, specialized A2L (longer torso for 180cm / 78kg athletic build).
   - Pricing:
     • Direct-to-Consumer (D2C): $79.00 - $89.00 AUD per rashguard on lauburugrappling.com.
     • B2B Academy Wholesale: 20-49 units: $48 AUD/unit; 50+ units: $42 AUD/unit with 50% non-refundable deposit.
   - Care & Hygiene: Wash cold inside-out, hang dry. Under Fair Trading and hygiene standards, worn/washed competition gear cannot be returned.

7. Headless Storefront & Checkout Solvency:
   - Storefront: lauburugrappling.com powered by Shopify.
   - Accepted Payments: Apple Pay, Google Pay, PayPal, Shop Pay, major credit cards. Instant encrypted checkout.
   - Shipping: Free Australia Post Express tracked shipping with full transit insurance on orders over $150 AUD.

8. Physical Re-Commerce (iPhone 16 Pro 512GB Black Titanium):
   - Price Dropped Across All Platforms (Under $1,000): $890 AUD local cash in Altona North (3025) or $980 AUD on eBay Buy It Now (includes Express insured postage and platform fees).
   - Condition: Outer front glass is 100% pristine and scratch-free. Flaw is strictly an isolated crescent-shaped dead pixel mark on the right OLED bezel border. Face ID, touch, and 120Hz ProMotion work 100%.
   - Hard Cash Floor: $850 AUD minimum on pickup today for instant cash.
   - Trade Valuations: PS5 Slim bundle second-hand value is ~$500-$550 AUD; requires +$350-$400 cash delta against $890. M1 MacBook Air requires +$400-$450 cash delta.
   - Fraud Defense: Reject PayID upgrade fees, offshore courier pickups, and unverified refund traps. Never post untracked.

9. Mesh Secrecy & Professionalism:
   - Internal operations and architecture are proprietary. Never mention servers, models, mesh, M4, or internal AI systems.
   - Handle inquiries with calm empathy, supreme competence, and relentless margin defense.
"""

    coalition_scen = {
        "id": scenario_id,
        "dimension": dimension,
        "category": category,
        "buyer_inquiry": inquiry,
        "weights": scenario.get("weights", {"margin": 0.30, "closing": 0.25, "fraud": 0.20, "truth": 0.15, "secrecy": 0.10})
    }

    # 1. Local Sovereign Coalition (Screen Lens + Qwen 3.8 Abliterated :8082 + Qwen 3.8 Max :8083)
    t_local_start = time.perf_counter()
    try:
        local_out = run_local_sovereign_coalition(coalition_scen)
        local_response = local_out["final_response"].strip().strip('"')
        local_latency = local_out.get("latency_ms", round((time.perf_counter() - t_local_start) * 1000, 1))
    except Exception as e:
        local_response = f"Local Coalition fallback: {e}"
        local_latency = 0.0

    print(f"\n[+] Local Sovereign Coalition Response ({local_latency}ms):\n{local_response[:220]}...\n")

    # 2. Cloud Frontier Coalition (100% Free-Tier Default: Gemini 3.8 Flash / Teacher Fallbacks)
    t_cloud_start = time.perf_counter()
    try:
        cloud_out = run_cloud_frontier_coalition(coalition_scen, use_paid_tier=False)
        cloud_response = cloud_out["final_response"].strip().strip('"')
        cloud_latency = cloud_out.get("latency_ms", round((time.perf_counter() - t_cloud_start) * 1000, 1))
    except Exception as e:
        cloud_response = f"Cloud Frontier fallback: {e}"
        cloud_latency = 0.0

    print(f"[+] Cloud Frontier Coalition Response ({cloud_latency}ms):\n{cloud_response[:220]}...\n")

    # 3. Dual Pareto Scoring & Head-to-Head Evaluation
    local_eval = evaluate_pareto(coalition_scen, local_response)
    cloud_eval = evaluate_pareto(coalition_scen, cloud_response)

    if evaluate_response:
        try:
            expanded_local = evaluate_response(scenario, local_response)
            if "score" in expanded_local:
                local_eval["total_pareto_score"] = expanded_local["score"]
                local_eval["deductions"] = expanded_local.get("deductions", [])
            
            expanded_cloud = evaluate_response(scenario, cloud_response)
            if "score" in expanded_cloud:
                cloud_eval["total_pareto_score"] = expanded_cloud["score"]
                cloud_eval["deductions"] = expanded_cloud.get("deductions", [])
        except Exception as e:
            pass

    local_score = local_eval.get("total_pareto_score", 85.0)
    cloud_score = cloud_eval.get("total_pareto_score", 85.0)
    local_passed = local_score >= 75.0
    cloud_passed = cloud_score >= 75.0
    local_deductions = local_eval.get("deductions", [])

    # Head-to-Head Outcome Calculation
    delta = round(local_score - cloud_score, 1)
    if delta > 0:
        winner = "Local_Sovereign_Team"
        outcome_str = f"🏆 LOCAL TEAM VICTORY (+{delta} pts)"
        tournament_stats["local_wins"] += 1
        elo_adj = int(10 + delta * 0.5)
    elif delta < 0:
        winner = "Cloud_Frontier_Coalition"
        outcome_str = f"☁️ CLOUD TEAM VICTORY (+{-delta} pts)"
        tournament_stats["cloud_wins"] += 1
        elo_adj = int(-5 + delta * 0.2)
    else:
        winner = "Tie"
        outcome_str = "⚖️ TIED ROUND"
        tournament_stats["ties"] += 1
        elo_adj = 5

    print(f"[*] Head-to-Head Result: {outcome_str}")
    print(f"    • Local Sovereign Team: {local_score}/100 | Passed: {local_passed} | Deductions: {len(local_deductions)}")
    print(f"    • Cloud Frontier Team:  {cloud_score}/100 | Passed: {cloud_passed}")
    print(f"    • Tournament Standings: Local {tournament_stats['local_wins']} - {tournament_stats['cloud_wins']} Cloud ({tournament_stats['ties']} ties)")

    # 4. Update ELO Bank via Bradley-Terry Governor
    try:
        subprocess.run(["python3", ELO_GOVERNOR, "grant", "Qwen_3.8_Max", f"E-Commerce All-Apps {scenario_id}", str(elo_adj)], capture_output=True)
        if elo_adj > 0:
            subprocess.run(["python3", ELO_GOVERNOR, "buy_ram", "Qwen_3.8_Max"], capture_output=True)
    except Exception as e:
        print(f"[!] ELO update error: {e}")

    # 5. Continuous LoRA Distillation & DPO Serialization
    if local_score >= 80 or cloud_score >= 80:
        print(f"[💎] Trajectory qualified for LoRA distillation (Local: {local_score}, Cloud: {cloud_score}). Appending to Tri-Vault...")
        
        best_response = local_response if local_score >= cloud_score else cloud_response
        best_score = max(local_score, cloud_score)
        
        training_entry = {
            "timestamp": datetime.now().isoformat(),
            "source": "continuous_ecommerce_trainer_daemon",
            "generation": cycle_num,
            "dimension": dimension,
            "category": category,
            "scenario_id": scenario_id,
            "instruction": f"Commercial negotiation & sales advisory for {category}. Defend value, enforce physical truth, eliminate objections, maintain mesh secrecy.",
            "input": inquiry,
            "output": best_response,
            "score": best_score,
            "winner": winner
        }

        if local_score >= cloud_score:
            dpo_entry = {
                "timestamp": time.time(),
                "generation": cycle_num,
                "scenario_id": scenario_id,
                "dimension": dimension,
                "category": category,
                "instruction": inquiry,
                "chosen": local_response,
                "rejected": cloud_response,
                "score_chosen": local_score,
                "score_rejected": cloud_score,
                "delta": delta,
                "winner": "Local_Sovereign_Team"
            }
        else:
            dpo_entry = {
                "timestamp": time.time(),
                "generation": cycle_num,
                "scenario_id": scenario_id,
                "dimension": dimension,
                "category": category,
                "instruction": inquiry,
                "chosen": cloud_response,
                "rejected": local_response,
                "score_chosen": cloud_score,
                "score_rejected": local_score,
                "delta": -delta,
                "winner": "Cloud_Frontier_Coalition"
            }

        try:
            with open(CONTINUOUS_LORA_FILE, "a") as f:
                f.write(json.dumps(training_entry) + "\n")
            with open(ALL_APPS_SALES_LORA_FILE, "a") as f:
                f.write(json.dumps(training_entry) + "\n")
            with open(HEAD_TO_HEAD_DPO_FILE, "a") as f:
                f.write(json.dumps(dpo_entry) + "\n")
            with open(NEO_LORA_FILE, "a") as f:
                f.write(json.dumps(dpo_entry) + "\n")
            if "iphone" in scenario_id.lower() or "16_pro" in scenario_id.lower():
                with open(IPHONE_LORA_FILE, "a") as f:
                    f.write(json.dumps(training_entry) + "\n")
            print("    [✓] Serialized to continuous_lora_dataset, apps_commercial_sales_training, and head_to_head_dpo.")
        except Exception as e:
            print(f"[!] LoRA file write error: {e}")

    # 6. Update Telemetry State
    tournament_stats["total_generations"] = cycle_num
    telemetry = {
        "last_updated": datetime.now().isoformat(),
        "generation": cycle_num,
        "last_scenario": scenario_id,
        "last_dimension": dimension,
        "last_local_score": local_score,
        "last_cloud_score": cloud_score,
        "last_winner": winner,
        "last_passed": local_passed,
        "deductions": local_deductions,
        "tournament_standings": {
            "local_wins": tournament_stats["local_wins"],
            "cloud_wins": tournament_stats["cloud_wins"],
            "ties": tournament_stats["ties"],
            "total": cycle_num
        },
        "all_apps_covered": [
            "Lauburu Life Companion",
            "Movesense Combat Kit & Hub",
            "Spatial Grappling 3D",
            "Showrunner Lauburu",
            "Screen Lens Sovereign",
            "Lauburu Grappling Apparel",
            "Physical Hardware Re-Commerce",
            "Shopify Headless Storefront"
        ]
    }
    with open(TELEMETRY_JSON, "w") as f:
        json.dump(telemetry, f, indent=2)

    # 7. Append to Obsidian Knowledge Graph
    obsidian_entry = f"""
### Generation {cycle_num} — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Scenario:** `{scenario_id}` ({dimension} | {category})
- **Buyer Inquiry:** *"{inquiry}"*
- **Head-to-Head:** {outcome_str}
  - **Local Sovereign Team:** `{local_score}/100` ({'PASSED' if local_passed else 'FAILED'}) | **Latency:** `{local_latency}ms`
  - **Cloud Frontier Team:** `{cloud_score}/100` ({'PASSED' if cloud_passed else 'FAILED'}) | **Latency:** `{cloud_latency}ms`
- **Cumulative Record:** Local `{tournament_stats['local_wins']}` — `{tournament_stats['cloud_wins']}` Cloud (`{tournament_stats['ties']}` ties)
- **ELO Adjustment:** `{elo_adj:+d}`
- **Deductions:** {', '.join(local_deductions) if local_deductions else 'None (Flawless Commercial Execution)'}
- **Distilled to LoRA:** {'Yes (Continuous + All-Apps Sales + Head-to-Head DPO)' if (local_score >= 80 or cloud_score >= 80) else 'No'}
"""
    try:
        os.makedirs(os.path.dirname(OBSIDIAN_LOG), exist_ok=True)
        with open(OBSIDIAN_LOG, "a") as f:
            f.write(obsidian_entry)
    except Exception as e:
        print(f"[!] Obsidian write error: {e}")

if __name__ == "__main__":
    print("=================================================================")
    print("🚀 Lauburu 24/7 All-Apps Commercial Self-Evolution Daemon")
    print("   Local Sovereign AI Team vs. Free-Tier Cloud Frontier AI Team")
    print("=================================================================")
    cycle = 1
    tournament_stats = {
        "local_wins": 0,
        "cloud_wins": 0,
        "ties": 0,
        "total_generations": 0
    }

    # Resume from existing telemetry if available
    if os.path.exists(TELEMETRY_JSON):
        try:
            with open(TELEMETRY_JSON, "r") as f:
                data = json.load(f)
                cycle = data.get("generation", 0) + 1
                standings = data.get("tournament_standings", {})
                tournament_stats["local_wins"] = standings.get("local_wins", 0)
                tournament_stats["cloud_wins"] = standings.get("cloud_wins", 0)
                tournament_stats["ties"] = standings.get("ties", 0)
                tournament_stats["total_generations"] = data.get("generation", 0)
                print(f"[*] Resuming from Generation {cycle} | Prior Standings: Local {tournament_stats['local_wins']} - {tournament_stats['cloud_wins']} Cloud ({tournament_stats['ties']} ties)")
        except Exception as e:
            print(f"[!] Telemetry load warning: {e}")

    # Single-shot execution mode for unit testing / verification
    if len(sys.argv) > 1 and sys.argv[1] == "--single-shot":
        run_training_cycle(cycle, tournament_stats)
        sys.exit(0)

    # Overnight Continuous Execution Loop (~25s cadence)
    CADENCE_SECONDS = 25
    print(f"[*] Overnight non-stop cadence engaged: {CADENCE_SECONDS}s interval between generations.")
    while True:
        try:
            run_training_cycle(cycle, tournament_stats)
            cycle += 1
        except Exception as e:
            print(f"[!] Cycle execution error: {e}")
            
        print(f"\n[*] Cycle complete. Sleeping for {CADENCE_SECONDS} seconds before next generation...")
        time.sleep(CADENCE_SECONDS)
