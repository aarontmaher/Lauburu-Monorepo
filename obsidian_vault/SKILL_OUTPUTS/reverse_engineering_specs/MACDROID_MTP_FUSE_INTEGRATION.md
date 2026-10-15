---
title: "MacDroid Reverse Engineering & Lens MTP/FUSE Integration"
tags: [macdroid, adb, mtp, fuse, screen_lens, reverse_engineering]
date: "2026-09-15"
---

# 🕵️‍♂️ MacDroid Protocol Analysis & Screen Lens Integration

## 1. MacDroid Architecture Reconnaissance
MacDroid bridges macOS and Android storage using two primary protocols:
1. **MTP (Media Transfer Protocol) Mode:** Utilizes standard USB-IF MTP. macOS lacks native MTP support (unlike Windows). MacDroid uses a custom `macFUSE` (OSXFUSE) kext/daemon to translate MTP bulk endpoints into a virtual POSIX filesystem.
2. **ADB (Android Debug Bridge) Mode:** Bypasses MTP instability by running a daemon that converts `adb push`/`adb pull` and `adb shell ls` commands into FUSE filesystem calls, mounting the Android device at `/Volumes/MacDroid`.

## 2. Weaknesses of KDE Connect for Storage
While `kdeconnect-cli` handles clipboard and notifications beautifully, its file transfer relies on TCP over LAN. If the Wi-Fi drops or the Pixel 10 sleeps, file transfers stall. It does not provide a POSIX-compliant mount for SeaweedFS to index.

## 3. Sovereign Clean-Room Lens Integration Strategy (Rule 4)
Instead of relying on proprietary software like MacDroid, Screen Lens will integrate **ADB-based FUSE mounting** natively into its Omni-Bridge.

### Proposed Architecture (Lens `adbfs` Daemon)
*   **Technology:** `macfuse` + Python `llfuse` / `fusepy` bound to the local ADB server (which Lens already uses for OpenClaw).
*   **Mount Point:** Lens will automatically mount the Pixel 10 (L6) and Samsung S20 (L7) at:
    `/Volumes/Lauburu-Monorepo/04_data_and_memory/android_mounts/`
*   **SeaweedFS Ingestion:** Once mounted as a local POSIX folder, Lens will point SeaweedFS `weed filer` at the mount point, instantly bridging Android storage into the 7-layer mesh DFS.
*   **Execution:** We will utilize the open-source `adbfs-rootless` C++ codebase, cross-compiled for Apple Silicon, wrapped by `lens_storage_orchestrator.py`.

## 4. Integration Blueprint
1. Screen Lens polls `adb devices -l` (as per the mesh matrix).
2. If `100.73.38.87:8022` (Pixel 10) is online, trigger `adbfs`.
3. Map the Pixel's `/sdcard/DCIM` and `/sdcard/Download` directly into the Mac's Finder.
