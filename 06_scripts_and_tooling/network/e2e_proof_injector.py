import zmq
import json
import time
from datetime import datetime, timezone

context = zmq.Context()
publisher = context.socket(zmq.PUB)
publisher.connect("tcp://127.0.0.1:5550")
time.sleep(1) # Prevent Slow Joiner Syndrome

payload = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "source": "lauburu_life_companion_pixel10",
    "event_type": "VLA_OBSERVATION",
    "hardware_state": "EDGE_TPU_ACTIVE",
    "observation": "E2E Proof: Edge payload traverses the Mesh.",
}

for i in range(10):
    publisher.send_multipart([b"LORA.DATASET", json.dumps(payload).encode('utf-8')])
    print(f"Sent {i+1}")
    time.sleep(0.2)
