"""
Authentic TCP Loopback Server Factory (Zero-Mock)
Part of Canonical Mesh Fallback Terminal E2E Test Suite.

Binds genuine OS TCP sockets to 127.0.0.1 on ephemeral ports.
Strictly adheres to Rule 0 (Zero-Mock): 0 mock libraries used.
"""

from __future__ import annotations

import asyncio
import socket
import threading
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator, Optional, Tuple


def get_unused_port() -> int:
    """Finds an unused local port by briefly binding and releasing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


@asynccontextmanager
async def start_async_tcp_server(
    banner: bytes = b"SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6\r\n",
) -> AsyncGenerator[Tuple[str, int], None]:
    """
    Spawns an authentic asynchronous TCP echo/banner server on 127.0.0.1.
    Yields (host, port). Cleans up cleanly on exit.
    """
    connected_clients = []

    async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        connected_clients.append(writer)
        try:
            if banner:
                writer.write(banner)
                await writer.drain()
            # Keep connection open until closed by client or server shutdown
            while not reader.at_eof():
                data = await reader.read(1024)
                if not data:
                    break
        except Exception:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
    sockets = server.sockets
    if not sockets:
        raise RuntimeError("Failed to bind TCP server")
    port = sockets[0].getsockname()[1]

    try:
        yield "127.0.0.1", port
    finally:
        server.close()
        await server.wait_closed()
        for w in connected_clients:
            try:
                w.close()
            except Exception:
                pass


@contextmanager
def start_sync_tcp_server(
    banner: bytes = b"SSH-2.0-OpenSSH_8.9p1\r\n",
) -> Generator[Tuple[str, int], None, None]:
    """
    Spawns an authentic synchronous TCP server in a background thread.
    Yields (host, port).
    """
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("127.0.0.1", 0))
    server_sock.listen(5)
    port = server_sock.getsockname()[1]

    stop_event = threading.Event()

    def run_server():
        server_sock.settimeout(0.5)
        while not stop_event.is_set():
            try:
                client_sock, _ = server_sock.accept()
                if banner:
                    try:
                        client_sock.sendall(banner)
                    except Exception:
                        pass
                client_sock.close()
            except socket.timeout:
                continue
            except Exception:
                break
        server_sock.close()

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    try:
        yield "127.0.0.1", port
    finally:
        stop_event.set()
        thread.join(timeout=1.5)
