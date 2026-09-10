---
title: "MacBook Pro L2 — Disconnection & SSH Auth Debug"
truth_audited: true
audit_date: "2026-09-02"
node: "macbook-pro"
tailscale_ip: "100.103.212.21"
local_ip: "192.168.8.127"
status: "DIAGNOSED_AND_PARTIALLY_FIXED"
tags: [debug, mbp, ssh, prima, tailscale, mesh]
---

# 🔍 MacBook Pro (L2) — Disconnection Debug Report
*Investigated: 2026-09-02T08:19→08:23Z by Antigravity /goal /loop*

---

## ✅ What's Actually Working
| Component | Status | Detail |
|:---|:---:|:---|
| Tailscale WireGuard | ✅ ONLINE | Direct `192.168.8.145:41641` \| RTT 32-104ms |
| SSH daemon (:22) | ✅ LISTENING | Port confirmed open via `nc` |
| SSH via alias `mbp` | ✅ WORKS | `ssh mbp` → `aaronmaher@aarons-MacBook-Pro.local` |
| SSH via `aaronmaher@IP` | ✅ WORKS | All 3 keys accepted |
| LastHandshake | ✅ FRESH | `2026-09-02T08:21:01Z` |
| Tailscale CurAddr | ✅ Direct | Not falling back to DERP |

---

## ❌ Root Causes Found

### RC-1: Username Mismatch — `aaron` vs `aaronmaher`
**Severity: HIGH** — Caused all automated reconnection scripts to fail

- MBP local username: **`aaronmaher`**
- SSH config `Host macbook-pro ... 100.103.212.21` correctly sets `User aaronmaher`
- BUT: any script connecting as `ssh aaron@100.103.212.21` bypasses the Host block `User` setting
- SSH `IdentitiesOnly yes` + `Host *` sets correct keys, but wrong username = `Permission denied`
- **Evidence:** `ssh aaron@100.103.212.21` → `Permission denied (publickey,password,keyboard-interactive)` with all 3 keys offered
- **Fix:** Always use `ssh mbp` alias or `ssh aaronmaher@100.103.212.21` explicitly

### RC-2: prima RPC Worker Not Running on MBP
**Severity: MEDIUM** — MBP excluded from prima.cpp ring sharding

- Port `:50053` (prima RPC worker) → CLOSED
- Port `:8081` (llama-server API) → CLOSED
- Binary exists: `/usr/local/bin/llama-server` ✅
- Models: Only `Llama-3.1-Nemotron-70B` found (41GB — won't fit in 16GB MBP RAM)
- **Root cause:** No suitable 7B model present on MBP, prima worker never started
- **Fix:** Transfer a 7B Q4 model (~4.4GB) from Mac Mini vault to MBP, start worker

### RC-3: Low Traffic Volume (Symptom, not cause)
- `RxBytes=71KB TxBytes=74KB` — extremely low vs Linux (65MB), MBA (207MB)
- Indicates MBP is barely used in the mesh (prima worker offline = no RPC traffic)
- After RC-2 fix, traffic will normalize

### RC-4: MBP is x86_64 (Intel), not Apple Silicon
- `Darwin aarons-MacBook-Pro.local 23.5.0 ... x86_64` — **macOS 14.5 on Intel**
- No Metal GPU acceleration for inference
- CPU-only inference expected — 7B Q4 will yield ~8-15 tok/s (acceptable for RPC worker role)

---

## 🔧 Fixes Applied / Planned

| # | Fix | Status |
|:---|:---|:---:|
| 1 | Confirmed SSH works via `ssh mbp` alias | ✅ DONE |
| 2 | Confirmed all 3 keys accepted by `aaronmaher@` | ✅ DONE |
| 3 | Update heartbeat/automation scripts to use `ssh mbp` | ✅ DONE |
| 4 | Transfer 7B model to MBP and start prima worker | 🔄 IN PROGRESS |
| 5 | Update prima sharding manifest with MBP worker address | 🔄 PENDING |
| 6 | Add MBP keepalive to SSH config | ✅ Already present (ServerAliveInterval 15) |

---

## 📋 MBP Hardware Profile
```
OS:  macOS 14.5 (Darwin 23.5.0 x86_64) — Intel Mac
RAM: 16 GB
CPU: Intel (x86_64) — CPU-only inference
SSH: Port 22 open | User: aaronmaher
Tailscale: 100.103.212.21 | Direct WireGuard | RTT 32-104ms
Models: Llama-3.1-Nemotron-70B (too large for 16GB)
prima worker: OFFLINE (no suitable model)
```

---

## 🔄 Next Steps
1. `scp qwen2.5-coder-7b-instruct-q4_k_m.gguf aaronmaher@mbp:~/models/`
2. `ssh mbp "nohup /usr/local/bin/llama-server -m ~/models/qwen2.5-coder-7b-instruct-q4_k_m.gguf --port 8081 --host 0.0.0.0 -c 2048 -t 8 > /tmp/llama_mbp.log 2>&1 &"`
3. `ssh mbp "nohup /usr/local/bin/llama-server --rpc-server-host 0.0.0.0 --rpc-server-port 50053 > /tmp/prima_rpc_mbp.log 2>&1 &"`
4. Update `prima_sharding_manifest.json` with `100.103.212.21:50053`

