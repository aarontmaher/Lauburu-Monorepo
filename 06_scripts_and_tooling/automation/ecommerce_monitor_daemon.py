import subprocess
import time
import re
import datetime
from pathlib import Path

LOG_FILE = "/Users/aaron/.gemini/antigravity/brain/cdca10c9-e3ec-4303-aabd-7860383dd9a8/inbox_alerts.md"

def dump_ui():
    subprocess.run(["adb", "shell", "uiautomator", "dump", "/sdcard/window_dump.xml"], capture_output=True)
    subprocess.run(["adb", "pull", "/sdcard/window_dump.xml", "window_dump.xml"], capture_output=True)
    try:
        with open("window_dump.xml", "r") as f:
            return f.read()
    except:
        return ""

print("Starting E-Commerce Inbox Monitor Daemon...")
Path(LOG_FILE).write_text("# 📬 E-Commerce Inbox Monitor Log\n")

last_known_count = 0

while True:
    try:
        ui_data = dump_ui()
        # Look for indicators like "Messages: 1" or unread badges on standard marketplace apps
        # Gumtree usually shows "Replies: X" or a badge on the Messages tab.
        # Facebook shows a badge on the Messenger icon.
        
        replies_match = re.search(r'text="Replies:.*?text="(\d+)"', ui_data)
        messages_match = re.search(r'text="Messages".*?content-desc="(\d+) unread', ui_data)
        
        current_count = 0
        if replies_match:
            current_count += int(replies_match.group(1))
        if messages_match:
            current_count += int(messages_match.group(1))
            
        # Generic fallback: just look for the word "Messages" with a number next to it if not caught above
        if current_count == 0:
            generic_match = re.search(r'text="(\d+) New Message', ui_data, re.IGNORECASE)
            if generic_match:
                current_count += int(generic_match.group(1))

        if current_count > last_known_count:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            alert = f"[{timestamp}] 🚨 New Message Detected! Total unread/replies: {current_count}\n"
            with open(LOG_FILE, "a") as f:
                f.write(alert)
            
            # Announce via Mac TTS
            subprocess.run(["say", "-v", "Samantha", f"Alert: {current_count} new messages received regarding the iPhone sale."])
            
            last_known_count = current_count
            
        elif current_count < last_known_count:
            # User read the messages
            last_known_count = current_count
            
    except Exception as e:
        print(f"Daemon Error: {e}")
        
    time.sleep(120) # Check every 2 minutes
