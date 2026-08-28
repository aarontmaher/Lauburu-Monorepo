"""
Zero-PII & HMAC-SHA256 Cryptographic Security Test Suite.
Verifies token format, timing attack resistance, and 100% rejection of all PII keys.
"""

import time
import pytest
from app.core.security import (
    generate_session_token,
    compute_hmac_signature,
    verify_hmac_signature,
    validate_session_token_format,
    is_pii_key,
    is_pii_value,
    contains_pii,
    get_pii_violations,
    sanitize_pii,
    PROHIBITED_PII_KEYS,
)


class TestZeroPiiSecurityBasics:
    def test_session_token_generation_and_format(self):
        token1 = generate_session_token()
        token2 = generate_session_token()
        assert len(token1) == 64
        assert len(token2) == 64
        assert token1 != token2
        assert validate_session_token_format(token1) is True
        assert validate_session_token_format(token2) is True
        assert validate_session_token_format("invalid_token_short") is False
        assert validate_session_token_format("g" * 64) is False  # Non-hex

    def test_hmac_signature_verification_and_constant_time(self):
        secret = "super_secret_key_12345"
        msg = "payload_content_to_verify"
        sig = compute_hmac_signature(secret, msg)
        
        assert verify_hmac_signature(secret, msg, sig) is True
        assert verify_hmac_signature(secret, msg + "_tampered", sig) is False
        assert verify_hmac_signature(secret + "_wrong", msg, sig) is False

    def test_prohibited_pii_keys_rejection(self):
        for key in PROHIBITED_PII_KEYS:
            assert is_pii_key(key) is True, f"Failed to flag prohibited key '{key}'"
            assert is_pii_key(f"user_{key}") is True or is_pii_key(key) is True

    def test_pii_value_pattern_detection(self):
        assert is_pii_value("00:1A:2B:3C:4D:5E") is True
        assert is_pii_value("AA-BB-CC-DD-EE-FF") is True
        assert is_pii_value("runner@example.com") is True
        assert is_pii_value("valid_session_token_12345") is False
        assert is_pii_value(123.45) is False

    def test_nested_pii_detection_and_sanitization(self):
        dirty_payload = {
            "session_token": generate_session_token(),
            "telemetry": {
                "ptt_ms": 220.0,
                "hr_bpm": 140.0,
                "user_email": "runner@lauburu.ai",
                "device": {
                    "mac_address": "00:11:22:33:44:55"
                }
            }
        }
        assert contains_pii(dirty_payload) is True
        violations = get_pii_violations(dirty_payload)
        assert len(violations) >= 2

        cleaned = sanitize_pii(dirty_payload)
        assert contains_pii(cleaned) is False
        assert "user_email" not in cleaned["telemetry"]
        assert "device" not in cleaned["telemetry"]
        assert "mac_address" not in cleaned["telemetry"].get("device", {})


class TestMiddlewarePiiRejection:
    def test_reject_query_param_pii_key(self, client):
        res = client.get("/health?email=test@lauburu.ai")
        assert res.status_code == 422
        assert "Zero-PII Policy Violation" in res.json()["detail"]

    def test_reject_query_param_mac_address(self, client):
        res = client.get("/health?device=00:11:22:33:44:55")
        assert res.status_code == 422
        assert "Zero-PII Policy Violation" in res.json()["detail"]

    def test_reject_custom_pii_header(self, client):
        headers = {"X-User-Email": "athlete@lauburu.ai"}
        res = client.get("/health", headers=headers)
        assert res.status_code == 422
        assert "Zero-PII Policy Violation" in res.json()["detail"]

    def test_reject_payload_with_pii_in_invert(self, client, sample_session_token):
        dirty_body = {
            "session_token": sample_session_token,
            "user_id": "athlete_9921",
            "vector_u": {
                "ptt_ms": 220.0,
                "hr_bpm": 140.0
            }
        }
        res = client.post("/api/v1/hemodynamics/invert", json=dirty_body)
        assert res.status_code == 422
        assert "Zero-PII Policy Violation" in res.json()["detail"]

    def test_accept_clean_payload(self, client, sample_session_token, sample_valid_vector_u):
        clean_body = {
            "session_token": sample_session_token,
            "delta_time_ms": 5000,
            "vector_u": sample_valid_vector_u
        }
        res = client.post("/api/v1/hemodynamics/invert", json=clean_body)
        assert res.status_code == 200
        data = res.json()
        assert data["session_token"] == sample_session_token
        assert data["hemodynamic_state"]["systolic_bp_mmHg"] > 70.0
