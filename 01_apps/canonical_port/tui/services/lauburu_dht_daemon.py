import asyncio
import json
import random
import zmq
import zmq.asyncio

async def dht_gossip_loop(socket):
    """
    Simulates a high-frequency DHT Gossip protocol node.
    This runs entirely independently of the Textual UI, shielding it from the GIL overhead.
    """
    print("[DHT Daemon] Starting background gossip network...")
    peer_count = 10
    
    while True:
        # Simulate network churn and gossip chatter
        peer_count += random.randint(-2, 3)
        peer_count = max(1, peer_count)
        
        telemetry = {
            "node_status": "ACTIVE",
            "active_peers": peer_count,
            "packets_per_sec": random.randint(1000, 5000),
            "latest_hash": f"0x{random.randbytes(4).hex()}"
        }
        
        # Broadcast the aggregated state over ZeroMQ to any connected TUI clients
        socket.send_string(f"DHT_STATE {json.dumps(telemetry)}")
        
        # Gossip frequency: 10 times a second
        await asyncio.sleep(0.1)

async def main():
    ctx = zmq.asyncio.Context()
    socket = ctx.socket(zmq.PUB)
    # Bind to local port for IPC
    socket.bind("tcp://127.0.0.1:5556")
    print("[DHT Daemon] ZeroMQ PUB socket bound on tcp://127.0.0.1:5556")
    
    await dht_gossip_loop(socket)

if __name__ == "__main__":
    asyncio.run(main())
