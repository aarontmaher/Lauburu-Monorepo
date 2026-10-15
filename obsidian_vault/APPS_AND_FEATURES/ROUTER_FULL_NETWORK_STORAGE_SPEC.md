---
title: "GL-BE14000 Sovereign Gateway Full Network Storage & SeaweedFS Architecture"
tags: [lauburu, router, network_storage, seaweedfs, samba, luci, fstab, openwrt]
---

# 🌐 GL-BE14000 Sovereign Gateway Full Network Storage Architecture

- [[Index]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[00_MASTER_INFRASTRUCTURE_TOPOLOGY/CANONICAL_MESH_RAM_AND_MODEL_DISTRIBUTION]]
- [[APPS_AND_FEATURES/LAUBURU_UNIFIED_STORAGE_AND_SEAWEEDFS_ARCHITECTURE]]

This canonical specification documents the deployment, configuration, and verification of the full network storage subsystem delivered through the **GL-BE14000 Sovereign Gateway Router** (`192.168.8.1`).

---

## 🏛️ 1. Architecture Overview

The router operates as a 24/7 high-availability network storage bridge across all 7 layers of the Lauburu Mesh, combining local fast eMMC flash storage with the SeaweedFS distributed cluster:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│             GL-BE14000 SOVEREIGN ROUTER FULL NETWORK STORAGE                │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. ROUTER PERSISTENT STORAGE POOL                                           │
│    • Hardware: Qualcomm IPQ9574 ARMv8 64-bit quad-core, 2.0 GB RAM          │
│    • Local Flash: 57.9 GB /overlay (F2FS on /dev/mmcblk0p7 -> /dev/loop0)   │
│    • Swap Memory: 2.0 GB swapfile (/overlay/swapfile)                       │
│    • Flash Share: /overlay/shared_mesh (drwxrwxrwx)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. SEAWEEDFS DISTRIBUTED CLUSTER NODE (Native ARM64 Daemon)                │
│    • Master Server: http://192.168.8.1:9333 (Raft Leader)                   │
│    • Filer Service: http://192.168.8.1:8888 (LevelDB2 Store)                │
│    • S3 API Gateway: http://192.168.8.1:8333 (AWS S3-compatible)            │
│    • WebDAV Service: http://192.168.8.1:7333                                │
│    • Volume Server: http://192.168.8.1:8085 (30GB eMMC allocation)          │
│    • Local FUSE Mount: 127.0.0.1:8888:/ -> /mnt/seaweedfs (900 GB virtual)  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. NETWORK PROTOCOL EXPORTS                                                 │
│    • Samba 4 (CIFS): smb://192.168.8.1/seaweedfs & /lauburu_shared (TCP 445)│
│    • WebDAV: http://192.168.8.1:7333/ & GL-WebDAV :6008                    │
│    • S3 Object Store: http://192.168.8.1:8333/                             │
│    • LuCI Mounts Web UI: https://192.168.8.1:8443/cgi-bin/luci/admin/...    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ 2. LuCI & FSTAB Configuration

LuCI Mount Points URL: `https://192.168.8.1:8443/cgi-bin/luci/admin/system/mounts` (or `http://192.168.8.1:8080/cgi-bin/luci/admin/system/mounts`)

### Canonical `/etc/config/fstab` on Router
```uci
config global
	option anon_swap '0'
	option anon_mount '1'
	option auto_swap '1'
	option auto_mount '1'
	option delay_root '5'
	option check_fs '0'

config mount 'overlay_mount'
	option target '/overlay'
	option device '/dev/loop0'
	option fstype 'f2fs'
	option options 'rw,noatime'
	option enabled '1'

config mount 'net_storage'
	option target '/mnt/network_storage'
	option device '/overlay/shared_mesh'
	option options 'bind'
	option enabled '1'

config mount 'seaweed_mount'
	option target '/mnt/seaweedfs'
	option device 'seaweedfs'
	option fstype 'fuse'
	option options 'defaults,allow_other'
	option enabled '1'

config swap
	option device '/overlay/swapfile'
	option enabled '1'
```

---

## 🚀 3. Service Daemon: `/etc/init.d/seaweedfs`

The SeaweedFS service is registered as an OpenWrt `procd` managed service with automatic respawn:
- Binary: `/overlay/bin/weed` (symlinked to `/usr/bin/weed`)
- Init Script: `/etc/init.d/seaweedfs` (Enabled on boot: `START=95`)
- Subprocesses:
  1. `server`: SeaweedFS Master (port 9333), Filer (port 8888), S3 (port 8333), Volume (port 8085).
  2. `webdav`: SeaweedFS WebDAV bridge (port 7333).
  3. `mount`: FUSE client mounting `127.0.0.1:8888:/` to `/mnt/seaweedfs`.

---

## 📁 4. Samba 4 (CIFS) Shares

Samba 4 config (`/etc/config/samba4`) exports two shares:
1. `[seaweedfs]`:
   - Path: `/mnt/seaweedfs`
   - Permissions: `read_only = no`, `guest_ok = yes`, mask `0666`/`0777`
   - Target: Full distributed SeaweedFS filesystem accessible natively in macOS Finder, Windows Explorer, and Linux file managers.
2. `[lauburu_shared]`:
   - Path: `/overlay/shared_mesh`
   - Target: Direct ultra-fast flash share for mesh scratch files and backup.

---

## 🛡️ 5. Empirical Tri-Proof Verification (Rule 1 & Rule 5)

1. **Proof 1 (Actuation & Mounting):**
   - Router process status: `running` (`/etc/init.d/seaweedfs status` and `/etc/init.d/samba4 status`).
   - Active mount table: `127.0.0.1:8888:/ on /mnt/seaweedfs type fuse.seaweedfs (rw,...)`.
   - Client mount exit code 0: `mount_smbfs //guest:@192.168.8.1/seaweedfs ~/Network_Storage/Router_SeaweedFS`.
2. **Proof 2 (Line-by-Line & Cryptographic SHA256 Checksum):**
   - Test write from Mac Mini: `mac_mini_verified.txt` written into `Router_SeaweedFS`.
   - Exact SHA256 computed on Mac Mini:
     `4ae6ee82d21da0f73cb63d0d3fa17cb8fb67cba26545b61c9bd4b4f8c562382a`
   - Exact SHA256 computed on Router:
     `4ae6ee82d21da0f73cb63d0d3fa17cb8fb67cba26545b61c9bd4b4f8c562382a`
   - Checksum match: `IDENTICAL` (100% data integrity verified).
3. **Proof 3 (Visual & DOM Verification):**
   - LuCI Mount Points (`admin/system/mounts`) accessibility snapshot verified via Chrome DevTools.
   - Displayed rows:
     - `/dev/root` on `/rom` (95.50 MiB)
     - `tmpfs` on `/tmp` (993.16 MiB)
     - `/dev/loop0` on `/overlay` (57.91 GiB, 54.45 GiB avail)
     - `127.0.0.1:8888:/` on `/mnt/seaweedfs` (900.00 GiB virtual pool)
     - Configured mount points `/overlay`, `/mnt/network_storage`, `/mnt/seaweedfs`, and SWAP `/overlay/swapfile`.

---

## 🛠️ 6. Client Automation Scripts

- `06_scripts_and_tooling/storage/mount_router_network_storage.sh`:
  - Mounts both `Router_Shared` and `Router_SeaweedFS` to `~/Network_Storage/`.
  - Performs automatic SMB probe and read/write health test.
- `00_core_infrastructure/seaweedfs/router_seaweed_cluster_bridge.sh`:
  - Probes Master (`:9333`), Filer (`:8888`), S3 (`:8333`), and WebDAV (`:7333`).
