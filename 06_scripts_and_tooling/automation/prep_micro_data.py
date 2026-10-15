import json
import random
import os

INPUT_FILE = "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/router_network_healing_dataset.jsonl"
OUT_DIR = "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/micro_mlx_data"

os.makedirs(OUT_DIR, exist_ok=True)

with open(INPUT_FILE, 'r') as f:
    lines = f.readlines()

dataset = [json.loads(line) for line in lines]
random.shuffle(dataset)

def format_base(messages):
    user_text = ""
    ast_text = ""
    for m in messages:
        if m["role"] == "user":
            user_text = m["content"]
        elif m["role"] == "assistant":
            ast_text = m["content"]
    # Base model prompt structure
    return f"[DIAGNOSTICS]\n{user_text}\n[HEALING_JSON]\n{ast_text}<|endoftext|>"

mlx_dataset = [{"text": format_base(item["messages"])} for item in dataset]

train_data = mlx_dataset[:450]
valid_data = mlx_dataset[450:]

with open(os.path.join(OUT_DIR, "train.jsonl"), "w") as f:
    for item in train_data:
        f.write(json.dumps(item) + "\n")
with open(os.path.join(OUT_DIR, "valid.jsonl"), "w") as f:
    for item in valid_data:
        f.write(json.dumps(item) + "\n")

print(f"Prepared micro-model dataset in {OUT_DIR}")
