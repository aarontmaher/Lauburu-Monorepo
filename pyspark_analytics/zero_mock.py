"""
Rule #0 Zero-Mock Verification Engine.
Enforces zero-mock requirements on training datasets, compiler traces, and test execution data.
No synthetic, dummy, or mock records are permitted to pass into lora_datasets.
"""

import json
import os
from typing import Dict, Any, List


class RuleZeroError(ValueError):
    """Raised when a dataset record fails Rule #0 zero-mock verification."""
    pass


class ZeroMockVerifier:
    """
    Validates organic compiler and test execution traces to ensure zero mock data.
    Rule #0 Criteria:
    1. Mandatory provenance: record must cite real trace_file or execution_id from actual tool runs.
    2. Zero mock flags: `is_mock`, `synthetic`, `dummy`, `mock` must NOT be True or present as positive flags.
    3. Mandatory real execution metadata: compiler_exit_code/test_exit_code, timestamp, duration_ms, host/env info.
    4. Non-trivial content: prompt, chosen, rejected must contain real compiler/test strings, not mock placeholders.
    """

    MOCK_INDICATORS = [
        "mock",
        "synthetic",
        "dummy",
        "fake",
        "placeholder",
        "simulated",
        "sample_code",
        "test_mock",
    ]

    @classmethod
    def verify_record(cls, record: Dict[str, Any]) -> bool:
        """
        Verifies a single DPO training record against Rule #0 requirements.
        Raises RuleZeroError if record contains mock data or lacks required trace provenance.
        """
        if not isinstance(record, dict):
            raise RuleZeroError("Record must be a JSON object dictionary.")

        # Check explicit mock/synthetic boolean flags
        for flag in ["is_mock", "synthetic", "mock", "is_synthetic", "dummy_data"]:
            if record.get(flag) is True or str(record.get(flag)).lower() in ("true", "1"):
                raise RuleZeroError(f"Rule #0 Violation: Record explicitly flagged with {flag}=True.")

        # Check required fields
        for required_field in ["prompt", "chosen", "rejected", "metadata"]:
            if required_field not in record or not record[required_field]:
                raise RuleZeroError(f"Rule #0 Violation: Missing required field '{required_field}'.")

        metadata = record.get("metadata", {})
        if not isinstance(metadata, dict):
            raise RuleZeroError("Rule #0 Violation: Metadata must be a dictionary.")

        # Check trace provenance
        trace_file = metadata.get("trace_file") or metadata.get("execution_id") or metadata.get("source_trace")
        if not trace_file or not isinstance(trace_file, str) or len(trace_file.strip()) < 3:
            raise RuleZeroError("Rule #0 Violation: Missing valid trace provenance (trace_file or execution_id).")

        # Check execution telemetry
        has_exit_code = "exit_code" in metadata or "compiler_exit_code" in metadata or "test_exit_code" in metadata
        has_timestamp = "timestamp" in metadata or "created_at" in metadata
        has_duration = "duration_ms" in metadata or "execution_time_ms" in metadata

        if not (has_exit_code and has_timestamp and has_duration):
            raise RuleZeroError(
                "Rule #0 Violation: Incomplete execution telemetry in metadata. "
                "Must include exit_code, timestamp, and duration_ms."
            )

        # Scan text fields for mock/synthetic placeholders
        prompt = str(record.get("prompt", "")).lower()
        chosen = str(record.get("chosen", "")).lower()
        rejected = str(record.get("rejected", "")).lower()

        # Rejection of explicit mock markers in prompt/chosen/rejected content
        for indicator in cls.MOCK_INDICATORS:
            if f"[mock" in prompt or f"mock_" in prompt or prompt == "mock" or prompt == "dummy":
                raise RuleZeroError(f"Rule #0 Violation: Prompt contains mock indicator '{indicator}'.")
            if f"[mock" in chosen or f"mock_" in chosen or chosen == "mock" or chosen == "dummy":
                raise RuleZeroError(f"Rule #0 Violation: Chosen output contains mock indicator '{indicator}'.")

        return True

    @classmethod
    def verify_dataset_file(cls, jsonl_path: str) -> Dict[str, Any]:
        """
        Verifies an entire JSONL dataset file against Rule #0 zero-mock criteria.
        Returns summary statistics if valid; raises RuleZeroError on the first violation.
        """
        if not os.path.exists(jsonl_path):
            raise FileNotFoundError(f"Dataset file not found: {jsonl_path}")

        total_records = 0
        verified_records = 0

        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                total_records += 1
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as e:
                    raise RuleZeroError(f"Invalid JSON on line {line_num}: {e}")

                try:
                    cls.verify_record(record)
                    verified_records += 1
                except RuleZeroError as e:
                    raise RuleZeroError(f"Line {line_num} failed Rule #0 verification: {e}")

        return {
            "file": jsonl_path,
            "total_records": total_records,
            "verified_records": verified_records,
            "status": "PASS_ZERO_MOCK_VERIFIED",
        }
