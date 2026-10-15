import os
import time
import json
import zmq
from datetime import datetime, timezone

BROKER_IP = "10.1.0.10" # L1 Mac Host Tailscale IP (Primary Broker)

def get_battery_info():
    """Reads battery capacity and charging status from Linux sysfs."""
    try:
        # Common paths for Debian Linux tablets
        bat_dir = None
        for p in os.listdir('/sys/class/power_supply/'):
            if p.startswith('BAT') or p.startswith('max170xx_battery'):
                bat_dir = f'/sys/class/power_supply/{p}'
                break
                
        if not bat_dir:
            return {"capacity": 100, "status": "Unknown"}
            
        with open(f'{bat_dir}/capacity', 'r') as f:
            capacity = int(f.read().strip())
        with open(f'{bat_dir}/status', 'r') as f:
            status = f.read().strip()
            
        return {"capacity": capacity, "status": status}
    except Exception as e:
        print(f"Error reading battery: {e}")
        return {"capacity": 100, "status": "Unknown"}

def main():
    context = zmq.Context()
    publisher = context.socket(zmq.PUB)
    publisher.connect(f"tcp://{BROKER_IP}:5550")
    
    print("🔋 Linux Tablet Battery Governor Online. Protecting nodes from thermal/power crashes.")
    
    training_killed = False
    
    while True:
        try:
            bat_info = get_battery_info()
            capacity = bat_info["capacity"]
            status = bat_info["status"]
            
            # Publish Telemetry
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "node": "L4_Linux_Tablet",
                "battery_percent": capacity,
                "charging_status": status
            }
            publisher.send_multipart([b"MESH.TELEMETRY.BATTERY", json.dumps(payload).encode('utf-8')])
            print(f"[{payload['timestamp']}] Battery: {capacity}% ({status})")
            
            # Actionable Intelligence: Protect the Node
            if capacity < 15 and status == "Discharging" and not training_killed:
                print("⚠️ CRITICAL POWER LEVEL. USB tether is not providing enough power for AI workload.")
                print("🛑 Autonomously terminating 'lens_dev_training' tmux session to save state...")
                
                # Kill the heavy training loop
                os.system("tmux kill-session -t lens_dev_training 2>/dev/null")
                
                # Throttle CPU to powersave
                os.system("echo powersave | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null 2>&1")
                
                alert_payload = {
                    "action": "HALT_TRAINING",
                    "reason": f"Battery critically low ({capacity}%). CPU throttled."
                }
                publisher.send_multipart([b"MESH.ALERT.SYSTEM", json.dumps(alert_payload).encode('utf-8')])
                training_killed = True
                
            elif capacity > 30 or status == "Charging":
                # Reset kill flag if power is restored
                training_killed = False
                
            time.sleep(60) # Poll every 60 seconds
        except Exception as e:
            time.sleep(10)

if __name__ == "__main__":
    main()
