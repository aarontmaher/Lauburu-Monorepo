# -*- coding: utf-8 -*-
"""
GL.iNet Beryl AX (GL-MT3000/3600) USB 3.0 Port Multiplexer & Hotplug Detector
=============================================================================
Subsystem: 01_apps/glinet_web_optimizer/usb_port_multiplexer.py
Lauburu Mesh Ecosystem — 2026

Dynamically identifies devices connected to the Beryl AX physical USB 3.0 port:
1. Android ADB Target (Samsung S20+ / Pixel) -> Path 4.5/4.75 Hardware ADB Override
2. 5G Cellular USB Modem (CDC-NCM / RNDIS / QMI) -> Multi-WAN lauburu_bond
3. External USB Flash / NVMe Storage -> Model Vault Cache (/tmp/mnt/usb_storage)
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("USBPortMultiplexer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


@dataclass
class USBDeviceProfile:
    detected: bool
    device_type: str  # "ANDROID_ADB", "CELLULAR_5G_MODEM", "STORAGE_DRIVE", "DISCONNECTED"
    vendor_id: Optional[str]
    product_id: Optional[str]
    device_description: str
    active_pathway: str  # e.g., "Path 4.5 Hardware ADB", "Multi-WAN Bonding", "Model Vault"
    interface_name: Optional[str]


class USBPortMultiplexer:
    """
    Auto-detects and configures hardware behaviors on the Beryl AX USB 3.0 port.
    """

    KNOWN_ANDROID_VENDORS = {"04e8", "18d1", "2717", "0bb4"}  # Samsung, Google, Xiaomi, HTC
    KNOWN_CELLULAR_DRIVERS = {"cdc_ncm", "cdc_ether", "rndis_host", "qmi_wwan"}

    def inspect_usb_bus(
        self,
        simulated_devices: Optional[List[Dict[str, str]]] = None,
    ) -> USBDeviceProfile:
        """
        Inspects `/sys/bus/usb/devices/` or `lsusb` output to identify the connected peripheral.
        """
        if simulated_devices is not None:
            # Test / simulated inspection
            for dev in simulated_devices:
                vid = dev.get("vendor_id", "")
                desc = dev.get("description", "")
                driver = dev.get("driver", "")

                if vid in self.KNOWN_ANDROID_VENDORS or "adb" in desc.lower() or "samsung" in desc.lower():
                    return USBDeviceProfile(
                        detected=True,
                        device_type="ANDROID_ADB",
                        vendor_id=vid,
                        product_id=dev.get("product_id", "6860"),
                        device_description=f"Android Device ({desc})",
                        active_pathway="Path 4.5 / 4.75 (Hardware USB ADB Override)",
                        interface_name=None,
                    )
                elif driver in self.KNOWN_CELLULAR_DRIVERS or "modem" in desc.lower() or "rndis" in desc.lower():
                    return USBDeviceProfile(
                        detected=True,
                        device_type="CELLULAR_5G_MODEM",
                        vendor_id=vid,
                        product_id=dev.get("product_id", "0001"),
                        device_description=f"5G Cellular Modem ({desc})",
                        active_pathway="Multi-WAN WAN Bonding (lauburu_bond)",
                        interface_name="usb0",
                    )
                elif "storage" in desc.lower() or "mass" in desc.lower():
                    return USBDeviceProfile(
                        detected=True,
                        device_type="STORAGE_DRIVE",
                        vendor_id=vid,
                        product_id=dev.get("product_id", "1234"),
                        device_description=f"USB Storage ({desc})",
                        active_pathway="Model Vault Cache (/tmp/mnt/usb_storage)",
                        interface_name="sda1",
                    )

        # Real sysfs inspection
        sys_usb = "/sys/bus/usb/devices/"
        if os.path.exists(sys_usb):
            try:
                for entry in os.listdir(sys_usb):
                    dev_path = os.path.join(sys_usb, entry)
                    vid_file = os.path.join(dev_path, "idVendor")
                    if os.path.isfile(vid_file):
                        with open(vid_file, "r") as f:
                            vid = f.read().strip()
                        if vid in self.KNOWN_ANDROID_VENDORS:
                            return USBDeviceProfile(
                                detected=True,
                                device_type="ANDROID_ADB",
                                vendor_id=vid,
                                product_id="detected",
                                device_description="Physical Android Device attached to Beryl AX USB",
                                active_pathway="Path 4.5 / 4.75 (Hardware USB ADB Override)",
                                interface_name=None,
                            )
            except Exception as e:
                logger.warning(f"Error inspecting sysfs USB: {e}")

        # Default: No peripheral attached
        return USBDeviceProfile(
            detected=False,
            device_type="DISCONNECTED",
            vendor_id=None,
            product_id=None,
            device_description="No USB device attached to Beryl AX",
            active_pathway="Idle (Wi-Fi 6 + Ethernet Standard)",
            interface_name=None,
        )
