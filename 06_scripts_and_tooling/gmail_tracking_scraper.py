import imaplib
import email
import re
import sys
import os
from email.header import decode_header

# ---------------------------------------------------------
# SETUP INSTRUCTIONS:
# 1. Go to https://myaccount.google.com/apppasswords
# 2. Create a new App Password (e.g. named "Lauburu Tracker")
# 3. Paste your Gmail address and that 16-letter password below.
# ---------------------------------------------------------
GMAIL_USER = "aaron.t.maher@gmail.com"
GMAIL_APP_PASSWORD = "vtnqdfqouabaxvau"

def extract_tracking_number(text):
    # Regex to catch common tracking formats (AusPost, DHL, etc.)
    # AusPost is usually 23-42 digits or starts with 33 / ETA / etc.
    # DHL is usually 10 digits.
    # We look for explicit keywords first
    match = re.search(r'(?i)(?:tracking number|track|tracking_no)[^\w]*(?:is|:|-)?\s*([A-Z0-9]{10,35})', text)
    if match:
        return match.group(1)
    return None

def check_for_shipping_email():
    if GMAIL_APP_PASSWORD == "your_16_letter_app_password":
        print("❌ ERROR: Please update GMAIL_APP_PASSWORD inside the script first!")
        sys.exit(1)

    print("🔌 Connecting to Gmail via IMAP...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        mail.select("inbox")
        
        # Search for unread emails from GL.iNet or containing "shipped"
        status, messages = mail.search(None, '(UNSEEN FROM "gl-inet.com")')
        # Also check general shipping keywords if GL.iNet uses a third-party sender
        if not messages[0]:
            status, messages = mail.search(None, '(UNSEEN SUBJECT "Shipped")')

        email_ids = messages[0].split()
        if not email_ids:
            print("📭 No new shipping emails found.")
            return

        print(f"📬 Found {len(email_ids)} unread shipping email(s). Analyzing...")

        for e_id in email_ids:
            res, msg_data = mail.fetch(e_id, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Extract text body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                try:
                                    body += part.get_payload(decode=True).decode()
                                except:
                                    pass
                    else:
                        body = msg.get_payload(decode=True).decode()

                    # Find tracking number
                    tracking_number = extract_tracking_number(body)
                    
                    if tracking_number:
                        print(f"🎯 SUCCESS: Found Tracking Number: {tracking_number}")
                        print("Injecting into router_tracker.py...")
                        
                        tracker_path = "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/router_tracker.py"
                        with open(tracker_path, 'r') as file:
                            script_content = file.read()
                        
                        script_content = re.sub(r'TRACKING_NUMBER = "WAITING_FOR_TRACKING_NUMBER"', 
                                                f'TRACKING_NUMBER = "{tracking_number}"', 
                                                script_content)
                                                
                        with open(tracker_path, 'w') as file:
                            file.write(script_content)
                            
                        print("✅ Tracking script updated successfully. Marking email as read.")
                        return

        print("🔍 Analyzed emails but couldn't find a tracking number pattern.")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("Ensure IMAP is enabled in your Gmail settings and the App Password is correct.")
        
if __name__ == "__main__":
    check_for_shipping_email()
