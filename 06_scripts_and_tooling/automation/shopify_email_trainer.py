#!/usr/bin/env python3
import imaplib
import email
import sys
import os
import re
import subprocess
import json
import time
from email.header import decode_header

print("=====================================================")
print("📧 Lauburu AI E-Commerce Email Training Simulator (24/7 DAEMON)")
print("=====================================================")

GMAIL_USER = "aaron.t.maher@gmail.com"
GMAIL_APP_PASSWORD = "vtnqdfqouabaxvau"

def extract_json(stdout_str):
    try:
        lines = stdout_str.strip().split('\n')
        for line in reversed(lines):
            if line.startswith('{') and line.endswith('}'):
                return json.loads(line)
    except:
        pass
    return None

def fetch_spam_shopify_emails(seen_ids):
    print("[*] Connecting to Gmail via IMAP...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        mail.select("inbox")
        status, messages = mail.search(None, '(OR SUBJECT "Shopify" SUBJECT "Order")')
        
        all_ids = messages[0].split()
        if not all_ids:
            return [], []

        print(f"    [+] Found {len(all_ids)} total relevant emails in inbox.")
        
        # Find new IDs not processed yet
        new_ids = [eid for eid in all_ids if eid not in seen_ids]
        if not new_ids:
            print("    [✓] No new emails to process this cycle.")
            return [], []
            
        print(f"    [+] Found {len(new_ids)} NEW emails to train on.")
        
        training_batch = []
        # Process up to 3 new emails per cycle to avoid API spam
        for e_id in new_ids[-3:]: 
            res, msg_data = mail.fetch(e_id, '(RFC822)')
            msg = email.message_from_bytes(msg_data[0][1])
            subject_encoded = msg.get("Subject")
            if subject_encoded:
                subject, encoding = decode_header(subject_encoded)[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else "utf-8")
            else:
                subject = "No Subject"
            
            sender = msg.get("From")
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            body += part.get_payload(decode=True).decode()
                        except:
                            pass
            else:
                body = msg.get_payload(decode=True).decode()
                
            training_batch.append({"subject": subject, "body": body[:500], "sender": sender})
            
        return training_batch, new_ids[-3:]
    except Exception as e:
        print(f"[-] Connection failed: {e}")
        return [], []

def practice_responding(emails):
    if not emails:
        return
        
    for idx, em in enumerate(emails):
        print(f"\n--- 🏋️ Training Scenario {idx+1} ---")
        print(f"From: {em['sender']}")
        print(f"Subject: {em['subject']}")
        print(f"Body snippet: {em['body'].strip()[:100]}...")
        
        print("\n    -> Local Master Orchestrator drafting response...")
        prompt = f"You are the e-commerce manager for Lauburu. Draft a response to this customer email. DO NOT lowball. Defend the value. Respond professionally.\nCustomer Email: {em['body']}"
        
        # Local AI simulating via Gemini Flash to save costs on the draft side (in production this would be local Qwen 3.8)
        res = subprocess.run(["python3", "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/automation/lens_intelligence_router.py", "agy", "gemini_flash", prompt], capture_output=True, text=True) 
        
        json_res = extract_json(res.stdout)
        draft = json_res.get("response", "Draft Failed") if json_res else "Parsing Failed"
        
        print(f"\n    [+] Drafted Response:\n{draft[:200]}...\n")
        
        print("    -> Sending to Cloud Frontier Architect (Gemini 3.1 Pro) for Grading & ELO Adjustment...")
        # We explicitly use gemini_pro here because of the higher usage quota vs Opus!
        grade_prompt = f"Grade this AI e-commerce response on a scale of 1-100 based on value preservation and professionalism. Reply with ONLY the number and a 1-sentence reason.\nResponse: {draft}"
        grade_res = subprocess.run(["python3", "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/automation/lens_intelligence_router.py", "agy", "gemini_pro", grade_prompt], capture_output=True, text=True)
        
        grade_json = extract_json(grade_res.stdout)
        evaluation = grade_json.get("response", "0 - Grade Failed") if grade_json else "0 - Parsing Failed"
        print(f"    [🌟] Cloud Grade: {evaluation.strip()}")
        
        try:
            score = int(re.search(r'\d+', evaluation).group())
            if score >= 80:
                print("    [💰] High quality response! Awarding +15 ELO to Local Orchestrator.")
                os.system("python3 /Volumes/Lauburu-Monorepo/05_agents_and_swarms/elo_currency_governor.py grant Qwen_3.8_Max 'Excellent Email Response' 15")
                # Attempt to buy RAM automatically if possible
                os.system("python3 /Volumes/Lauburu-Monorepo/05_agents_and_swarms/elo_currency_governor.py buy_ram Qwen_3.8_Max")
            else:
                print("    [-] Poor response. Deducting -5 ELO.")
                os.system("python3 /Volumes/Lauburu-Monorepo/05_agents_and_swarms/elo_currency_governor.py grant Qwen_3.8_Max 'Poor Email Response' -5")
        except:
            print("    [!] Could not parse numeric score.")
            
        print("\n    -> Executing Dry-Run Email Dispatch...")
        subprocess.run(["python3", "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/automation/ecommerce_email_agent.py", "--origin", "local", "--to", em['sender'], "--subject", f"Re: {em['subject']}", "--body", draft])

if __name__ == "__main__":
    seen_ids = set()
    while True:
        try:
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Waking up for training cycle...")
            emails, new_ids = fetch_spam_shopify_emails(seen_ids)
            if emails:
                practice_responding(emails)
                for i in new_ids:
                    seen_ids.add(i)
        except Exception as e:
            print(f"Cycle Error: {e}")
            
        print("\n[*] Cycle complete. Sleeping for 30 minutes to conserve API quotas and IMAP connections...")
        time.sleep(1800)
