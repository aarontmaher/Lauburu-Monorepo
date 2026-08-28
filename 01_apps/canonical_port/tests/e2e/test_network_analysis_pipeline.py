"""
Canonical Port — E2E Test Suite: Network Analysis Pipeline Engine
Verifies asynchronous multi-node telemetry aggregation (>=3 distinct node payloads),
time-series ring buffer retention, anomaly detection, Obsidian Vault sync formatting,
and zero event loop lag / UI isolation. Strictly enforces Rule #0 (Zero-Mock Data).
"""

import pytest
import asyncio
import time
import os
import tempfile
import statistics
import collections
from typing import Dict, Any, List, Optional, Tuple


# ============================================================================
# PIPELINE DATA STRUCTURES & ENGINE IMPLEMENTATION (PROJECT.md CONTRACT)
# Imported from canonical backend.pipeline package
# ============================================================================

from backend.pipeline import (
    TimeSeriesRingBuffer,
    AnomalyDetector,
    ObsidianVaultSyncFormatter,
    NetworkAnalysisPipeline,
)



# ============================================================================
# TIER 1: MULTI-NODE INGESTION (AT LEAST 3 DISTINCT NODES)
# ============================================================================

class TestMultiNodeTelemetryIngestion:
    """Verifies async ingestion across at least 3 distinct node payloads and full 7 layers."""

    @pytest.mark.asyncio
    async def test_ingest_minimum_three_distinct_node_payloads(self, sample_mesh_node_payloads):
        pipeline = NetworkAnalysisPipeline()
        
        # Ingest 3 distinct nodes: Mac_Node, Linux_Head_Node, MacBook_Pro
        nodes_to_test = ["Mac_Node", "Linux_Head_Node", "MacBook_Pro"]
        for node_id in nodes_to_test:
            payload = sample_mesh_node_payloads[node_id]
            anomalies = await pipeline.ingest_payload(node_id, payload)
            assert isinstance(anomalies, list)
            assert pipeline.latest_payloads[node_id]["layer"] == payload["layer"]

        metrics = pipeline.get_aggregated_metrics()
        assert metrics["total_nodes"] == 3
        assert metrics["online_nodes"] == 3
        assert metrics["total_vram_cap_gb"] == round(21.6 + 12.8 + 14.4, 2)
        assert metrics["total_ingested_packets"] == 3

    @pytest.mark.asyncio
    async def test_ingest_all_eight_mesh_nodes(self, sample_mesh_node_payloads):
        pipeline = NetworkAnalysisPipeline()
        
        for node_id, payload in sample_mesh_node_payloads.items():
            await pipeline.ingest_payload(node_id, payload)

        metrics = pipeline.get_aggregated_metrics()
        assert metrics["total_nodes"] == 8
        assert metrics["online_nodes"] == 8
        assert "Mac_Node" in metrics["nodes"]
        assert "Samsung_S20" in metrics["nodes"]
        assert "GL_iNet_Router" in metrics["nodes"]

    @pytest.mark.asyncio
    async def test_concurrent_multi_node_streaming(self, sample_mesh_node_payloads):
        pipeline = NetworkAnalysisPipeline()

        async def stream_node(node_id: str, count: int):
            base_payload = sample_mesh_node_payloads[node_id]
            for i in range(count):
                p = dict(base_payload)
                p["timestamp"] = time.time()
                p["cpu_percent"] = (p["cpu_percent"] + i) % 100.0
                await pipeline.ingest_payload(node_id, p)
                await asyncio.sleep(0.001)

        # Stream 5 nodes concurrently, 20 packets each = 100 packets total
        tasks = [
            asyncio.create_task(stream_node("Mac_Node", 20)),
            asyncio.create_task(stream_node("Linux_Head_Node", 20)),
            asyncio.create_task(stream_node("MacBook_Pro", 20)),
            asyncio.create_task(stream_node("Pixel_10_Pro_XL", 20)),
            asyncio.create_task(stream_node("MacBook_Air", 20)),
        ]
        await asyncio.gather(*tasks)

        metrics = pipeline.get_aggregated_metrics()
        assert metrics["total_nodes"] == 5
        assert metrics["total_ingested_packets"] == 100


# ============================================================================
# TIER 2: TIME-SERIES RING BUFFER RETENTION
# ============================================================================

class TestTimeSeriesRingBufferRetention:
    """Verifies time-series ring buffer bounds, FIFO retention, and window pruning."""

    def test_ring_buffer_capacity_bounded(self):
        buf = TimeSeriesRingBuffer(maxlen=50)
        now = time.time()
        for i in range(120):
            buf.append(now + i, float(i))

        assert buf.size() == 50
        # The oldest items (0..69) must have been evicted, retaining 70..119
        recent = buf.get_recent(5)
        assert len(recent) == 5
        assert recent[-1][1] == 119.0
        assert recent[0][1] == 115.0

    def test_ring_buffer_window_slicing_by_time(self):
        buf = TimeSeriesRingBuffer(maxlen=100)
        base = 1000.0
        for i in range(50):
            buf.append(base + i, float(i * 2))

        window = buf.get_window(1010.0, 1020.0)
        assert len(window) == 11
        assert window[0][0] == 1010.0
        assert window[-1][0] == 1020.0

    def test_ring_buffer_statistical_aggregations(self):
        buf = TimeSeriesRingBuffer(maxlen=100)
        for val in [10.0, 20.0, 30.0, 40.0, 50.0]:
            buf.append(time.time(), val)

        stats = buf.get_stats()
        assert stats["count"] == 5.0
        assert stats["mean"] == 30.0
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0
        assert stats["stddev"] > 0.0


# ============================================================================
# TIER 3: ANOMALY DETECTION ENGINE
# ============================================================================

class TestAnomalyDetectionEngine:
    """Verifies anomaly detection logic for latency spikes, packet loss, VRAM, and dropouts."""

    def test_normal_payload_produces_no_anomalies(self, sample_mesh_node_payloads):
        detector = AnomalyDetector()
        anomalies = detector.evaluate_payload(sample_mesh_node_payloads["Mac_Node"])
        assert len(anomalies) == 0

    def test_latency_spike_anomaly_detected(self, sample_mesh_node_payloads):
        detector = AnomalyDetector(rtt_spike_threshold_ms=10.0)
        spiked_payload = dict(sample_mesh_node_payloads["MacBook_Pro"])
        spiked_payload["rtt_ms"] = 45.2  # Spike > 10.0ms threshold

        anomalies = detector.evaluate_payload(spiked_payload)
        assert len(anomalies) == 1
        assert anomalies[0]["type"] == "LATENCY_SPIKE"
        assert anomalies[0]["node_id"] == "MacBook_Pro"
        assert anomalies[0]["value"] == 45.2

    def test_packet_drop_burst_anomaly_detected(self, sample_mesh_node_payloads):
        detector = AnomalyDetector(drop_threshold_percent=2.0)
        dropped_payload = dict(sample_mesh_node_payloads["Linux_Head_Node"])
        dropped_payload["drop_rate"] = 7.5  # 7.5% drop rate

        anomalies = detector.evaluate_payload(dropped_payload)
        assert len(anomalies) == 1
        assert anomalies[0]["type"] == "PACKET_LOSS_BURST"
        assert anomalies[0]["value"] == 7.5

    def test_vram_saturation_anomaly_detected(self, sample_mesh_node_payloads):
        detector = AnomalyDetector()
        saturated_payload = dict(sample_mesh_node_payloads["Mac_Node"])
        # Mac_Node AI cap is 21.6 GB; set used to 21.0 GB (> 90%)
        saturated_payload["vram_used_gb"] = 21.0
        saturated_payload["ai_vram_cap_gb"] = 21.6

        anomalies = detector.evaluate_payload(saturated_payload)
        assert len(anomalies) == 1
        assert anomalies[0]["type"] == "VRAM_SATURATION"

    def test_offline_node_critical_anomaly_detected(self, sample_mesh_node_payloads):
        detector = AnomalyDetector()
        offline_payload = dict(sample_mesh_node_payloads["Samsung_S20"])
        offline_payload["status"] = "OFFLINE"

        anomalies = detector.evaluate_payload(offline_payload)
        assert len(anomalies) == 1
        assert anomalies[0]["type"] == "NODE_OFFLINE"
        assert anomalies[0]["severity"] == "CRITICAL"


# ============================================================================
# TIER 4: OBSIDIAN VAULT SYNC & ATOMIC WRITING
# ============================================================================

class TestObsidianVaultSyncFormatting:
    """Verifies Markdown note formatting, YAML frontmatter, and atomic note persistence."""

    def test_obsidian_telemetry_note_formatting(self, sample_mesh_node_payloads):
        payload = sample_mesh_node_payloads["Mac_Node"]
        note = ObsidianVaultSyncFormatter.format_node_telemetry_note("Mac_Node", payload)

        assert "---" in note
        assert "node_id: \"Mac_Node\"" in note
        assert "layer: \"L1\"" in note
        assert "[[Mac_Node]]" in note
        assert "[[Index]]" in note
        assert "[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]" in note
        assert "192.168.8.230" in note
        assert "100.119.199.76" in note

    def test_atomic_vault_note_write(self, mock_obsidian_vault_dir, sample_mesh_node_payloads):
        payload = sample_mesh_node_payloads["Linux_Head_Node"]
        note = ObsidianVaultSyncFormatter.format_node_telemetry_note("Linux_Head_Node", payload)
        
        file_path = ObsidianVaultSyncFormatter.write_atomic_vault_note(
            mock_obsidian_vault_dir, "Linux_Head_Node.md", note
        )
        assert os.path.exists(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "[[Linux_Head_Node]]" in content
        assert "100.101.39.98" in content

    @pytest.mark.asyncio
    async def test_pipeline_vault_sync_integration(self, mock_obsidian_vault_dir, sample_mesh_node_payloads):
        pipeline = NetworkAnalysisPipeline(vault_dir=mock_obsidian_vault_dir)
        
        await pipeline.ingest_payload("MacBook_Pro", sample_mesh_node_payloads["MacBook_Pro"])
        
        expected_note = os.path.join(mock_obsidian_vault_dir, "MacBook_Pro.md")
        assert os.path.exists(expected_note)
        with open(expected_note, "r", encoding="utf-8") as f:
            content = f.read()
        assert "TB4 DMA Vault" in content or "MacBook_Pro" in content


# ============================================================================
# TIER 5: EVENT LOOP LATENCY & UI ISOLATION
# ============================================================================

class TestEventLoopLatencyAndUIIsolation:
    """Verifies that high-frequency packet ingestion does not starve asyncio event loop."""

    @pytest.mark.asyncio
    async def test_event_loop_latency_under_500_packet_burst(self, sample_mesh_node_payloads):
        pipeline = NetworkAnalysisPipeline()
        loop = asyncio.get_running_loop()
        
        # Track event loop tick jitter during heavy ingestion
        max_loop_lag_ms = 0.0

        async def monitor_loop_lag():
            nonlocal max_loop_lag_ms
            for _ in range(50):
                t0 = loop.time()
                await asyncio.sleep(0.002)
                elapsed_ms = (loop.time() - t0 - 0.002) * 1000.0
                if elapsed_ms > max_loop_lag_ms:
                    max_loop_lag_ms = elapsed_ms

        async def flood_packets():
            for i in range(500):
                node_id = "Mac_Node" if i % 2 == 0 else "Linux_Head_Node"
                p = dict(sample_mesh_node_payloads[node_id])
                p["timestamp"] = time.time()
                await pipeline.ingest_payload(node_id, p)

        # Run packet flood and loop monitor concurrently
        await asyncio.gather(flood_packets(), monitor_loop_lag())

        assert pipeline.total_ingested == 500
        # Event loop lag must remain below 15ms (ensures 60+ FPS UI responsiveness)
        assert max_loop_lag_ms < 15.0

    def test_non_blocking_metrics_getter_latency(self, sample_mesh_node_payloads):
        pipeline = NetworkAnalysisPipeline()
        pipeline.latest_payloads = dict(sample_mesh_node_payloads)
        
        t0 = time.perf_counter()
        metrics = pipeline.get_aggregated_metrics()
        duration_ms = (time.perf_counter() - t0) * 1000.0
        
        assert metrics["total_nodes"] == len(sample_mesh_node_payloads)
        # Reading aggregated metrics must take < 1.0ms
        assert duration_ms < 1.0
