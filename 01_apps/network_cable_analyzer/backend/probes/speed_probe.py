"""
Lauburu Cable Probe - Transfer Speed, Throughput & Latency Engine
Calculates real-time interface I/O throughput (Bytes/sec, KB/s, MB/s)
and pings physical and overlay links for sub-millisecond RTT latency.
"""
import time
import subprocess
import logging
from typing import Dict, Any

try:
    from .dynamic_ip_finder import get_tb4_bridge_ip, get_node_dynamic_ips
except (ImportError, ValueError):
    from probes.dynamic_ip_finder import get_tb4_bridge_ip, get_node_dynamic_ips

logger = logging.getLogger("lauburu.speed_probe")

_last_sample_time = 0.0
_last_counters: Dict[str, Dict[str, int]] = {}

def run_cmd(cmd: str, timeout: float = 2.0) -> str:
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL, timeout=timeout).strip()
    except Exception as e:
        logger.debug(f"Command failed ({cmd}): {e}")
        return ""

def sample_netstat_counters() -> Dict[str, Dict[str, int]]:
    """Sample raw cumulative I/O bytes from Darwin netstat -ib."""
    out = run_cmd("netstat -ib -n")
    counters: Dict[str, Dict[str, int]] = {}
    if not out:
        return counters

    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 10:
            iface = parts[0]
            # Skip link-local alias lines like <Link#7>
            try:
                ibytes = int(parts[6])
                obytes = int(parts[9])
                if iface not in counters:
                    counters[iface] = {"ibytes": ibytes, "obytes": obytes}
            except (ValueError, IndexError):
                continue
    return counters

def get_realtime_throughput() -> Dict[str, Any]:
    """Calculate instantaneous Rx and Tx throughput per interface in MB/s and KB/s."""
    global _last_sample_time, _last_counters
    now = time.time()
    current_counters = sample_netstat_counters()

    if not _last_counters or (now - _last_sample_time) <= 0:
        _last_sample_time = now
        _last_counters = current_counters
        time.sleep(0.1)
        current_counters = sample_netstat_counters()
        now = time.time()

    dt = max(now - _last_sample_time, 0.05)
    throughput: Dict[str, Any] = {}

    target_interfaces = ["en0", "en1", "bridge0", "utun4"]
    for iface in target_interfaces:
        curr = current_counters.get(iface, {"ibytes": 0, "obytes": 0})
        prev = _last_counters.get(iface, {"ibytes": 0, "obytes": 0})

        rx_bytes_sec = max(0, (curr["ibytes"] - prev["ibytes"]) / dt)
        tx_bytes_sec = max(0, (curr["obytes"] - prev["obytes"]) / dt)

        rx_mbps = round((rx_bytes_sec * 8) / 1_000_000, 2)
        tx_mbps = round((tx_bytes_sec * 8) / 1_000_000, 2)

        rx_sec = round(rx_bytes_sec, 2)
        tx_sec = round(tx_bytes_sec, 2)

        rx_kb = round(rx_bytes_sec / 1024, 1)
        tx_kb = round(tx_bytes_sec / 1024, 1)

        throughput[iface] = {
            "rx_bytes_sec": rx_sec,
            "tx_bytes_sec": tx_sec,
            "rx_mbps": rx_mbps,
            "tx_mbps": tx_mbps,
            "rx_kb_s": rx_kb,
            "tx_kb_s": tx_kb
        }

    _last_sample_time = now
    _last_counters = current_counters
    return throughput

def ping_rtt(ip: str, timeout_ms: int = 400) -> float:
    """Measure single-packet ping latency in milliseconds."""
    out = run_cmd(f"ping -c 1 -W {timeout_ms} {ip}")
    if not out or "time=" not in out:
        return -1.0
    try:
        part = out.split("time=")[1].split()[0]
        val = float(part)
        return val
    except Exception:
        return -1.0

def probe_network_latencies() -> Dict[str, Any]:
    """Probe live link latencies across physical cables and overlays using dynamic IPs."""
    tb4_ip = get_tb4_bridge_ip()
    mbp_ts = get_node_dynamic_ips("l2_macbook_pro").get("tailscale_ip", "100.103.212.21")
    router_ip = get_node_dynamic_ips("gw_router").get("local_ip", "192.168.8.1")
    linux_ts = get_node_dynamic_ips("l3_linux_head").get("tailscale_ip", "100.101.39.98")
    pixel_ip = get_node_dynamic_ips("l6_pixel_10").get("local_ip", "192.168.8.145")
    samsung_ip = get_node_dynamic_ips("l7_samsung_s20").get("local_ip", "192.168.8.118")

    latencies = {
        "tb4_mac_bridge": {
            "target": f"Intel MacBook Pro via TB4 ({tb4_ip})",
            "link_type": "Thunderbolt 4 Smart Cable (40 Gbps)",
            "rtt_ms": ping_rtt(tb4_ip, timeout_ms=300)
        },
        "tailscale_mbp": {
            "target": f"Intel MacBook Pro via Tailscale ({mbp_ts})",
            "link_type": "Tailscale WireGuard Mesh",
            "rtt_ms": ping_rtt(mbp_ts, timeout_ms=500)
        },
        "ethernet_router_lan": {
            "target": f"GL.iNet Router ({router_ip})",
            "link_type": "Cat6 RJ45 Gigabit Ethernet / Wi-Fi",
            "rtt_ms": ping_rtt(router_ip, timeout_ms=300)
        },
        "tailscale_linux_head": {
            "target": f"Linux Head Node ({linux_ts})",
            "link_type": "Tailscale WireGuard Mesh",
            "rtt_ms": ping_rtt(linux_ts, timeout_ms=500)
        },
        "wifi_pixel_10": {
            "target": f"Pixel 10 Pro XL ({pixel_ip})",
            "link_type": "Wi-Fi 7 Local Subnet",
            "rtt_ms": ping_rtt(pixel_ip, timeout_ms=400)
        },
        "wifi_samsung_s20": {
            "target": f"Samsung Galaxy S20+ ({samsung_ip})",
            "link_type": "Wi-Fi Subnet / USB ADB",
            "rtt_ms": ping_rtt(samsung_ip, timeout_ms=400)
        }
    }
    return latencies

def probe_all_speed_metrics() -> Dict[str, Any]:
    """Aggregate throughput, latencies, and link specifications."""
    return {
        "throughput": get_realtime_throughput(),
        "latencies": probe_network_latencies(),
        "link_specs": {
            "thunderbolt_4": {"theoretical_gbps": 40.0, "lanes": 2, "per_lane_gbps": 20.0},
            "hdmi_2_1": {"delivered_gbps": 25.92, "lanes": 4, "rate_hbr3_gbps": 8.1},
            "ethernet_gigabit": {"bandwidth_gbps": 1.0, "duplex": "Full", "standard": "1000BASE-T"},
            "wifi_7": {"theoretical_gbps": 2.4, "bands": "2.4GHz / 5GHz / 6GHz", "mlo": True},
            "usb_3_2_gen2": {"bandwidth_gbps": 10.0},
            "usb_3_2_gen1": {"bandwidth_gbps": 5.0},
            "usb_2_0_high_speed": {"bandwidth_mbps": 480.0},
            "usb_1_1_full_speed": {"bandwidth_mbps": 12.0}
        }
    }
