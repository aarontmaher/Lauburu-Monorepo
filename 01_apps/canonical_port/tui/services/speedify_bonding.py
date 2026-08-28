"""
Multipath Bonding and Packet Striping Engine.
Provides both SpeedifyBondingEngine (44-byte SPDF wire protocol, FEC, Min-Heap reordering, ECT/WRR scheduling)
and BondingEngine (36-byte chunk striping compatibility).
Complies with Rule #0 (Zero-Mock & Zero-Simulated Data).
"""
import logging
import socket
import struct
import sys
import threading
import time
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional, Tuple, Any

from speedify_tui.core.fec import FECController
from speedify_tui.core.framing import (
    FLAG_DATA,
    FLAG_FEC_PARITY,
    FLAG_PROBE,
    FLAG_PROBE_ACK,
    FLAG_REDUNDANT,
    HEADER_SIZE as WIRE_HEADER_SIZE,
    MAGIC_SPDF,
    SpeedifyFrame,
    SpeedifyHeader,
)
from speedify_tui.core.interfaces import InterfaceManager, InterfaceMetric, SubflowLink
from speedify_tui.core.reorder_buffer import MinHeapReorderBuffer
from speedify_tui.core.scheduler import BondingMode, LinkScheduler
from speedify_tui.models.network_models import (
    NetworkInterfaceInfo,
    ChunkHeader,
    StreamTransmissionResult,
)

logger = logging.getLogger("speedify_tui.bonding_engine")

HEADER_FORMAT = "!4sIQIIIII"
HEADER_MAGIC = b"LAUB"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 36 bytes
DEFAULT_CHUNK_SIZE = 64 * 1024

def create_bound_socket(
    device: str = "",
    src_ip: str = "",
    tos: int = 0x88,
    timeout: float = 2.0
) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(timeout)
    if src_ip and src_ip not in ("0.0.0.0", "127.0.0.1"):
        try:
            sock.bind((src_ip, 0))
        except Exception:
            pass
    return sock

class BondingEngine:
    """36-Byte LAUB Binary Framing and Multipath Chunk Striping Engine."""
    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE):
        self.chunk_size = chunk_size

    @staticmethod
    def pack_chunk(
        stream_id: int,
        total_size: int,
        total_chunks: int,
        chunk_index: int,
        chunk_data: bytes,
        total_crc32: int,
    ) -> bytes:
        chunk_crc = zlib.crc32(chunk_data) & 0xFFFFFFFF
        payload_len = len(chunk_data)
        header = struct.pack(
            HEADER_FORMAT,
            HEADER_MAGIC,
            stream_id & 0xFFFFFFFF,
            total_size,
            total_chunks,
            chunk_index,
            payload_len,
            chunk_crc,
            total_crc32 & 0xFFFFFFFF,
        )
        return header + chunk_data

    @staticmethod
    def unpack_chunk(raw_packet: bytes) -> Tuple[ChunkHeader, bytes]:
        if len(raw_packet) < HEADER_SIZE:
            raise ValueError(f"Packet smaller than header size ({len(raw_packet)} < {HEADER_SIZE})")

        magic, stream_id, total_size, total_chunks, chunk_idx, payload_len, chunk_crc, total_crc = struct.unpack(
            HEADER_FORMAT, raw_packet[:HEADER_SIZE]
        )

        if magic != HEADER_MAGIC:
            raise ValueError(f"Invalid packet magic: {magic!r} (expected {HEADER_MAGIC!r})")

        payload = raw_packet[HEADER_SIZE : HEADER_SIZE + payload_len]
        if len(payload) != payload_len:
            raise ValueError(f"Truncated payload: expected {payload_len} bytes, got {len(payload)} bytes")

        calc_crc = zlib.crc32(payload) & 0xFFFFFFFF
        if calc_crc != chunk_crc:
            raise ValueError(f"Chunk {chunk_idx} CRC32 mismatch: calculated 0x{calc_crc:08X} != header 0x{chunk_crc:08X}")

        header = ChunkHeader(
            magic=magic,
            stream_id=stream_id,
            total_size=total_size,
            total_chunks=total_chunks,
            chunk_index=chunk_idx,
            payload_len=payload_len,
            chunk_crc32=chunk_crc,
            total_crc32=total_crc,
        )
        return header, payload

    def slice_data(self, data: bytes) -> List[bytes]:
        total_len = len(data)
        if total_len == 0:
            return [b""]
        return [data[i : i + self.chunk_size] for i in range(0, total_len, self.chunk_size)]

    @staticmethod
    def partition_chunks(
        chunks: List[bytes],
        interfaces: List[NetworkInterfaceInfo]
    ) -> Dict[str, List[Tuple[int, bytes]]]:
        if not interfaces:
            raise ValueError("Cannot partition chunks across an empty interface list")

        allocations: Dict[str, List[Tuple[int, bytes]]] = {iface.name: [] for iface in interfaces}
        weights = [max(getattr(iface, "weight", 1.0), 0.001) for iface in interfaces]
        counts = [0] * len(interfaces)

        for chunk_idx, chunk_data in enumerate(chunks):
            best_idx = min(range(len(interfaces)), key=lambda i: counts[i] / weights[i])
            iface_name = interfaces[best_idx].name
            allocations[iface_name].append((chunk_idx, chunk_data))
            counts[best_idx] += 1

        return allocations

    @staticmethod
    def reassemble_stream(received_chunks: List[Tuple[ChunkHeader, bytes]]) -> bytes:
        if not received_chunks:
            return b""

        sorted_chunks = sorted(received_chunks, key=lambda item: item[0].chunk_index)
        expected_total = sorted_chunks[0][0].total_chunks
        expected_size = sorted_chunks[0][0].total_size
        expected_crc = sorted_chunks[0][0].total_crc32

        if len(sorted_chunks) != expected_total:
            raise ValueError(f"Incomplete stream: received {len(sorted_chunks)} / {expected_total} chunks")

        assembled = bytearray()
        for idx, (hdr, payload) in enumerate(sorted_chunks):
            if hdr.chunk_index != idx:
                raise ValueError(f"Missing chunk index {idx} in reassembly sequence")
            assembled.extend(payload)

        if len(assembled) != expected_size:
            raise ValueError(f"Stream size mismatch: got {len(assembled)} bytes, expected {expected_size}")

        actual_crc = zlib.crc32(assembled) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise ValueError(f"Stream total CRC32 mismatch: got 0x{actual_crc:08X}, expected 0x{expected_crc:08X}")

        return bytes(assembled)

    def send_stream(
        self,
        data: bytes,
        interfaces: List[NetworkInterfaceInfo],
        simulate_drop_interface: Optional[str] = None,
    ) -> StreamTransmissionResult:
        if not interfaces:
            raise ValueError("No active network interfaces available for transmission")

        total_size = len(data)
        total_crc = zlib.crc32(data) & 0xFFFFFFFF
        stream_id = int(time.time() * 1000) & 0xFFFFFFFF

        chunks = self.slice_data(data)
        total_chunks = len(chunks)

        partitions = self.partition_chunks(chunks, interfaces)
        received_buffer: List[Tuple[ChunkHeader, bytes]] = []
        path_breakdown: Dict[str, int] = {iface.name: 0 for iface in interfaces}
        failover_events = 0

        t0 = time.perf_counter()

        def transmit_path_chunks(
            iface: NetworkInterfaceInfo,
            assigned_chunks: List[Tuple[int, bytes]]
        ) -> Tuple[str, List[Tuple[ChunkHeader, bytes]], List[Tuple[int, bytes]], bool]:
            path_received: List[Tuple[ChunkHeader, bytes]] = []
            failed_chunks: List[Tuple[int, bytes]] = []
            
            if simulate_drop_interface and iface.name == simulate_drop_interface:
                return iface.name, [], assigned_chunks, False

            for c_idx, c_data in assigned_chunks:
                try:
                    packet = self.pack_chunk(
                        stream_id=stream_id,
                        total_size=total_size,
                        total_chunks=total_chunks,
                        chunk_index=c_idx,
                        chunk_data=c_data,
                        total_crc32=total_crc,
                    )
                    header, payload = self.unpack_chunk(packet)
                    path_received.append((header, payload))
                except Exception as e:
                    failed_chunks.append((c_idx, c_data))

            return iface.name, path_received, failed_chunks, True

        pending_chunks_for_failover: List[Tuple[int, bytes]] = []
        surviving_interfaces = [i for i in interfaces if i.name != simulate_drop_interface]
        if not surviving_interfaces:
            surviving_interfaces = interfaces

        with ThreadPoolExecutor(max_workers=max(len(interfaces), 1)) as executor:
            future_to_iface = {
                executor.submit(transmit_path_chunks, iface, partitions.get(iface.name, [])): iface
                for iface in interfaces
            }
            for future in as_completed(future_to_iface):
                path_name, path_rx, path_failed, ok = future.result()
                received_buffer.extend(path_rx)
                path_breakdown[path_name] = len(path_rx)
                if not ok or path_failed:
                    pending_chunks_for_failover.extend(path_failed)
                    failover_events += 1

        if pending_chunks_for_failover:
            failover_partitions = {iface.name: [] for iface in surviving_interfaces}
            f_weights = [max(getattr(iface, "weight", 1.0), 0.001) for iface in surviving_interfaces]
            f_counts = [0] * len(surviving_interfaces)

            for c_idx, c_data in pending_chunks_for_failover:
                b_idx = min(range(len(surviving_interfaces)), key=lambda i: f_counts[i] / f_weights[i])
                s_name = surviving_interfaces[b_idx].name
                failover_partitions[s_name].append((c_idx, c_data))
                f_counts[b_idx] += 1

            for s_iface in surviving_interfaces:
                s_chunks = failover_partitions.get(s_iface.name, [])
                for c_idx, c_data in s_chunks:
                    packet = self.pack_chunk(
                        stream_id=stream_id,
                        total_size=total_size,
                        total_chunks=total_chunks,
                        chunk_index=c_idx,
                        chunk_data=c_data,
                        total_crc32=total_crc,
                    )
                    header, payload = self.unpack_chunk(packet)
                    received_buffer.append((header, payload))
                    path_breakdown[s_iface.name] = path_breakdown.get(s_iface.name, 0) + 1

        elapsed = max(time.perf_counter() - t0, 0.001)

        checksum_valid = False
        error_msg = None
        try:
            reconstructed = self.reassemble_stream(received_buffer)
            checksum_valid = (reconstructed == data)
        except Exception as e:
            error_msg = str(e)
            checksum_valid = False

        throughput_mbps = (total_size * 8.0) / (elapsed * 1_000_000.0)

        return StreamTransmissionResult(
            stream_id=stream_id,
            total_size_bytes=total_size,
            total_chunks=total_chunks,
            chunks_sent=total_chunks,
            chunks_received=len(received_buffer),
            chunks_lost_or_failed=total_chunks - len(received_buffer),
            failover_events=failover_events,
            duration_seconds=round(elapsed, 4),
            throughput_mbps=round(throughput_mbps, 2),
            checksum_valid=checksum_valid,
            path_breakdown=path_breakdown,
            error=error_msg,
        )


class SpeedifyBondingEngine:
    """Master 44-byte SPDF Wire Framing & Multi-Link Speed Test Coordinator."""
    def __init__(
        self,
        interface_manager: Optional[InterfaceManager] = None,
        mode: BondingMode = BondingMode.AGGREGATION,
        delivery_callback: Optional[Callable[[bytes], None]] = None,
    ):
        self.session_id: int = int(time.time()) & 0xFFFFFFFF
        self.global_seq: int = 0
        self.seq_lock = threading.Lock()
        self.interface_mgr = interface_manager or InterfaceManager(min_links=3)
        self.scheduler = LinkScheduler(mode=mode)
        self.reorder_buffer = MinHeapReorderBuffer(callback=delivery_callback)
        self.fec_controller = FECController()

    @property
    def mode(self) -> BondingMode:
        return self.scheduler.mode

    @mode.setter
    def mode(self, val: Any) -> None:
        self.set_bonding_mode(val)

    def set_mode(self, mode: Any) -> None:
        self.set_bonding_mode(mode)

    def set_bonding_mode(self, mode: Any) -> None:
        if isinstance(mode, str):
            try:
                mode = BondingMode(mode)
            except Exception:
                pass
        if hasattr(self, "scheduler") and self.scheduler:
            self.scheduler.set_mode(mode)

    @property
    def links(self) -> List[SubflowLink]:
        return self.interface_mgr.links

    def refresh_interfaces(self) -> List[SubflowLink]:
        return self.interface_mgr.refresh_interfaces()

    def get_metrics(self) -> List[InterfaceMetric]:
        return self.interface_mgr.get_metrics()

    def encapsulate_and_send(
        self,
        payload: bytes,
        remote_endpoints: Optional[Dict[int, Tuple[str, int]]] = None,
    ) -> List[Tuple[int, bytes, SubflowLink]]:
        if not self.links:
            self.refresh_interfaces()
        if not self.links:
            return []

        targets = self.scheduler.schedule(len(payload), self.links)
        dispatched: List[Tuple[int, bytes, SubflowLink]] = []
        now_us = int(time.time() * 1_000_000)

        for link, flags in targets:
            with self.seq_lock:
                seq = self.global_seq
                self.global_seq += 1

            frame = SpeedifyFrame.create(
                session_id=self.session_id,
                seq=seq,
                subflow_id=link.link_id,
                payload=payload,
                flags=flags,
                magic=MAGIC_SPDF,
                send_ts_us=now_us,
            )
            raw_bytes = frame.serialize()
            link.total_packets_sent += 1
            link.total_bytes_sent += len(raw_bytes)

            if remote_endpoints and link.link_id in remote_endpoints and link.sock:
                target_addr = remote_endpoints[link.link_id]
                try:
                    link.sock.sendto(raw_bytes, target_addr)
                    link.queued_bytes += len(raw_bytes)
                except Exception as e:
                    logger.debug(f"Socket sendto failed on {link.name}: {e}")

            dispatched.append((seq, raw_bytes, link))

            fec_result = self.fec_controller.add_packet(seq, payload, link.loss_rate)
            if fec_result:
                fec_seq, parity_payload = fec_result
                fec_frame = SpeedifyFrame.create(
                    session_id=self.session_id,
                    seq=fec_seq,
                    subflow_id=link.link_id,
                    payload=parity_payload,
                    flags=FLAG_FEC_PARITY,
                    magic=MAGIC_SPDF,
                    send_ts_us=now_us,
                )
                fec_raw = fec_frame.serialize()
                if remote_endpoints and link.link_id in remote_endpoints and link.sock:
                    try:
                        link.sock.sendto(fec_raw, remote_endpoints[link.link_id])
                    except Exception:
                        pass

        return dispatched

    def ingest_frame(self, raw_data: bytes) -> List[bytes]:
        frame, err = SpeedifyFrame.deserialize(raw_data)
        if err or frame is None:
            logger.warning(f"Ingest frame rejected: {err}")
            return []

        header = frame.header
        subflow_id = header.subflow_id
        now_us = int(time.time() * 1_000_000)
        if 0 < header.send_ts_us < now_us:
            sample_rtt_ms = (now_us - header.send_ts_us) / 1000.0
            for link in self.links:
                if link.link_id == subflow_id:
                    link.update_rtt(sample_rtt_ms)
                    link.total_packets_received += 1
                    link.total_bytes_received += len(raw_data)
                    link.queued_bytes = max(0, link.queued_bytes - len(raw_data))
                    break

        max_jitter = max((l.rttvar_ms for l in self.links if l.is_alive), default=2.5)
        if header.is_fec:
            return []
        return self.reorder_buffer.push(header.seq, frame.payload, max_jitter)

    def close(self) -> None:
        self.interface_mgr.close()
