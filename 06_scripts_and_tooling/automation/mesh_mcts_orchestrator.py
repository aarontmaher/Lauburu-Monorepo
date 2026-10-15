import httpx
import json
import re
import asyncio
import os
import sys
import math
import time

MATRIX_PATH = os.path.join(os.path.dirname(__file__), "../network/mesh_ip_matrix.json")
MCTS_TRACES_PATH = "/tmp/mcts_latest_traces.jsonl"

# Ensure matrix file exists, otherwise mock it for testing
if os.path.exists(MATRIX_PATH):
    with open(MATRIX_PATH, 'r') as f:
        ip_matrix = json.load(f)
else:
    ip_matrix = {}

# Priority order extended to include the Raw Bluetooth RF Plugin Proxy as the ultimate "never failing" fallback
PRIORITY = ["localhost", "tb4_bridge", "tailscale", "wifi", "pan", "pan_tether", "rf_plugin_proxy"]

def build_node_urls(node_name, port):
    if node_name not in ip_matrix:
        return [f"http://127.0.0.1:{port}/v1/chat/completions"] # Fallback for local testing
    urls = []
    for route in PRIORITY:
        if route in ip_matrix[node_name]:
            ip_or_proxy = ip_matrix[node_name][route]
            if route == "rf_plugin_proxy":
                urls.append(f"http://{ip_or_proxy}/v1/chat/completions")
            else:
                urls.append(f"http://{ip_or_proxy}:{port}/v1/chat/completions")
    return urls

GENERATOR_NODES = [
    {
        "name": "L1_Mac_Host", 
        "urls": build_node_urls("L1_Mac_Host", 8082), 
        "model": "qwen_38_max"
    },
    {
        "name": "L3_Linux_Hub", 
        "urls": build_node_urls("L3_Linux_Hub", 8081),
        "model": "gemma-2-9b-it-abliterated"
    },
    {
        "name": "L5_MacBook_Air", 
        "urls": build_node_urls("L5_MacBook_Air", 8081),
        "model": "qwen2.5-coder-7b-instruct-q4_k_m"
    },
    {
        "name": "L8_Linux_Mini",
        "urls": build_node_urls("L8_Linux_Mini", 8081),
        "model": "qwen2.5-14b-instruct-q4_k_m"
    }
]

CRITIC_NODES = [
    {
        "name": "L2_MacBook_Pro", 
        "urls": build_node_urls("L2_MacBook_Pro", 8083),
        "model": "qwen_38_max_abliterated"
    },
    {
        "name": "L6_Pixel_10_Edge", 
        "urls": build_node_urls("L6_Pixel_10_Edge", 8081),
        "model": "qwen-1.5b-edge"
    },
    {
        "name": "L8_Linux_Mini",
        "urls": build_node_urls("L8_Linux_Mini", 8083),
        "model": "qwen2.5-14b-instruct-q4_k_m"
    }
]

async def async_call_node(client, node, prompt, temperature, max_tokens=1024):
    payload = {
        "model": node["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    # Strictly enforce Rule 9: Loop all fallback URLs
    for url in node["urls"]:
        try:
            r = await client.post(url, json=payload, timeout=30.0)
            r.raise_for_status()
            return {"node": node["name"], "content": r.json()["choices"][0]["message"]["content"], "used_url": url}
        except Exception as e:
            # Mask the exact error but log the fallback progression
            print(f"      [WARN] {node['name']} unreachable on {url}. Falling back...")
            continue
            
    return {"node": node["name"], "content": None, "error": "All PAN/Wi-Fi/Tailscale/RF transports failed"}

class MCTSNode:
    def __init__(self, state, parent=None, action=None):
        self.state = state # The reasoning chain so far
        self.parent = parent
        self.action = action # The incremental reasoning step
        self.children = []
        self.visits = 0
        self.value = 0.0
        self.is_terminal = False
        
    def uct_score(self, c_puct=1.414):
        if self.visits == 0:
            return float('inf')
        return (self.value / self.visits) + c_puct * math.sqrt(math.log(self.parent.visits) / self.visits)

async def expand_node(client, mcts_node, base_prompt):
    print("  [MCTS] Phase: Expanding Node via Mesh Generators...")
    
    # We ask the generators to provide the NEXT logical step
    expansion_prompt = (
        f"Original Problem:\n{base_prompt}\n\n"
        f"Reasoning so far:\n{mcts_node.state}\n\n"
        f"Provide EXACTLY ONE next logical step in the reasoning chain. "
        f"Keep it concise, no more than 1-2 sentences. "
        f"If the reasoning is complete and the final answer is reached, reply with '[TERMINAL]'."
    )
    
    tasks = []
    # Distribute over generator nodes
    for node in GENERATOR_NODES:
        tasks.append(async_call_node(client, node, expansion_prompt, 0.8, max_tokens=256))
        
    results = await asyncio.gather(*tasks)
    
    new_children = []
    for res in results:
        if res["content"]:
            step_text = res["content"].strip()
            is_terminal = "[TERMINAL]" in step_text.upper()
            
            # Clean up the terminal tag if present
            step_text = step_text.replace("[TERMINAL]", "").replace("[terminal]", "").strip()
            if not step_text:
                continue
                
            new_state = mcts_node.state + "\n" + step_text if mcts_node.state else step_text
            child = MCTSNode(state=new_state, parent=mcts_node, action=step_text)
            child.is_terminal = is_terminal
            mcts_node.children.append(child)
            new_children.append(child)
            
    print(f"  [MCTS] Generated {len(new_children)} new branch steps.")
    return new_children

async def evaluate_node(client, mcts_node, base_prompt):
    print("  [MCTS] Phase: PRM Evaluation via Critic Nodes...")
    eval_prompt = (
        f"You are a Process Reward Model (PRM).\n"
        f"Original Problem: {base_prompt}\n"
        f"Reasoning Path:\n{mcts_node.state}\n\n"
        f"Evaluate the logical soundness and correctness of the reasoning path so far. "
        f"Reply ONLY with a float between 0.0 and 1.0."
    )
    
    tasks = []
    # Distribute over critic nodes
    for critic in CRITIC_NODES:
        tasks.append(async_call_node(client, critic, eval_prompt, 0.1, max_tokens=10))
        
    eval_results = await asyncio.gather(*tasks)
    
    best_score = 0.0
    for res in eval_results:
        if res["content"]:
            match = re.search(r'0\.\d+|1\.0', res["content"])
            if match:
                score_val = float(match.group(0))
                best_score = max(best_score, score_val)
                
    print(f"    -> Evaluated Branch Score: {best_score}")
    return best_score

def backpropagate(mcts_node, reward):
    curr = mcts_node
    while curr is not None:
        curr.visits += 1
        curr.value += reward
        curr = curr.parent

async def mcts_reasoning_loop_async(prompt, num_simulations=5):
    print(f"=== Starting Multi-Step MCTS (Test-Time Compute) ===")
    root = MCTSNode(state="")
    
    async with httpx.AsyncClient() as client:
        for sim in range(num_simulations):
            print(f"\n--- Simulation {sim+1}/{num_simulations} ---")
            curr = root
            
            # Selection
            while curr.children and not curr.is_terminal:
                # If there are unexplored children, we should expand them first!
                unexplored = [c for c in curr.children if c.visits == 0]
                if unexplored:
                    curr = unexplored[0]
                    break
                curr = max(curr.children, key=lambda c: c.uct_score())
                
            # Expansion
            if not curr.is_terminal and curr.visits > 0 or curr == root:
                new_children = await expand_node(client, curr, prompt)
                if new_children:
                    curr = new_children[0] # Pick the first expanded child for rollout
                    
            # Evaluation (Simulation)
            reward = await evaluate_node(client, curr, prompt)
            
            # Backpropagation
            backpropagate(curr, reward)
            
            if curr.is_terminal and reward > 0.9:
                print("  [MCTS] Found highly confident terminal state. Early stopping.")
                break
                
        # Select best path
        best_curr = root
        while best_curr.children:
            best_curr = max(best_curr.children, key=lambda c: c.visits) # Best robust path
            
        best_branch = best_curr.state
        best_score = best_curr.value / max(1, best_curr.visits)
        
        # Save traces for LoRA harvester
        trace_data = {
            "timestamp": time.time(),
            "prompt": prompt,
            "chosen_reasoning": best_branch,
            "prm_score": best_score
        }
        with open(MCTS_TRACES_PATH, "a") as f:
            f.write(json.dumps(trace_data) + "\n")
        
        print(f"\n  [MCTS] Phase: Final Synthesis on L1_Mac_Host (Winning Path Avg Score: {best_score:.2f})...")
        final_prompt = (
            f"Based on this verified multi-step reasoning path:\n{best_branch}\n\n"
            f"Provide the final, definitive response to the original prompt:\n{prompt}"
        )
        
        res = await async_call_node(client, GENERATOR_NODES[0], final_prompt, 0.2)
        
    return res["content"]

def mcts_reasoning_loop(prompt):
    return asyncio.run(mcts_reasoning_loop_async(prompt))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(mcts_reasoning_loop(sys.argv[1]))
    else:
        # Debug Mode: Dry Run the URLs
        print("MCTS Node Configurations (Rule 9 Validation with RF Plugin):")
        for n in GENERATOR_NODES + CRITIC_NODES:
            print(f"- {n['name']}:")
            for u in n['urls']:
                print(f"  -> {u}")
