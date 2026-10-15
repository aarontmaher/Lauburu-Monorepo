# 📱 Pixel AVF Linux IDE Suite — Chromium, Code-Server & JupyterLab

This suite provides pre-configured, lightweight IDE options designed to run natively inside the **Android Virtualization Framework (AVF) Linux microVM** (Debian 13 under `crosvm`/pKVM with Linux kernel `6.12.92-android16`) on the **Google Pixel 10 Pro XL (Tensor G5)**.

---

## 🏛️ Architecture Overview

The Google Pixel 10 Pro XL hosts a dedicated Linux AVF microVM allocated up to 10.5 GB RAM. To preserve host battery, keep memory residency under 3.5 GB (Rule 9), and enable seamless remote development, three distinct IDE surfaces are packaged:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PIXEL 10 PRO XL — AVF LINUX IDE SUITE                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. CODE-SERVER (VS Code in Browser)                                         │
│    • Port: 8443 (HTTP/WebSocket)                                            │
│    • Low-overhead web-based VS Code IDE with touch optimizations             │
│    • Pre-configured extensions, dark mode, large touch targets              │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. JUPYTERLAB (Interactive Data & Biometrics Notebooks)                     │
│    • Port: 8888 (HTTP/WebSocket)                                            │
│    • Real-time data science, Pan-Tompkins ECG DSP, and PySpark exploration  │
│    • Headless server with token/passwordless authentication on WireGuard/TS │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. CHROMIUM (Headless & Touch Kiosk Browser Engine)                         │
│    • Port: 9222 (DevTools CDP Remote Debugging) / GUI or VNC Display        │
│    • Optimized flags for ARM64 Tensor G5 NEON vector acceleration           │
│    • Screen Lens accessibility auditing and automated UI validation         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Fast Deployment

### Option A: Native Systemd Services (Recommended on AVF microVM)
```bash
cd /mnt/shared/00_core_infrastructure/pixel_avf_ide
sudo bash code-server/install_code_server.sh
sudo bash jupyterlab/install_jupyterlab.sh
sudo bash chromium/install_chromium.sh

# Start the unified supervisor
sudo bash avf_ide_supervisor.sh start
```

### Option B: Zero-Install Docker Compose
```bash
cd /mnt/shared/00_core_infrastructure/pixel_avf_ide
docker compose -f docker-compose.pixel-ide.yml up -d
```

---

## 🌐 Network Access & Port Forwarding

Services bind to `0.0.0.0` inside the AVF microVM. To access them from Android or other mesh nodes:
- **Tailscale IP:** `http://100.88.197.78:8443` (code-server), `:8888` (JupyterLab)
- **Local Tap Gateway:** `http://10.86.187.34:8443`
- **Android Port Reverse (via ADB):**
  ```bash
  adb reverse tcp:8443 tcp:8443
  adb reverse tcp:8888 tcp:8888
  adb reverse tcp:9222 tcp:9222
  ```
