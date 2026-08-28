"""Unit tests for updated mesh_telemetry_crawler with Delta Lake support."""
import json
import os
import shutil
import tempfile
import pytest

from delta_engine.writer import DeltaDatasetWriter
from delta_engine.schema import MESH_TELEMETRY_ARROW_SCHEMA
import mesh_telemetry_crawler


@pytest.fixture
def telemetry_test_env(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="test_telemetry_")
    trends_json = os.path.join(tmp, "mesh_trends.json")
    delta_uri = os.path.join(tmp, "delta_mesh_stream")

    monkeypatch.setattr(mesh_telemetry_crawler, "TRENDS_FILE", trends_json)
    monkeypatch.setattr(mesh_telemetry_crawler, "DEFAULT_DELTA_URI", delta_uri)

    yield {"tmp": tmp, "trends_json": trends_json, "delta_uri": delta_uri}

    if os.path.exists(tmp):
        shutil.rmtree(tmp)


def test_mesh_telemetry_crawler_crawl_once(telemetry_test_env):
    trends_json = telemetry_test_env["trends_json"]
    delta_uri = telemetry_test_env["delta_uri"]

    writer = DeltaDatasetWriter(table_uri=delta_uri, schema=MESH_TELEMETRY_ARROW_SCHEMA)
    telemetry, delta_records = mesh_telemetry_crawler.crawl_once(delta_writer=writer)

    assert "timestamp" in telemetry
    assert "nodes" in telemetry
    assert len(telemetry["nodes"]) == len(mesh_telemetry_crawler.NODES)

    # Check JSON file written
    assert os.path.exists(trends_json)
    with open(trends_json, "r") as f:
        data = json.load(f)
        assert len(data["nodes"]) == len(mesh_telemetry_crawler.NODES)

    # Check Delta Lake table
    assert writer.count_rows() == len(mesh_telemetry_crawler.NODES)
    dt = writer.get_table()
    assert dt is not None
    table = dt.to_pyarrow_table()
    assert "latency_ms" in table.column_names
    assert "transport" in table.column_names
