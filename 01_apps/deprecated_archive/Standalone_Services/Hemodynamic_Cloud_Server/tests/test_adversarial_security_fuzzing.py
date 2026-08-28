"""
Adversarial Security & Zero-PII Fuzzing Test Suite.
Empirically stress-tests Zero-PII sanitization across nested JSON, obscured keys,
case variations, whitespace padding, URL-encoded parameters, headers, and malicious payloads.
"""

import json
import pytest
from pydantic import ValidationError
from httpx import ASGITransport, AsyncClient
from app.core.security import (
    contains_pii,
    get_pii_violations,
    is_pii_key,
    is_pii_value,
    sanitize_pii,
    PROHIBITED_PII_KEYS,
    PROHIBITED_PII_SUBSTRINGS,
)
from app.models.schemas import (
    VectorU,
    TransitHemodynamics,
    CardiacAutonomic,
    InversionRequest,
    ZeroPiiPayload,
)
from app.main import app


@pytest.fixture
def clean_inversion_payload():
    return {
        "protocol_version": "1.0",
        "session_token": "a" * 64,
        "delta_time_ms": 1000,
        "vector_u": {
            "ptt_ms": 220.0,
            "hr_bpm": 72.0,
            "rr_ms": 833.0,
            "delta_t_dia_ms": 280.0,
            "imu_acc_g": 1.02,
            "e0_elasticity": 400.0,
        }
    }


class TestAdversarialSecurityFuzzing:
    """Rigorous empirical fuzzing of Zero-PII gate against adversarial bypass attempts."""

    # -------------------------------------------------------------------------
    # 1. Obscured Key Names & Case Variations
    # -------------------------------------------------------------------------
    @pytest.mark.parametrize("fuzzed_key", [
        "EMAIL", "EmAiL", "user_email", "mail",
        "MAC", "MaC_AdDrEsS", "macaddress", "ble_mac", "bluetooth_address",
        "SERIAL", "SeRiAl_NuMbEr", "device_serial", "serialnumber",
        "DEVICE_ID", "DeviceId", "user_id", "UsEr_Id", "UUID", "guid",
        "IP_ADDRESS", "client_ip", "remote_addr",
        "PHONE", "phone_number", "GPS", "latitude", "longitude",
        "SENSOR_ID", "sensorid", "DEVICE_NAME", "devicename",
        "  email  ", "\tmac_address\t", "\nuser_id\n",
        "client_mac_address", "custom_serial_code", "raw_sensor_id",
    ])
    def test_fuzzed_prohibited_key_detection(self, fuzzed_key: str):
        """Verify that standard casing, padding, and recognized substring variations are detected."""
        assert is_pii_key(fuzzed_key) is True, f"Failed to detect prohibited key: '{fuzzed_key}'"

    @pytest.mark.parametrize("bypass_key", [
        "e_mail",
        "e-mail",
        "e.mail",
        "full_name",
        "athlete_name",
        "patient_name",
        "client_name",
        "cell_phone",
        "mobile_phone",
        "contact_phone",
        "client_mail",
        "contact_mail",
        "postal_code",
        "zip_code",
        "ssn",
        "imei",
        "social",
        "address",
        "location",
        "latitude",
        "longitude",
    ])
    def test_hardened_pii_key_detection(self, bypass_key: str):
        """
        Hardened Zero-PII Detection:
        Verifies that non-alphanumeric normalization and comprehensive keyword sets
        intercept all common PII key variants (e_mail, e-mail, e.mail, full_name, cell_phone, etc.).
        """
        assert is_pii_key(bypass_key) is True, f"Key '{bypass_key}' should have been intercepted as PII"

    # -------------------------------------------------------------------------
    # 2. Obscured PII Value Patterns (MAC & Email variations)
    # -------------------------------------------------------------------------
    @pytest.mark.parametrize("fuzzed_mac", [
        "00:1A:2B:3C:4D:5E",
        "00:1a:2b:3c:4d:5e",
        "00-1A-2B-3C-4D-5E",
        "00-1a-2b-3c-4d-5e",
        "  AA:BB:CC:DD:EE:FF  ",
        "\t12:34:56:78:9A:BC\n",
    ])
    def test_fuzzed_mac_pattern_detection(self, fuzzed_mac: str):
        """Verify MAC address regex matches regardless of case, delimiters, or whitespace padding."""
        assert is_pii_value(fuzzed_mac) is True, f"Failed to detect MAC value: '{fuzzed_mac}'"

    @pytest.mark.parametrize("fuzzed_email", [
        "athlete@lauburu.com",
        "TEST.USER+TAG@SUB.DOMAIN.CO.UK",
        "first.last@medical-hospital.org",
        "  runner_123@fitness-cloud.io  ",
        "\tcoach@team.de\n",
    ])
    def test_fuzzed_email_pattern_detection(self, fuzzed_email: str):
        """Verify Email address regex matches complex, mixed-case, tagged, or padded addresses."""
        assert is_pii_value(fuzzed_email) is True, f"Failed to detect Email value: '{fuzzed_email}'"

    # -------------------------------------------------------------------------
    # 3. Deeply Nested JSON Payloads
    # -------------------------------------------------------------------------
    def test_deeply_nested_pii_key_detection(self):
        """Verify detection of PII keys nested 10 levels deep inside dictionaries and lists."""
        nested_payload = {
            "level1": {
                "level2": {
                    "level3": [
                        {"clean": 123},
                        {
                            "level5": {
                                "level6": {
                                    "level7": [
                                        {
                                            "level9": {
                                                "EMaiL": "sneaky@hidden.com"
                                            }
                                        }
                                    ]
                                }
                            }
                        }
                    ]
                }
            }
        }
        assert contains_pii(nested_payload) is True
        violations = get_pii_violations(nested_payload)
        assert len(violations) >= 2  # Prohibited key 'EMaiL' and Prohibited value 'sneaky@hidden.com'

    def test_deeply_nested_pii_sanitization(self):
        """Verify recursive sanitization scrubs deeply nested PII without corrupting clean structure."""
        nested_payload = {
            "valid_metric": 42.0,
            "sub_structure": {
                "keep_me": [1, 2, 3],
                "secret_user_id": 9999,
                "clean_child": {
                    "mac_address": "00:1A:2B:3C:4D:5E",
                    "safe_float": 3.14
                }
            }
        }
        cleaned = sanitize_pii(nested_payload)
        assert "valid_metric" in cleaned
        assert cleaned["sub_structure"]["keep_me"] == [1, 2, 3]
        assert "secret_user_id" not in cleaned["sub_structure"]
        assert "mac_address" not in cleaned["sub_structure"]["clean_child"]
        assert cleaned["sub_structure"]["clean_child"]["safe_float"] == 3.14

    # -------------------------------------------------------------------------
    # 4. HTTP Middleware Rejection: Fuzzed Query Parameters
    # -------------------------------------------------------------------------
    @pytest.mark.asyncio
    @pytest.mark.parametrize("fuzzed_query", [
        "email=attacker@evil.com",
        "EmAiL=victim@corp.com",
        "user_name=alice",
        "device_id=dev-9988",
        "mac_address=00:1A:2B:3C:4D:5E",
        "mac=00-11-22-33-44-55",
        "serial=SN-102938",
        "user_id=1001",
        "gps=37.7749,-122.4194",
        "ip_address=192.168.1.100",
        "sensor_id=sensor-01",
    ])
    async def test_middleware_rejects_fuzzed_query_params(self, fuzzed_query: str):
        """Verify middleware intercepts all PII query parameters and rejects with HTTP 422."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/health?{fuzzed_query}")
            assert response.status_code == 422
            data = response.json()
            assert "Zero-PII Policy Violation" in data["detail"]
            assert data["violation_type"] in ("prohibited_query_param", "prohibited_value_pattern")

    @pytest.mark.asyncio
    async def test_middleware_rejects_url_encoded_query_params(self):
        """Verify middleware catches URL-encoded PII parameters (e.g. %65%6d%61%69%6c -> email)."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # URL encoded 'email=test@test.com'
            response = await client.get("/health?%65%6d%61%69%6c=test%40test.com")
            assert response.status_code == 422
            assert "Zero-PII Policy Violation" in response.json()["detail"]

    # -------------------------------------------------------------------------
    # 5. HTTP Middleware Rejection: Custom PII Headers
    # -------------------------------------------------------------------------
    @pytest.mark.asyncio
    @pytest.mark.parametrize("pii_header,header_val", [
        ("X-User-Email", "test@test.com"),
        ("X-Device-Id", "device-uuid-1234"),
        ("X-Client-Mac", "00:1A:2B:3C:4D:5E"),
        ("X-User-Name", "john_doe"),
        ("X-Sensor-Serial", "SN-998811"),
        ("X-User-Id", "99001"),
        ("X-Device-Name", "Garmin-Edge"),
    ])
    async def test_middleware_rejects_custom_pii_headers(self, pii_header: str, header_val: str):
        """Verify middleware blocks custom X-* headers containing prohibited PII keys with HTTP 422."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {pii_header: header_val}
            response = await client.get("/health", headers=headers)
            assert response.status_code == 422
            assert "Zero-PII Policy Violation" in response.json()["detail"]
            assert response.json()["violation_type"] == "prohibited_header"

    # -------------------------------------------------------------------------
    # 6. HTTP Middleware Rejection: Invert Endpoint Fuzzed Payloads
    # -------------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_middleware_rejects_obscured_pii_in_inversion_body(self, clean_inversion_payload):
        """Verify middleware rejects POST /invert if payload contains obscured PII keys."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Inject nested PII key
            dirty_payload = dict(clean_inversion_payload)
            dirty_payload["metadata"] = {"DeViCe_MaC": "00:11:22:33:44:55"}

            response = await client.post("/api/v1/hemodynamics/invert", json=dirty_payload)
            assert response.status_code == 422
            data = response.json()
            assert "Zero-PII Policy Violation" in data["detail"]
            assert data["violation_type"] == "prohibited_payload_body"

    @pytest.mark.asyncio
    async def test_middleware_rejects_pii_value_without_pii_key(self, clean_inversion_payload):
        """Verify middleware rejects payload containing a MAC or email value even under a benign key."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            dirty_payload = dict(clean_inversion_payload)
            dirty_payload["custom_note"] = "00:1A:2B:3C:4D:5E"

            response = await client.post("/api/v1/hemodynamics/invert", json=dirty_payload)
            assert response.status_code == 422
            assert "Zero-PII Policy Violation" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_middleware_allows_clean_payloads_with_proper_status(self, clean_inversion_payload):
        """Positive Control: Verify clean telemetry requests pass through and return HTTP 200."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/hemodynamics/invert", json=clean_inversion_payload)
            assert response.status_code == 200
            data = response.json()
            assert "hemodynamic_state" in data
            assert data["hemodynamic_state"]["systolic_bp_mmHg"] > 0

    # -------------------------------------------------------------------------
    # 7. Schema Field Range Validations (Physiological Bounds)
    # -------------------------------------------------------------------------
    @pytest.mark.parametrize("invalid_field,invalid_val", [
        ("ptt_ms", 5.0),       # Below 10.0 ms
        ("ptt_ms", 2500.0),    # Above 2000.0 ms
        ("ptt_ms", -100.0),    # Negative
        ("hr_bpm", 10.0),      # Below 20.0 bpm
        ("hr_bpm", 350.0),     # Above 300.0 bpm
        ("hr_bpm", -50.0),     # Negative
        ("rr_ms", 50.0),       # Below 100.0 ms
        ("rr_ms", 3500.0),     # Above 3000.0 ms
        ("delta_t_dia_ms", 5.0),    # Below 20.0 ms
        ("delta_t_dia_ms", 2500.0), # Above 2000.0 ms
        ("imu_acc_g", -1.0),   # Negative
        ("imu_acc_g", 35.0),   # Above 30.0 g
        ("e0_elasticity", 5.0),     # Below 10.0 kPa
        ("e0_elasticity", 60000.0), # Above 50000.0 kPa
    ])
    def test_vector_u_physiological_bounds_validation(self, invalid_field: str, invalid_val: float):
        """Verify VectorU rejects physiologically impossible telemetry values with ValidationError."""
        valid_kwargs = {
            "ptt_ms": 220.0,
            "hr_bpm": 72.0,
            "rr_ms": 833.0,
            "delta_t_dia_ms": 280.0,
            "imu_acc_g": 1.0,
            "e0_elasticity": 400.0,
        }
        valid_kwargs[invalid_field] = invalid_val
        with pytest.raises(ValidationError):
            VectorU(**valid_kwargs)

    @pytest.mark.parametrize("invalid_field,invalid_val", [
        ("ptt_ms", 5.0),
        ("ptt_ms", 2500.0),
        ("ptt_ms", -50.0),
    ])
    def test_transit_hemodynamics_bounds_validation(self, invalid_field: str, invalid_val: float):
        """Verify TransitHemodynamics rejects invalid PTT bounds."""
        with pytest.raises(ValidationError):
            TransitHemodynamics(**{invalid_field: invalid_val})

    @pytest.mark.parametrize("invalid_field,invalid_val", [
        ("hr_bpm", 10.0),
        ("hr_bpm", 350.0),
        ("hr_bpm", -10.0),
    ])
    def test_cardiac_autonomic_bounds_validation(self, invalid_field: str, invalid_val: float):
        """Verify CardiacAutonomic rejects invalid HR bounds."""
        with pytest.raises(ValidationError):
            CardiacAutonomic(**{invalid_field: invalid_val})

    # -------------------------------------------------------------------------
    # 8. Schema Extra Field Forbidding (extra="forbid")
    # -------------------------------------------------------------------------
    def test_vector_u_forbids_extra_fields(self):
        """Verify VectorU rejects unmapped extra fields with ValidationError."""
        with pytest.raises(ValidationError):
            VectorU(
                ptt_ms=220.0,
                hr_bpm=72.0,
                rr_ms=833.0,
                delta_t_dia_ms=280.0,
                imu_acc_g=1.0,
                e0_elasticity=400.0,
                unrecognized_extra_metric=99.9,
            )

    def test_inversion_request_forbids_extra_fields(self):
        """Verify InversionRequest (and ZeroPiiPayload) rejects unmapped extra fields."""
        with pytest.raises(ValidationError):
            InversionRequest(
                session_token="a" * 64,
                delta_time_ms=1000,
                unexpected_payload_key=12345,
            )

    @pytest.mark.asyncio
    async def test_endpoint_rejects_out_of_bounds_telemetry_with_422(self, clean_inversion_payload):
        """Verify HTTP endpoint rejects out-of-bounds telemetry with 422 Unprocessable Entity."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            invalid_payload = dict(clean_inversion_payload)
            invalid_payload["vector_u"] = dict(clean_inversion_payload["vector_u"])
            invalid_payload["vector_u"]["ptt_ms"] = -500.0

            response = await client.post("/api/v1/hemodynamics/invert", json=invalid_payload)
            assert response.status_code == 422

