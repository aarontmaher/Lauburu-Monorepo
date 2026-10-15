import asyncio
import json
import zmq
import time
from datetime import datetime, timezone
try:
    from bleak import BleakScanner, BleakClient
    HAS_BLEAK = True
except ImportError:
    HAS_BLEAK = False

# Standard BLE Heart Rate Service UUID
HR_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
HR_MEASUREMENT_CHAR = "00002a37-0000-1000-8000-00805f9b34fb"

class UniversalBLEBridge:
    def __init__(self, broker_ip="127.0.0.1"):
        self.context = zmq.Context()
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.connect(f"tcp://{broker_ip}:5550")
        
        # Track presence of non-connectable beacons (Keyring)
        self.presence_state = {"keyring_rssi": None, "last_seen": None}

    def hr_data_handler(self, sender, data):
        """Standard GATT 0x180D payload parser (Supports Polar, Whoop, Movesense)"""
        hr_value = data[1] # Basic 8-bit format assumption for simplicity
        
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sensor": "ble_hr_monitor",
            "heart_rate_bpm": hr_value
        }
        self.publisher.send_multipart([b"MESH.TELEMETRY.BIOMETRICS", json.dumps(payload).encode('utf-8')])
        print(f"❤️ [Biometrics] Heart Rate: {hr_value} BPM")

    async def scan_and_connect(self):
        print("🔍 Initiating Sovereign BLE Scan (Looking for Polar, Movesense, Whoop, Keyring)...")
        
        while True:
            try:
                devices = await BleakScanner.discover(timeout=5.0)
                target_hr_device = None
                
                for d in devices:
                    name = d.name or "Unknown"
                    rssi = d.rssi
                    
                    # 1. Keyring / Presence Tracking
                    if "keyring" in name.lower() or "tile" in name.lower() or "smarttag" in name.lower():
                        if self.presence_state["keyring_rssi"] != rssi:
                            self.presence_state = {"keyring_rssi": rssi, "last_seen": time.time()}
                            payload = {"sensor": "keyring", "rssi": rssi, "status": "IN_RANGE"}
                            self.publisher.send_multipart([b"MESH.TELEMETRY.PRESENCE", json.dumps(payload).encode('utf-8')])
                            print(f"🔑 [Presence] Keyring detected. RSSI: {rssi} dBm")
                    
                    # 2. Biometric Sensors
                    if "polar" in name.lower() or "movesense" in name.lower() or "whoop" in name.lower():
                        print(f"🎯 Found target biometric sensor: {name} (RSSI: {rssi})")
                        target_hr_device = d

                # If we found a biometric device, connect and stream
                if target_hr_device:
                    try:
                        async with BleakClient(target_hr_device) as client:
                            print(f"🔗 Connected to {target_hr_device.name}! Subscribing to Heart Rate stream...")
                            await client.start_notify(HR_MEASUREMENT_CHAR, self.hr_data_handler)
                            
                            # Keep connection alive
                            while await client.is_connected():
                                await asyncio.sleep(1)
                    except Exception as e:
                        print(f"Connection lost/failed to {target_hr_device.name}: {e}")
                        
            except Exception as e:
                print(f"BLE Scanner Error (Ensure you are on Mac L1 or Linux L3): {e}")
                
            await asyncio.sleep(5) # Rest before rescanning

if __name__ == "__main__":
    if not HAS_BLEAK:
        print("❌ Error: 'bleak' library not installed. Run: pip install bleak")
    else:
        bridge = UniversalBLEBridge()
        asyncio.run(bridge.scan_and_connect())
