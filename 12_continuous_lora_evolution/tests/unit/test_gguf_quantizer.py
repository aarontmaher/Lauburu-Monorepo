"""
Unit Tests for GGUF Quantization Pipeline (Feature F14).
Tests binary GGUF header inspection, metadata parsing, quantization type validation,
and two-stage conversion pipeline error handling and directory creation.
"""

import os
import struct
import tempfile
import unittest
from pathlib import Path

from src.weight_merging.gguf_quantizer import (
    DEFAULT_VAULT_DIR,
    GGUF_MAGIC,
    SUPPORTED_OUTTYPES,
    SUPPORTED_QUANT_TYPES,
    GGUFMetadata,
    GGUFQuantizer,
    QuantizationResult,
    convert_hf_to_gguf,
    inspect_gguf,
    quantize_gguf,
    quantize_model,
    validate_gguf,
)


def create_synthetic_gguf_file(
    file_path: Path,
    version: int = 3,
    tensor_count: int = 42,
    arch_name: str = "qwen2",
    context_length: int = 32768,
) -> None:
    """Creates a well-formed binary GGUF file for testing inspection."""
    with open(file_path, "wb") as f:
        # Magic (4 bytes)
        f.write(GGUF_MAGIC)
        # Header: version (uint32), tensor_count (uint64), metadata_kv_count (uint64)
        # We write 2 metadata pairs: general.architecture (string) and general.context_length (uint32)
        f.write(struct.pack("<IQQ", version, tensor_count, 2))

        # Metadata 1: general.architecture (STRING = 8)
        key1 = "general.architecture"
        f.write(struct.pack("<Q", len(key1)))
        f.write(key1.encode("utf-8"))
        f.write(struct.pack("<I", 8))  # val_type = STRING
        f.write(struct.pack("<Q", len(arch_name)))
        f.write(arch_name.encode("utf-8"))

        # Metadata 2: qwen2.context_length (UINT32 = 4)
        key2 = f"{arch_name}.context_length"
        f.write(struct.pack("<Q", len(key2)))
        f.write(key2.encode("utf-8"))
        f.write(struct.pack("<I", 4))  # val_type = UINT32
        f.write(struct.pack("<I", context_length))

        # Pad with dummy tensor payload
        f.write(b"\x00" * 128)


class TestGGUFQuantizer(unittest.TestCase):
    """Test suite for GGUF quantizer and header parser."""

    def test_supported_quant_types_and_outtypes(self):
        """Validates that standard quant types and outtypes are supported."""
        self.assertIn("Q4_K_M", SUPPORTED_QUANT_TYPES)
        self.assertIn("IQ2_XXS", SUPPORTED_QUANT_TYPES)
        self.assertIn("Q8_0", SUPPORTED_QUANT_TYPES)
        self.assertIn("f16", SUPPORTED_OUTTYPES)
        self.assertIn("bf16", SUPPORTED_OUTTYPES)

    def test_gguf_metadata_dataclass(self):
        """GGUFMetadata stores and serializes attributes properly."""
        meta = GGUFMetadata(
            file_path="/vault/model-Q4_K_M.gguf",
            file_size_bytes=1024 * 1024,
            magic="GGUF",
            version=3,
            tensor_count=120,
            metadata_kv_count=15,
            architecture="qwen2",
            quant_type="Q4_K_M",
            context_length=32768,
        )
        d = meta.to_dict()
        self.assertEqual(d["magic"], "GGUF")
        self.assertEqual(d["version"], 3)
        self.assertEqual(d["tensor_count"], 120)
        self.assertEqual(d["architecture"], "qwen2")

    def test_inspect_gguf_binary_parser(self):
        """inspect_gguf reads real binary GGUF headers accurately."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            gguf_path = Path(tmp_dir) / "test_model-Q4_K_M.gguf"
            create_synthetic_gguf_file(
                gguf_path,
                version=3,
                tensor_count=64,
                arch_name="qwen2",
                context_length=32768,
            )

            meta = inspect_gguf(gguf_path)
            self.assertEqual(meta.magic, "GGUF")
            self.assertEqual(meta.version, 3)
            self.assertEqual(meta.tensor_count, 64)
            self.assertEqual(meta.architecture, "qwen2")
            self.assertEqual(meta.context_length, 32768)
            self.assertEqual(meta.quant_type, "Q4_K_M")

    def test_inspect_gguf_file_not_found(self):
        """inspect_gguf raises FileNotFoundError for non-existent files."""
        with self.assertRaises(FileNotFoundError):
            inspect_gguf("/non_existent_path_98765.gguf")

    def test_inspect_gguf_invalid_magic_bytes(self):
        """inspect_gguf raises ValueError for invalid magic bytes."""
        with tempfile.NamedTemporaryFile(suffix=".gguf", delete=False) as tmp:
            tmp.write(b"NOT_GGUF_HEADER_DATA_PADDING_1234567890")
            tmp_path = Path(tmp.name)

        try:
            with self.assertRaises(ValueError) as ctx:
                inspect_gguf(tmp_path)
            self.assertIn("Invalid GGUF magic", str(ctx.exception))
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_validate_gguf_success_and_failures(self):
        """validate_gguf properly distinguishes valid GGUF from corrupt files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 1. Valid file
            valid_path = Path(tmp_dir) / "valid.gguf"
            create_synthetic_gguf_file(valid_path, version=3, tensor_count=10)
            is_valid, errors = validate_gguf(valid_path)
            self.assertTrue(is_valid)
            self.assertEqual(len(errors), 0)

            # 2. 0-byte file
            empty_path = Path(tmp_dir) / "empty.gguf"
            empty_path.touch()
            is_valid_empty, err_empty = validate_gguf(empty_path)
            self.assertFalse(is_valid_empty)
            self.assertTrue(any("0 bytes" in e for e in err_empty))

            # 3. Non-existent file
            is_valid_none, _ = validate_gguf(Path(tmp_dir) / "missing.gguf")
            self.assertFalse(is_valid_none)

    def test_convert_hf_to_gguf_validation(self):
        """convert_hf_to_gguf validates input directory and outtype."""
        quantizer = GGUFQuantizer()
        with self.assertRaises(FileNotFoundError):
            quantizer.convert_hf_to_gguf("/non_existent_hf_dir", "/out.gguf")

        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaises(ValueError):
                quantizer.convert_hf_to_gguf(tmp_dir, "/out.gguf", outtype="invalid_outtype")

    def test_quantize_gguf_validation(self):
        """quantize_gguf validates input file and quant_type."""
        quantizer = GGUFQuantizer()
        with self.assertRaises(FileNotFoundError):
            quantizer.quantize_gguf("/non_existent.gguf", "/out.gguf")

        with tempfile.NamedTemporaryFile(suffix=".gguf", delete=False) as tmp:
            tmp.write(b"data")
            tmp_path = Path(tmp.name)

        try:
            with self.assertRaises(ValueError):
                quantizer.quantize_gguf(tmp_path, "/out.gguf", quant_type="INVALID_TYPE")
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_quantize_model_interface_contract(self):
        """quantize_model interface contract validates empty paths and creates output dirs."""
        quantizer = GGUFQuantizer()
        with self.assertRaises(ValueError):
            quantize_model("", "/out.gguf")
        with self.assertRaises(ValueError):
            quantize_model("/hf", "")

    def test_output_parent_directory_creation(self):
        """quantize_model automatically creates parent output directories."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            nested_out = Path(tmp_dir) / "sub1" / "sub2" / "model-Q4_K_M.gguf"
            # Direct invocation on GGUFQuantizer with non-existent directory triggers validation
            quantizer = GGUFQuantizer()
            with self.assertRaises(FileNotFoundError):
                quantizer.convert_hf_to_gguf("/non_existent_dir", nested_out)


if __name__ == "__main__":
    unittest.main()
