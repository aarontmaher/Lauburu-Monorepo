import os
import time
import httpx
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

load_dotenv("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.env")
TARGET_FILE = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/07_RESEARCH/LIVE_OPEN_SOURCE_SCOUTING.md"

def search_github(query):
    url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc"
    try:
        # We use a public search; in production we'd add an auth token
        resp = httpx.get(url, headers={"Accept": "application/vnd.github.v3+json"})
        if resp.status_code == 200:
            return resp.json().get("items", [])[:3]
    except Exception as e:
        logging.error(f"GitHub Search Error: {e}")
    return []

def run_scout_loop():
    logging.info("🕵️‍♂️ Continuous Deep Research Scout Started...")
    
    queries = [
        "screen recording AI local memory OCR",
        "multipath UDP VPN channel bonding",
        "screenpipe alternative",
        "limitless rewind alternative rust"
    ]
    
    while True:
        results = []
        for q in queries:
            logging.info(f"Scouting for: {q}")
            items = search_github(q.replace(" ", "+"))
            for item in items:
                repo_info = f"- **[{item['name']}]({item['html_url']})** ({item['stargazers_count']} ⭐) - {item['description']}"
                if repo_info not in results:
                    results.append(repo_info)
            time.sleep(10) # rate limit prevention
            
        if results:
            os.makedirs(os.path.dirname(TARGET_FILE), exist_ok=True)
            with open(TARGET_FILE, "a") as f:
                f.write(f"\n## 🕵️‍♂️ Scout Run: {time.ctime()}\n")
                f.write("\n".join(results) + "\n")
            logging.info("✅ Saved scout results to Obsidian Vault.")
        
        # Sleep for 4 hours
        time.sleep(14400)

if __name__ == "__main__":
    run_scout_loop()
