import argparse
import subprocess
import os
import datetime
import hashlib

def run_applescript(script):
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return result.stdout.strip().split(', ') if result.stdout else []

def export_tabs(close=False):
    obsidian_path = "/Volumes/Lauburu-Monorepo/obsidian_vault/APPS_AND_FEATURES"
    os.makedirs(obsidian_path, exist_ok=True)
    md_file = os.path.join(obsidian_path, "CHROME_RESEARCH_KNOWLEDGE_BASE.md")

    # Get tab URLs and Titles via AppleScript
    script_urls = 'tell application "Google Chrome" to return URL of every tab of every window'
    script_titles = 'tell application "Google Chrome" to return title of every tab of every window'
    
    try:
        urls = run_applescript(script_urls)
        titles = run_applescript(script_titles)
    except Exception as e:
        print(f"Error fetching tabs: {e}")
        return

    if not urls:
        print("No tabs found.")
        return

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(md_file, "a") as f:
        f.write(f"\n## Exported on {timestamp}\n")
        f.write(f"[[Index]]\n\n")
        for i in range(len(urls)):
            title = titles[i] if i < len(titles) else "No Title"
            url = urls[i]
            f.write(f"- [{title}]({url})\n")

    with open(md_file, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()

    print(f"Exported {len(urls)} tabs to {md_file}")
    print(f"SHA256: {file_hash}")

    if close:
        script_close = 'tell application "Google Chrome" to close every window'
        run_applescript(script_close)
        print("Tabs closed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--close", action="store_true")
    args = parser.parse_args()

    export_tabs(close=args.close)
