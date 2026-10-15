#!/usr/bin/env python3
import subprocess
import xml.etree.ElementTree as ET
import sys
import re
import time

def dump_ui():
    """Extracts the UI hierarchy via ADB."""
    print("[*] Dumping UI hierarchy via Screen Lens ADB...")
    subprocess.run(["adb", "shell", "uiautomator", "dump", "/data/local/tmp/window_dump.xml"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["adb", "pull", "/data/local/tmp/window_dump.xml", "window_dump.xml"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tree = ET.parse("window_dump.xml")
    return tree.getroot()

def get_center_coords(bounds_str):
    """Calculates the center (x, y) from a bounds string like '[0,10][100,200]'."""
    m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
    if not m: return None
    x1, y1, x2, y2 = map(int, m.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2

def list_elements():
    root = dump_ui()
    print("\n--- Screen Lens UI Element Graph ---")
    idx = 0
    for node in root.iter('node'):
        text = node.get('text', '')
        desc = node.get('content-desc', '')
        bounds = node.get('bounds', '')
        clickable = node.get('clickable', 'false')
        val = text if text else desc
        if val:
            coords = get_center_coords(bounds)
            print(f"[{idx}] Text: '{val}' | Clickable: {clickable} | Center: {coords}")
        idx += 1
    print("------------------------------------\n")

def click_element(search_text):
    root = dump_ui()
    for node in root.iter('node'):
        text = node.get('text', '')
        desc = node.get('content-desc', '')
        val = text if text else desc
        if search_text.lower() in val.lower():
            bounds = node.get('bounds', '')
            coords = get_center_coords(bounds)
            if coords:
                print(f"[*] Clicking '{val}' at {coords}")
                subprocess.run(["adb", "shell", "input", "tap", str(coords[0]), str(coords[1])], check=True)
                return True
    print(f"[!] Element containing '{search_text}' not found.")
    return False

def type_text(text_to_type):
    print(f"[*] Injecting text: {text_to_type}")
    # Escape spaces for adb shell input text
    escaped = text_to_type.replace(" ", "%s")
    subprocess.run(["adb", "shell", "input", "text", escaped], check=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: screen_lens_automator.py [list|click|type] [args]")
        sys.exit(1)
        
    action = sys.argv[1]
    if action == "list":
        list_elements()
    elif action == "click" and len(sys.argv) > 2:
        click_element(sys.argv[2])
    elif action == "type" and len(sys.argv) > 2:
        type_text(sys.argv[2])
    else:
        print("Invalid command.")
