#!/usr/bin/env python3
import os
import glob
import json
import requests
import time
import shutil

print("🔍 [Local AI Sovereign] Initializing Zero-Cloud Credential Hunter...")

DOWNLOADS_DIR = os.path.expanduser("~/Downloads")
DESKTOP_DIR = os.path.expanduser("~/Desktop")
VAULT_FILE = os.path.expanduser("~/.lauburu/sovereign_vault.json")
LAUBURU_CONFIG = os.path.expanduser("~/.lauburu/config.yaml")

# Expand the search net for ALL credential types
extensions = ["*.json", "*.txt", "*.csv", "*.pem", "*.pub", "*.key", "*.env", "*.conf", "*.ovpn"]
search_patterns = []
for ext in extensions:
    search_patterns.append(os.path.join(DOWNLOADS_DIR, ext))
    search_patterns.append(os.path.join(DESKTOP_DIR, ext))

target_files = []
now = time.time()

for pattern in search_patterns:
    for f in glob.glob(pattern):
        # Check if modified in last 24h
        if os.path.isfile(f) and (now - os.path.getmtime(f)) < 86400:
            target_files.append(f)

print(f"📁 Found {len(target_files)} recent files to analyze locally.")

# Using Rule 10 Offloaded Syntax Worker if available, otherwise local fallback
QWEN_ENDPOINT = "http://100.101.39.98:8081/v1/chat/completions"
try:
    requests.get("http://100.101.39.98:8081", timeout=0.5)
except:
    # Fallback to local host if Linux Mini is offline
    QWEN_ENDPOINT = "http://127.0.0.1:8081/v1/chat/completions"

found_keys = 0
vault_data = []

# Load existing vault if present
if os.path.exists(VAULT_FILE):
    try:
        with open(VAULT_FILE, 'r') as vf:
            vault_data = json.load(vf)
    except:
        pass

# Expanded fast-skip triggers for emails, passwords, SSH keys, API keys
triggers = ["sk-", "client_id", "Bearer", "OPENROUTER", "ssh-rsa", "ssh-ed25519", 
            "BEGIN PRIVATE KEY", "BEGIN PUBLIC KEY", "password", "passwd", 
            "token", "secret", "login", "@gmail", "@"]

for file_path in target_files:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read(5000) # Read first 5k chars
            
        if not any(t.lower() in content.lower() for t in triggers):
            continue # Fast skip
            
        print(f"🧠 Detected potential credential in {os.path.basename(file_path)}. Routing to Local Qwen 2.5 Coder...")
        
        system_prompt = """You are a local Sovereign Credential Parser. Extract any API keys, public/private SSH keys, passwords, emails, or login details from the text.
Return ONLY a valid JSON array of objects. Each object must have:
- 'type' (e.g. 'api_key', 'ssh_public_key', 'password', 'email', 'oauth_secret')
- 'identifier' (the username, email, or service name, if applicable)
- 'secret' (the actual key, password, or token)
No markdown formatting, just the raw JSON array. If nothing is found, return []"""

        payload = {
            "model": "qwen2.5-coder-7b",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ],
            "temperature": 0.0
        }
        
        resp = requests.post(QWEN_ENDPOINT, json=payload, timeout=15)
        if resp.status_code == 200:
            raw_out = resp.json()["choices"][0]["message"]["content"].strip()
            # Strip potential markdown code blocks
            if raw_out.startswith("```json"):
                raw_out = raw_out[7:]
            elif raw_out.startswith("```"):
                raw_out = raw_out[3:]
            if raw_out.endswith("```"):
                raw_out = raw_out[:-3]
            
            try:
                extracted_creds = json.loads(raw_out.strip())
                if isinstance(extracted_creds, list) and len(extracted_creds) > 0:
                    print(f"✅ Success! Extracted {len(extracted_creds)} credentials.")
                    for cred in extracted_creds:
                        cred["source_file"] = os.path.basename(file_path)
                        cred["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        vault_data.append(cred)
                        
                        # Special injection for OpenRouter config.yaml
                        if cred.get("secret", "").startswith("sk-or-v1-"):
                            if os.path.exists(LAUBURU_CONFIG):
                                with open(LAUBURU_CONFIG, 'r') as cf:
                                    config_data = cf.read()
                                if "sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxx" in config_data:
                                    config_data = config_data.replace("sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxx", cred["secret"])
                                    with open(LAUBURU_CONFIG, 'w') as cf:
                                        cf.write(config_data)
                                    print("💉 Injected OpenRouter Key into ~/.lauburu/config.yaml")

                    print(f"🧹 Zero-Trace Cleanup: Shredding {os.path.basename(file_path)}...")
                    os.remove(file_path)
                    found_keys += len(extracted_creds)
            except json.JSONDecodeError:
                print(f"⚠️ Failed to parse JSON from model output: {raw_out}")
                
    except Exception as e:
        print(f"⚠️ Error analyzing {file_path}: {e}")

# Save updated vault
if found_keys > 0:
    with open(VAULT_FILE, 'w') as vf:
        json.dump(vault_data, vf, indent=4)
    print(f"🔐 Sovereign Vault updated securely at {VAULT_FILE} ({found_keys} new entries)")
else:
    print("💤 No new local credentials found requiring injection.")
