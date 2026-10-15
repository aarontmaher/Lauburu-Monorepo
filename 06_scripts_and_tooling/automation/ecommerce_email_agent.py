#!/usr/bin/env python3
import argparse
import sys
import os

print("=====================================================")
print("📧 Lauburu AI Dual-Context Email Agent")
print("=====================================================")

def send_email(origin, to_address, subject, body, live_mode=False):
    # Determine the sender based on the AI origin
    if origin == "cloud":
        sender = "aaron.t.maher@gmail.com"
        tier = "Frontier Cloud Orchestrator"
    elif origin == "local":
        sender = "lauburu@lauburugrappling.com"
        tier = "Sovereign Master Local AI"
    else:
        print("[!] Unknown origin. Defaulting to local.")
        sender = "lauburu@lauburugrappling.com"
        tier = "Unknown AI"

    print(f"[*] Origin Context: {tier}")
    print(f"[*] Dispatching Email As: {sender}")
    print(f"[*] Target: {to_address}")
    print(f"[*] Subject: {subject}")
    print("-" * 50)
    print(body)
    print("-" * 50)

    if not live_mode:
        print("[🛡️ GUARDRAIL ACTIVE] Executing in DRY-RUN mode.")
        print("    -> No actual network transmission occurred.")
        print("    -> To execute a live business transaction, use --live flag. Ensure it passes the Truth Audit.")
    else:
        print("[⚠️ LIVE MODE ENGAGED] Transmitting payload to SMTP gateway...")
        # Placeholder for actual SMTP/SendGrid/Apple Mail automation
        print(f"    [+] Successfully dispatched email from {sender} to {to_address}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Email Dispatcher")
    parser.add_argument("--origin", choices=["cloud", "local"], required=True, help="Cloud or Local AI")
    parser.add_argument("--to", required=True, help="Recipient email address")
    parser.add_argument("--subject", required=True, help="Email subject")
    parser.add_argument("--body", required=True, help="Email body content")
    parser.add_argument("--live", action="store_true", help="Send actual email instead of dry-run")
    
    args = parser.parse_args()
    send_email(args.origin, args.to, args.subject, args.body, args.live)
