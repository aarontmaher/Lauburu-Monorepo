import httpx
import json
import re
import asyncio
import os
import sys
import math
import time
import random

MATRIX_PATH = os.path.join(os.path.dirname(__file__), "../network/mesh_ip_matrix.json")
MCTS_TRACES_PATH = "/tmp/mcts_latest_traces.jsonl"

if os.path.exists(MATRIX_PATH):
    with open(MATRIX_PATH, 'r') as f:
        ip_matrix = json.load(f)
else:
    ip_matrix = {}

PRIORITY = ["localhost", "tb4_bridge", "tailscale", "wifi", "pan", "pan_tether", "rf_plugin_proxy"]

def build_node_urls(node_name, port):
    if node_name not in ip_matrix:
        return [f"http://127.0.0.1:{port}/v1/chat/completions"]
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
    {"name": "L1_Mac_Host", "urls": build_node_urls("L1_Mac_Host", 8082), "model": "qwen_38_max"},
    {"name": "L3_Linux_Hub", "urls": build_node_urls("L3_Linux_Hub", 8081), "model": "gemma-2-9b-it-abliterated"},
    {"name": "L5_MacBook_Air", "urls": build_node_urls("L5_MacBook_Air", 8081), "model": "qwen2.5-coder-7b-instruct-q4_k_m"},
    {"name": "L8_Linux_Mini", "urls": build_node_urls("L8_Linux_Mini", 8081), "model": "qwen2.5-14b-instruct-q4_k_m"}
]

CRITIC_NODES = [
    {"name": "L2_MacBook_Pro", "urls": build_node_urls("L2_MacBook_Pro", 8083), "model": "qwen_38_max_abliterated"},
    {"name": "L6_Pixel_10_Edge", "urls": build_node_urls("L6_Pixel_10_Edge", 8081), "model": "qwen-1.5b-edge"},
    {"name": "L8_Linux_Mini", "urls": build_node_urls("L8_Linux_Mini", 8083), "model": "qwen2.5-14b-instruct-q4_k_m"}
]

async def async_call_node(client, node, prompt, temperature, max_tokens=1024):
    payload = {
        "model": node["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    for url in node["urls"]:
        try:
            r = await client.post(url, json=payload, timeout=30.0)
            r.raise_for_status()
            return {"node": node["name"], "content": r.json()["choices"][0]["message"]["content"], "used_url": url}
        except Exception:
            continue
    return {"node": node["name"], "content": None, "error": "All transports failed"}

class MCTSNode:
    def __init__(self, state, parent=None, action=None, depth=0):
        self.state = state 
        self.parent = parent
        self.action = action 
        self.children = []
        self.visits = 0
        self.value = 0.0
        self.is_terminal = False
        self.depth = depth
        
    def uct_score(self, dynamic_c_puct=1.414):
        if self.visits == 0:
            return float('inf')
        return (self.value / self.visits) + dynamic_c_puct * math.sqrt(math.log(self.parent.visits) / self.visits)

async def expand_nodes_parallel(client, nodes_to_expand, base_prompt):
    print(f"  [MCTS] Phase: Mesh-Level Speculative Branching ({len(nodes_to_expand)} nodes)...")
    tasks = []
    task_mapping = []
    
    # Round-robin assign generators to the nodes we want to expand
    for i, mcts_node in enumerate(nodes_to_expand):
        gen_node = GENERATOR_NODES[i % len(GENERATOR_NODES)]
        expansion_prompt = (
            f"Original Problem:\n{base_prompt}\n\n"
            f"Reasoning so far:\n{mcts_node.state}\n\n"
            f"Provide EXACTLY ONE next logical step in the reasoning chain. "
            f"Keep it concise, no more than 1-2 sentences. "
            f"If the reasoning is complete and the final answer is reached, reply with '[TERMINAL]'."
        )
        tasks.append(async_call_node(client, gen_node, expansion_prompt, 0.8, max_tokens=256))
        task_mapping.append(mcts_node)
        
    results = await asyncio.gather(*tasks)
    
    new_children = []
    for res, mcts_node in zip(results, task_mapping):
        if res["content"]:
            step_text = res["content"].strip()
            is_terminal = "[TERMINAL]" in step_text.upper()
            step_text = step_text.replace("[TERMINAL]", "").replace("[terminal]", "").strip()
            if not step_text:
                continue
                
            new_state = mcts_node.state + "\n" + step_text if mcts_node.state else step_text
            child = MCTSNode(state=new_state, parent=mcts_node, action=step_text, depth=mcts_node.depth + 1)
            child.is_terminal = is_terminal
            mcts_node.children.append(child)
            new_children.append(child)
            
    print(f"  [MCTS] Generated {len(new_children)} new speculative branches across mesh.")
    return new_children

async def evaluate_nodes_parallel(client, nodes_to_eval, base_prompt):
    print(f"  [MCTS] Phase: Consensus Arbitration via Critics ({len(nodes_to_eval)} nodes)...")
    tasks = []
    task_mapping = []
    
    for i, mcts_node in enumerate(nodes_to_eval):
        critic = CRITIC_NODES[i % len(CRITIC_NODES)]
        eval_prompt = (
            f"You are a Process Reward Model (PRM).\n"
            f"Original Problem: {base_prompt}\n"
            f"Reasoning Path:\n{mcts_node.state}\n\n"
            f"Evaluate the logical soundness and correctness of the reasoning path so far. "
            f"Reply ONLY with a float between 0.0 and 1.0."
        )
        tasks.append(async_call_node(client, critic, eval_prompt, 0.1, max_tokens=10))
        task_mapping.append(mcts_node)
        
    eval_results = await asyncio.gather(*tasks)
    
    rewards = []
    for res in eval_results:
        score = 0.0
        if res["content"]:
            match = re.search(r'0\.\d+|1\.0', res["content"])
            if match:
                score = float(match.group(0))
        rewards.append(score)
        
    return rewards

def backpropagate(mcts_node, reward):
    curr = mcts_node
    while curr is not None:
        curr.visits += 1
        curr.value += reward
        curr = curr.parent

async def mcts_reasoning_loop_async(prompt, num_simulations=10):
    print(f"=== Starting Multi-Step MCTS V2 (Mesh Speculative Branching) ===")
    root = MCTSNode(state="")
    
    async with httpx.AsyncClient() as client:
        # Initial expansion
        initial_children = await expand_nodes_parallel(client, [root] * len(GENERATOR_NODES), prompt)
        rewards = await evaluate_nodes_parallel(client, initial_children, prompt)
        for child, reward in zip(initial_children, rewards):
            backpropagate(child, reward)
            
        for sim in range(num_simulations):
            print(f"\n--- Mesh Arbitration Cycle {sim+1}/{num_simulations} ---")
            
            # Select multiple leaves for speculative branching
            leaves_to_expand = []
            
            # Dynamic C_PUCT: Lower exploration if we found deep confident paths
            max_depth = max([c.depth for c in root.children] + [0])
            dynamic_c = max(0.5, 1.414 - (max_depth * 0.1)) 
            
            # Traverse to find top 3 leaves
            for _ in range(3):
                curr = root
                while curr.children and not curr.is_terminal:
                    unexplored = [c for c in curr.children if c.visits == 0]
                    if unexplored:
                        curr = unexplored[0]
                        break
                    curr = max(curr.children, key=lambda c: c.uct_score(dynamic_c))
                if curr not in leaves_to_expand and not curr.is_terminal:
                    leaves_to_expand.append(curr)
                    
            if not leaves_to_expand:
                print("  [MCTS] Trees exhausted or all terminal. Early stopping.")
                break
                
            new_children = await expand_nodes_parallel(client, leaves_to_expand, prompt)
            if new_children:
                rewards = await evaluate_nodes_parallel(client, new_children, prompt)
                for child, reward in zip(new_children, rewards):
                    backpropagate(child, reward)
                    if child.is_terminal and reward > 0.9:
                        print("  [MCTS] Found highly confident terminal state.")
                        
        best_curr = root
        while best_curr.children:
            best_curr = max(best_curr.children, key=lambda c: c.visits)
            
        best_branch = best_curr.state
        best_score = best_curr.value / max(1, best_curr.visits)
        
        trace_data = {
            "timestamp": time.time(),
            "prompt": prompt,
            "chosen_reasoning": best_branch,
            "prm_score": best_score,
            "version": "v2_mesh_arbitration"
        }
        with open(MCTS_TRACES_PATH, "a") as f:
            f.write(json.dumps(trace_data) + "\n")
        
        print(f"\n  [MCTS] Final Synthesis (Avg Score: {best_score:.2f})...")
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
