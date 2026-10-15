import os
import sys
import pickle
import argparse
import io
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account

# Full Drive access so we can create/read folders like 'Lauburu_AI_Memory/lora_datasets'
SCOPES = ['https://www.googleapis.com/auth/drive']
VAULT_FOLDER_NAME = 'Lauburu_Model_Vault'
SERVICE_ACCOUNT_FILE = 'service_account.json'

def get_credentials(cli_client_id=None, cli_client_secret=None):
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"❌ ERROR: {SERVICE_ACCOUNT_FILE} not found!")
        print("Please ensure the service account key is saved in the current directory.")
        sys.exit(1)
        
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return creds

def get_or_create_folder(service, folder_name):
    results = service.files().list(
        q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        spaces='drive',
        fields='files(id, name)'
    ).execute()
    
    items = results.get('files', [])
    if not items:
        print("❌ ERROR: 'Lauburu_Model_Vault' folder not found or not shared!")
        print("\nTo use your 30 TB plan, you must:")
        print("1. Go to your personal Google Drive in the browser.")
        print("2. Create a folder named exactly 'Lauburu_Model_Vault'.")
        print("3. Right-click the folder -> Share.")
        print("4. Add this exact email as an 'Editor':")
        print("   gdrive-mesh-agent@gen-lang-client-0982729216.iam.gserviceaccount.com")
        sys.exit(1)
    return items[0].get('id')

def list_models(service, folder_id):
    print(f"📦 Listing models in Google Drive '{VAULT_FOLDER_NAME}'...")
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id, name, size)"
    ).execute()
    
    items = results.get('files', [])
    if not items:
        print("No models found in the vault.")
    else:
        for item in items:
            size_mb = int(item.get('size', 0)) / (1024 * 1024)
            print(f" - {item['name']} ({size_mb:.2f} MB) [ID: {item['id']}]")

def upload_model(service, folder_id, filepath):
    filename = os.path.basename(filepath)
    print(f"🚀 Uploading {filename} to Google Drive...")
    
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    
    # Use resumable upload for large models (GGUF, PyTorch, etc)
    media = MediaFileUpload(filepath, resumable=True)
    request = service.files().create(body=file_metadata, media_body=media, fields='id')
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%.", end='\r')
            
    print(f"\n✅ Upload complete! File ID: {response.get('id')}")

def download_model(service, file_id, output_path):
    print(f"⬇️ Downloading model to {output_path}...")
    request = service.files().get_media(fileId=file_id)
    
    with io.FileIO(output_path, 'wb') as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            if status:
                print(f"Downloaded {int(status.progress() * 100)}%.", end='\r')
                
    print("\n✅ Download complete!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Google Drive Model Vault Sync")
    parser.add_argument('action', choices=['list', 'upload', 'download'], help='Action to perform')
    parser.add_argument('--file', type=str, help='Local path to model for upload')
    parser.add_argument('--id', type=str, help='Google Drive File ID for download')
    parser.add_argument('--out', type=str, help='Output path for download')
    
    parser.add_argument('--client-id', type=str, help='OAuth Client ID (if not using client_secret.json)')
    parser.add_argument('--client-secret', type=str, help='OAuth Client Secret (if not using client_secret.json)')
    
    args = parser.parse_args()
    
    creds = get_credentials(cli_client_id=args.client_id, cli_client_secret=args.client_secret)
    service = build('drive', 'v3', credentials=creds)
    
    vault_id = get_or_create_folder(service, VAULT_FOLDER_NAME)
    
    if args.action == 'list':
        list_models(service, vault_id)
    elif args.action == 'upload':
        if not args.file:
            print("❌ --file is required for upload.")
            sys.exit(1)
        upload_model(service, vault_id, args.file)
    elif args.action == 'download':
        if not args.id or not args.out:
            print("❌ --id and --out are required for download.")
            sys.exit(1)
        download_model(service, args.id, args.out)
