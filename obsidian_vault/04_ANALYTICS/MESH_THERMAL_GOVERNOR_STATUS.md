---
title: "Autonomous Mesh Thermal & Cooling Governor Status"
tags: [lauburu, mesh, thermals, cooling, hardware_governance, zero_mock]
updated: "2026-09-10T03:11:36.177483+00:00"
---

# 🌡️ 7-Layer Mesh Thermal & Cooling Governor Status

**Overall State:** `NOMINAL_OPTIMAL`  
**Offload Required:** `False` | **Recommended Compute Target:** `[[L3_Linux_Head_Node]]`

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 7-LAYER MESH THERMAL REGULATION MATRIX                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ • L1 Mac Mini Host:     NORMAL (Pressure L0, Limit 100%) │
│ • L2 MacBook Pro:       ONLINE (Limit 100%)                            │
│ • L3 Linux Head Node:   ONLINE (44.0°C, Cap: 75.0°C)                 │
│ • L5 MacBook Air:       OFFLINE (Limit 100%)                            │
│ • GW Beryl 7 Router:    53.3°C (Fan: 80 PWM / 31.4%, Cap: 68.0°C)   │
│ • L6 Pixel 10 Pro XL:   OFFLINE / ASLEEP (Doze) (0.0°C, Battery: 0%)                       │
│ • L7 Samsung S20+:      OFFLINE / ASLEEP (Doze) (BT: False, Temp: 0.0°C)       │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🎯 Autonomous Remediation Actions
1. **GL.iNet Router Fan Dynamic Modulation**:
   - Active PWM set to `80 / 255` (31.4%).
   - Target thermal equilibrium: $\le 65^\circ\text{C}$.
2. **Mac Mini Host Sanctuary**:
   - Thermal pressure: `NORMAL`. No CPU throttling detected.
3. **Linux Head Node**:
   - Temperature is nominal at `44.0°C` (Well below 75.0°C ceiling). Readily absorbs peripheral offloads.
4. **Android Device Duty-Cycle & Thermal Guard**:
   - Pixel 10 Pro XL: `0.0°C` (Ceiling: 42.0°C).
   - Samsung S20+: `OFFLINE / ASLEEP (Doze)` (Ceiling: 40.0°C).
   - Multi-transport Bluetooth L2 presence confirms device availability even during aggressive One UI Wi-Fi Doze modes.

---
[[Index]] | [[00_MASTER_INFRASTRUCTURE_TOPOLOGY]] | [[HARDWARE_THERMAL_BATTERY_CAPABILITY_AUDIT_2026]]
