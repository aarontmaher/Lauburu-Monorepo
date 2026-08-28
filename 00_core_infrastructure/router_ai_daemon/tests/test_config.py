"""Unit tests for smolagi RouterConfig."""

import os
import pytest
from src.config import RouterConfig, get_config


def test_default_config_invariants():
    """Verify default config satisfies strict 300MB router constraint."""
    cfg = RouterConfig()
    assert cfg.ram_budget_mb == 300.0
    assert cfg.ram_warning_threshold_mb == 240.0
    assert cfg.ram_critical_threshold_mb == 270.0
    assert cfg.llama_server_port == 8081
    assert cfg.daemon_port == 8080
    assert cfg.context_size == 1024
    assert cfg.batch_size == 128
    assert cfg.parallel_slots == 1
    assert cfg.threads == 3
    assert cfg.cache_type_k == "q4_0"
    assert cfg.cache_type_v == "q4_0"
    assert cfg.no_mmap is True
    cfg.validate()


def test_config_validation_exceeds_budget():
    """Verify ValueError when RAM budget exceeds 300MB."""
    cfg = RouterConfig(ram_budget_mb=350.0)
    with pytest.raises(ValueError, match="exceeds hard ceiling"):
        cfg.validate()


def test_config_validation_invalid_thresholds():
    """Verify ValueError when warning threshold >= critical threshold."""
    cfg = RouterConfig(ram_warning_threshold_mb=280.0, ram_critical_threshold_mb=270.0)
    with pytest.raises(ValueError, match="strictly less than"):
        cfg.validate()

    cfg2 = RouterConfig(ram_critical_threshold_mb=310.0, ram_budget_mb=300.0)
    with pytest.raises(ValueError, match="cannot exceed total RAM budget"):
        cfg2.validate()


def test_get_config_singleton():
    """Verify get_config returns global config instance."""
    cfg = get_config()
    assert isinstance(cfg, RouterConfig)
    assert cfg.ram_budget_mb <= 300.0
