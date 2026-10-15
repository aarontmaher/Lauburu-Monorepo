import subprocess
import json
from pathlib import Path

DATASET_PATH = Path("/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_free_ai_dataset.jsonl")

def run_cloud_triad_review(tiny_lm_action_log: str):
    """
    Sends the Tiny LM's action log to Gemini 3.8 Flash (via free API) 
    and requests both corrections and structural improvement suggestions.
    """
    prompt = f"""
    You are the Cloud Triad Auditor (Gemini 3.8 Flash). 
    Review the following action taken by a Tiny LM in the Lauburu Mesh:
    {tiny_lm_action_log}
    
    Tasks:
    1. Verify if the action was correct.
    2. PROVIDE EXPLICIT IMPROVEMENT SUGGESTIONS on how the Tiny LM or the architecture can be optimized.
    3. Generate a corrected input/output pair for LoRA distillation.
    """
    
    # Use agy headless to hit the free Gemini Flash endpoint
    result = subprocess.run([
        "agy", "--model", "gemini-3.8-flash", "--headless", "--print", "--prompt", prompt
    ], capture_output=True, text=True)
    
    output = result.stdout.strip()
    
    if output:
        # Append to the continuous LoRA dataset
        with open(DATASET_PATH, "a") as f:
            f.write(json.dumps({"prompt": prompt, "completion": output, "source": "gemini-3.8-flash-auditor"}) + "\n")
        print(f"✅ Cloud Triad Audit Complete. Improvement suggestions appended to {DATASET_PATH}")
    else:
        print("❌ Cloud API returned empty response.")

if __name__ == "__main__":
    sample_log = "Tiny LM Action: Scaled LR by 1.5x after detecting NaN loss."
    run_cloud_triad_review(sample_log)
