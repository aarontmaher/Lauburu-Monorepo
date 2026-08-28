"""
Tests for Local GGUF Q4_K_M Weight Export Engine.
Validates GGUF export orchestration, binary header formatting, and Q4_K_M metadata integrity.
"""

import os
import pytest
from pyspark_analytics.gguf_exporter import GGUFQ4KMExporter


def test_gguf_q4_k_m_export(tmp_path):
    export_dir = os.path.join(tmp_path, "gguf_exports")
    exporter = GGUFQ4KMExporter(export_dir=export_dir)

    result = exporter.export_to_gguf_q4_k_m(
        model_name="DeepSeek-R1-Distill-Llama-70B",
        custom_metadata={"architecture.layers": "80", "context.length": "131072"},
    )

    assert result["status"] == "GGUF_EXPORT_SUCCESS"
    assert result["quantization"] == "Q4_K_M"
    assert os.path.exists(result["output_path"])

    validation = result["validation"]
    assert validation["status"] == "VALID_GGUF_Q4_K_M"
    assert validation["magic"] == "GGUF"
    assert validation["version"] == 3
    assert validation["quantization"] == "Q4_K_M"


def test_validate_invalid_gguf_magic(tmp_path):
    invalid_file = os.path.join(tmp_path, "invalid.gguf")
    with open(invalid_file, "wb") as f:
        f.write(b"BADHEADER00000000000000000000000")

    with pytest.raises(ValueError, match="Invalid GGUF magic header"):
        GGUFQ4KMExporter.validate_gguf_q4_k_m_file(invalid_file)


def test_validate_nonexistent_file():
    with pytest.raises(FileNotFoundError):
        GGUFQ4KMExporter.validate_gguf_q4_k_m_file("nonexistent_path.gguf")
