import asyncio
import platform
import subprocess
import logging
from datetime import datetime
from bleak import BleakScanner

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [nRF-Recovery] %(message)s')
logger = logging.getLogger(__name__)

# The specific UUID or Manufacturer ID that the nRF Mesh app / dongle will broadcast when commanding a resurrection.
# Using standard Bluetooth Mesh Provisioning Service UUID as a trigger for this example.
NRF_MESH_PROVISIONING_UUID = "00001827-0000-1000-8000-00805f9b34fb"
CUSTOM_RESURRECTION_NAME = "LAUBURU_OOB_RECOVER"

async def execute_network_resurrection():
    """Executes the out-of-band network recovery sequence based on the OS."""
    logger.warning("🚨 [MESH RESURRECTION] Triggered via nRF Bluetooth Mesh Beacon! Rebuilding network layer...")
    
    os_name = platform.system().lower()
    
    try:
        if os_name == "linux":
            logger.info("Executing Linux recovery (NetworkManager & Tailscale)...")
            subprocess.run(["sudo", "systemctl", "restart", "NetworkManager"], check=False)
            await asyncio.sleep(5)
            subprocess.run(["sudo", "tailscale", "up", "--accept-routes"], check=False)
            
        elif os_name == "darwin":
            logger.info("Executing macOS recovery (en0 bounce & Tailscale)...")
            subprocess.run(["sudo", "ifconfig", "en0", "down"], check=False)
            await asyncio.sleep(2)
            subprocess.run(["sudo", "ifconfig", "en0", "up"], check=False)
            await asyncio.sleep(5)
            # macOS Tailscale CLI path
            subprocess.run(["/Applications/Tailscale.app/Contents/MacOS/Tailscale", "up"], check=False)
            
        else:
            logger.warning(f"OS {os_name} not supported for automated interface bounce. Attempting generic Tailscale restart.")
            subprocess.run(["tailscale", "up"], check=False)

        logger.info("✅ Network layer resurrection sequence completed.")
    except Exception as e:
        logger.error(f"Failed to execute resurrection: {e}")

def detection_callback(device, advertisement_data):
    """Callback triggered on every BLE advertisement seen."""
    # Check if this is our OOB Recovery Beacon
    service_uuids = [str(u).lower() for u in advertisement_data.service_uuids]
    local_name = advertisement_data.local_name or device.name or ""
    
    if NRF_MESH_PROVISIONING_UUID.lower() in service_uuids or local_name == CUSTOM_RESURRECTION_NAME:
        logger.info(f"OOB Beacon Detected from {device.address} (RSSI: {advertisement_data.rssi}dBm)")
        
        # Fire and forget the resurrection task
        asyncio.create_task(execute_network_resurrection())

async def run_mesh_listener():
    """Runs an infinite background BLE scanner listening for nRF Mesh recovery packets."""
    logger.info("Starting nRF Mesh Last-Layer Recovery Daemon...")
    logger.info(f"Listening for OOB Beacons (UUID: {NRF_MESH_PROVISIONING_UUID} or Name: {CUSTOM_RESURRECTION_NAME})")
    
    scanner = BleakScanner(detection_callback)
    
    while True:
        try:
            await scanner.start()
            await asyncio.sleep(30.0) # Scan in 30s blocks
            await scanner.stop()
        except Exception as e:
            logger.error(f"Scanner exception: {e}")
            await asyncio.sleep(5.0)

if __name__ == "__main__":
    try:
        asyncio.run(run_mesh_listener())
    except KeyboardInterrupt:
        logger.info("Shutting down recovery daemon.")
