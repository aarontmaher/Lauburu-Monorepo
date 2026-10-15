---
title: "GL.iNet Router Gateway Health & Hardware Hub Overload Audit"
tags: [lauburu, glinet, router, hardware_health, coil_whine, overcurrent, zero_mock]
date: 2026-09-19
status: "ONLINE_HEALTHY"
---

# ⚡ GL.iNet Gateway Router Health & Hub Hardware Audit

## 📋 Incident & Telemetry Summary
- **Timestamp:** `2026-09-19 01:34:21 UTC`
- **Router Model:** `GL.iNet GL-BE14000 (GL-MT3600BE / MediaTek Wi-Fi 7)`
- **Router LAN IP:** `192.168.8.1` (10GbE LAN port `eth2` -> Mac Mini `en0`)
- **Tailscale IP:** `100.103.212.34` (`gl-be14000-1`)
- **Current Router State:** `ONLINE`

---

## ⚠️ 1. Hardware Forensic Analysis: Why a Powered Hub Makes Noise & Causes Resets

Even when an external AC/DC power adapter is connected to the USB hub, plugging it into the GL.iNet router can produce loud acoustic noise (high-pitched coil whine, buzzing, or clicking) and trigger router brownouts. Here is the exact physical and electrical breakdown:

### 1. Reverse VBUS Back-Powering (Host vs Hub 5V Rail Collision)
- **The Physical Flaw:** USB 2.0/3.0 specification (**Section 7.2.1**) strictly dictates that self-powered hubs must NEVER back-feed voltage onto the upstream host VBUS pin. However, many consumer powered hubs omit the reverse-current blocking diode or high-side P-channel MOSFET switch.
- **The Collision:** The hub's external power supply delivers ~5.1V to 5.3V (engineered slightly high to offset cable voltage drop). Meanwhile, the GL.iNet router's onboard 5V DC-DC buck converter is actively generating 5.0V.
- **Why It Makes Noise (Router Coil Whine):** The router's synchronous buck regulator is designed to *source* current, not *sink* it. When 5.2V back-feeds into its output, the regulator's PWM feedback loop enters erratic burst/pulse-skipping mode. The magnetic core of the router's power inductor vibrates mechanically due to magnetostriction, emitting audible acoustic squeal (2 kHz – 16 kHz).
- **Why It Crashes the Router:** The reverse voltage raises the router's internal rail above the PMIC's over-voltage protection (OVP) latch threshold, triggering an emergency shutdown/reboot of the MediaTek MT7988A SoC.

### 2. Extreme Dual-Phone Current Overload (Hub Inductor Core Saturation)
- **Live Connected Peripherals (`/sys/bus/usb/devices`):**
  1. `3-1.1.3`: **Apple iPhone** (`05ac:12a8`) — battery charging draw: 1.0A – 2.0A
  2. `4-1.2`: **Samsung Galaxy S20+** (`04e8:6864`) — battery charging draw: 1.0A – 1.8A
  3. `4-1.1`: **Realtek RTL8153 Gigabit LAN** (`0bda:8153`) — 288 mA
  4. `3-1.2`: **USB Type-C Billboard Device** (`057e:0000`) — 100 mA
  5. `1-1`: **TP-Link UB500 Bluetooth Dongle** (`2357:0604`) — 500 mA
  6. **3 Cascaded Hub ICs** (`1a40:0801`, `05e3:0610`, `05e3:0626`) — ~300 mA
- **Total Load:** Charging two modern smartphones concurrently while powering an RTL8153 and multiple hubs pulls **3.5A to 4.5A (>18W to 22.5W)**.
- **Failure Mode:** Most powered hubs ship with an undersized **5V/2A (10W)** adapter or an internal step-down buck converter rated for 3A peak. When overloaded by 150–200%, the hub's internal ferrite inductor enters **magnetic saturation**. Once saturated, core permeability drops, causing massive current spikes and loud, vibrating coil whine in the hub's casing or power brick.

### 3. Switched-Mode Ground Loops & High-Frequency Noise
- The router's 12V supply and the hub's AC adapter operate on separate, unsynchronized high-frequency switching oscillators (often 65 kHz – 200 kHz).
- Interconnecting their ground planes via the USB cable shield circulates common-mode leakage currents, exciting acoustic resonances in ceramic surface-mount capacitors (piezoelectric whining).

---

## 🛠️ 2. Rapid Diagnostics & 100% Safe Fixes

1. **The 3-Second "Router Power Plug" Back-Feed Test:**
   - Unplug the router's 12V DC power barrel jack while leaving the powered hub connected.
   - If any router LEDs remain lit or dimly glowing, the hub is **back-powering the router** (confirming VBUS back-feeding).
2. **The VBUS Tape Mod / Data Blocker (Instant Fix):**
   - Place a tiny piece of electrical tape over **Pin 1 (5V VBUS)** on the USB-A plug connecting the hub to the router (the far right outer pin looking into the plug).
   - This keeps Data+ (Pin 2), Data- (Pin 3), and Ground (Pin 4) connected so all devices function normally, while 100% isolating the router's 5V rail from back-feeding and coil whine.
3. **Phone Charging Load Shedding:**
   - Disconnect the iPhone and Samsung S20+ charging cables from the data hub and connect them to dedicated wall chargers. Powered data hubs should primarily host low-power data devices (NIC, Bluetooth dongles, MCU serial adapters).
3. **Observe Front Panel LEDs:**
   - Solid / flashing light indicates OpenWrt boot cycle (~60 seconds).
4. **Automated Re-Connection:**
   - The Mac Mini Ethernet interface (`en0`) is statically configured at `192.168.8.230/24` with gateway `192.168.8.1`.
   - As soon as OpenWrt finishes booting, `router_recovery_sentinel.py` will automatically detect the gateway, verify health, and restore default routing.

---

## 📊 3. Live Hardware Diagnostics

### Probe Results
```json
{
  "is_online": true,
  "lan_ip": "192.168.8.1",
  "lan_icmp": true,
  "lan_http_80": true,
  "lan_ssh_22": true,
  "ts_ip": "100.103.212.34",
  "ts_icmp": true,
  "ts_ssh_22": true,
  "timestamp": "2026-09-19T01:34:20.985761+00:00"
}
```

### Remote OpenWrt Telemetry
- **Reachable via SSH:** `True`
- **Uptime:** `11:33:24 up 24 min,  load average: 2.51, 3.05, 2.93`
- **Memory:**
```text
total        used        free      shared  buff/cache   available
Mem:        2033996      709776      819784       71904      504436     1151816
Swap:       2097148           0     2097148
```
- **USB & Kernel dmesg:**
```text
[ 1343.199100] TXPowerCons=0
[ 1343.199118]     Priority = 255, TxpowerDataRate = 0, idletime = 0, AvgDataRateParam = 0, APcount = 0
[ 1343.199122]     Priority = 255, TxpowerDataRate = 0, idletime = 0, AvgDataRateParam = 0, APcount = 0
[ 1343.199126]     Priority = 255, TxpowerDataRate = 0, idletime = 0, AvgDataRateParam = 0, APcount = 0
[ 1343.199130]     Priority = 255, TxpowerDataRate = 0, idletime = 0, AvgDataRateParam = 0, APcount = 0
[ 1343.199133]     Priority = 255, TxpowerDataRate = 0, idletime = 0, AvgDataRateParam = 0, APcount = 0
[ 1343.199136]     Priority = 255, TxpowerDataRate = 0, idletime = 0, AvgDataRateParam = 0, APcount = 0
[ 1343.199139]     Priority = 255, TxpowerDataRate = 0, idletime = 0, AvgDataRateParam = 0, APcount = 0
[ 1343.199143]     Priority = 255, TxpowerDataRate = 0, idletime = 0, AvgDataRateParam = 0, APcount = 0
[ 1343.199146]     Priority = 255, TxpowerDataRate = 0, idletime = 0, AvgDataRateParam = 0, APcount = 0
[ 1343.199149]     Priority = 255, TxpowerDataRate = 0, idletime = 0, AvgDataRateParam = 0, APcount = 0
[ 1343.199152]     Priority = 255, TxpowerDataRate = 0, idletime = 0, AvgDataRateParam = 0, APcount = 0
[ 1343.208438] TXPowerCons=0
[ 1343.208456]     Priority = 255, TxpowerDataRate = 0, idletime = 0, AvgDataRateParam = 0, APcount = 0
[ 1343.208461]     Priority = 255, TxpowerDataRate = 0, idletime = 0, AvgDataRateParam = 0, APcount = 0
[ 1343.208465]     Priority = 255, TxpowerDataRate = 0, idletime = 0, AvgDataRateParam = 0, APcount = 0
[ 1343.208468]     Priority = 255, TxpowerDataRate = 0, idletime = 0, AvgDataRateParam = 0, APcount = 0
[ 1343.208472]     Priority = 255, TxpowerDataRate = 0, idletime = 0, AvgDataRateParam = 0, APcount = 0
[ 1343.208475]     Priority = 255, TxpowerDataRate = 0, idletime = 0, AvgDataRateParam = 0, APcount = 0
[ 1343.208479]     Priority = 255, TxpowerDataRate = 0, idletime = 0, AvgDataRateParam = 0, APcount = 0
[ 1343.208482]     Priority = 255, TxpowerDataRate = 0, idletime = 0, AvgDataRateParam = 0, APcount = 0
[ 1343.208485]     Priority = 255, TxpowerDataRate = 0, idletime = 0, AvgDataRateParam = 0, APcount = 0
[ 1343.208488]     Priority = 255, TxpowerDataRate = 0, idletime = 0, AvgDataRateParam = 0, APcount = 0
[ 1343.208492]     Priority = 255, TxpowerDataRate = 0, idletime = 0, AvgDataRateParam = 0, APcount = 0
[ 1347.359780] 7990@WARN.CFG,BN2,cfg80211_drv_vndr_get_static_info() 4088: failed - [ERROR] Interface is down .
[ 1347.655351] 7990@WARN.CFG,BN1,cfg80211_drv_vndr_get_static_info() 4088: failed - [ERROR] Interface is down .
[ 1347.938348] 7990@WARN.CFG,BN0,cfg80211_drv_vndr_get_static_info() 4088: failed - [ERROR] Interface is down .
[ 1348.107537] 7990@NOTICE.CFG80211,BN2,cfg80211_drv_vndr_get_runtime_info() 3894: failed - [ERROR] Interface is down .
[ 1348.148287] 7990@NOTICE.CFG80211,BN1,cfg80211_drv_vndr_get_runtime_info() 3894: failed - [ERROR] Interface is down .
[ 1348.188881] 7990@NOTICE.CFG80211,BN0,cfg80211_drv_vndr_get_runtime_info() 3894: failed - [ERROR] Interface is down .
```

---

## 🔗 Wikilinks
- [[Index]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[APPS_AND_FEATURES/ROUTER_FULL_NETWORK_STORAGE_SPEC]]
- [[APPS_AND_FEATURES/PORT_4007_CABLE_AND_MESH_ANALYZER_LIVE_AUDIT]]
