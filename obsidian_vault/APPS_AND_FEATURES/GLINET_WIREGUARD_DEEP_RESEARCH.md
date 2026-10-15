# 🌐 GL.iNet Router WireGuard Architecture, Setup & Diagnostic Dossier

**Target Reference:** [GL.iNet WireGuard Client Guide (v4.x)](https://docs.gl-inet.com/router/en/4/interface_guide/wireguard_client/#set-up-wireguard-server-on-glinet-router)  
**Ecosystem Anchor:** Lauburu 7-Layer Physical Mesh (`GW_Router` GL-BE14000 @ `192.168.8.1`, WAN `100.90.9.130`)  
**Methodology:** Multimodal Visual Grounding (Screen Lens), OpenWrt 21.02/Linux 5.4 Kernel Invariant Audit, Official Documentation Deep Research.

---

## 🏛️ 1. Executive Summary & Core Distinction

The official GL.iNet documentation defines two reciprocal WireGuard roles across its router portfolio:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    WIREGUARD CLIENT vs. WIREGUARD SERVER                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. WIREGUARD SERVER (Inbound Gateway / Host)                                │
│    • Route: VPN -> WireGuard Server (https://192.168.8.1/#/wgserver)        │
│    • Function: Router listens on UDP:51820 (`wgserver`) with a static       │
│      public key. It issues profiles (IPs: 10.1.0.2/32 - 10.1.0.x/32) to     │
│      remote clients (Mac Mini, Pixel 10, iPhone, Linux Hub, etc.).          │
│    • Prerequisite: Requires a Public WAN IP or CGNAT Port Forwarding.       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. WIREGUARD CLIENT (Outbound Uplink / Tunnel Consumer)                     │
│    • Route: VPN -> WireGuard Client (https://192.168.8.1/#/vpn-client)       │
│    • Function: Router establishes an outbound tunnel (`wgclient1..5`) to an │
│      external WireGuard host (commercial VPN or remote home server). All LAN│
│      traffic is encapsulated and encrypted before reaching the WAN ISP.     │
│    • Prerequisite: Works behind any NAT/CGNAT/Firewall without public IP.   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 2. Deep Dive: Setting Up WireGuard Server on GL.iNet

According to the official guide (`#set-up-wireguard-server-on-glinet-router`):

### 2.1 The Two-Router / CGNAT Prerequisite
1. **Public IP Verification:**  
   The server requires that the router's WAN IP matches its internet-facing Public IP.
   * **The Reality on GL-BE14000:** The WAN IP is `100.90.9.130`. The `100.64.0.0/10` block is **RFC 6598 Carrier-Grade NAT (CGNAT)** assigned by the Australian NBN retail service provider.
   * **The Consequence:** Incoming UDP packets to port 51820 cannot reach the GL-BE14000 directly from the public internet unless:
     * A static public IP is requested from the ISP, or
     * An external VPS acts as a WireGuard bounce relay, or
     * Tailscale DERP / WireGuard Mesh overlay is used.

### 2.2 Server Step-by-Step Configuration
1. Navigate to **VPN** ➔ **WireGuard Server** in the Admin Panel.
2. Click **Generate Configuration**:
   * Generates server private key and listening port (`51820`).
   * Default Tunnel subnet: `10.0.0.1/24` (or `10.1.0.1/24` as configured in Lauburu to avoid 10.0.0.x upstream collisions).
3. **Profiles Creation:**
   * Under the **Profiles** tab, click **Add**.
   * Give the client a descriptive name (e.g., `MacBook Air`, `Pixel 10 Pro XL`).
   * Advanced settings allow specifying DNS servers, MTU (`1420`), and preshared keys (PSK).
4. **Configuration Export:**
   * Exports in 3 formats: **QR Code** (for mobile apps), **Plain Text**, and **`.conf` File**.
5. **Server Options & Route Rules:**
   * **Allow Remote Access to the LAN Subnet:** Must be toggled **ON** if clients need to reach LAN resources (`192.168.8.0/24`, SeaweedFS storage, local AI endpoints).
   * **IP Masquerading:** Enabled by default to rewrite client IPs to the router's tunnel address.

---

## ⚡ 3. Deep Dive: Setting Up WireGuard Client Manually

According to the official section `Set Up WireGuard Client Manually (for other providers)`:

### 3.1 Adding Configuration in the Web GUI
1. Go to **VPN** ➔ **WireGuard Client Profile** (`https://192.168.8.1/#/vpn-client`).
2. Click **Add Manually**.
3. Create a Group (e.g., `Lauburu_External_Mesh` or commercial provider name).
4. Choose between:
   * **Upload Configuration File:** Drag and drop a `.conf` or `.zip` file.
   * **Manually Add Configuration (Text Mode):** Paste raw WireGuard INI format.

### 3.2 Required Syntax Anatomy
The GL.iNet firmware parses the standard WireGuard structure:
```ini
[Interface]
Address = 10.1.0.2/24          # Mandatory: Client's assigned VPN IP
PrivateKey = <CLIENT_PRIVKEY>  # Mandatory: Client's 32-byte private key
DNS = 1.1.1.1, 8.8.8.8         # Recommended: Prevents ISP DNS leakage
MTU = 1420                     # Optional: Prevents fragmentation

[Peer]
PublicKey = <SERVER_PUBKEY>    # Mandatory: Remote server's public key
Endpoint = <IP_OR_DOMAIN>:51820 # Mandatory: Remote server address and port
AllowedIPs = 0.0.0.0/0, ::/0   # 0.0.0.0/0 for full tunnel; or subnets for split
PersistentKeepalive = 25       # Mandatory behind NAT/firewalls
```

---

## 🔬 4. Live Router Configuration State (`GL-BE14000`)

Audited directly via kernel probes and `/etc/config/`:

1. **Active WireGuard Server:**
   * Server IP: `10.1.0.1/24`
   * Listening Port: `51820` (UDP)
   * Public Key: `SBY2Wf6XZho60QQ43/k+08WnqxTslo/ZJCbHa3R6Sx8=`
   * Active Peers Connected: `Pixel 10 Pro XL` (10.1.0.2), `Mac Mini M4 Pro` (10.1.0.3), `Linux Workstation` (10.1.0.4), `MacBook Air` (10.1.0.5), `Samsung S20+` (10.1.0.6).
   * Kernel transfer active: ~100 KiB Tx/Rx across local interfaces.

2. **Loopback Client Interfaces (`wgclient1..5`):**
   * The router currently has 5 client interfaces configured pointing back to `192.168.8.1:51820` (created as test clients during automated device provisioning).

---

## 🛡️ 5. Architectural Recommendations for the Mesh

1. **When connecting the GL-BE14000 to an Outbound VPN:**  
   Always use a complete `.conf` file uploaded via the file picker rather than typing into Item Mode. This avoids missing `Address` or `Endpoint` fields.
2. **When connecting Edge Devices to the Home Mesh:**  
   Do not use the `vpn-client` tab. Instead, export the QR code or `.conf` directly from `https://192.168.8.1/#/wgserver` under the **Profiles** tab.
3. **Overcoming Carrier CGNAT (`100.90.9.130`):**  
   Since the NBN connection is behind CGNAT, external devices outside the home network should utilize **Tailscale** (`100.103.212.34`) or request a static IPv4 from the ISP to allow remote UDP handshake to port 51820.
