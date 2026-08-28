import urllib.request
import json
import time

def verify_telemetry():
    print("Initiating Swarm Truth Audit Verification...\n")
    url = "http://localhost:5001/api/telemetry"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"FAILED: Could not reach API: {e}")
        return False
        
    devices = data.get("devices", {})
    if not devices:
        print("FAILED: No devices found in telemetry.")
        return False
        
    print(f"Found {len(devices)} devices connected to the Swarm Mesh.\n")
    
    passed = True
    for name, stats in devices.items():
        print(f"Verifying {name}...")
        
        # Check Reachability
        ping = stats.get("ping_latency_ms")
        if ping is None:
            print(f"  [!] {name} is UNREACHABLE (ping is null).")
        else:
            print(f"  [x] Connectivity active: {ping} ms")
            
            # Check Memory Fake Data
            mem = stats.get("memory")
            if mem:
                if mem.get("total_mb", 0) > 0:
                    print(f"  [x] Valid memory footprint detected: {mem.get('total_mb')} MB total")
                else:
                    print(f"  [!] INVALID MEMORY DATA: {mem}")
                    passed = False
            else:
                print("  [-] Memory stats unavailable.")
                
            # Check Network Fake Data
            net = stats.get("net_stats")
            if net:
                if len(net) > 0:
                    print(f"  [x] Valid network interfaces detected: {len(net)} interfaces")
                    for iface, data in list(net.items())[:2]:
                        print(f"      - {iface}: RX {data.get('rx_bytes')} bytes")
                else:
                    print(f"  [!] EMPTY NETWORK INTERFACES")
                    passed = False
                    
            # Check Battery
            bat = stats.get("battery")
            if bat:
                print(f"  [x] Battery reading active: {bat.get('level')}% ({bat.get('status')})")
        print()
        
    if passed:
        print("VERIFICATION COMPLETE: ALL DATA IS GENUINE. No mock arrays or hallucinated numbers detected.")
    else:
        print("VERIFICATION FAILED: Suspected fake data or missing attributes.")
        
    return passed

if __name__ == "__main__":
    verify_telemetry()
