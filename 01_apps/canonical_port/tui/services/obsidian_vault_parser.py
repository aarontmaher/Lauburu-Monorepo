"""
Canonical Port TUI - Obsidian Vault Parser Service
Version: 1.0.0-CANONICAL
High-performance parser and graph constructor for Obsidian markdown vaults:
- Parses YAML frontmatter with robust regex fallback for malformed headers.
- Extracts Obsidian Wikilinks [[target|alias#anchor]] and resolves bidirectional links.
- Extracts architecture features, headings, and component capabilities.
- Deterministically classifies nodes into 9 canonical architectural categories.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

try:
    from models.architecture_graph import (
        WikilinkRef,
        VaultFeature,
        VaultNode,
        ArchitectureGraph,
    )
except ImportError:
    from tui.models.architecture_graph import (
        WikilinkRef,
        VaultFeature,
        VaultNode,
        ArchitectureGraph,
    )


class ObsidianVaultParser:
    """
    Crawls and parses an Obsidian markdown vault, constructing a rich ArchitectureGraph.
    """

    DEFAULT_VAULT_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault")

    # Canonical module prefix patterns (00..12)
    CANONICAL_MODULE_PREFIXES = [
        "00_", "01_", "02_", "03_", "04_", "05_",
        "06_", "07_", "08_", "09_", "10_", "11_", "12_"
    ]

    # Category classification keyword rules
    CATEGORY_KEYWORDS = {
        "Canonical Module": [
            "canonical_module", "canonical 13-module", "module"
        ],
        "Infrastructure": [
            "infrastructure", "seaweedfs", "docker", "tailscale", "wireguard",
            "derp", "gateway", "router", "wan", "network", "mesh", "speedify",
            "gl_inet", "sovereign", "bonding", "tun_tap", "storage_topology"
        ],
        "AI & Inference": [
            "ai_inference", "inference", "petals", "llama", "gguf", "rpc",
            "exo", "vram", "models", "sharding", "huggingface", "smolagents",
            "vlm", "termius", "ai-debate", "hardware_ram"
        ],
        "Biometrics & DSP": [
            "biometrics", "ecg", "dsp", "pan_tompkins", "movesense", "dfa",
            "ble", "bluetooth", "heart_rate", "kinematics"
        ],
        "Data & Memory": [
            "pyspark", "data", "memory", "lora", "dataset", "qdrant",
            "delta_lake", "sync", "google_workspace", "drive"
        ],
        "Swarm & Governance": [
            "swarm", "debate", "governance", "agent", "orchestrator",
            "consensus", "triad", "council", "teamwork", "shizuku",
            "device-hardware-governor", "deliberation"
        ],
        "Tooling & Scripts": [
            "tooling", "scripts", "ssh", "adb", "wol", "wake_on_lan",
            "automation", "daemon", "self-healing", "cron", "mcp"
        ],
        "Architecture & Docs": [
            "index", "architecture", "canonical_project", "rule",
            "whitepaper", "rfc", "deep_architecture", "global_architecture",
            "hardware_topology", "7_device_mesh"
        ],
        "Audit & Telemetry": [
            "audit", "telemetry", "ledger", "crawl", "triage", "report",
            "results", "anomalies", "state_august", "unfinished", "crash"
        ]
    }

    def __init__(self, vault_path: Optional[Path] = None) -> None:
        if vault_path is not None:
            self.vault_path = Path(vault_path)
        else:
            # Fallback path search
            if self.DEFAULT_VAULT_PATH.exists() and self.DEFAULT_VAULT_PATH.is_dir():
                self.vault_path = self.DEFAULT_VAULT_PATH
            else:
                # Monorepo relative search
                cur = Path(__file__).resolve()
                repo_vault = cur.parents[4] / "obsidian_vault" if len(cur.parents) >= 5 else cur.parent / "obsidian_vault"
                if repo_vault.exists() and repo_vault.is_dir():
                    self.vault_path = repo_vault
                else:
                    self.vault_path = self.DEFAULT_VAULT_PATH

    def parse_vault(self) -> ArchitectureGraph:
        """
        Crawls the vault directory, parses all markdown files, resolves bidirectional links,
        and constructs an ArchitectureGraph.
        """
        graph = ArchitectureGraph()
        if not self.vault_path.exists() or not self.vault_path.is_dir():
            return graph

        # 1. First Pass: Parse each markdown file into a VaultNode
        node_lookup: Dict[str, VaultNode] = {}
        for md_path in sorted(self.vault_path.rglob("*.md")):
            if md_path.name.startswith("."):
                continue
            node = self.parse_file(md_path)
            node_lookup[node.id] = node
            # Also register by lowercase and filename for alias resolution
            node_lookup[node.id.lower()] = node
            graph.add_node(node)

        # 2. Second Pass: Resolve Wikilinks and construct bidirectional edges
        for node in list(graph.nodes.values()):
            resolved_out_links: List[WikilinkRef] = []
            for link in node.out_links:
                target_stem = Path(link.target_id).stem
                matched_node: Optional[VaultNode] = None

                if link.target_id in graph.nodes:
                    matched_node = graph.nodes[link.target_id]
                elif target_stem in graph.nodes:
                    matched_node = graph.nodes[target_stem]
                elif link.target_id.lower() in node_lookup:
                    matched_node = node_lookup[link.target_id.lower()]
                elif target_stem.lower() in node_lookup:
                    matched_node = node_lookup[target_stem.lower()]

                if matched_node:
                    # Update link reference to canonical ID
                    link.target_id = matched_node.id
                    resolved_out_links.append(link)
                    # Add directed edge
                    graph.add_edge(node.id, matched_node.id)
                    # Update target incoming backlinks
                    if node.id not in matched_node.in_links:
                        matched_node.in_links.append(node.id)
                else:
                    # Dangling link target
                    graph.dangling_links.add(link.target_id)
                    resolved_out_links.append(link)

            node.out_links = resolved_out_links
            node.out_degree = len(graph.get_out_edges(node.id))
            node.in_degree = len(graph.get_in_edges(node.id))

        return graph

    def parse_file(self, file_path: Path) -> VaultNode:
        """
        Parses a single Obsidian markdown file into a VaultNode.
        """
        stem = file_path.stem
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                raw_text = f.read()
        except Exception:
            raw_text = ""

        frontmatter, body_text = self.extract_frontmatter(raw_text)

        # Determine Title
        title = frontmatter.get("title")
        if not title:
            # Look for first markdown h1 header in body
            h1_match = re.search(r"^#\s+(.+)$", body_text, flags=re.MULTILINE)
            if h1_match:
                title = h1_match.group(1).strip()
            else:
                title = stem.replace("_", " ")

        # Determine Tags
        tags_raw = frontmatter.get("tags", [])
        tags: List[str] = []
        if isinstance(tags_raw, list):
            for t in tags_raw:
                if t:
                    tags.append(str(t).strip().lstrip("#"))
        elif isinstance(tags_raw, str):
            for t in tags_raw.split(","):
                clean = t.strip().lstrip("#")
                if clean:
                    tags.append(clean)

        # Also extract inline hashtag tags from body (e.g. #tag)
        inline_tags = re.findall(r"(?:^|\s)#([a-zA-Z0-9_\-]+)", body_text)
        for it in inline_tags:
            if it.lower() not in [x.lower() for x in tags] and not it.isdigit():
                tags.append(it)

        # Updated timestamp
        updated = str(frontmatter.get("updated", ""))

        # Extract Wikilinks
        wikilinks = self.extract_wikilinks(raw_text, source_file=stem)

        # Extract Headings and Features
        headings = self.extract_headings(body_text)
        features = self.extract_features(body_text)

        # Classify Category
        category = self.classify_category(stem, frontmatter, title, file_path)

        return VaultNode(
            id=stem,
            file_path=file_path,
            title=title,
            category=category,
            tags=tags,
            updated=updated,
            frontmatter=frontmatter,
            features=features,
            headings=headings,
            raw_content=raw_text,
            out_links=wikilinks,
            in_links=[],
            in_degree=0,
            out_degree=len(wikilinks)
        )

    def extract_frontmatter(self, text: str) -> Tuple[Dict[str, Any], str]:
        """
        Extracts YAML frontmatter delimiters (---) and returns parsed dict and remainder body.
        Implements regex fallback for malformed YAML headers.
        """
        text = text.lstrip("\ufeff")  # Strip UTF-8 BOM if present
        fm_match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", text, flags=re.DOTALL)
        if not fm_match:
            # Check for alternative '...' ending
            fm_match = re.match(r"^---\r?\n(.*?)\r?\n\.\.\.\r?\n(.*)$", text, flags=re.DOTALL)

        if fm_match:
            raw_fm = fm_match.group(1)
            body = fm_match.group(2)
            try:
                parsed = yaml.safe_load(raw_fm)
                if isinstance(parsed, dict):
                    return parsed, body
            except Exception:
                pass

            # Regex Fallback for YAML parsing failures
            fallback_dict: Dict[str, Any] = {}
            title_m = re.search(r"^title:\s*[\"']?(.*?)[\"']?$", raw_fm, flags=re.MULTILINE)
            if title_m:
                fallback_dict["title"] = title_m.group(1).strip()

            tags_m = re.search(r"^tags:\s*\[?([^\n\r]+)", raw_fm, flags=re.MULTILINE)
            if tags_m:
                raw_tags = tags_m.group(1).rstrip("]").strip()
                tags_list = [t.strip().strip("\"'").lstrip("#") for t in raw_tags.split(",") if t.strip()]
                fallback_dict["tags"] = tags_list
            else:
                tag_block = re.search(r"^tags:\s*\n((?:\s*-\s*.*\n?)+)", raw_fm, flags=re.MULTILINE)
                if tag_block:
                    tags_list = [re.sub(r"^\s*-\s*", "", line).strip().strip("\"'").lstrip("#") for line in tag_block.group(1).splitlines() if line.strip()]
                    fallback_dict["tags"] = tags_list

            cat_m = re.search(r"^category:\s*[\"']?(.*?)[\"']?$", raw_fm, flags=re.MULTILINE)
            if cat_m:
                fallback_dict["category"] = cat_m.group(1).strip()

            upd_m = re.search(r"^updated:\s*[\"']?(.*?)[\"']?$", raw_fm, flags=re.MULTILINE)
            if upd_m:
                fallback_dict["updated"] = upd_m.group(1).strip()

            return fallback_dict, body

        return {}, text

    def extract_wikilinks(self, text: str, source_file: str = "") -> List[WikilinkRef]:
        """
        Extracts all Obsidian Wikilinks [[target|alias#anchor]] from markdown text.
        """
        wikilinks: List[WikilinkRef] = []
        # Matches [[target#anchor|alias]] or [[target|alias]] or [[target#anchor]] or [[target]]
        pattern = re.compile(r"\[\[([^\]\|\#]+)(?:\#([^\]\|]+))?(?:\|([^\]]+))?\]\]")

        lines = text.splitlines()
        for line_idx, line in enumerate(lines, 1):
            for match in pattern.finditer(line):
                raw_target = match.group(1).strip()
                anchor = match.group(2).strip() if match.group(2) else None
                alias = match.group(3).strip() if match.group(3) else None

                # Extract canonical stem if target contains folder path
                target_id = Path(raw_target).stem if "/" in raw_target else raw_target

                wikilinks.append(WikilinkRef(
                    target_id=target_id,
                    raw_target=raw_target,
                    alias=alias,
                    anchor=anchor,
                    source_file=source_file,
                    line_number=line_idx
                ))

        return wikilinks

    def extract_headings(self, text: str) -> List[str]:
        """Extracts markdown headings (H1-H6)."""
        headings: List[str] = []
        for line in text.splitlines():
            line_str = line.strip()
            if line_str.startswith("#"):
                m = re.match(r"^#+\s+(.+)$", line_str)
                if m:
                    headings.append(m.group(1).strip())
        return headings

    def extract_features(self, text: str) -> List[VaultFeature]:
        """
        Extracts structured bullet points, feature lists, and subsystem specifications.
        """
        features: List[VaultFeature] = []
        current_section = ""

        lines = text.splitlines()
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                m = re.match(r"^#+\s+(.+)$", stripped)
                if m:
                    current_section = m.group(1).strip()
                continue

            # Check for bullet or numbered list items
            # E.g. - **Feature Name**: Description
            # E.g. 1. **Feature Name:** Description
            # E.g. - [[Link]] — **Description**
            feat_match = re.match(r"^(?:[\*\-\+]|\d+\.)\s+(?:\*\*|__)?([^\*\_:\—\-]+)(?:\*\*|__)?(?:\s*[:\—\-]\s*(.+))?$", stripped)
            if feat_match:
                name = feat_match.group(1).strip()
                desc = feat_match.group(2).strip() if feat_match.group(2) else ""
                # Filter out pure markdown formatting artifacts
                if len(name) > 1 and not name.startswith("[["):
                    features.append(VaultFeature(
                        name=name,
                        description=desc,
                        section=current_section,
                        line_number=idx
                    ))
            elif stripped.startswith("- [[") or stripped.startswith("* [["):
                # E.g. - [[CANONICAL_PROJECT_AND_STORAGE_RULE]] — **Canonical Architecture...**
                link_m = re.match(r"^(?:[\*\-\+])\s+\[\[([^\]]+)\]\]\s*(?:[—\-:\s]+)(.*)$", stripped)
                if link_m:
                    name = link_m.group(1).strip()
                    desc = link_m.group(2).strip()
                    features.append(VaultFeature(
                        name=name,
                        description=desc,
                        section=current_section,
                        line_number=idx
                    ))

        return features

    def classify_category(
        self,
        node_id: str,
        frontmatter: Dict[str, Any],
        title: str,
        path: Path
    ) -> str:
        """
        Deterministically classifies a node into one of the 9 canonical categories.
        """
        # 1. Frontmatter explicit category
        if "category" in frontmatter and frontmatter["category"]:
            explicit = str(frontmatter["category"]).strip()
            for cat in self.CATEGORY_KEYWORDS.keys():
                if explicit.lower() == cat.lower():
                    return cat
            return explicit

        # 2. Canonical 13-Module Check (00_core_infrastructure .. 12_continuous_lora_evolution)
        for pfx in self.CANONICAL_MODULE_PREFIXES:
            if node_id.startswith(pfx):
                return "Canonical Module"

        # 3. Keyword / Tag heuristic scoring
        haystack = f"{node_id} {title} {' '.join(frontmatter.get('tags', []))} {path.name}".lower()

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            if category == "Canonical Module":
                continue
            for kw in keywords:
                if kw in haystack:
                    return category

        # 4. Fallback defaults based on naming conventions
        if "spec" in node_id.lower() or "architecture" in node_id.lower():
            return "Architecture & Docs"

        return "Uncategorized"
