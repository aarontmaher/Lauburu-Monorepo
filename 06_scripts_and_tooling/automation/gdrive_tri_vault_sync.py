import os
import time
import logging
import json
from pathlib import Path
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Sovereign Credential Loading (Zero-Cloud Leakage)
# Adhering to api-key-handler skill and Rule #2
CREDENTIALS_PATH = os.environ.get(
    "GDRIVE_CREDENTIALS_PATH", 
    "/Volumes/Lauburu-Monorepo/04_data_and_memory/client_secret.json"
)

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

def get_drive_service():
    """Initializes and returns the Google Drive API service."""
    if not os.path.exists(CREDENTIALS_PATH):
        logging.warning(f"Credentials not found at {CREDENTIALS_PATH}. Cannot authenticate to Google Drive.")
        return None

    creds = None
    token_path = os.path.join(os.path.dirname(CREDENTIALS_PATH), 'token.json')
    
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, ['https://www.googleapis.com/auth/drive'])
        
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logging.error(f"Failed to refresh token: {e}")
                creds = None
                
        if not creds:
            # Check if it's a service account first
            try:
                with open(CREDENTIALS_PATH, 'r') as f:
                    creds_data = json.load(f)
                if "type" in creds_data and creds_data["type"] == "service_account":
                    creds = service_account.Credentials.from_service_account_info(
                        creds_data, scopes=['https://www.googleapis.com/auth/drive']
                    )
                else:
                    logging.error(f"No valid token.json found. You must run an interactive OAuth flow to generate it using {CREDENTIALS_PATH}.")
                    return None
            except Exception as e:
                logging.error(f"Error parsing credentials: {e}")
                return None

    try:
        service = build('drive', 'v3', credentials=creds)
        logging.info("Google Drive API service initialized successfully.")
        return service
    except Exception as e:
        logging.error(f"Failed to initialize Drive service: {e}")
        return None

def get_or_create_folder(service, folder_name, parent_id=None):
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
        
    response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = response.get('files', [])
    if files:
        return files[0]['id']
        
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]
        
    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')

def upload_file(service, filepath, parent_id):
    file_name = os.path.basename(filepath)
    query = f"name='{file_name}' and '{parent_id}' in parents and trashed=false"
    response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = response.get('files', [])
    
    media = MediaFileUpload(filepath, resumable=True)
    if files:
        file_id = files[0]['id']
        logging.info(f"[Sync] Updating {file_name} (ID: {file_id})...")
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        logging.info(f"[Sync] Uploading {file_name}...")
        file_metadata = {'name': file_name, 'parents': [parent_id]}
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()

def sync_directory(service, local_dir, gdrive_parent_id=None):
    """
    Recursively uploads files from local_dir to Google Drive.
    """
    if not service:
        return
        
    local_path = Path(local_dir)
    if not local_path.exists():
        logging.warning(f"Local directory {local_dir} does not exist.")
        return
        
    root_folder_id = get_or_create_folder(service, local_path.name, gdrive_parent_id)
    
    for root, dirs, files in os.walk(local_dir):
        rel_path = os.path.relpath(root, local_dir)
        current_parent_id = root_folder_id
        
        if rel_path != '.':
            parts = rel_path.split(os.sep)
            for part in parts:
                current_parent_id = get_or_create_folder(service, part, current_parent_id)
                
        for file in files:
            # Skip hidden files
            if file.startswith('.'):
                continue
            filepath = os.path.join(root, file)
            try:
                upload_file(service, filepath, current_parent_id)
            except Exception as e:
                logging.error(f"Failed to upload {filepath}: {e}")

def run_sync_daemon():
    """Continuous background daemon to sync Tri-Vault structures."""
    obsidian_src = "/Volumes/Lauburu-Monorepo/obsidian_vault/"
    lora_src = "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/"
    
    logging.info("Starting Google Workspace Tri-Vault sync daemon...")
    
    while True:
        service = get_drive_service()
        
        if service:
            logging.info("Initiating sync for obsidian_vault...")
            sync_directory(service, obsidian_src)
            
            logging.info("Initiating sync for lora_datasets...")
            sync_directory(service, lora_src)
            
            logging.info("Sync cycle completed.")
        else:
            logging.error("Sync cycle skipped due to missing/invalid credentials.")
            
        time.sleep(3600)

if __name__ == "__main__":
    try:
        run_sync_daemon()
    except KeyboardInterrupt:
        logging.info("Sync daemon stopped by user.")
