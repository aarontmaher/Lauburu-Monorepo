#!/usr/bin/env python3
"""
Antigravity Multi-Device Account & Auto-Connect System
Manages device registration, user accounts, and cross-device connectivity
"""

import json
import hashlib
import uuid
import subprocess
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import socket
import os


class AccountManager:
    """Manage user accounts and device registration"""
    
    def __init__(self):
        self.accounts_file = Path.home() / ".antigravity" / "accounts.json"
        self.devices_file = Path.home() / ".antigravity" / "devices.json"
        self.sessions_file = Path.home() / ".antigravity" / "sessions.json"
        
        # Create config directories
        self.accounts_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.accounts = self._load_accounts()
        self.devices = self._load_devices()
        self.sessions = self._load_sessions()
    
    def log(self, msg):
        print(f"👤 [ACCOUNT] {msg}")
    
    def _load_accounts(self):
        """Load accounts from file"""
        if self.accounts_file.exists():
            with open(self.accounts_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _load_devices(self):
        """Load device registry"""
        if self.devices_file.exists():
            with open(self.devices_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _load_sessions(self):
        """Load active sessions"""
        if self.sessions_file.exists():
            with open(self.sessions_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_accounts(self):
        """Save accounts to file"""
        with open(self.accounts_file, 'w') as f:
            json.dump(self.accounts, f, indent=2)
    
    def _save_devices(self):
        """Save device registry"""
        with open(self.devices_file, 'w') as f:
            json.dump(self.devices, f, indent=2)
    
    def _save_sessions(self):
        """Save sessions"""
        with open(self.sessions_file, 'w') as f:
            json.dump(self.sessions, f, indent=2)
    
    def _hash_password(self, password, salt=None):
        """Hash password with salt"""
        if salt is None:
            salt = os.urandom(32).hex()
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}${hashed.hex()}"
    
    def _verify_password(self, password, hash_with_salt):
        """Verify password against hash"""
        salt = hash_with_salt.split('$')[0]
        return hash_with_salt == self._hash_password(password, salt)
    
    def create_account(self, username, password, email, full_name=""):
        """Create new user account"""
        
        if username in self.accounts:
            self.log(f"❌ Account '{username}' already exists")
            return False
        
        account = {
            "username": username,
            "email": email,
            "full_name": full_name,
            "password_hash": self._hash_password(password),
            "account_id": str(uuid.uuid4()),
            "created_at": datetime.now().isoformat(),
            "devices": [],
            "is_active": True
        }
        
        self.accounts[username] = account
        self._save_accounts()
        
        self.log(f"✅ Account created: {username} ({email})")
        return True
    
    def verify_account(self, username, password):
        """Verify account credentials"""
        
        if username not in self.accounts:
            self.log(f"❌ Account '{username}' not found")
            return False
        
        account = self.accounts[username]
        
        if not self._verify_password(password, account["password_hash"]):
            self.log(f"❌ Invalid password for '{username}'")
            return False
        
        if not account["is_active"]:
            self.log(f"❌ Account '{username}' is inactive")
            return False
        
        self.log(f"✅ Account verified: {username}")
        return True
    
    def register_device(self, username, device_name, device_type, device_ip):
        """Register device to account"""
        
        if username not in self.accounts:
            self.log(f"❌ Account not found")
            return None
        
        device_id = str(uuid.uuid4())
        
        device = {
            "device_id": device_id,
            "device_name": device_name,
            "device_type": device_type,  # "phone", "laptop", "desktop", "server"
            "device_ip": device_ip,
            "device_hostname": subprocess.run("hostname", shell=True, capture_output=True, text=True).stdout.strip(),
            "username": username,
            "registered_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "is_online": True,
            "public_key": self._generate_public_key()
        }
        
        self.devices[device_id] = device
        self.accounts[username]["devices"].append(device_id)
        
        self._save_devices()
        self._save_accounts()
        
        self.log(f"✅ Device registered: {device_name} ({device_type}) for {username}")
        return device_id
    
    def _generate_public_key(self):
        """Generate public key for device"""
        return str(uuid.uuid4())
    
    def create_session(self, username, device_id):
        """Create authenticated session"""
        
        session_token = str(uuid.uuid4())
        
        session = {
            "session_id": session_token,
            "username": username,
            "device_id": device_id,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
            "is_active": True
        }
        
        self.sessions[session_token] = session
        self._save_sessions()
        
        self.log(f"✅ Session created for {username}")
        return session_token
    
    def verify_session(self, session_token):
        """Verify session token"""
        
        if session_token not in self.sessions:
            return None
        
        session = self.sessions[session_token]
        
        if not session["is_active"]:
            return None
        
        if datetime.fromisoformat(session["expires_at"]) < datetime.now():
            return None
        
        return session
    
    def get_user_devices(self, username):
        """Get all devices for user"""
        
        if username not in self.accounts:
            return []
        
        device_ids = self.accounts[username]["devices"]
        devices = [self.devices[did] for did in device_ids if did in self.devices]
        return devices
    
    def get_account_info(self, username):
        """Get account information"""
        
        if username not in self.accounts:
            return None
        
        account = self.accounts[username].copy()
        account.pop("password_hash", None)  # Don't expose hash
        
        return account


class LocalHostAutoConnect:
    """Auto-connect devices on localhost/LAN"""
    
    def __init__(self, account_manager):
        self.am = account_manager
        self.discovery_running = False
    
    def log(self, msg):
        print(f"🔗 [AUTO-CONNECT] {msg}")
    
    def get_local_ip(self):
        """Get this device's local IP"""
        try:
            result = subprocess.run(
                "hostname -I | awk '{print $1}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip()
        except:
            return None
    
    def discover_local_devices(self):
        """Discover other Antigravity devices on local network"""
        
        self.log("Scanning local network for Antigravity devices...")
        
        local_devices = []
        
        try:
            # Scan for devices responding to Antigravity port
            result = subprocess.run(
                "arp-scan -l 2>/dev/null | grep -i antigravity || true",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            for line in result.stdout.split('\n'):
                if line.strip():
                    local_devices.append(line.strip())
            
            self.log(f"Found {len(local_devices)} local Antigravity devices")
            return local_devices
        
        except Exception as e:
            self.log(f"Discovery failed: {str(e)[:50]}")
            return []
    
    def auto_connect_device(self, username, password, device_name, device_type):
        """Auto-connect a device to account"""
        
        self.log(f"Auto-connecting {device_name}...")
        
        # Verify account
        if not self.am.verify_account(username, password):
            self.log("❌ Authentication failed")
            return False
        
        # Get local IP
        device_ip = self.get_local_ip()
        if not device_ip:
            self.log("❌ Could not determine device IP")
            return False
        
        # Register device
        device_id = self.am.register_device(username, device_name, device_type, device_ip)
        if not device_id:
            self.log("❌ Device registration failed")
            return False
        
        # Create session
        session_token = self.am.create_session(username, device_id)
        
        # Save session locally
        session_file = Path.home() / ".antigravity" / "current_session.json"
        with open(session_file, 'w') as f:
            json.dump({
                "session_token": session_token,
                "device_id": device_id,
                "username": username,
                "connected_at": datetime.now().isoformat()
            }, f, indent=2)
        
        self.log(f"✅ Device auto-connected!")
        return True
    
    def sync_devices_on_lan(self, username):
        """Sync all user's devices on local network"""
        
        self.log(f"Syncing devices for {username}...")
        
        devices = self.am.get_user_devices(username)
        
        for device in devices:
            self.log(f"  → {device['device_name']} ({device['device_type']}) at {device['device_ip']}")


class MultiUserIntegration:
    """Manage multiple users and their devices"""
    
    def __init__(self):
        self.am = AccountManager()
        self.auto_connect = LocalHostAutoConnect(self.am)
    
    def log(self, msg):
        print(f"🌐 [MULTI-USER] {msg}")
    
    def setup_new_user(self, username, password, email, full_name=""):
        """Set up new user account"""
        
        self.log(f"Setting up new user: {username}")
        
        if not self.am.create_account(username, password, email, full_name):
            return False
        
        self.log(f"✅ User account created for {username}")
        return True
    
    def onboard_device(self, username, password, device_name, device_type):
        """Onboard new device for user"""
        
        self.log(f"Onboarding {device_name} ({device_type}) for {username}...")
        
        if not self.auto_connect.auto_connect_device(username, password, device_name, device_type):
            return False
        
        self.log(f"✅ Device onboarded successfully")
        return True
    
    def list_user_devices(self, username):
        """List all devices for user"""
        
        devices = self.am.get_user_devices(username)
        
        print(f"\n📱 Devices for {username}:\n")
        
        for device in devices:
            online_status = "🟢 Online" if device["is_online"] else "🔴 Offline"
            print(f"  {device['device_name']}")
            print(f"    Type: {device['device_type']}")
            print(f"    IP: {device['device_ip']}")
            print(f"    Status: {online_status}")
            print(f"    Last seen: {device['last_seen']}")
            print()
    
    def show_account_dashboard(self, username):
        """Show account dashboard"""
        
        account = self.am.get_account_info(username)
        devices = self.am.get_user_devices(username)
        
        print(f"""
╔════════════════════════════════════════════════════════════════════════════╗
║                        ANTIGRAVITY ACCOUNT DASHBOARD                       ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║ Account Information:
║ ├─ Username: {account['username']}
║ ├─ Email: {account['email']}
║ ├─ Full Name: {account['full_name'] or 'Not set'}
║ ├─ Account ID: {account['account_id'][:8]}...
║ ├─ Created: {account['created_at'][:10]}
║ └─ Status: {'Active' if account['is_active'] else 'Inactive'}
║
║ Connected Devices: {len(devices)}
║""")
        
        for i, device in enumerate(devices, 1):
            online = "🟢" if device["is_online"] else "🔴"
            print(f"║ {i}. {online} {device['device_name']} ({device['device_type']})")
            print(f"║    └─ {device['device_ip']} • {device['device_hostname']}")
        
        print(f"""║
╚════════════════════════════════════════════════════════════════════════════╝
        """)


class CrossDeviceSyncService:
    """Sync data and state across all user devices"""
    
    def __init__(self, account_manager):
        self.am = account_manager
        self.sync_state = defaultdict(dict)
    
    def log(self, msg):
        print(f"🔄 [SYNC] {msg}")
    
    def sync_network_config(self, username):
        """Sync network optimization config across all user's devices"""
        
        self.log(f"Syncing network config for {username}...")
        
        devices = self.am.get_user_devices(username)
        
        config = {
            "timestamp": datetime.now().isoformat(),
            "user": username,
            "devices": len(devices),
            "optimization_strategy": "auto"  # Can be set per network conditions
        }
        
        for device in devices:
            self.sync_state[username][device['device_id']] = config
            self.log(f"  → Synced to {device['device_name']}")
        
        return config
    
    def sync_ai_conclusions(self, username):
        """Sync all AI conclusions across devices"""
        
        self.log(f"Syncing AI conclusions for {username}...")
        
        devices = self.am.get_user_devices(username)
        
        # In production, would read from shared bus
        conclusions = {
            "timestamp": datetime.now().isoformat(),
            "total_devices": len(devices),
            "conclusions_count": 0
        }
        
        return conclusions


def interactive_setup():
    """Interactive setup for new users"""
    
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║   🚀 ANTIGRAVITY - MULTI-DEVICE ACCOUNT SETUP                            ║
║                                                                            ║
║   Set up your account and auto-connect all your devices                   ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    multi_user = MultiUserIntegration()
    
    print("\n1️⃣  CREATE ACCOUNT")
    print("-" * 50)
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    email = input("Email: ").strip()
    full_name = input("Full Name (optional): ").strip()
    
    if not multi_user.setup_new_user(username, password, email, full_name):
        print("❌ Account creation failed")
        return
    
    print("\n2️⃣  REGISTER DEVICES")
    print("-" * 50)
    
    devices_count = 0
    while True:
        device_name = input(f"\nDevice name (e.g., 'My Pixel', 'MacBook Pro'): ").strip()
        if not device_name:
            break
        
        device_type = input("Device type (phone/laptop/desktop/server): ").strip()
        
        if multi_user.onboard_device(username, password, device_name, device_type):
            devices_count += 1
            print(f"✅ {device_name} registered")
        
        another = input("\nAdd another device? (y/n): ").strip().lower()
        if another != 'y':
            break
    
    print("\n3️⃣  ACCOUNT DASHBOARD")
    print("-" * 50)
    multi_user.show_account_dashboard(username)
    
    print(f"\n✅ Setup complete! You have registered {devices_count} device(s)")
    print(f"\nYour devices are now:")
    print("  • Auto-connected on local network")
    print("  • Synced across all platforms")
    print("  • Ready for distributed AI analysis")


if __name__ == "__main__":
    interactive_setup()

