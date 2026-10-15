#!/usr/bin/env python3
"""
tb4_inference_bridge.py - High-throughput, zero-copy TCP bridge for TB4 inference offloading.
Bridges Mac Mini (L1) Port 8081 to MacBook Pro (L2) Port 8081 over 10Gbps Thunderbolt 4 (0.56ms RTT).
Preserves >= 9.6GB Host RAM Sanctuary by completely offloading GGUF model weights to L2.
"""

import asyncio
import sys
import os
import signal
import socket
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

TARGET_HOST = os.getenv("TB4_TARGET_HOST", "169.254.215.118")
TARGET_PORT = int(os.getenv("TB4_TARGET_PORT", "8081"))
LISTEN_HOST = os.getenv("BRIDGE_LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = int(os.getenv("BRIDGE_LISTEN_PORT", "8081"))
BUFFER_SIZE = 65536

async def handle_client(client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
    remote_reader, remote_writer = None, None
    for attempt in range(3):
        try:
            remote_reader, remote_writer = await asyncio.wait_for(
                asyncio.open_connection(TARGET_HOST, TARGET_PORT), timeout=2.0
            )
            break
        except Exception as exc:
            if attempt < 2:
                await asyncio.sleep(0.3)
            else:
                logging.error(f"Failed to connect to L2 TB4 target {TARGET_HOST}:{TARGET_PORT} after 3 attempts: {exc}")

    if remote_writer is None:
        try:
            error_body = b'{"error":{"message":"L2 TB4 inference node temporarily unreachable","code":503}}\n'
            response = (
                b"HTTP/1.1 503 Service Unavailable\r\n"
                b"Content-Type: application/json\r\n"
                b"Content-Length: " + str(len(error_body)).encode() + b"\r\n"
                b"Connection: close\r\n\r\n" + error_body
            )
            client_writer.write(response)
            await client_writer.drain()
        except Exception:
            pass
        finally:
            client_writer.close()
            await client_writer.wait_closed()
            return

    async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            while not reader.at_eof():
                chunk = await reader.read(BUFFER_SIZE)
                if not chunk:
                    break
                writer.write(chunk)
                await writer.drain()
        except Exception:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    await asyncio.gather(
        pipe(client_reader, remote_writer),
        pipe(remote_reader, client_writer),
        return_exceptions=True
    )

async def main():
    logging.info(f"Starting TB4 Inference Bridge: {LISTEN_HOST}:{LISTEN_PORT} -> {TARGET_HOST}:{TARGET_PORT}")
    server = await asyncio.start_server(handle_client, LISTEN_HOST, LISTEN_PORT, reuse_port=True)
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bridge stopped by signal.")
