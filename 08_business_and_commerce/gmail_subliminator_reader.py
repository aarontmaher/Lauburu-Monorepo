import os.path
import base64
import json
from pathlib import Path
from email.message import EmailMessage
from typing import List, Dict

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("ERROR: Missing Google API packages. Please run: pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    exit(1)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

CREDENTIALS_FILE = 'google_workspace_credentials.json'
TOKEN_FILE = 'google_workspace_token.json'

def authenticate_gmail():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"ERROR: {CREDENTIALS_FILE} not found!")
                print("Please download your OAuth 2.0 Client ID JSON from Google Cloud Console and save it as google_workspace_credentials.json")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return creds

def get_subliminator_emails(creds) -> List[Dict]:
    try:
        service = build('gmail', 'v1', credentials=creds)
        
        # Search for Subliminator emails
        query = "from:subliminator.com OR to:subliminator.com"
        results = service.users().messages().list(userId='me', q=query, maxResults=20).execute()
        messages = results.get('messages', [])

        if not messages:
            print('No emails found from Subliminator.')
            return []

        email_data = []
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
            payload = msg['payload']
            headers = payload.get("headers")
            
            subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), 'No Subject')
            sender = next((header['value'] for header in headers if header['name'].lower() == 'from'), 'Unknown Sender')
            date = next((header['value'] for header in headers if header['name'].lower() == 'date'), 'Unknown Date')
            
            # Extract body
            body = ""
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            elif 'body' in payload and 'data' in payload['body']:
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
                
            email_data.append({
                "date": date,
                "sender": sender,
                "subject": subject,
                "body": body
            })
            
        return email_data
    except HttpError as error:
        print(f'An error occurred: {error}')
        return []

def main():
    print("Authenticating with Google Workspace (lauburu@lauburugrappling.com)...")
    creds = authenticate_gmail()
    if not creds:
        return
        
    print("Successfully authenticated. Fetching Subliminator correspondence...")
    emails = get_subliminator_emails(creds)
    
    export_path = Path("subliminator_email_audit.json")
    with open(export_path, 'w') as f:
        json.dump(emails, f, indent=2)
        
    print(f"Exported {len(emails)} emails to {export_path}")
    print("These are now staged for AI review.")

if __name__ == '__main__':
    main()
