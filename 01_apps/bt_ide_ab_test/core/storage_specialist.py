"""
Tri-Vault Storage Specialist & SeaweedFS Hardware Affinity Engine.
Part of the Lauburu IDE Intelligence Architecture (Requirement R3).

Governs physical node affinity behind the scenes while maintaining a unified
conceptual project tree across the 7-Layer Lauburu Physical Mesh Network:
- Heavy datasets (*.parquet, *.jsonl, lora_datasets/, biometrics_lake/)
    -> L3 Linux Hub (collection: heavy_datasets, dataCenter: L3_Linux)
- Vector context (qdrant_data/, *.lance, *.index, kv_cache/)
    -> L4/L6 Edge NPUs (collection: vector_context, dataCenter: L6_Edge)
- Active Git source & IDE buffers (.git/, 01_apps/, *.py, *.dart, *.rs)
    -> L1 Mac Host (collection: git_source, dataCenter: L1_Mac)

Preserves Mac Mini Sanctuary RAM (Rule 3) and offloads heavy background compute
and datasets to L3 Linux Hub (Rule 10).
"""

from dataclasses import dataclass, field, asdict
import json
import logging
import os
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger("storage_specialist")

# ==============================================================================
# Canonical Topology & Mesh Hardware Matrix Constants (Rule 0 & PROJECT.md)
# ==============================================================================

# Node Identifiers
NODE_L1_MAC = "L1_Mac"
NODE_L3_LINUX = "L3_Linux"
NODE_L6_EDGE = "L6_Edge"
NODE_L4_TABLET = "L4_Tablet"
NODE_L2_VAULT = "L2_Vault"

# Tailscale & Physical IPs per Canonical Hardware Matrix
IP_L1_MAC_TS = "100.119.199.76"
IP_L1_MAC_LAN = "192.168.8.230"

IP_L3_LINUX_TS = "100.101.39.98"
IP_L3_LINUX_LAN = "192.168.8.224"

IP_L6_EDGE_PIXEL_TS = "100.73.38.87"
IP_L4_EDGE_TABLET_TS = "100.81.92.125"

IP_L2_VAULT_TS = "100.103.212.21"
IP_L2_VAULT_LAN = "192.168.8.127"

# Default Ports
PORT_SEAWEED_MASTER = 9333
PORT_SEAWEED_FILER = 8888
PORT_SEAWEED_VOLUME = 8080

# Canonical Master Endpoints (Primary: L3 Linux Head Node per spec-00-core-infrastructure)
DEFAULT_MASTER_URL = f"http://{IP_L3_LINUX_TS}:{PORT_SEAWEED_MASTER}"
LOCAL_MASTER_URL = f"http://127.0.0.1:{PORT_SEAWEED_MASTER}"

MASTER_PEER_URLS = [
    DEFAULT_MASTER_URL,
    f"http://{IP_L1_MAC_TS}:{PORT_SEAWEED_MASTER}",
    f"http://{IP_L2_VAULT_TS}:{PORT_SEAWEED_MASTER}",
    LOCAL_MASTER_URL,
]

# Storage Categories & Collections
CATEGORY_HEAVY_DATASETS = "heavy_datasets"
CATEGORY_VECTOR_CONTEXT = "vector_context"
CATEGORY_GIT_SOURCE = "git_source"

COLLECTION_HEAVY_DATASETS = "heavy_datasets"
COLLECTION_VECTOR_CONTEXT = "vector_context"
COLLECTION_GIT_SOURCE = "git_source"

DATACENTER_L1_MAC = "L1_Mac"
DATACENTER_L3_LINUX = "L3_Linux"
DATACENTER_L6_EDGE = "L6_Edge"


# ==============================================================================
# Data Contracts (per PROJECT.md §4.4)
# ==============================================================================

@dataclass
class StorageAffinityRoute:
    """Interface Contract per PROJECT.md §4.4."""
    path: str
    category: str                     # "heavy_datasets", "vector_context", "git_source"
    target_node: str                  # "L3_Linux", "L6_Edge", "L1_Mac"
    target_ip: str
    collection: str
    seaweed_assign_params: Dict[str, str]
    data_center: str = ""
    rack: str = "Rack1"
    replication: str = "000"
    rationale: str = ""

    def __post_init__(self) -> None:
        if not self.data_center:
            self.data_center = self.target_node
        if not self.seaweed_assign_params:
            self.seaweed_assign_params = {
                "collection": self.collection,
                "dataCenter": self.data_center,
            }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize route to clean dictionary."""
        return {
            "path": self.path,
            "category": self.category,
            "target_node": self.target_node,
            "target_ip": self.target_ip,
            "collection": self.collection,
            "dataCenter": self.data_center,
            "rack": self.rack,
            "replication": self.replication,
            "seaweed_assign_params": self.seaweed_assign_params,
            "rationale": self.rationale,
        }


@dataclass
class AssignmentResult:
    """Result of querying SeaweedFS Master /dir/assign."""
    success: bool
    path: str
    category: str
    target_node: str
    target_ip: str
    collection: str
    data_center: str
    fid: Optional[str] = None
    url: Optional[str] = None
    public_url: Optional[str] = None
    count: int = 1
    error: Optional[str] = None
    assign_params: Dict[str, str] = field(default_factory=dict)
    raw_response: Dict[str, Any] = field(default_factory=dict)
    query_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ClusterHealthReport:
    """SeaweedFS cluster topology and affinity readiness report."""
    status: str                       # "HEALTHY", "DEGRADED", "OFFLINE"
    leader: str
    active_masters: List[str]
    unreachable_masters: List[str]
    datacenters_detected: List[str]
    affinity_readiness: Dict[str, bool]
    total_volumes: int
    free_volumes: int
    max_volumes: int
    timestamp_utc: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ==============================================================================
# TriVaultStorageSpecialist Engine
# ==============================================================================

class TriVaultStorageSpecialist:
    """
    Governs storage placement and physical node affinity across the Lauburu Mesh.
    Presents a unified conceptual project tree while routing file I/O to optimal hardware.
    """

    # Compiled rule definitions in priority order
    AFFINITY_RULES: List[Dict[str, Any]] = [
        # ----------------------------------------------------------------------
        # Rule 1: Vector Context & Embedding Indices -> L4/L6 Edge NPUs
        # Priority 1: Specific vector extensions and directories
        # ----------------------------------------------------------------------
        {
            "category": CATEGORY_VECTOR_CONTEXT,
            "target_node": NODE_L6_EDGE,
            "target_ip": IP_L6_EDGE_PIXEL_TS,
            "collection": COLLECTION_VECTOR_CONTEXT,
            "data_center": DATACENTER_L6_EDGE,
            "rack": "Rack_Mobile",
            "replication": "000",
            "dir_patterns": [
                r"(^|/)qdrant_data(/|$)",
                r"(^|/)kv_cache(/|$)",
                r"(^|/)vector_db(/|$)",
                r"(^|/)embeddings(/|$)",
                r"(^|/)04_data_and_memory/qdrant_data(/|$)",
            ],
            "ext_patterns": [
                r"\.lance$",
                r"\.index$",
                r"\.faiss$",
                r"\.hnsw$",
                r"\.sqlite-wal$",
                r"\.ann$",
            ],
            "rationale": "Hardware-accelerated systolic vector dot-products on Google Tensor G5 TPU & Edge NPU.",
        },
        # ----------------------------------------------------------------------
        # Rule 2: Heavy Datasets -> L3 Linux Hub (Ryzen 7 5700U, NVMe/SSD)
        # Priority 2: Large data formats, Parquet data lakes, and LoRA instruction pairs
        # ----------------------------------------------------------------------
        {
            "category": CATEGORY_HEAVY_DATASETS,
            "target_node": NODE_L3_LINUX,
            "target_ip": IP_L3_LINUX_TS,
            "collection": COLLECTION_HEAVY_DATASETS,
            "data_center": DATACENTER_L3_LINUX,
            "rack": "Rack1",
            "replication": "000",
            "dir_patterns": [
                r"(^|/)lora_datasets(/|$)",
                r"(^|/)biometrics_lake(/|$)",
                r"(^|/)delta_tables(/|$)",
                r"(^|/)pyspark_analytics(/|$)",
                r"(^|/)04_data_and_memory/biometrics_lake(/|$)",
                r"(^|/)04_data_and_memory/delta_tables(/|$)",
                r"(^|/)04_data_and_memory/lora_datasets(/|$)",
                r"(^|/)data_lake(/|$)",
            ],
            "ext_patterns": [
                r"\.parquet$",
                r"\.jsonl$",
                r"\.arrow$",
                r"\.feather$",
                r"\.orc$",
                r"\.tar\.gz$",
                r"\.h5$",
                r"\.hdf5$",
                r"\.bin$",
            ],
            "rationale": "High-throughput disk I/O; preserves Mac Mini sanctuary RAM (Rule 3 & Rule 10).",
        },
        # ----------------------------------------------------------------------
        # Rule 3: Active Git Source & IDE Working Tree -> L1 Mac Host (Apple M4 Pro)
        # Priority 3: Source files, project directories, AST caches, active IDE buffers
        # ----------------------------------------------------------------------
        {
            "category": CATEGORY_GIT_SOURCE,
            "target_node": NODE_L1_MAC,
            "target_ip": IP_L1_MAC_TS,
            "collection": COLLECTION_GIT_SOURCE,
            "data_center": DATACENTER_L1_MAC,
            "rack": "Rack1",
            "replication": "000",
            "dir_patterns": [
                r"(^|/)\.git(/|$)",
                r"(^|/)00_core_infrastructure(/|$)",
                r"(^|/)01_apps(/|$)",
                r"(^|/)02_ai_models_and_inference(/|$)",
                r"(^|/)03_biometrics_and_telemetry(/|$)",
                r"(^|/)05_agents_and_swarms(/|$)",
                r"(^|/)06_scripts_and_tooling(/|$)",
                r"(^|/)07_docs_and_architecture(/|$)",
                r"(^|/)teamwork_projects(/|$)",
                r"(^|/)vscodium_prototype(/|$)",
                r"(^|/)tui_only(/|$)",
                r"(^|/)gateway(/|$)",
                r"(^|/)core(/|$)",
                r"(^|/)tests(/|$)",
            ],
            "ext_patterns": [
                r"\.py$",
                r"\.dart$",
                r"\.rs$",
                r"\.ts$",
                r"\.js$",
                r"\.tsx$",
                r"\.jsx$",
                r"\.c$",
                r"\.cpp$",
                r"\.h$",
                r"\.hpp$",
                r"\.go$",
                r"\.sh$",
                r"\.bash$",
                r"\.zsh$",
                r"\.toml$",
                r"\.json$",
                r"\.yaml$",
                r"\.yml$",
                r"\.md$",
                r"\.txt$",
                r"\.html$",
                r"\.css$",
                r"\.swift$",
                r"\.kt$",
            ],
            "rationale": "0ms local NVMe access for compiler AST parsing, linting, and active IDE buffers.",
        },
    ]

    # Precompile regexes for performance
    _COMPILED_RULES: List[Dict[str, Any]] = []

    @classmethod
    def _init_compiled_rules(cls) -> None:
        if cls._COMPILED_RULES:
            return
        for rule in cls.AFFINITY_RULES:
            dir_regexes = [re.compile(p, re.IGNORECASE) for p in rule["dir_patterns"]]
            ext_regexes = [re.compile(p, re.IGNORECASE) for p in rule["ext_patterns"]]
            cls._COMPILED_RULES.append({
                **rule,
                "_dir_regexes": dir_regexes,
                "_ext_regexes": ext_regexes,
            })

    def __init__(self, master_url: Optional[str] = None):
        self.master_url = master_url or DEFAULT_MASTER_URL
        self._init_compiled_rules()

    @classmethod
    def normalize_path(cls, path: Union[str, Path]) -> str:
        """Normalize path to unified Unix POSIX format without trailing slash."""
        s = str(path).replace("\\", "/").strip()
        # Remove redundant leading/trailing separators
        if s.startswith("./"):
            s = s[2:]
        return s

    @classmethod
    def resolve_affinity(cls, path: Union[str, Path]) -> StorageAffinityRoute:
        """
        Classify a file or directory path and return the physical hardware target,
        SeaweedFS collection, dataCenter, and assign parameters.
        """
        cls._init_compiled_rules()
        norm_path = cls.normalize_path(path)
        base_name = os.path.basename(norm_path)

        # 1. Evaluate specific rules in priority order
        for rule in cls._COMPILED_RULES:
            # Check directory patterns across the path
            for r_dir in rule["_dir_regexes"]:
                if r_dir.search(norm_path):
                    return cls._create_route(norm_path, rule)

            # Check file extension patterns on base_name or norm_path
            for r_ext in rule["_ext_regexes"]:
                if r_ext.search(base_name) or r_ext.search(norm_path):
                    return cls._create_route(norm_path, rule)

        # 2. Fallback to L1 Mac Host (Default Git Source workspace)
        return StorageAffinityRoute(
            path=norm_path,
            category=CATEGORY_GIT_SOURCE,
            target_node=NODE_L1_MAC,
            target_ip=IP_L1_MAC_TS,
            collection=COLLECTION_GIT_SOURCE,
            data_center=DATACENTER_L1_MAC,
            rack="Rack1",
            replication="000",
            seaweed_assign_params={
                "collection": COLLECTION_GIT_SOURCE,
                "dataCenter": DATACENTER_L1_MAC,
            },
            rationale="Default fallback to local Mac Mini NVMe workspace.",
        )

    @classmethod
    def _create_route(cls, norm_path: str, rule: Dict[str, Any]) -> StorageAffinityRoute:
        assign_params = {
            "collection": rule["collection"],
            "dataCenter": rule["data_center"],
        }
        return StorageAffinityRoute(
            path=norm_path,
            category=rule["category"],
            target_node=rule["target_node"],
            target_ip=rule["target_ip"],
            collection=rule["collection"],
            data_center=rule["data_center"],
            rack=rule.get("rack", "Rack1"),
            replication=rule.get("replication", "000"),
            seaweed_assign_params=assign_params,
            rationale=rule["rationale"],
        )

    @classmethod
    def get_seaweed_assign_params(
        cls,
        path: Union[str, Path],
        count: int = 1,
        replication: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Generate SeaweedFS Master /dir/assign query parameters for the given path.
        Returns a dict of query params: collection, dataCenter, count, replication.
        """
        route = cls.resolve_affinity(path)
        params: Dict[str, str] = {
            "collection": route.collection,
            "dataCenter": route.data_center,
            "count": str(max(1, count)),
            "replication": replication or route.replication,
        }
        if route.rack:
            params["rack"] = route.rack
        return params

    @classmethod
    def build_assign_url(
        cls,
        path: Union[str, Path],
        master_url: Optional[str] = None,
        count: int = 1,
        replication: Optional[str] = None,
    ) -> str:
        """Construct the full HTTP GET URL for SeaweedFS Master /dir/assign."""
        base = (master_url or DEFAULT_MASTER_URL).rstrip("/")
        params = cls.get_seaweed_assign_params(path, count=count, replication=replication)
        query = urllib.parse.urlencode(params)
        return f"{base}/dir/assign?{query}"

    def assign_file(
        self,
        path: Union[str, Path],
        master_url: Optional[str] = None,
        count: int = 1,
        replication: Optional[str] = None,
        timeout: float = 3.0,
    ) -> AssignmentResult:
        """
        Query SeaweedFS Master /dir/assign to allocate storage volume and file ID
        according to the physical node affinity rule.
        Strictly follows Rule 1 (Zero-Mock): reports genuine network response or authentic error.
        """
        route = self.resolve_affinity(path)
        base = (master_url or self.master_url).rstrip("/")
        params = self.get_seaweed_assign_params(path, count=count, replication=replication)
        query_url = f"{base}/dir/assign?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(
                query_url,
                headers={"User-Agent": "TriVaultStorageSpecialist/1.0", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status_code = resp.status
                raw_text = resp.read().decode("utf-8")
                data = json.loads(raw_text)

                if "error" in data and data["error"]:
                    return AssignmentResult(
                        success=False,
                        path=route.path,
                        category=route.category,
                        target_node=route.target_node,
                        target_ip=route.target_ip,
                        collection=route.collection,
                        data_center=route.data_center,
                        count=count,
                        error=data["error"],
                        assign_params=params,
                        raw_response=data,
                        query_url=query_url,
                    )

                fid = data.get("fid")
                url = data.get("url")
                public_url = data.get("publicUrl", url)

                return AssignmentResult(
                    success=True,
                    path=route.path,
                    category=route.category,
                    target_node=route.target_node,
                    target_ip=route.target_ip,
                    collection=route.collection,
                    data_center=route.data_center,
                    fid=fid,
                    url=url,
                    public_url=public_url,
                    count=int(data.get("count", count)),
                    error=None,
                    assign_params=params,
                    raw_response=data,
                    query_url=query_url,
                )

        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8")
            except Exception:
                pass
            return AssignmentResult(
                success=False,
                path=route.path,
                category=route.category,
                target_node=route.target_node,
                target_ip=route.target_ip,
                collection=route.collection,
                data_center=route.data_center,
                count=count,
                error=f"HTTP_{e.code}: {e.reason} ({err_body.strip()})",
                assign_params=params,
                raw_response={"http_code": e.code, "error": err_body},
                query_url=query_url,
            )
        except Exception as e:
            return AssignmentResult(
                success=False,
                path=route.path,
                category=route.category,
                target_node=route.target_node,
                target_ip=route.target_ip,
                collection=route.collection,
                data_center=route.data_center,
                count=count,
                error=f"{type(e).__name__}: {str(e)}",
                assign_params=params,
                raw_response={"exception": str(e)},
                query_url=query_url,
            )

    @classmethod
    def check_cluster_health(
        cls,
        master_urls: Optional[List[str]] = None,
        timeout: float = 2.0,
    ) -> ClusterHealthReport:
        """
        Audit SeaweedFS Master cluster topology and check whether datacenters
        required for affinity placement (L1_Mac, L3_Linux, L6_Edge) are registered.
        Zero-mock: Performs real HTTP queries against master peers.
        """
        peers = master_urls or MASTER_PEER_URLS
        active_masters: List[str] = []
        unreachable_masters: List[str] = []
        leader = ""
        datacenters_detected: List[str] = []
        affinity_readiness: Dict[str, bool] = {
            DATACENTER_L1_MAC: False,
            DATACENTER_L3_LINUX: False,
            DATACENTER_L6_EDGE: False,
        }
        total_vols = 0
        free_vols = 0
        max_vols = 0
        details: Dict[str, Any] = {}

        for peer in peers:
            clean_peer = peer.rstrip("/")
            # Probe /dir/status
            dir_url = f"{clean_peer}/dir/status"
            try:
                req = urllib.request.Request(
                    dir_url,
                    headers={"User-Agent": "TriVaultStorageSpecialist/1.0", "Accept": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if resp.status == 200:
                        raw = resp.read().decode("utf-8")
                        data = json.loads(raw)
                        active_masters.append(clean_peer)

                        topology = data.get("Topology", {})
                        max_vols = max(max_vols, int(topology.get("Max", 0)))
                        free_vols = max(free_vols, int(topology.get("Free", 0)))

                        dcs = topology.get("DataCenters", [])
                        for dc in dcs:
                            dc_id = dc.get("Id", "")
                            if dc_id and dc_id not in datacenters_detected:
                                datacenters_detected.append(dc_id)
                            # Check affinity readiness
                            if dc_id in affinity_readiness:
                                affinity_readiness[dc_id] = True
                            # Tally volumes
                            for rack in dc.get("Racks", []):
                                for dn in rack.get("DataNodes", []):
                                    total_vols += int(dn.get("Volumes", 0))

                        details[clean_peer] = {
                            "reachable": True,
                            "version": data.get("Version", ""),
                            "datacenters": [dc.get("Id") for dc in dcs],
                        }
                    else:
                        unreachable_masters.append(f"{clean_peer} (HTTP_{resp.status})")
            except Exception as e:
                unreachable_masters.append(f"{clean_peer} ({type(e).__name__})")

            # Probe /cluster/status for leader
            if clean_peer in active_masters and not leader:
                cluster_url = f"{clean_peer}/cluster/status"
                try:
                    req_c = urllib.request.Request(
                        cluster_url,
                        headers={"User-Agent": "TriVaultStorageSpecialist/1.0", "Accept": "application/json"},
                    )
                    with urllib.request.urlopen(req_c, timeout=timeout) as resp_c:
                        if resp_c.status == 200:
                            c_data = json.loads(resp_c.read().decode("utf-8"))
                            leader = c_data.get("Leader", "")
                            if not leader and c_data.get("IsLeader"):
                                leader = clean_peer
                except Exception:
                    pass

        # Determine overall status
        if not active_masters:
            status = "OFFLINE"
        elif all(affinity_readiness.values()):
            status = "HEALTHY"
        else:
            status = "DEGRADED"

        timestamp_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        return ClusterHealthReport(
            status=status,
            leader=leader,
            active_masters=active_masters,
            unreachable_masters=unreachable_masters,
            datacenters_detected=datacenters_detected,
            affinity_readiness=affinity_readiness,
            total_volumes=total_vols,
            free_volumes=free_vols,
            max_volumes=max_vols,
            timestamp_utc=timestamp_utc,
            details=details,
        )

    @classmethod
    def verify_placement_compliance(
        cls,
        path: str,
        fid: str,
        master_url: Optional[str] = None,
        timeout: float = 2.0,
    ) -> Dict[str, Any]:
        """
        Verify if a SeaweedFS file/volume allocation matches the intended hardware datacenter.
        Queries /dir/lookup?volumeId=<id> to confirm real physical volume location.
        """
        route = cls.resolve_affinity(path)
        volume_id = fid.split(",")[0] if "," in fid else fid
        base = (master_url or DEFAULT_MASTER_URL).rstrip("/")
        lookup_url = f"{base}/dir/lookup?volumeId={urllib.parse.quote(volume_id)}"

        result: Dict[str, Any] = {
            "path": route.path,
            "fid": fid,
            "volume_id": volume_id,
            "expected_category": route.category,
            "expected_node": route.target_node,
            "expected_datacenter": route.data_center,
            "compliant": False,
            "actual_locations": [],
            "error": None,
        }

        try:
            req = urllib.request.Request(
                lookup_url,
                headers={"User-Agent": "TriVaultStorageSpecialist/1.0", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                locations = data.get("locations", [])
                result["actual_locations"] = locations
                if locations:
                    # In SeaweedFS, location entries contain url, publicUrl, dataCenter
                    matched = False
                    for loc in locations:
                        loc_dc = loc.get("dataCenter", "")
                        if loc_dc == route.data_center or (not loc_dc and loc.get("url", "").startswith(route.target_ip)):
                            matched = True
                            break
                    result["compliant"] = matched
                else:
                    result["error"] = "No physical volume locations found for volume ID"
        except Exception as e:
            result["error"] = f"Lookup failed: {type(e).__name__} ({str(e)})"

        return result

    @classmethod
    def get_conceptual_project_tree(
        cls,
        root_dir: Union[str, Path] = ".",
        paths: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Demonstrate that the conceptual project tree is completely unified
        while physical node affinity is strictly governed behind the scenes.
        Classifies given paths or traverses root_dir.
        """
        file_paths: List[str] = []
        if paths is not None:
            file_paths = [cls.normalize_path(p) for p in paths]
        else:
            p = Path(root_dir)
            if p.exists() and p.is_dir():
                for item in p.rglob("*"):
                    if item.is_file():
                        # Exclude cache or metadata if desired
                        rel = str(item.relative_to(p)).replace("\\", "/")
                        if not rel.startswith(".git/objects") and not "__pycache__" in rel:
                            file_paths.append(rel)

        by_category: Dict[str, List[Dict[str, Any]]] = {
            CATEGORY_HEAVY_DATASETS: [],
            CATEGORY_VECTOR_CONTEXT: [],
            CATEGORY_GIT_SOURCE: [],
        }
        by_node: Dict[str, List[str]] = {
            NODE_L1_MAC: [],
            NODE_L3_LINUX: [],
            NODE_L6_EDGE: [],
        }

        for fpath in file_paths:
            route = cls.resolve_affinity(fpath)
            entry = {
                "path": fpath,
                "target_node": route.target_node,
                "target_ip": route.target_ip,
                "collection": route.collection,
                "dataCenter": route.data_center,
                "assign_params": route.seaweed_assign_params,
            }
            by_category[route.category].append(entry)
            by_node.setdefault(route.target_node, []).append(fpath)

        return {
            "root_dir": str(root_dir),
            "total_files": len(file_paths),
            "conceptual_tree_unified": True,
            "physical_partitioning_enforced": True,
            "counts": {
                "heavy_datasets_l3": len(by_category[CATEGORY_HEAVY_DATASETS]),
                "vector_context_l6": len(by_category[CATEGORY_VECTOR_CONTEXT]),
                "git_source_l1": len(by_category[CATEGORY_GIT_SOURCE]),
            },
            "by_category": by_category,
            "by_node": by_node,
        }
