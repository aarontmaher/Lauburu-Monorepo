import subprocess
import re
import logging
import time
import threading
from typing import Dict, Any, List

logger = logging.getLogger("multi_wan.wifi_optimizer")

class WifiOptimizer:
    """
    Analyzes current Wi-Fi status and automatically optimizes (switches networks)
    if the connection degrades or drops, comparing against known preferred networks.
    Utilizes physical metrics (RSSI, Latency) to overcome macOS location privacy limits.
    """
    
    def __init__(self, rssi_threshold: int = -75, health_threshold: int = 40):
        self.rssi_threshold = rssi_threshold
        self.health_threshold = health_threshold
        self.interface = "en0"
        self.last_optimization_time = 0.0
        self.current_telemetry = self._get_empty_telemetry()
        
        # Start a background loop to constantly evaluate health
        self._running = True
        self._loop_thread = threading.Thread(target=self._optimization_loop, daemon=True)
        self._loop_thread.start()

    def _get_empty_telemetry(self) -> Dict[str, Any]:
        return {
            "connected": False,
            "rssi": -100,
            "noise": -100,
            "tx_rate": 0,
            "mcs_index": 0,
            "channel": "Unknown",
            "phy_mode": "Unknown",
            "ping_latency_ms": 999.0,
            "health_score": 0.0,
            "status": "Disconnected"
        }

    def get_preferred_networks(self) -> List[str]:
        """Fetch the list of preferred Wi-Fi networks saved on macOS."""
        try:
            result = subprocess.run(
                ["networksetup", "-listpreferredwirelessnetworks", self.interface],
                capture_output=True,
                text=True,
                check=True
            )
            lines = result.stdout.strip().split('\n')
            if len(lines) <= 1:
                return []
            return [line.strip() for line in lines[1:] if line.strip()]
        except Exception as e:
            logger.error(f"Failed to get preferred networks: {e}")
            return []

    def _ping_latency(self, target: str = "8.8.8.8") -> float:
        """Measures RTT latency to a target to assess real connection health."""
        try:
            result = subprocess.run(
                ["ping", "-c", "2", "-W", "1000", target],
                capture_output=True,
                text=True
            )
            match = re.search(r'round-trip min/avg/max/stddev = [\d\.]+/(.*?)/[\d\.]+/', result.stdout)
            if match:
                return float(match.group(1))
        except Exception:
            pass
        return 999.0

    def analyze_current_wifi(self) -> Dict[str, Any]:
        """
        Parses system_profiler SPAirPortDataType to extract physical link quality
        and combines it with active ping latency to create a Wi-Fi Health Score.
        """
        status = self._get_empty_telemetry()
        
        try:
            result = subprocess.run(
                ["system_profiler", "SPAirPortDataType"],
                capture_output=True,
                text=True,
                timeout=5
            )
            output = result.stdout
            
            if "Status: Connected" in output or "Current Network Information:" in output:
                status["connected"] = True
                
                # Signal / Noise
                sig_match = re.search(r'Signal / Noise:\s+(-?\d+)\s+dBm\s+/\s+(-?\d+)\s+dBm', output)
                if sig_match:
                    status["rssi"] = int(sig_match.group(1))
                    status["noise"] = int(sig_match.group(2))
                    
                # Tx Rate
                tx_match = re.search(r'Transmit Rate:\s+(\d+)', output)
                if tx_match:
                    status["tx_rate"] = int(tx_match.group(1))
                    
                # MCS Index
                mcs_match = re.search(r'MCS Index:\s+(\d+)', output)
                if mcs_match:
                    status["mcs_index"] = int(mcs_match.group(1))
                    
                # Channel & PHY
                ch_match = re.search(r'Channel:\s+(.*)', output)
                if ch_match:
                    status["channel"] = ch_match.group(1).strip()
                    
                phy_match = re.search(r'PHY Mode:\s+(.*)', output)
                if phy_match:
                    status["phy_mode"] = phy_match.group(1).strip()

            # Active Ping Check
            latency = self._ping_latency()
            status["ping_latency_ms"] = latency
            
            # Compute Wi-Fi Health Score (0-100)
            if not status["connected"]:
                status["health_score"] = 0.0
                status["status"] = "CRITICAL (Disconnected)"
            else:
                # RSSI factor (0 to 50 points). Optimal >= -50, Poor <= -85
                rssi = status["rssi"]
                rssi_score = max(0, min(50, (rssi + 85) * (50 / 35)))
                
                # Latency factor (0 to 50 points). Optimal <= 20ms, Poor >= 200ms
                lat_score = 50 if latency < 20 else max(0, 50 - ((latency - 20) * (50 / 180)))
                if latency >= 999.0:
                    lat_score = 0
                    
                health = round(rssi_score + lat_score, 1)
                status["health_score"] = health
                
                if health >= 80:
                    status["status"] = "EXCELLENT"
                elif health >= 60:
                    status["status"] = "GOOD"
                elif health >= 40:
                    status["status"] = "FAIR"
                else:
                    status["status"] = "POOR"
                    
            self.current_telemetry = status
            return status
            
        except Exception as e:
            logger.error(f"Failed to analyze Wi-Fi: {e}")
            return self.current_telemetry

    def _connect_to_network(self, ssid: str) -> bool:
        """Attempt to connect to a preferred network by name."""
        logger.info(f"📡 Cycling to preferred network: '{ssid}'...")
        try:
            result = subprocess.run(
                ["networksetup", "-setairportnetwork", self.interface, ssid],
                capture_output=True,
                text=True,
                timeout=15
            )
            if "Failed" in result.stdout or "Error" in result.stdout or "Could not" in result.stdout:
                logger.warning(f"Failed to connect to '{ssid}': {result.stdout.strip()}")
                return False
            
            logger.info(f"✅ Successfully associated with '{ssid}'. Validating connection...")
            time.sleep(3) # Wait for DHCP
            return True
        except Exception as e:
            logger.error(f"Exception connecting to '{ssid}': {e}")
            return False

    def trigger_optimization(self) -> bool:
        """Forces the network optimization cycle."""
        logger.warning(f"⚠️ Wi-Fi optimization triggered! Current Health: {self.current_telemetry['health_score']}")
        preferred = self.get_preferred_networks()
        
        if not preferred:
            logger.warning("No preferred networks found to cycle.")
            return False
            
        for i, candidate in enumerate(preferred[:5]): # Try top 5
            self.last_optimization_time = time.time()
            success = self._connect_to_network(candidate)
            if success:
                new_status = self.analyze_current_wifi()
                if new_status["health_score"] >= 60:
                    logger.info(f"🎉 Optimization successful! Latched onto stable connection (Health: {new_status['health_score']})")
                    return True
                else:
                    logger.warning(f"Connection established but health is still poor ({new_status['health_score']}). Continuing cycle...")
        
        logger.error("Failed to find a stable preferred network during optimization cycle.")
        return False

    def _optimization_loop(self):
        """Background thread continuously monitoring and optimizing the connection."""
        while self._running:
            status = self.analyze_current_wifi()
            now = time.time()
            
            # Optimization Cooldown: 2 minutes
            if now - self.last_optimization_time > 120:
                if status["health_score"] < self.health_threshold:
                    self.trigger_optimization()
            
            time.sleep(10) # Poll every 10 seconds
            
    def get_latest_telemetry(self) -> Dict[str, Any]:
        return self.current_telemetry

    def optimize_wifi(self) -> Dict[str, Any]:
        self.trigger_optimization()
        return self.current_telemetry

