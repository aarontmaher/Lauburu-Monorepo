"""
Unit & Integration Tests for Network-Wide Data Analysis Pipeline
Tests REST endpoints, WebSocket streams, Mesh Collector, Obsidian Engine,
Z-Score Anomaly Detection, Ring Buffer Pruning, and Pipeline Event Callbacks.
"""

import asyncio
import os
import time
import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.pipeline import (
    AnomalyDetector,
    CANONICAL_MESH_NODES,
    MeshTelemetryCollector,
    NetworkAnalysisPipeline,
    ObsidianVaultSyncEngine,
    ObsidianVaultSyncFormatter,
    TimeSeriesRingBuffer,
    get_network_pipeline,
    reset_network_pipeline,
)


@pytest.fixture
def test_client():
    return TestClient(app)


# ============================================================================
# 1. TIME-SERIES RING BUFFER EXTENDED TESTS
# ============================================================================

class TestTimeSeriesRingBufferExtended:
    def test_invalid_capacity_raises_value_error(self):
        with pytest.raises(ValueError):
            TimeSeriesRingBuffer(maxlen=0)

    def test_empty_buffer_stats(self):
        buf = TimeSeriesRingBuffer(maxlen=10)
        assert buf.size() == 0
        assert len(buf) == 0
        assert buf.get_latest() is None
        assert buf.get_oldest() is None
        stats = buf.get_stats()
        assert stats["count"] == 0.0
        assert stats["mean"] == 0.0

    def test_latest_and_oldest_retrieval(self):
        buf = TimeSeriesRingBuffer(maxlen=10)
        t0 = time.time()
        buf.append(t0, 10.5, {"tag": "first"})
        buf.append(t0 + 1, 20.5, {"tag": "second"})
        buf.append(t0 + 2, 30.5, {"tag": "third"})

        assert buf.get_oldest()[1] == 10.5
        assert buf.get_oldest()[2]["tag"] == "first"
        assert buf.get_latest()[1] == 30.5
        assert buf.get_latest()[2]["tag"] == "third"
        assert len(buf.to_list()) == 3

    def test_prune_older_than(self):
        buf = TimeSeriesRingBuffer(maxlen=20)
        t0 = 1000.0
        for i in range(10):
            buf.append(t0 + i, float(i))

        # Prune everything before 1005.0
        pruned_count = buf.prune_older_than(1005.0)
        assert pruned_count == 5
        assert buf.size() == 5
        assert buf.get_oldest()[0] == 1005.0

    def test_clear_buffer(self):
        buf = TimeSeriesRingBuffer(maxlen=10)
        buf.append(time.time(), 42.0)
        assert buf.size() == 1
        buf.clear()
        assert buf.size() == 0


# ============================================================================
# 2. ANOMALY DETECTOR EXTENDED TESTS
# ============================================================================

class TestAnomalyDetectorExtended:
    def test_cpu_saturation_anomaly(self):
        detector = AnomalyDetector(cpu_saturation_pct=90.0)
        payload = {
            "node_id": "Mac_Node",
            "cpu_percent": 95.5,
            "status": "ONLINE",
            "rtt_ms": 0.05,
            "drop_rate": 0.0,
        }
        anomalies = detector.evaluate_payload(payload)
        assert len(anomalies) == 1
        assert anomalies[0]["type"] == "CPU_SATURATION"
        assert anomalies[0]["severity"] == "WARNING"

    def test_high_severity_latency_spike(self):
        detector = AnomalyDetector(rtt_spike_threshold_ms=15.0)
        payload = {
            "node_id": "MacBook_Air",
            "status": "ONLINE",
            "rtt_ms": 150.0,  # >= 100ms triggers HIGH severity
        }
        anomalies = detector.evaluate_payload(payload)
        assert len(anomalies) == 1
        assert anomalies[0]["type"] == "LATENCY_SPIKE"
        assert anomalies[0]["severity"] == "HIGH"

    def test_z_score_anomaly_evaluation(self):
        detector = AnomalyDetector(z_score_threshold=2.5)
        buf = TimeSeriesRingBuffer(maxlen=50)
        t0 = time.time()
        # Seed historical normal samples: mean ~10.0, small variance
        for i in range(20):
            buf.append(t0 + i, 10.0 + (i % 3) * 0.5)

        # Normal sample should not trigger z-score anomaly
        assert detector.evaluate_z_score("Mac_Node", 10.5, buf) is None

        # Extreme outlier (50.0) should trigger z-score anomaly
        anomaly = detector.evaluate_z_score("Mac_Node", 50.0, buf)
        assert anomaly is not None
        assert anomaly["type"] == "Z_SCORE_ANOMALY"
        assert anomaly["z_score"] > 2.5


# ============================================================================
# 3. MESH COLLECTOR TESTS
# ============================================================================

class TestMeshTelemetryCollector:
    @pytest.mark.asyncio
    async def test_canonical_mesh_node_definitions_catalog(self):
        collector = MeshTelemetryCollector()
        assert len(collector.nodes) == 8
        assert "Mac_Node" in collector.nodes
        assert "MacBook_Pro" in collector.nodes
        assert "GL_iNet_Router" in collector.nodes
        assert collector.nodes["Mac_Node"]["layer"] == "L1"
        assert collector.nodes["MacBook_Pro"]["layer"] == "L2"

    @pytest.mark.asyncio
    async def test_poll_single_node_returns_telemetry(self):
        collector = MeshTelemetryCollector()
        payload = await collector.poll_node("Mac_Node", timeout_seconds=0.1)
        assert payload["node_id"] == "Mac_Node"
        assert payload["layer"] == "L1"
        assert payload["status"] == "ONLINE"
        assert payload["ram_total_gb"] == 24.0

    @pytest.mark.asyncio
    async def test_poll_all_nodes_returns_all_eight(self):
        collector = MeshTelemetryCollector()
        results = await collector.poll_all_nodes(timeout_seconds=0.1)
        assert len(results) == 8
        assert "Pixel_10_Pro_XL" in results
        assert "Samsung_S20" in results

    @pytest.mark.asyncio
    async def test_background_polling_lifecycle(self):
        collector = MeshTelemetryCollector()
        received = []

        def on_telemetry(node_id, payload):
            received.append((node_id, payload))

        await collector.start_background_polling(
            interval_seconds=0.02, timeout_seconds=0.01, callback=on_telemetry
        )
        await asyncio.sleep(0.2)
        await collector.stop_background_polling()

        assert len(received) >= 8


# ============================================================================
# 4. OBSIDIAN VAULT SYNC ENGINE TESTS
# ============================================================================

class TestObsidianVaultSyncEngineExtended:
    def test_daily_summary_formatting(self, sample_mesh_node_payloads):
        pipeline = NetworkAnalysisPipeline()
        for nid, p in sample_mesh_node_payloads.items():
            pipeline.latest_payloads[nid] = p

        metrics = pipeline.get_aggregated_metrics()
        anomalies = [{"type": "LATENCY_SPIKE", "node_id": "MacBook_Pro", "severity": "WARNING", "message": "RTT spike"}]
        summary = ObsidianVaultSyncFormatter.format_daily_telemetry_summary("2026-08-28", metrics, anomalies)

        assert "# 🌐 [[Telemetry-2026-08-28]] Daily Summary" in summary
        assert "[[Mac_Node]]" in summary
        assert "[[Index]]" in summary
        assert "LATENCY_SPIKE" in summary

    def test_engine_index_creation(self, mock_obsidian_vault_dir):
        # Remove Index.md to test generation
        index_file = os.path.join(mock_obsidian_vault_dir, "Index.md")
        if os.path.exists(index_file):
            os.remove(index_file)

        engine = ObsidianVaultSyncEngine(vault_dir=mock_obsidian_vault_dir)
        assert engine.update_index_links() is True
        assert os.path.exists(index_file)
        with open(index_file, "r") as f:
            content = f.read()
        assert "[[Mac_Node]]" in content
        assert "[[Index]]" in content


# ============================================================================
# 5. PIPELINE SUBSCRIBERS & BATCH INGESTION
# ============================================================================

class TestPipelineSubscribersAndBatch:
    @pytest.mark.asyncio
    async def test_subscriber_callback_invoked(self, sample_mesh_node_payloads):
        pipeline = NetworkAnalysisPipeline()
        events = []

        def subscriber(event):
            events.append(event)

        pipeline.subscribe(subscriber)
        await pipeline.ingest_payload("Mac_Node", sample_mesh_node_payloads["Mac_Node"])

        assert len(events) == 1
        assert events[0]["node_id"] == "Mac_Node"
        assert events[0]["type"] == "telemetry_ingested"

        pipeline.unsubscribe(subscriber)
        await pipeline.ingest_payload("Linux_Head_Node", sample_mesh_node_payloads["Linux_Head_Node"])
        assert len(events) == 1  # Unsubscribed, no new events

    @pytest.mark.asyncio
    async def test_batch_ingest_payloads(self, sample_mesh_node_payloads):
        pipeline = NetworkAnalysisPipeline()
        payloads = [
            sample_mesh_node_payloads["Mac_Node"],
            sample_mesh_node_payloads["MacBook_Pro"],
            sample_mesh_node_payloads["Linux_Head_Node"],
        ]
        detected = await pipeline.batch_ingest(payloads)
        assert isinstance(detected, list)
        assert pipeline.total_ingested == 3
        metrics = pipeline.get_aggregated_metrics()
        assert metrics["total_nodes"] == 3


# ============================================================================
# 6. REST API ROUTER & WEBSOCKET ENDPOINTS
# ============================================================================

class TestNetworkPipelineRestAndWebSocketApi:
    def test_rest_get_network_metrics(self, test_client, sample_mesh_node_payloads):
        pipeline = get_network_pipeline()
        for nid in ["Mac_Node", "MacBook_Pro", "Linux_Head_Node"]:
            pipeline.latest_payloads[nid] = sample_mesh_node_payloads[nid]

        res = test_client.get("/api/v1/network/metrics")
        assert res.status_code == 200
        data = res.json()
        assert data["total_nodes"] >= 3
        assert "nodes" in data

    def test_rest_get_network_anomalies(self, test_client):
        res = test_client.get("/api/v1/network/anomalies?limit=10")
        assert res.status_code == 200
        data = res.json()
        assert "anomalies" in data
        assert "total_anomalies" in data

    def test_rest_post_network_ingest(self, test_client, sample_mesh_node_payloads):
        payload = dict(sample_mesh_node_payloads["MacBook_Air"])
        res = test_client.post("/api/v1/network/ingest", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["node_id"] == "MacBook_Air"

    def test_rest_get_network_node_buffer(self, test_client, sample_mesh_node_payloads):
        pipeline = get_network_pipeline()
        pipeline.latest_payloads["Pixel_10_Pro_XL"] = sample_mesh_node_payloads["Pixel_10_Pro_XL"]
        buf = TimeSeriesRingBuffer(maxlen=50)
        buf.append(time.time(), 6.8, {"cpu": 22.0})
        pipeline.node_buffers["Pixel_10_Pro_XL"] = buf

        res = test_client.get("/api/v1/network/buffer/Pixel_10_Pro_XL")
        assert res.status_code == 200
        data = res.json()
        assert data["node_id"] == "Pixel_10_Pro_XL"
        assert data["buffer_size"] == 1
        assert "stats" in data

    def test_rest_post_obsidian_sync(self, test_client):
        res = test_client.post("/api/v1/network/obsidian/sync")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True

    def test_websocket_network_telemetry_stream(self, test_client):
        with test_client.websocket_connect("/ws/network/telemetry") as ws:
            # Receive initial metrics
            initial_data = ws.receive_json()
            assert "total_nodes" in initial_data

            # Send ping
            ws.send_text("ping")
            resp = ws.receive_text()
            assert resp == "pong"

            # Send poll
            ws.send_text("poll")
            polled = ws.receive_json()
            assert "total_nodes" in polled

            # Send anomalies request
            ws.send_text("anomalies")
            anomalies_resp = ws.receive_json()
            assert "anomalies" in anomalies_resp
