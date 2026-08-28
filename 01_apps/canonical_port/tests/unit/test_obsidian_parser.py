"""
Unit Test Suite: Obsidian Vault Parser & Architecture Graph Engine
Requirements Covered:
- R1. Obsidian YAML Frontmatter Parser with regex fallback.
- R1. Wikilink Dependency Extractor ([[target]], [[target|alias]], [[target#anchor]]).
- R1. In-Memory Architecture Graph Model (indexing directed edges, in/out degrees, dangling links).
- R1. Vault Category Classifier (deterministic 9 canonical categories).
- R1. Tarjan SCC cycle detection and Sugiyama topological stratification.
"""

import os
import sys
import tempfile
from pathlib import Path
import pytest

# Ensure tui package is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))

from models.architecture_graph import (
    WikilinkRef,
    VaultFeature,
    VaultNode,
    ArchitectureGraph,
)
from services.obsidian_vault_parser import ObsidianVaultParser


class TestObsidianFrontmatterParser:
    """Tests for YAML frontmatter extraction and regex fallback."""

    def test_extract_frontmatter_standard_yaml(self):
        parser = ObsidianVaultParser()
        text = (
            "---\n"
            'title: "Core Infrastructure Module"\n'
            'category: "Infrastructure"\n'
            'updated: "2026-08-27"\n'
            "tags: [seaweedfs, docker, tailscale]\n"
            "---\n"
            "# Heading 1\n"
            "Body content here."
        )
        fm, body = parser.extract_frontmatter(text)
        assert fm["title"] == "Core Infrastructure Module"
        assert fm["category"] == "Infrastructure"
        assert fm["updated"] == "2026-08-27"
        assert fm["tags"] == ["seaweedfs", "docker", "tailscale"]
        assert "# Heading 1" in body

    def test_extract_frontmatter_malformed_regex_fallback(self):
        parser = ObsidianVaultParser()
        text = (
            "---\n"
            'title: "Malformed Title"\n'
            "tags: [tag1, tag2, tag3]\n"
            'category: "AI & Inference"\n'
            'updated: "2026-08-26"\n'
            "bad: [unclosed\n"
            "---\n"
            "Body content."
        )
        fm, body = parser.extract_frontmatter(text)
        assert fm.get("title") == "Malformed Title"
        assert "tag1" in fm.get("tags", [])
        assert "tag2" in fm.get("tags", [])
        assert fm.get("category") == "AI & Inference"
        assert fm.get("updated") == "2026-08-26"
        assert "Body content." in body

    def test_extract_frontmatter_empty_or_no_delimiters(self):
        parser = ObsidianVaultParser()
        text = "# Pure Markdown\nNo frontmatter here."
        fm, body = parser.extract_frontmatter(text)
        assert fm == {}
        assert body == text

    def test_extract_frontmatter_yaml_list_format(self):
        parser = ObsidianVaultParser()
        text = (
            "---\n"
            "title: List Tags\n"
            "tags:\n"
            "  - alpha\n"
            "  - beta\n"
            "  - gamma\n"
            "---\n"
            "Content."
        )
        fm, body = parser.extract_frontmatter(text)
        assert fm["title"] == "List Tags"
        assert fm["tags"] == ["alpha", "beta", "gamma"]

    def test_extract_frontmatter_nested_structure_fallback(self):
        parser = ObsidianVaultParser()
        text = (
            "---\n"
            "title: Complex Node\n"
            "category: Tooling & Scripts\n"
            "metadata:\n"
            "  version: 2.0\n"
            "  status: active\n"
            "---\n"
            "Main content."
        )
        fm, body = parser.extract_frontmatter(text)
        assert fm.get("title") == "Complex Node"
        assert fm.get("category") == "Tooling & Scripts"
        assert "Main content." in body


class TestWikilinkExtractor:
    """Tests for Obsidian Wikilink extraction across various syntaxes."""

    def test_extract_standard_wikilinks(self):
        parser = ObsidianVaultParser()
        text = "Check out [[00_core_infrastructure]] and [[01_apps]] for details."
        links = parser.extract_wikilinks(text, source_file="Index")
        assert len(links) == 2
        assert links[0].target_id == "00_core_infrastructure"
        assert links[0].alias is None
        assert links[0].anchor is None
        assert links[0].source_file == "Index"
        assert links[1].target_id == "01_apps"

    def test_extract_aliased_wikilinks(self):
        parser = ObsidianVaultParser()
        text = "See [[CANONICAL_PROJECT_AND_STORAGE_RULE|Storage Rules]] for the full spec."
        links = parser.extract_wikilinks(text)
        assert len(links) == 1
        assert links[0].target_id == "CANONICAL_PROJECT_AND_STORAGE_RULE"
        assert links[0].alias == "Storage Rules"
        assert links[0].display_text == "Storage Rules"

    def test_extract_anchored_wikilinks(self):
        parser = ObsidianVaultParser()
        text = "Refer to [[Hardware_Topology#CPU Topology]] for core specs."
        links = parser.extract_wikilinks(text)
        assert len(links) == 1
        assert links[0].target_id == "Hardware_Topology"
        assert links[0].anchor == "CPU Topology"
        assert links[0].display_text == "Hardware_Topology#CPU Topology"

    def test_extract_anchored_and_aliased_wikilinks(self):
        parser = ObsidianVaultParser()
        text = "Read [[02_ai_models_and_inference#Sharding|RPC Sharding Ports]] now."
        links = parser.extract_wikilinks(text)
        assert len(links) == 1
        assert links[0].target_id == "02_ai_models_and_inference"
        assert links[0].anchor == "Sharding"
        assert links[0].alias == "RPC Sharding Ports"
        assert links[0].display_text == "RPC Sharding Ports"

    def test_extract_subfolder_wikilinks(self):
        parser = ObsidianVaultParser()
        text = "Check [[00_Overview/Hardware_Topology]] in subfolder."
        links = parser.extract_wikilinks(text)
        assert len(links) == 1
        assert links[0].target_id == "Hardware_Topology"
        assert links[0].raw_target == "00_Overview/Hardware_Topology"

    def test_extract_wikilinks_multiple_links_per_paragraph(self):
        parser = ObsidianVaultParser()
        text = "Paragraph with [[Node1]], [[Node2|Two]], and [[Node3#Sec|Three]]."
        links = parser.extract_wikilinks(text)
        assert len(links) == 3
        assert links[0].target_id == "Node1"
        assert links[1].target_id == "Node2"
        assert links[2].target_id == "Node3"

    def test_extract_wikilinks_with_spaces_in_alias(self):
        parser = ObsidianVaultParser()
        text = "Link to [[Target_Node|Long Human Friendly Alias With Spaces]]."
        links = parser.extract_wikilinks(text)
        assert len(links) == 1
        assert links[0].target_id == "Target_Node"
        assert links[0].alias == "Long Human Friendly Alias With Spaces"

    def test_extract_wikilinks_case_preservation(self):
        parser = ObsidianVaultParser()
        text = "Link to [[CamelCaseNode]] and [[UPPER_CASE_NODE]]."
        links = parser.extract_wikilinks(text)
        assert links[0].target_id == "CamelCaseNode"
        assert links[1].target_id == "UPPER_CASE_NODE"


class TestFeatureAndHeadingExtractor:
    """Tests for extracting structured architectural features and headings."""

    def test_extract_headings(self):
        parser = ObsidianVaultParser()
        text = (
            "# Main Architecture\n"
            "Content\n"
            "## Core Subsystems\n"
            "Content\n"
            "### Network Layer\n"
            "Content\n"
        )
        headings = parser.extract_headings(text)
        assert headings == ["Main Architecture", "Core Subsystems", "Network Layer"]

    def test_extract_features_bullet_format(self):
        parser = ObsidianVaultParser()
        text = (
            "## 🏗️ Core Subsystems\n"
            "- **SeaweedFS Distributed File System:** Master (:9333) and Filer (:8888).\n"
            "- **Docker Compose Infrastructure:** Multi-node container sandboxes.\n"
            "1. **Tailscale WireGuard:** L3 mesh routing overlay.\n"
        )
        features = parser.extract_features(text)
        assert len(features) >= 3
        assert features[0].name == "SeaweedFS Distributed File System"
        assert "Master (:9333)" in features[0].description
        assert features[0].section == "🏗️ Core Subsystems"
        assert features[1].name == "Docker Compose Infrastructure"


class TestVaultClassifier:
    """Tests for deterministic category classification."""

    def test_classify_canonical_modules(self):
        parser = ObsidianVaultParser()
        for mod in [
            "00_core_infrastructure",
            "01_apps",
            "02_ai_models_and_inference",
            "03_biometrics_and_telemetry",
            "04_data_and_memory",
            "05_agents_and_swarms",
            "06_scripts_and_tooling",
            "07_docs_and_architecture",
            "08_business_and_commerce",
            "09_app_store_and_release",
            "10_spatial_grappling_kinematics",
            "11_security_and_governance",
            "12_continuous_lora_evolution",
        ]:
            cat = parser.classify_category(mod, {}, mod, Path(f"{mod}.md"))
            assert cat == "Canonical Module", f"Failed for {mod}"

    def test_classify_infrastructure_and_ai(self):
        parser = ObsidianVaultParser()
        cat_infra = parser.classify_category("LIGHTWEIGHT_WIREGUARD_DERP_MESH_SPEC", {}, "WireGuard Mesh", Path("spec.md"))
        assert cat_infra == "Infrastructure"

        cat_ai = parser.classify_category("CUSTOM_AI_SHARDING_DAEMON_PETALS_DHT_SPEC", {}, "Petals AI Sharding", Path("petals.md"))
        assert cat_ai == "AI & Inference"

    def test_classify_swarm_governance_and_audit(self):
        parser = ObsidianVaultParser()
        cat_gov = parser.classify_category("ROUTER_ORCHESTRATOR_CONSENSUS", {}, "Router Orchestrator", Path("router.md"))
        assert cat_gov in ("Swarm & Governance", "Infrastructure")

        cat_audit = parser.classify_category("CODE_AUDIT_RESULTS_AUGUST_26", {}, "Code Audit Results", Path("audit.md"))
        assert cat_audit == "Audit & Telemetry"

    def test_classify_category_custom_frontmatter_override(self):
        parser = ObsidianVaultParser()
        cat = parser.classify_category("custom_note", {"category": "Biometrics & DSP"}, "Custom Note", Path("custom.md"))
        assert cat == "Biometrics & DSP"

    def test_classify_category_docs_and_whitepapers(self):
        parser = ObsidianVaultParser()
        cat = parser.classify_category("LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX", {}, "Deep Index", Path("doc.md"))
        assert cat == "Architecture & Docs"


class TestArchitectureGraphModel:
    """Tests for ArchitectureGraph in-memory index, search, and algorithms."""

    def test_graph_add_nodes_and_edges(self):
        graph = ArchitectureGraph()
        n1 = VaultNode(id="node_a", file_path=Path("node_a.md"), title="Node A", category="Canonical Module")
        n2 = VaultNode(id="node_b", file_path=Path("node_b.md"), title="Node B", category="Infrastructure")
        n3 = VaultNode(id="node_c", file_path=Path("node_c.md"), title="Node C", category="AI & Inference")

        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_node(n3)

        graph.add_edge("node_a", "node_b")
        graph.add_edge("node_a", "node_c")
        graph.add_edge("node_b", "node_c")

        assert len(graph.nodes) == 3
        assert len(graph.edges) == 3
        assert graph.get_out_edges("node_a") == ["node_b", "node_c"]
        assert graph.get_in_edges("node_c") == ["node_a", "node_b"]
        assert n1.out_degree == 2
        assert n3.in_degree == 2

    def test_graph_filtering_and_search(self):
        graph = ArchitectureGraph()
        n1 = VaultNode(id="00_infra", file_path=Path("00_infra.md"), title="Infrastructure", category="Infrastructure", tags=["mesh", "docker"])
        n2 = VaultNode(id="01_apps", file_path=Path("01_apps.md"), title="Applications", category="Canonical Module", tags=["react", "textual"])
        n3 = VaultNode(id="02_ai", file_path=Path("02_ai.md"), title="AI Inference", category="AI & Inference", tags=["llamacpp", "rpc"])

        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_node(n3)

        # Filter by Category
        infra_nodes = graph.filter_nodes(category="Infrastructure")
        assert len(infra_nodes) == 1
        assert infra_nodes[0].id == "00_infra"

        # Search by Query
        search_res = graph.search("textual")
        assert len(search_res) == 1
        assert search_res[0].id == "01_apps"

        # Search across tags
        tag_res = graph.filter_nodes(tags=["rpc"])
        assert len(tag_res) == 1
        assert tag_res[0].id == "02_ai"

    def test_tarjan_scc_cycle_detection(self):
        graph = ArchitectureGraph()
        n1 = VaultNode(id="A", file_path=Path("a.md"), title="A")
        n2 = VaultNode(id="B", file_path=Path("b.md"), title="B")
        n3 = VaultNode(id="C", file_path=Path("c.md"), title="C")
        n4 = VaultNode(id="D", file_path=Path("d.md"), title="D")

        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_node(n3)
        graph.add_node(n4)

        # Cycle: A -> B -> C -> A
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")
        graph.add_edge("C", "A")
        # DAG edge: C -> D
        graph.add_edge("C", "D")

        cycles = graph.find_cycles()
        assert len(cycles) == 1
        assert sorted(cycles[0]) == ["A", "B", "C"]

    def test_sugiyama_stratified_layers(self):
        graph = ArchitectureGraph()
        for nid in ["Root", "Mid1", "Mid2", "Leaf"]:
            graph.add_node(VaultNode(id=nid, file_path=Path(f"{nid}.md"), title=nid))

        graph.add_edge("Root", "Mid1")
        graph.add_edge("Root", "Mid2")
        graph.add_edge("Mid1", "Leaf")
        graph.add_edge("Mid2", "Leaf")

        layers = graph.get_stratified_layers()
        assert len(layers) == 3
        assert layers[0] == ["Root"]
        assert sorted(layers[1]) == ["Mid1", "Mid2"]
        assert layers[2] == ["Leaf"]

    def test_graph_metrics_calculation(self):
        graph = ArchitectureGraph()
        n1 = VaultNode(id="A", file_path=Path("a.md"), title="A", category="Cat1")
        n2 = VaultNode(id="B", file_path=Path("b.md"), title="B", category="Cat2")
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_edge("A", "B")
        graph.dangling_links.add("Dangling_X")

        metrics = graph.get_metrics()
        assert metrics["total_nodes"] == 2
        assert metrics["total_edges"] == 1
        assert metrics["dangling_links_count"] == 1
        assert metrics["categories_count"] == 2
        assert metrics["avg_degree"] == 0.5

    def test_graph_dangling_links_set_indexing(self):
        graph = ArchitectureGraph()
        node = VaultNode(id="Source", file_path=Path("src.md"), title="Source", out_links=[WikilinkRef(target_id="Missing_Target", raw_target="[[Missing_Target]]")])
        graph.add_node(node)
        graph.dangling_links.add("Missing_Target")
        assert "Missing_Target" in graph.dangling_links
        assert graph.get_node("Missing_Target") is None

    def test_graph_bidirectional_degree_symmetry(self):
        graph = ArchitectureGraph()
        n1 = VaultNode(id="X", file_path=Path("x.md"), title="X")
        n2 = VaultNode(id="Y", file_path=Path("y.md"), title="Y")
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_edge("X", "Y")
        assert len(graph.get_out_edges("X")) == len(graph.get_in_edges("Y")) == 1

    def test_graph_search_case_insensitivity_and_partial_match(self):
        graph = ArchitectureGraph()
        graph.add_node(VaultNode(id="LongArchitectureModuleName", file_path=Path("l.md"), title="Long Architecture Module Name"))
        res = graph.search("architecture")
        assert len(res) == 1
        assert res[0].id == "LongArchitectureModuleName"


class TestLiveVaultCrawl:
    """Tests against the live monorepo obsidian_vault directory."""

    def test_live_vault_crawl_integrity(self):
        parser = ObsidianVaultParser()
        graph = parser.parse_vault()

        assert len(graph.nodes) >= 50, f"Expected >=50 nodes, found {len(graph.nodes)}"
        assert len(graph.edges) >= 150, f"Expected >=150 edges, found {len(graph.edges)}"
        assert len(graph.categories) >= 5, f"Expected >=5 categories, found {len(graph.categories)}"
        assert "Canonical Module" in graph.categories
        assert "Infrastructure" in graph.categories

        index_node = graph.get_node("Index")
        assert index_node is not None
        assert index_node.out_degree >= 10
        assert len(index_node.features) >= 10

        core_infra = graph.get_node("00_core_infrastructure")
        assert core_infra is not None
        assert core_infra.category == "Canonical Module"
        assert len(core_infra.features) >= 3

    def test_parse_vault_missing_directory_graceful_handling(self):
        parser = ObsidianVaultParser(vault_path=Path("/tmp/nonexistent_vault_test_dir_12345"))
        graph = parser.parse_vault()
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0
