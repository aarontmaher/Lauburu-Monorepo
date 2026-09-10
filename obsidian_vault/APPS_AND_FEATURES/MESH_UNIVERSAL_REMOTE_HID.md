---
title: "Lauburu Mesh Universal Remote HID & Screen Controller"
tags: [mesh, hid, trackpad, keyboard, screenview, s20, pixel, macos, linux, tri_proof]
updated: "2026-09-05"
---

# 🖱️ Lauburu Mesh Universal Remote HID & Screen Controller (Port 4006)
- Related: [[Index]] | [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]] | [[CANONICAL_PROJECT_AND_STORAGE_RULE]]

The **Mesh Universal Remote HID Controller** turns your **Samsung Galaxy S20** and **Pixel 10 Pro XL** into a headless multi-touch trackpad, optional keyboard, and screenview monitor across all 7 layers of the physical mesh.

## 🌐 Quick Access URLs
- **Local Mesh (Wi-Fi):** `http://192.168.8.155:4006`
- **Global Zero-Trust (Tailscale):** `http://100.119.199.76:4006`

## 🕹️ Supported Multi-Node Routing Across 7 Layers
1. **L1: Mac Mini M4 Pro (Host):** Native CoreGraphics Ctypes (`<1ms` latency, zero external pip dependencies).
2. **L2: MacBook Pro M1 Max:** Remote SSH AppleScript & CoreGraphics injection via 10Gbps TB4 bridge.
3. **L3: Linux Head Node (Ryzen 7):** Remote terminal execution & Docker compute gateway.
4. **L4: Linux Tablet (Debian):** Mobile touch DSP console.
5. **L5: MacBook Air M4:** Remote SSH AppleScript & CoreGraphics injection.
6. **L6: Pixel 10 Pro XL:** Termux SSH daemon (Port 8022) & Edge TPU sensor telemetry.
7. **GW: GL.iNet Router:** OpenWrt UCI/terminal administration & USB ADB bridge.
8. **L7: Samsung S20:** Triple-redundant ADB input injection (Local Wi-Fi, Tailscale, Router USB).

## 📲 Native App Installation Across Devices
1. **Mac Mini M4 Pro (L1):**
   - Native App Bundle: `/Users/aaron/Applications/Lauburu Remote.app`
   - Configured in standalone application window mode (`--app=http://localhost:4006 --user-data-dir=...`).
   - Custom macOS `.icns` icon generated directly from canonical Lauburu branding (`AppIcon.icns`).
2. **Google Pixel 10 Pro XL (L6):**
   - PWA Web App Manifest + Service Worker (`lauburu-remote-v2`).
   - Native Termux shortcut: `~/.shortcuts/lauburu_remote.sh` and `~/bin/lauburu-remote`.
   - 1-tap browser intent launch to `http://100.119.199.76:4006`.
3. **Samsung Galaxy S20 (L7):**
   - PWA Web App Manifest + Service Worker with 192px/512px maskable icons.
   - 1-tap Android home screen installation as WebAPK.
   - ADB intent launch directly to `http://192.168.8.155:4006`.

## 🛡️ Rule 1 & Rule 5: Empirical Tri-Proof E2E Verification
Automated test suite (`01_apps/screen_lens/tests/test_remote_hid_e2e.py`) passed 10/10 tests with **Exit Code 0**:
1. **Proof 1 (Actuation):**
   - Physical CoreGraphics pointer moved `(+19.4, +19.6)` delta on Mac Mini display.
   - Left click, right click, and 2-finger scroll events dispatched without error.
   - Real terminal commands executed on Mac Mini (`Darwin aaron`), GL.iNet Router (`GL-MT3600BE`), Pixel 10 Pro XL (`Pixel 10 Pro XL`), and Samsung S20 (`SM-G986B`).
2. **Proof 2 (Line-by-Line & Hashes):**
   - `icon-192.png`: 9,299 bytes | SHA256: `70e28fa17c2a56fcc8c2b5cb884b25f54924ea15c0e189872fb79d0f4d3826ba`
   - `icon-512.png`: 36,920 bytes | SHA256: `aad58ba33bb328e202573fb9e9f9024f0cbf2d8e404be124119fc9b4e72338c0`
   - `Lauburu Remote.app/Contents/Resources/AppIcon.icns`: 223,157 bytes | SHA256: `143f6cb1fe211915951a89c9d520f9d95f00e95cb4d2cf99a896d8e874ce2041`
3. **Proof 3 (Visual):**
   - Live SVG screen capture generated and saved to `remote_screen_preview.svg` (1,479 bytes).
   - Samsung Galaxy S20 screen capture saved to `s20_remote_screen.png` (2,530,267 bytes).

## ⚙️ Daemon Management
- **Launchd Daemon:** `~/Library/LaunchAgents/ai.lauburu.mesh_remote_hid.plist` (Auto-restarts on boot).
- **Service Script:** `01_apps/screen_lens/src/mesh_universal_remote_hid_server.py`.
