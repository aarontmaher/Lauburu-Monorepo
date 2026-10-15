import json
import os

OBSIDIAN_PRIORITY_FILE = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/PROJECT_PRIORITIES.md"

def get_priorities():
    if not os.path.exists(OBSIDIAN_PRIORITY_FILE):
        return []
        
    try:
        priorities = []
        with open(OBSIDIAN_PRIORITY_FILE, "r") as f:
            lines = f.readlines()
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("- [ ]") or stripped.startswith("- [x]"):
                    # Basic markdown parser
                    parts = stripped.split(":", 1)
                    title = parts[0].replace("- [ ]", "").replace("- [x]", "").strip()
                    desc = parts[1].strip() if len(parts) > 1 else ""
                    priority = "P?"
                    for p in ["P0", "P1", "P2", "P3"]:
                        if p in title:
                            priority = p
                            break
                    priorities.append({"title": title, "priority": priority, "desc": desc})
        return priorities
    except Exception:
        return []

if __name__ == "__main__":
    print(json.dumps(get_priorities(), indent=2))
