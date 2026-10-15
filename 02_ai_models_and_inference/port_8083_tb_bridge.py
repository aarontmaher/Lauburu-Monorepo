#!/usr/bin/env python3
"""
High-Speed Thunderbolt DMA TCP Bridge for Port 8083
Routes local connections on Mac Mini (127.0.0.1:8083 / 0.0.0.0:8083)
to the offloaded 27B model on Linux Mini (192.168.2.3:8083) with sub-millisecond latency.
"""

import sys
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [TB-Bridge-8083] %(message)s")
log = logging.getLogger("TB-Bridge-8083")

TARGET_HOST = "192.168.2.3"
TARGET_PORT = 8083
LOCAL_PORT = 8083

async def handle_client(local_reader, local_writer):
    try:
        remote_reader, remote_writer = await asyncio.open_connection(TARGET_HOST, TARGET_PORT)
    except Exception as e:
        log.error(f"Failed to connect to backend {TARGET_HOST}:{TARGET_PORT} - {e}")
        local_writer.close()
        try:
            await local_writer.wait_closed()
        except Exception:
            pass
        return

    async def forward(src, dst):
        try:
            while not src.at_eof():
                data = await src.read(65536)
                if not data:
                    break
                dst.write(data)
                await dst.drain()
        except Exception:
            pass
        finally:
            try:
                dst.close()
                await dst.wait_closed()
            except Exception:
                pass

    t1 = asyncio.create_task(forward(local_reader, remote_writer))
    t2 = asyncio.create_task(forward(remote_reader, local_writer))
    await asyncio.gather(t1, t2, return_exceptions=True)

async def main():
    server = await asyncio.start_server(handle_client, "0.0.0.0", LOCAL_PORT)
    addr = server.sockets[0].getsockname()
    log.info(f"Serving Port {LOCAL_PORT} bridge -> {TARGET_HOST}:{TARGET_PORT} on {addr}")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
