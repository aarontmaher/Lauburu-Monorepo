import subprocess
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("cable_analyzer.bridge0")

def get_bridge0_telemetry() -> Optional[Dict[str, Any]]:
    """Polls Darwin Mach netstat -I bridge0 for 40Gbps DMA rates."""
    try:
        cmd = ["netstat", "-I", "bridge0", "-b"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        if len(lines) < 2:
            return None
        
        headers = lines[0].split()
        try:
            ibytes_idx = headers.index("Ibytes")
            obytes_idx = headers.index("Obytes")
        except ValueError:
            return None

        # Parse the second line (data line)
        parts = lines[1].split()
        if len(parts) > max(ibytes_idx, obytes_idx):
            rx_bytes = int(parts[ibytes_idx]) if parts[ibytes_idx].isdigit() else 0
            tx_bytes = int(parts[obytes_idx]) if parts[obytes_idx].isdigit() else 0
            
            return {
                "interface": "bridge0",
                "rx_bytes": rx_bytes,
                "tx_bytes": tx_bytes,
                "timestamp": time.time()
            }
    except Exception as e:
        logger.error(f"Error polling bridge0 telemetry: {e}")
    return None

def get_sysfs_dma_rates() -> Dict[str, Any]:
    """Mock implementation for sysfs 40Gbps DMA rates, since Darwin uses IOKit."""
    return {
        "status": "active",
        "speed": "40Gbps",
        "type": "DMA"
    }

