
import sys
import time
import json
import os
import urllib.request
from pathlib import Path
import subprocess

sys.path.insert(0, "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/edge_ai")
from gemini_nano import HybridAIRouter, GeminiNanoClient


REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "01_apps/screen_lens/src/mcp"))
import multi_cloud_router

def load_keys():
    keys = {}
    env_path = Path(os.path.expanduser("~/.env"))
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                keys[k.strip()] = v.strip().strip('"').strip("'")
    return keys

def invoke_model(provider, prompt, keys, task_type="ocr_caption"):
    print(f"  -> Routing Screen Lens Task ({task_type})...")
    
    # Initialize the edge router
    router = HybridAIRouter(GeminiNanoClient())
    decision = router.route_task(task_type, prompt)
    
    if decision.target == "GEMINI_NANO_AICORE":
        print("  -> ⚡ Executing INSTANTLY on Pixel 10 Tensor G5 TPU (Zero Cloud Egress)...")
        return router.nano_client.rewrite(prompt, style="lens_ocr_extract")
        
    elif decision.target.startswith("LOCAL_QWEN"):
        print(f"  -> 🖥️ Falling back to Sovereign Local Mesh ({decision.target})...")
        pass # Handle Qwen locally if needed

    print(f"  -> ☁️ Escalating to {decision.target} / {provider.upper()} API...")
    try:
        if provider == "groq":
            req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", method="POST")
            req.add_header("Authorization", f"Bearer {keys['GROQ_API_KEY']}")
            req.add_header("Content-Type", "application/json")
            req.add_header("User-Agent", "Lauburu-Mesh/1.0")
            data = json.dumps({"model": "openai/gpt-oss-20b", "messages": [{"role": "user", "content": prompt}]}).encode()
            res = urllib.request.urlopen(req, data=data, timeout=30)
            return json.loads(res.read())["choices"][0]["message"]["content"]
            
        elif provider == "xai":
            req = urllib.request.Request("https://api.x.ai/v1/chat/completions", method="POST")
            req.add_header("Authorization", f"Bearer {keys['XAI_API_KEY']}")
            req.add_header("Content-Type", "application/json")
            data = json.dumps({"model": "grok-4.20-0309-reasoning", "messages": [{"role": "user", "content": prompt}]}).encode()
            res = urllib.request.urlopen(req, data=data, timeout=30)
            return json.loads(res.read())["choices"][0]["message"]["content"]
            
        elif provider == "nvidia":
            req = urllib.request.Request("https://integrate.api.nvidia.com/v1/chat/completions", method="POST")
            req.add_header("Authorization", f"Bearer {keys['NVIDIA_API_KEY']}")
            req.add_header("Content-Type", "application/json")
            data = json.dumps({"model": "deepseek-ai/deepseek-v4-flash-0731", "messages": [{"role": "user", "content": prompt}], "max_tokens": 1024}).encode()
            res = urllib.request.urlopen(req, data=data, timeout=30)
            return json.loads(res.read())["choices"][0]["message"]["content"]
            
        elif provider == "cloudflare":
            # Extract OAuth token from wrangler config
            wrangler_cfg = Path(os.path.expanduser("~/.wrangler/config/default.toml")).read_text()
            cf_token = [line.split('"')[1] for line in wrangler_cfg.splitlines() if line.startswith('oauth_token')][0]
            req = urllib.request.Request("https://api.cloudflare.com/client/v4/accounts/883d9ae28a5ead3b314b8eba33bafbb6/ai/run/@cf/meta/llama-3.1-8b-instruct", method="POST")
            req.add_header("Authorization", f"Bearer {cf_token}")
            req.add_header("Content-Type", "application/json")
            data = json.dumps({"messages": [{"role": "user", "content": prompt}]}).encode()
            res = urllib.request.urlopen(req, data=data, timeout=30)
            return json.loads(res.read())["result"]["response"]
            
        elif provider == "google":
            api_key = keys['GEMINI_API_KEY']
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            req = urllib.request.Request(url, method="POST")
            req.add_header("Content-Type", "application/json")
            data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
            res = urllib.request.urlopen(req, data=data, timeout=30)
            return json.loads(res.read())["candidates"][0]["content"]["parts"][0]["text"]
            
        else:
            return "Local fallback execution: Network API not implemented for " + provider

    except Exception as e:
        return f"Error executing {provider}: {str(e)}"

def update_global_project_overview():
    print("[1/5] Initiating Screen Lens Global Project Overview Optimization...")
    keys = load_keys()
    
    # 1. Fetch recent git commits and mesh status
    print("[2/5] Fetching live git logs and Mesh telemetry...")
    git_log = subprocess.check_output(["git", "log", "-n", "5", "--oneline"], cwd=str(REPO_ROOT)).decode()
    
    # 2. Request optimal cloud model via the Multi-Armed Bandit router
    print("[3/5] Querying UCB1 Multi-Armed Bandit router for optimal free-tier...")
    cloud_routing = multi_cloud_router.route_request(estimated_tokens=800)
    selected_provider = cloud_routing.get("selected_provider", "google")
    print(f"      Selected self-optimized free tier: {selected_provider.upper()}")
    
    # 3. Call the API
    print(f"[4/5] Transmitting telemetry to {selected_provider.upper()} for synthesis...")
    prompt = f"You are the Lauburu Screen Lens AI. Synthesize a brief 3-section Global Project Overview Markdown document based on this recent git activity. Section 1: Mesh State. Section 2: Recent Activity Summary. Section 3: Strategic Direction.\n\nGit Logs:\n{git_log}"
    
    overview_content = invoke_model(selected_provider, prompt, keys)
    
    if "Error" in overview_content:
        print("      " + overview_content)
        # Give negative feedback for failure
        multi_cloud_router.record_feedback(selected_provider, 0.0)
        return
        
    print("      Synthesis complete. Writing to Obsidian Vault...")
    
    header = f"### 🧠 Lauburu AI Monorepo - Global Project Overview\n*(Self-Optimized & Maintained by Screen Lens via {selected_provider.upper()})*\n\n"
    
    index_path = REPO_ROOT / "obsidian_vault" / "LENS_GLOBAL_PROJECT_OVERVIEW.md"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(header + overview_content)
    
    # 5. Provide feedback to the router
    # Calculate a rough success metric (e.g., if it has the required sections)
    score = 0.98 if "##" in overview_content else 0.5
    multi_cloud_router.record_feedback(selected_provider, score)
    print(f"[5/5] Success! Global Overview Updated. Feedback score {score} rewarded to {selected_provider.upper()} in UCB1 Engine.")

if __name__ == "__main__":
    update_global_project_overview()
