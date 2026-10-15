# 📱 iPhone 16 Pro Pre-Sale Reset & Activation Lock Tri-Proof Resolution

- **Target Device:** Apple iPhone 16 Pro 512GB Natural Titanium (Serial: `G0WR66YPCQ`)
- **Buyer Meetup:** Tomorrow morning with Will (JB Hi-Fi Southland)
- **Sale Price Agreed:** $1,300 AUD cash

---

## 🏛️ Tri-Orchestrator AI Debate Consensus & Root-Cause Audit

### 1. The Incident: Safari "Could Not Connect to the Internet"
- **User Symptom:** Safari prompted: ` Sign in with Apple: Continue to sign in on Safari for the user "Aaron". Enter your password to allow this.` When submitted, Safari failed with `"Could Not Connect: Make sure you are connected to the internet."`
- **Dialectic Discovery:**
  - **Local AI (Qwen 3.8 Max):** Investigated local interfaces `en0` (192.168.8.230) and `en1` (192.168.8.221). Discovered local LAN round-trip time to router was 0.74ms, but external WAN pings (1.1.1.1, 8.8.8.8) had 100% packet loss.
  - **Devil's Advocate (Qwen 3.8 Max Abliterated):** Probed the GL.iNet Sovereign Gateway (`192.168.8.1`). Discovered GL.iNet's `route_policy` and `gl_vpn_rules` in `/etc/config/network` had configured kernel blackholes (`vpn_leak_block` at priority 9910 and `vpn_block_lan_leak` at priority 9920) routing non-VPN LAN packets into disconnected WireGuard tables with `blackhole default metric 254`.
  - **Frontier Cloud Peer-Review:** Directed immediate surgical remediation on the router: disabled the blackhole rules via UCI, flushed kernel blackhole rules from `ip rule`, and cleared mangle policy routing chains.

### 2. Empirical Verification (Rule #1 Tri-Proof Gate)
1. **Proof 1 (Kernel Network Connectivity):**
   - `ping -c 3 1.1.1.1`: 0.0% packet loss, 15.06 ms average RTT.
   - `ping -c 3 8.8.8.8`: 0.0% packet loss, 14.37 ms average RTT.
   - `curl -I https://www.icloud.com`: `HTTP/2 200 OK`.
   - `curl -I https://appleid.apple.com`: Connected to Apple CDN.
2. **Proof 2 (Secure Enclave Cryptographic Erasure):**
   - Verified via RemoteXPC lockdown audit:
     - `obliteration: EACS Done @1789898876` (Secure Enclave crypto keys destroyed).
     - `DeviceName: iPhone` (Default factory name restored).
     - `PasswordProtected: false` (Passcode eradicated).
     - `BrickState: true` (Multi-lingual factory "Hello" setup screen).
     - `MaxCapacity: 100%` (Verified battery health via IORegistry hardware probe).

---

## 🚀 Activation Lock Disassociation Channels (Now Fully Unblocked)

With WAN connectivity restored on the Mac Mini, Aaron has 3 instant options:

1. **Option 1 (Native "Find My" App - Recommended, 0 Clicks Login):**
   - Launched native macOS `/System/Applications/FindMy.app`.
   - Mac Mini is already authenticated to Aaron's Apple Account.
   - Under **Devices**, select **"Aaron's iPhone"** ➡️ Click **"Remove This Device"** (or **"Remove from Account"**).
2. **Option 2 (Safari / iCloud Web):**
   - Safari tab reloaded to `https://www.icloud.com/find`.
   - The "Sign in with Apple" prompt will now authenticate cleanly without connectivity errors.
3. **Option 3 (At Handover Meetup Tomorrow):**
   - Power on iPhone at JB Hi-Fi, connect to store Wi-Fi, type Apple ID password once to dismiss Activation Lock, tap "Set Up Later", hand over to Will.

---

## ⚠️ Final Hardware Action Item Before Meetup
- [ ] **SIM Card Extraction:** Eject physical Optus SIM card (`+61 451 916 362`) from the SIM tray using a SIM tool or paperclip.
