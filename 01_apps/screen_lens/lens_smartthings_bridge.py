import zmq
import json
import time
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

class SmartThingsLensBridge:
    """
    Transforms the raw Android Accessibility XML DOM of the official SmartThings app
    into a clean, real-time JSON API for the Lauburu ecosystem.
    """
    def __init__(self, broker_ip="127.0.0.1"):
        self.context = zmq.Context()
        
        # Subscribe to the raw Pixel 10 XML feed and Lauburu Commands
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect(f"tcp://{broker_ip}:5555")
        self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "LENS.OBS.PIXEL10_ACCESSIBILITY")
        self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "MESH.COMMAND.SMARTTHINGS")
        
        # Publish the cleaned state back to the Mesh
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.connect(f"tcp://{broker_ip}:5550")
        
        self.device_state = {}
        print("🏠 SmartThings Headless Bridge Online. Parsing DOM...")

    def parse_smartthings_xml(self, xml_string):
        """Extracts device names and their toggle states from the XML tree."""
        try:
            root = ET.fromstring(xml_string)
            new_state = {}
            
            # The SmartThings UI typically uses Switch widgets or specific content-desc patterns
            # We look for all nodes that are clickable or checkable
            for node in root.iter('node'):
                content_desc = node.attrib.get('content-desc', '')
                text = node.attrib.get('text', '')
                is_checked = node.attrib.get('checked', 'false')
                bounds = node.attrib.get('bounds', '')
                
                # Heuristic: If it's a switch or labeled as a device
                label = text if text else content_desc
                if label and ('light' in label.lower() or 'switch' in label.lower() or 'tv' in label.lower()):
                    # Clean bounds string "[x1,y1][x2,y2]"
                    new_state[label] = {
                        "state": "ON" if is_checked == "true" else "OFF",
                        "bounds": bounds
                    }
            
            # If the state changed, publish an update to the mesh
            if new_state != self.device_state and new_state:
                self.device_state = new_state
                payload = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "devices": self.device_state
                }
                self.publisher.send_multipart([b"MESH.STATE.SMARTTHINGS", json.dumps(payload).encode('utf-8')])
                print(f"[SmartThings Bridge] State Updated: {list(self.device_state.keys())}")
                
        except Exception as e:
            # Silently pass XML parsing errors if the DOM is mid-render
            pass

    def handle_mesh_command(self, payload):
        """Translates a Lauburu command (e.g. 'Turn on Living Room') into a physical Lens action."""
        target_device = payload.get("device")
        action = payload.get("action") # "ON", "OFF", "TOGGLE"
        
        if target_device in self.device_state:
            current_state = self.device_state[target_device]["state"]
            if current_state != action and action != "TOGGLE":
                # We need to click it! Extract center coordinates from bounds "[100,200][300,400]"
                bounds = self.device_state[target_device]["bounds"]
                coords = re.findall(r'\d+', bounds)
                if len(coords) == 4:
                    x = (int(coords[0]) + int(coords[2])) // 2
                    y = (int(coords[1]) + int(coords[3])) // 2
                    
                    # Draft the action for the Shadow AI to review
                    draft = {
                        "action": "input_tap",
                        "x": x,
                        "y": y,
                        "reason": f"SmartThings Bridge: Toggling {target_device} to {action}",
                        "target_node": "Pixel_10_Pro_XL"
                    }
                    self.publisher.send_multipart([b"LENS.DRAFT_ACTION", json.dumps(draft).encode('utf-8')])
                    print(f"⚡ Drafted Tap for {target_device} at ({x}, {y})")

    def run(self):
        while True:
            try:
                msg = self.subscriber.recv_multipart()
                topic = msg[0].decode('utf-8')
                payload = json.loads(msg[1].decode('utf-8'))
                
                if topic == "LENS.OBS.PIXEL10_ACCESSIBILITY":
                    self.parse_smartthings_xml(payload.get("dom_tree", ""))
                elif topic == "MESH.COMMAND.SMARTTHINGS":
                    self.handle_mesh_command(payload)
                    
            except Exception as e:
                print(f"Bridge Error: {e}")
                time.sleep(1)

if __name__ == "__main__":
    bridge = SmartThingsLensBridge()
    bridge.run()
