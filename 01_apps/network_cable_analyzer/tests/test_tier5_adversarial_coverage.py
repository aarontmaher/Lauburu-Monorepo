"""
Tier 5 White-Box Coverage & Adversarial Hardening Test Suite.
Milestone M4 Challenger 1 Implementation.

Adversarial Stress Testing & Attack Vectors:
1. Boundary Packet Sizes (MTU 1500, Jumbo 9000, Runt < 14B, 0-byte frames)
2. Malformed WireGuard Frames on UDP 41641 (unsupported types, truncated handshake, truncated data)
3. Local AI RPC Edge Cases on Ports 8081-8084 (partial HTTP chunks, malformed SSE deltas, HTTP/2 frames)
4. Filter Syntax Stress & Fuzzing (deep nesting, unbalanced parens, unicode, unknown fields, code injection)
5. Ring Buffer High-Throughput Stress (10,000 rapid concurrent bursts, clear while exporting PCAP)
6. WhatCable Hardware Edge Cases (unknown vendor IDs, unusual DP lane rates, negative headroom alerts)
7. Server Endpoint Adversarial Invocations (FastAPI REST and SSE boundary robustness)

Adheres strictly to Rule 1 (Zero-Mock Truth Verification) and PROJECT.md Interface Contracts.
"""

import os
import sys
import time
import json
import struct
import socket
import threading
from pathlib import Path
from typing import Dict, Any, List
import pytest

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from probes.shark_wire.ring_buffer import SharkWireRingBuffer, TCPDUMP_MAGIC
from probes.shark_wire.filter import SharkWireFilter
from probes.shark_wire.interfaces import discover_darwin_interfaces
from probes.shark_wire.dissector import (
    dissect_packet,
    dissect_ethernet,
    dissect_ipv4,
    dissect_ipv6,
    dissect_tcp,
    dissect_udp,
    dissect_icmp,
    dissect_wireguard,
    dissect_local_ai_rpc,
    dissect_darwin_utun,
    format_hex_dump,
)
from probes.whatcable_inspector import (
    resolve_vendor_name,
    detect_display_bottleneck,
    detect_cable_bottleneck,
    detect_cable_bottlenecks,
    parse_displayport_alt_mode,
    parse_power_delivery,
    parse_speed_to_gbps,
    probe_whatcable_hardware_details,
)
from server import app
from starlette.testclient import TestClient

from .fixtures.packet_samples import (
    build_ethernet_header,
    build_ipv4_header,
    build_ipv6_header,
    build_tcp_header,
    build_udp_header,
    build_icmp_echo_request,
    build_wireguard_handshake_init,
    build_wireguard_handshake_response,
    build_wireguard_cookie_reply,
    build_wireguard_transport_data,
    build_ai_rpc_http11_request,
    build_ai_rpc_sse_chunk,
    build_ai_rpc_sse_done,
    build_ai_rpc_http2_preface_and_frame,
    assemble_ethernet_wireguard_frame,
    assemble_ethernet_ai_rpc_frame,
)


# ============================================================================
# Class 1: Boundary Packet Sizes (MTU 1500, Jumbo 9000, Runt < 14B, 0-byte)
# ============================================================================

class TestTier5BoundaryPacketSizes:
    """Stress-test packet dissector under boundary packet dimensions and runt frames."""

    def test_t5_boundary_zero_byte_frame_en0(self):
        """0-byte frame on Ethernet interface must not crash and return truncated frame dict."""
        pkt = dissect_packet(b"", interface="en0", index=1)
        assert isinstance(pkt, dict)
        assert pkt["length"] == 0
        assert pkt["protocol"] == "Truncated"
        assert "Truncated" in pkt["info"]
        assert pkt["hex_dump"] == ""
        assert pkt["raw_bytes_base64"] == ""
        assert pkt["source"] == "--"
        assert pkt["destination"] == "--"

    def test_t5_boundary_zero_byte_frame_utun(self):
        """0-byte frame on Darwin utun interface must not crash."""
        pkt = dissect_packet(b"", interface="utun3", index=2)
        assert isinstance(pkt, dict)
        assert pkt["length"] == 0
        assert "Truncated" in pkt["protocol"] or pkt["protocol"] == "Unknown"
        assert isinstance(pkt["layers"], list)
        assert isinstance(pkt["tree"], list)

    def test_t5_boundary_single_byte_runt(self):
        """1-byte runt frame must be handled safely without struct.error."""
        pkt = dissect_packet(b"\x00", interface="en0", index=3)
        assert pkt["length"] == 1
        assert pkt["captured_length"] == 1
        assert "Truncated" in pkt["protocol"] or "Truncated" in pkt["info"]
        assert len(pkt["hex_dump"]) > 0

    @pytest.mark.parametrize("runt_len", [2, 5, 7, 10, 12, 13])
    def test_t5_boundary_sub_14_byte_runt_frames(self, runt_len: int):
        """Sub-14 byte runt frames (< Ethernet II header) must not raise unhandled exceptions."""
        raw_runt = b"\xff" * runt_len
        pkt = dissect_packet(raw_runt, interface="en0", index=10 + runt_len)
        assert pkt["length"] == runt_len
        assert isinstance(pkt["tree"], list)
        assert len(pkt["tree"]) >= 1

    def test_t5_boundary_exact_14_byte_ethernet_header_no_payload(self):
        """Exact 14-byte Ethernet frame with zero payload bytes."""
        raw_eth = build_ethernet_header(src_mac="00:11:22:33:44:55", dst_mac="00:e0:4c:68:03:04", ethertype=0x0800)
        assert len(raw_eth) == 14
        pkt = dissect_packet(raw_eth, interface="en0", index=20)
        assert pkt["length"] == 14
        assert "eth" in pkt["layers"]
        # IPv4 with 0 bytes payload is flagged as IPv4 (Truncated)
        assert pkt["protocol"] == "IPv4 (Truncated)"
        assert pkt["source"] == "00:11:22:33:44:55" or pkt["source"] == "00:e0:4c:68:03:04" or pkt["source"] == "--"

    def test_t5_boundary_standard_mtu_1500_frame(self):
        """Full standard MTU 1500 frame (1514 bytes on the wire: 14B Eth + 20B IP + 8B UDP + 1472B Data)."""
        udp_payload = os.urandom(1472)
        udp_hdr = build_udp_header(src_port=5000, dst_port=6000, payload_len=len(udp_payload))
        ip_hdr = build_ipv4_header(src_ip="192.168.8.230", dst_ip="192.168.8.1", protocol=17, payload_len=len(udp_hdr) + len(udp_payload))
        eth_hdr = build_ethernet_header()
        raw_frame = eth_hdr + ip_hdr + udp_hdr + udp_payload
        assert len(raw_frame) == 1514

        pkt = dissect_packet(raw_frame, interface="en0", index=21)
        assert pkt["length"] == 1514
        assert pkt["protocol"] == "UDP"
        assert "ipv4" in pkt["layers"]
        assert "udp" in pkt["layers"]
        assert pkt["src_port"] == 5000
        assert pkt["dst_port"] == 6000

    def test_t5_boundary_jumbo_9000_frame(self):
        """Full Jumbo frame (9014 bytes on the wire: 14B Eth + 20B IP + 20B TCP + 8960B Data)."""
        tcp_payload = os.urandom(8960)
        tcp_hdr = build_tcp_header(src_port=8080, dst_port=9000, seq=1000, flags=0x18)
        ip_hdr = build_ipv4_header(src_ip="100.119.199.76", dst_ip="100.103.212.21", protocol=6, payload_len=len(tcp_hdr) + len(tcp_payload))
        eth_hdr = build_ethernet_header()
        raw_jumbo = eth_hdr + ip_hdr + tcp_hdr + tcp_payload
        assert len(raw_jumbo) == 9014

        pkt = dissect_packet(raw_jumbo, interface="bridge0", index=22)
        assert pkt["length"] == 9014
        assert pkt["protocol"] == "TCP"
        assert "tcp" in pkt["layers"]
        assert pkt["src_port"] == 8080
        assert pkt["dst_port"] == 9000

    def test_t5_boundary_extreme_oversized_65535_frame(self):
        """Extreme 65,535-byte oversized frame must not cause buffer overflow or crash."""
        oversized = b"\x45\x00\xff\xff" + b"\x00" * (65535 - 4)
        pkt = dissect_packet(oversized, interface="utun3", index=23)
        assert pkt["length"] == 65535
        assert isinstance(pkt["hex_dump"], str)
        assert len(pkt["hex_dump"]) > 0


# ============================================================================
# Class 2: Malformed WireGuard Frames on UDP 41641
# ============================================================================

class TestTier5MalformedWireGuardFrames:
    """Stress-test WireGuard overlay dissector with truncated, corrupt, and unknown frames."""

    @pytest.mark.parametrize("sub_len", [0, 1, 2, 3])
    def test_t5_wg_truncated_under_4_bytes(self, sub_len: int):
        """WireGuard packet shorter than 4-byte message type header."""
        res = dissect_wireguard(b"\x01\x02\x03"[:sub_len])
        assert res["type"] == "truncated"
        assert "Truncated" in res["info"]
        assert res["msg_type"] == 0

    @pytest.mark.parametrize("bad_type", [0, 5, 6, 99, 255, 0xFFFF, 0x7FFFFFFF])
    def test_t5_wg_unsupported_message_types(self, bad_type: int):
        """Unsupported or invalid WireGuard message types (valid types are 1..4)."""
        payload = struct.pack("<I", bad_type) + os.urandom(40)
        res = dissect_wireguard(payload)
        assert res["type"] == "unknown"
        assert res["msg_type"] == bad_type
        assert "Unknown Message Type" in res["info"]
        assert "tree" in res

    @pytest.mark.parametrize("trunc_len", [4, 8, 20, 40, 88, 116, 147])
    def test_t5_wg_handshake_init_truncated_sub_148_bytes(self, trunc_len: int):
        """WireGuard Handshake Initiation (Type 1) truncated to less than 148 bytes."""
        payload = struct.pack("<I", 1) + os.urandom(trunc_len - 4)
        res = dissect_wireguard(payload)
        assert res["type"] == "handshake_init"
        assert res["msg_type"] == 1
        assert "Handshake Initiation" in res["info"]
        assert "tree" in res
        assert isinstance(res["tree"]["fields"], list)

    @pytest.mark.parametrize("trunc_len", [4, 8, 12, 44, 60, 91])
    def test_t5_wg_handshake_response_truncated_sub_92_bytes(self, trunc_len: int):
        """WireGuard Handshake Response (Type 2) truncated to less than 92 bytes."""
        payload = struct.pack("<I", 2) + os.urandom(trunc_len - 4)
        res = dissect_wireguard(payload)
        assert res["type"] == "handshake_response"
        assert res["msg_type"] == 2
        assert "Handshake Response" in res["info"]
        assert "tree" in res

    @pytest.mark.parametrize("trunc_len", [4, 8, 24, 48, 63])
    def test_t5_wg_cookie_reply_truncated_sub_64_bytes(self, trunc_len: int):
        """WireGuard Cookie Reply (Type 3) truncated to less than 64 bytes."""
        payload = struct.pack("<I", 3) + os.urandom(trunc_len - 4)
        res = dissect_wireguard(payload)
        assert res["type"] == "cookie_reply"
        assert res["msg_type"] == 3
        assert "Cookie Reply" in res["info"]

    @pytest.mark.parametrize("trunc_len", [4, 8, 16, 24, 31])
    def test_t5_wg_transport_data_truncated_sub_32_bytes(self, trunc_len: int):
        """WireGuard Transport Data (Type 4) with less than minimum 32 bytes (16B header + 16B Poly1305 tag)."""
        payload = struct.pack("<I", 4) + os.urandom(trunc_len - 4)
        res = dissect_wireguard(payload)
        assert res["type"] == "transport_data"
        assert res["msg_type"] == 4
        # Payload len must safely report 0 without negative numbers
        assert res["payload_len"] == 0
        assert "0 bytes payload" in res["info"]

    def test_t5_wg_malformed_frames_in_full_ethernet_pipeline(self):
        """Malformed WireGuard frames wrapped inside complete L2/L3/L4 frames on en0 and utun3."""
        bad_wg_payload = struct.pack("<I", 0xEE) + b"CorruptedPayloadData"
        udp = build_udp_header(41641, 41641, len(bad_wg_payload))
        ip = build_ipv4_header(src_ip="100.119.199.76", dst_ip="100.103.212.21", protocol=17, payload_len=len(udp) + len(bad_wg_payload))
        eth = build_ethernet_header()
        frame = eth + ip + udp + bad_wg_payload

        # 1. Test on Ethernet interface (en0)
        pkt_en0 = dissect_packet(frame, interface="en0")
        assert pkt_en0["protocol"] == "WireGuard"
        assert "wireguard" in pkt_en0["layers"]
        assert "0xee" in pkt_en0["info"].lower() or "wireguard" in pkt_en0["info"].lower()

        # 2. Test on Tunnel interface (utun3) with DLT_NULL header
        raw_utun = struct.pack("<I", 2) + ip + udp + bad_wg_payload
        pkt_utun = dissect_packet(raw_utun, interface="utun3")
        assert pkt_utun["protocol"] == "WireGuard"
        assert "wireguard" in pkt_utun["layers"]


# ============================================================================
# Class 3: Local AI RPC Edge Cases (Ports 8081-8084)
# ============================================================================

class TestTier5LocalAiRpcEdgeCases:
    """Stress-test Local AI RPC dissectors across Ports 8081-8084 under edge cases."""

    def test_t5_ai_rpc_partial_http_request_line(self):
        """Incomplete HTTP request line without CRLF or headers."""
        res = dissect_local_ai_rpc(b"POST /v1/chat/compl", port=8082)
        assert res["protocol"] == "AI-RPC"
        assert res["type"] == "http11_request"
        assert res["method"] == "POST"
        assert "/v1/chat/compl" in res["uri"]

    def test_t5_ai_rpc_headers_without_body(self):
        """HTTP/1.1 request with headers but completely empty body."""
        raw = b"POST /v1/chat/completions HTTP/1.1\r\nHost: 127.0.0.1:8082\r\n\r\n"
        res = dissect_local_ai_rpc(raw, port=8082)
        assert res["protocol"] == "AI-RPC"
        assert res["type"] == "http11_request"
        assert res["model"] == ""
        assert res["stream"] is False

    def test_t5_ai_rpc_corrupted_json_request_body(self):
        """HTTP/1.1 request with truncated or invalid JSON body."""
        raw = b"POST /v1/chat/completions HTTP/1.1\r\n\r\n{\"model\": \"qwen_38_max\", \"stream\": "
        res = dissect_local_ai_rpc(raw, port=8082)
        assert res["protocol"] == "AI-RPC"
        assert res["type"] == "http11_request"
        # Must not throw json.decoder.JSONDecodeError
        assert isinstance(res["info"], str)

    @pytest.mark.parametrize("bad_sse", [
        b"data: not_valid_json\n\n",
        b"data: {\"unrelated\": 123}\n\n",
        b"data: {\"choices\": []}\n\n",
        b"data: {\"choices\": [{}]}\n\n",
        b"data: {\"choices\": [{\"delta\": {}}]}\n\n",
        b"data: {\"choices\": [{\"delta\": {\"content\": null}}]}\n\n",
    ])
    def test_t5_ai_rpc_malformed_sse_chunks(self, bad_sse: bytes):
        """Malformed or unexpected SSE chunks must fallback cleanly without unhandled exceptions."""
        res = dissect_local_ai_rpc(bad_sse, port=8082)
        assert res["protocol"] in ("AI-RPC", "AI-SSE")
        assert "type" in res

    def test_t5_ai_rpc_http2_rst_stream_frame(self):
        """HTTP/2 preface + RST_STREAM frame (Type 3) with error code."""
        preface = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
        # Length=4 (3B), Type=3 (1B RST_STREAM), Flags=0 (1B), StreamID=1 (4B), ErrorCode=8 (4B CANCEL)
        rst_payload = preface + struct.pack(">I", 4)[1:] + b"\x03\x00" + struct.pack(">I", 1) + struct.pack(">I", 8)
        res = dissect_local_ai_rpc(rst_payload, port=8082)
        assert res["protocol"] == "HTTP/2"
        assert res["frame_type"] == "RST_STREAM"
        assert res["stream_id"] == 1
        assert res["length"] == 4

    def test_t5_ai_rpc_http2_goaway_frame(self):
        """HTTP/2 preface + GOAWAY frame (Type 7)."""
        preface = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
        # Length=8 (3B), Type=7 (1B GOAWAY), Flags=0 (1B), StreamID=0 (4B), LastStreamID=1 (4B), ErrorCode=0 (4B NO_ERROR)
        goaway_payload = preface + struct.pack(">I", 8)[1:] + b"\x07\x00" + struct.pack(">I", 0) + struct.pack(">II", 1, 0)
        res = dissect_local_ai_rpc(goaway_payload, port=8082)
        assert res["protocol"] == "HTTP/2"
        assert res["frame_type"] == "GOAWAY"
        assert res["stream_id"] == 0
        assert res["length"] == 8

    def test_t5_ai_rpc_http2_truncated_frame_header(self):
        """HTTP/2 preface followed by truncated frame header (< 9 bytes)."""
        preface = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
        truncated_h2 = preface + b"\x00\x00\x04\x01"  # only 4 bytes of frame header
        res = dissect_local_ai_rpc(truncated_h2, port=8082)
        # Should gracefully return raw payload
        assert res["protocol"] == "AI-RPC"
        assert res["type"] == "raw_payload"

    def test_t5_ai_rpc_rapid_streaming_burst_500_chunks(self):
        """Simulate high-speed inference burst of 500 SSE delta tokens."""
        tokens = ["The", " Lauburu", " mesh", " runs", " prima.cpp", " at", " 100", " tok/s", "."]
        for i in range(500):
            token = tokens[i % len(tokens)]
            sse_bytes = build_ai_rpc_sse_chunk(content_delta=token)
            res = dissect_local_ai_rpc(sse_bytes, port=8082)
            assert res["protocol"] == "AI-SSE"
            assert res["type"] == "sse_chunk"
            assert res["delta"] == token

    @pytest.mark.parametrize("port", [8081, 8082, 8083, 8084])
    def test_t5_ai_rpc_all_governed_mesh_ports(self, port: int):
        """Verify all 4 governed AI ports activate AI-RPC dissector in full packet pipeline."""
        raw_sse = build_ai_rpc_sse_chunk(f"Port_{port}_Token")
        frame = assemble_ethernet_ai_rpc_frame(raw_sse, dst_port=port)
        pkt = dissect_packet(frame, interface="bridge0")
        assert pkt["protocol"] == "AI-SSE"
        assert "airpc" in pkt["layers"]
        assert pkt["dst_port"] == port


# ============================================================================
# Class 4: Filter Syntax Stress & Fuzzing
# ============================================================================

class TestTier5FilterSyntaxStressFuzzing:
    """Stress-test display filter AST parser, fuzzing, and code injection defenses."""

    def test_t5_filter_nested_parentheses_deep_nesting(self):
        """Deeply nested parentheses (up to 8 levels) must parse and compile."""
        expr = "((((((((tcp.port == 8082))))))))"
        flt = SharkWireFilter(expr)
        valid, err = flt.validate()
        assert valid is True
        assert err is None

        # Matching evaluation
        pkt = {"protocol": "TCP", "layers": ["tcp"], "src_port": 12345, "dst_port": 8082}
        assert flt.matches(pkt) is True

    @pytest.mark.parametrize("bad_expr", [
        "((ip.addr == 127.0.0.1)",
        "ip.addr == 127.0.0.1))",
        "(((tcp.port == 8082))",
        ")tcp.port == 8082(",
        "()",
        "( && )",
    ])
    def test_t5_filter_unbalanced_parentheses_rejection(self, bad_expr: str):
        """Unbalanced or empty parentheses must be rejected with informative error."""
        flt = SharkWireFilter(bad_expr)
        valid, err = flt.validate()
        assert valid is False
        assert err is not None

    @pytest.mark.parametrize("fuzz_input", [
        "protocol == 🦈",
        "ip.addr == 🚀.🌟.🔥.💥",
        "tcp.port == ８０８２",
        "\x00\x01\x02",
        "wireguard \u200b && \u200c tcp",
        "ip.src == \U0001F600",
    ])
    def test_t5_filter_unicode_and_special_chars_fuzzing(self, fuzz_input: str):
        """Unicode, emojis, and non-ASCII control characters must not crash the parser."""
        flt = SharkWireFilter(fuzz_input)
        valid, err = flt.validate()
        # Either rejected gracefully or parsed safely — never unhandled crash
        assert isinstance(valid, bool)
        assert (err is None) or isinstance(err, str)

    def test_t5_filter_unknown_fields_and_truthy_presence(self):
        """Unknown or arbitrary fields must evaluate presence safely without KeyError."""
        flt1 = SharkWireFilter("custom_vendor_tag == testing")
        valid, err = flt1.validate()
        assert valid is True

        pkt1 = {"custom_vendor_tag": "testing"}
        pkt2 = {"custom_vendor_tag": "other"}
        assert flt1.matches(pkt1) is True
        assert flt1.matches(pkt2) is False

        # Standalone presence check
        flt2 = SharkWireFilter("custom_flag")
        valid, err = flt2.validate()
        assert valid is True
        assert flt2.matches({"custom_flag": True}) is True
        assert flt2.matches({"custom_flag": False}) is False
        assert flt2.matches({}) is False

    @pytest.mark.parametrize("malicious_expr", [
        "__import__('os').system('id')",
        "eval('1+1')",
        "exec('print(1)')",
        "open('/etc/passwd')",
        "__class__",
        "__subclasses__",
        "builtins",
        "__builtins__",
        "globals()",
        "locals()",
        "getattr(__import__('sys'), 'exit')",
        "; rm -rf /",
        "`whoami`",
        "${PATH}",
        "{bad: 1}",
        "[x for x in ()]",
        "lambda x: x",
    ])
    def test_t5_filter_malicious_code_injection_rejection(self, malicious_expr: str):
        """Comprehensive verification of Python code injection prevention in filter engine."""
        flt = SharkWireFilter(malicious_expr)
        valid, err = flt.validate()
        assert valid is False, f"Malicious expression '{malicious_expr}' must be rejected"
        assert err is not None

    def test_t5_filter_boolean_short_circuit_and_or_not_combinations(self):
        """Complex boolean combination: (wireguard and not tcp) or (ai-rpc and tcp.port == 8082)."""
        expr = "(wireguard and not tcp) or (airpc and tcp.port == 8082)"
        flt = SharkWireFilter(expr)
        valid, err = flt.validate()
        assert valid is True

        # WireGuard frame (UDP 41641) -> matches first clause
        pkt_wg = {"protocol": "WireGuard", "layers": ["eth", "ipv4", "udp", "wireguard"], "src_port": 41641}
        assert flt.matches(pkt_wg) is True

        # TCP SSH frame (port 22) -> matches neither clause
        pkt_ssh = {"protocol": "SSH", "layers": ["eth", "ipv4", "tcp", "ssh"], "src_port": 22, "dst_port": 54321}
        assert flt.matches(pkt_ssh) is False

        # AI-RPC frame (port 8082) -> matches second clause
        pkt_ai = {"protocol": "AI-RPC", "layers": ["eth", "ipv4", "tcp", "airpc"], "src_port": 8082, "dst_port": 50000}
        assert flt.matches(pkt_ai) is True

    def test_t5_filter_comparison_edge_cases_boundary_ports_and_lengths(self):
        """Length comparisons (<, <=, >, >=, ==, !=) and boundary ports."""
        flt_gt = SharkWireFilter("len > 1500")
        flt_le = SharkWireFilter("length <= 64")
        flt_port = SharkWireFilter("port == 65535")

        assert flt_gt.validate()[0] is True
        assert flt_le.validate()[0] is True
        assert flt_port.validate()[0] is True

        assert flt_gt.matches({"length": 1514}) is True
        assert flt_gt.matches({"length": 1500}) is False

        assert flt_le.matches({"length": 64}) is True
        assert flt_le.matches({"length": 65}) is False

        assert flt_port.matches({"src_port": 65535, "dst_port": 80}) is True
        assert flt_port.matches({"src_port": 80, "dst_port": 443}) is False


# ============================================================================
# Class 5: Ring Buffer High-Throughput Stress
# ============================================================================

class TestTier5RingBufferHighThroughputStress:
    """Multi-threaded concurrency and throughput stress on SharkWireRingBuffer."""

    def test_t5_ring_buffer_10000_concurrent_packet_burst(self):
        """10 concurrent threads appending 1,000 packets each (10,000 packets total) into 5,000 cap buffer."""
        rb = SharkWireRingBuffer(maxlen=5000)
        errors = []

        def worker(tid: int):
            try:
                for i in range(1000):
                    pkt = {
                        "index": tid * 10000 + i,
                        "timestamp": time.time(),
                        "length": 64,
                        "raw_bytes": b"GET / HTTP/1.1\r\n\r\n",
                    }
                    rb.append(pkt)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(10)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        assert len(errors) == 0, f"Concurrent appends produced errors: {errors}"
        assert len(rb) == 5000, f"Ring buffer capacity exceeded maxlen: {len(rb)}"
        assert rb.total_appended == 10000

    def test_t5_ring_buffer_simultaneous_clear_while_exporting_pcap(self):
        """Concurrent threads: writer, cleaner, exporter, and reader operating in parallel."""
        rb = SharkWireRingBuffer(maxlen=5000)
        errors = []
        stop_flag = threading.Event()

        def writer():
            idx = 0
            while not stop_flag.is_set():
                try:
                    rb.append({"index": idx, "timestamp": time.time(), "length": 32, "raw_bytes": b"X" * 32})
                    idx += 1
                except Exception as e:
                    errors.append(("writer", e))
                time.sleep(0.0001)

        def cleaner():
            while not stop_flag.is_set():
                try:
                    time.sleep(0.005)
                    rb.clear()
                except Exception as e:
                    errors.append(("cleaner", e))

        def exporter():
            while not stop_flag.is_set():
                try:
                    time.sleep(0.003)
                    pcap_data = rb.export_pcap()
                    assert len(pcap_data) >= 24, "PCAP export must have at least 24-byte global header"
                    magic = struct.unpack("<I", pcap_data[:4])[0]
                    assert magic == TCPDUMP_MAGIC, f"PCAP magic mismatch: 0x{magic:08x}"
                except Exception as e:
                    errors.append(("exporter", e))

        def reader():
            while not stop_flag.is_set():
                try:
                    time.sleep(0.002)
                    snapshot = rb.get_range(offset=0, limit=20)
                    assert isinstance(snapshot, list)
                except Exception as e:
                    errors.append(("reader", e))

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=cleaner),
            threading.Thread(target=exporter),
            threading.Thread(target=reader),
        ]
        for th in threads:
            th.start()

        # Run stress for 0.4 seconds
        time.sleep(0.4)
        stop_flag.set()

        for th in threads:
            th.join()

        assert len(errors) == 0, f"Concurrent mutation and PCAP export produced errors: {errors}"

    def test_t5_ring_buffer_fifo_eviction_strict_ordering(self):
        """FIFO eviction must drop the oldest packets and preserve strict monotonic ordering."""
        rb = SharkWireRingBuffer(maxlen=500)
        for i in range(1, 1501):  # push 1,500 packets
            rb.append({"index": i, "timestamp": 1726550000.0 + i, "length": 64})

        assert len(rb) == 500
        snapshot = rb.get_all()
        # Oldest preserved packet must be index 1001
        assert snapshot[0]["index"] == 1001
        # Newest packet must be index 1500
        assert snapshot[-1]["index"] == 1500
        # Strictly monotonic
        for i in range(len(snapshot) - 1):
            assert snapshot[i + 1]["index"] == snapshot[i]["index"] + 1


# ============================================================================
# Class 6: WhatCable Hardware Edge Cases
# ============================================================================

class TestTier5WhatcableHardwareEdgeCases:
    """Stress-test WhatCable inspector under unknown IDs, lane rates, and deficit alerts."""

    @pytest.mark.parametrize("vendor_id, expected_substr", [
        (0, "No vendor reported"),
        (-1, "No vendor reported"),
        (None, "Unknown Vendor"),
        (0x9999, "0x9999"),
        (0xFFFF, "0xFFFF"),
        (11037, "0x2B1D"),
        (11564, "0x2D2C"),
        (1452, "Apple"),
    ])
    def test_t5_whatcable_unknown_vendor_ids_resolution(self, vendor_id, expected_substr):
        """Resolution of known, unknown, negative, and null vendor IDs."""
        name = resolve_vendor_name(vendor_id)
        assert expected_substr.lower() in name.lower()

    @pytest.mark.parametrize("rate_str, lanes, expected_delivered", [
        ("1.62 Gbps (RBR)", 1, 1.3),
        ("1.62 Gbps (RBR)", 2, 2.59),
        ("1.62 Gbps (RBR)", 4, 5.18),
        ("2.7 Gbps (HBR)", 2, 4.32),
        ("2.7 Gbps (HBR)", 4, 8.64),
        ("5.4 Gbps (HBR2)", 4, 17.28),
        ("8.1 Gbps (HBR3)", 4, 25.92),
    ])
    def test_t5_whatcable_displayport_unusual_lane_rates_and_counts(self, rate_str, lanes, expected_delivered):
        """DisplayPort bandwidth math across standard and unusual lane rates and lane counts."""
        dp_data = {
            "displays": [
                {"rate": rate_str, "lanes": lanes, "neededGbps": 8.0, "monitorName": "TestMonitor"}
            ]
        }
        res = parse_displayport_alt_mode(dp_data)
        assert res["lanes"] == lanes
        assert abs(res["delivered_gbps"] - expected_delivered) <= 0.05

    def test_t5_whatcable_negative_headroom_critical_alerts(self):
        """Negative DisplayPort bandwidth headroom must trigger CRITICAL severity."""
        # 4K high refresh display requiring 32.0 Gbps on an 8.64 Gbps link (-23.36 Gbps deficit)
        display = {
            "monitor_name": "UltraWide Gaming Display",
            "delivered_gbps": 8.64,
            "needed_gbps": 32.0,
            "headroom_gbps": -23.36,
        }
        b = detect_display_bottleneck(display)
        assert b["is_bottleneck"] is True
        assert b["severity"] == "CRITICAL"
        assert "bottleneck" in b["summary"].lower()

    def test_t5_whatcable_dead_display_link_critical(self):
        """Display stream with 0 Gbps delivered but needed > 0 must trigger CRITICAL."""
        display = {"monitor_name": "Offline Sink", "delivered_gbps": 0.0, "needed_gbps": 18.0}
        b = detect_display_bottleneck(display)
        assert b["is_bottleneck"] is True
        assert b["severity"] == "CRITICAL"
        assert "failure" in b["summary"].lower() or "0 gbps" in b["summary"].lower()

    @pytest.mark.parametrize("watts, volts, expected_range, expected_pps", [
        (0, 0, "Unadvertised / Bus Power", False),
        (15, 5, "Standard USB Power", False),
        (60, 20, "SPR (Standard Power Range 60W)", True),
        (100, 20, "SPR (Standard Power Range 100W)", True),
        (140, 28, "EPR (Extended Power Range 140W)", True),
        (240, 50, "EPR (Extended Power Range 240W)", True),
        (300, 48, "EPR (Extended Power Range 300W)", True),
    ])
    def test_t5_whatcable_power_delivery_boundary_wattage_profiles(self, watts, volts, expected_range, expected_pps):
        """Boundary USB-PD power delivery profiling (0W to 300W EPR)."""
        pd = parse_power_delivery(max_watts=watts, max_volts=volts)
        assert pd["max_wattage"] == watts
        assert pd["pd_range"] == expected_range
        assert pd["pps_supported"] == expected_pps

    @pytest.mark.parametrize("speed_str, expected_gbps", [
        (None, 0.0),
        ("", 0.0),
        ("unknown", 0.0),
        ("480 Mbps", 0.48),
        ("USB 2.0 (High Speed)", 0.48),
        ("1000 Mbps", 1.0),
        ("2.5 Gbps", 2.5),
        ("USB 3.2 Gen 1 (5 Gbps)", 5.0),
        ("USB 3.2 Gen 2 (10 Gbps)", 10.0),
        ("USB4 Gen 2x2 (20 Gbps)", 20.0),
        ("10 Gb/s × 2", 20.0),
        ("Thunderbolt 4 (40 Gbps)", 40.0),
        ("Thunderbolt 5 (80 Gbps)", 80.0),
        ("120 Gbps", 120.0),
    ])
    def test_t5_whatcable_speed_parser_complex_and_asymmetric_strings(self, speed_str, expected_gbps):
        """Robust parsing of complex and asymmetric bandwidth strings without substring collisions."""
        val = parse_speed_to_gbps(speed_str)
        assert abs(val - expected_gbps) <= 0.001

    def test_t5_whatcable_concurrent_probe_calls_cache_thread_safety(self):
        """10 concurrent threads invoking probe_whatcable_hardware_details."""
        results = []
        errors = []

        def worker():
            try:
                res = probe_whatcable_hardware_details(force=False)
                results.append(res)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        assert len(errors) == 0
        assert len(results) == 10
        for r in results:
            assert r["status"] == "success"
            assert "ports" in r
            assert "display_ports" in r


# ============================================================================
# Class 7: Server Endpoint Adversarial Invocations
# ============================================================================

class TestTier5ServerEndpointAdversarialRequests:
    """Verify FastAPI server resilience against malformed HTTP bodies, queries, and actions."""

    @pytest.fixture
    def test_client(self):
        return TestClient(app)

    def test_t5_api_packets_filter_adversarial_payloads(self, test_client):
        """POST /api/packets/filter with malicious code injections and malformed JSON."""
        # 1. Code injection attempt
        r1 = test_client.post("/api/packets/filter", json={"filter": "__import__('os').system('id')"})
        assert r1.status_code == 200
        data1 = r1.json()
        assert data1["valid"] is False
        assert "strictly rejected" in data1["error"]

        # 2. Empty json
        r2 = test_client.post("/api/packets/filter", json={})
        assert r2.status_code == 200
        assert r2.json()["valid"] is True

        # 3. Non-JSON body
        r3 = test_client.post("/api/packets/filter", content=b"invalid-raw-bytes", headers={"content-type": "application/json"})
        assert r3.status_code == 200
        assert r3.json()["valid"] is True

    def test_t5_api_packets_control_invalid_actions(self, test_client):
        """POST /api/packets/control with illegal or unknown action types."""
        for bad_action in ["destroy", "hack", "reboot", "123", ""]:
            r = test_client.post("/api/packets/control", json={"action": bad_action})
            assert r.status_code == 400
            assert "Unknown action" in r.json()["error"]

    def test_t5_api_packets_stream_extreme_and_invalid_parameters(self, test_client):
        """GET /api/packets/stream with invalid limit strings and broken filter syntax."""
        r = test_client.get("/api/packets/stream?limit=not_an_int&filter=(((")
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]
        body_text = r.text
        assert "event: initial_batch" in body_text
        assert "event: stats" in body_text

    def test_t5_api_whatcable_details_rapid_concurrent_requests(self, test_client):
        """Rapid concurrent GET /api/whatcable/details requests."""
        statuses = []

        def call_endpoint():
            resp = test_client.get("/api/whatcable/details")
            statuses.append(resp.status_code)

        threads = [threading.Thread(target=call_endpoint) for _ in range(8)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        assert all(s == 200 for s in statuses)
        assert len(statuses) == 8
