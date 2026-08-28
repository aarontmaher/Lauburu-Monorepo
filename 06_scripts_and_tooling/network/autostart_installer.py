import os
import sys
import platform
from pathlib import Path
import subprocess

def install_macos_launchd():
    print("🍎 Detected macOS. Installing LaunchAgent for Autostart & Sleep Prevention...")
    plist_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.lauburu.nomad_courier</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>caffeinate -dimsu python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/nomad_courier_self_healer.py --daemon &amp; python3 /Users/aaron/DFS_UNIFIED/05_agents_and_swarms/teamwork_projects/swarm_dashboard_ai_training/backend/app.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/lauburu_nomad.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/lauburu_nomad_error.log</string>
</dict>
</plist>"""
    
    plist_path = Path.home() / "Library/LaunchAgents/ai.lauburu.nomad_courier.plist"
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    plist_path.write_text(plist_content)
    
    subprocess.run(f"launchctl load -w {plist_path} 2>/dev/null", shell=True)
    print("✅ macOS LaunchAgent Installed and Loaded! It runs caffeinate (non-sleeping) and the Nomad Courier + AI Training Game on boot.")

def install_linux_systemd():
    print("🐧 Detected Linux. Installing systemd user service...")
    service_content = """[Unit]
Description=Lauburu Nomad Courier & AI Training Game
After=network.target

[Service]
Type=simple
ExecStart=/bin/bash -c "python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/nomad_courier_self_healer.py --daemon & python3 /Users/aaron/DFS_UNIFIED/05_agents_and_swarms/teamwork_projects/swarm_dashboard_ai_training/backend/app.py"
Restart=always
RestartSec=10

[Install]
WantedBy=default.target"""

    systemd_dir = Path.home() / ".config/systemd/user"
    systemd_dir.mkdir(parents=True, exist_ok=True)
    service_path = systemd_dir / "lauburu_nomad.service"
    service_path.write_text(service_content)
    
    subprocess.run("systemctl --user enable lauburu_nomad.service", shell=True)
    subprocess.run("systemctl --user start lauburu_nomad.service", shell=True)
    print("✅ Linux systemd service enabled and started!")

def install_android_termux():
    print("📱 Detected Android (Termux). Installing Termux:Boot script and wake-lock...")
    boot_dir = Path.home() / ".termux/boot"
    boot_dir.mkdir(parents=True, exist_ok=True)
    boot_script = boot_dir / "99_lauburu_nomad.sh"
    
    script_content = """#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
nohup python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/nomad_courier_self_healer.py --daemon > /dev/null 2>&1 &
nohup python3 /Users/aaron/DFS_UNIFIED/05_agents_and_swarms/teamwork_projects/swarm_dashboard_ai_training/backend/app.py > /dev/null 2>&1 &
"""
    boot_script.write_text(script_content)
    subprocess.run(f"chmod +x {boot_script}", shell=True)
    print("✅ Android Termux:Boot script installed with termux-wake-lock enabled!")

if __name__ == "__main__":
    system = platform.system().lower()
    if sys.prefix != sys.base_prefix and 'com.termux' in sys.prefix:
        install_android_termux()
    elif system == 'darwin':
        install_macos_launchd()
    elif system == 'linux':
        install_linux_systemd()
    else:
        print(f"⚠️ Unsupported OS: {system}")
