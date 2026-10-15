import os
import json
import time
import logging
from google.cloud import pubsub_v1
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "lauburu-project")
SUBSCRIPTION_ID = os.environ.get("PUBSUB_SUBSCRIPTION_ID", "google-chat-outbound")
SHEET_ID = os.environ.get("TELEMETRY_SHEET_ID")
DRIVE_FOLDER_ID = os.environ.get("BACKUP_DRIVE_FOLDER_ID")
CREDENTIALS_FILE = os.environ.get("GCP_CREDENTIALS_FILE", "/Volumes/Lauburu-Monorepo/client_secret.json")

def get_google_services():
    try:
        if os.path.exists(CREDENTIALS_FILE):
            credentials = service_account.Credentials.from_service_account_file(
                CREDENTIALS_FILE,
                scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            )
            sheets_service = build('sheets', 'v4', credentials=credentials)
            drive_service = build('drive', 'v3', credentials=credentials)
            return sheets_service, drive_service
    except Exception as e:
        logging.error(f"Failed to init Google Services: {e}")
    return None, None

sheets_service, drive_service = get_google_services()

def log_to_sheets(payload_size, latency):
    if not sheets_service or not SHEET_ID:
        return
    try:
        body = {
            'values': [[time.strftime("%Y-%m-%dT%H:%M:%SZ"), "GoogleChat", payload_size, latency]]
        }
        sheets_service.spreadsheets().values().append(
            spreadsheetId=SHEET_ID,
            range="A1",
            valueInputOption="RAW",
            body=body
        ).execute()
        logging.info("Telemetry appended to Google Sheets")
    except Exception as e:
        logging.error(f"Failed to log to sheets: {e}")

def backup_to_drive(payload_json):
    if not drive_service or not DRIVE_FOLDER_ID:
        return
    try:
        filename = f"chat_backup_{int(time.time())}.json"
        with open(filename, 'w') as f:
            f.write(payload_json)
        
        file_metadata = {
            'name': filename,
            'parents': [DRIVE_FOLDER_ID]
        }
        media = MediaFileUpload(filename, mimetype='application/json')
        drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        os.remove(filename)
        logging.info(f"Backed up {filename} to Google Drive")
    except Exception as e:
        logging.error(f"Failed to backup to drive: {e}")

def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    start_time = time.time()
    payload = message.data.decode("utf-8")
    logging.info(f"Received message ID: {message.message_id}")
    
    # Google Workspace Integrations
    log_to_sheets(len(payload), round(time.time() - start_time, 4))
    backup_to_drive(payload)
    
    message.ack()
    logging.info(f"Acknowledged message ID: {message.message_id}")

def main():
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)
    
    logging.info(f"Listening for messages on {subscription_path}...")
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    
    with subscriber:
        try:
            streaming_pull_future.result()
        except Exception as e:
            logging.error(f"Subscriber error: {e}")
            streaming_pull_future.cancel()
            time.sleep(10) # Throttle restarts on error

if __name__ == "__main__":
    main()
