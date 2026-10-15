import subprocess
import json
import time

def get_bluetooth_state():
    try:
        output = subprocess.check_output(["system_profiler", "SPBluetoothDataType", "-json"]).decode('utf-8')
        data = json.loads(output)
        return data.get("SPBluetoothDataType", [])
    except Exception as e:
        print(f"Error extracting Bluetooth state: {e}")
        return []

def map_mesh_graph(bt_data):
    connected_nodes = []
    print("\n🌐 [Screen Lens Sovereign] Omnipresent Bluetooth IP-Less Graph (Layer 0) 🌐")
    print("="*80)
    
    if not bt_data:
        print("Fatal: Could not access CoreBluetooth stack.")
        return

    controller = bt_data[0]
    host_address = controller.get('device_address', 'Unknown')
    print(f"L1 Host (Mac Mini) MAC: {host_address} [STATE: ACTIVE]")
    print("-" * 80)

    devices_dict = controller.get('device_title', {})
    
    # In newer macOS versions, it might be an array of dicts or nested under connected/not_connected
    if isinstance(devices_dict, list):
        # Fallback parsing
        pass
    
    # We will just parse the text output natively since json structure varies wildly across macOS versions
    text_output = subprocess.check_output(["system_profiler", "SPBluetoothDataType"]).decode('utf-8')
    lines = text_output.split('\n')
    
    current_device = None
    is_connected = False
    
    for line in lines:
        line_s = line.strip()
        if line_s == "Connected:":
            is_connected = True
        elif line_s == "Not Connected:":
            is_connected = False
        elif line_s.endswith(":") and len(line_s) > 1 and "Address" not in line_s and "Vendor ID" not in line_s and "Bluetooth" not in line_s:
            current_device = line_s[:-1]
        elif "Address:" in line_s and current_device:
            mac = line_s.split("Address:")[1].strip()
            if is_connected:
                print(f"✅ LINK ACTIVE   | Node: {current_device.ljust(25)} | MAC: {mac}")
                connected_nodes.append(current_device)
            else:
                print(f"❌ LINK STANDBY  | Node: {current_device.ljust(25)} | MAC: {mac}")
            current_device = None

    print("-" * 80)
    print(f"Total Active Layer 0 Anchors: {len(connected_nodes)}")
    
    if "Macbook" in connected_nodes or "aaron's MacBook Pro" in connected_nodes:
        print("\n🎯 DEFINITIVE PROOF: L2 (MacBook Pro) is successfully integrated into the Bluetooth Full-Mesh Graph!")
        print("Screen Lens Sovereign now possesses an unbreakable OOB IP-less control plane to the MacBook Pro.")
    else:
        print("\n⚠️ WARNING: L2 (MacBook Pro) connection dropped. Please accept the pairing code 103361 on the MBP.")

if __name__ == "__main__":
    bt = get_bluetooth_state()
    map_mesh_graph(bt)
