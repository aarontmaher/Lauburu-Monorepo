---
title: "Lens CLI Hub — Unified Device Control Interface"
tags: [screen-lens, cli, android, glinet, shizuku, scrcpy, fdroid, magisk]
---

# 🔧 Lens CLI Hub — Unified Device Control Interface

`01_apps/screen_lens/src/lens_cli_hub.py`

## Quick Reference

```bash
PY=/Users/aaron/.local/bin/python3
HUB=$MONOREPO/01_apps/screen_lens/src/lens_cli_hub.py

# Router / LuCI / GL.iNet
$PY $HUB router status          # Full router health
$PY $HUB router wg              # WireGuard status (10 peers)
$PY $HUB router peers           # Peer table
$PY $HUB router check-routing  # Audit firewall/routing

# ADB (mesh-aware)
$PY $HUB adb s20 shell echo OK

# Android high-level
$PY $HUB android s20 info
$PY $HUB android s20 wake
$PY $HUB android pixel screenshot

# F-Droid (fdroidcl at ~/go/bin/fdroidcl)
$PY $HUB fdroid s20 update
$PY $HUB fdroid s20 install org.videolan.vlc

# Shizuku
$PY $HUB shizuku s20 status
$PY $HUB shizuku s20 rish "pm list packages | grep termux"

# Scrcpy GUI
$PY $HUB scrcpy s20             # Launch window
$PY $HUB scrcpy pixel           # Pixel window
$PY $HUB scrcpy-record s20 /tmp/s20_session.mp4

# Magisk/Sui evaluation
$PY $HUB magisk s20
$PY $HUB magisk pixel

# Full status
$PY $HUB status
```

## MCP Tools (24 total)
- Tool 19: `screen_lens_router_cli`
- Tool 20: `screen_lens_android_cli`
- Tool 21: `screen_lens_fdroid_cli`
- Tool 22: `screen_lens_shizuku_cli`
- Tool 23: `screen_lens_scrcpy_control`
- Tool 24: `screen_lens_magisk_sui_eval`

## Device Registry
| Key | Device | Primary IP | Shizuku | rish |
|-----|--------|-----------|---------|------|
| s20 | Samsung S20+ (L7) | 192.168.8.131:5555 | PID 3139 ✅ | UID=2000 ✅ |
| pixel | Pixel 10 Pro XL (L6) | 192.168.8.114:5555 | Intermittent | UID=2000 ✅ |

## R5 — SeaweedFS Storage Mesh (Verified 2026-09-20)
- Mount: `/Volumes/seaweed_network` via SMB `GL-BE14000._smb._tcp.local`
- Capacity: 58GB total / 45GB free ✅
- Write test: `lens_connectivity_test.txt` written ✅

## R6 — HA Persistence (Verified 2026-09-20)
- S20 boot script: `/data/data/com.termux/files/home/.termux/boot/lauburu_boot.sh` ✅
- Doze whitelist: com.android.shell, com.termux, moe.shizuku.privileged.api, com.tailscale.ipn ✅
- ADB keepalive: LaunchAgent `com.lauburu.android-dep-daemon` ✅
- Resurrection engine: `06_scripts_and_tooling/network/canonical_network_resurrection_engine.py` ✅
