import os
import time
import json
import psutil
import subprocess
import socket
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

TOKEN_PATH = "/Volumes/Lauburu-Monorepo/04_data_and_memory/token.json"
CONFIG_PATH = "/Volumes/Lauburu-Monorepo/04_data_and_memory/sheets_config.json"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']
SHEET_TITLE = "Lauburu Mesh Telemetry Lake"
BATCH_INTERVAL_SEC = 10

def get_real_ping():
    try:
        # Ping 8.8.8.8 to get real RTT latency (timeout in ms for macOS)
        output = subprocess.check_output(["ping", "-c", "1", "-W", "1000", "8.8.8.8"], universal_newlines=True)
        for line in output.split('\n'):
            if 'time=' in line:
                return float(line.split('time=')[1].split(' ')[0])
    except Exception:
        pass
    return -1.0

def get_real_ram_free():
    mem = psutil.virtual_memory()
    return mem.available / (1024 ** 3)  # GB

def get_credentials():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                print("Token refresh failed. Please regenerate token.json.")
                return None
        else:
            print(f"Token not found or invalid at {TOKEN_PATH}. Please generate token.json.")
            return None
            
    if not creds.has_scopes(['https://www.googleapis.com/auth/spreadsheets']):
        print("Warning: 'spreadsheets' scope is missing from token.json.")
        print("The script will attempt to use Drive API to create the sheet and Sheets API to edit it.")
        print("If editing fails, please regenerate the token with 'https://www.googleapis.com/auth/spreadsheets'.")
        
    return creds

def get_or_create_sheet(creds, service):
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
            if 'spreadsheet_id' in config:
                return config['spreadsheet_id']
    
    print(f"Creating new spreadsheet: {SHEET_TITLE} via Drive API")
    try:
        drive_service = build('drive', 'v3', credentials=creds)
        file_metadata = {
            'name': SHEET_TITLE,
            'mimeType': 'application/vnd.google-apps.spreadsheet'
        }
        file = drive_service.files().create(body=file_metadata, fields='id').execute()
        spreadsheet_id = file.get('id')
        
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, 'w') as f:
            json.dump({'spreadsheet_id': spreadsheet_id}, f)
        
        print("Initializing headers via Sheets API...")
        headers = [['Timestamp', 'Host', 'RAM_Available_GB', 'Ping_RTT_ms']]
        body = {'values': headers}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range="Sheet1!A1",
            valueInputOption="RAW", body=body).execute()
            
        return spreadsheet_id
    except HttpError as error:
        print(f"An error occurred creating or initializing sheet: {error}")
        return None

def publish_loop():
    creds = get_credentials()
    if not creds:
        return

    try:
        service = build('sheets', 'v4', credentials=creds)
    except Exception as e:
        print(f"Failed to build Sheets service: {e}")
        return

    spreadsheet_id = get_or_create_sheet(creds, service)
    if not spreadsheet_id:
        print("Could not obtain spreadsheet ID.")
        return
        
    print(f"Starting telemetry publisher. Spreadsheet ID: {spreadsheet_id}")
    hostname = socket.gethostname()
    buffer = []
    
    while True:
        try:
            timestamp = datetime.now().isoformat()
            ping_ms = get_real_ping()
            ram_gb = get_real_ram_free()
            
            row = [timestamp, hostname, f"{ram_gb:.2f}", f"{ping_ms:.2f}"]
            buffer.append(row)
            
            if len(buffer) >= BATCH_INTERVAL_SEC:
                body = {'values': buffer}
                backoff = 1
                success = False
                while not success and backoff <= 32:
                    try:
                        service.spreadsheets().values().append(
                            spreadsheetId=spreadsheet_id, range="Sheet1!A:D",
                            valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS", body=body).execute()
                        print(f"Published {len(buffer)} rows.")
                        buffer.clear()
                        success = True
                    except HttpError as err:
                        if err.resp.status in [429, 500, 502, 503, 504]:
                            print(f"HttpError {err.resp.status}. Backing off for {backoff} seconds.")
                            time.sleep(backoff)
                            backoff *= 2
                        else:
                            print(f"Fatal HttpError during append: {err}")
                            return
                            
            time.sleep(1)
            
        except KeyboardInterrupt:
            print("Stopping.")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    publish_loop()
