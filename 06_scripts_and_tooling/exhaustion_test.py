import sys
from pathlib import Path
import json

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "01_apps/screen_lens/src/mcp"))
import multi_cloud_router

def run_exhaustion():
    print("Initiating Sequential Quota Exhaustion Test...")
    
    task_types = ["vision", "low_latency", "reasoning", "edge_background", "general"]
    
    # 200 tasks * 5 types = 1000 requests
    for _ in range(200):
        for t in task_types:
            multi_cloud_router.route_request(estimated_tokens=50, task_type=t)
            
    print("\nExhaustion Burst Complete. 1000 requests routed.")
    print("Summarizing Quota Ledger...")
    
    state_file = REPO_ROOT / "04_data_and_memory" / "multi_cloud_priority_state.json"
    state = json.loads(state_file.read_text())
    
    for provider, usage in state["usage"].items():
        limit = multi_cloud_router.QUOTA_LIMITS[provider]
        if limit > 0:
            pct = (usage / limit) * 100
            print(f"  - {provider.upper()}: {usage}/{limit} ({pct:.1f}% utilized)")

if __name__ == "__main__":
    run_exhaustion()
