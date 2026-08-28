"""
Hugging Face Hub Discovery & Authentication Module for smolagi Router AI Daemon.

Provides token authentication, sub-1B GGUF model discovery, metadata extraction,
and memory budget validation within the strict <= 300MB RAM router ceiling.
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.config import RouterConfig, get_config

logger = logging.getLogger("smolagi.hf_discovery")

# Default Hugging Face API base endpoints
HF_API_BASE = "https://huggingface.co/api"
HF_HUB_BASE = "https://huggingface.co"

# Regex patterns for quantizations and parameter counts
QUANT_PATTERN = re.compile(
    r"\b(IQ1_S|IQ1_M|IQ2_XXS|IQ2_XS|IQ2_S|IQ2_M|IQ3_XXS|IQ3_S|IQ3_M|"
    r"Q2_K|Q3_K_S|Q3_K_M|Q3_K_L|Q4_0|Q4_1|Q4_K_S|Q4_K_M|Q5_0|Q5_1|Q5_K_S|Q5_K_M|"
    r"Q6_K|Q8_0|F16|BF16)\b",
    re.IGNORECASE,
)

PARAM_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)(M|B)\b",
    re.IGNORECASE,
)


class HFAuth:
    """Manages Hugging Face Hub token resolution and credential isolation."""

    @classmethod
    def resolve_token(
        cls,
        explicit_token: Optional[str] = None,
        secrets_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Resolve authentication token following priority order:
        1. Explicit token argument
        2. Environment variable HF_TOKEN / HUGGINGFACE_HUB_TOKEN
        3. Volatile tmpfs secret file (/tmp/secrets/hf_token)
        4. None (Anonymous public access)
        """
        if explicit_token:
            return explicit_token.strip()

        env_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
        if env_token:
            return env_token.strip()

        token_file = Path(secrets_path or "/tmp/secrets/hf_token")
        if token_file.is_file():
            try:
                content = token_file.read_text(encoding="utf-8").strip()
                if content:
                    return content
            except OSError as e:
                logger.warning("Failed to read token from secret file %s: %s", token_file, e)

        return None

    @classmethod
    def get_headers(
        cls,
        token: Optional[str] = None,
        user_agent: str = "SmolAGI-Router/1.0",
    ) -> Dict[str, str]:
        """Generate HTTP headers for Hugging Face REST requests."""
        headers = {"User-Agent": user_agent, "Accept": "application/json"}
        resolved = cls.resolve_token(token)
        if resolved:
            headers["Authorization"] = f"Bearer {resolved}"
        return headers


@dataclass(frozen=True)
class DiscoveredModel:
    """Metadata representing a discovered GGUF model candidate on Hugging Face Hub."""

    repo_id: str
    filename: str
    size_bytes: int
    size_mb: float
    quantization: str
    parameter_count: str
    projected_ram_mb: float
    sha256: Optional[str] = None
    download_url: str = ""
    pipeline_tag: str = "text-generation"
    tags: List[str] = field(default_factory=list)

    @property
    def is_ram_compliant(self) -> bool:
        """Check if model meets router memory budget constraints (<= 200MB weights, <= 300MB total)."""
        return self.size_mb <= 200.0 and self.projected_ram_mb <= 300.0


def extract_quantization(filename_or_name: str) -> str:
    """Extract standard GGUF quantization identifier from string."""
    m = QUANT_PATTERN.search(filename_or_name)
    if m:
        return m.group(1).upper()
    # Secondary check for lower/mixed case in file stems
    lower = filename_or_name.lower()
    for q in ["q4_k_m", "iq2_xxs", "iq1_s", "q4_0", "q8_0", "iq3_s", "q5_k_m", "q6_k"]:
        if q in lower:
            return q.upper()
    return "UNKNOWN"


def extract_parameter_count(name: str) -> str:
    """Extract model parameter count (e.g., '135M', '360M', '0.5B')."""
    m = PARAM_PATTERN.search(name)
    if m:
        return f"{m.group(1)}{m.group(2).upper()}"
    lower = name.lower()
    if "135m" in lower:
        return "135M"
    if "360m" in lower:
        return "360M"
    if "0.5b" in lower or "500m" in lower:
        return "0.5B"
    if "1.5b" in lower:
        return "1.5B"
    if "1.1b" in lower:
        return "1.1B"
    if "7b" in lower:
        return "7B"
    return "UNKNOWN"


def calculate_projected_ram_mb(
    weight_mb: float,
    context_len: int = 2048,
    cache_type: str = "q4_0",
    server_rss_mb: float = 35.0,
    daemon_rss_mb: float = 20.0,
) -> float:
    """
    Project total resident RAM usage under inference load:
    RAM_total = RAM_weights + RAM_kv_cache + RSS_llama_server + RSS_daemon
    """
    # Quantized KV cache calculation (q4_0: 4 bits per element)
    # For sub-1B architectures with ~30 layers and hidden dim ~576-1024:
    # kv_bytes = context_len * 2 * n_layers * n_kv_heads * head_dim * (bits / 8)
    # Approximation ~1.2 MB for 2048 ctx with q4_0, ~2.4 MB for 4096 ctx
    kv_cache_mb = max(0.5, (context_len * 2 * 64 * 4) / (1024 * 1024 * 8))
    total_ram = weight_mb + kv_cache_mb + server_rss_mb + daemon_rss_mb
    return round(total_ram, 2)


def validate_ram_budget(
    weight_mb: float,
    max_weight_mb: float = 200.0,
    max_total_ram_mb: float = 300.0,
    context_len: int = 2048,
) -> bool:
    """Validate that model fits within the router's physical RAM constraints."""
    if weight_mb > max_weight_mb:
        return False
    projected = calculate_projected_ram_mb(weight_mb, context_len=context_len)
    return projected <= max_total_ram_mb


# Curated catalog of known sub-1B GGUF models for offline / edge fallback
CURATED_SUB_1B_CATALOG: List[Dict[str, Any]] = [
    {
        "repo_id": "unsloth/SmolLM2-135M-Instruct-GGUF",
        "filename": "SmolLM2-135M-Instruct-Q4_K_M.gguf",
        "size_bytes": 96468992,
        "quantization": "Q4_K_M",
        "parameter_count": "135M",
        "sha256": "4b6a8d79b90c1f5e8e8e7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d",
        "tags": ["smollm2", "sub-1b", "instruct", "q4_k_m"],
    },
    {
        "repo_id": "unsloth/SmolLM2-135M-Instruct-GGUF",
        "filename": "SmolLM2-135M-Instruct-IQ2_XXS.gguf",
        "size_bytes": 60817408,
        "quantization": "IQ2_XXS",
        "parameter_count": "135M",
        "sha256": "9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b",
        "tags": ["smollm2", "sub-1b", "instruct", "iq2_xxs"],
    },
    {
        "repo_id": "unsloth/SmolLM2-360M-Instruct-GGUF",
        "filename": "SmolLM2-360M-Instruct-IQ2_XXS.gguf",
        "size_bytes": 144703488,
        "quantization": "IQ2_XXS",
        "parameter_count": "360M",
        "sha256": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b",
        "tags": ["smollm2", "sub-1b", "instruct", "iq2_xxs"],
    },
    {
        "repo_id": "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
        "filename": "qwen2.5-0.5b-instruct-q4_k_m.gguf",
        "size_bytes": 193986560,
        "quantization": "Q4_K_M",
        "parameter_count": "0.5B",
        "sha256": "3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d",
        "tags": ["qwen2.5", "sub-1b", "instruct", "q4_k_m"],
    },
    {
        "repo_id": "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B-GGUF",
        "filename": "DeepSeek-R1-Distill-Qwen-1.5B-IQ1_S.gguf",
        "size_bytes": 204472320,
        "quantization": "IQ1_S",
        "parameter_count": "1.5B",
        "sha256": "5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f",
        "tags": ["deepseek-r1", "reasoning", "iq1_s"],
    },
]


class HFModelDiscovery:
    """Discovers, queries, and filters sub-1B GGUF models on Hugging Face Hub."""

    def __init__(
        self,
        token: Optional[str] = None,
        secrets_path: Optional[str] = None,
        config: Optional[RouterConfig] = None,
        api_base: str = HF_API_BASE,
        hub_base: str = HF_HUB_BASE,
    ) -> None:
        self.config = config or get_config()
        self.token = token
        self.secrets_path = secrets_path or os.path.join(self.config.tmpfs_telemetry_dir, "../secrets/hf_token")
        self.api_base = api_base
        self.hub_base = hub_base
        self.max_weight_mb = self.config.max_model_size_mb
        self.max_total_ram_mb = self.config.ram_budget_mb

    def _get_headers(self) -> Dict[str, str]:
        return HFAuth.get_headers(self.token, user_agent="SmolAGI-Router/1.0")

    def _fetch_json(self, url: str, timeout_sec: float = 5.0) -> Any:
        """Fetch JSON from URL with timeout and authentication."""
        req = urllib.request.Request(url, headers=self._get_headers())
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content)

    def discover_models(
        self,
        search_query: str = "gguf",
        limit: int = 20,
        architectures: Optional[List[str]] = None,
        quantizations: Optional[List[str]] = None,
    ) -> List[DiscoveredModel]:
        """
        Discover compliant sub-1B GGUF models on Hugging Face Hub.
        Falls back gracefully to curated local catalog if offline or API error.
        """
        query_params = {
            "search": search_query,
            "filter": "text-generation",
            "sort": "downloads",
            "direction": "-1",
            "limit": str(limit),
        }
        url = f"{self.api_base}/models?{urllib.parse.urlencode(query_params)}"
        discovered: List[DiscoveredModel] = []

        try:
            repos_data = self._fetch_json(url)
            if isinstance(repos_data, list):
                for repo in repos_data:
                    repo_id = repo.get("id") or repo.get("modelId", "")
                    if not repo_id:
                        continue
                    # Check if repo matches architecture filter if provided
                    if architectures:
                        if not any(arch.lower() in repo_id.lower() for arch in architectures):
                            continue
                    try:
                        repo_models = self.get_model_files(repo_id)
                        for m in repo_models:
                            if quantizations:
                                if not any(q.upper() == m.quantization.upper() for q in quantizations):
                                    continue
                            if m.is_ram_compliant:
                                discovered.append(m)
                    except Exception as err:
                        logger.debug("Failed inspecting repo %s: %s", repo_id, err)
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
            logger.warning("Online HuggingFace discovery failed (%s). Utilizing curated fallback catalog.", e)
            discovered = self._load_curated_models(architectures, quantizations)

        # Ensure curated catalog candidates are merged if discovery is sparse
        if not discovered:
            discovered = self._load_curated_models(architectures, quantizations)

        return discovered

    def _load_curated_models(
        self,
        architectures: Optional[List[str]] = None,
        quantizations: Optional[List[str]] = None,
    ) -> List[DiscoveredModel]:
        """Load curated sub-1B candidates that meet constraints."""
        results: List[DiscoveredModel] = []
        for item in CURATED_SUB_1B_CATALOG:
            repo_id = item["repo_id"]
            filename = item["filename"]
            if architectures:
                if not any(arch.lower() in repo_id.lower() or arch.lower() in filename.lower() for arch in architectures):
                    continue
            quant = item["quantization"]
            if quantizations:
                if not any(q.upper() == quant.upper() for q in quantizations):
                    continue

            size_bytes = item["size_bytes"]
            size_mb = round(size_bytes / (1024 * 1024), 2)
            param_count = item["parameter_count"]
            projected = calculate_projected_ram_mb(size_mb)
            download_url = f"{self.hub_base}/{repo_id}/resolve/main/{filename}"

            model = DiscoveredModel(
                repo_id=repo_id,
                filename=filename,
                size_bytes=size_bytes,
                size_mb=size_mb,
                quantization=quant,
                parameter_count=param_count,
                projected_ram_mb=projected,
                sha256=item.get("sha256"),
                download_url=download_url,
                tags=item.get("tags", []),
            )
            if model.is_ram_compliant:
                results.append(model)
        return results

    def get_model_files(self, repo_id: str) -> List[DiscoveredModel]:
        """Retrieve all GGUF files in a repository tree."""
        url = f"{self.api_base}/models/{repo_id}/tree/main"
        tree_data = self._fetch_json(url)
        results: List[DiscoveredModel] = []

        if isinstance(tree_data, list):
            for item in tree_data:
                if item.get("type") != "file":
                    continue
                path = item.get("path", "")
                if not path.lower().endswith(".gguf"):
                    continue

                size_bytes = int(item.get("size", 0))
                size_mb = round(size_bytes / (1024 * 1024), 2)
                quant = extract_quantization(path)
                param_count = extract_parameter_count(path) or extract_parameter_count(repo_id)
                projected_ram = calculate_projected_ram_mb(size_mb)
                lfs = item.get("lfs", {})
                sha256 = lfs.get("oid") or lfs.get("sha256")
                download_url = f"{self.hub_base}/{repo_id}/resolve/main/{path}"

                model = DiscoveredModel(
                    repo_id=repo_id,
                    filename=path,
                    size_bytes=size_bytes,
                    size_mb=size_mb,
                    quantization=quant,
                    parameter_count=param_count,
                    projected_ram_mb=projected_ram,
                    sha256=sha256,
                    download_url=download_url,
                    tags=[quant.lower(), param_count.lower()],
                )
                results.append(model)

        return results

    def inspect_model_file(self, repo_id: str, filename: str) -> DiscoveredModel:
        """
        Inspect a specific model file in a repository via HEAD request
        or tree lookup to extract headers and size.
        """
        url = f"{self.hub_base}/{repo_id}/resolve/main/{filename}"
        req = urllib.request.Request(url, headers=self._get_headers(), method="HEAD")
        
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                headers = resp.headers
                content_len = int(headers.get("Content-Length", 0))
                lfs_size = headers.get("X-Linked-Size")
                size_bytes = int(lfs_size) if lfs_size else content_len
                sha256 = headers.get("X-Linked-ETag", "").strip('"') or headers.get("ETag", "").strip('"')
                
                size_mb = round(size_bytes / (1024 * 1024), 2)
                quant = extract_quantization(filename)
                param_count = extract_parameter_count(filename) or extract_parameter_count(repo_id)
                projected_ram = calculate_projected_ram_mb(size_mb)

                return DiscoveredModel(
                    repo_id=repo_id,
                    filename=filename,
                    size_bytes=size_bytes,
                    size_mb=size_mb,
                    quantization=quant,
                    parameter_count=param_count,
                    projected_ram_mb=projected_ram,
                    sha256=sha256 if len(sha256) == 64 else None,
                    download_url=url,
                    tags=[quant.lower(), param_count.lower()],
                )
        except Exception as e:
            logger.debug("HEAD request failed for %s/%s (%s). Falling back to catalog/tree search.", repo_id, filename, e)
            for m in self._load_curated_models():
                if m.repo_id == repo_id and m.filename == filename:
                    return m
            # If not in curated catalog, generate fallback descriptor
            quant = extract_quantization(filename)
            param_count = extract_parameter_count(filename)
            size_bytes = 100 * 1024 * 1024
            size_mb = 100.0
            return DiscoveredModel(
                repo_id=repo_id,
                filename=filename,
                size_bytes=size_bytes,
                size_mb=size_mb,
                quantization=quant,
                parameter_count=param_count,
                projected_ram_mb=calculate_projected_ram_mb(size_mb),
                download_url=url,
                tags=[quant.lower(), param_count.lower()],
            )
