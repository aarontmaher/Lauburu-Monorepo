import argparse
import asyncio
import hashlib
import os
import struct

CHUNK_SIZE = 1024 * 1024  # 1MB chunks

async def handle_client(reader, writer, output_file, lock, received_chunks):
    try:
        header_data = await reader.readexactly(12)
        chunk_id, chunk_size = struct.unpack('!IQ', header_data)
        
        data = await reader.readexactly(chunk_size)
        
        async with lock:
            if chunk_id not in received_chunks:
                with open(output_file, 'r+b') as f:
                    f.seek(chunk_id * CHUNK_SIZE)
                    f.write(data)
                received_chunks.add(chunk_id)
                print(f"Received chunk {chunk_id} ({chunk_size} bytes)")
        
        writer.write(b"ACK")
        await writer.drain()
    except asyncio.IncompleteReadError:
        pass
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

async def server(host_ports, output_file, expected_size, expected_hash):
    # Initialize file with zeros
    with open(output_file, 'wb') as f:
        f.truncate(expected_size)
        
    lock = asyncio.Lock()
    received_chunks = set()
    total_chunks = (expected_size + CHUNK_SIZE - 1) // CHUNK_SIZE
    
    stop_event = asyncio.Event()

    async def run_server(host, port):
        async def client_handler(reader, writer):
            await handle_client(reader, writer, output_file, lock, received_chunks)
            if len(received_chunks) == total_chunks:
                stop_event.set()
                
        srv = await asyncio.start_server(client_handler, host, port)
        print(f"Listening on {host}:{port}")
        async with srv:
            await srv.serve_forever()

    servers = [asyncio.create_task(run_server(host, port)) for host, port in host_ports]
    
    # Wait until all chunks are received
    await stop_event.wait()
    
    # Cancel servers
    for srv in servers:
        srv.cancel()
        
    print("All chunks received! Verifying hash...")
    hasher = hashlib.sha256()
    with open(output_file, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    
    actual_hash = hasher.hexdigest()
    if actual_hash == expected_hash:
        print("Hash matches! File transfer successful.")
    else:
        print(f"Hash mismatch! Expected {expected_hash}, got {actual_hash}")

async def send_chunk(host, port, chunk_id, data, retries=5):
    for attempt in range(retries):
        try:
            reader, writer = await asyncio.open_connection(host, port)
            header = struct.pack('!IQ', chunk_id, len(data))
            writer.write(header + data)
            await writer.drain()
            
            ack = await reader.readexactly(3)
            writer.close()
            await writer.wait_closed()
            if ack == b"ACK":
                return True
        except Exception as e:
            print(f"Failed to send chunk {chunk_id} to {host}:{port} (attempt {attempt+1}): {e}")
            await asyncio.sleep(1)
    return False

async def client(file_path, endpoints):
    file_size = os.path.getsize(file_path)
    print("Calculating hash of file to send...")
    hasher = hashlib.sha256()
    chunks = []
    
    with open(file_path, 'rb') as f:
        chunk_id = 0
        while True:
            data = f.read(CHUNK_SIZE)
            if not data:
                break
            hasher.update(data)
            chunks.append((chunk_id, data))
            chunk_id += 1
            
    expected_hash = hasher.hexdigest()
    print(f"File size: {file_size}, Hash: {expected_hash}, Total Chunks: {len(chunks)}")
    
    queue = asyncio.Queue()
    for chunk in chunks:
        await queue.put(chunk)
        
    async def worker(host, port):
        while not queue.empty():
            try:
                chunk_id, data = queue.get_nowait()
            except asyncio.QueueEmpty:
                break
                
            print(f"Sending chunk {chunk_id} via {host}:{port}")
            success = await send_chunk(host, port, chunk_id, data)
            if not success:
                print(f"Failed to send chunk {chunk_id}, putting back in queue")
                await queue.put((chunk_id, data))
            queue.task_done()
            
    # Launch a worker for each transport endpoint to ensure concurrency across transports
    workers = [asyncio.create_task(worker(host, port)) for host, port in endpoints]
    await asyncio.gather(*workers)
    
    print("All chunks sent!")
    print(f"Command for server to start before client: python multiwan_bond.py server --file <output_file> --endpoints <endpoints> --size {file_size} --hash {expected_hash}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="MultiWAN file bonding transfer script")
    parser.add_argument('mode', choices=['server', 'client'])
    parser.add_argument('--file', required=True, help='Path to read from (client) or write to (server)')
    parser.add_argument('--endpoints', nargs='+', help='List of IP:PORT combinations (e.g. 100.x.x.x:5000 192.168.1.x:5000 127.0.0.1:5000)', required=True)
    parser.add_argument('--size', type=int, help='Expected file size (required for server)')
    parser.add_argument('--hash', type=str, help='Expected SHA256 hash (required for server)')
    args = parser.parse_args()
    
    endpoints = []
    for ep in args.endpoints:
        host, port = ep.split(':')
        endpoints.append((host, int(port)))
        
    if args.mode == 'server':
        if not args.size or not args.hash:
            print("Server mode requires --size and --hash")
            exit(1)
        asyncio.run(server(endpoints, args.file, args.size, args.hash))
    else:
        asyncio.run(client(args.file, endpoints))
