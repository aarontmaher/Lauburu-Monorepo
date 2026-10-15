#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import base64
import json
from datetime import datetime, timedelta
from typing import List, Optional
from email.message import EmailMessage

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError:
    print("Missing Google API libraries. Please run:")
    print("pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    sys.exit(1)

# UPGRADED SCOPES FOR WRITE / SEND ACCESS (E-Commerce Use)
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/calendar'
]

CREDS_FILE = 'workspace_credentials.json'
TOKEN_FILE = 'workspace_token.json'

def get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Failed to refresh token: {e}. Re-authenticating...", file=sys.stderr)
                creds = None
        if not creds:
            if not os.path.exists(CREDS_FILE):
                raise FileNotFoundError(f"Missing {CREDS_FILE}. Please complete Phase 1 of the implementation plan.")
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return creds

def get_gmail_service():
    return build('gmail', 'v1', credentials=get_credentials())

def get_calendar_service():
    return build('calendar', 'v3', credentials=get_credentials())

def search_gmail(query: str, max_results: int = 5) -> str:
    try:
        service = get_gmail_service()
        results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return "No emails found matching the query."
            
        output = []
        for msg in messages:
            msg_detail = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['Subject', 'From', 'Date']).execute()
            headers = msg_detail.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            output.append(f"ID: {msg['id']} | From: {sender} | Subject: {subject}")
            
        return "\n".join(output)
    except Exception as e: return f"Error searching Gmail: {str(e)}"

def read_email(message_id: str) -> str:
    try:
        service = get_gmail_service()
        msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
        headers = msg.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        
        parts = msg.get('payload', {}).get('parts', [])
        body = "No plain text body found."
        
        if not parts:
            data = msg.get('payload', {}).get('body', {}).get('data')
            if data: body = base64.urlsafe_b64decode(data).decode('utf-8')
        else:
            for part in parts:
                if part.get('mimeType') == 'text/plain':
                    data = part.get('body', {}).get('data')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
        return f"From: {sender}\nSubject: {subject}\n\n{body}"
    except Exception as e: return f"Error reading email: {str(e)}"

def send_email(to: str, subject: str, body: str) -> str:
    """Drafts and sends an email."""
    try:
        service = get_gmail_service()
        message = EmailMessage()
        message.set_content(body)
        message['To'] = to
        message['From'] = 'me'
        message['Subject'] = subject
        
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}
        
        sent = service.users().messages().send(userId="me", body=create_message).execute()
        return f"Successfully sent email to {to}. Message ID: {sent['id']}"
    except Exception as e: return f"Error sending email: {str(e)}"

def list_calendar_events(days_ahead: int = 7) -> str:
    try:
        service = get_calendar_service()
        now = datetime.utcnow().isoformat() + 'Z'
        time_max = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary', timeMin=now, timeMax=time_max, maxResults=20, singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events: return f"No upcoming events found in the next {days_ahead} days."
        output = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            output.append(f"[{start}] {event['summary']}")
        return "\n".join(output)
    except Exception as e: return f"Error listing calendar events: {str(e)}"

def create_calendar_event(summary: str, start_time: str, end_time: str) -> str:
    """Creates a new calendar event."""
    try:
        service = get_calendar_service()
        event = {
            'summary': summary,
            'start': {'dateTime': start_time}, # e.g. '2026-09-11T09:00:00-07:00'
            'end': {'dateTime': end_time},
        }
        created = service.events().insert(calendarId='primary', body=event).execute()
        return f"Successfully created event: {created.get('htmlLink')}"
    except Exception as e: return f"Error creating event: {str(e)}"

def run_stdio_mcp():
    print("E-Commerce Workspace MCP Server Initialized (Stdio Mode)", file=sys.stderr)
    while True:
        try:
            line = sys.stdin.readline()
            if not line: break
            
            request = json.loads(line)
            method = request.get("method")
            params = request.get("params", {})
            req_id = request.get("id")
            
            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "ecommerce-workspace-mcp", "version": "1.0.0"}
                    }
                }
            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": [
                            {"name": "search_gmail", "description": "Search inbox", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
                            {"name": "read_email", "description": "Read email", "inputSchema": {"type": "object", "properties": {"message_id": {"type": "string"}}, "required": ["message_id"]}},
                            {"name": "send_email", "description": "Send an email (E-Commerce B2B/B2C communication)", "inputSchema": {"type": "object", "properties": {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}, "required": ["to", "subject", "body"]}},
                            {"name": "list_calendar_events", "description": "List events", "inputSchema": {"type": "object", "properties": {"days_ahead": {"type": "integer"}}, "required": ["days_ahead"]}},
                            {"name": "create_calendar_event", "description": "Schedule a meeting or fulfillment deadline", "inputSchema": {"type": "object", "properties": {"summary": {"type": "string"}, "start_time": {"type": "string", "description": "ISO 8601 e.g. 2026-09-11T09:00:00-07:00"}, "end_time": {"type": "string"}}, "required": ["summary", "start_time", "end_time"]}}
                        ]
                    }
                }
            elif method == "tools/call":
                tool_name = params.get("name")
                args = params.get("arguments", {})
                
                try:
                    if tool_name == "search_gmail": result_text = search_gmail(args.get("query"), args.get("max_results", 5))
                    elif tool_name == "read_email": result_text = read_email(args.get("message_id"))
                    elif tool_name == "send_email": result_text = send_email(args.get("to"), args.get("subject"), args.get("body"))
                    elif tool_name == "list_calendar_events": result_text = list_calendar_events(args.get("days_ahead", 7))
                    elif tool_name == "create_calendar_event": result_text = create_calendar_event(args.get("summary"), args.get("start_time"), args.get("end_time"))
                    else: result_text = f"Unknown tool: {tool_name}"
                    response = {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": result_text}]}}
                except Exception as e:
                    response = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32603, "message": str(e)}}
            else:
                response = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}
                
            print(json.dumps(response), flush=True)
            
        except json.JSONDecodeError: continue
        except Exception as e:
            print(f"Fatal error: {e}", file=sys.stderr)
            break

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--auth-only":
        print("Authenticating with Google Workspace...")
        get_credentials()
        print("Authentication complete. token.json generated securely.")
    else:
        run_stdio_mcp()
