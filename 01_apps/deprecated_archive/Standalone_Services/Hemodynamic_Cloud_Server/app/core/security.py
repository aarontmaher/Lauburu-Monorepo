"""
Zero-PII security, HMAC-SHA256 tokenization, and strict PII gate enforcement.
"""

import hmac
import hashlib
import time
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from app.core.config import settings

# Comprehensive list of prohibited Personally Identifiable Information (PII) keys
PROHIBITED_PII_KEYS: Set[str] = {
    "name", "username", "user_name", "first_name", "firstname", "last_name", "lastname",
    "fullname", "full_name", "athletename", "athlete_name", "patientname", "patient_name",
    "clientname", "client_name",
    "email", "useremail", "user_email", "mail", "clientmail", "client_mail", "contactmail", "contact_mail",
    "mac", "mac_address", "macaddress", "bluetooth_address", "ble_mac", "blemac",
    "serial", "serial_number", "serialnumber", "device_serial", "deviceserial",
    "device_id", "deviceid", "user_id", "userid", "uuid", "guid",
    "ip_address", "ipaddress", "client_ip", "clientip", "remote_addr", "remoteaddr",
    "phone", "phone_number", "phonenumber", "cellphone", "cell_phone", "mobilephone", "mobile_phone",
    "contactphone", "contact_phone",
    "gps", "latitude", "lat", "longitude", "lon", "location", "address",
    "sensor_id", "sensorid", "device_name", "devicename",
    "postalcode", "postal_code", "zipcode", "zip_code", "postal", "zip",
    "ssn", "imei", "social"
}

PROHIBITED_PII_SUBSTRINGS: List[str] = [
    "name", "mail", "phone", "mac", "serial", "uuid", "guid",
    "device", "sensor", "user", "athlete", "patient",
    "postal", "zip", "ssn", "imei", "social", "address", "location", "gps", "lat", "lon"
]

MAC_ADDRESS_REGEX = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def is_pii_key(key: str) -> bool:
    """
    Check whether a key name violates the Zero-PII policy.
    Normalizes input by stripping all non-alphanumeric characters.
    """
    if not isinstance(key, str):
        key = str(key)
    normalized = re.sub(r"[^a-z0-9]", "", key.lower().strip())
    if not normalized:
        return False
    if normalized in PROHIBITED_PII_KEYS:
        return True
    for sub in PROHIBITED_PII_SUBSTRINGS:
        if sub in normalized:
            return True
    return False


def is_pii_value(value: Any) -> bool:
    """Check whether a primitive value matches known PII patterns (e.g. MAC, Email)."""
    if isinstance(value, str):
        val_strip = value.strip()
        if MAC_ADDRESS_REGEX.match(val_strip):
            return True
        if EMAIL_REGEX.match(val_strip):
            return True
    return False


def get_pii_violations(obj: Any, path: str = "") -> List[str]:
    """Recursively scan an object and return all paths violating Zero-PII policy."""
    violations: List[str] = []
    
    if isinstance(obj, dict):
        for k, v in obj.items():
            current_path = f"{path}.{k}" if path else str(k)
            if is_pii_key(str(k)):
                violations.append(f"Prohibited key '{k}' at '{current_path}'")
            if is_pii_value(v):
                violations.append(f"Prohibited value matching PII pattern at '{current_path}'")
            violations.extend(get_pii_violations(v, current_path))
    elif isinstance(obj, (list, tuple, set)):
        for idx, item in enumerate(obj):
            current_path = f"{path}[{idx}]"
            if is_pii_value(item):
                violations.append(f"Prohibited value matching PII pattern at '{current_path}'")
            violations.extend(get_pii_violations(item, current_path))
    elif is_pii_value(obj):
        violations.append(f"Prohibited value matching PII pattern at '{path}'")
        
    return violations


def contains_pii(obj: Any) -> bool:
    """Return True if the object contains any prohibited PII keys or patterns."""
    return len(get_pii_violations(obj)) > 0


def sanitize_pii(obj: Any) -> Any:
    """Recursively remove all prohibited PII keys and values."""
    if isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            if is_pii_key(str(k)):
                continue
            if is_pii_value(v):
                continue
            cleaned[k] = sanitize_pii(v)
        return cleaned
    elif isinstance(obj, list):
        return [sanitize_pii(item) for item in obj if not is_pii_value(item)]
    elif is_pii_value(obj):
        return None
    return obj


def generate_session_token(secret: Optional[str] = None, nonce: Optional[str] = None) -> str:
    """
    Generate an anonymous, deterministic HMAC-SHA256 session token.
    Uses constant-time construction.
    """
    key = (secret or settings.ZERO_PII_HMAC_SECRET).encode("utf-8")
    if nonce is None:
        now_ns = time.time_ns()
        rand_bytes = os.urandom(16).hex()
        nonce = f"{now_ns}_{rand_bytes}"
    msg = nonce.encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def compute_hmac_signature(key: str, message: str) -> str:
    """Compute HMAC-SHA256 signature for a message given a secret key."""
    return hmac.new(key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_hmac_signature(key: str, message: str, signature: str) -> bool:
    """
    Validate HMAC-SHA256 signature using constant-time comparison
    to prevent timing attacks.
    """
    expected = compute_hmac_signature(key, message)
    return hmac.compare_digest(expected, signature)


def validate_session_token_format(token: str) -> bool:
    """Validate that the session token is a valid 64-character hexadecimal SHA-256 hash."""
    if not isinstance(token, str):
        return False
    if len(token) != 64:
        return False
    try:
        int(token, 16)
        return True
    except ValueError:
        return False
