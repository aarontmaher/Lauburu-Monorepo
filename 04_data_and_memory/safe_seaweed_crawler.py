import os

SEARCH_DIR = "/Users/aaron/mnt/seaweed_webdav/"
TARGET_KEYWORD = "movesense"
RESULTS_FILE = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/seaweed_movesense_hits.log"

def safe_crawl(directory, keyword, out_file):
    hit_count = 0
    with open(out_file, "w", encoding="utf-8") as out:
        for root, dirs, files in os.walk(directory):
            # Skip hidden dirs to speed up
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if file.startswith('.') or not file.endswith(('.txt', '.md', '.log', '.json', '.csv', '.jsonl')):
                    continue
                file_path = os.path.join(root, file)
                try:
                    # Strict handle closure
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            if keyword.lower() in line.lower():
                                out.write(f"[{file_path}:{line_num}] {line.strip()}\n")
                                hit_count += 1
                except Exception as e:
                    # Ignore unreadable files
                    pass
    return hit_count

if __name__ == "__main__":
    print(f"Starting safe crawl of {SEARCH_DIR}...")
    hits = safe_crawl(SEARCH_DIR, TARGET_KEYWORD, RESULTS_FILE)
    print(f"Crawl complete. Found {hits} matching lines.")
