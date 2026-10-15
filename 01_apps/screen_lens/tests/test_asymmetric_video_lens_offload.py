#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit and Integration Tests for Asymmetric Video Lens Offload (4GB Phone -> 16GB Laptop)
"""

import sys
import pytest
from pathlib import Path

SCREEN_LENS_DIR = Path(__file__).resolve().parents[1]
if str(SCREEN_LENS_DIR) not in sys.path:
    sys.path.insert(0, str(SCREEN_LENS_DIR))

from asymmetric_video_lens_offload_bridge import (
    LowRAMPhoneVideoProducer,
    HighRAMLaptopComputeConsumer,
    AsymmetricVideoLensBridge
)


def test_phone_producer_ram_footprint():
    producer = LowRAMPhoneVideoProducer()
    assert producer.client_ram_usage_mb < 50.0  # Must be < 50MB
    packet = producer.capture_and_compress_frame(hr_telemetry=80.0)
    assert packet.frame_id == 1
    assert packet.device_ram_tier == "4GB_MOBILE"
    assert packet.compressed_bytes_b64 is not None


def test_laptop_consumer_processing():
    consumer = HighRAMLaptopComputeConsumer()
    producer = LowRAMPhoneVideoProducer()
    packet = producer.capture_and_compress_frame(hr_telemetry=145.0)
    response = consumer.process_incoming_frame(packet)
    assert response.frame_id == 1
    assert response.processing_node == "MacBook_Air_M4_16GB"
    assert len(response.detected_objects) > 0
    assert response.lora_harvested is True


def test_asymmetric_bridge_end_to_end():
    bridge = AsymmetricVideoLensBridge()
    res = bridge.run_live_pipeline_step(hr=135.0)
    assert res["status"] == "OFFLOAD_INFERENCE_SUCCESS"
    assert res["client_ram_mb"] < 30.0
    assert res["server_vram_gb"] >= 5.0
    assert res["roundtrip_latency_ms"] < 100.0


if __name__ == "__main__":
    pytest.main(["-v", str(__file__)])
