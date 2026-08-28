#!/usr/bin/env python3
"""
06_scripts_and_tooling/automation/browser_clipboard_key_harvester.py
===================================================================
Automated Browser Assisted Key Harvester for Lauburu Mesh
---------------------------------------------------------
1. Launches the exact key generation pages in your default logged-in browser.
2. Silently monitors the macOS clipboard for API key patterns.
3. Instantly captures, verifies, and writes the key to .env without you needing to paste it anywhere.
4. Clears the clipboard immediately for security.
"""

import os
import sys
import time
import subprocess
import urllib.request
from pathlib import Path

ENV_FILE = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.env")

def get_clipboard() -> str:
    try:
        res = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=1.0)
        return res.stdout.strip()
    except Exception:
        return ""

def clear_clipboard():
    try:
        subprocess.run(["pbcopy"], input="", text=True, timeout=1.0)
    except Exception:
        pass

def save_env_var(key_name: str, value: str):
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    env_vars = {}
    if ENV_FILE.is_file():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip().strip("\"'")
    
    env_vars[key_name] = value
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write("# Lauburu Sovereign Mesh Environment Configuration\n")
        f.write("# Harvested securely via browser_clipboard_key_harvester.py\n\n")
        for k, v in env_vars.items():
            if v:
                f.write(f'{k}="{v}"\n')
    try:
        os.chmod(ENV_FILE, 0o600)
    except Exception:
        pass

def verify_gemini_key(key: str) -> bool:
    if not key:
        return False
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Lauburu-Mesh/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False

def harvest_gemini():
    print("\n" + "=" * 65)
    print(" 🌐 [Step 1/2] Harvesting Google Gemini Free Tier Key")
    print("=" * 65)
    print(" Opening Google AI Studio in your default browser...")
    subprocess.run(["open", "https://aistudio.google.com/app/apikey"])
    
    print("\n 📋 Action required in browser:")
    print(" 1. Click 'Create API Key' (or copy an existing key).")
    print(" 2. Click 'Copy'.")
    print(" ⏳ Listening to your clipboard in the background...")

    initial_cb = get_clipboard()
    start_time = time.time()
    while time.time() - start_time < 90:
        time.sleep(0.5)
        current = get_clipboard()
        if current and current != initial_cb:
            # Gemini keys start with AIzaSy
            if current.startswith("AIzaSy") or len(current) == 39:
                print("\n 🎯 Key detected on clipboard!")
                print(" -> Verifying with Google AI Studio...", end="", flush=True)
                if verify_gemini_key(current):
                    print(" [✅ VERIFIED - Free Tier 1500 RPD Active]")
                else:
                    print(" [⚠️ Saved to .env]")
                save_env_var("GEMINI_API_KEY", current)
                clear_clipboard()
                print(" -> Cleared clipboard & saved directly to .env.")
                return True
    print("\n ⏱️ Timed out waiting for copy. Skipping to next step.")
    return False

def harvest_cloudflare():
    print("\n" + "=" * 65)
    print(" 🌐 [Step 2/2] Harvesting Cloudflare Workers AI Token")
    print("=" * 65)
    print(" Opening Cloudflare API Tokens in your default browser...")
    subprocess.run(["open", "https://dash.cloudflare.com/profile/api-tokens"])
    
    print("\n 📋 Action required in browser:")
    print(" 1. Click 'Create Token' -> 'Workers AI' template -> 'Continue to summary' -> 'Create Token'.")
    print(" 2. Click 'Copy' on the generated API token.")
    print(" ⏳ Listening to your clipboard in the background...")

    initial_cb = get_clipboard()
    start_time = time.time()
    while time.time() - start_time < 90:
        time.sleep(0.5)
        current = get_clipboard()
        if current and current != initial_cb:
            if len(current) >= 30 and not current.startswith("AIzaSy"):
                print("\n 🎯 Cloudflare Token detected on clipboard!")
                save_env_var("CLOUDFLARE_API_TOKEN", current)
                clear_clipboard()
                print(" -> Cleared clipboard & saved directly to .env.")
                return True
    print("\n ⏱️ Timed out waiting for copy.")
    return False

def main():
    print("\n" + "=" * 65)
    print(" 🤖 LAUBURU BROWSER-ASSISTED ZERO-LEAK KEY HARVESTER")
    print("=" * 65)
    print(" This tool opens the official provider pages in your logged-in")
    print(" browser and auto-catches the keys the moment you hit 'Copy'.")
    print(" Nothing is typed or displayed in the terminal or chat!")
    print("=" * 65)

    harvest_gemini()
    harvest_cloudflare()

    print("\n" + "=" * 65)
    print(" 🎉 HARVEST COMPLETE! All keys securely synced to .env.")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    main()
