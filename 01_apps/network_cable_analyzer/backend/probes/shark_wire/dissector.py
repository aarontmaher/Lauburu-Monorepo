"""
Pure Python Zero-Dependency Network Packet Dissector for Shark Wire.
Dissects Ethernet II, Darwin utun (DLT_NULL / raw IP), IPv4, IPv6, TCP, UDP, ICMP,
WireGuard (UDP 41641), Local AI RPC (Ports 8081-8084), SSH, and DNS.
Produces canonical packet dictionaries with collapsible protocol trees and hex dumps.
"""

import time
import json
import base64
import socket
import struct
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

# Known Lauburu Mesh Node Directory
MESH_IP_DIRECTORY: Dict[str, str] = {
    "100.119.199.76": "Mac_Node (L1)",
    "100.103.212.21": "MacBook_Pro (L2)",
    "100.101.39.98": "Linux_Mini (L3)",
    "100.81.92.125": "Linux_Tablet (L4)",
    "100.93.158.96": "MacBook_Air (L5)",
    "100.73.38.87": "Pixel_10_Pro_XL (L6)",
    "100.84.40.95": "Samsung_S20 (L7)",
    "100.99.123.58": "Samsung_S20 (L7 Alt)",
    "100.122.185.123": "GL.iNet Gateway",
    "192.168.8.1": "GL.iNet Gateway",
    "192.168.8.230": "Mac_Node (10GbE en0)",
    "192.168.8.127": "MacBook_Pro (L2 en0)",
    "192.168.8.224": "Linux_Mini (L3 LAN)",
    "192.168.8.222": "MacBook_Air (L5 Wi-Fi)",
    "169.254.187.138": "MacBook_Pro (TB4 DMA)",
    "192.168.2.2": "Mac_Node (TB4 bridge0)",
    "127.0.0.1": "localhost (L1 Host)",
}

AI_RPC_PORTS = {8081, 8082, 8083, 8084}


def format_hex_dump(data: bytes) -> str:
    """Format raw binary bytes into standard 16-byte offset hex + ASCII lines."""
    if not data:
        return ""
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i : i + 16]
        hex_bytes = [f"{b:02x}" for b in chunk]
        left_bytes = hex_bytes[:8]
        right_bytes = hex_bytes[8:]
        left_str = " ".join(left_bytes)
        right_str = " ".join(right_bytes)
        if right_str:
            hex_part = f"{left_str:<23}  {right_str:<23}"
        else:
            hex_part = f"{left_str:<23}"
        ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
        lines.append(f"{i:04x}  {hex_part:<48}  {ascii_part}")
    return "\n".join(lines)


def dissect_ethernet(data: bytes) -> Tuple[Dict[str, Any], int, bytes]:
    """
    Dissect 14-byte Ethernet II header.
    Returns (info_dict, ethertype, payload).
    """
    if len(data) < 14:
        return ({"error": "Truncated Ethernet frame", "length": len(data)}, 0, b"")
    dst_mac = ":".join(f"{b:02x}" for b in data[0:6])
    src_mac = ":".join(f"{b:02x}" for b in data[6:12])
    ethertype = struct.unpack(">H", data[12:14])[0]
    eth_type_name = "IPv4" if ethertype == 0x0800 else ("IPv6" if ethertype == 0x86DD else f"0x{ethertype:04x}")

    tree_node = {
        "name": f"Ethernet II, Src: {src_mac}, Dst: {dst_mac}",
        "expanded": False,
        "fields": [
            {"label": "Destination MAC", "value": dst_mac, "start": 0, "end": 6},
            {"label": "Source MAC", "value": src_mac, "start": 6, "end": 12},
            {"label": "Type", "value": f"{eth_type_name} (0x{ethertype:04x})", "start": 12, "end": 14},
        ],
    }
    return (
        {"src_mac": src_mac, "dst_mac": dst_mac, "ethertype": ethertype, "tree": tree_node},
        ethertype,
        data[14:],
    )


def dissect_darwin_utun(data: bytes) -> Tuple[Dict[str, Any], bytes]:
    """
    Dissect Darwin utun DLT_NULL 4-byte header or Raw IP frame.
    Returns (info_dict, ip_payload).
    """
    if len(data) < 4:
        return ({"error": "Truncated utun frame"}, data)

    # Check for 4-byte BSD AF family header
    af_le = struct.unpack("<I", data[:4])[0]
    af_be = struct.unpack(">I", data[:4])[0]
    
    # AF_INET is 2, AF_INET6 is 30 on Darwin
    if (af_le in (2, 30) or af_be in (2, 30)) and len(data) > 4 and ((data[4] >> 4) in (4, 6)):
        family = af_le if af_le in (2, 30) else af_be
        proto_name = "IPv4" if family == 2 else "IPv6"
        tree_node = {
            "name": f"Darwin utun DLT_NULL Tunnel Header (AF: {proto_name})",
            "expanded": False,
            "fields": [
                {"label": "Address Family", "value": f"{proto_name} ({family})", "start": 0, "end": 4},
            ],
        }
        return ({"header_len": 4, "family": family, "protocol": proto_name, "tree": tree_node}, data[4:])

    # Raw IP (starts directly with 0x45 or 0x60)
    version = data[0] >> 4
    if version in (4, 6):
        proto_name = "IPv4" if version == 4 else "IPv6"
        tree_node = {
            "name": f"Darwin utun Raw IP Framing ({proto_name})",
            "expanded": False,
            "fields": [
                {"label": "Framing", "value": f"Raw {proto_name} (No Link-Layer Header)", "start": 0, "end": 0},
            ],
        }
        return ({"header_len": 0, "family": 2 if version == 4 else 30, "protocol": proto_name, "tree": tree_node}, data)

    return ({"header_len": 0, "family": 0, "protocol": "Unknown"}, data)


def dissect_ipv4(data: bytes, base_offset: int = 14) -> Tuple[Dict[str, Any], int, bytes]:
    """
    Dissect IPv4 header.
    Returns (info_dict, protocol, payload).
    """
    if len(data) < 20:
        return ({"error": "Truncated IPv4 packet", "length": len(data)}, 0, b"")

    ver_ihl = data[0]
    version = ver_ihl >> 4
    ihl = (ver_ihl & 0x0F) * 4

    if version != 4 or ihl < 20 or len(data) < ihl:
        return ({"error": "Invalid IPv4 header"}, 0, b"")

    tos = data[1]
    tot_len = struct.unpack(">H", data[2:4])[0]
    ident = struct.unpack(">H", data[4:6])[0]
    flags_frag = struct.unpack(">H", data[6:8])[0]
    ttl = data[8]
    protocol = data[9]
    csum = struct.unpack(">H", data[10:12])[0]
    src_ip = socket.inet_ntoa(data[12:16])
    dst_ip = socket.inet_ntoa(data[16:20])

    df = bool(flags_frag & 0x4000)
    mf = bool(flags_frag & 0x2000)
    flags_str = "Don't fragment (DF)" if df else ("More fragments (MF)" if mf else "None")

    proto_names = {1: "ICMP", 6: "TCP", 17: "UDP"}
    proto_name = proto_names.get(protocol, f"Proto {protocol}")

    src_name = MESH_IP_DIRECTORY.get(src_ip, src_ip)
    dst_name = MESH_IP_DIRECTORY.get(dst_ip, dst_ip)

    tree_node = {
        "name": f"Internet Protocol Version 4, Src: {src_ip}, Dst: {dst_ip}",
        "expanded": False,
        "fields": [
            {"label": "Version", "value": "4", "start": base_offset, "end": base_offset + 1},
            {"label": "Header Length", "value": f"{ihl} bytes ({ihl // 4})", "start": base_offset, "end": base_offset + 1},
            {"label": "Total Length", "value": f"{tot_len} bytes", "start": base_offset + 2, "end": base_offset + 4},
            {"label": "Identification", "value": f"0x{ident:04x} ({ident})", "start": base_offset + 4, "end": base_offset + 6},
            {"label": "Flags", "value": f"0x{flags_frag >> 13:02x}, {flags_str}", "start": base_offset + 6, "end": base_offset + 8},
            {"label": "Time to Live (TTL)", "value": str(ttl), "start": base_offset + 8, "end": base_offset + 9},
            {"label": "Protocol", "value": f"{proto_name} ({protocol})", "start": base_offset + 9, "end": base_offset + 10},
            {"label": "Header Checksum", "value": f"0x{csum:04x}", "start": base_offset + 10, "end": base_offset + 12},
            {"label": "Source Address", "value": f"{src_ip} ({src_name})", "start": base_offset + 12, "end": base_offset + 16},
            {"label": "Destination Address", "value": f"{dst_ip} ({dst_name})", "start": base_offset + 16, "end": base_offset + 20},
        ],
    }

    payload = data[ihl:tot_len] if (tot_len >= ihl and tot_len <= len(data)) else data[ihl:]
    return (
        {
            "version": 4,
            "ihl": ihl,
            "total_len": tot_len,
            "ident": ident,
            "ttl": ttl,
            "protocol": protocol,
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "src_name": src_name,
            "dst_name": dst_name,
            "tree": tree_node,
        },
        protocol,
        payload,
    )


def dissect_ipv6(data: bytes, base_offset: int = 14) -> Tuple[Dict[str, Any], int, bytes]:
    """
    Dissect IPv6 40-byte fixed header.
    Returns (info_dict, next_header, payload).
    """
    if len(data) < 40:
        return ({"error": "Truncated IPv6 packet", "length": len(data)}, 0, b"")

    ver_tc_fl, plen, next_hdr, hlim, src_bytes, dst_bytes = struct.unpack(">IHBB16s16s", data[:40])
    version = ver_tc_fl >> 28
    src_ip = socket.inet_ntop(socket.AF_INET6, src_bytes)
    dst_ip = socket.inet_ntop(socket.AF_INET6, dst_bytes)

    proto_names = {1: "ICMPv6", 6: "TCP", 17: "UDP", 58: "ICMPv6"}
    proto_name = proto_names.get(next_hdr, f"NextHdr {next_hdr}")

    tree_node = {
        "name": f"Internet Protocol Version 6, Src: {src_ip}, Dst: {dst_ip}",
        "expanded": False,
        "fields": [
            {"label": "Version", "value": "6", "start": base_offset, "end": base_offset + 4},
            {"label": "Payload Length", "value": f"{plen} bytes", "start": base_offset + 4, "end": base_offset + 6},
            {"label": "Next Header", "value": f"{proto_name} ({next_hdr})", "start": base_offset + 6, "end": base_offset + 7},
            {"label": "Hop Limit", "value": str(hlim), "start": base_offset + 7, "end": base_offset + 8},
            {"label": "Source Address", "value": src_ip, "start": base_offset + 8, "end": base_offset + 24},
            {"label": "Destination Address", "value": dst_ip, "start": base_offset + 24, "end": base_offset + 40},
        ],
    }

    payload = data[40 : 40 + plen] if (plen > 0 and 40 + plen <= len(data)) else data[40:]
    return (
        {
            "version": 6,
            "next_header": next_hdr,
            "payload_len": plen,
            "hop_limit": hlim,
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "src_name": MESH_IP_DIRECTORY.get(src_ip, src_ip),
            "dst_name": MESH_IP_DIRECTORY.get(dst_ip, dst_ip),
            "tree": tree_node,
        },
        next_hdr,
        payload,
    )


def dissect_tcp(data: bytes, base_offset: int = 34) -> Tuple[Dict[str, Any], int, int, bytes]:
    """
    Dissect TCP segment.
    Returns (info_dict, src_port, dst_port, payload).
    """
    if len(data) < 20:
        return ({"error": "Truncated TCP segment"}, 0, 0, b"")

    src_port, dst_port, seq, ack, offset_flags, window, csum, urg = struct.unpack(">HHIIHHHH", data[:20])
    data_offset = (offset_flags >> 12) * 4
    flags = offset_flags & 0x01FF

    fin = bool(flags & 0x01)
    syn = bool(flags & 0x02)
    rst = bool(flags & 0x04)
    psh = bool(flags & 0x08)
    ack_f = bool(flags & 0x10)
    urg_f = bool(flags & 0x20)
    ece = bool(flags & 0x40)
    cwr = bool(flags & 0x80)

    flag_names = []
    if cwr: flag_names.append("CWR")
    if ece: flag_names.append("ECE")
    if urg_f: flag_names.append("URG")
    if ack_f: flag_names.append("ACK")
    if psh: flag_names.append("PSH")
    if rst: flag_names.append("RST")
    if syn: flag_names.append("SYN")
    if fin: flag_names.append("FIN")
    flags_summary = f"[{', '.join(flag_names)}]" if flag_names else "[None]"

    tree_node = {
        "name": f"Transmission Control Protocol, Src Port: {src_port}, Dst Port: {dst_port}, Seq: {seq}, Ack: {ack}",
        "expanded": False,
        "fields": [
            {"label": "Source Port", "value": str(src_port), "start": base_offset, "end": base_offset + 2},
            {"label": "Destination Port", "value": str(dst_port), "start": base_offset + 2, "end": base_offset + 4},
            {"label": "Sequence Number", "value": str(seq), "start": base_offset + 4, "end": base_offset + 8},
            {"label": "Acknowledgment Number", "value": str(ack), "start": base_offset + 8, "end": base_offset + 12},
            {"label": "Header Length", "value": f"{data_offset} bytes ({data_offset // 4})", "start": base_offset + 12, "end": base_offset + 13},
            {"label": "Flags", "value": f"0x{flags:03x} {flags_summary}", "start": base_offset + 12, "end": base_offset + 14},
            {"label": "Window", "value": str(window), "start": base_offset + 14, "end": base_offset + 16},
            {"label": "Checksum", "value": f"0x{csum:04x}", "start": base_offset + 16, "end": base_offset + 18},
        ],
    }

    payload = data[data_offset:] if data_offset >= 20 and data_offset <= len(data) else data[20:]
    return (
        {
            "src_port": src_port,
            "dst_port": dst_port,
            "seq": seq,
            "ack": ack,
            "window": window,
            "flags": flags,
            "flags_summary": flags_summary,
            "syn": syn,
            "ack_flag": ack_f,
            "psh": psh,
            "rst": rst,
            "fin": fin,
            "header_len": data_offset,
            "tree": tree_node,
        },
        src_port,
        dst_port,
        payload,
    )


def dissect_udp(data: bytes, base_offset: int = 34) -> Tuple[Dict[str, Any], int, int, bytes]:
    """
    Dissect UDP datagram.
    Returns (info_dict, src_port, dst_port, payload).
    """
    if len(data) < 8:
        return ({"error": "Truncated UDP datagram"}, 0, 0, b"")

    src_port, dst_port, length, csum = struct.unpack(">HHHH", data[:8])
    tree_node = {
        "name": f"User Datagram Protocol, Src Port: {src_port}, Dst Port: {dst_port}",
        "expanded": False,
        "fields": [
            {"label": "Source Port", "value": str(src_port), "start": base_offset, "end": base_offset + 2},
            {"label": "Destination Port", "value": str(dst_port), "start": base_offset + 2, "end": base_offset + 4},
            {"label": "Length", "value": str(length), "start": base_offset + 4, "end": base_offset + 6},
            {"label": "Checksum", "value": f"0x{csum:04x}", "start": base_offset + 6, "end": base_offset + 8},
        ],
    }

    payload = data[8:length] if length >= 8 and length <= len(data) else data[8:]
    return ({"src_port": src_port, "dst_port": dst_port, "length": length, "tree": tree_node}, src_port, dst_port, payload)


def dissect_icmp(data: bytes, base_offset: int = 34) -> Tuple[Dict[str, Any], bytes]:
    """
    Dissect ICMP packet.
    Returns (info_dict, payload).
    """
    if len(data) < 8:
        return ({"error": "Truncated ICMP packet"}, b"")

    i_type, i_code, csum, ident, seq = struct.unpack(">BBHHH", data[:8])
    type_name = "Echo Request" if i_type == 8 else ("Echo Reply" if i_type == 0 else f"Type {i_type}")

    tree_node = {
        "name": f"Internet Control Message Protocol ({type_name})",
        "expanded": False,
        "fields": [
            {"label": "Type", "value": f"{i_type} ({type_name})", "start": base_offset, "end": base_offset + 1},
            {"label": "Code", "value": str(i_code), "start": base_offset + 1, "end": base_offset + 2},
            {"label": "Checksum", "value": f"0x{csum:04x}", "start": base_offset + 2, "end": base_offset + 4},
            {"label": "Identifier", "value": f"0x{ident:04x} ({ident})", "start": base_offset + 4, "end": base_offset + 6},
            {"label": "Sequence Number", "value": str(seq), "start": base_offset + 6, "end": base_offset + 8},
        ],
    }
    return ({"type": i_type, "code": i_code, "type_name": type_name, "ident": ident, "seq": seq, "tree": tree_node}, data[8:])


def dissect_wireguard(data: bytes, base_offset: int = 42) -> Dict[str, Any]:
    """
    Dissect WireGuard packet on UDP 41641:
    - Type 1: Handshake Initiation (148 bytes)
    - Type 2: Handshake Response (92 bytes)
    - Type 3: Cookie Reply (64 bytes)
    - Type 4: Transport Data (>= 32 bytes)
    """
    if len(data) < 4:
        return {
            "type": "truncated",
            "info": "WireGuard Truncated (< 4 bytes)",
            "msg_type": 0,
            "tree": {
                "name": "WireGuard Protocol (Truncated)",
                "expanded": False,
                "fields": [{"label": "Error", "value": "Packet shorter than 4 bytes", "start": base_offset, "end": base_offset + len(data)}],
            },
        }

    msg_type = struct.unpack("<I", data[:4])[0]

    if msg_type == 1:
        # Handshake Initiation
        sender_index = struct.unpack("<I", data[4:8])[0] if len(data) >= 8 else 0
        ephemeral = data[8:40].hex() if len(data) >= 40 else ""
        static = data[40:88].hex() if len(data) >= 88 else ""
        timestamp = data[88:116].hex() if len(data) >= 116 else ""
        mac1 = data[116:132].hex() if len(data) >= 132 else ""
        mac2 = data[132:148].hex() if len(data) >= 148 else ""

        tree_node = {
            "name": "WireGuard Protocol (Mesh Layer 3 Overlay)",
            "expanded": True,
            "fields": [
                {"label": "Message Type", "value": "Handshake Initiation (1)", "start": base_offset, "end": base_offset + 4},
                {"label": "Sender Index", "value": f"0x{sender_index:08x}", "start": base_offset + 4, "end": base_offset + 8},
                {"label": "Unencrypted Ephemeral", "value": f"{ephemeral[:16]}... (32 bytes)", "start": base_offset + 8, "end": base_offset + 40},
                {"label": "Encrypted Static", "value": f"{static[:16]}... (48 bytes)", "start": base_offset + 40, "end": base_offset + 88},
                {"label": "Encrypted Timestamp", "value": f"{timestamp[:16]}... (28 bytes)", "start": base_offset + 88, "end": base_offset + 116},
                {"label": "MAC1", "value": f"{mac1[:16]}... (16 bytes)", "start": base_offset + 116, "end": base_offset + 132},
                {"label": "MAC2", "value": f"{mac2[:16]}... (16 bytes)", "start": base_offset + 132, "end": base_offset + 148},
            ],
        }
        return {
            "type": "handshake_init",
            "msg_type": 1,
            "sender_index": sender_index,
            "info": f"WireGuard Handshake Initiation (sender=0x{sender_index:08x})",
            "tree": tree_node,
        }

    elif msg_type == 2:
        # Handshake Response
        sender_index = struct.unpack("<I", data[4:8])[0] if len(data) >= 8 else 0
        receiver_index = struct.unpack("<I", data[8:12])[0] if len(data) >= 12 else 0
        ephemeral = data[12:44].hex() if len(data) >= 44 else ""
        tree_node = {
            "name": "WireGuard Protocol (Mesh Layer 3 Overlay)",
            "expanded": True,
            "fields": [
                {"label": "Message Type", "value": "Handshake Response (2)", "start": base_offset, "end": base_offset + 4},
                {"label": "Sender Index", "value": f"0x{sender_index:08x}", "start": base_offset + 4, "end": base_offset + 8},
                {"label": "Receiver Index", "value": f"0x{receiver_index:08x}", "start": base_offset + 8, "end": base_offset + 12},
                {"label": "Unencrypted Ephemeral", "value": f"{ephemeral[:16]}... (32 bytes)", "start": base_offset + 12, "end": base_offset + 44},
            ],
        }
        return {
            "type": "handshake_response",
            "msg_type": 2,
            "sender_index": sender_index,
            "receiver_index": receiver_index,
            "info": f"WireGuard Handshake Response (sender=0x{sender_index:08x}, receiver=0x{receiver_index:08x})",
            "tree": tree_node,
        }

    elif msg_type == 3:
        # Cookie Reply
        receiver_index = struct.unpack("<I", data[4:8])[0] if len(data) >= 8 else 0
        tree_node = {
            "name": "WireGuard Protocol (Mesh Layer 3 Overlay)",
            "expanded": True,
            "fields": [
                {"label": "Message Type", "value": "Cookie Reply (3)", "start": base_offset, "end": base_offset + 4},
                {"label": "Receiver Index", "value": f"0x{receiver_index:08x}", "start": base_offset + 4, "end": base_offset + 8},
            ],
        }
        return {
            "type": "cookie_reply",
            "msg_type": 3,
            "receiver_index": receiver_index,
            "info": f"WireGuard Cookie Reply (receiver=0x{receiver_index:08x})",
            "tree": tree_node,
        }

    elif msg_type == 4:
        # Transport Data
        receiver_index = struct.unpack("<I", data[4:8])[0] if len(data) >= 8 else 0
        counter = struct.unpack("<Q", data[8:16])[0] if len(data) >= 16 else 0
        payload_len = max(0, len(data) - 32)
        tree_node = {
            "name": "WireGuard Protocol (Mesh Layer 3 Overlay)",
            "expanded": True,
            "fields": [
                {"label": "Message Type", "value": "Transport Data (4)", "start": base_offset, "end": base_offset + 4},
                {"label": "Receiver Index", "value": f"0x{receiver_index:08x}", "start": base_offset + 4, "end": base_offset + 8},
                {"label": "Counter", "value": str(counter), "start": base_offset + 8, "end": base_offset + 16},
                {"label": "Encrypted Payload", "value": f"{payload_len} bytes", "start": base_offset + 16, "end": base_offset + len(data) - 16},
                {"label": "Authentication Tag", "value": "16 bytes Poly1305", "start": base_offset + len(data) - 16, "end": base_offset + len(data)},
            ],
        }
        return {
            "type": "transport_data",
            "msg_type": 4,
            "receiver_index": receiver_index,
            "counter": counter,
            "payload_len": payload_len,
            "info": f"WireGuard Data (receiver=0x{receiver_index:08x}, counter={counter}, {payload_len} bytes payload)",
            "tree": tree_node,
        }

    else:
        tree_node = {
            "name": "WireGuard Protocol (Unknown)",
            "expanded": False,
            "fields": [
                {"label": "Message Type", "value": f"Unknown (0x{msg_type:02x})", "start": base_offset, "end": base_offset + 4},
            ],
        }
        return {
            "type": "unknown",
            "msg_type": msg_type,
            "info": f"WireGuard Unknown Message Type 0x{msg_type:02x}",
            "tree": tree_node,
        }


def dissect_local_ai_rpc(data: bytes, port: int = 8082, base_offset: int = 54) -> Dict[str, Any]:
    """
    Dissect Local AI RPC frames on Ports 8081-8084:
    - HTTP/1.1 POST /v1/chat/completions (JSON parameters, model, stream)
    - HTTP/1.1 SSE delta tokens (data: {"choices": [{"delta": {"content": ...}}]})
    - HTTP/1.1 SSE stream finish token (data: [DONE])
    - HTTP/2 preface and 9-byte frame header
    """
    # HTTP/2 Check
    if data.startswith(b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"):
        frame_data = data[24:]
        if len(frame_data) >= 9:
            length = struct.unpack(">I", b"\x00" + frame_data[0:3])[0]
            f_type = frame_data[3]
            f_flags = frame_data[4]
            stream_id = struct.unpack(">I", frame_data[5:9])[0] & 0x7FFFFFFF
            type_names = {0: "DATA", 1: "HEADERS", 2: "PRIORITY", 3: "RST_STREAM", 4: "SETTINGS", 5: "PUSH_PROMISE", 6: "PING", 7: "GOAWAY"}
            type_name = type_names.get(f_type, f"TYPE_{f_type}")

            tree_node = {
                "name": f"HyperText Transfer Protocol 2 (HTTP/2 Frame: {type_name})",
                "expanded": True,
                "fields": [
                    {"label": "Connection Preface", "value": "PRI * HTTP/2.0... (24 bytes)", "start": base_offset, "end": base_offset + 24},
                    {"label": "Frame Length", "value": f"{length} bytes", "start": base_offset + 24, "end": base_offset + 27},
                    {"label": "Type", "value": f"{type_name} ({f_type})", "start": base_offset + 27, "end": base_offset + 28},
                    {"label": "Flags", "value": f"0x{f_flags:02x}", "start": base_offset + 28, "end": base_offset + 29},
                    {"label": "Stream ID", "value": str(stream_id), "start": base_offset + 29, "end": base_offset + 33},
                ],
            }
            return {
                "protocol": "HTTP/2",
                "type": "http2_frame",
                "frame_type": type_name,
                "stream_id": stream_id,
                "length": length,
                "info": f"HTTP/2 Frame: type={type_name}, stream_id={stream_id}, len={length}",
                "tree": tree_node,
            }

    # HTTP/1.1 SSE Stream Chunk Check
    if data.startswith(b"data: "):
        if data.startswith(b"data: [DONE]"):
            tree_node = {
                "name": "Local AI Server-Sent Events (SSE Stream Termination)",
                "expanded": True,
                "fields": [
                    {"label": "Token", "value": "[DONE]", "start": base_offset, "end": base_offset + len(data)},
                ],
            }
            return {
                "protocol": "AI-SSE",
                "type": "sse_done",
                "info": f"AI-SSE Stream [Port {port}] [DONE]",
                "tree": tree_node,
            }
        try:
            line = data.split(b"\n\n")[0]
            json_str = line[6:].decode("utf-8", errors="ignore")
            delta_obj = json.loads(json_str)
            content = delta_obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
            tree_node = {
                "name": f"Local AI Server-Sent Events (SSE Delta Token: '{content}')",
                "expanded": True,
                "fields": [
                    {"label": "Delta Content", "value": content, "start": base_offset, "end": base_offset + len(data)},
                ],
            }
            return {
                "protocol": "AI-SSE",
                "type": "sse_chunk",
                "delta": content,
                "info": f"AI-SSE Stream [Port {port}] chunk: '{content}'",
                "tree": tree_node,
            }
        except Exception:
            pass

    # HTTP/1.1 Request Check
    if data.startswith(b"POST ") or data.startswith(b"GET ") or data.startswith(b"HTTP/"):
        try:
            text = data.decode("utf-8", errors="ignore")
            lines = text.split("\r\n")
            req_line = lines[0]
            method = req_line.split(" ")[0] if " " in req_line else "HTTP"
            uri = req_line.split(" ")[1] if len(req_line.split(" ")) > 1 else ""

            model = ""
            stream = False
            if "\r\n\r\n" in text:
                body = text.split("\r\n\r\n", 1)[1]
                if body:
                    try:
                        body_json = json.loads(body)
                        model = body_json.get("model", "")
                        stream = body_json.get("stream", False)
                    except Exception:
                        pass

            tree_fields = [
                {"label": "Request Line", "value": req_line, "start": base_offset, "end": base_offset + len(lines[0])},
            ]
            if model:
                tree_fields.append({"label": "Target AI Model", "value": model, "start": base_offset, "end": base_offset + len(data)})
            if stream:
                tree_fields.append({"label": "Stream Mode", "value": "true", "start": base_offset, "end": base_offset + len(data)})

            tree_node = {
                "name": f"Local AI RPC (HTTP/1.1 {method} {uri})",
                "expanded": True,
                "fields": tree_fields,
            }
            info_str = f"AI-RPC [{method} {uri}] model={model or 'default'} stream={str(stream).lower()}"
            return {
                "protocol": "AI-RPC",
                "type": "http11_request",
                "method": method,
                "uri": uri,
                "model": model,
                "stream": stream,
                "info": info_str,
                "tree": tree_node,
            }
        except Exception:
            pass

    # Generic TCP payload on AI port
    return {
        "protocol": "AI-RPC",
        "type": "raw_payload",
        "info": f"AI-RPC Data Frame on Port {port} ({len(data)} bytes)",
        "tree": {
            "name": f"Local AI RPC Data (Port {port})",
            "expanded": False,
            "fields": [{"label": "Payload Length", "value": f"{len(data)} bytes", "start": base_offset, "end": base_offset + len(data)}],
        },
    }


def dissect_packet(
    raw_bytes: bytes,
    interface: str = "en0",
    timestamp: Optional[float] = None,
    index: int = 1,
    prev_timestamp: Optional[float] = None
) -> Dict[str, Any]:
    """
    Main entry point for full-stack packet dissection.
    Parses L2 to application layer and emits a unified canonical packet dictionary
    adhering to PROJECT.md § Interface Contracts.
    """
    if timestamp is None:
        timestamp = time.time()

    time_dt = datetime.fromtimestamp(timestamp)
    time_str = time_dt.strftime("%H:%M:%S") + f".{time_dt.microsecond:06d}"

    delta_time = 0.0
    if prev_timestamp is not None:
        delta_time = max(0.0, timestamp - prev_timestamp)

    pkt_len = len(raw_bytes)
    layers: List[str] = ["frame"]
    tree: List[Dict[str, Any]] = [
        {
            "name": f"Frame {index}: {pkt_len} bytes on interface {interface}",
            "expanded": False,
            "fields": [
                {"label": "Interface", "value": f"{interface}", "start": 0, "end": pkt_len},
                {"label": "Arrival Time", "value": f"{time_dt.strftime('%b %d, %Y %H:%M:%S')}.{time_dt.microsecond:06d} AEST", "start": 0, "end": pkt_len},
                {"label": "Frame Length", "value": f"{pkt_len} bytes ({pkt_len * 8} bits)", "start": 0, "end": pkt_len},
                {"label": "Captured Length", "value": f"{pkt_len} bytes ({pkt_len * 8} bits)", "start": 0, "end": pkt_len},
            ],
        }
    ]

    source = "--"
    destination = "--"
    source_name = None
    destination_name = None
    protocol = "Unknown"
    info = f"Raw packet ({pkt_len} bytes)"
    src_ip = ""
    dst_ip = ""
    src_port = None
    dst_port = None
    http_method = None
    tcp_flags_syn = 0

    # Truncated Frame Guard
    is_utun = interface.startswith("utun") or (len(raw_bytes) >= 1 and (raw_bytes[0] >> 4 in (4, 6)))
    if not is_utun and pkt_len < 14:
        return {
            "index": index,
            "timestamp": timestamp,
            "time_str": time_str,
            "delta_time": delta_time,
            "interface": interface,
            "length": pkt_len,
            "captured_length": pkt_len,
            "protocol": "Truncated",
            "source": "--",
            "destination": "--",
            "source_name": None,
            "destination_name": None,
            "info": f"Truncated Ethernet frame ({pkt_len} bytes < 14B header)",
            "layers": layers,
            "tree": tree,
            "hex_dump": format_hex_dump(raw_bytes),
            "raw_bytes_base64": base64.b64encode(raw_bytes).decode("ascii"),
            "raw_bytes": raw_bytes,
            "src_ip": "",
            "dst_ip": "",
            "src_port": None,
            "dst_port": None,
        }

    # Step 1: L2 Dissection (Ethernet or Darwin utun)
    ip_payload = b""
    ethertype = 0
    curr_offset = 0

    if is_utun:
        layers.append("utun")
        utun_res, ip_payload = dissect_darwin_utun(raw_bytes)
        if "tree" in utun_res:
            tree.append(utun_res["tree"])
        curr_offset = utun_res.get("header_len", 0)
        ethertype = 0x0800 if utun_res.get("family") == 2 else 0x86DD
    else:
        layers.append("eth")
        eth_res, ethertype, ip_payload = dissect_ethernet(raw_bytes)
        if "tree" in eth_res:
            tree.append(eth_res["tree"])
        source = eth_res.get("src_mac", "--")
        destination = eth_res.get("dst_mac", "--")
        curr_offset = 14

    # Step 2: L3 Dissection (IPv4 or IPv6)
    l4_payload = b""
    l4_proto = 0

    if ethertype == 0x0800 or (is_utun and len(ip_payload) > 0 and (ip_payload[0] >> 4 == 4)):
        layers.append("ipv4")
        protocol = "IPv4"
        ip4_res, l4_proto, l4_payload = dissect_ipv4(ip_payload, base_offset=curr_offset)
        if "error" not in ip4_res:
            if "tree" in ip4_res:
                tree.append(ip4_res["tree"])
            src_ip = ip4_res.get("src_ip", "")
            dst_ip = ip4_res.get("dst_ip", "")
            source = src_ip
            destination = dst_ip
            source_name = ip4_res.get("src_name")
            destination_name = ip4_res.get("dst_name")
            curr_offset += ip4_res.get("ihl", 20)
            info = f"IPv4 from {src_ip} to {dst_ip}"
        else:
            protocol = "IPv4 (Truncated)"
            info = "Truncated IPv4 header"

    elif ethertype == 0x86DD or (is_utun and len(ip_payload) > 0 and (ip_payload[0] >> 4 == 6)):
        layers.append("ipv6")
        protocol = "IPv6"
        ip6_res, l4_proto, l4_payload = dissect_ipv6(ip_payload, base_offset=curr_offset)
        if "error" not in ip6_res:
            if "tree" in ip6_res:
                tree.append(ip6_res["tree"])
            src_ip = ip6_res.get("src_ip", "")
            dst_ip = ip6_res.get("dst_ip", "")
            source = src_ip
            destination = dst_ip
            source_name = ip6_res.get("src_name")
            destination_name = ip6_res.get("dst_name")
            curr_offset += 40
            info = f"IPv6 from {src_ip} to {dst_ip}"
        else:
            protocol = "IPv6 (Truncated)"
            info = "Truncated IPv6 header"

    # Step 3: L4 Dissection (TCP, UDP, ICMP)
    app_payload = b""

    if l4_proto == 6:  # TCP
        layers.append("tcp")
        protocol = "TCP"
        tcp_res, src_port, dst_port, app_payload = dissect_tcp(l4_payload, base_offset=curr_offset)
        if "error" not in tcp_res:
            if "tree" in tcp_res:
                tree.append(tcp_res["tree"])
            source = f"{src_ip}:{src_port}" if src_ip else f"{src_port}"
            destination = f"{dst_ip}:{dst_port}" if dst_ip else f"{dst_port}"
            tcp_flags_syn = 1 if tcp_res.get("syn") else 0
            curr_offset += tcp_res.get("header_len", 20)
            flags_summary = tcp_res.get("flags_summary", "")
            seq = tcp_res.get("seq", 0)
            ack = tcp_res.get("ack", 0)
            win = tcp_res.get("window", 0)
            info = f"{src_port} -> {dst_port} {flags_summary} Seq={seq} Ack={ack} Win={win} Len={len(app_payload)}"

            # Step 4a: Local AI RPC Inspection (Ports 8081-8084)
            if src_port in AI_RPC_PORTS or dst_port in AI_RPC_PORTS:
                ai_port = dst_port if dst_port in AI_RPC_PORTS else src_port
                layers.append("airpc")
                ai_res = dissect_local_ai_rpc(app_payload, port=ai_port, base_offset=curr_offset)
                protocol = ai_res.get("protocol", "AI-RPC")
                info = ai_res.get("info", info)
                http_method = ai_res.get("method")
                if "tree" in ai_res:
                    tree.append(ai_res["tree"])

            # Step 4b: SSH Inspection (Ports 22, 8022)
            elif src_port in (22, 8022) or dst_port in (22, 8022):
                layers.append("ssh")
                protocol = "SSH"
                if app_payload.startswith(b"SSH-"):
                    banner = app_payload.split(b"\r\n")[0].decode("utf-8", errors="ignore")
                    info = f"SSH Banner: {banner}"
                else:
                    info = f"SSH Protocol Data ({len(app_payload)} bytes)"

    elif l4_proto == 17:  # UDP
        layers.append("udp")
        protocol = "UDP"
        udp_res, src_port, dst_port, app_payload = dissect_udp(l4_payload, base_offset=curr_offset)
        if "error" not in udp_res:
            if "tree" in udp_res:
                tree.append(udp_res["tree"])
            source = f"{src_ip}:{src_port}" if src_ip else f"{src_port}"
            destination = f"{dst_ip}:{dst_port}" if dst_ip else f"{dst_port}"
            curr_offset += 8
            info = f"UDP {src_port} -> {dst_port} Len={len(app_payload)}"

            # Step 4c: WireGuard Inspection (UDP Port 41641)
            if src_port == 41641 or dst_port == 41641:
                layers.append("wireguard")
                protocol = "WireGuard"
                wg_res = dissect_wireguard(app_payload, base_offset=curr_offset)
                info = wg_res.get("info", info)
                if "tree" in wg_res:
                    tree.append(wg_res["tree"])

            # Step 4d: DNS Inspection (Port 53)
            elif src_port == 53 or dst_port == 53:
                layers.append("dns")
                protocol = "DNS"
                info = f"DNS Standard query/response ({len(app_payload)} bytes)"

    elif l4_proto == 1:  # ICMP
        layers.append("icmp")
        protocol = "ICMP"
        icmp_res, app_payload = dissect_icmp(l4_payload, base_offset=curr_offset)
        if "error" not in icmp_res:
            if "tree" in icmp_res:
                tree.append(icmp_res["tree"])
            t_name = icmp_res.get("type_name", "Echo")
            seq = icmp_res.get("seq", 0)
            ident = icmp_res.get("ident", 0)
            info = f"ICMP {t_name} id=0x{ident:04x}, seq={seq}"

    return {
        "index": index,
        "timestamp": timestamp,
        "time_str": time_str,
        "delta_time": delta_time,
        "interface": interface,
        "length": pkt_len,
        "captured_length": pkt_len,
        "protocol": protocol,
        "source": source,
        "destination": destination,
        "source_name": source_name,
        "destination_name": destination_name,
        "info": info,
        "layers": layers,
        "tree": tree,
        "hex_dump": format_hex_dump(raw_bytes),
        "raw_bytes_base64": base64.b64encode(raw_bytes).decode("ascii"),
        "raw_bytes": raw_bytes,
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "src_port": src_port,
        "dst_port": dst_port,
        "http_method": http_method,
        "tcp_flags_syn": tcp_flags_syn,
    }
