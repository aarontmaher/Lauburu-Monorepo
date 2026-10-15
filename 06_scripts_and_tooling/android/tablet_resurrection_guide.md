# 📱 Samsung Galaxy Tablet (Node L4) Physical Keyboard Resurrection Guide & Mesh Manual

**Target Device**: Samsung Galaxy Tablet (`Node L4` / `Linux_Tablet`)  
**Hardware Serial**: `R3CN40CJJ1R`  
**USB Vendor/Product**: `0x04e8:0x6860` (Default MTP) $\rightarrow$ `0x04e8:0x686e` / `0x685e` (RNDIS + ADB Composite)  
**Host Port**: Front USB-C Port 1 (`0x03110000` / Location ID `51445760`) on Apple M4 Pro Mac Mini Host (`L1`)  
**Canonical Mesh Transports**:
- USB Tethering Subnet: `192.168.42.129:5555` (Host: `192.168.42.1`)
- Wi-Fi Subnet: `192.168.8.185:5555` / `192.168.8.173:5555`
- Tailscale Overlay: `100.81.92.125:5555` / `100.99.210.89:5555`

---

## 🎯 Executive Summary

When Wi-Fi ADB drops (e.g. `192.168.8.185` is unreachable or ARP resolution is incomplete) and the tablet defaults to standard USB MTP/charging mode without exposing an ADB or CDC-NCM interface, remote host injection is physically blocked.

This guide provides the exact terminal commands to enter on the tablet's **physical hardware keyboard** to bridge the airgap. Once entered, the tablet immediately provisions a high-speed wired USB network bridge (`192.168.42.0/24`), starts `adbd` on TCP port `5555`, locks the CPU against Android Doze sleep (`termux-wake-lock`), and starts OpenSSH.

---

## 🔌 Pre-Flight Physical Check

1. **Cable Connection**: Ensure the USB-C cable is firmly seated into the **front left USB-C Port 1** of the Mac Mini M4 Pro and into the tablet's USB-C charging port.
2. **Display Power**: Wake the tablet display and ensure the lockscreen is unlocked.
3. **Active Terminal**: Open the terminal application on screen (Termux, Termux PRoot, or Debian Linux terminal).

---

## ⚡ Tier 1: The "Golden One-Liner" (Fastest Resurrection)

If your terminal is running **Termux with root access (`su`)**, copy or type this single contiguous line into the tablet terminal and press **Enter**:

```bash
termux-wake-lock; su -c "settings put global adb_enabled 1; setprop sys.usb.config rndis,adb; setprop service.adb.tcp.port 5555; stop adbd; start adbd; cmd connectivity start-tethering usb 2>/dev/null || true"; pkill sshd 2>/dev/null; sshd; echo "=== CURRENT IPS ==="; ip -br a || ip a
```

### What this accomplishes in $\le 2$ seconds:
1. `termux-wake-lock`: Prevents Android OS from putting CPU and Wi-Fi to sleep.
2. `settings put global adb_enabled 1`: Force-enables Android USB debugging.
3. `setprop sys.usb.config rndis,adb`: Switches Samsung USB hardware endpoint to composite RNDIS Ethernet + ADB.
4. `setprop service.adb.tcp.port 5555; stop adbd; start adbd`: Binds ADB daemon to TCP port 5555 across all interfaces.
5. `cmd connectivity start-tethering usb`: Activates USB-C network tethering, creating `192.168.42.0/24`.
6. `pkill sshd; sshd`: Restarts OpenSSH daemon on Termux port 8022.
7. Prints active IP assignments directly to the tablet screen.

---

## 📋 Tier 2: Step-by-Step Command Sequence (Typo-Resistant)

If you prefer typing clean, individual commands, or if you need non-root UI fallbacks, execute these steps sequentially:

### Step 1: Prevent Sleep & Start SSH
```bash
termux-wake-lock
pkill sshd 2>/dev/null
sshd
```
*(Termux SSH will listen on port `8022`)*

### Step 2: Resurrect ADB on TCP Port 5555 & USB
- **If Rooted (`su` available)**:
  ```bash
  su -c "setprop service.adb.tcp.port 5555; setprop sys.usb.config rndis,adb; stop adbd; start adbd"
  ```
- **If Non-Root (Opens Developer Options on Screen)**:
  ```bash
  am start -a com.android.settings.APPLICATION_DEVELOPMENT_SETTINGS
  ```
  *(Toggle **USB debugging** to ON, and **Wireless debugging** to ON)*

### Step 3: Enable USB Tethering (RNDIS / CDC-NCM Ethernet)
- **If Rooted (`su` available)**:
  ```bash
  su -c "svc usb setFunctions rndis,adb 2>/dev/null || cmd connectivity start-tethering usb"
  ```
- **If Non-Root (Opens Tethering Settings on Screen)**:
  ```bash
  am start -a android.settings.TETHER_SETTINGS
  ```
  *(Tap or toggle **USB tethering** to ON)*

### Step 4: Display Current Network Status & IP
```bash
ip -br a || ip a
```
*Note the IP assigned to `rndis0`, `wlan0`, or `tailscale0`.*

---

## 🐧 Tier 3: Emergency Fallback If Prompt is in Debian PRoot / Native Linux

If your tablet terminal shows `debian@...` or `root@localhost`:

1. **Restart Debian SSH Daemon**:
   ```bash
   sudo service ssh restart 2>/dev/null || /usr/sbin/sshd -p 22
   ```
2. **Bring up USB Gadget (If Native Kernel)**:
   ```bash
   sudo modprobe g_ether 2>/dev/null || true
   sudo ip link set usb0 up 2>/dev/null || sudo ip link set eth0 up 2>/dev/null
   sudo ip addr add 192.168.42.129/24 dev usb0 2>/dev/null || true
   ```
3. **If in Termux PRoot Container**:
   Type `exit` to return to the host Termux shell (`$`), then execute Tier 1 or Tier 2.

---

## 🖥️ Host Verification Commands (Run on Mac Mini)

Once the commands are executed on the tablet, verify connection state from the Mac Mini terminal:

### 1. Verify Physical USB & ADB Detection
```bash
# Check USB descriptor in IORegistry
ioreg -p IOUSB -w 0 -l | grep -B 2 -A 10 "SAMSUNG_Android"

# Check ADB devices
adb devices -l
```
*Expected*: `R3CN40CJJ1R` listed with status `device`.  
*(If status is `unauthorized`, look at the tablet screen and tap **Always allow from this computer** $\rightarrow$ **OK**)*.

### 2. Verify USB Network Bridge (RNDIS / CDC-NCM)
```bash
# Check if a new network interface appeared (e.g. en5, en8, etc.)
ifconfig | grep -B 1 -A 3 "inet 192.168.42."

# Ping the tablet over the physical USB-C cable
ping -c 3 192.168.42.129
```

### 3. Verify OpenSSH Connectivity
- **Termux SSH (Port 8022)**:
  ```bash
  ssh -p 8022 -o ConnectTimeout=3 u0_a...@[ip] "uname -a"
  ```
- **Debian SSH (Port 22)**:
  ```bash
  ssh -p 22 -o ConnectTimeout=3 -i ~/.ssh/id_ed25519 debian@[ip] "uname -a"
  ```

---

## 🔄 Automated Mesh Daemons & Long-Term Persistence

To ensure the tablet never drops offline again after physical reconnection:

### 1. Run the Dedicated Tablet USB Keepalive Daemon
```bash
# Test single diagnostic cycle
python3 /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/android/tablet_usb_keepalive.py --once

# Run persistent keepalive daemon
python3 /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/android/tablet_usb_keepalive.py --daemon &
```
The keepalive daemon automatically:
- Detects USB attachment of `R3CN40CJJ1R`.
- Establishes ADB reverse tunnels:
  - `tcp:8082` $\rightarrow$ `tcp:8082` (Qwen 3.8 Max Master Orchestrator via Prima.cpp PRP)
  - `tcp:4000` $\rightarrow$ `tcp:4000` (Lauburu Hub Services)
- Maintains `adbd tcpip 5555` for seamless Wi-Fi fallback.
- Monitors the `192.168.42.0/24` USB Ethernet link.

### 2. Mesh ADB Multi-Transport Watchdog
The monorepo's central watchdog `/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/android/mesh_adb_watchdog.py` now includes `Linux_Tablet` in its `EDGE_NODES` matrix:
```python
"Linux_Tablet": {
    "transports": [
        "192.168.42.129:5555",  # L1 USB-C Tethering ADB (RNDIS/CDC-NCM)
        "192.168.8.185:5555",   # L2 Local Wi-Fi LAN
        "192.168.8.173:5555",   # L2 Alt Local Wi-Fi LAN
        "100.81.92.125:5555",   # L3 Tailscale WireGuard Overlay
        "100.99.210.89:5555",     # Alt Tailscale Interface
    ],
    "usb_serials": ["R3CN40CJJ1R"],
    "device_hint": "tablet"
}
```

### 3. Hardening Against Android Doze & Phantom Process Killer
Once ADB is authorized, harden the tablet against background process termination:
```bash
bash /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/android/harden_android_node.sh R3CN40CJJ1R
```
This disables the Android 12+ Phantom Process Killer (`max_phantom_processes 2147483647`), keeps Wi-Fi awake during sleep (`wifi_sleep_policy 2`), keeps the tablet awake while plugged into USB (`stay_on_while_plugged_in 7`), and whitelists Termux, Tailscale, and OpenClaw from battery optimization.

---

## 🛠️ 4. Resolving Tailscale GitHub Version Sideloading & Update Conflicts

When Tailscale is sideloaded from GitHub releases (`tailscale-android`), Android signs it with the open-source release key rather than the Google Play Store key. This causes two major issues:
1. **No Auto-Updates**: Sideloaded GitHub APKs freeze on the downloaded version and never auto-update.
2. **Signature Collision (`INSTALL_FAILED_UPDATE_INCOMPATIBLE`)**: Google Play Store refuses to install updates over the GitHub APK due to certificate mismatches.

### Automated Tailscale Manager Script:
Use the dedicated automation tool:
```bash
python3 /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/android/manage_tablet_tailscale.py --inspect
```

#### Option A: Migrate to Auto-Updating Google Play Store Version (Recommended)
Cleanly removes the GitHub APK (clearing the signature lock) and redirects directly to Google Play:
```bash
python3 /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/android/manage_tablet_tailscale.py --migrate-play
```
On the tablet screen, tap **Install** in the Google Play Store. Future updates will be 100% automated by Google Play.

#### Option B: In-Place GitHub APK Upgrade via ADB (Preserves Data)
Downloads the latest release (`universal` / `arm64`) from the GitHub API and reinstalls in-place:
```bash
python3 /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/android/manage_tablet_tailscale.py --update-github
```

#### Option C: Automated On-Device Updates via Obtainium
Installs Obtainium to track GitHub releases and update Tailscale directly on the tablet without Google Play:
```bash
python3 /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/android/manage_tablet_tailscale.py --setup-obtainium
```

