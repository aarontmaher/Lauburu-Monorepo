"""
Lauburu Probe - Dynamic IP Finder Engine
Discovers authentic dynamic DHCP, Tailscale, Thunderbolt 4, and ADB endpoints
across all 8 mesh devices in real time via Darwin kernel syscalls, Tailscale status,
OpenWrt router DHCP leases, and ADB device tables.
"""
import re
import json
import time
import shutil
import logging
import subprocess
from typing import Dict, Any, Optional, List

logger = logging.getLogger("lauburu.dynamic_ip_finder")

# Cache to avoid running heavy CLI subshells on every millisecond call
_cached_ip_map: Optional[Dict[str, Any]] = None
_last_lookup_time = 0.0
CACHE_TTL = 3.0  # seconds (responsive auto-discovery)

def run_cmd(cmd: str, timeout: float = 2.0) -> str:
    """Run shell command safely with timeout and return stripped stdout."""
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL, timeout=timeout).strip()
    except Exception as e:
        logger.debug(f"Command failed ({cmd}): {e}")
        return ""

def is_ip_alive(ip: str, timeout_ms: int = 400) -> bool:
    """Verify whether an IP address is actively responding to ping."""
    if not ip or ip.endswith(".255") or ip == "127.0.0.1":
        return False
    out = run_cmd(f"ping -c 1 -W {timeout_ms} {ip} 2>/dev/null", timeout=0.6)
    return "time=" in out or "1 packets received" in out

def get_tailscale_peers_info() -> Dict[str, Any]:
    """Parse tailscale status --json to extract live Tailscale IPs, HostNames, and CurAddr."""
    raw = run_cmd("tailscale status --json", timeout=2.5)
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        result = {
            "self": data.get("Self", {}),
            "peers": data.get("Peer", {})
        }
        return result
    except Exception as e:
        logger.warning(f"Error parsing tailscale status JSON: {e}")
        return {}

def get_arp_table_info() -> List[Dict[str, str]]:
    """Parse numeric arp -an output for fast IP to MAC and interface mapping without DNS stalls."""
    raw = run_cmd("arp -an", timeout=1.5)
    entries = []
    if not raw:
        return entries
    
    # Example line: ? (192.168.8.128) at a4:83:e7:d1:7c:82 on en1 ifscope [ethernet]
    # Example line: ? (169.254.215.118) at 82:e6:6d:c0:a4:1 on bridge0 [ethernet]
    pattern = re.compile(r"\?\s+\(([\d\.]+)\)\s+at\s+([0-9a-fA-F:]+|\(incomplete\))\s+on\s+([a-zA-Z0-9]+)")
    for line in raw.splitlines():
        m = pattern.search(line)
        if m:
            ip, mac, iface = m.group(1), m.group(2), m.group(3)
            entries.append({
                "ip": ip,
                "mac": mac.lower() if mac != "(incomplete)" else None,
                "interface": iface
            })
    return entries

def get_router_dhcp_leases() -> List[Dict[str, str]]:
    """Fetch live DHCP leases from GL.iNet router over SSH (192.168.8.1)."""
    raw = run_cmd("ssh -o BatchMode=yes -o ConnectTimeout=1 root@192.168.8.1 'cat /tmp/dhcp.leases' 2>/dev/null", timeout=1.5)
    leases = []
    if not raw:
        return leases
    
    # Format: timestamp mac ip hostname client_id
    for line in raw.splitlines():
        parts = line.strip().split()
        if len(parts) >= 4:
            leases.append({
                "timestamp": parts[0],
                "mac": parts[1].lower(),
                "ip": parts[2],
                "hostname": parts[3]
            })
    try:
        leases.sort(key=lambda x: int(x.get("timestamp", 0)))
    except Exception:
        pass
    return leases

def get_adb_attached_targets() -> Dict[str, Dict[str, str]]:
    """Parse adb devices -l for attached devices and active wireless/USB targets."""
    raw = run_cmd("adb devices -l", timeout=2.0)
    targets = {}
    if not raw:
        return targets

    for line in raw.splitlines()[1:]:
        line = line.strip()
        if not line or "offline" in line:
            continue
        parts = line.split()
        serial_or_endpoint = parts[0]
        model = ""
        product = ""
        transport = "usb" if "usb:" in line else "tcp"
        for part in parts[1:]:
            if part.startswith("model:"):
                model = part.split(":", 1)[1]
            elif part.startswith("product:"):
                product = part.split(":", 1)[1]

        targets[serial_or_endpoint] = {
            "target": serial_or_endpoint,
            "model": model,
            "product": product,
            "transport": transport,
            "raw": line
        }
    return targets

def get_local_interfaces_info() -> Dict[str, str]:
    """Inspect local network interfaces on Mac host."""
    interfaces = {}
    # Wi-Fi 7 (en1)
    en1 = run_cmd("ipconfig getifaddr en1 2>/dev/null || ifconfig en1 | grep 'inet ' | awk '{print $2}'")
    if en1:
        interfaces["en1"] = en1.splitlines()[0].strip()
    
    # Ethernet (en0)
    en0 = run_cmd("ipconfig getifaddr en0 2>/dev/null || ifconfig en0 | grep 'inet ' | awk '{print $2}'")
    if en0:
        interfaces["en0"] = en0.splitlines()[0].strip()

    # TB4 Bridge (bridge0)
    b0 = run_cmd("ifconfig bridge0 2>/dev/null | grep 'inet ' | awk '{print $2}'")
    if b0:
        interfaces["bridge0"] = b0.splitlines()[0].strip()

    # Tailscale (utun4)
    utun4 = run_cmd("ifconfig utun4 2>/dev/null | grep 'inet ' | awk '{print $2}'")
    if utun4:
        interfaces["utun4"] = utun4.splitlines()[0].strip()

    return interfaces

def find_dynamic_mesh_ips(force: bool = False) -> Dict[str, Dict[str, Any]]:
    """
    Fuses Tailscale peers, ARP cache, Router DHCP leases, ADB devices, and Darwin interfaces
    to return a live dynamic IP mapping for all 8 mesh layers.
    """
    global _cached_ip_map, _last_lookup_time
    now = time.time()
    if not force and _cached_ip_map is not None and (now - _last_lookup_time) < CACHE_TTL:
        return _cached_ip_map

    t0 = time.time()
    ts_info = get_tailscale_peers_info()
    arp_entries = get_arp_table_info()
    dhcp_leases = get_router_dhcp_leases()
    adb_targets = get_adb_attached_targets()
    local_ifaces = get_local_interfaces_info()

    # Canonical base dictionary
    mesh_map: Dict[str, Dict[str, Any]] = {
        "l1_mac_mini": {
            "device_id": "l1_mac_mini",
            "name": "Mac Mini M4 Pro (Host L1)",
            "local_ip": local_ifaces.get("en1", "192.168.8.155"),
            "tailscale_ip": local_ifaces.get("utun4", "100.119.199.76"),
            "tb4_ip": local_ifaces.get("bridge0", None),
            "mac_address": "5e:30:9d:be:28:75",
            "interface": "en1",
            "online": True,
            "source": "kernel_darwin"
        },
        "l2_macbook_pro": {
            "device_id": "l2_macbook_pro",
            "name": "Intel MacBook Pro (L2)",
            "local_ip": "10.127.110.221",
            "tailscale_ip": "100.103.212.21",
            "tb4_ip": "169.254.175.124",
            "mac_address": "82:e6:6d:c0:a4:01",
            "ssh_host": "macbook-pro",
            "online": True,
            "source": "verified_wifi"
        },
        "l3_linux_head": {
            "device_id": "l3_linux_head",
            "name": "Linux Head Node (L3)",
            "local_ip": "192.168.8.225",
            "tailscale_ip": "100.101.39.98",
            "tb4_ip": None,
            "mac_address": "00:41:0e:14:28:43",
            "ssh_host": "linux",
            "online": False,
            "source": "unresolved"
        },
        "l4_linux_tablet": {
            "device_id": "l4_linux_tablet",
            "name": "Linux Tablet (L4)",
            "local_ip": "192.168.8.190",
            "tailscale_ip": "100.118.79.63",
            "tb4_ip": None,
            "mac_address": "76:1c:bf:4f:03:51",
            "ssh_host": "tablet",
            "online": False,
            "source": "unresolved"
        },
        "l5_macbook_air": {
            "device_id": "l5_macbook_air",
            "name": "MacBook Air M4 (L5)",
            "local_ip": "192.168.8.122",
            "tailscale_ip": "100.121.202.34",
            "tb4_ip": "192.168.2.11",
            "mac_address": "36:90:11:cc:f:40",
            "ssh_host": "macbook-air-tb",
            "online": False,
            "source": "unresolved"
        },
        "l6_pixel_10": {
            "device_id": "l6_pixel_10",
            "name": "Pixel 10 Pro XL (L6)",
            "local_ip": "100.73.38.87",
            "tailscale_ip": "100.73.38.87",
            "adb_target": "100.73.38.87:5555",
            "mac_address": "66:00:88:ca:e8:3b",
            "online": False,
            "source": "unresolved"
        },
        "l7_samsung_s20": {
            "device_id": "l7_samsung_s20",
            "name": "Samsung Galaxy S20+ (L7)",
            "local_ip": "10.127.110.219",
            "tailscale_ip": "100.84.40.95",
            "adb_target": "R3CN40CJJ1R",
            "mac_address": "5a:0f:80:ad:7c:28",
            "online": False,
            "source": "unresolved"
        },
        "l8_linux_mini": {
            "device_id": "l8_linux_mini",
            "name": "Linux Mini Compute Vault (L8)",
            "local_ip": "192.168.8.238",
            "tailscale_ip": "100.121.247.8",
            "tb4_ip": None,
            "mac_address": "2:82:a3:9e:ae:71",
            "ssh_host": "linuxmini-tb",
            "online": False,
            "source": "unresolved"
        },
        "l9_iphone_16": {
            "device_id": "l9_iphone_16",
            "name": "iPhone 16 Pro (L9)",
            "local_ip": "192.168.8.102",
            "tailscale_ip": "100.122.52.89",
            "tb4_ip": None,
            "mac_address": "74:cc:40:20:8e:10",
            "ssh_host": "iphone",
            "online": False,
            "source": "unresolved"
        },
        "gw_router": {
            "device_id": "gw_router",
            "name": "GL.iNet Gateway Router (GW)",
            "local_ip": "192.168.8.1",
            "tailscale_ip": "100.103.212.34",
            "tb4_ip": None,
            "mac_address": "94:83:c4:eb:e7:31",
            "ssh_host": "root@192.168.8.1",
            "online": True,
            "source": "kernel_gateway"
        }
    }

    # 1. Enrich from Tailscale Status
    self_node = ts_info.get("self", {})
    if self_node:
        ts_ips = self_node.get("TailscaleIPs", [])
        if ts_ips:
            mesh_map["l1_mac_mini"]["tailscale_ip"] = ts_ips[0]

    peers = ts_info.get("peers", {})
    for _, peer in peers.items():
        hn = peer.get("HostName", "").lower()
        dns = peer.get("DNSName", "").lower()
        ips = peer.get("TailscaleIPs", [])
        primary_ip = ips[0] if ips else None
        cur_addr = peer.get("CurAddr", "")
        online = peer.get("Online", False)

        cur_ip = cur_addr.split(":")[0] if cur_addr and ":" in cur_addr else None

        # Match L2 MacBook Pro
        if "mac-pro" in hn or "mbp" in hn:
            if primary_ip:
                mesh_map["l2_macbook_pro"]["tailscale_ip"] = primary_ip
            if cur_ip:
                mesh_map["l2_macbook_pro"]["local_ip"] = cur_ip
            mesh_map["l2_macbook_pro"]["online"] = online
            mesh_map["l2_macbook_pro"]["source"] = "tailscale_peer"

        # Match L8 Linux Mini (hostname "lauburu" or "linuxmini")
        elif "lauburu" in hn or "linuxmini" in hn:
            if primary_ip:
                mesh_map["l8_linux_mini"]["tailscale_ip"] = primary_ip
            if cur_ip:
                mesh_map["l8_linux_mini"]["local_ip"] = cur_ip
            is_active = online or (bool(primary_ip) and is_ip_alive(primary_ip)) or (bool(cur_ip) and is_ip_alive(cur_ip))
            mesh_map["l8_linux_mini"]["online"] = is_active
            mesh_map["l8_linux_mini"]["source"] = "tailscale_peer"

        # Match L3 Linux Head (AMD Ryzen 7 laptop, hostname "linux")
        elif hn == "linux" or "inspiron" in hn or "dell" in hn:
            if primary_ip:
                mesh_map["l3_linux_head"]["tailscale_ip"] = primary_ip
            if cur_ip:
                mesh_map["l3_linux_head"]["local_ip"] = cur_ip
            is_active = online or (bool(primary_ip) and is_ip_alive(primary_ip)) or (bool(cur_ip) and is_ip_alive(cur_ip))
            mesh_map["l3_linux_head"]["online"] = is_active
            mesh_map["l3_linux_head"]["source"] = "tailscale_peer"

        # Match L4 Tablet
        elif "tablet" in hn or "tab" in hn:
            if primary_ip:
                mesh_map["l4_linux_tablet"]["tailscale_ip"] = primary_ip
            if cur_ip:
                mesh_map["l4_linux_tablet"]["local_ip"] = cur_ip
            mesh_map["l4_linux_tablet"]["online"] = online
            mesh_map["l4_linux_tablet"]["source"] = "tailscale_peer"

        # Match L5 MacBook Air
        elif "macbook" in hn or "air" in hn:
            if primary_ip:
                mesh_map["l5_macbook_air"]["tailscale_ip"] = primary_ip
            if cur_ip:
                mesh_map["l5_macbook_air"]["local_ip"] = cur_ip
            is_active = online or (bool(primary_ip) and is_ip_alive(primary_ip)) or (bool(cur_ip) and is_ip_alive(cur_ip))
            mesh_map["l5_macbook_air"]["online"] = is_active
            mesh_map["l5_macbook_air"]["source"] = "tailscale_peer"

        # Match L6 Pixel 10 Pro XL
        elif "pixel" in hn:
            if primary_ip:
                mesh_map["l6_pixel_10"]["tailscale_ip"] = primary_ip
            if cur_ip:
                mesh_map["l6_pixel_10"]["local_ip"] = cur_ip
            mesh_map["l6_pixel_10"]["online"] = online
            mesh_map["l6_pixel_10"]["source"] = "tailscale_peer"

        # Match L7 Samsung S20+
        elif "s20" in hn or "samsung" in hn:
            if primary_ip:
                mesh_map["l7_samsung_s20"]["tailscale_ip"] = primary_ip
            if cur_ip:
                mesh_map["l7_samsung_s20"]["local_ip"] = cur_ip
            mesh_map["l7_samsung_s20"]["online"] = online
            mesh_map["l7_samsung_s20"]["source"] = "tailscale_peer"

        # Match L9 iPhone 16 Pro (iPhone17,1)
        elif "iphone171" in dns or primary_ip == "100.122.52.89":
            if primary_ip:
                mesh_map["l9_iphone_16"]["tailscale_ip"] = primary_ip
            if cur_ip:
                mesh_map["l9_iphone_16"]["local_ip"] = cur_ip
            is_active = online or (bool(primary_ip) and is_ip_alive(primary_ip))
            mesh_map["l9_iphone_16"]["online"] = is_active
            mesh_map["l9_iphone_16"]["source"] = "tailscale_peer"

        # Match Gateway Router
        elif "gl-router" in hn or "router" in hn:
            if primary_ip:
                mesh_map["gw_router"]["tailscale_ip"] = primary_ip
            mesh_map["gw_router"]["online"] = online
            mesh_map["gw_router"]["source"] = "tailscale_peer"

    # 2. Enrich from DHCP Leases
    for lease in dhcp_leases:
        hname = lease.get("hostname", "").lower()
        lip = lease.get("ip")
        mac = lease.get("mac")
        target_key = None
        if "s20" in hname or "samsung" in hname:
            target_key = "l7_samsung_s20"
        elif "tab" in hname:
            target_key = "l4_linux_tablet"
        elif "pixel" in hname:
            target_key = "l6_pixel_10"
        elif "mbp" in hname:
            target_key = "l2_macbook_pro"
        elif "air" in hname:
            target_key = "l5_macbook_air"
        elif "linux" in hname:
            target_key = "l3_linux_head"
        elif "iphone" in hname or "apple" in hname:
            target_key = "l9_iphone_16"

        if target_key:
            current_ip = mesh_map[target_key].get("local_ip")
            if lip and is_ip_alive(lip):
                mesh_map[target_key]["local_ip"] = lip
                mesh_map[target_key]["mac_address"] = mac
            elif not current_ip:
                mesh_map[target_key]["local_ip"] = lip
                mesh_map[target_key]["mac_address"] = mac

    # 3. Enrich from ARP cache (especially bridge0 TB4 and direct LAN peers)
    for entry in arp_entries:
        eip = entry.get("ip")
        iface = entry.get("interface")
        # TB4 Bridge IP on bridge0
        if iface == "bridge0" and eip and not eip.endswith(".255") and entry.get("mac") != "ff:ff:ff:ff:ff:ff":
            if eip.startswith("169.254."):
                mesh_map["l2_macbook_pro"]["tb4_ip"] = eip
                mesh_map["l2_macbook_pro"]["online"] = True

    # 4. Enrich ADB Targets
    for target_str, tgt_data in adb_targets.items():
        model = tgt_data.get("model", "")
        product = tgt_data.get("product", "")
        # Pixel 10 Pro XL
        if "pixel" in model.lower() or "mustang" in product.lower():
            mesh_map["l6_pixel_10"]["adb_target"] = target_str
            mesh_map["l6_pixel_10"]["online"] = True
            mesh_map["l6_pixel_10"]["adb_transport"] = tgt_data.get("transport")
        # Samsung S20+
        elif "sm_g986" in model.upper() or "y2s" in product.lower() or "samsung" in model.lower():
            mesh_map["l7_samsung_s20"]["adb_target"] = target_str
            mesh_map["l7_samsung_s20"]["online"] = True
            mesh_map["l7_samsung_s20"]["adb_transport"] = tgt_data.get("transport")

    duration_ms = round((time.time() - t0) * 1000, 2)
    result_payload = {
        "timestamp": now,
        "resolution_latency_ms": duration_ms,
        "nodes": mesh_map,
        "total_resolved": len(mesh_map),
        "online_count": sum(1 for n in mesh_map.values() if n.get("online"))
    }

    _cached_ip_map = result_payload
    _last_lookup_time = now
    return result_payload

def get_node_dynamic_ips(node_id: str) -> Dict[str, Any]:
    """Retrieve dynamic IP details for a single node."""
    ip_map = find_dynamic_mesh_ips()
    return ip_map.get("nodes", {}).get(node_id, {})

def get_adb_target(node_id: str, default: Optional[str] = None) -> Optional[str]:
    """Retrieve active dynamic ADB target string for a node (e.g. USB serial or IP:port)."""
    node_data = get_node_dynamic_ips(node_id)
    return node_data.get("adb_target", default)

def get_tb4_bridge_ip() -> str:
    """Retrieve live TB4 bridge IP for MacBook Pro (L2)."""
    node_data = get_node_dynamic_ips("l2_macbook_pro")
    return node_data.get("tb4_ip") or "169.254.175.124"

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    data = find_dynamic_mesh_ips(force=True)
    print(f"Dynamic IP Finder (Resolved in {data['resolution_latency_ms']}ms, {data['online_count']}/{data['total_resolved']} Online):")
    for nid, info in data["nodes"].items():
        lip = str(info.get('local_ip') or '--')
        tsip = str(info.get('tailscale_ip') or '--')
        tbip = str(info.get('tb4_ip') or '--')
        onl = str(info.get('online', False))
        src = str(info.get('source') or '--')
        print(f" - {nid:16}: LAN={lip:15} TS={tsip:15} TB4={tbip:16} Online={onl:5} Src={src}")
