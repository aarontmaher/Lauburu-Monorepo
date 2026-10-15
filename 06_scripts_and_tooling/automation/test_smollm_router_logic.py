import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import json
import time
import sys
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

print("1. Loading SmolLM2-135M-Instruct (Router Simulation)...", flush=True)
model_id = "HuggingFaceTB/SmolLM2-135M-Instruct"

tokenizer = AutoTokenizer.from_pretrained(model_id)
# Fallback to CPU to avoid MPS semaphore crash on 135M model
model = AutoModelForCausalLM.from_pretrained(model_id, device_map="cpu", torch_dtype=torch.float32)

system_prompt = "You are the Autonomous Mesh Governor running on an OpenWrt GL.iNet router. Analyze the system diagnostics and output a strictly formatted JSON object with 'action' and 'command' to heal the network. If healthy, action is 'none'."
user_prompt = "Diagnostics:\nuptime: 3451s\ntailscale status\n# Health check:\n#     - state: NeedsLogin"

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_prompt}
]

print("2. Formatting Prompt...", flush=True)
input_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tokenizer(input_text, return_tensors="pt").to("cpu")

print("3. Generating Zero-Shot Response (Testing if LoRA is needed)...", flush=True)
start_time = time.time()
outputs = model.generate(**inputs, max_new_tokens=100, temperature=0.1)
end_time = time.time()

response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)

print(f"\n--- INFERENCE RESULTS ({end_time - start_time:.2f}s) ---", flush=True)
print("Response:\n", response, flush=True)

print("\n--- ANALYSIS ---", flush=True)
try:
    parsed = json.loads(response.strip().replace("```json","").replace("```",""))
    if "action" in parsed and "command" in parsed:
        print("✅ SUCCESS: The 135M model successfully output valid JSON without fine-tuning!", flush=True)
    else:
        print("❌ FAIL: JSON missing required keys. Model requires LoRA fine-tuning.", flush=True)
except json.JSONDecodeError:
    print("❌ FAIL: Invalid JSON syntax. Model requires LoRA fine-tuning.", flush=True)

