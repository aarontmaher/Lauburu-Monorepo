import zmq
import json
import time
import psutil
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_telemetry():
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    return {
        "cpu_percent": cpu,
        "ram_percent": ram.percent,
        "ram_free_gb": ram.available / (1024**3)
    }

def main():
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    
    # Configure socket options for safety against buffer overflow
    socket.setsockopt(zmq.SNDHWM, 1000)
    socket.setsockopt(zmq.LINGER, 0)

    try:
        socket.bind("tcp://*:5555")
        logging.info("ZMQ Telemetry Broadcaster (ALERT.SYS) bound to tcp://*:5555")
    except zmq.ZMQError as e:
        logging.error(f"Failed to bind socket: {e}")
        return

    iteration = 0
    while True:
        try:
            iteration += 1
            time.sleep(15) # Wait 15 seconds

            # Check telemetry
            telemetry = get_telemetry()
            
            # Construct payload
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "severity": "WARNING",
                "message": "Tailscale latency spike detected. Falling back to Bluetooth PAN.",
                "telemetry": telemetry
            }
            
            # Send multipart message
            socket.send_multipart([
                b"ALERT.SYS",
                json.dumps(payload).encode('utf-8')
            ])
            logging.info(f"Published ALERT.SYS message: {payload}")

        except zmq.ZMQError as e:
            logging.error(f"ZMQ Error during send: {e}")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            time.sleep(1) # Prevent tight loop on error

if __name__ == "__main__":
    main()
