#!/usr/bin/env python3
"""
tests/test_nomad_truth_consistency_auditor.py
=============================================
Unit and adversarial test suite for Nomad Truth Consistency Auditor & Anti-Hallucination Scanner.

Verifies:
1. Regex blockers for 5-layer mesh, 5-device mesh, 62.8 GB, 54.65 GB, 55.58 GB, M4 Max, legacy paths.
2. Programmatic dummy file injection tests demonstrating failure & blocking of non-compliant text.
3. Auto-fix repair engine converting legacy metrics to canonical 7-layer / 108.0 GB standards.
4. Strict compliance evaluation and CLI exit codes.
5. Canonical 7-layer mesh topology mathematical invariants.
"""

import os
import sys
import json
import pytest
import tempfile
import subprocess
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling/automation"))

from nomad_truth_consistency_auditor import (
    audit_content,
    auto_fix_content,
    is_compliant,
    verify_mesh_topology,
    audit_file,
    NomadTruthAuditorEngine,
    GROUND_TRUTH_HARDWARE,
    HALLUCINATED_METRIC_PATTERNS,
    SUSPICIOUS_MOCK_PATTERNS
)


class TestNomadTruthAuditorRegexBlockers:
    """Tests regex blockers for catching all forms of legacy 5-layer and outdated RAM hallucinations."""

    @pytest.mark.parametrize("hallucinated_text,expected_pattern", [
        ("The system operates on a 5-layer mesh across nodes.", r"\b5[-\s]layer\s+mesh\b"),
        ("Compute is pooled in a 5 layer mesh.", r"\b5[-\s]layer\s+mesh\b"),
        ("Shard tensor layers across the 5-Layer Mesh.", r"\b5[-\s]layer\s+mesh\b"),
        ("Deploy worker to the 5-device mesh.", r"\b5[-\s]device\s+mesh\b"),
        ("The 5 device mesh coordinates tasks.", r"\b5[-\s]device\s+mesh\b"),
        ("The 5-node mesh coordinates tasks.", r"\b5[-\s]node\s+mesh\b"),
        ("The 5 node mesh coordinates tasks.", r"\b5[-\s]node\s+mesh\b"),
        ("Refer to the 5-Layer Physical Topology diagram.", r"\b5[-\s]layer\s+(?:hardware\s+|physical\s+|cluster\s+)?topology\b"),
        ("Refer to the 5-layer hardware topology.", r"\b5[-\s]layer\s+(?:hardware\s+)?topology\b"),
        ("Running 5-Layer llama.cpp RPC sharding.", r"\b5[-\s]layer\s+(?:llama\.cpp\s+rpc|pooled\s+mesh|distributed\s+mesh|overlay\s+vpn|network|telemetry|sharding)\b"),
        ("Status: 5-Layer Pooled Mesh online.", r"\b5[-\s]layer\s+(?:llama\.cpp\s+rpc|pooled\s+mesh|distributed\s+mesh|overlay\s+vpn|network|telemetry|sharding)\b"),
        ("Stream 4: 5-Layer Mesh Telemetry.", r"\b5[-\s]layer\s+mesh\b"),
        ("Total capacity is 62.8 GB pooled VRAM.", r"\b62\.8\s*GB\b(?!\s*\(old\))"),
        ("Pool 54.65 GB usable AI VRAM across TB4.", r"\b54\.65\s*GB\b"),
        ("VRAM status: 55.58 GB available.", r"\b55\.58\s*GB\b"),
        ("Host node is running on Host M4 Max with 16GB RAM.", r"\bHost\s+M4\s+Max\b"),
        ("Data path located at /Volumes/aaronmaher/Lauburu-Monorepo.", r"/Volumes/aaronmaher"),
        ("Clone repository to /Volumes/Lauburu-Monorepo/apps.", r"/Volumes/Lauburu-Monorepo"),
        ("Warning: Exceeds Mesh 62.8 GB VRAM limit.", r"Exceeds\s+Mesh\s+62\.8\s*GB\s+VRAM"),
        # Adversarial compound edge cases
        ("computes 5-layer hardware mesh sharding", "exact root-cause phrase from SKILL.md"),
        ("5-layer-mesh", "kebab-case identifier"),
        ("5_layer_mesh", "snake-case identifier"),
        ("5-layer hardware mesh", "intermediate hardware qualifier"),
        ("5-layer physical mesh", "intermediate physical qualifier"),
        ("5-layer cluster mesh", "intermediate cluster qualifier"),
        ("5-layer physical hardware mesh", "double intermediate qualifier"),
        ("5-node cluster", "node cluster variant"),
        ("5-node topology", "node topology variant"),
        ("5-node setup", "node setup variant"),
        ("5-node hardware", "node hardware variant"),
        ("5-device cluster", "device cluster variant"),
        ("5-device topology", "device topology variant"),
        ("5-device setup", "device setup variant"),
        ("5-device hardware", "device hardware variant"),
        ("5-layer cluster", "layer cluster variant"),
        ("5-layer architecture", "layer architecture variant"),
        ("5-layer setup", "layer setup variant"),
        ("5-layer hardware", "layer hardware variant"),
        ("5-layer system", "layer system variant"),
        ("5-layer sharding", "layer sharding variant"),
        ("5-layer MoE Router", "MoE router variant"),
        ("sharding over 5 layers", "inverted phrase with over"),
        ("across 5 layers of mesh", "inverted phrase with across"),
        ("pool of 5 nodes", "inverted phrase with pool of"),
        ("62.8GB", "RAM metric without space"),
        ("62.8 GiB", "GiB unit variant"),
        ("62.80 GB", "decimal precision variant"),
        ("54.65GB", "RAM metric without space"),
        ("54.65 GiB", "GiB unit variant"),
        ("55.58GB", "RAM metric without space"),
        ("55.58 GiB", "GiB unit variant"),
        # Additional Adversarial Round 1 variations
        ("five-layer mesh", "word number variant five-layer"),
        ("five layer mesh", "word number variant space separated"),
        ("five-device mesh", "word number device mesh"),
        ("five device mesh", "word number space device mesh"),
        ("five-node mesh", "word number node mesh"),
        ("five node mesh", "word number space node mesh"),
        ("5 tier mesh", "tier variant space"),
        ("5-tier mesh", "tier variant hyphen"),
        ("5-tier topology", "tier topology variant"),
        ("five-tier mesh", "word number tier mesh"),
        ("5-layer edge mesh", "edge modifier mesh"),
        ("5-layer federated mesh", "federated modifier mesh"),
        ("5-node edge cluster", "edge cluster variant"),
        ("5-device edge network", "edge network variant"),
        ("mesh of 5 layers", "prepositional mesh of layers"),
        ("mesh of 5 nodes", "prepositional mesh of nodes"),
        ("mesh of 5 devices", "prepositional mesh of devices"),
        ("topology of 5 layers", "prepositional topology of layers"),
        ("cluster of 5 nodes", "prepositional cluster of nodes"),
        ("cluster of 5 devices", "prepositional cluster of devices"),
        ("cluster of 5 layers", "prepositional cluster of layers"),
        ("Apple M4 Max Mac Mini", "Apple M4 Max Mac Mini hallucination"),
        ("M4 Max Host", "M4 Max Host suffix"),
        ("Mac Mini (M4 Max)", "M4 Max parenthetical"),
        ("host is M4 Max", "lowercase host is M4 Max"),
        ("M4 Max with 16GB RAM", "M4 Max with RAM capacity"),
        ("legacy 5-layer mesh", "legacy prefix without old marker"),
        ("deprecated 5-layer mesh", "deprecated prefix without old marker"),
        ("62.8 GB VRAM", "RAM metric with explicit VRAM"),
        ("54.65 GB VRAM", "RAM metric with explicit VRAM"),
        ("55.58 GB VRAM", "RAM metric with explicit VRAM"),
        ("SHARDING OVER 5-LAYER MESH WITH 62.8 GB VRAM", "uppercase compound phrase"),
        ("5-layer overlay vpn", "overlay vpn modifier"),
        ("Legacy static 5-layer topology notes in Obsidian have been superseded.", "multi-word prefix legacy note"),
        # Round 2 Adversarial Cases: Unicode dashes & whitespace
        ("5\u2013layer mesh", "en-dash 5–layer mesh"),
        ("5\u2014layer mesh", "em-dash 5—layer mesh"),
        ("5\u2212layer mesh", "minus sign 5−layer mesh"),
        ("5\u2011layer mesh", "non-breaking hyphen 5‑layer mesh"),
        ("five\u2013layer mesh", "five en-dash layer mesh"),
        ("five\u2014layer mesh", "five em-dash layer mesh"),
        ("5\u2013node cluster", "5–node cluster en-dash"),
        ("5\u2013device topology", "5–device topology en-dash"),
        ("5\u00A0layer\u00A0mesh", "non-breaking space 5 layer mesh"),
        ("5\u2003layer\u2003mesh", "em space 5 layer mesh"),
        # Round 2 Adversarial Cases: Markdown & Inline Formatting
        ("**5-layer** mesh", "bold layer qualifier"),
        ("**5-layer mesh**", "full bold mesh"),
        ("*5-layer* mesh", "italic layer qualifier"),
        ("`5-layer` mesh", "code backtick layer qualifier"),
        ("`5-layer mesh`", "code backtick full mesh"),
        ("[5-layer mesh](https://example.com)", "markdown link anchor"),
        # Round 2 Adversarial Cases: Natural Language Verbal Phrasing
        ("The mesh is formed of 5 nodes", "verbal phrase formed of 5 nodes"),
        ("The cluster is composed of 5 devices", "verbal phrase composed of 5 devices"),
        ("The mesh is made of 5 layers", "verbal phrase made of 5 layers"),
        ("The network is comprised of 5 nodes", "verbal phrase comprised of 5 nodes"),
        ("The mesh consists of 5 nodes", "verbal phrase consists of 5 nodes"),
        ("The system contains 5 nodes", "verbal phrase contains 5 nodes"),
        ("The cluster includes 5 devices", "verbal phrase includes 5 devices"),
        ("The mesh has 5 layers", "verbal phrase has 5 layers"),
        ("The mesh uses 5 nodes", "verbal phrase uses 5 nodes"),
        ("The cluster spans 5 layers", "verbal phrase spans 5 layers"),
        ("The network spans 5 nodes", "verbal phrase network spans 5 nodes"),
        ("mesh with 5 layers", "associative mesh with 5 layers"),
        ("mesh with 5 nodes", "associative mesh with 5 nodes"),
        ("mesh with 5 devices", "associative mesh with 5 devices"),
        ("mesh consisting of 5 nodes", "participial mesh consisting of 5 nodes"),
        ("mesh comprising 5 layers", "participial mesh comprising 5 layers"),
        ("mesh composed of 5 devices", "participial mesh composed of 5 devices"),
        ("mesh consisting of 5 tiers", "participial mesh consisting of 5 tiers"),
        ("cluster consisting of 5 devices", "participial cluster consisting of 5 devices"),
        ("cluster comprising 5 nodes", "participial cluster comprising 5 nodes"),
        # Round 2 Adversarial Cases: Intermediate Adjectives
        ("across 5 physical layers", "adjective 5 physical layers"),
        ("across 5 distinct nodes", "adjective 5 distinct nodes"),
        ("across 5 individual devices", "adjective 5 individual devices"),
        ("pooling over 5 physical nodes", "adjective pooling over 5 physical nodes"),
        ("distributing over 5 physical devices", "adjective distributing over 5 physical devices"),
        ("sharding over 5 separate nodes", "adjective sharding over 5 separate nodes"),
        ("5 physical layers mesh", "adjective 5 physical layers mesh"),
        ("5 physical nodes cluster", "adjective 5 physical nodes cluster"),
        ("5 distinct nodes topology", "adjective 5 distinct nodes topology"),
        ("5 separate devices cluster", "adjective 5 separate devices cluster"),
        ("cluster of 5 physical nodes", "adjective cluster of 5 physical nodes"),
        ("cluster of 5 distinct devices", "adjective cluster of 5 distinct devices"),
        # Round 2 Adversarial Cases: Extended RAM/VRAM Metrics
        ("62.8 gigabytes", "RAM metric word gigabytes"),
        ("62.8 gigabytes of RAM", "RAM metric word gigabytes of RAM"),
        ("62.8 gigabytes VRAM", "RAM metric word gigabytes VRAM"),
        ("54.65 gigabytes", "RAM metric word gigabytes 54.65"),
        ("55.58 gigabytes", "RAM metric word gigabytes 55.58"),
        ("62.800 GB", "RAM metric 3 decimal precision"),
        ("54.650 GB", "RAM metric 3 decimal precision"),
        ("55.580 GB", "RAM metric 3 decimal precision"),
        ("100.0 GB total mesh RAM", "RAM metric 100.0 GB total mesh RAM"),
        ("104.8 GB mesh", "RAM metric 104.8 GB mesh"),
        # Round 3 Adversarial Cases: Swarms, Fleets, Matrices & Collective Nouns
        ("5-node swarm", "swarm noun 5-node swarm"),
        ("5-device fleet", "fleet noun 5-device fleet"),
        ("5-member swarm", "member swarm 5-member swarm"),
        ("5-peer swarm", "peer swarm 5-peer swarm"),
        ("5-node matrix", "matrix noun 5-node matrix"),
        ("matrix of 5 nodes", "collective matrix of 5 nodes"),
        ("array of 5 nodes", "collective array of 5 nodes"),
        ("group of 5 nodes", "collective group of 5 nodes"),
        ("set of 5 nodes", "collective set of 5 nodes"),
        ("federation of 5 nodes", "collective federation of 5 nodes"),
        ("ensemble of 5 nodes", "collective ensemble of 5 nodes"),
        # Round 3 Adversarial Cases: Machines, Hosts, Units & Hardware Entities
        ("5-machine mesh", "machine mesh 5-machine mesh"),
        ("5-host cluster", "host cluster 5-host cluster"),
        ("5-unit mesh", "unit mesh 5-unit mesh"),
        ("across 5 machines", "preposition across 5 machines"),
        ("across 5 hosts", "preposition across 5 hosts"),
        ("cluster of 5 machines", "collective cluster of 5 machines"),
        ("mesh of 5 hosts", "collective mesh of 5 hosts"),
        ("5 machine cluster", "space machine cluster 5 machine cluster"),
        ("five-host mesh", "word number five-host mesh"),
        # Round 3 Adversarial Cases: Active Natural Language Verbs
        ("The cluster features 5 nodes", "verbal phrase features 5 nodes"),
        ("The mesh utilizes 5 nodes", "verbal phrase utilizes 5 nodes"),
        ("The mesh employs 5 nodes", "verbal phrase employs 5 nodes"),
        ("The network links 5 nodes", "verbal phrase links 5 nodes"),
        ("The topology connects 5 nodes", "verbal phrase connects 5 nodes"),
        ("The mesh incorporates 5 nodes", "verbal phrase incorporates 5 nodes"),
        ("The cluster integrates 5 nodes", "verbal phrase integrates 5 nodes"),
        ("The cluster aggregates 5 nodes", "verbal phrase aggregates 5 nodes"),
        ("The mesh joins 5 nodes", "verbal phrase joins 5 nodes"),
        # Round 3 Adversarial Cases: Standalone Physical Adjective-Noun Pairs
        ("5 physical nodes", "standalone 5 physical nodes"),
        ("5 physical devices", "standalone 5 physical devices"),
        ("5 physical layers", "standalone 5 physical layers"),
        ("5 edge nodes", "standalone 5 edge nodes"),
        ("5 edge devices", "standalone 5 edge devices"),
        ("5 hardware nodes", "standalone 5 hardware nodes"),
        ("5 connected nodes", "standalone 5 connected nodes"),
        ("5 federated devices", "standalone 5 federated devices"),
        ("5 local nodes", "standalone 5 local nodes"),
        ("5 separate nodes", "standalone 5 separate nodes"),
        ("5 distinct nodes", "standalone 5 distinct nodes"),
        ("5 individual nodes", "standalone 5 individual nodes"),
        ("5 heterogeneous nodes", "standalone 5 heterogeneous nodes"),
        # Round 3 Adversarial Cases: Expanded RAM Metric Variations
        ("100 GB total mesh RAM", "RAM metric 100 GB total mesh RAM"),
        ("100 GB mesh RAM", "RAM metric 100 GB mesh RAM"),
        ("100 GB pooled RAM", "RAM metric 100 GB pooled RAM"),
        ("100 GB cluster RAM", "RAM metric 100 GB cluster RAM"),
        ("100 GB total RAM", "RAM metric 100 GB total RAM"),
        ("100.0 GB total RAM", "RAM metric 100.0 GB total RAM"),
        ("100.00 GB total RAM", "RAM metric 100.00 GB total RAM")
    ])
    def test_catches_individual_hallucinations(self, hallucinated_text, expected_pattern):
        findings = audit_content(hallucinated_text)
        assert len(findings) > 0, f"Failed to detect hallucination in: {hallucinated_text} (expected: {expected_pattern})"
        assert any(f["severity"] == "CRITICAL" for f in findings)
        assert not is_compliant(findings)
        assert not is_compliant(hallucinated_text)

    def test_auto_fix_repairs_all_adversarial_patterns(self):
        """Ensures every single hallucination test pattern is 100% cleanly repaired by auto_fix_content."""
        test_inputs = [
            "The system operates on a 5-layer mesh across nodes.",
            "Compute is pooled in a 5 layer mesh.",
            "Shard tensor layers across the 5-Layer Mesh.",
            "Deploy worker to the 5-device mesh.",
            "The 5-node mesh coordinates tasks.",
            "Refer to the 5-Layer Physical Topology diagram.",
            "Running 5-Layer llama.cpp RPC sharding.",
            "Status: 5-Layer Pooled Mesh online.",
            "Stream 4: 5-Layer Mesh Telemetry.",
            "Total capacity is 62.8 GB pooled VRAM.",
            "Pool 54.65 GB usable AI VRAM across TB4.",
            "VRAM status: 55.58 GB available.",
            "Host node is running on Host M4 Max with 16GB RAM.",
            "Data path located at /Volumes/aaronmaher/Lauburu-Monorepo.",
            "Clone repository to /Volumes/Lauburu-Monorepo/apps.",
            "Warning: Exceeds Mesh 62.8 GB VRAM limit.",
            "computes 5-layer hardware mesh sharding",
            "5-layer-mesh",
            "5-node cluster",
            "5-node topology",
            "5-node setup",
            "5-node hardware",
            "5-device cluster",
            "5-device topology",
            "5-device setup",
            "5-device hardware",
            "5-layer cluster",
            "5-layer architecture",
            "5-layer setup",
            "5-layer hardware",
            "5-layer system",
            "5-layer sharding",
            "5-layer MoE Router",
            "sharding over 5 layers",
            "across 5 layers of mesh",
            "pool of 5 nodes",
            "62.8GB",
            "62.8 GiB",
            "62.80 GB",
            "54.65GB",
            "54.65 GiB",
            "55.58GB",
            "55.58 GiB",
            "five-layer mesh",
            "five layer mesh",
            "five-device mesh",
            "five-node mesh",
            "5 tier mesh",
            "5-tier mesh",
            "5-tier topology",
            "five-tier mesh",
            "5-layer edge mesh",
            "5-layer federated mesh",
            "5-node edge cluster",
            "5-device edge network",
            "mesh of 5 layers",
            "mesh of 5 nodes",
            "mesh of 5 devices",
            "topology of 5 layers",
            "cluster of 5 nodes",
            "cluster of 5 devices",
            "cluster of 5 layers",
            "Apple M4 Max Mac Mini",
            "M4 Max Host",
            "Mac Mini (M4 Max)",
            "host is M4 Max",
            "M4 Max with 16GB RAM",
            "legacy 5-layer mesh",
            "62.8 GB VRAM",
            "54.65 GB VRAM",
            "55.58 GB VRAM",
            "SHARDING OVER 5-LAYER MESH WITH 62.8 GB VRAM",
            "5-layer overlay vpn",
            "Legacy static 5-layer topology notes in Obsidian have been superseded.",
            # Round 2 Adversarial Cases
            "5\u2013layer mesh",
            "5\u2014layer mesh",
            "5\u2212layer mesh",
            "5\u2011layer mesh",
            "five\u2013layer mesh",
            "five\u2014layer mesh",
            "5\u2013node cluster",
            "5\u2013device topology",
            "**5-layer** mesh",
            "**5-layer mesh**",
            "*5-layer* mesh",
            "`5-layer` mesh",
            "`5-layer mesh`",
            "[5-layer mesh](https://example.com)",
            "The mesh is formed of 5 nodes",
            "The cluster is composed of 5 devices",
            "The mesh is made of 5 layers",
            "The network is comprised of 5 nodes",
            "The mesh consists of 5 nodes",
            "The system contains 5 nodes",
            "The cluster includes 5 devices",
            "The mesh has 5 layers",
            "The mesh uses 5 nodes",
            "The cluster spans 5 layers",
            "The network spans 5 nodes",
            "mesh with 5 layers",
            "mesh with 5 nodes",
            "mesh with 5 devices",
            "mesh consisting of 5 nodes",
            "mesh comprising 5 layers",
            "mesh composed of 5 devices",
            "mesh consisting of 5 tiers",
            "cluster consisting of 5 devices",
            "cluster comprising 5 nodes",
            "across 5 physical layers",
            "across 5 distinct nodes",
            "across 5 individual devices",
            "pooling over 5 physical nodes",
            "distributing over 5 physical devices",
            "sharding over 5 separate nodes",
            "5 physical layers mesh",
            "5 physical nodes cluster",
            "5 distinct nodes topology",
            "5 separate devices cluster",
            "cluster of 5 physical nodes",
            "cluster of 5 distinct devices",
            "62.8 gigabytes",
            "62.8 gigabytes of RAM",
            "62.8 gigabytes VRAM",
            "54.65 gigabytes",
            "55.58 gigabytes",
            "62.800 GB",
            "54.650 GB",
            "55.580 GB",
            "100.0 GB total mesh RAM",
            "104.8 GB mesh",
            # Round 3 Adversarial Auto-Fix Test Inputs
            "5-node swarm",
            "5-device fleet",
            "5-member swarm",
            "5-peer swarm",
            "5-node matrix",
            "matrix of 5 nodes",
            "array of 5 nodes",
            "group of 5 nodes",
            "set of 5 nodes",
            "federation of 5 nodes",
            "ensemble of 5 nodes",
            "5-machine mesh",
            "5-host cluster",
            "5-unit mesh",
            "across 5 machines",
            "across 5 hosts",
            "cluster of 5 machines",
            "mesh of 5 hosts",
            "5 machine cluster",
            "five-host mesh",
            "The cluster features 5 nodes",
            "The mesh utilizes 5 nodes",
            "The mesh employs 5 nodes",
            "The network links 5 nodes",
            "The topology connects 5 nodes",
            "The mesh incorporates 5 nodes",
            "The cluster integrates 5 nodes",
            "The cluster aggregates 5 nodes",
            "The mesh joins 5 nodes",
            "5 physical nodes",
            "5 physical devices",
            "5 physical layers",
            "5 edge nodes",
            "5 edge devices",
            "5 hardware nodes",
            "5 connected nodes",
            "5 federated devices",
            "5 local nodes",
            "5 separate nodes",
            "5 distinct nodes",
            "5 individual nodes",
            "5 heterogeneous nodes",
            "100 GB total mesh RAM",
            "100 GB mesh RAM",
            "100 GB pooled RAM",
            "100 GB cluster RAM",
            "100 GB total RAM",
            "100.0 GB total RAM",
            "100.00 GB total RAM"
        ]
        for item in test_inputs:
            fixed, mod = auto_fix_content(item)
            assert mod is True, f"auto_fix_content did not modify: {item}"
            findings = audit_content(fixed)
            assert len(findings) == 0, f"auto_fix_content left findings in '{item}' -> '{fixed}': {findings}"
            assert is_compliant(fixed) is True

    def test_catches_mock_data_patterns(self):
        mock_snippets = [
            "const data = mock_data;",
            "auth_token: fake_token",
            "ping_time = simulated_rtt",
            "send(dummy_payload)",
            "host_ip = placeholder_ip",
            "// TODO: replace with real data",
            "// FIXME: fake value used for test"
        ]
        for snippet in mock_snippets:
            findings = audit_content(snippet)
            assert len(findings) > 0, f"Failed to flag mock pattern in: {snippet}"
            assert any(f["severity"] == "HIGH" for f in findings)
            assert not is_compliant(findings)

    def test_clean_canonical_content_passes(self):
        canonical_texts = [
            "The cluster operates as a 7-Layer Mesh with 108.0 GB RAM (82.8 GB Usable AI VRAM Headroom).",
            "Host: Apple M4 Pro Mac Mini (24 GB RAM, 100.119.199.76).",
            "Layer 5 Compute: Apple M4 MacBook Air (16 GB RAM, 100.93.158.96).",
            "Repo path: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling.",
            "All sensors stream authentic 512Hz ECG data with zero mock arrays.",
            "Historical benchmark logged at 62.8 GB (old) for reference."
        ]
        for text in canonical_texts:
            findings = audit_content(text)
            assert len(findings) == 0, f"False positive detected on clean content: {findings}"
            assert is_compliant(text)

    @pytest.mark.parametrize("nn_model_text", [
        "// one autoregressive decode step of the 5-layer code_predictor. See the",
        "Trained a 5-layer neural network for fast feature extraction.",
        "The architecture is a 5-layer transformer encoder.",
        "Using a 5-layer CNN for edge image preprocessing.",
        "A 5-layer MLP regressor maps sensor signals.",
        "5-layer perceptron baseline model.",
        "5-layer deep learning model backbone.",
        "5-layer ResNet backbone for spatial tracking.",
        "5-layer protocol stack for local socket serialization.",
        "5-layer convolutional network for spectrograph DSP.",
        "5-layer autoencoder model for latent embedding.",
        "5-layer LSTM network for heart rate sequence prediction.",
        "5-layer GAN generator model.",
        "5-layer transformer decoder with 8 heads.",
        "5-layer feedforward network.",
        "5-layer dense network with dropout.",
        "5-layer attention network.",
        "5-layer deep neural network.",
        "5-layer classification model.",
        "5-layer regression model.",
        "5-layer vision backbone for 3D pose detection.",
        "A 5-layer BERT model for sentiment analysis.",
        "Constructed a 5-layer GNN graph neural network.",
        "A 5-layer diffusion model denoising pipeline.",
        "5-layer U-Net segmentation network."
    ])
    def test_neural_network_layers_not_false_positived(self, nn_model_text):
        """Ensures neural network model layer counts are not wrongly flagged as mesh hallucinations."""
        findings = audit_content(nn_model_text)
        assert len(findings) == 0, f"False positive on neural net layer description: {findings}"
        assert is_compliant(nn_model_text)

    def test_input_type_robustness(self):
        """Verifies safe handling of None and unexpected input types."""
        assert audit_content(None) == []
        assert is_compliant(None) is True
        assert is_compliant("") is True
        assert is_compliant([]) is True
        
        fixed, mod = auto_fix_content(None)
        assert fixed == ""
        assert mod is False

        with pytest.raises(ValueError):
            is_compliant(12345)


class TestNomadTruthAuditorProgrammaticInjection:
    """Tests programmatic file injection, detection, blocking, and auto-repair."""

    def test_dummy_file_injection_blocked(self, tmp_path):
        dummy_file = tmp_path / "dummy_proposal.md"
        dummy_file.write_text(
            "# Proposed System Architecture\n"
            "This model will shard tensor weights over a 5-layer mesh with 62.8 GB pooled VRAM.\n",
            encoding="utf-8"
        )

        findings, was_modified = audit_file(dummy_file, auto_fix=False)
        assert len(findings) >= 2, f"Expected at least 2 findings, got: {findings}"
        assert not is_compliant(findings)
        assert not was_modified

        # Verify CLI --check-file exits with code 1 in strict mode
        script_path = REPO_ROOT / "06_scripts_and_tooling/automation/nomad_truth_consistency_auditor.py"
        res = subprocess.run(
            [sys.executable, str(script_path), "--check-file", str(dummy_file), "--strict"],
            capture_output=True,
            text=True
        )
        assert res.returncode == 1, f"Expected exit code 1 for non-compliant file, got: {res.returncode}"
        output = json.loads(res.stdout)
        assert output["compliant"] is False
        assert output["findings_count"] >= 2

    def test_dummy_file_auto_fix_repair(self, tmp_path):
        dummy_file = tmp_path / "legacy_notes.md"
        dummy_file.write_text(
            "# Legacy Topology Note\n"
            "- Running on 5-Layer Mesh with 62.8 GB VRAM.\n"
            "- DFS Root: /Volumes/aaronmaher/Lauburu-Monorepo\n"
            "- Orchestrator: Host M4 Max\n"
            "- Description: computes 5-layer hardware mesh sharding\n"
            "- Variant: 5-node cluster with 54.65 GiB and 55.58GB\n",
            encoding="utf-8"
        )

        # Run auto-fix
        findings_after, was_modified = audit_file(dummy_file, auto_fix=True)
        assert was_modified is True

        repaired_content = dummy_file.read_text(encoding="utf-8")
        assert "5-Layer Mesh" not in repaired_content
        assert "7-Layer Mesh" in repaired_content
        assert "/Volumes/aaronmaher" not in repaired_content
        assert "/Users/aaron/DFS_UNIFIED" in repaired_content
        assert "Host M4 Max" not in repaired_content
        assert "Apple M4 Pro Mac Mini (Host)" in repaired_content
        assert "5-layer hardware mesh sharding" not in repaired_content
        assert "7-layer hardware mesh sharding" in repaired_content
        assert "5-node cluster" not in repaired_content
        assert "7-node cluster" in repaired_content

        # Re-audit should be 100% compliant
        assert is_compliant(repaired_content)

    def test_multi_hallucination_compound_document(self):
        compound_doc = """
        # Full System Overview
        The system utilizes a 5-layer mesh connecting 5 devices with 62.8 GB total VRAM.
        Host is Host M4 Max running on /Volumes/Lauburu-Monorepo.
        Local VRAM ceiling is 54.65 GB with 55.58 GB peak.
        TODO: replace with real data
        """
        findings = audit_content(compound_doc)
        categories = {f["category"] for f in findings}
        assert "HALLUCINATED_HARDWARE_METRIC" in categories
        assert "SUSPICIOUS_MOCK_DATA" in categories
        assert len(findings) >= 5


class TestCanonicalTopologyInvariants:
    """Tests mathematical enforcement of 7-layer 108.0 GB RAM cluster topology."""

    def test_ground_truth_constants(self):
        assert GROUND_TRUTH_HARDWARE["total_mesh_ram_gb"] == 108.0
        assert GROUND_TRUTH_HARDWARE["usable_ai_vram_cap_gb"] == 82.8
        assert GROUND_TRUTH_HARDWARE["total_layers"] == 7
        assert len(GROUND_TRUTH_HARDWARE["nodes"]) == 7

        # Sum of nodes must equal 108.0 GB
        sum_ram = sum(n["ram_gb"] for n in GROUND_TRUTH_HARDWARE["nodes"].values())
        assert sum_ram == 108.0, f"Sum of node RAM ({sum_ram}) does not equal 108.0 GB"

    @pytest.mark.parametrize("layers,ram_gb,expected_valid", [
        (7, 108.0, True),
        ("7", "108.0", True),
        (7, 108.2, True),
        (7, 104.8, False),
        (7, 100.0, False),
        (7, 500.0, False),
        (7, 10000.0, False),
        (5, 62.8, False),
        (5, 108.0, False),
        (6, 108.0, False),
        (8, 108.0, False),
        (7, 54.65, False),
        (7, 62.8, False),
        ("invalid", "invalid", False),
    ])
    def test_verify_mesh_topology_boundaries(self, layers, ram_gb, expected_valid):
        valid, reason = verify_mesh_topology(layers, ram_gb)
        assert valid == expected_valid, f"Failed topology boundary for layers={layers}, ram={ram_gb}: {reason}"


class TestNomadTruthAuditorEngineExecution:
    """Tests the core auditor engine end-to-end execution and dashboard sync."""

    def test_auditor_engine_run_once(self):
        auditor = NomadTruthAuditorEngine()
        report = auditor.run_full_audit(auto_fix=False)
        assert "timestamp_utc" in report
        assert "files_scanned" in report
        assert "ground_truth" in report
        assert report["ground_truth"]["cluster_hardware"]["total_mesh_ram_gb"] == 108.0
        assert report["ground_truth"]["cluster_hardware"]["usable_ai_vram_cap_gb"] == 82.8
        assert report["files_scanned"] > 0
