import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/cloud-platform'
]
CLIENT_SECRET_FILE = '/Volumes/Lauburu-Monorepo/04_data_and_memory/client_secret.json'
TOKEN_FILE = '/Volumes/Lauburu-Monorepo/04_data_and_memory/token.json'

def generate_token():
    print(f"🔑 Initializing Sovereign OAuth Flow for Lauburu Workspace...")
    print(f"⚠️ IMPORTANT: Please ensure you select 'lauburu@lauburugrappling.com' when the browser opens.\n")
    if not os.path.exists(CLIENT_SECRET_FILE):
        print(f"[ERROR] Cannot find {CLIENT_SECRET_FILE}.")
        return
    
    # We explicitly bind to 127.0.0.1 to avoid macOS localhost IPv6 connection refused bugs
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    creds = flow.run_local_server(host='127.0.0.1', port=0)
    
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())
    print(f"\n✅ SUCCESS: token.json generated at {TOKEN_FILE}.")
    print("The Tri-Vault Sync, Sheets Publisher, and BigQuery Exporter can now all operate autonomously!")

if __name__ == '__main__':
    generate_token()
