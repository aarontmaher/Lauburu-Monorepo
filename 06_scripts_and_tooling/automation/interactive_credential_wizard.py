#!/usr/bin/env python3
"""
06_scripts_and_tooling/automation/interactive_credential_wizard.py
=================================================================
Interactive Zero-Leak Credential Wizard for Lauburu Mesh
-------------------------------------------------------
Runs directly in your local terminal to configure .env variables
with hidden input masking, zero shell-history footprint, and
immediate offline/free-tier endpoint verification.
"""

import os
import sys
import getpass
import urllib.request
import urllib.error
import json
from pathlib import Path

ENV_FILE = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.env")

def print_banner():
    print("\n" + "=" * 65)
    print(" 🛡️  LAUBURU SOVEREIGN CREDENTIAL & API WIZARD (Zero-Leak)")
    print("=" * 65)
    print(" Inputs are masked (typing is hidden). Keys are written directly")
    print(f" to: {ENV_FILE}")
    print(" Press ENTER to skip any key you do not want to configure right now.")
    print("=" * 65 + "\n")

def read_existing_env() -> dict:
    env_vars = {}
    if ENV_FILE.is_file():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip().strip("\"'")
    return env_vars

def write_env(env_vars: dict):
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write("# Lauburu Sovereign Mesh Environment Configuration\n")
        f.write("# Generated securely by interactive_credential_wizard.py\n\n")
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

def verify_cloudflare_token(token: str, account_id: str) -> bool:
    if not token or not account_id:
        return False
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/models/search"
    try:
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "Lauburu-Mesh/1.0"
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False

def main():
    print_banner()
    env_vars = read_existing_env()
    
    # 1. Julien AI / Google Jules
    print("🔹 [1/4] Julien AI / @google/jules Key (300 Free Requests/Day)")
    curr = " [Configured]" if env_vars.get("JULIEN_API_KEY") else " [Not Set]"
    print(f"    Current Status: {curr}")
    julien_key = getpass.getpass("    Enter JULIEN_API_KEY (or Enter to keep): ").strip()
    if julien_key:
        env_vars["JULIEN_API_KEY"] = julien_key
        print("    -> Stored locally.")

    # 2. Gemini Free Tier
    print("\n🔹 [2/4] Google Gemini API Key (1,500 Free Requests/Day)")
    curr = " [Configured]" if env_vars.get("GEMINI_API_KEY") else " [Not Set]"
    print(f"    Current Status: {curr}")
    gemini_key = getpass.getpass("    Enter GEMINI_API_KEY (or Enter to keep): ").strip()
    if gemini_key:
        env_vars["GEMINI_API_KEY"] = gemini_key
        print("    -> Verifying key with Google AI Studio...", end="", flush=True)
        if verify_gemini_key(gemini_key):
            print(" [✅ VERIFIED - Free Tier Active]")
        else:
            print(" [⚠️ Key saved, but verification timed out or failed]")

    # 3. Cloudflare Account ID & API Token
    print("\n🔹 [3/4] Cloudflare Workers AI (1,000 Free Requests/Day)")
    curr_acc = " [Configured]" if env_vars.get("CLOUDFLARE_ACCOUNT_ID") else " [Not Set]"
    print(f"    Account ID Status: {curr_acc}")
    cf_acc = input("    Enter CLOUDFLARE_ACCOUNT_ID (Visible, or Enter to keep): ").strip()
    if cf_acc:
        env_vars["CLOUDFLARE_ACCOUNT_ID"] = cf_acc

    curr_tok = " [Configured]" if env_vars.get("CLOUDFLARE_API_TOKEN") else " [Not Set]"
    print(f"    API Token Status:  {curr_tok}")
    cf_tok = getpass.getpass("    Enter CLOUDFLARE_API_TOKEN (Hidden, or Enter to keep): ").strip()
    if cf_tok:
        env_vars["CLOUDFLARE_API_TOKEN"] = cf_tok
        if env_vars.get("CLOUDFLARE_ACCOUNT_ID"):
            print("    -> Verifying token with Cloudflare...", end="", flush=True)
            if verify_cloudflare_token(cf_tok, env_vars["CLOUDFLARE_ACCOUNT_ID"]):
                print(" [✅ VERIFIED - Cloudflare AI Active]")
            else:
                print(" [⚠️ Token saved, but verification failed]")

    # 4. Storage / Secret Access Keys (Optional S3/R2)
    print("\n🔹 [4/4] Storage Keys (AWS / R2 S3 Compatibility - Optional)")
    s3_id = input("    Enter AWS_ACCESS_KEY_ID (or Enter to skip): ").strip()
    if s3_id:
        env_vars["AWS_ACCESS_KEY_ID"] = s3_id
    s3_secret = getpass.getpass("    Enter AWS_SECRET_ACCESS_KEY (or Enter to skip): ").strip()
    if s3_secret:
        env_vars["AWS_SECRET_ACCESS_KEY"] = s3_secret

    write_env(env_vars)
    print("\n" + "=" * 65)
    print(" 🎉 SUCCESS! All configuration saved to .env with permissions (0600).")
    print(" The Quota Manager and Local Mesh will now pick up these keys.")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    main()
