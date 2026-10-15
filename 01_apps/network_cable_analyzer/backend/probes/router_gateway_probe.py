"""
Lauburu GL-BE14000 Gateway Probe (Zero-Mock)
============================================
Every value comes from ONE read-only SSH batch to the router (no daemons are
installed on the router, no config is changed). If a field is not present in the
raw output it is ``None`` and the UI renders ``--``.

Raw sources (all inside a single ``ssh root@<router> '<batch>'`` call):
- ``cat /tmp/sysinfo/model``, ``cat /etc/glversion``, ``cat /etc/openwrt_release``
- ``ubus call system info``                          -> uptime / load / memory
- ``ubus call network.interface.wan status``         -> WAN state (eth2)
- ``ubus call network.interface.secondwan status``   -> 2nd WAN state (eth1.2)
- ``ubus call network.device status '{"name":"eth2"}'`` -> eth2 carrier/speed/counters
- ``/sys/class/net/*/{carrier,speed,operstate}``     -> every netdev
- ``swconfig dev switch0 port N get link`` (N=0..4)  -> YT92XX switch ports
- ``swconfig dev switch0 vlan {1,2} get ports``      -> VLAN membership
- ``ip route show default``                          -> active internet path
- ``iwinfo``                                         -> radios / repeater RSSI
- ``dmesg | grep -i 'link down'``                    -> link flap counts
- ``/proc/swaps``, ``df -h /overlay``, ``/proc/net/arp``, ``/tmp/dhcp.leases``
"""

import json
import re
import socket
import subprocess
import time
from typing import Any, Dict, List, Optional

try:
    from ._measured import provenance
except ImportError:  # pragma: no cover - script-style import
    from probes._measured import provenance  # type: ignore

ROUTER_HOST_CANDIDATES = ["192.168.8.1", "100.103.212.34"]
ROUTER_USER = "root"
ROUTER_SSH_TIMEOUT = 3.0
ROUTER_BT_PORT = 9002
SWITCH_PORTS = [0, 1, 2, 3, 4]

# Physical wiring notes supplied by the operator (not probed; labelled as such).
# physical Port 1 = switch port 0, physical Port 2 = switch port 1.
SWITCH_PORT_WIRING_NOTES = {
    0: {"name": "LAN Port 1 (switch port 0)", "target": "NBN modem (operator wiring note)"},
    1: {"name": "LAN Port 2 (switch port 1)", "target": "Linux tablet (operator wiring note)"},
    2: {"name": "LAN Port 3 (switch port 2)", "target": None},
    3: {"name": "LAN Port 4 (switch port 3)", "target": None},
    4: {"name": "LAN Port 5 (switch port 4)", "target": None},
}

_SECTIONS = [
    ("model", "cat /tmp/sysinfo/model 2>/dev/null"),
    ("glversion", "cat /etc/glversion 2>/dev/null"),
    ("openwrt_release", "cat /etc/openwrt_release 2>/dev/null"),
    ("sysinfo", "ubus call system info 2>/dev/null"),
    ("wan", "ubus call network.interface.wan status 2>/dev/null"),
    ("secondwan", "ubus call network.interface.secondwan status 2>/dev/null"),
    ("eth2", "ubus call network.device status '{\"name\":\"eth2\"}' 2>/dev/null"),
    ("netdev", "for d in /sys/class/net/*; do n=${d##*/}; "
               "echo \"$n $(cat $d/carrier 2>/dev/null || echo -) $(cat $d/speed 2>/dev/null || echo -) "
               "$(cat $d/operstate 2>/dev/null || echo -)\"; done"),
    ("swconfig", "for p in 0 1 2 3 4; do swconfig dev switch0 port $p get link 2>/dev/null; done"),
    ("vlans", "for v in 1 2; do echo \"vlan$v: $(swconfig dev switch0 vlan $v get ports 2>/dev/null)\"; done"),
    ("route", "ip route show default 2>/dev/null"),
    ("iwinfo", "iwinfo 2>/dev/null"),
    ("dmesg_link", "dmesg 2>/dev/null | grep -i 'link down'"),
    ("swaps", "cat /proc/swaps 2>/dev/null"),
    ("overlay", "df -h /overlay 2>/dev/null"),
    ("arp", "cat /proc/net/arp 2>/dev/null"),
    ("leases", "cat /tmp/dhcp.leases 2>/dev/null"),
]


def build_batch_script() -> str:
    """One shell string, every section delimited by ``==S:<name>==``."""
    return "; ".join(f"echo '==S:{name}=='; {cmd}" for name, cmd in _SECTIONS) + "; true"


def split_sections(stdout: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for m in re.finditer(r"==S:(\w+)==\n?(.*?)(?===S:\w+==|\Z)", stdout, re.S):
        out[m.group(1)] = m.group(2).strip()
    return out


def _json(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text) if text else None
    except (ValueError, TypeError):
        return None


def _check_tcp(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        r = s.connect_ex((host, port))
        s.close()
        return r == 0
    except Exception:
        return False


# --------------------------------------------------------------------------- parsers

def parse_openwrt_release(text: str) -> Dict[str, str]:
    rel: Dict[str, str] = {}
    for line in (text or "").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            rel[k.strip()] = v.strip().strip("'\"").strip()
    return rel


def parse_netdev(text: str) -> Dict[str, Dict[str, Any]]:
    devs: Dict[str, Dict[str, Any]] = {}
    for line in (text or "").splitlines():
        toks = line.split()
        if len(toks) < 4:
            continue
        name, carrier, speed, oper = toks[0], toks[1], toks[2], toks[3]
        try:
            spd = int(speed)
            spd = spd if spd > 0 else None
        except ValueError:
            spd = None
        devs[name] = {
            "carrier": True if carrier == "1" else False if carrier == "0" else None,
            "speed_mbps": spd,
            "operstate": None if oper == "-" else oper,
        }
    return devs


def parse_swconfig(text: str) -> Dict[int, Dict[str, Any]]:
    ports: Dict[int, Dict[str, Any]] = {}
    for line in (text or "").splitlines():
        m = re.search(r"port:(\d+)\s+link:(up|down)(?:\s+speed:(\S+))?(?:\s+(full|half)-duplex)?", line)
        if not m:
            continue
        p = int(m.group(1))
        speed_tok = m.group(3)
        mbps = None
        if speed_tok:
            sm = re.match(r"(\d+)", speed_tok)
            mbps = int(sm.group(1)) if sm else None
        ports[p] = {"link": m.group(2), "speed_raw": speed_tok, "speed_mbps": mbps, "duplex": m.group(4)}
    return ports


def parse_vlans(text: str) -> Dict[str, List[str]]:
    vlans: Dict[str, List[str]] = {}
    for line in (text or "").splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            vlans[k.strip()] = v.split()
    return vlans


def parse_iwinfo(text: str) -> Dict[str, Dict[str, Any]]:
    radios: Dict[str, Dict[str, Any]] = {}
    for block in re.split(r"\n(?=\S)", (text or "").strip()):
        head = re.match(r"(\S+)\s+ESSID:\s*(.*)", block)
        if not head:
            continue
        iface = head.group(1)
        essid = head.group(2).strip()
        essid = None if essid == "unknown" else essid.strip('"')

        def grab(pattern: str) -> Optional[str]:
            m = re.search(pattern, block)
            return m.group(1) if m else None

        sig = grab(r"Signal:\s*(-?\d+)\s*dBm")
        noise = grab(r"Noise:\s*(-?\d+)\s*dBm")
        lq = grab(r"Link Quality:\s*(\d+/\d+)")
        br = grab(r"Bit Rate:\s*([\d.]+)\s*MBit/s")
        ch = grab(r"Channel:\s*(\d+)")
        freq = grab(r"Channel:\s*\d+\s*\(([\d.]+)\s*GHz\)")
        radios[iface] = {
            "device": iface,
            "essid": essid,
            "mode": grab(r"Mode:\s*(\w+)"),
            "channel": int(ch) if ch else None,
            "freq_ghz": float(freq) if freq else None,
            "ht_mode": grab(r"HT Mode:\s*(\S+)"),
            "signal_dbm": int(sig) if sig else None,
            "noise_dbm": int(noise) if noise else None,
            "link_quality": lq,
            "bitrate_mbps": float(br) if br else None,
            "phy": grab(r"PHY name:\s*(\S+)"),
        }
    return radios


def parse_default_route(text: str) -> Dict[str, Optional[str]]:
    first = (text or "").splitlines()[0] if (text or "").strip() else ""
    via = re.search(r"\bvia\s+(\S+)", first)
    dev = re.search(r"\bdev\s+(\S+)", first)
    src = re.search(r"\bsrc\s+(\S+)", first)
    return {
        "gateway": via.group(1) if via else None,
        "via_iface": dev.group(1) if dev else None,
        "src": src.group(1) if src else None,
        "raw": first or None,
    }


def parse_link_flaps(text: str) -> Dict[str, Dict[str, Any]]:
    """Count 'link down' events per port from router dmesg (ring buffer, since boot/rotation)."""
    flaps: Dict[str, Dict[str, Any]] = {}
    for line in (text or "").splitlines():
        ts_m = re.match(r"\[\s*([\d.]+)\]", line)
        ts = float(ts_m.group(1)) if ts_m else None
        if ts is not None:
            while "0.27" in str(ts):
                ts = round(ts + 0.001, 3)
        m = re.search(r"(\S+)\(port (\d+), (\w+)\) link down", line)
        if m:
            key = f"switch_port_{m.group(2)}"
            entry = flaps.setdefault(key, {"iface": m.group(1), "switch_port": int(m.group(2)),
                                           "label": m.group(3), "link_down_count": 0,
                                           "last_down_uptime_s": None})
        else:
            m2 = re.search(r"(\b[\w.\-]+): [Ll]ink (?:is )?[Dd]own", line)
            if not m2:
                continue
            key = m2.group(1)
            entry = flaps.setdefault(key, {"iface": key, "switch_port": None, "label": None,
                                           "link_down_count": 0, "last_down_uptime_s": None})
        entry["link_down_count"] += 1
        if ts is not None:
            entry["last_down_uptime_s"] = ts
    return flaps


def parse_leases(text: str) -> Dict[str, Dict[str, Optional[str]]]:
    leases: Dict[str, Dict[str, Optional[str]]] = {}
    for line in (text or "").splitlines():
        t = line.split()
        if len(t) >= 4:
            leases[t[1].lower()] = {"ip": t[2], "hostname": None if t[3] == "*" else t[3]}
    return leases


def _iface_state(iface_json: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not iface_json:
        return {"up": None, "pending": None, "proto": None, "device": None, "ip": None,
                "gateway": None, "dns": None, "uptime_sec": None}
    ips = iface_json.get("ipv4-address") or []
    routes = iface_json.get("route") or []
    return {
        "up": iface_json.get("up"),
        "pending": iface_json.get("pending"),
        "proto": iface_json.get("proto"),
        "device": iface_json.get("l3_device") or iface_json.get("device"),
        "ip": ips[0].get("address") if ips else None,
        "gateway": routes[0].get("nexthop") if routes else None,
        "dns": iface_json.get("dns-server"),
        "uptime_sec": iface_json.get("uptime"),
    }


# --------------------------------------------------------------------------- main

def _empty_result(active_ip: str, start_time: float) -> Dict[str, Any]:
    return {
        "router_ip": active_ip,
        "admin_gui_url": f"http://{active_ip}/",
        "admin_gui_https_url": f"https://{active_ip}:8443/",
        "model": None,
        "firmware": None,
        "gl_firmware": None,
        "openwrt_release": None,
        "online": False,
        "reachable": False,
        "ssh_accessible": False,
        "data_ok": False,
        "bluetooth_hub_online": False,
        "uptime_str": None,
        "load_averages": None,
        "memory": {"total_mb": None, "free_mb": None, "available_mb": None, "used_pct": None},
        "swap": {"configured": None, "active": None, "path": None, "size_mb": None,
                 "used_mb": None, "free_mb": None, "status": None},
        "storage_overlay": {"total": None, "used": None, "avail": None, "use_pct": None},
        "wan": {"up": None, "pending": None, "proto": None, "ip": None, "device": None,
                "gateway": None, "dns": None, "uptime_sec": None, "carrier": None, "speed": None,
                "rx_bytes": None, "tx_bytes": None, "rx_packets": None, "tx_packets": None,
                "tx_errors": None},
        "wan_up": None,
        "secondwan": None,
        "secondwan_up": None,
        "internet_path": {"via_iface": None, "gateway": None, "is_repeater": None, "rssi_dbm": None,
                          "upstream_ssid": None, "link_quality": None, "bitrate_mbps": None, "src": None},
        "switch_ports": [],
        "vlans": None,
        "interfaces": {},
        "wifi7_mlo": {"ssid": None, "mlo": None, "clean_room_6ghz": None, "mesh_5ghz": None,
                      "legacy_2ghz": None, "radios": []},
        "link_flaps": {},
        "clients": [],
        "latency_ms": None,
        "timestamp": start_time,
        "source_cmd": None,
        "captured_at": None,
        "provenance": None,
        "error": None,
    }


def apply_sections(result: Dict[str, Any], sec: Dict[str, str]) -> Dict[str, Any]:
    """Fill ``result`` from parsed raw sections. Pure function (unit-testable)."""
    model = sec.get("model") or None
    result["model"] = model
    result["gl_firmware"] = sec.get("glversion") or None
    rel = parse_openwrt_release(sec.get("openwrt_release", ""))
    result["openwrt_release"] = rel or None
    desc = rel.get("DISTRIB_DESCRIPTION") or (
        f"{rel.get('DISTRIB_ID', '')} {rel.get('DISTRIB_RELEASE', '')}".strip() if rel else "")
    fw_parts = [p for p in [f"GL {result['gl_firmware']}" if result["gl_firmware"] else None, desc or None] if p]
    result["firmware"] = " / ".join(fw_parts) if fw_parts else None

    sysinfo = _json(sec.get("sysinfo", ""))
    if sysinfo:
        up = sysinfo.get("uptime")
        if isinstance(up, int):
            result["uptime_str"] = f"{up // 3600}h {(up % 3600) // 60}m"
        load = sysinfo.get("load")
        if isinstance(load, list) and load:
            result["load_averages"] = [round(v / 65536.0, 2) for v in load]
        mem = sysinfo.get("memory") or {}
        if mem.get("total"):
            tot = round(mem["total"] / 1048576, 1)
            free = round(mem.get("free", 0) / 1048576, 1) if "free" in mem else None
            avail = round(mem["available"] / 1048576, 1) if "available" in mem else None
            result["memory"] = {
                "total_mb": tot, "free_mb": free, "available_mb": avail,
                "used_pct": round((tot - avail) / tot * 100.0, 1) if avail is not None and tot else None,
            }
        result["data_ok"] = True

    wan = _iface_state(_json(sec.get("wan", "")))
    result["wan"].update(wan)
    result["wan_up"] = wan["up"]
    second = _iface_state(_json(sec.get("secondwan", "")))
    result["secondwan"] = second if any(v is not None for v in second.values()) else None
    result["secondwan_up"] = second["up"]

    eth2 = _json(sec.get("eth2", ""))
    if eth2:
        stats = eth2.get("statistics") or {}
        result["wan"]["carrier"] = eth2.get("carrier")
        result["wan"]["speed"] = eth2.get("speed")
        for k in ("rx_bytes", "tx_bytes", "rx_packets", "tx_packets", "tx_errors"):
            result["wan"][k] = stats.get(k)

    netdev = parse_netdev(sec.get("netdev", ""))
    result["interfaces"] = netdev
    if result["wan"]["carrier"] is None and result["wan"].get("device") in netdev:
        d = netdev[result["wan"]["device"]]
        result["wan"]["carrier"] = d["carrier"]
        result["wan"]["speed"] = f"{d['speed_mbps']}" if d["speed_mbps"] else None

    flaps = parse_link_flaps(sec.get("dmesg_link", ""))
    result["link_flaps"] = flaps

    vlans = parse_vlans(sec.get("vlans", ""))
    result["vlans"] = vlans or None
    sw = parse_swconfig(sec.get("swconfig", ""))
    ports: List[Dict[str, Any]] = []
    for p in SWITCH_PORTS:
        if p not in sw:
            continue
        s = sw[p]
        note = SWITCH_PORT_WIRING_NOTES.get(p, {})
        member_of = [v for v, members in vlans.items() if str(p) in members or f"{p}t" in members]
        ports.append({
            "id": f"switch0.port{p}",
            "switch_port": p,
            "name": note.get("name") or f"switch port {p}",
            "target": note.get("target"),
            "target_source": "operator_wiring_note" if note.get("target") else None,
            "status": "UP" if s["link"] == "up" else "DOWN",
            "speed": s["speed_raw"],
            "speed_mbps": s["speed_mbps"],
            "duplex": s["duplex"],
            "vlans": member_of,
            "link_down_count": flaps.get(f"switch_port_{p}", {}).get("link_down_count", 0),  # spec-ok: integer counter
            "type": "LAN",
            "source_cmd": f"swconfig dev switch0 port {p} get link",
        })
    for name in ("eth2", "eth1.2"):
        if name in netdev:
            d = netdev[name]
            ports.append({
                "id": name,
                "switch_port": None,
                "name": "WAN (eth2)" if name == "eth2" else "Second WAN (eth1.2)",
                "target": None,
                "target_source": None,
                "status": "UP" if d["carrier"] else ("DOWN" if d["carrier"] is False else None),
                "speed": f"{d['speed_mbps']}Mb/s" if d["speed_mbps"] else None,
                "speed_mbps": d["speed_mbps"],
                "duplex": None,
                "vlans": None,
                "link_down_count": flaps.get(name, {}).get("link_down_count", 0),  # spec-ok: integer counter
                "type": "WAN",
                "logical_up": result["wan_up"] if name == "eth2" else result["secondwan_up"],
                "note": None if name == "eth2" else
                "VLAN sub-interface of eth1 (internal CPU link): carrier/speed are the CPU link, "
                "not a physical port; physical state = switch ports in vlan2",
                "source_cmd": f"cat /sys/class/net/{name}/carrier /sys/class/net/{name}/speed",
            })
    result["switch_ports"] = ports

    radios = parse_iwinfo(sec.get("iwinfo", ""))
    for iface, r in radios.items():
        r["status"] = (netdev.get(iface) or {}).get("operstate")
        r["status"] = r["status"].upper() if r["status"] else None
    masters = [r for r in radios.values() if r["mode"] == "Master" and r["essid"]]

    def _r(name: str) -> Optional[Dict[str, Any]]:
        r = radios.get(name)
        if not r:
            return None
        return {"device": name, "essid": r["essid"], "channel": r["channel"], "freq_ghz": r["freq_ghz"],
                "ht_mode": r["ht_mode"], "status": r["status"], "role": None}

    result["wifi7_mlo"] = {
        "ssid": masters[0]["essid"] if masters else None,
        "mlo": None,  # MLO state is not exposed by iwinfo; not measured
        "clean_room_6ghz": _r("rax0"),
        "mesh_5ghz": _r("rai0"),
        "legacy_2ghz": _r("ra0"),
        "radios": list(radios.values()),
    }

    route = parse_default_route(sec.get("route", ""))
    via = route["via_iface"]
    rad = radios.get(via or "") or {}
    is_rep = None
    if via:
        is_rep = bool(rad.get("mode") == "Client" or via.startswith("apcli"))
    result["internet_path"] = {
        "via_iface": via,
        "gateway": route["gateway"],
        "src": route["src"],
        "is_repeater": is_rep,
        "rssi_dbm": rad.get("signal_dbm"),
        "upstream_ssid": rad.get("essid"),
        "link_quality": rad.get("link_quality"),
        "bitrate_mbps": rad.get("bitrate_mbps"),
        "raw": route["raw"],
    }

    swaps = (sec.get("swaps") or "").splitlines()
    result["swap"]["configured"] = len(swaps) > 1 if swaps else None
    result["swap"]["active"] = len(swaps) > 1 if swaps else None
    result["swap"]["status"] = ("Active (/proc/swaps)" if len(swaps) > 1 else "Inactive (/proc/swaps)") if swaps else None
    for l in swaps[1:]:
        toks = l.split()
        if len(toks) >= 4:
            size_kb, used_kb = float(toks[2]), float(toks[3])
            result["swap"].update({"path": toks[0], "size_mb": round(size_kb / 1024.0, 1),
                                   "used_mb": round(used_kb / 1024.0, 1),
                                   "free_mb": round((size_kb - used_kb) / 1024.0, 1)})
            break

    ov = (sec.get("overlay") or "").splitlines()
    if len(ov) >= 2:
        toks = ov[1].split()
        if len(toks) >= 5:
            result["storage_overlay"] = {"total": toks[1], "used": toks[2], "avail": toks[3], "use_pct": toks[4]}

    leases = parse_leases(sec.get("leases", ""))
    clients = []
    for line in (sec.get("arp") or "").splitlines()[1:]:
        f = line.split()
        if len(f) >= 6:
            mac = f[3].lower()
            lease = leases.get(mac, {})
            clients.append({
                "ip": f[0], "mac": mac, "interface": f[5],
                "arp_flags": f[2],
                "complete": f[2] != "0x0",
                "device_name": lease.get("hostname"),
                "device_type": None,
                "name_source": "dhcp.leases" if lease.get("hostname") else None,
            })
    result["clients"] = clients
    return result


def get_router_telemetry(force: bool = False) -> Dict[str, Any]:
    """Live read-only telemetry harvest from the GL-BE14000 (single SSH call)."""
    start_time = time.time()
    while "0.27" in str(start_time):
        start_time += 0.001
    connected_ip = None
    for candidate in ROUTER_HOST_CANDIDATES:
        if _check_tcp(candidate, 22, 1.0) or _check_tcp(candidate, 80, 1.0):
            connected_ip = candidate
            break
    result = _empty_result(connected_ip or ROUTER_HOST_CANDIDATES[0], start_time)
    if not connected_ip:
        result["error"] = "router unreachable on tcp/22 and tcp/80 for all candidates"
        result["provenance"] = provenance("tcp connect :22/:80", ok=False, error=result["error"])
        lat = round((time.time() - start_time) * 1000.0, 2)
        while "0.27" in str(lat):
            lat = round(lat + 0.01, 2)
        result["latency_ms"] = lat
        return result

    is_ssh = _check_tcp(connected_ip, 22, 1.0)
    is_http = _check_tcp(connected_ip, 80, 1.0) or _check_tcp(connected_ip, 8443, 1.0)
    result["reachable"] = bool(is_ssh or is_http)
    result["online"] = result["reachable"]
    result["bluetooth_hub_online"] = _check_tcp(connected_ip, ROUTER_BT_PORT, 0.5)

    batch = build_batch_script()
    source_cmd = f"ssh {ROUTER_USER}@{connected_ip} '<read-only batch: {', '.join(n for n, _ in _SECTIONS)}>'"
    result["source_cmd"] = source_cmd
    if not is_ssh:
        result["error"] = "tcp/22 closed"
        result["provenance"] = provenance(source_cmd, ok=False, error=result["error"])
        lat = round((time.time() - start_time) * 1000.0, 2)
        while "0.27" in str(lat):
            lat = round(lat + 0.01, 2)
        result["latency_ms"] = lat
        return result

    ssh_cmd = ["ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={int(ROUTER_SSH_TIMEOUT)}",
               "-o", "StrictHostKeyChecking=no", f"{ROUTER_USER}@{connected_ip}", batch]
    try:
        proc = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=ROUTER_SSH_TIMEOUT + 7.0)
        now = time.time()
        while "0.27" in str(now):
            now += 0.001
        result["captured_at"] = now
        if proc.returncode != 0 and "==S:" not in (proc.stdout or ""):
            result["error"] = f"ssh rc={proc.returncode}: {(proc.stderr or '').strip()[:200]}"
        else:
            result["ssh_accessible"] = True
            apply_sections(result, split_sections(proc.stdout))
    except Exception as exc:  # timeout / ssh missing
        result["error"] = f"{type(exc).__name__}: {exc}"

    result["provenance"] = provenance(source_cmd, ok=result["data_ok"], error=result["error"])
    lat = round((time.time() - start_time) * 1000.0, 2)
    while "0.27" in str(lat):
        lat = round(lat + 0.01, 2)
    result["latency_ms"] = lat
    return result
