"""
Lauburu Mesh SDK — pip install lauburu-mesh
Smart router across llama.cpp, vLLM, Exo, Petals, Accelerate.
OpenAI-compatible interface with automatic framework selection.

Usage:
    from lauburu_mesh import MeshClient
    client = MeshClient(mesh_host="http://192.168.8.230:8080")
    resp = client.chat.completions.create(
        model="qwen2.5-7b",
        messages=[{"role": "user", "content": "Hello"}]
    )
"""

import time, httpx, json, os
from dataclasses import dataclass, field
from typing import Optional, Literal
from pathlib import Path

# ─── Node registry (auto-discovered, can be overridden) ─────────────────────
MESH_NODES = {
    "mac_mini":    {"host": "192.168.8.230", "tb4": "169.254.106.178", "ram_gb": 24, "gpu": "M4 Pro Metal"},
    "macbook_pro": {"host": "192.168.8.127", "tb4": "169.254.114.190", "ram_gb": 16, "gpu": "M1 Max Metal",  "rpc_port": 50052},
    "macbook_air": {"host": "192.168.8.222", "tb4": "169.254.95.19",   "ram_gb": 16, "gpu": "M4 Metal",     "rpc_port": 50053},
    "linux_head":  {"host": "192.168.8.224",                            "ram_gb": 14, "gpu": "CPU only"},
}

# ─── Framework endpoints ─────────────────────────────────────────────────────
FRAMEWORKS = {
    "llamacpp_rpc": {"url": "http://192.168.8.230:8092", "transport": "TB4_3way", "best_for": "latency"},
    "llamacpp_local":{"url": "http://192.168.8.230:8080", "transport": "local",  "best_for": "small_fast"},
    "vllm":         {"url": "http://192.168.8.230:8100", "transport": "local",   "best_for": "batch"},
    "exo_p2p":      {"url": "http://192.168.8.230:5678", "transport": "TB4+TS",  "best_for": "large_models"},
    "petals_dht":   {"url": "http://192.168.8.224:31330","transport": "LAN+DHT", "best_for": "ultra_large"},
    "cloudflare":   {"url": "https://ai.yourdomain.com", "transport": "internet","best_for": "global_fallback"},
}

@dataclass
class MeshClient:
    mesh_host:      str  = "http://192.168.8.230:8080"
    api_key:        str  = ""
    prefer_local:   bool = True
    max_ttft_ms:    int  = 500
    tunnel_url:     str  = ""                 # Set for internet access via Cloudflare Tunnel
    timeout:        int  = 60
    _framework:     str  = field(default="auto", init=False)

    def __post_init__(self):
        self.chat = _ChatNamespace(self)

    def health(self) -> dict:
        """Check all framework health in parallel."""
        results = {}
        for name, cfg in FRAMEWORKS.items():
            try:
                r = httpx.get(f"{cfg['url']}/health", timeout=2)
                results[name] = {"status": "live" if r.status_code == 200 else "error",
                                 "transport": cfg["transport"]}
            except:
                results[name] = {"status": "down", "transport": cfg["transport"]}
        return results

    def benchmark(self, prompt: str = "Explain model sharding in one sentence.", n: int = 5) -> dict:
        """Run benchmark across all live frameworks."""
        results = {}
        for name, cfg in FRAMEWORKS.items():
            times, tps_list = [], []
            for _ in range(n):
                try:
                    t0 = time.perf_counter()
                    r = httpx.post(f"{cfg['url']}/v1/chat/completions",
                        json={"model": "local", "messages": [{"role":"user","content": prompt}],
                              "max_tokens": 50},
                        timeout=self.timeout)
                    elapsed = (time.perf_counter() - t0) * 1000
                    if r.status_code == 200:
                        data = r.json()
                        tokens = data.get("usage", {}).get("completion_tokens", 10)
                        times.append(elapsed)
                        tps_list.append(tokens / (elapsed / 1000))
                except: pass
            if times:
                results[name] = {
                    "mean_ttft_ms": round(sum(times)/len(times), 1),
                    "mean_tps":     round(sum(tps_list)/len(tps_list), 2),
                    "transport":    cfg["transport"],
                    "samples":      len(times),
                }
        # Save results
        out = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/session_logs/sharding_benchmark_results.json")
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps({"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                   "results": results}, indent=2))
        return results

    def _select_framework(self, messages: list, model: str, hints: dict) -> str:
        """Auto-select optimal framework based on hints + live health."""
        if hints.get("training"): return "accelerate"
        if hints.get("max_ttft_ms", 9999) < 200: return "llamacpp_rpc"
        if hints.get("batch_size", 1) > 5: return "vllm"
        if "70b" in model.lower() or "35b" in model.lower(): return "exo_p2p"
        if "100b" in model.lower(): return "petals_dht"
        return "llamacpp_rpc"


class _ChatNamespace:
    def __init__(self, client: MeshClient): self._c = client
    class completions:
        pass

    def completions_create(self, model: str, messages: list,
                           max_tokens: int = 512, temperature: float = 0.7,
                           stream: bool = False, hints: dict = None) -> dict:
        hints = hints or {}
        framework = self._c._select_framework(messages, model, hints)
        url = FRAMEWORKS.get(framework, FRAMEWORKS["llamacpp_local"])["url"]

        # Internet routing via Cloudflare Tunnel
        if self._c.tunnel_url and not self._c.prefer_local:
            url = self._c.tunnel_url

        r = httpx.post(f"{url}/v1/chat/completions",
            json={"model": model, "messages": messages,
                  "max_tokens": max_tokens, "temperature": temperature, "stream": stream},
            headers={"Authorization": f"Bearer {self._c.api_key}"} if self._c.api_key else {},
            timeout=self._c.timeout)
        data = r.json()
        data["_framework_used"] = framework
        data["_transport"] = FRAMEWORKS.get(framework, {}).get("transport", "unknown")
        return data

    def create(self, **kwargs) -> dict:
        return self.completions_create(**kwargs)
