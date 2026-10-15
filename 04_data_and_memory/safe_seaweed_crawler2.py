import os

SEARCH_DIR = "/Users/aaron/mnt/seaweed_webdav/"
TARGET_KEYWORD = "movesense"
RESULTS_FILE = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/seaweed_movesense_hits2.log"

def safe_crawl(directory, keyword, out_file):
    hit_count = 0
    dirs_to_visit = [directory]
    
    with open(out_file, "w", encoding="utf-8") as out:
        while dirs_to_visit:
            current_dir = dirs_to_visit.pop()
            
            try:
                # listdir reads all entries and closes the directory handle immediately
                entries = os.listdir(current_dir)
            except Exception as e:
                # print(f"Failed to list {current_dir}: {e}")
                continue
                
            for entry in entries:
                if entry.startswith('.'):
                    continue
                
                full_path = os.path.join(current_dir, entry)
                
                try:
                    if os.path.isdir(full_path):
                        dirs_to_visit.append(full_path)
                    elif os.path.isfile(full_path):
                        if not full_path.endswith(('.txt', '.md', '.log', '.json', '.csv', '.jsonl')):
                            continue
                        
                        try:
                            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                                for line_num, line in enumerate(f, 1):
                                    if keyword.lower() in line.lower():
                                        out.write(f"[{full_path}:{line_num}] {line.strip()}\n")
                                        hit_count += 1
                        except Exception:
                            pass
                except Exception:
                    pass

    return hit_count

if __name__ == "__main__":
    print(f"Starting safe crawl of {SEARCH_DIR}...")
    hits = safe_crawl(SEARCH_DIR, TARGET_KEYWORD, RESULTS_FILE)
    print(f"Crawl complete. Found {hits} matching lines.")
