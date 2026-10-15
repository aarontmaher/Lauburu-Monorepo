import os
import json
import torch
import requests
import torch.nn as nn
import time

class TinyEloSpecialist(nn.Module):
    def __init__(self):
        super().__init__()
        self.k_factor = nn.Parameter(torch.tensor(32.0))
        self.scale = nn.Parameter(torch.tensor(400.0))
        
    def forward(self, elo_a, elo_b, outcome_a):
        prob_a = 1.0 / (1.0 + torch.pow(10.0, (elo_b - elo_a) / self.scale))
        new_elo_a = elo_a + self.k_factor * (outcome_a - prob_a)
        new_elo_b = elo_b + self.k_factor * ((1.0 - outcome_a) - (1.0 - prob_a))
        return new_elo_a, new_elo_b, prob_a

def score_with_tinyml(model, elo_a, elo_b, outcome):
    with torch.no_grad():
        new_a, new_b, _ = model(torch.tensor(float(elo_a)), torch.tensor(float(elo_b)), torch.tensor(float(outcome)))
    return new_a.item(), new_b.item()

def score_with_llm(endpoint, elo_a, elo_b, outcome, model_name=""):
    outcome_str = "Model A wins" if outcome == 1 else "Model B wins" if outcome == 0 else "Draw"
    prompt = f"Model A has ELO {elo_a}. Model B has ELO {elo_b}. Outcome: {outcome_str}. What are their new ELOs? Return ONLY a valid JSON object with keys 'elo_a' and 'elo_b', containing float numbers."
    
    headers = {"Content-Type": "application/json"}
    data = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }
    
    try:
        if "gemini" in model_name.lower():
            # Call Gemini
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                env_path = "/Volumes/Lauburu-Monorepo/.env"
                if os.path.exists(env_path):
                    with open(env_path, "r") as f:
                        for line in f:
                            if line.startswith("GEMINI_API_KEY="):
                                api_key = line.strip().split("=", 1)[1].strip('"\'')
                                break
            if not api_key:
                # If no key, just return unupdated to avoid crash
                print("No GEMINI_API_KEY found, skipping Gemini.")
                return elo_a, elo_b
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={api_key}"
            gemini_data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1}
            }
            resp = requests.post(url, headers=headers, json=gemini_data, timeout=10)
            text = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
        else:
            resp = requests.post(f"http://127.0.0.1:{endpoint}/v1/chat/completions", headers=headers, json=data, timeout=1.0)
            text = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "{}")
        
        # Clean text
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
            
        res = json.loads(text)
        return float(res.get("elo_a", elo_a)), float(res.get("elo_b", elo_b))
    except Exception as e:
        print(f"Error querying {model_name}: {e}")
        return elo_a, elo_b

def load_battles_from_leaderboard():
    leaderboard_path = "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/canonical_elo_leaderboard.json"
    battles = []
    if os.path.exists(leaderboard_path):
        with open(leaderboard_path, "r") as f:
            data = json.load(f)
            models = list(data.get("models", {}).values())
            for i in range(len(models)):
                for j in range(i + 1, min(i+5, len(models))): # limit battles
                    elo_a = models[i].get("elo", 1500)
                    elo_b = models[j].get("elo", 1500)
                    win_rate_a = models[i].get("win_rate_pct", 50) / 100.0
                    win_rate_b = models[j].get("win_rate_pct", 50) / 100.0
                    if win_rate_a > win_rate_b:
                        battles.append((elo_a, elo_b, 1.0))
                    elif win_rate_b > win_rate_a:
                        battles.append((elo_a, elo_b, 0.0))
                    else:
                        battles.append((elo_a, elo_b, 0.5))
    return battles[:10] # just take 10 battles for evaluation

def evaluate_models():
    # Load TinyML
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tiny_elo_specialist.pth")
    tinyml = TinyEloSpecialist()
    if os.path.exists(model_path):
        tinyml.load_state_dict(torch.load(model_path))
    else:
        print("TinyML model not found, using untrained.")
        
    battles = load_battles_from_leaderboard()
    
    results = {
        "TinyML Specialist": 0,
        "Qwen 2.5 Coder 7B (8081)": 0,
        "Qwen 3.8 Max (8083)": 0,
        "Gemini Flash": 0
    }
    
    print(f"Evaluating models on {len(battles)} battles...")
    
    for elo_a, elo_b, outcome in battles:
        print(f"\nBattle: ELO A {elo_a:.1f}, ELO B {elo_b:.1f}, Outcome {outcome}")
        
        # Ground truth new ELOs based on standard ELO with K=32
        gt_prob = 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / 400.0))
        gt_a = elo_a + 32 * (outcome - gt_prob)
        gt_b = elo_b + 32 * ((1-outcome) - (1-gt_prob))
        
        preds = {}
        # TinyML
        t_a, t_b = score_with_tinyml(tinyml, elo_a, elo_b, outcome)
        preds["TinyML Specialist"] = (t_a, t_b)
        
        # LLMs
        qa, qb = score_with_llm(8081, elo_a, elo_b, outcome, "qwen2.5-coder-7b-instruct")
        preds["Qwen 2.5 Coder 7B (8081)"] = (qa, qb)
        
        qa_max, qb_max = score_with_llm(8083, elo_a, elo_b, outcome, "qwen_38_max")
        preds["Qwen 3.8 Max (8083)"] = (qa_max, qb_max)
        
        ga, gb = score_with_llm(None, elo_a, elo_b, outcome, "gemini-3.8-flash") 
        preds["Gemini Flash"] = (ga, gb)
        
        # Calculate error from standard ELO math
        for name, (pred_a, pred_b) in preds.items():
            err = abs(pred_a - gt_a) + abs(pred_b - gt_b)
            print(f"  {name}: {pred_a:.1f}, {pred_b:.1f} (Error: {err:.2f})")
            results[name] += err

    print("\n--- FINAL EVALUATION RESULTS (Total Absolute Error vs Standard K=32) ---")
    for k, v in sorted(results.items(), key=lambda item: item[1]):
        print(f"{k}: {v:.2f}")

if __name__ == "__main__":
    evaluate_models()
