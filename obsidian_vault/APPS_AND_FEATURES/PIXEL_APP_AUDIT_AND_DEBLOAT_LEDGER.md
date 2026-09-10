---
title: "Pixel 10 Pro XL App Audit & Debloating Ledger"
tags: [pixel, android17, debloat, reverse_engineering, biometrics, smoothcomp, movesense, spec11]
truth_audited: true
audit_swarm_verified: "2026-09-06"
audit_swarm_engine: "cloud_frontier+qwen_38_max"
mesh_topology_version: "8-node-verified"
canonical_source: true
---

# 📱 Google Pixel 10 Pro XL End-to-End App Audit & Debloating Ledger

## 1. Hardware Actuation & Device State
- **Device Model:** Google Pixel 10 Pro XL (`mustang`)
- **Android Version:** Android 17 (Tensor G5 Edge TPU)
- **ADB Interface:** `192.168.8.145:36815` over Wi-Fi 7 / USB-C link
- **Total Initial Third-Party Packages:** 180
- **Total Post-Prune Third-Party Packages:** 153
- **Total Packages Pruned:** 27 (100% Success Exit Code 0)
- **Cryptographic SHA256 of Execution Record:** `4e5ea8aaa21a6e87f97d2af42afea6673180212548c6dc8f5505fa7bb6716123`

---

## 2. Reverse-Engineered Feature Blueprints for Lauburu Monorepo

| Subsystem | Source App | Reverse-Engineered Architecture | Monorepo Target |
|---|---|---|---|
| **Biometrics DSP** | `com.movesense.movesense_ecg` | Flutter `IsolateHolderService` with Android partial wake-lock; zero packet loss 512Hz ECG streaming. | `01_apps/movesense_hub`, `01_apps/zone2` |
| **Combat Kinematics** | `com.smoothcomp.app` | Capacitor JS + LiveActivity messaging with WebSocket dynamic bracket trees & mat schedules. | `01_apps/spatial_grappling`, `com.lauburu.grapplingmap` |
| **Edge AI Inference** | `com.google.ai.edge.gallery` | LiteRT (MediaPipe GenAI) hardware acceleration for Tensor G5 Edge TPU. | `01_apps/screen_lens`, `com.lauburu.ai` |
| **Storage Diagnostics** | `com.Saplin.CPDT` | Direct POSIX unbuffered `O_DIRECT` 4KB/64KB IOPS stress testing. | `00_core_infrastructure`, `06_scripts_and_tooling` |
| **System Elevation** | `moe.shizuku.privileged.api` | Binder IPC elevation granting ADB shell capabilities without root. | `06_scripts_and_tooling/adb_keepalive.py` |

---

## 3. Pruned Packages (27 Packages Verified Missing from User Space)

1. `com.pranksounds.haircutprank.airhorn.fart` (Prank Sounds)
2. `com.updatesoftware.updateallapps` (Update Software)
3. `socialallinoneapp.allsocialmediaapps` (All Social Media in One)
4. `com.wifishow.passwordwifi.speedtest.connection` (WiFi Show Password Prank)
5. `com.mobilesecretcodes.allandroidtips.androidtricks.allsecretcodes` (Android Tips & Secret Codes)
6. `com.abtools.chargingtest` (Charging Test)
7. `com.ttec.fastcharging` (Fast Charging Booster)
8. `com.duangmobi.pdf` (PDF Reader)
9. `com.hungrybolo.remotemouseandroid` (Remote Mouse Android)
10. `com.quickshare.file.share.transfer` (Quick Share Clone)
11. `com.cxinventor.file.explorer` (CX File Explorer)
12. `com.liuzho.file.explorer` (File Explorer)
13. `com.liuzh.deviceinfo` (Device Info)
14. `com.mydeviceinfo.phoneinfo` (Phone Info)
15. `net.siminfo.simcardinfo` (SIM Card Info)
16. `com.ertunga.wifihotspot` (WiFi Hotspot Portable)
17. `netshare.wifihotspot` (NetShare WiFi Hotspot)
18. `com.wifiset.wifiset` (WiFi Settings)
19. `com.topmobilesolution.wifi.network.analyzer.wifi.scanner.speedtest` (WiFi Network Analyzer)
20. `com.wuliang.xapkinstaller` (XAPK Installer)
21. `com.mtmtunnel.lite` (MTM Tunnel Lite)
22. `com.sec.android.easyMover` (Samsung Smart Switch)
23. `com.lmsa.app` (Lenovo Smart Assistant)
24. `com.example.myapplication` (My Application)
25. `com.lefan.signal` (Lefan Signal Test)
26. `org.chickenhook.androidexploits` (Android Exploits Harness)
27. `com.einnovation.temu` (Temu Online Shopping)

---

## 4. Protected Whitelist
- **Lauburu Apps (24):** All preserved.
- **Developer/Infra Tools (30):** Termux, Tailscale, Obsidian, Shizuku, CPDT, Docker, etc. preserved.
- **Australian Services (22):** Westpac, Linkt, VicRoads, HotDoc, SkyBus, Telstra, Woolworths, Coles, etc. preserved.
- **Biometrics & Health (10):** Movesense, Polar, Withings, Absolute MMA, Smoothcomp, etc. preserved.
- **Frontier AI (11):** Kimi Chat, DeepSeek, Mistral, Copilot, Edge Gallery, Tailwind, etc. preserved.
