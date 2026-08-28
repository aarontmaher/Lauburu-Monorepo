#!/usr/bin/env python3
import json
import os
import shutil
import glob
from pathlib import Path

# Paths
LEADERBOARD_PATH = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/ai_elo_leaderboard.json"
VAULT_PATH = "/Volumes/localhost/AI_Models/champions"
MODEL_SEARCH_PATHS = [
    "/Volumes/localhost/AI_Models/gguf",
    "/Volumes/localhost/AI_Models/exo",
    "/Users/aaron/models"
]

def load_leaderboard():
    if not os.path.exists(LEADERBOARD_PATH):
        print(f"Leaderboard not found at {LEADERBOARD_PATH}")
        return None
    with open(LEADERBOARD_PATH, 'r') as f:
        return json.load(f)

def find_model_file(model_name):
    # Try to find a file loosely matching the model name
    search_term = model_name.lower().replace("-", "").replace("_", "")
    for search_dir in MODEL_SEARCH_PATHS:
        if not os.path.exists(search_dir):
            continue
        for root, _, files in os.walk(search_dir):
            for file in files:
                clean_file = file.lower().replace("-", "").replace("_", "")
                if search_term in clean_file or clean_file.startswith(search_term):
                    return os.path.join(root, file)
    return None

def sync_champions():
    data = load_leaderboard()
    if not data:
        return

    models = data.get("models", {})
    
    # Group by tier (specialist role)
    roles = {}
    for name, stats in models.items():
        if "CLOUD" in stats["tier"]:
            continue # We only house Local AI champions
            
        role = stats["tier"]
        if role not in roles or stats["elo"] > roles[role]["elo"]:
            roles[role] = {
                "name": name,
                "elo": stats["elo"],
                "stats": stats
            }
            
    print(f"👑 Crowned {len(roles)} Local AI Champions from Training Games:")
    
    for role, champ in roles.items():
        role_dir = os.path.join(VAULT_PATH, role.lower().replace("_", "-"))
        os.makedirs(role_dir, exist_ok=True)
        
        print(f" -> Role: {role}")
        print(f"    Champion: {champ['name']} (ELO: {champ['elo']})")
        
        # Clear old champion links/files in this role
        for old_file in glob.glob(os.path.join(role_dir, "*")):
            if os.path.islink(old_file) or os.path.isfile(old_file):
                os.remove(old_file)
                
        # Find the physical model file
        model_file = find_model_file(champ['name'])
        
        metadata_path = os.path.join(role_dir, "champion_metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(champ, f, indent=2)
            
        if model_file:
            print(f"    Found model file: {model_file}")
            symlink_path = os.path.join(role_dir, os.path.basename(model_file))
            try:
                os.symlink(model_file, symlink_path)
                print(f"    ✅ Symlinked to vault: {symlink_path}")
            except OSError as e:
                print(f"    ⚠️ Failed to symlink: {e}")
        else:
            print(f"    ⚠️ Physical model file not found in search paths. Awaiting download.")
            placeholder_path = os.path.join(role_dir, f"{champ['name']}.gguf.pending")
            with open(placeholder_path, 'w') as f:
                f.write(f"Awaiting download of {champ['name']} after winning ELO.")
            print(f"    ✅ Pending file created.")

if __name__ == "__main__":
    sync_champions()
