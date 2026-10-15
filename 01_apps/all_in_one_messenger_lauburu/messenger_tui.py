#!/usr/bin/env python3
"""
messenger_tui.py
================================================================================
🥋 LAUBURU SOVEREIGN OMNI-MESSENGER INTERACTIVE TERMINAL
Governed by Rule 0 (Zero-Mock), Rule 1 (Truth Verification), and Rule 9.
Clean-Room Ad-Free Terminal Companion for macOS, Linux AVF, and SSH.
Interacts with the Unified Backend on Port 5050.
================================================================================
"""

import sys
import os
import json
import time
import urllib.request
import urllib.error
from datetime import datetime

BACKEND_URL = os.environ.get("OMNI_BACKEND_URL", "http://127.0.0.1:5050")
INBOX_FILE = "/tmp/lauburu_unified_inbox.json"

# ANSI Colors
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_RED = "\033[91m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_MAGENTA = "\033[95m"
C_CYAN = "\033[96m"
C_WHITE = "\033[97m"
C_BG_BLUE = "\033[44m"
C_BG_RED = "\033[41m"
C_BG_GREEN = "\033[42m"

def fetch_inbox_data():
    """Fetches real messages from port 5050 or fallback JSON."""
    try:
        req = urllib.request.Request(f"{BACKEND_URL}/inbox", headers={"User-Agent": "OmniTUI/1.0"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("messages", [])
    except Exception:
        pass

    # Local fallback
    if os.path.exists(INBOX_FILE):
        try:
            with open(INBOX_FILE, "r") as f:
                raw = json.load(f)
                return [{
                    "id": f"MSG-LOCAL-{i}",
                    "platform": m.get("platform", "Local"),
                    "account": "Local Account",
                    "sender": m.get("sender", "Unknown"),
                    "preview": m.get("content", ""),
                    "timestamp": m.get("timestamp", "Recent"),
                    "triage": {"priority": "P2 - Standard", "suggested_reply": None}
                } for i, m in enumerate(raw)]
        except Exception:
            pass

    return []

def send_reply(recipient: str, text: str) -> bool:
    """Dispatches a reply through the unified backend."""
    try:
        payload = json.dumps({"recipient": recipient, "reply": text}).encode("utf-8")
        req = urllib.request.Request(
            f"{BACKEND_URL}/message/send",
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "OmniTUI/1.0"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"\n{C_RED}Error sending reply: {e}{C_RESET}")
        return False

def render_tui(filter_mode: str = "ALL", selected_index: int = 0):
    messages = fetch_inbox_data()
    
    # Filter
    if filter_mode == "PERSONAL":
        messages = [m for m in messages if "personal" in m.get("account", "").lower() or "gumtree" in m.get("platform", "").lower() or "facebook" in m.get("platform", "").lower() or "gmail" in m.get("platform", "").lower()]
    elif filter_mode == "BUSINESS":
        messages = [m for m in messages if "business" in m.get("account", "").lower() or "workspace" in m.get("platform", "").lower() or "subliminator" in m.get("sender", "").lower()]
    elif filter_mode == "URGENT":
        messages = [m for m in messages if "p0" in m.get("triage", {}).get("priority", "").lower() or "p1" in m.get("triage", {}).get("priority", "").lower()]

    print("\033[2J\033[H", end="") # Clear screen
    print(f"{C_BOLD}{C_BG_BLUE}{C_WHITE} ✉️  OMNI MESSENGER LAUBURU — SOVEREIGN MULTI-CHANNEL TERMINAL {C_RESET}")
    print(f"{C_DIM}Zero Ads | Zero Trackers | <350MB RAM | TinyLM Sub-2ms Triage | Port 5050{C_RESET}")
    print(f"{C_CYAN}Active Filter: {C_BOLD}[{filter_mode}]{C_RESET} | Total in View: {C_BOLD}{len(messages)}{C_RESET}\n" + "─" * 78)

    if not messages:
        print(f"\n {C_YELLOW}📭 No messages match the active filter [{filter_mode}].{C_RESET}\n")
    else:
        for idx, msg in enumerate(messages):
            is_selected = (idx == selected_index)
            prefix = f"{C_BOLD}{C_GREEN}▶{C_RESET} " if is_selected else "  "
            
            platform = msg.get("platform", "Unknown")
            sender = msg.get("sender", "Unknown")
            preview = msg.get("preview", msg.get("content", ""))
            timestamp = msg.get("timestamp", "")
            triage = msg.get("triage", {})
            priority = triage.get("priority", "P2 - Standard")
            
            # Color code priorities
            if "p0" in priority.lower():
                p_badge = f"{C_BOLD}{C_RED}[{priority.split(' - ')[0]}]{C_RESET}"
            elif "p1" in priority.lower():
                p_badge = f"{C_BOLD}{C_YELLOW}[{priority.split(' - ')[0]}]{C_RESET}"
            elif "p3" in priority.lower():
                p_badge = f"{C_BOLD}{C_CYAN}[{priority.split(' - ')[0]}]{C_RESET}"
            else:
                p_badge = f"{C_GREEN}[{priority.split(' - ')[0]}]{C_RESET}"

            account_badge = f"{C_MAGENTA}[{msg.get('account', 'Account')}]{C_RESET}"
            
            print(f"{prefix}{p_badge} {C_BOLD}{platform}{C_RESET} • {account_badge}")
            print(f"   {C_WHITE}From:{C_RESET} {C_BOLD}{sender}{C_RESET} ({C_DIM}{timestamp}{C_RESET})")
            print(f"   ╰─> {C_WHITE}{preview}{C_RESET}")
            
            if triage.get("suggested_reply"):
                print(f"   {C_GREEN}💡 AI Suggestion:{C_RESET} {C_DIM}{triage['suggested_reply']}{C_RESET}")
            print("─" * 78)

    print(f"\n{C_BOLD}Commands:{C_RESET} [1-{len(messages)}] Select | [R]eply | [T]oggle Filter (All/Personal/Business/Urgent) | [Q]uit")
    return messages

def main_interactive():
    filter_modes = ["ALL", "PERSONAL", "BUSINESS", "URGENT"]
    filter_idx = 0
    selected_idx = 0

    if "--once" in sys.argv or not sys.stdin.isatty():
        render_tui(filter_modes[filter_idx], selected_idx)
        print("\n[Non-interactive exit]")
        return

    while True:
        messages = render_tui(filter_modes[filter_idx], selected_idx)
        try:
            choice = input(f"\n{C_CYAN}Omni-Messenger > {C_RESET}").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting Omni-Messenger.")
            break

        if choice == "q":
            print("\nExiting Omni-Messenger.")
            break
        elif choice == "t":
            filter_idx = (filter_idx + 1) % len(filter_modes)
            selected_idx = 0
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(messages):
                selected_idx = idx
        elif choice == "r":
            if 0 <= selected_idx < len(messages):
                target = messages[selected_idx]
                recipient = target.get("sender", "Unknown")
                suggestion = target.get("triage", {}).get("suggested_reply", "")
                
                print(f"\n{C_BOLD}Drafting reply to:{C_RESET} {recipient}")
                if suggestion:
                    print(f"{C_GREEN}Suggested:{C_RESET} {suggestion}")
                    use_sugg = input("Use AI suggested reply? (Y/n): ").strip().lower()
                    if use_sugg in ["", "y", "yes"]:
                        reply_text = suggestion
                    else:
                        reply_text = input("Enter your custom reply: ").strip()
                else:
                    reply_text = input("Enter your reply: ").strip()

                if reply_text:
                    if send_reply(recipient, reply_text):
                        print(f"\n{C_GREEN}✓ Reply staged and logged successfully!{C_RESET}")
                    else:
                        print(f"\n{C_RED}✗ Failed to send reply.{C_RESET}")
                    time.sleep(1.5)
            else:
                print(f"\n{C_RED}No valid message selected to reply to.{C_RESET}")
                time.sleep(1.0)

if __name__ == "__main__":
    main_interactive()
