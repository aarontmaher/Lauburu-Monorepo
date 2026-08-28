#!/usr/bin/env python3
"""
Test Obsidian Vault Parser Specification & Schema Validator
"""
import os
import re
import yaml
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Set, Any

@dataclass
class WikilinkRef:
    raw: str
    target: str
    resolved_target: Optional[str] = None
    alias: Optional[str] = None
    heading: Optional[str] = None
    block_id: Optional[str] = None
    is_resolved: bool = False

@dataclass
class VaultFeature:
    name: str
    description: str = ""
    section: str = ""

@dataclass
class VaultNode:
    id: str
    stem: str
    rel_path: str
    base_name: str
    title: str
    category: str
    tags: List[str] = field(default_factory=list)
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    headings: List[str] = field(default_factory=list)
    features: List[VaultFeature] = field(default_factory=list)
    specialist_agent: Optional[str] = None
    outgoing_edges: List[str] = field(default_factory=list)
    incoming_edges: List[str] = field(default_factory=list)
    raw_wikilinks: List[WikilinkRef] = field(default_factory=list)
    dangling_links: List[str] = field(default_factory=list)
    size_bytes: int = 0
    line_count: int = 0
    has_frontmatter: bool = True

class ObsidianVaultParser:
    """Canonical Obsidian Vault Parser Specification Implementation"""
    
    WIKILINK_REGEX = re.compile(r'\[\[(.*?)\]\]')
    FRONTMATTER_REGEX = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
    HEADING_REGEX = re.compile(r'^(#{1,6})\s+(.*)$', re.MULTILINE)
    AGENT_REGEX = re.compile(r'Specialist Agent:\*?\*?\s*`?([a-zA-Z0-9_\-]+)`?')

    def __init__(self, vault_dir: str):
        self.vault_dir = os.path.abspath(vault_dir)
        self.nodes: Dict[str, VaultNode] = {}
        self.edges: List[Dict[str, str]] = []
        self.categories: Set[str] = set()
        self.tags_index: Dict[str, List[str]] = {}
        self.stem_map: Dict[str, str] = {}
        self.base_map: Dict[str, str] = {}
        self.lower_map: Dict[str, str] = {}

    def parse(self) -> Dict[str, VaultNode]:
        # Step 1: Scan all markdown files
        md_files = []
        for root, _, files in os.walk(self.vault_dir):
            if '.git' in root or '.obsidian' in root:
                continue
            for f in files:
                if f.endswith('.md'):
                    md_files.append(os.path.join(root, f))

        # Build index maps for fast wikilink resolution
        for fpath in md_files:
            rel = os.path.relpath(fpath, self.vault_dir)
            stem = os.path.splitext(rel)[0]
            base = os.path.splitext(os.path.basename(fpath))[0]
            self.stem_map[stem] = stem
            self.base_map[base] = stem
            self.lower_map[stem.lower()] = stem
            self.lower_map[base.lower()] = stem

        # Step 2: First pass - Parse node content and metadata
        for fpath in md_files:
            rel = os.path.relpath(fpath, self.vault_dir)
            stem = os.path.splitext(rel)[0]
            base = os.path.splitext(os.path.basename(fpath))[0]
            
            with open(fpath, 'r', encoding='utf-8', errors='replace') as fp:
                content = fp.read()
                
            node = self._parse_file_content(stem, rel, base, content)
            self.nodes[stem] = node
            self.categories.add(node.category)
            for t in node.tags:
                self.tags_index.setdefault(t, []).append(stem)

        # Step 3: Second pass - Resolve wikilinks & construct graph edges
        for stem, node in self.nodes.items():
            for link in node.raw_wikilinks:
                resolved = self._resolve_target(link.clean_target, stem)
                if resolved and resolved in self.nodes:
                    link.resolved_target = resolved
                    link.is_resolved = True
                    if resolved not in node.outgoing_edges:
                        node.outgoing_edges.append(resolved)
                    if stem not in self.nodes[resolved].incoming_edges:
                        self.nodes[resolved].incoming_edges.append(stem)
                    self.edges.append({
                        "source": stem,
                        "target": resolved,
                        "raw": link.raw,
                        "alias": link.alias or ""
                    })
                else:
                    node.dangling_links.append(link.raw)

        return self.nodes

    def _resolve_target(self, target: str, current_stem: str) -> Optional[str]:
        if not target:
            return current_stem
        # Exact stem match (e.g. 00_Overview/Hardware_Topology)
        if target in self.stem_map:
            return self.stem_map[target]
        # Base name match (e.g. Hardware_Topology or 01_apps)
        if target in self.base_map:
            return self.base_map[target]
        # Case-insensitive match
        if target.lower() in self.lower_map:
            return self.lower_map[target.lower()]
        return None

    def _parse_file_content(self, stem: str, rel: str, base: str, content: str) -> VaultNode:
        fm_match = self.FRONTMATTER_REGEX.match(content)
        fm = {}
        body = content
        has_fm = False
        if fm_match:
            has_fm = True
            try:
                parsed = yaml.safe_load(fm_match.group(1))
                if isinstance(parsed, dict):
                    fm = parsed
            except Exception:
                pass
            body = content[fm_match.end():]

        # Extract Headings
        headings = [h[1].strip() for h in self.HEADING_REGEX.findall(body)]
        h1s = [h[1].strip() for h in self.HEADING_REGEX.findall(body) if h[0] == '#']
        title = fm.get('title') or (h1s[0] if h1s else base)

        # Extract Tags
        tags = fm.get('tags', [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',') if t.strip()]
        elif isinstance(tags, list):
            tags = [str(t).strip() for t in tags if str(t).strip()]
        else:
            tags = []

        # Category mapping
        cat = fm.get('category', fm.get('type', None))
        if not cat:
            if re.match(r'^(0[0-9]|1[0-2])_', base):
                cat = "Canonical Module"
            elif "00_overview" in rel.lower():
                cat = "Overview"
            elif any(k in base.lower() for k in ["debate", "consensus", "deliberation"]):
                cat = "AI Debate & Consensus"
            elif "spec" in base.lower():
                cat = "Specification"
            elif any(k in base.lower() for k in ["audit", "ledger", "triage", "crawl"]):
                cat = "Audit & Verification"
            elif any(k in base.lower() for k in ["mesh", "network", "topology", "accelerator", "governor", "sync", "gateway"]):
                cat = "Infrastructure & Mesh"
            elif "app" in base.lower():
                cat = "Applications"
            elif base == "Index":
                cat = "Root Index"
            else:
                cat = "Documentation"

        # Specialist Agent
        specialist_agent = None
        agent_match = self.AGENT_REGEX.search(body)
        if agent_match:
            specialist_agent = agent_match.group(1)

        # Features Extraction
        features = []
        for sec_match in re.finditer(r'##\s+([^\n]+)\n(.*?)(?=\n##|\Z)', body, re.DOTALL):
            sec_title = sec_match.group(1).strip()
            sec_body = sec_match.group(2)
            if any(k in sec_title.lower() for k in ["feature", "module", "algorithm", "component", "endpoint", "protocol", "architecture", "scope", "services", "subsystem"]):
                for line in sec_body.splitlines():
                    line = line.strip()
                    m = re.match(r'^(?:\d+\.|\-|\*)\s+\*?\*?([^\*\:\n]+)\*?\*?(?:\:\s*(.*))?$', line)
                    if m:
                        name = m.group(1).strip()
                        desc = m.group(2).strip() if m.group(2) else ""
                        if len(name) > 2 and not name.startswith("[["):
                            features.append(VaultFeature(name=name, description=desc, section=sec_title))

        # Parse Wikilinks
        wikilinks = []
        for match in self.WIKILINK_REGEX.finditer(content):
            raw_link = match.group(1).strip()
            target = raw_link
            alias = None
            heading = None
            block_id = None

            if "|" in raw_link:
                parts = raw_link.split("|", 1)
                target = parts[0].strip()
                alias = parts[1].strip()

            if "#" in target:
                t_parts = target.split("#", 1)
                target = t_parts[0].strip()
                anchor = t_parts[1].strip()
                if anchor.startswith("^"):
                    block_id = anchor[1:]
                else:
                    heading = anchor

            clean_target = target.strip()
            if clean_target.endswith(".md"):
                clean_target = clean_target[:-3]

            wikilink_ref = WikilinkRef(
                raw=raw_link,
                target=target,
                alias=alias,
                heading=heading,
                block_id=block_id
            )
            # Store clean target on ref for second pass
            wikilink_ref.clean_target = clean_target
            wikilinks.append(wikilink_ref)

        return VaultNode(
            id=stem,
            stem=stem,
            rel_path=rel,
            base_name=base,
            title=title,
            category=cat,
            tags=tags,
            frontmatter=fm,
            headings=headings,
            features=features,
            specialist_agent=specialist_agent,
            raw_wikilinks=wikilinks,
            size_bytes=len(content.encode('utf-8')),
            line_count=len(content.splitlines()),
            has_frontmatter=has_fm
        )

def run_tests():
    vault_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault"
    parser = ObsidianVaultParser(vault_path)
    nodes = parser.parse()

    print(f"Parsed {len(nodes)} nodes successfully.")
    print(f"Total graph edges: {len(parser.edges)}")
    print(f"Total categories: {len(parser.categories)} -> {sorted(list(parser.categories))}")
    print(f"Total indexed tags: {len(parser.tags_index)}")

    # Verification checks
    assert len(nodes) == 51, f"Expected 51 nodes, got {len(nodes)}"
    assert "00_core_infrastructure" in nodes, "00_core_infrastructure missing"
    assert "01_apps" in nodes, "01_apps missing"
    assert "03_biometrics_and_telemetry" in nodes, "03_biometrics_and_telemetry missing"

    # Test edge resolution
    core_infra = nodes["00_core_infrastructure"]
    assert "01_apps" in core_infra.outgoing_edges, "00_core_infrastructure should link to 01_apps"
    assert "11_security_and_governance" in core_infra.outgoing_edges, "00_core_infrastructure should link to 11_security"

    apps_node = nodes["01_apps"]
    assert "00_core_infrastructure" in apps_node.outgoing_edges, "01_apps should link to 00_core_infrastructure"
    assert "03_biometrics_and_telemetry" in apps_node.outgoing_edges, "01_apps should link to 03_biometrics_and_telemetry"

    # Test incoming edge resolution
    assert "00_core_infrastructure" in apps_node.incoming_edges, "01_apps should have incoming edge from 00_core_infrastructure"
    assert "01_apps" in core_infra.incoming_edges, "00_core_infrastructure should have incoming edge from 01_apps"

    # Test features extraction
    assert len(core_infra.features) > 0, "00_core_infrastructure should have extracted features"
    assert len(nodes["03_biometrics_and_telemetry"].features) > 0, "03_biometrics should have extracted features"

    # Test specialist agent extraction
    assert core_infra.specialist_agent == "spec-00-core-infrastructure", f"Got {core_infra.specialist_agent}"
    assert apps_node.specialist_agent == "spec-01-apps-ecosystem", f"Got {apps_node.specialist_agent}"

    print("ALL VERIFICATION ASSERTIONS PASSED PERFECTLY!")

if __name__ == "__main__":
    run_tests()
