---
title: 'SeaweedFS 5-Node Distributed Storage Mesh Index'
tags: [seaweedfs, storage, mesh, screen_lens, tri_vault]
updated_at: '2026-09-19T06:48:19.723510+00:00'
---

# 🌐 SeaweedFS 5-Node Distributed Storage Mesh Index

Autonomous storage inventory compiled by `/screen-lens-sovereign` under **Rule 1 (Zero-Mock Truth)** and **Rule 2 (Tri-Vault Storage)**.

## 📊 Storage Pool Reality: Logical Slots vs. Physical Hardware

| Metric | Logical Allocation (SeaweedFS Slots) | Authentic Physical Hardware (SSD/Flash) |
| :--- | :--- | :--- |
| **Total Capacity** | **6.33 TB** (6,330 GB) | **2.13 TB** (2,132 GB) |
| **Free Space** | **6.12 TB** (6,120 GB) | **608.0 GB** |
| **Physical Used Space** | -- | **1,524.0 GB** |
| **Active Nodes** | **6 Nodes Online** | **100% Verified Zero-Mock** |

> [!NOTE]
> **Why 6.3 TB was reported:** SeaweedFS provisions storage in logical volume files sized at 30 GB each (`Version: 30GB 4.44`). The 6 registered nodes were assigned volume slots. The physical SSD pool actually contains **2.13 TB** total raw drive capacity with **608 GB** of unallocated physical headroom across the 6 devices.

## 🖥️ 6-Node Hard Drive Merger Topology

| Layer | Node | Endpoint | Mount Directory | Physical Total | Physical Free | Max Slots |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GW** | GL-BE14000 Router | `192.168.8.1:8085` | `/overlay/seaweedfs` | 57 GB | **53 GB** (92%) | 30 |
| **L1** | Mac Mini M4 Pro Host | `192.168.8.230:8090` | `/Users/aaron/.local/var/seaweedfs/mesh_pool` | 460 GB | **80 GB** (18%) | 60 |
| **L2** | MacBook Pro Intel | `192.168.8.128:8095` | `/Users/aaronmaher/.local/var/seaweedfs` | 465 GB | **94 GB** (20%) | 60 |
| **L3** | Linux Laptop (AMD Ryzen 5700U) | `192.168.8.225:8091` | `/mnt/seaweed_data/volume` | 467 GB | **88 GB** (19%) | 2 |
| **L5** | MacBook Pro (Node L2) | `192.168.8.215:8096` | `/Volumes/.local/var/seaweedfs` | 228 GB | **40 GB** (18%) | 1 |
| **L8** | Lauburu Ubuntu (Intel i7) | `192.168.8.238:8092` | `/home/linuxmini/seaweed_volume` | 455 GB | **253 GB** (56%) | 60 |

## 📁 Unified Directory Tree & Screen Lens Classification Map

Screen Lens Sovereign organizes files automatically across the following schema:

```
/mnt/seaweedfs/seaweed_network_projects/
├── README.md                          (Cluster topology & access credentials)
├── shared_workspace/                  (Collaborative multi-device scratch space)
└── device_sync/                       (Individual device dropboxes)
    ├── mac_mini/                      (L1 Apple M4 Pro Host)
    ├── macbook_pro/                   (L2 Intel MacBook Pro)
    ├── macbook_air/                   (L5 Apple M4 MacBook Air)
    ├── lauburu_laptop/                (L8 Mobile Linux Compute)
    ├── pixel_10_pro_xl/               (L6 Google Tensor G5 Edge)
    ├── samsung_s20/                   (L7 Samsung Exynos Testbed)
    └── iphone_16_pro/                 (L9 Apple A18 Pro iOS Node)
```

## 🔗 Network Access Protocols
- **Samba SMB Share:** `smb://192.168.8.1/seaweed_network` (LAN) or `smb://100.103.212.34/seaweed_network` (Tailscale)
- **Credentials:** User `root` | Password `goldfighting1`
- **HTTP Filer REST API:** `http://192.168.8.1:8888/seaweed_network_projects/`
- **Filer Master Status:** `http://192.168.8.1:9333/dir/status`

---

## 🧠 8-Device Live Full-Network RAM Pool

Monitored in real-time via `/usr/bin/mesh-top` on the GL-BE14000 gateway (accessible via Layer 0 Bluetooth Serial `/dev/rfcomm0` and SSH).

| Layer | Device | Network Link | Total RAM | Used RAM | Utilization | Primary Workload |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GW** | GL-BE14000 Router | `192.168.8.1` | 1,986 MB | 947 MB | 47% | SeaweedFS Master, Samba SMB, Layer 0 Monitor |
| **L1** | Mac Mini M4 Pro | `192.168.8.230` | 24,576 MB | 20,385 MB | 82% | Memory Governor, Master Orchestrator, TUI |
| **L2** | MacBook Pro (Intel i7) | `192.168.8.128` | 16,384 MB | 9,080 MB | 55% | RPC Sharding Worker, SeaweedFS Volume |
| **L3** | Linux Laptop (Ryzen 5700U) | `192.168.8.225` | 15,329 MB | 2,663 MB | 17% | Docker Hub, Distributed Compute, SeaweedFS Volume |
| **L5** | MacBook Air (M4) | `192.168.8.215` | 16,384 MB | 13,071 MB | 79% | Metal Performance Shaders, LoRA Worker |
| **L6** | Pixel 10 Pro XL | `100.73.38.87:8022` | 15,575 MB | 11,439 MB | 73% | Google Tensor G5, Edge TPU, 8K Vision |
| **L7** | Samsung Galaxy S20+ | Direct USB ADB | 10,900 MB | 5,227 MB | 47% | Dedicated Automated UI Tester |
| **L8** | Lauburu Ubuntu (Intel i7) | `192.168.8.238` | 31,941 MB | 8,103 MB | 25% | Linux Mini Compute Node, SeaweedFS Volume |
| **TOTAL** | **Full 8-Device Mesh** | **7-Layer Grid** | **133,075 MB (~133.1 GB)** | **70,915 MB (~70.9 GB)** | **53% Pooled** | **Pooled Zero-Mock Memory Grid** |

