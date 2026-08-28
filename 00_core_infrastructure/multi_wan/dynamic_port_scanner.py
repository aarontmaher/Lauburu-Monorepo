"""
multi_wan/dynamic_port_scanner.py - Autonomous AI Service Port Scanner & Confirmed Port Cache Manager.

Fast Path & Fallback Architecture:
1. Fast Path: Defaults to the last confirmed working IP & port (persisted in /tmp/lauburu_confirmed_ports.json).
2. Fallback Scan: If the primary port probe fails or is unreachable, automatically triggers full subnet & port range scan.
3. Cache Update: Persists newly discovered IP & port as the new confirmed primary.

STRICT MANDATE: ZERO SIMULATED DATA. All discoveries perform real socket connect probes
and HTTP signature fingerprinting.
"""

import asyncio
import json
import logging
import os
import socket
import time
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("multi_wan.dynamic_port_scanner")

# Persistent cache location for confirmed working ports
CONFIRMED_PORTS_CACHE_FILE = "/tmp/lauburu_confirmed_ports.json"

# Default high-probability AI service port candidates
COMMON_AI_PORT_RANGES = [
    # Ollama ports
    11434, 11435, 11436,
    # LM Studio / lmlink / OpenAI API ports
    1234, 1235, 1236, 8900, 8901,
    # Local Web & AGI service ports
    8087, 8088, 8888, 5050, 8000, 8080, 5000, 3000
]

TARGET_MESH_IPS = [
    "127.0.0.1",       # Local host
    "100.101.39.98",   # Linux linux-1
    "100.73.38.87",    # Pixel 10 Pro XL
    "100.99.123.58",   # Samsung S20
    "100.118.79.63",   # Samsung Tablet
]


class DiscoveredAIService:
    """Represents an autonomously discovered AI service endpoint."""

    def __init__(
        self,
        ip: str,
        port: int,
        service_type: str,  # "ollama", "lm_studio", "gemini_service", "openai_compatible"
        name: str,
        models: List[str],
        latency_ms: float,
        endpoint_url: str
    ):
        self.ip = ip
        self.port = port
        self.service_type = service_type
        self.name = name
        self.models = models
        self.latency_ms = latency_ms
        self.endpoint_url = endpoint_url
        self.discovered_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ip": self.ip,
            "port": self.port,
            "service_type": self.service_type,
            "name": self.name,
            "models": self.models,
            "latency_ms": round(self.latency_ms, 2),
            "endpoint_url": self.endpoint_url,
            "discovered_at": self.discovered_at
        }


class ConfirmedPortRegistry:
    """Manages persistent cache of confirmed working ports across restarts."""

    @staticmethod
    def load_cache() -> Dict[str, Dict[str, Any]]:
        if os.path.exists(CONFIRMED_PORTS_CACHE_FILE):
            try:
                with open(CONFIRMED_PORTS_CACHE_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.debug(f"Error reading confirmed ports cache: {e}")
        return {}

    @staticmethod
    def save_cache(cache_data: Dict[str, Dict[str, Any]]):
        try:
            with open(CONFIRMED_PORTS_CACHE_FILE, "w") as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save confirmed ports cache: {e}")

    @classmethod
    def get_confirmed_endpoint(cls, service_key: str, default_ip: str, default_port: int) -> Tuple[str, int]:
        cache = cls.load_cache()
        if service_key in cache:
            entry = cache[service_key]
            return (entry.get("ip", default_ip), int(entry.get("port", default_port)))
        return (default_ip, default_port)

    @classmethod
    def set_confirmed_endpoint(cls, service_key: str, ip: str, port: int, endpoint_url: str):
        cache = cls.load_cache()
        cache[service_key] = {
            "ip": ip,
            "port": port,
            "endpoint_url": endpoint_url,
            "confirmed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        cls.save_cache(cache)


class DynamicPortScanner:
    """
    Autonomous port scanner & fast-path probe engine:
    1. Probes last confirmed IP & port first (Fast Path).
    2. Fallbacks to full range scan if primary port is offline.
    """

    def __init__(self, target_ips: Optional[List[str]] = None, port_list: Optional[List[int]] = None):
        self.target_ips = target_ips or TARGET_MESH_IPS
        self.port_list = port_list or COMMON_AI_PORT_RANGES
        self.discovered_services: Dict[str, DiscoveredAIService] = {}
        self.last_scan_time = 0.0

    def probe_port_tcp(self, ip: str, port: int, timeout: float = 0.6) -> Tuple[bool, float]:
        """Probes TCP socket connection."""
        start = time.time()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            res = sock.connect_ex((ip, port))
            sock.close()
            elapsed = (time.time() - start) * 1000.0
            return (res == 0, elapsed)
        except Exception:
            return (False, 0.0)

    def fingerprint_http_service(self, ip: str, port: int, latency_ms: float) -> Optional[DiscoveredAIService]:
        """
        Queries HTTP endpoints to fingerprint the specific AI service type.
        """
        base_url = f"http://{ip}:{port}"

        # 1. Test Ollama API (/api/tags)
        try:
            req = urllib.request.Request(f"{base_url}/api/tags", headers={"User-Agent": "Lauburu-PortScanner/1.0"})
            with urllib.request.urlopen(req, timeout=1.2) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name") for m in data.get("models", [])] if isinstance(data, dict) else []
                    return DiscoveredAIService(
                        ip=ip, port=port,
                        service_type="ollama",
                        name=f"Ollama Server ({ip}:{port})",
                        models=models,
                        latency_ms=latency_ms,
                        endpoint_url=f"{base_url}/api/tags"
                    )
        except Exception:
            pass

        # 2. Test LM Studio / vLLM / OpenAI compatible (/v1/models)
        try:
            req = urllib.request.Request(f"{base_url}/v1/models", headers={"User-Agent": "Lauburu-PortScanner/1.0"})
            with urllib.request.urlopen(req, timeout=1.2) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("id") for m in data.get("data", [])] if isinstance(data, dict) and "data" in data else []
                    return DiscoveredAIService(
                        ip=ip, port=port,
                        service_type="lm_studio",
                        name=f"LM Studio / vLLM Server ({ip}:{port})",
                        models=models,
                        latency_ms=latency_ms,
                        endpoint_url=f"{base_url}/v1/models"
                    )
        except Exception:
            pass

        # 3. Test Lauburu Gemini Service (/health)
        try:
            req = urllib.request.Request(f"{base_url}/health", headers={"User-Agent": "Lauburu-PortScanner/1.0"})
            with urllib.request.urlopen(req, timeout=1.2) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if isinstance(data, dict) and data.get("service") in ("gemini_service", "lauburu_proxy", "lauburu_dashboard"):
                        return DiscoveredAIService(
                            ip=ip, port=port,
                            service_type="gemini_service",
                            name=f"Lauburu Service ({ip}:{port})",
                            models=["gemini-2.5-flash", "gemini-2.5-pro"],
                            latency_ms=latency_ms,
                            endpoint_url=f"{base_url}/health"
                        )
        except Exception:
            pass

        return None

    def get_service_fast_path_or_scan(
        self,
        service_type: str,
        default_ip: str,
        default_port: int
    ) -> DiscoveredAIService:
        """
        Fast Path & Fallback Workflow:
        1. Reads last confirmed (IP, Port) from persistent cache.
        2. Probes last confirmed endpoint. If ONLINE -> Return immediately (Fast Path hit).
        3. If OFFLINE -> Triggers full scan, updates cache, and returns discovered endpoint.
        """
        conf_ip, conf_port = ConfirmedPortRegistry.get_confirmed_endpoint(service_type, default_ip, default_port)

        # 1. Fast Path Probe on Confirmed Endpoint
        open_flag, latency = self.probe_port_tcp(conf_ip, conf_port, timeout=0.5)
        if open_flag:
            service = self.fingerprint_http_service(conf_ip, conf_port, latency)
            if service and service.service_type == service_type:
                logger.debug(f"⚡ [Fast Path Hit] Service '{service_type}' active at confirmed endpoint {conf_ip}:{conf_port}")
                return service

        # 2. Fallback Scan (Full Subnet & Port Probe)
        logger.info(f"🔍 [Fast Path Miss] Confirmed port {conf_ip}:{conf_port} for '{service_type}' unreachable. Triggering full auto-scan...")
        self.scan_all()

        # 3. Check if discovered during scan
        for key, srv in self.discovered_services.items():
            if srv.service_type == service_type:
                # Update confirmed port cache
                ConfirmedPortRegistry.set_confirmed_endpoint(service_type, srv.ip, srv.port, srv.endpoint_url)
                logger.info(f"✓ Updated confirmed endpoint for '{service_type}' -> {srv.ip}:{srv.port}")
                return srv

        # 4. Return offline stub if unlocated
        return DiscoveredAIService(
            ip=conf_ip,
            port=conf_port,
            service_type=service_type,
            name=f"{service_type} (Offline)",
            models=[],
            latency_ms=0.0,
            endpoint_url=f"http://{conf_ip}:{conf_port}"
        )

    def scan_all(self) -> Dict[str, Any]:
        """
        Executes real socket & HTTP fingerprinting scan across target IPs and port ranges.
        Returns full discovered AI service map and updates confirmed registry cache.
        """
        self.last_scan_time = time.time()
        new_discoveries: Dict[str, DiscoveredAIService] = {}

        for ip in self.target_ips:
            for port in self.port_list:
                open_flag, latency = self.probe_port_tcp(ip, port)
                if open_flag:
                    service = self.fingerprint_http_service(ip, port, latency)
                    if service:
                        key = f"{ip}:{port}"
                        new_discoveries[key] = service
                        ConfirmedPortRegistry.set_confirmed_endpoint(service.service_type, service.ip, service.port, service.endpoint_url)
                        logger.info(f"🔍 Discovered AI Service: {service.name} (Type: {service.service_type}, Models: {len(service.models)})")

        self.discovered_services = new_discoveries
        return self.get_summary()

    def get_summary(self) -> Dict[str, Any]:
        """Returns structured JSON summary of discovered AI services."""
        discovered_list = [s.to_dict() for s in self.discovered_services.values()]
        
        by_type = {}
        for s in self.discovered_services.values():
            if s.service_type not in by_type:
                by_type[s.service_type] = []
            by_type[s.service_type].append(s.to_dict())

        return {
            "discovered_services_count": len(discovered_list),
            "last_scan_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.last_scan_time)) if self.last_scan_time else "NEVER",
            "services_by_type": by_type,
            "confirmed_ports_cache": ConfirmedPortRegistry.load_cache(),
            "all_discovered": discovered_list
        }
