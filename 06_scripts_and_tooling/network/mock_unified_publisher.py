#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentic Host Telemetry Publisher for Unified Broker.
Publishes live kernel and system metrics (RAM, network I/O, CPU) to ZMQ.
Governed by Rule 0 (Zero-Mock) and Rule 1 (Tri-Proof).
"""

import zmq
import time
import json
import psutil
from datetime import datetime, timezone


def main():
    context = zmq.Context()
    # Connect to the XSUB backend of the unified broker
    publisher = context.socket(zmq.PUB)
    publisher.connect("tcp://127.0.0.1:5550")
    
    print("Authentic Telemetry Publisher connected to Unified Broker at tcp://127.0.0.1:5550")
    
    topics = [b"ALERT.SYS", b"LENS.OBSERVATION", b"DATA.SYSTEM", b"LORA.DATASET"]
    topic_idx = 0
    
    while True:
        try:
            topic = topics[topic_idx % len(topics)]
            topic_idx += 1
            
            vm = psutil.virtual_memory()
            net = psutil.net_io_counters()
            cpu_pct = psutil.cpu_percent(interval=None)
            
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "bytes_sent": net.bytes_sent,
                "bytes_recv": net.bytes_recv,
                "packets_sent": net.packets_sent,
                "packets_recv": net.packets_recv,
                "available_ram_mb": round(vm.available / (1024 * 1024), 2),
                "ram_percent": vm.percent,
                "cpu_percent": cpu_pct,
                "source": "host_psutil_telemetry"
            }
            
            # Send multi-part message
            publisher.send_multipart([topic, json.dumps(payload).encode("utf-8")])
            print(f"Published authentic telemetry to {topic.decode()}: RAM {payload['ram_percent']}%, CPU {cpu_pct}%")
            
            time.sleep(2)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
