import os
import time
import json
import socket
import platform
import subprocess
import zmq
from datetime import datetime, timezone

def get_active_window_mac():
    try:
        # A headless, zero-collision way to get the active app on macOS
        script = 'tell application "System Events" to get name of first application process whose frontmost is true'
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return "Unknown"

def scrape_state():
    os_name = platform.system()
    state = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "os": os_name,
        "cpu_load": os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0,
    }
    
    if os_name == "Darwin":
        state["active_window"] = get_active_window_mac()
    elif os_name == "Linux":
        # Placeholder for X11/Wayland or Termux ADB headless dumps
        state["active_window"] = "Headless_Linux_Session"
        
    return state

def main():
    broker_ip = os.environ.get("ZMQ_BROKER_IP", "127.0.0.1")
    context = zmq.Context()
    publisher = context.socket(zmq.PUB)
    publisher.connect(f"tcp://{broker_ip}:5550")
    
    hostname = socket.gethostname().upper().replace("-", "_")
    topic = f"LENS.OBS.{hostname}".encode('utf-8')
    
    print(f"Lens Edge Sensor started on {hostname}. Pushing to {broker_ip}:5550")
    print(f"Operating purely headlessly. Zero UI collision.")
    
    last_state = None
    
    while True:
        try:
            current_state = scrape_state()
            
            # Smart Sensor: Only push to ZMQ if state materially changes to prevent network choke
            if current_state.get("active_window") != (last_state.get("active_window") if last_state else None):
                payload = json.dumps(current_state).encode('utf-8')
                publisher.send_multipart([topic, payload])
                print(f"[{current_state['timestamp']}] State Change Detected. Pushed to ZMQ.")
                last_state = current_state
                
            time.sleep(2)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Sensor error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
