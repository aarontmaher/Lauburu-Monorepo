import os
import time
import json
import subprocess
import zmq
from datetime import datetime, timezone

def get_uiautomator_xml():
    """
    Executes a native Android uiautomator dump to extract the structural DOM of the screen.
    This runs entirely locally on the Pixel 10 via Termux (requires root/ADB localhost).
    """
    dump_file = "/sdcard/window_dump.xml"
    try:
        # Dump the structural UI hierarchy
        subprocess.run(["uiautomator", "dump", dump_file], capture_output=True, check=True)
        
        # Read the XML file
        with open(dump_file, "r", encoding="utf-8") as f:
            xml_data = f.read()
            
        return xml_data
    except Exception as e:
        print(f"UIAutomator Error: {e}")
        return None

def main():
    # In production, this targets the Mac Mini's ZMQ broker over the Bluetooth PAN IP
    broker_ip = os.environ.get("ZMQ_BROKER_IP", "192.168.44.1") 
    context = zmq.Context()
    publisher = context.socket(zmq.PUB)
    publisher.connect(f"tcp://{broker_ip}:5550")
    
    topic = b"LENS.OBS.PIXEL10_ACCESSIBILITY"
    print(f"📱 Pixel 10 Accessibility Sensor Online. Streaming DOM to {broker_ip}:5550")
    
    last_xml = ""
    
    while True:
        try:
            current_xml = get_uiautomator_xml()
            
            # Only push if the UI structure actually changed
            if current_xml and current_xml != last_xml:
                payload = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "pixel_10_accessibility_service",
                    "format": "xml",
                    "dom_tree": current_xml
                }
                
                publisher.send_multipart([topic, json.dumps(payload).encode('utf-8')])
                print(f"[{payload['timestamp']}] Accessibility DOM Updated. Pushed to ZMQ.")
                last_xml = current_xml
                
            time.sleep(1.0) # Poll at 1Hz to save battery
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Sensor error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
