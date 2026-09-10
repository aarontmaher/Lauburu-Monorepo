---
title: "Omni Terminal & Sovereign Console: Cross-Device App Installation Manifest"
tags: [omniterminal, terminal_app, pwa, mesh_deployment, zero_mock]
updated: "2026-09-05T19:18:45+10:00"
---

# ⚡ Omni Terminal: Cross-Device App Installation Manifest

The **Omni Terminal & Sovereign Console** has been deployed as a standalone, installable application across all physical layers of the 7-layer Lauburu Mesh Ecosystem.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│             OMNITERMINAL CROSS-DEVICE INSTALLATION MATRIX                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. UNIVERSAL PWA (All Browsers, Mobile & Desktop)                           │
│    • Access URL: http://100.119.199.76:4000/terminal/                       │
│    • Local IP:   http://192.168.8.230:4000/terminal/                        │
│    • Features:   PWA Manifest, Service Worker, offline cache, mobile touch  │
│                  key bar (Esc, Tab, Ctrl, Alt, Arrows), xterm.js PTY bridge.│
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. MACOS NATIVE APP BUNDLE (L1 Mac Mini Host, L2 Mac Pro, L5 Mac Air)       │
│    • Paths:      /Applications/Omniterminal.app                             │
│                  ~/Applications/Omniterminal.app                            │
│                  ~/.local/bin/omniterminal & sovereign_console              │
│    • Launcher:   Native macOS application bundle with high-res AppIcon.icns │
│                  and AppleScript TTY session initializer.                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. ANDROID APPLICATION (L6 Pixel 10 Pro XL & L7 Samsung S20+)               │
│    • Termux CLI: ~/bin/omniterminal                                         │
│    • Home Icon:  ~/.shortcuts/omniterminal (Termux:Widget one-tap launcher) │
│    • Web App:    Android Chrome PWA "Add to Home screen" active intent.     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. ROUTER GATEWAY BRIDGE (GW GL.iNet GL-MT3600BE)                           │
│    • Path:       /usr/sbin/omniterminal                                     │
│    • Access:     Direct hardware SSH bridge to Host Mac Mini and mesh state.│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📱 How to Install on Any Connected Device

1. **Android (Pixel 10 Pro XL, Samsung S20+)**:
   - Open Chrome to `http://100.119.199.76:4000/terminal/`.
   - Tap the **"INSTALL APP"** button or select browser menu $\to$ **"Add to Home screen"** / **"Install app"**.
   - Omni Terminal appears on your home screen with its cyan neon icon and opens full-screen without browser chrome.
   - Alternatively, open the **Termux:Widget** on your home screen and tap `omniterminal`.

2. **macOS (Mac Mini, MacBook Pro, MacBook Air)**:
   - Double-click `/Applications/Omniterminal.app` or search Spotlight for `Omni Terminal`.
   - Run `omniterminal` or `sovereign_console` from any terminal.

3. **iOS (iPhone)**:
   - Open Safari to `http://100.119.199.76:4000/terminal/`.
   - Tap **Share** $\to$ **Add to Home Screen**.

4. **Linux & Gateway (Head Node, Tablet, Router)**:
   - Run `omniterminal` from terminal shell.

---

## 🛡️ Zero-Mock Empirical Verification

- **PWA Static Assets**: `index.html`, `manifest.json`, `sw.js`, `xterm.min.js`, `icon-192.png`, `icon-512.png` all returned `HTTP 200 OK`.
- **PTY WebSocket Bridge**: Bidirectional communication verified over `/ws/terminal` with `OMNITERMINAL_PTY_VERIFIED` echo received.
- **Android Actuation**: Termux launcher scripts deployed and verified via SSH to `100.84.40.95:8022` and `100.73.38.87:8022`. Intent launched on display.
- **macOS Bundle**: Valid bundle structure in `/Applications/Omniterminal.app` with `Info.plist` and `AppIcon.icns`.

---
[[Index]] | [[CANONICAL_PROJECT_OVERVIEW]] | [[OMNITERMINAL_CANONICAL_SPEC]]
