import json
import random
import os

INPUT_FILE = "/Users/aaron/DFS_UNIFIED/lora_datasets/router_network_healing_dataset.jsonl"
OUT_DIR = "/Users/aaron/DFS_UNIFIED/lora_datasets/router_mlx_data"

os.makedirs(OUT_DIR, exist_ok=True)

def apply_chatml(messages):
    text = ""
    for m in messages:
        text += f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n"
    return text

with open(INPUT_FILE, 'r') as f:
    lines = f.readlines()

dataset = [json.loads(line) for line in lines]
random.shuffle(dataset)

# Convert to MLX format {"text": "..."}
mlx_dataset = [{"text": apply_chatml(item["messages"])} for item in dataset]

train_data = mlx_dataset[:450]
valid_data = mlx_dataset[450:]

with open(os.path.join(OUT_DIR, "train.jsonl"), "w") as f:
    for item in train_data:
        f.write(json.dumps(item) + "\n")

with open(os.path.join(OUT_DIR, "valid.jsonl"), "w") as f:
    for item in valid_data:
        f.write(json.dumps(item) + "\n")

print(f"Prepared {len(train_data)} train and {len(valid_data)} valid samples in {OUT_DIR}")
