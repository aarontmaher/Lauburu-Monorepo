#!/usr/bin/env python3
import os
import pty
import select
import subprocess
import sys
from pathlib import Path

BT_PTY_SYMLINK = Path("/tmp/bluetooth_terminal_pty")

def main():
    print("🚀 Initializing OpenGo Bluetooth IDE Server...")
    
    # Create the PTY for the Kai Morich Android terminal
    master_fd, slave_fd = pty.openpty()
    pty_name = os.ttyname(slave_fd)
    
    if BT_PTY_SYMLINK.is_symlink() or BT_PTY_SYMLINK.exists():
        BT_PTY_SYMLINK.unlink()
    BT_PTY_SYMLINK.symlink_to(pty_name)
    
    print(f"✅ PTY established at {pty_name} (Symlinked to {BT_PTY_SYMLINK})")
    print("📡 Ready for Kai Morich Android Terminal to connect...")

    ide_path = "/Volumes/Lauburu-Monorepo/01_apps/opengo_bt_ide/opengo_bt_ide"
    
    try:
        # Spawn the Go IDE inside the PTY slave
        process = subprocess.Popen(
            [ide_path],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
            env=dict(os.environ, TERM="xterm-256color")
        )
        
        # We don't read from master_fd here; the external Bluetooth serial daemon
        # (like socat or rfcomm) will read/write to the symlink.
        # But wait, if nothing reads master_fd, it might block.
        # The Android app connects to /tmp/bluetooth_terminal_pty via some daemon?
        # Yes, usually a rfcomm proxy or socat pipes bluetooth to this PTY.
        process.wait()
        
    finally:
        os.close(master_fd)
        os.close(slave_fd)
        if BT_PTY_SYMLINK.is_symlink():
            BT_PTY_SYMLINK.unlink()
        print("IDE Server closed.")

if __name__ == "__main__":
    main()
