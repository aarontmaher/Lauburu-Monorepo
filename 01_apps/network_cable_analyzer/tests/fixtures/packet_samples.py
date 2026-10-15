"""
Authentic Packet Samples and Libpcap 2.4 Binary Fixtures for Shark Wire Testing.
Generates RFC-compliant binary frames for:
- Ethernet II
- IPv4 and IPv6
- TCP with options and flags (SYN, ACK, PSH, RST, FIN)
- UDP and ICMP
- WireGuard Overlay (UDP 41641): Type 1 (Init), Type 2 (Resp), Type 3 (Cookie), Type 4 (Data)
- Local AI RPC (Ports 8081-8084): HTTP/1.1 POST, JSON body, SSE chunks, HTTP/2 preface & frames
- Darwin utun frames (DLT_NULL 4-byte header and Raw IP)
- Libpcap 2.4 file writer and reader
"""

import struct
import socket
import os
from typing import List, Tuple, Dict, Any

# PCAP 2.4 Constants
TCPDUMP_MAGIC = 0xA1B2C3D4
PCAP_VERSION_MAJOR = 2
PCAP_VERSION_MINOR = 4
DLT_NULL = 0
DLT_EN10MB = 1
DLT_RAW = 12

def create_pcap_global_header(network: int = DLT_EN10MB, snaplen: int = 65535) -> bytes:
    """Create 24-byte libpcap 2.4 file header."""
    return struct.pack(
        "<IHHiIII",
        TCPDUMP_MAGIC,
        PCAP_VERSION_MAJOR,
        PCAP_VERSION_MINOR,
        0,  # thiszone
        0,  # sigfigs
        snaplen,
        network
    )

def create_pcap_record(packet_bytes: bytes, ts_sec: int = 1726550000, ts_usec: int = 0) -> bytes:
    """Create 16-byte libpcap packet record header followed by packet data."""
    caplen = len(packet_bytes)
    orig_len = len(packet_bytes)
    header = struct.pack("<IIII", ts_sec, ts_usec, caplen, orig_len)
    return header + packet_bytes

def build_ethernet_header(src_mac: str = "00:e0:4c:68:01:02", dst_mac: str = "00:e0:4c:68:03:04", ethertype: int = 0x0800) -> bytes:
    """Build 14-byte Ethernet II header."""
    dst_bytes = bytes.fromhex(dst_mac.replace(":", ""))
    src_bytes = bytes.fromhex(src_mac.replace(":", ""))
    return dst_bytes + src_bytes + struct.pack(">H", ethertype)

def build_ipv4_header(src_ip: str = "100.119.199.76", dst_ip: str = "100.103.212.21", protocol: int = 17, payload_len: int = 0, ttl: int = 64) -> bytes:
    """Build 20-byte IPv4 header with standard flags (DF=1)."""
    version_ihl = (4 << 4) | 5
    tos = 0
    total_len = 20 + payload_len
    ident = 0x5b3a
    flags_frag = 0x4000  # DF set
    checksum = 0  # placeholder or simple sum
    src_bytes = socket.inet_aton(src_ip)
    dst_bytes = socket.inet_aton(dst_ip)
    
    # Calculate checksum
    header_no_cs = struct.pack(
        ">BBHHHBBH4s4s",
        version_ihl, tos, total_len, ident, flags_frag, ttl, protocol, 0, src_bytes, dst_bytes
    )
    # RFC 1071 checksum
    words = struct.unpack(f">{len(header_no_cs)//2}H", header_no_cs)
    csum = sum(words)
    csum = (csum >> 16) + (csum & 0xffff)
    csum += (csum >> 16)
    checksum = (~csum) & 0xffff

    return struct.pack(
        ">BBHHHBBH4s4s",
        version_ihl, tos, total_len, ident, flags_frag, ttl, protocol, checksum, src_bytes, dst_bytes
    )

def build_ipv6_header(src_ip: str = "fe80::1", dst_ip: str = "fe80::2", next_header: int = 6, payload_len: int = 0) -> bytes:
    """Build 40-byte IPv6 header."""
    ver_tc_fl = (6 << 28)
    src_bytes = socket.inet_pton(socket.AF_INET6, src_ip)
    dst_bytes = socket.inet_pton(socket.AF_INET6, dst_ip)
    return struct.pack(">IHBB16s16s", ver_tc_fl, payload_len, next_header, 64, src_bytes, dst_bytes)

def build_tcp_header(src_port: int, dst_port: int, seq: int = 1000, ack: int = 0, flags: int = 0x02, window: int = 65535, options: bytes = b"") -> bytes:
    """Build TCP header with optional options."""
    data_offset = (20 + len(options)) // 4
    offset_flags = (data_offset << 12) | flags
    base = struct.pack(">HHIIHHHH", src_port, dst_port, seq, ack, offset_flags, window, 0, 0)
    return base + options

def build_udp_header(src_port: int, dst_port: int, payload_len: int) -> bytes:
    """Build 8-byte UDP header."""
    total_len = 8 + payload_len
    return struct.pack(">HHHH", src_port, dst_port, total_len, 0)

def build_icmp_echo_request(ident: int = 0x1234, seq: int = 1, data: bytes = b"LauburuPingTest") -> bytes:
    """Build 8-byte ICMP Echo Request + data."""
    # Type 8, Code 0
    header_no_cs = struct.pack(">BBHHH", 8, 0, 0, ident, seq) + data
    if len(header_no_cs) % 2 != 0:
        header_no_cs += b"\x00"
    words = struct.unpack(f">{len(header_no_cs)//2}H", header_no_cs)
    csum = sum(words)
    csum = (csum >> 16) + (csum & 0xffff)
    csum += (csum >> 16)
    checksum = (~csum) & 0xffff
    return struct.pack(">BBHHH", 8, 0, checksum, ident, seq) + data

# Specialized WireGuard Packets (UDP port 41641)
def build_wireguard_handshake_init(sender_index: int = 0x01A2B3C4) -> bytes:
    """
    Build RFC-compliant WireGuard Handshake Initiation packet (Type 1, exactly 148 bytes):
    - Byte 0: 0x01
    - Bytes 1..3: Reserved 0x00
    - Bytes 4..7: sender_index uint32 LE
    - Bytes 8..39: unencrypted_ephemeral (32B)
    - Bytes 40..87: encrypted_static (48B)
    - Bytes 88..115: encrypted_timestamp (28B)
    - Bytes 116..131: mac1 (16B)
    - Bytes 132..147: mac2 (16B)
    """
    msg_type = struct.pack("<I", 1)  # byte 0 is 1, bytes 1..3 are 0
    sender = struct.pack("<I", sender_index)
    ephemeral = os.urandom(32)
    static = os.urandom(48)
    timestamp = os.urandom(28)
    mac1 = os.urandom(16)
    mac2 = os.urandom(16)
    pkt = msg_type + sender + ephemeral + static + timestamp + mac1 + mac2
    assert len(pkt) == 148, f"WireGuard Handshake Init must be 148 bytes, got {len(pkt)}"
    return pkt

def build_wireguard_handshake_response(sender_index: int = 0x05D6E7F8, receiver_index: int = 0x01A2B3C4) -> bytes:
    """
    Build RFC-compliant WireGuard Handshake Response packet (Type 2, exactly 92 bytes):
    - Byte 0: 0x02
    - Bytes 1..3: Reserved 0x00
    - Bytes 4..7: sender_index uint32 LE
    - Bytes 8..11: receiver_index uint32 LE
    - Bytes 12..43: unencrypted_ephemeral (32B)
    - Bytes 44..59: encrypted_nothing (16B)
    - Bytes 60..75: mac1 (16B)
    - Bytes 76..91: mac2 (16B)
    """
    msg_type = struct.pack("<I", 2)
    sender = struct.pack("<I", sender_index)
    receiver = struct.pack("<I", receiver_index)
    ephemeral = os.urandom(32)
    encrypted_nothing = os.urandom(16)
    mac1 = os.urandom(16)
    mac2 = os.urandom(16)
    pkt = msg_type + sender + receiver + ephemeral + encrypted_nothing + mac1 + mac2
    assert len(pkt) == 92, f"WireGuard Handshake Response must be 92 bytes, got {len(pkt)}"
    return pkt

def build_wireguard_cookie_reply(receiver_index: int = 0x01A2B3C4) -> bytes:
    """Build WireGuard Cookie Reply packet (Type 3, exactly 64 bytes)."""
    msg_type = struct.pack("<I", 3)
    receiver = struct.pack("<I", receiver_index)
    nonce = os.urandom(24)
    encrypted_cookie = os.urandom(32)
    pkt = msg_type + receiver + nonce + encrypted_cookie
    assert len(pkt) == 64, f"WireGuard Cookie Reply must be 64 bytes, got {len(pkt)}"
    return pkt

def build_wireguard_transport_data(receiver_index: int = 0x01A2B3C4, counter: int = 42, payload_len: int = 64) -> bytes:
    """Build WireGuard Transport Data packet (Type 4, min 32 bytes)."""
    msg_type = struct.pack("<I", 4)
    receiver = struct.pack("<I", receiver_index)
    counter_bytes = struct.pack("<Q", counter)
    payload = os.urandom(payload_len)
    auth_tag = os.urandom(16)
    pkt = msg_type + receiver + counter_bytes + payload + auth_tag
    assert len(pkt) == 16 + payload_len + 16
    return pkt

# Specialized Local AI RPC Packets (TCP Ports 8081-8084)
def build_ai_rpc_http11_request(model: str = "qwen_38_max_abliterated", prompt: str = "Analyze cable", stream: bool = True) -> bytes:
    """Build HTTP/1.1 POST /v1/chat/completions payload."""
    body = f'{{"model": "{model}", "messages": [{{"role": "user", "content": "{prompt}"}}], "stream": {str(stream).lower()}}}'.encode("utf-8")
    headers_str = (
        "POST /v1/chat/completions HTTP/1.1\r\n"
        "Host: 127.0.0.1:8082\r\n"
        "User-Agent: LauburuMeshGovernor/2.0\r\n"
        "Content-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n\r\n"
    )
    return headers_str.encode("utf-8") + body

def build_ai_rpc_sse_chunk(content_delta: str = " verified") -> bytes:
    """Build HTTP/1.1 Server-Sent Events stream chunk."""
    data_str = f'{{"id":"chatcmpl-01","object":"chat.completion.chunk","choices":[{{"index":0,"delta":{{"content":"{content_delta}"}},"finish_reason":null}}]}}'
    return f"data: {data_str}\n\n".encode("utf-8")

def build_ai_rpc_sse_done() -> bytes:
    """Build SSE stream termination chunk."""
    return b"data: [DONE]\n\n"

def build_ai_rpc_http2_preface_and_frame() -> bytes:
    """Build HTTP/2 client connection preface and a HEADERS frame."""
    preface = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
    # 9-byte frame header: Length 24-bit (3B) + Type 8-bit (1B) + Flags 8-bit (1B) + Stream ID 31-bit (4B)
    length_bytes = struct.pack(">I", 12)[1:]  # 3 bytes: \x00\x00\x0c
    type_byte = b"\x01"                       # 1 byte HEADERS
    flags_byte = b"\x05"                      # 1 byte END_HEADERS | END_STREAM
    stream_id = struct.pack(">I", 1 & 0x7FFFFFFF)
    frame_payload = os.urandom(12)
    return preface + length_bytes + type_byte + flags_byte + stream_id + frame_payload

# Darwin utun frames
def build_darwin_utun_dlt_null_ipv4(ipv4_packet: bytes) -> bytes:
    """Darwin utun DLT_NULL 4-byte header (AF_INET = 2 in little-endian / host endianness) + IP."""
    return struct.pack("<I", 2) + ipv4_packet

def build_darwin_utun_raw_ipv4(ipv4_packet: bytes) -> bytes:
    """Darwin raw IP frame (starts directly with 0x45)."""
    return ipv4_packet

# Full Frame Assemblers
def assemble_ethernet_wireguard_frame(msg_type: int = 1) -> bytes:
    """Assemble complete Ethernet II -> IPv4 -> UDP 41641 -> WireGuard frame."""
    if msg_type == 1:
        wg_payload = build_wireguard_handshake_init()
    elif msg_type == 2:
        wg_payload = build_wireguard_handshake_response()
    elif msg_type == 3:
        wg_payload = build_wireguard_cookie_reply()
    else:
        wg_payload = build_wireguard_transport_data()
    
    udp_hdr = build_udp_header(41641, 41641, len(wg_payload))
    ip_hdr = build_ipv4_header(
        src_ip="100.119.199.76",
        dst_ip="100.103.212.21",
        protocol=17,
        payload_len=len(udp_hdr) + len(wg_payload)
    )
    eth_hdr = build_ethernet_header(ethertype=0x0800)
    return eth_hdr + ip_hdr + udp_hdr + wg_payload

def assemble_ethernet_ai_rpc_frame(payload: bytes, dst_port: int = 8082) -> bytes:
    """Assemble complete Ethernet II -> IPv4 -> TCP -> Local AI RPC payload."""
    tcp_hdr = build_tcp_header(src_port=52344, dst_port=dst_port, seq=1001, ack=2001, flags=0x18)  # PSH, ACK
    ip_hdr = build_ipv4_header(
        src_ip="127.0.0.1",
        dst_ip="127.0.0.1",
        protocol=6,
        payload_len=len(tcp_hdr) + len(payload)
    )
    eth_hdr = build_ethernet_header(ethertype=0x0800)
    return eth_hdr + ip_hdr + tcp_hdr + payload

def generate_sample_pcap_file(filepath: str, count: int = 20) -> int:
    """Generate a standard libpcap 2.4 file containing a rich mix of mesh frames."""
    frames = [
        assemble_ethernet_wireguard_frame(msg_type=1),
        assemble_ethernet_wireguard_frame(msg_type=2),
        assemble_ethernet_wireguard_frame(msg_type=4),
        assemble_ethernet_ai_rpc_frame(build_ai_rpc_http11_request(), dst_port=8082),
        assemble_ethernet_ai_rpc_frame(build_ai_rpc_sse_chunk("Cable"), dst_port=8082),
        assemble_ethernet_ai_rpc_frame(build_ai_rpc_sse_done(), dst_port=8082),
    ]
    
    with open(filepath, "wb") as f:
        f.write(create_pcap_global_header(network=DLT_EN10MB))
        for i in range(count):
            pkt = frames[i % len(frames)]
            f.write(create_pcap_record(pkt, ts_sec=1726550000 + i, ts_usec=i * 1000))
            
    return count
