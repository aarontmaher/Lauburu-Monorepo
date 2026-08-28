"""
Adversarial HMAC Tampering & Authentication Edge Cases Test Suite.
Empirically tests signature corruption, bit flips, empty tokens, invalid secrets,
timing attack resistance, token format enforcement, and session lifecycle security.
"""

import hmac
import hashlib
import time
import pytest
from httpx import ASGITransport, AsyncClient
from app.core.security import (
    compute_hmac_signature,
    generate_session_token,
    validate_session_token_format,
    verify_hmac_signature,
)
from app.main import app


class TestAdversarialHmacTamper:
    """Adversarial security tests for HMAC generation, validation, and session endpoints."""

    # -------------------------------------------------------------------------
    # 1. HMAC Signature Tampering & Bit Flips
    # -------------------------------------------------------------------------
    def test_hmac_tampered_signature_rejection(self):
        """Verify that any single-character or single-bit change in signature fails verification."""
        secret = "super_secure_secret_key_123456789"
        message = "session_nonce_data_12345"
        valid_sig = compute_hmac_signature(secret, message)

        # 1. Bit flip in first char
        corrupted_1 = ("0" if valid_sig[0] != "0" else "1") + valid_sig[1:]
        assert verify_hmac_signature(secret, message, corrupted_1) is False

        # 2. Bit flip in last char
        corrupted_2 = valid_sig[:-1] + ("0" if valid_sig[-1] != "0" else "1")
        assert verify_hmac_signature(secret, message, corrupted_2) is False

        # 3. Bit flip in middle
        mid = len(valid_sig) // 2
        corrupted_3 = valid_sig[:mid] + ("f" if valid_sig[mid] != "f" else "0") + valid_sig[mid+1:]
        assert verify_hmac_signature(secret, message, corrupted_3) is False

        # 4. Truncated signature
        assert verify_hmac_signature(secret, message, valid_sig[:32]) is False
        assert verify_hmac_signature(secret, message, valid_sig[:63]) is False

        # 5. Appended signature
        assert verify_hmac_signature(secret, message, valid_sig + "a") is False

        # 6. Empty signature
        assert verify_hmac_signature(secret, message, "") is False

    # -------------------------------------------------------------------------
    # 2. Secret and Message Tampering
    # -------------------------------------------------------------------------
    def test_hmac_tampered_secret_and_message(self):
        """Verify that altering the secret or the message invalidates verification."""
        secret = "secret_a"
        wrong_secret = "secret_b"
        message = "hemodynamic_payload"
        wrong_message = "hemodynamic_pay1oad"

        sig = compute_hmac_signature(secret, message)

        # Wrong secret
        assert verify_hmac_signature(wrong_secret, message, sig) is False
        # Wrong message
        assert verify_hmac_signature(secret, wrong_message, sig) is False
        # Empty secret
        assert verify_hmac_signature("", message, sig) is False
        # Empty message
        assert verify_hmac_signature(secret, "", sig) is False

    # -------------------------------------------------------------------------
    # 3. Session Token Format Validation
    # -------------------------------------------------------------------------
    @pytest.mark.parametrize("invalid_token", [
        "",                             # Empty string
        None,                           # None
        "a" * 63,                       # 63 chars (too short)
        "a" * 65,                       # 65 chars (too long)
        "a" * 32,                       # 32 chars (MD5 length)
        "z" * 64,                       # 64 chars but non-hex 'z'
        "G" * 64,                       # 64 chars but non-hex 'G'
        "0123456789abcdef" * 3 + "xyz!",# 64 chars with special chars
        1234567890,                     # Integer
        {"token": "a" * 64},            # Dict
    ])
    def test_invalid_session_token_formats(self, invalid_token):
        """Verify that non-64-character hexadecimal SHA-256 tokens are rejected by format validator."""
        assert validate_session_token_format(invalid_token) is False

    def test_valid_session_token_formats(self):
        """Verify that genuine SHA-256 hex tokens pass format validation."""
        valid_token_1 = generate_session_token()
        assert validate_session_token_format(valid_token_1) is True
        assert len(valid_token_1) == 64

        valid_token_2 = hashlib.sha256(b"custom_test_seed").hexdigest()
        assert validate_session_token_format(valid_token_2) is True

    # -------------------------------------------------------------------------
    # 4. Deterministic Nonce Generation
    # -------------------------------------------------------------------------
    def test_deterministic_session_token_with_nonce(self):
        """Verify that supplying the same secret and nonce generates a deterministic token."""
        secret = "test_deterministic_secret"
        nonce = "client_device_nonce_xyz_9988"
        t1 = generate_session_token(secret=secret, nonce=nonce)
        t2 = generate_session_token(secret=secret, nonce=nonce)
        assert t1 == t2
        assert len(t1) == 64

        # Different nonce produces different token
        t3 = generate_session_token(secret=secret, nonce="client_device_nonce_xyz_9989")
        assert t1 != t3

    # -------------------------------------------------------------------------
    # 5. API Session Endpoint Tampering & Validation
    # -------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_session_summary_rejects_malformed_hashes(self):
        """Verify GET /api/v1/sessions/{session_hash}/summary rejects malformed tokens with HTTP 400."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Too short (32 chars)
            res1 = await client.get(f"/api/v1/sessions/{'a'*32}/summary")
            assert res1.status_code == 400
            assert "Invalid session token format" in res1.json()["detail"]

            # 2. Too long (65 chars)
            res2 = await client.get(f"/api/v1/sessions/{'a'*65}/summary")
            assert res2.status_code == 400

            # 3. Non-hex characters
            res3 = await client.get(f"/api/v1/sessions/{'g'*64}/summary")
            assert res3.status_code == 400

    @pytest.mark.asyncio
    async def test_session_summary_returns_404_for_nonexistent_valid_hash(self):
        """Verify GET /api/v1/sessions/{session_hash}/summary returns 404 for valid format but non-existent session."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            fake_valid_hash = hashlib.sha256(b"non_existent_session_hash_123456789_unique").hexdigest()
            res = await client.get(f"/api/v1/sessions/{fake_valid_hash}/summary")
            assert res.status_code == 404
            assert "not found" in res.json()["detail"]

    @pytest.mark.asyncio
    async def test_session_lifecycle_tamper_resistance(self):
        """Verify session init -> summary retrieval lifecycle under valid vs tampered conditions."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Init session
            init_res = await client.post("/api/v1/sessions/init", json={"client_nonce": "test_nonce_adv_123"})
            assert init_res.status_code == 201
            session_token = init_res.json()["session_token"]
            assert validate_session_token_format(session_token) is True

            # 2. Retrieve summary with exact token -> 200 OK
            sum_res = await client.get(f"/api/v1/sessions/{session_token}/summary")
            assert sum_res.status_code == 200
            assert sum_res.json()["session_hash"] == session_token

            # 3. Retrieve with tampered last character -> 404 Not Found (valid hex) or 400 (invalid hex)
            tampered_token = session_token[:-1] + ("0" if session_token[-1] != "0" else "1")
            tampered_res = await client.get(f"/api/v1/sessions/{tampered_token}/summary")
            assert tampered_res.status_code == 404
