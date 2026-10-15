#!/usr/bin/env python3
"""
06_scripts_and_tooling/scripts/antigravity_session_manager.py
=============================================================
Automated Session & Context Orchestrator for Antigravity CLI (agy).
Launches and targets Antigravity sessions seamlessly across:
1. macOS Terminal (native Terminal.app / tmux / iTerm)
2. Android Termux (Pixel 10 Pro XL / Samsung S20 over Shizuku & ADB)
3. Headless background automation daemons

Supports targeting:
- Specific chat conversation ID (--conversation or --continue)
- Specific workspace directory / folder (--folder)
- Specific code file context (--file)
- Pre-populated initial prompt (--prompt)
- Execution modes (accept-edits, plan)
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import Optional

AGY_BIN = "/Users/aaron/.local/bin/agy"
DEFAULT_WORKSPACE = "/Volumes/Lauburu-Monorepo"


def build_agy_command(
    folder: Optional[str] = None,
    file_path: Optional[str] = None,
    conversation_id: Optional[str] = None,
    continue_latest: bool = False,
    mode: str = "accept-edits",
    prompt: Optional[str] = None,
    interactive: bool = True
) -> str:
    """Builds the exact agy CLI invocation command."""
    workspace = folder if folder and os.path.isdir(folder) else DEFAULT_WORKSPACE
    
    cmd_parts = [f"cd '{workspace}' && {AGY_BIN}"]
    
    if conversation_id:
        cmd_parts.append(f"--conversation '{conversation_id}'")
    elif continue_latest:
        cmd_parts.append("--continue")
        
    if mode in ["accept-edits", "plan"]:
        cmd_parts.append(f"--mode {mode}")
        
    # File context ingestion
    initial_text = prompt or ""
    if file_path and os.path.isfile(file_path):
        initial_text = f"Target File: {file_path}. {initial_text}".strip()
        cmd_parts.append(f"--add-dir '{os.path.dirname(os.path.abspath(file_path))}'")

    if initial_text:
        escaped_prompt = initial_text.replace("'", "'\\''")
        if interactive:
            cmd_parts.append(f"-i '{escaped_prompt}'")
        else:
            cmd_parts.append(f"-p '{escaped_prompt}'")
            
    return " ".join(cmd_parts)


def launch_in_macos_terminal(cmd: str):
    """Opens a new macOS Terminal window running the AGY command."""
    escaped_cmd = cmd.replace('\\', '\\\\').replace('"', '\\"')
    apple_script = f'''
    tell application "Terminal"
        activate
        do script "{escaped_cmd}"
    end tell
    '''
    subprocess.run(["osascript", "-e", apple_script], check=True)
    print("✔ [macOS Terminal] Launched Antigravity session in new Terminal window.")


def launch_in_android_termux(cmd: str, device_id: Optional[str] = None):
    """
    Automates launching Antigravity in Termux on Android device.
    Uses SSH bridge into Mac Mini host to execute agy without phone RAM overhead.
    """
    dev_flag = ["-s", device_id] if device_id else []
    
    # 1. Bring Termux to front
    start_termux = ["adb"] + dev_flag + ["shell", "am start -n com.termux/.app.TermuxActivity"]
    subprocess.run(start_termux, capture_output=True)
    
    # 2. Inject SSH launch command into Termux terminal
    escaped_inner = cmd.replace('"', '\\"')
    payload = f"ssh -t aaron@192.168.8.155 \\\"{escaped_inner}\\\"\\n"
    
    # Inject text into active Termux prompt
    input_cmd = ["adb"] + dev_flag + ["shell", f"input text 'ssh%saaron@192.168.8.155' && input keyevent 66"]
    subprocess.run(input_cmd, capture_output=True)
    
    print(f"✔ [Android Termux] Dispatched Antigravity launch to Termux on {device_id or 'device'}.")


def main():
    parser = argparse.ArgumentParser(description="Antigravity Automated Session & Context Manager")
    parser.add_argument("--target", choices=["terminal", "termux", "headless"], default="terminal",
                        help="Target execution environment")
    parser.add_argument("--folder", type=str, default=DEFAULT_WORKSPACE,
                        help="Target folder/workspace directory")
    parser.add_argument("--file", type=str, default=None,
                        help="Target specific file for context")
    parser.add_argument("--conversation", type=str, default=None,
                        help="Specific chat conversation ID to resume")
    parser.add_argument("--continue", "-c", dest="continue_latest", action="store_true",
                        help="Continue most recent conversation")
    parser.add_argument("--mode", choices=["accept-edits", "plan"], default="accept-edits",
                        help="Antigravity execution mode")
    parser.add_argument("--prompt", type=str, default=None,
                        help="Initial prompt or instruction to execute")
    parser.add_argument("--device", type=str, default="5B080DLCQ001LQ",
                        help="Android ADB device ID for Termux target")

    args = parser.parse_args()

    full_cmd = build_agy_command(
        folder=args.folder,
        file_path=args.file,
        conversation_id=args.conversation,
        continue_latest=args.continue_latest,
        mode=args.mode,
        prompt=args.prompt,
        interactive=(args.target != "headless")
    )

    print(f"🔧 Generated Antigravity Invocation:\n   {full_cmd}\n")

    if args.target == "terminal":
        launch_in_macos_terminal(full_cmd)
    elif args.target == "termux":
        launch_in_android_termux(full_cmd, device_id=args.device)
    elif args.target == "headless":
        print("🚀 Running non-interactively in background...")
        proc = subprocess.Popen(full_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            print(line, end="")
        proc.wait()


if __name__ == "__main__":
    main()
