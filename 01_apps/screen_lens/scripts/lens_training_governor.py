import os
import time
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [Training Governor] %(message)s')

SCAFFOLDER_SCRIPT = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/auto_skill_scaffolder.py"
TRAINING_TRIGGER = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/scripts/trigger_lora_finetune.sh"
DATASET_PATH = "/Users/aaron/DFS_UNIFIED/lora_datasets/specialist_candidates.jsonl"
ELO_AUDITOR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/src/lens_elo_auditor.py"
OPTIMIZER = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/src/lens_local_ai_optimizer.py"

def loop():
    logging.info("🧠 Lens Training Governor Online. 24/7 Priority VLA Training Loop Started.")
    while True:
        try:
            # 1. Run Auto-Skill Scaffolder
            logging.info("Running Auto-Skill Scaffolder...")
            subprocess.run(["python3", SCAFFOLDER_SCRIPT], check=False)
            
            # 2. Run Lens Audits (ELO & Optimization)
            logging.info("Running Lens ELO & AI Optimizers...")
            subprocess.run(["python3", ELO_AUDITOR], check=False)
            subprocess.run(["python3", OPTIMIZER], check=False)
            
            # 3. Check Dataset and Trigger Training
            if os.path.exists(DATASET_PATH):
                with open(DATASET_PATH, 'r') as f:
                    count = sum(1 for line in f)
                logging.info(f"Current Dataset Size: {count} examples.")
                
                if count >= 10:  # Threshold for testing
                    logging.info("Threshold reached! Triggering MLX LoRA Fine-Tuning Script...")
                    env = os.environ.copy()
                    env["OVERRIDE_TRAIN_THRESHOLD"] = "1"
                    subprocess.run(["bash", TRAINING_TRIGGER], env=env, check=False)
            else:
                logging.info("Dataset not found yet. Waiting for Handoff Worker to generate traces...")
                
        except Exception as e:
            logging.error(f"Governor error: {e}")
            
        # Sleep for 10 minutes (600 seconds)
        time.sleep(600)

if __name__ == "__main__":
    loop()
