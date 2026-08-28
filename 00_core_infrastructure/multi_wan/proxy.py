"""
multi_wan/proxy.py - Accumulative Bonding & Multiplexing Proxy Daemon (Port 8888).

Auto-detects HTTP and SOCKS5 protocols (RFC 1928 SOCKS5 handshake + HTTP CONNECT / GET / POST handling).
Socket binding (SocketBinder): binds local interface IPs (`bind((ip, 0))`) and sets `SO_BINDTODEVICE` where supported,
plus Tailscale overlay peer proxy forwarding.
StreamMultiplexer: supports bonding modes (aggregate, lowest_latency, redundant) and chunk/stream distribution
across active WAN interfaces & Tailscale peers.
Dynamic failover & chunk re-queuing when an interface drops, and re-admission on reconnect.
"""

import asyncio
import logging
import socket
import time
import urllib.parse
from typing import Dict, List, Optional, Tuple

from .discovery import InterfaceTracker, NetworkInterface

logger = logging.getLogger("multi_wan.proxy")

MODE_AGGREGATE = "aggregate"
MODE_LOWEST_LATENCY = "lowest_latency"
MODE_REDUNDANT = "redundant"


class SocketBinder:
    """Handles OS-level socket binding to local interface IPs or device names."""

    @staticmethod
    def create_bound_socket(
        interface_ip: Optional[str] = None,
        interface_name: Optional[str] = None,
    ) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except Exception:
                pass

        # 1. Bind to local interface IP if provided and non-wildcard
        if interface_ip and interface_ip != "0.0.0.0":
            try:
                sock.bind((interface_ip, 0))
            except Exception as e:
                logger.warning(f"Could not bind to interface IP {interface_ip}: {e}")

        # 2. Bind to SO_BINDTODEVICE on Linux/Android if interface name provided
        if interface_name and hasattr(socket, "SO_BINDTODEVICE"):
            try:
                opt_val = interface_name.encode("utf-8")
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, opt_val)
            except Exception as e:
                logger.debug(f"SO_BINDTODEVICE unavailable for {interface_name}: {e}")

        sock.setblocking(False)
        return sock


class StreamMultiplexer:
    """Manages path selection, bonding modes, dynamic failover, and stream distribution."""

    def __init__(self, tracker: Optional[InterfaceTracker] = None):
        self.tracker = tracker or InterfaceTracker()
        self.mode: str = MODE_AGGREGATE
        self._rr_index: int = 0
        self.total_bytes_transferred: int = 0
        self.total_requests: int = 0
        self.active_connections: int = 0

    def set_mode(self, mode: str):
        if mode in (MODE_AGGREGATE, MODE_LOWEST_LATENCY, MODE_REDUNDANT):
            self.mode = mode
            logger.info(f"StreamMultiplexer mode changed to: {mode}")
        else:
            raise ValueError(f"Invalid bonding mode: {mode}")

    def select_paths(self) -> List[NetworkInterface]:
        """Selects target paths based on active bonding mode and health status."""
        active = self.tracker.get_active_interfaces()
        if not active:
            return []

        if self.mode == MODE_LOWEST_LATENCY:
            active.sort(key=lambda x: x.latency_ms)
            return [active[0]]

        elif self.mode == MODE_REDUNDANT:
            active.sort(key=lambda x: x.latency_ms)
            return active[: min(2, len(active))]

        else:  # MODE_AGGREGATE
            # Weighted / Round-robin path selection
            idx = self._rr_index % len(active)
            self._rr_index += 1
            return [active[idx]]

    def get_all_active_paths(self) -> List[NetworkInterface]:
        """Returns all currently active interfaces for multi-chunk distribution."""
        active = self.tracker.get_active_interfaces()
        return active if active else self.select_paths()

    def record_transfer(self, iface_name: str, bytes_count: int):
        """Records byte count for metrics and pooled throughput calculation."""
        self.total_bytes_transferred += bytes_count
        if iface_name in self.tracker.interfaces:
            iface = self.tracker.interfaces[iface_name]
            iface.bytes_sent += bytes_count


class Socks5Handler:
    """Implements RFC 1928 SOCKS5 Protocol Handler."""

    @staticmethod
    async def handle(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        initial_data: bytes,
        multiplexer: StreamMultiplexer,
    ):
        # 1. Auth Handshake (NO AUTH 0x00)
        writer.write(b"\x05\x00")
        await writer.drain()

        # 2. Read Request Header
        req_header = await reader.readexactly(4)
        ver, cmd, rsv, atyp = req_header

        if cmd != 0x01:  # CONNECT command
            writer.write(b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00")  # Command not supported
            await writer.drain()
            writer.close()
            return

        # Parse Destination Host
        if atyp == 0x01:  # IPv4
            addr_bytes = await reader.readexactly(4)
            dst_host = socket.inet_ntoa(addr_bytes)
        elif atyp == 0x03:  # Domain Name
            domain_len = (await reader.readexactly(1))[0]
            dst_host = (await reader.readexactly(domain_len)).decode("utf-8")
        elif atyp == 0x04:  # IPv6
            addr_bytes = await reader.readexactly(16)
            dst_host = socket.inet_ntop(socket.AF_INET6, addr_bytes)
        else:
            writer.close()
            return

        port_bytes = await reader.readexactly(2)
        dst_port = int.from_bytes(port_bytes, "big")

        # 3. Connect Outbound using Multiplexer & SocketBinder
        remote_reader, remote_writer, selected_iface = await Socks5Handler._connect_outbound(
            dst_host, dst_port, multiplexer
        )

        if not remote_writer:
            writer.write(b"\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00")  # Connection Refused
            await writer.drain()
            writer.close()
            return

        # SOCKS5 Success Response
        writer.write(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
        await writer.drain()

        # 4. Pipe Stream
        await Socks5Handler._pipe_streams(reader, writer, remote_reader, remote_writer, multiplexer, selected_iface)

    @staticmethod
    async def _connect_outbound(
        dst_host: str, dst_port: int, multiplexer: StreamMultiplexer
    ) -> Tuple[Optional[asyncio.StreamReader], Optional[asyncio.StreamWriter], NetworkInterface]:
        paths = multiplexer.select_paths()
        if not paths:
            return None, None, NetworkInterface("none", "0.0.0.0", status="DOWN")
        selected_path = paths[0]

        loop = asyncio.get_event_loop()

        if multiplexer.mode == MODE_REDUNDANT and len(paths) >= 2:
            # Redundant dual-send race
            return await Socks5Handler._connect_redundant(dst_host, dst_port, paths, loop)

        is_loopback_dst = (dst_host in ("127.0.0.1", "localhost") or dst_host.startswith("127."))

        # Single path outbound (Aggregate or Lowest Latency)
        try:
            bind_ip = selected_path.ip if (not selected_path.is_tailscale and not is_loopback_dst) else None
            sock = SocketBinder.create_bound_socket(
                interface_ip=bind_ip,
                interface_name=selected_path.name if (not selected_path.is_tailscale and not is_loopback_dst) else None,
            )

            if selected_path.is_tailscale:
                # Forward to Tailscale Peer Proxy on port 8888
                await asyncio.wait_for(loop.sock_connect(sock, (selected_path.ip, 8888)), timeout=0.2)
                r, w = await asyncio.open_connection(sock=sock)
                connect_hdr = f"CONNECT {dst_host}:{dst_port} HTTP/1.1\r\nHost: {dst_host}:{dst_port}\r\n\r\n"
                w.write(connect_hdr.encode())
                await w.drain()
                resp = await r.readuntil(b"\r\n\r\n")
                if b"200" in resp:
                    return r, w, selected_path
                else:
                    w.close()
                    # Trigger failover
                    multiplexer.tracker.update_interface_status(selected_path.name, "DEGRADED")
                    return await Socks5Handler._connect_outbound_fallback(dst_host, dst_port, multiplexer)
            else:
                # Direct Outbound
                await loop.sock_connect(sock, (dst_host, dst_port))
                r, w = await asyncio.open_connection(sock=sock)
                return r, w, selected_path

        except Exception as e:
            logger.warning(f"Connection failed via {selected_path.name}: {e}")
            multiplexer.tracker.update_interface_status(selected_path.name, "DEGRADED")
            return await Socks5Handler._connect_outbound_fallback(dst_host, dst_port, multiplexer)

    @staticmethod
    async def _connect_outbound_fallback(
        dst_host: str, dst_port: int, multiplexer: StreamMultiplexer
    ) -> Tuple[Optional[asyncio.StreamReader], Optional[asyncio.StreamWriter], NetworkInterface]:
        """Failover connection attempt to surviving active paths."""
        is_loopback_dst = (dst_host in ("127.0.0.1", "localhost") or dst_host.startswith("127."))
        surviving = multiplexer.tracker.get_active_interfaces()
        for alt_path in surviving:
            try:
                loop = asyncio.get_event_loop()
                bind_ip = alt_path.ip if (not alt_path.is_tailscale and not is_loopback_dst) else None
                sock = SocketBinder.create_bound_socket(interface_ip=bind_ip)
                if alt_path.is_tailscale:
                    await asyncio.wait_for(loop.sock_connect(sock, (alt_path.ip, 8888)), timeout=0.2)
                    r, w = await asyncio.open_connection(sock=sock)
                    connect_hdr = f"CONNECT {dst_host}:{dst_port} HTTP/1.1\r\nHost: {dst_host}:{dst_port}\r\n\r\n"
                    w.write(connect_hdr.encode())
                    await w.drain()
                    resp = await r.readuntil(b"\r\n\r\n")
                    if b"200" in resp:
                        return r, w, alt_path
                else:
                    await loop.sock_connect(sock, (dst_host, dst_port))
                    r, w = await asyncio.open_connection(sock=sock)
                    return r, w, alt_path
            except Exception:
                continue

        # Final loopback fallback
        try:
            r, w = await asyncio.open_connection(dst_host, dst_port)
            return r, w, NetworkInterface("fallback", "0.0.0.0", status="DEGRADED")
        except Exception:
            return None, None, NetworkInterface("failed", "0.0.0.0", status="DOWN")

    @staticmethod
    async def _connect_redundant(
        dst_host: str, dst_port: int, paths: List[NetworkInterface], loop: asyncio.AbstractEventLoop
    ) -> Tuple[Optional[asyncio.StreamReader], Optional[asyncio.StreamWriter], NetworkInterface]:
        """Dual-send race across top 2 lowest-latency paths."""
        is_loopback_dst = (dst_host in ("127.0.0.1", "localhost") or dst_host.startswith("127."))
        async def try_connect(path: NetworkInterface):
            bind_ip = path.ip if (not path.is_tailscale and not is_loopback_dst) else None
            sock = SocketBinder.create_bound_socket(interface_ip=bind_ip)
            if path.is_tailscale:
                await asyncio.wait_for(loop.sock_connect(sock, (path.ip, 8888)), timeout=0.2)
                r, w = await asyncio.open_connection(sock=sock)
                w.write(f"CONNECT {dst_host}:{dst_port} HTTP/1.1\r\nHost: {dst_host}:{dst_port}\r\n\r\n".encode())
                await w.drain()
                resp = await r.readuntil(b"\r\n\r\n")
                if b"200" in resp:
                    return r, w, path
                else:
                    w.close()
                    raise ConnectionError("Peer proxy error")
            else:
                await loop.sock_connect(sock, (dst_host, dst_port))
                return await asyncio.open_connection(sock=sock)

        tasks = [asyncio.create_task(try_connect(p)) for p in paths[:2]]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        # Cancel slower pending connections
        for p_task in pending:
            p_task.cancel()

        for d_task in done:
            try:
                res = d_task.result()
                if res and res[1]:
                    return res[0], res[1], res[2]
            except Exception:
                pass

        return await Socks5Handler._connect_outbound_fallback(dst_host, dst_port, multiplexer=StreamMultiplexer())

    @staticmethod
    async def _pipe_streams(
        r1: asyncio.StreamReader,
        w1: asyncio.StreamWriter,
        r2: asyncio.StreamReader,
        w2: asyncio.StreamWriter,
        multiplexer: StreamMultiplexer,
        iface: NetworkInterface,
    ):
        async def forward(src_r, dst_w, direction_label):
            try:
                while True:
                    data = await src_r.read(65536)
                    if not data:
                        break
                    dst_w.write(data)
                    await dst_w.drain()
                    multiplexer.record_transfer(iface.name, len(data))
            except Exception:
                pass
            finally:
                try:
                    dst_w.close()
                except Exception:
                    pass

        await asyncio.gather(
            forward(r1, w2, "client->remote"),
            forward(r2, w1, "remote->client"),
            return_exceptions=True,
        )


class HttpProxyHandler:
    """Implements HTTP & HTTPS Proxy Handler with Accumulative Multiplexing."""

    @staticmethod
    async def handle(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        initial_data: bytes,
        multiplexer: StreamMultiplexer,
    ):
        try:
            header_bytes = initial_data + await reader.readuntil(b"\r\n\r\n")
        except Exception:
            writer.close()
            return

        lines = header_bytes.split(b"\r\n")
        if not lines or not lines[0]:
            writer.close()
            return

        request_line = lines[0].decode("utf-8", errors="ignore")
        parts = request_line.split()

        if len(parts) < 3:
            writer.close()
            return

        method, target, http_version = parts[0], parts[1], parts[2]

        if method == "CONNECT":
            # HTTPS Tunneling
            if ":" in target:
                host, port_str = target.split(":")
                port = int(port_str)
            else:
                host, port = target, 443

            r_out, w_out, selected_iface = await Socks5Handler._connect_outbound(host, port, multiplexer)
            if r_out and w_out:
                writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                await writer.drain()
                await Socks5Handler._pipe_streams(reader, writer, r_out, w_out, multiplexer, selected_iface)
            else:
                writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                await writer.drain()
                writer.close()

        else:
            # HTTP Request Forwarding (GET, POST, etc.)
            parsed = urllib.parse.urlparse(target)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 80

            # Accumulative Range Multiplexing for GET downloads in AGGREGATE mode
            if method == "GET" and multiplexer.mode == MODE_AGGREGATE:
                handled = await HttpProxyHandler._try_accumulative_range_fetch(
                    reader, writer, header_bytes, host, port, multiplexer
                )
                if handled:
                    return

            r_out, w_out, selected_iface = await Socks5Handler._connect_outbound(host, port, multiplexer)
            if r_out and w_out:
                w_out.write(header_bytes)
                await w_out.drain()
                await Socks5Handler._pipe_streams(reader, writer, r_out, w_out, multiplexer, selected_iface)
            else:
                writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                await writer.drain()
                writer.close()

    @staticmethod
    async def _connect_bound_path(
        dst_host: str, dst_port: int, path: NetworkInterface
    ) -> Tuple[Optional[asyncio.StreamReader], Optional[asyncio.StreamWriter]]:
        """Directly connects a socket bound to the specific physical interface IP and device name."""
        loop = asyncio.get_event_loop()
        is_loopback = (dst_host in ("127.0.0.1", "localhost") or dst_host.startswith("127."))
        bind_ip = path.ip if (not path.is_tailscale and not is_loopback) else None
        bind_dev = path.name if (not path.is_tailscale and not is_loopback) else None
        sock = SocketBinder.create_bound_socket(interface_ip=bind_ip, interface_name=bind_dev)
        try:
            if path.is_tailscale:
                await asyncio.wait_for(loop.sock_connect(sock, (path.ip, 8888)), timeout=0.5)
                r, w = await asyncio.open_connection(sock=sock)
                w.write(f"CONNECT {dst_host}:{dst_port} HTTP/1.1\r\nHost: {dst_host}:{dst_port}\r\n\r\n".encode())
                await w.drain()
                resp = await r.readuntil(b"\r\n\r\n")
                if b"200" in resp:
                    return r, w
                else:
                    w.close()
                    return None, None
            else:
                await loop.sock_connect(sock, (dst_host, dst_port))
                return await asyncio.open_connection(sock=sock)
        except Exception:
            return None, None

    @staticmethod
    async def _try_accumulative_range_fetch(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        header_bytes: bytes,
        host: str,
        port: int,
        multiplexer: StreamMultiplexer,
    ) -> bool:
        """Accumulative download multiplexing across available WAN paths using Range splitting."""
        active_paths = multiplexer.get_all_active_paths()
        local_paths = [p for p in active_paths if not p.is_tailscale]
        range_paths = local_paths if local_paths else active_paths

        if len(range_paths) < 2:
            return False  # Single path fallback

        # Probe headers to check Range support & Content-Length
        try:
            r_out, w_out, iface = await Socks5Handler._connect_outbound(host, port, multiplexer)
            if not r_out or not w_out:
                return False

            # Send HEAD / GET probe request
            probe_hdr = header_bytes.replace(b"GET ", b"HEAD ")
            w_out.write(probe_hdr)
            await w_out.drain()

            head_resp = await r_out.readuntil(b"\r\n\r\n")
            w_out.close()

            content_length = None
            accept_ranges = False
            for line in head_resp.split(b"\r\n"):
                line_str = line.decode("utf-8", errors="ignore").lower()
                if line_str.startswith("content-length:"):
                    content_length = int(line_str.split(":")[1].strip())
                elif line_str.startswith("accept-ranges:") and "bytes" in line_str:
                    accept_ranges = True

            if not content_length or content_length < 65536 or not accept_ranges:
                return False  # Not suitable for range splitting

            # Split payload into N equal chunks across active paths
            num_chunks = min(len(active_paths), 4)
            chunk_size = content_length // num_chunks
            chunks_data = [None] * num_chunks

            async def fetch_chunk(chunk_idx: int, start_b: int, end_b: int, path: NetworkInterface):
                try:
                    r_c, w_c = await HttpProxyHandler._connect_bound_path(host, port, path)
                    if not r_c or not w_c:
                        raise ConnectionError(f"Bound chunk connect failed on {path.name}")

                    # Inject Range header
                    range_header = f"Range: bytes={start_b}-{end_b}\r\n"
                    mod_headers = header_bytes.replace(b"\r\n\r\n", f"\r\n{range_header}\r\n".encode())
                    w_c.write(mod_headers)
                    await w_c.drain()

                    # Read HTTP response headers
                    resp_hdr = await r_c.readuntil(b"\r\n\r\n")
                    if b"206" in resp_hdr or b"200" in resp_hdr:
                        data = await r_c.readexactly(end_b - start_b + 1)
                        w_c.close()
                        return chunk_idx, data, path
                    else:
                        w_c.close()
                        raise ValueError("Non-206 status")
                except Exception as e:
                    logger.warning(f"Chunk {chunk_idx} failed on {path.name}: {e}. Re-queuing...")
                    # Re-queue chunk to surviving path
                    surviving = multiplexer.tracker.get_active_interfaces()
                    fallback_path = surviving[0] if surviving else path
                    r_c, w_c = await HttpProxyHandler._connect_bound_path(host, port, fallback_path)
                    if not r_c or not w_c:
                        raise ConnectionError("Fallback chunk connect failed")
                    range_header = f"Range: bytes={start_b}-{end_b}\r\n"
                    mod_headers = header_bytes.replace(b"\r\n\r\n", f"\r\n{range_header}\r\n".encode())
                    w_c.write(mod_headers)
                    await w_c.drain()
                    await r_c.readuntil(b"\r\n\r\n")
                    data = await r_c.readexactly(end_b - start_b + 1)
                    w_c.close()
                    return chunk_idx, data, fallback_path

            # Dispatch range chunk tasks concurrently
            tasks = []
            for i in range(num_chunks):
                sb = i * chunk_size
                eb = content_length - 1 if i == num_chunks - 1 else (i + 1) * chunk_size - 1
                p = range_paths[i % len(range_paths)]
                tasks.append(fetch_chunk(i, sb, eb, p))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify all chunk tasks succeeded BEFORE writing HTTP headers
            for res in results:
                if isinstance(res, Exception) or not isinstance(res, tuple):
                    logger.warning(f"Accumulative range chunk task failed: {res}. Falling back to single-path fetch.")
                    return False

            # Sort chunks sequentially by index
            results.sort(key=lambda x: x[0])

            # Write HTTP 200 header once integrity of all chunks is confirmed
            writer.write(f"HTTP/1.1 200 OK\r\nContent-Length: {content_length}\r\nContent-Type: application/octet-stream\r\n\r\n".encode())
            await writer.drain()

            for idx, cdata, p in results:
                writer.write(cdata)
                await writer.drain()
                multiplexer.record_transfer(p.name, len(cdata))

            writer.close()
            return True

        except Exception as e:
            logger.debug(f"Accumulative range fetch fallback: {e}")
            return False


class BondingProxyServer:
    """Accumulative Multiplexing Proxy Daemon on port 8888."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8888,
        tracker: Optional[InterfaceTracker] = None,
    ):
        self.host = host
        self.port = port
        self.tracker = tracker or InterfaceTracker()
        self.multiplexer = StreamMultiplexer(self.tracker)
        self.server: Optional[asyncio.Server] = None
        self._running = False

    async def start(self):
        """Starts the proxy daemon server."""
        self.tracker.start_monitoring()
        self.server = await asyncio.start_server(self._handle_client, self.host, self.port)
        self._running = True
        logger.info(f"BondingProxyServer listening on {self.host}:{self.port}")

    async def stop(self):
        """Stops the proxy daemon server."""
        self._running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        self.tracker.stop_monitoring()
        logger.info("BondingProxyServer stopped.")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.multiplexer.total_requests += 1
        self.multiplexer.active_connections += 1
        try:
            # Peek initial 3 bytes to auto-detect protocol
            initial_data = await reader.read(3)
            if not initial_data:
                writer.close()
                return

            if initial_data[0] == 0x05:
                # SOCKS5 Protocol
                await Socks5Handler.handle(reader, writer, initial_data, self.multiplexer)
            else:
                # HTTP Protocol
                await HttpProxyHandler.handle(reader, writer, initial_data, self.multiplexer)
        except Exception as e:
            logger.error(f"Client handling error: {e}")
            try:
                writer.close()
            except Exception:
                pass
        finally:
            self.multiplexer.active_connections = max(0, self.multiplexer.active_connections - 1)
