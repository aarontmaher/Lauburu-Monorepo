"""
GGUF Quantization Pipeline (Feature F14).
Provides two-stage compilation and conversion toolchain:
Stage 1: Converts HuggingFace / PyTorch Safetensors models into unquantized FP16/BF16 GGUF format.
Stage 2: Quantizes GGUF weights into target formats (Q4_K_M, IQ2_XXS, Q8_0, etc.) using llama-quantize.
Includes native binary GGUF header inspection and metadata verification.
"""

from __future__ import annotations

import os
import shutil
import struct
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union


# Supported quantization formats in the Lauburu Mesh
SUPPORTED_QUANT_TYPES: Set[str] = {
    "Q4_K_M",
    "IQ2_XXS",
    "Q8_0",
    "Q4_0",
    "Q4_1",
    "Q5_K_M",
    "Q6_K",
    "IQ3_XXS",
    "IQ1_S",
    "F16",
    "BF16",
    "F32",
}

# Supported precision output types for Stage 1 conversion
SUPPORTED_OUTTYPES: Set[str] = {"f16", "bf16", "f32", "q8_0"}

# Canonical paths in the Lauburu Mesh
DEFAULT_CONVERT_SCRIPT = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/prima_cpp/convert_hf_to_gguf.py"
DEFAULT_GGUF_PY_DIR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/prima_cpp/gguf-py"
DEFAULT_LLAMA_QUANTIZE_BIN = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/prima_cpp/llama-quantize"
DEFAULT_VAULT_DIR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf"

# GGUF Magic constants
GGUF_MAGIC = b"GGUF"
GGUF_MAGIC_LE = 0x46554747  # Little-endian 'GGUF'


@dataclass
class GGUFMetadata:
    """Metadata extracted from a GGUF file header."""
    file_path: str
    file_size_bytes: int
    magic: str
    version: int
    tensor_count: int
    metadata_kv_count: int
    architecture: Optional[str] = None
    quant_type: Optional[str] = None
    context_length: Optional[int] = None
    embedding_length: Optional[int] = None
    extra_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "magic": self.magic,
            "version": self.version,
            "tensor_count": self.tensor_count,
            "metadata_kv_count": self.metadata_kv_count,
            "architecture": self.architecture,
            "quant_type": self.quant_type,
            "context_length": self.context_length,
            "embedding_length": self.embedding_length,
            "extra_metadata": self.extra_metadata,
        }


@dataclass
class QuantizationResult:
    """Result of a GGUF conversion or quantization execution."""
    status: str
    input_path: str
    output_path: str
    quant_type: str
    file_size_bytes: int = 0
    duration_sec: float = 0.0
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "input_path": self.input_path,
            "output_path": self.output_path,
            "quant_type": self.quant_type,
            "file_size_bytes": self.file_size_bytes,
            "duration_sec": self.duration_sec,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "error_message": self.error_message,
        }


def _read_gguf_string(f) -> Optional[str]:
    """Helper to read a length-prefixed string from GGUF binary file."""
    len_bytes = f.read(8)
    if len(len_bytes) < 8:
        return None
    str_len = struct.unpack("<Q", len_bytes)[0]
    if str_len > 10 * 1024 * 1024:  # Safety sanity check: max 10MB string
        return None
    str_bytes = f.read(str_len)
    if len(str_bytes) < str_len:
        return None
    return str_bytes.decode("utf-8", errors="replace")


def inspect_gguf(gguf_path: Union[str, Path]) -> GGUFMetadata:
    """
    Parses and inspects the binary header and metadata of a GGUF file.

    Args:
        gguf_path: Path to the .gguf file.

    Returns:
        GGUFMetadata dataclass with parsed header information.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file is not a valid GGUF file.
    """
    p = Path(gguf_path)
    if not p.exists():
        raise FileNotFoundError(f"GGUF file not found: {p}")
    if not p.is_file():
        raise ValueError(f"Path is not a regular file: {p}")

    file_size = p.stat().st_size
    if file_size < 24:  # Minimum GGUF header size
        raise ValueError(f"GGUF file too small ({file_size} bytes, minimum 24 bytes required): {p}")

    with open(p, "rb") as f:
        magic = f.read(4)
        if magic != GGUF_MAGIC:
            raise ValueError(f"Invalid GGUF magic bytes: {magic!r}, expected {GGUF_MAGIC!r}")

        header_bytes = f.read(20)
        if len(header_bytes) < 20:
            raise ValueError(f"Truncated GGUF header in file: {p}")

        version, tensor_count, metadata_kv_count = struct.unpack("<IQQ", header_bytes)

        extra_kv: Dict[str, Any] = {}
        architecture = None
        context_length = None
        embedding_length = None

        # Attempt reading key-value metadata pairs
        try:
            for _ in range(min(metadata_kv_count, 500)):
                key = _read_gguf_string(f)
                if key is None:
                    break
                # Value type uint32
                type_bytes = f.read(4)
                if len(type_bytes) < 4:
                    break
                val_type = struct.unpack("<I", type_bytes)[0]

                # Type mapping: 0=UINT8, 1=INT8, 2=UINT16, 3=INT16, 4=UINT32, 5=INT32,
                # 6=FLOAT32, 7=BOOL, 8=STRING, 9=ARRAY, 10=UINT64, 11=INT64, 12=FLOAT64
                if val_type == 8:  # STRING
                    val = _read_gguf_string(f)
                    extra_kv[key] = val
                    if key.endswith(".architecture") or key == "general.architecture":
                        architecture = val
                elif val_type in (0, 1):
                    b = f.read(1)
                    if len(b) == 1:
                        extra_kv[key] = struct.unpack("<B" if val_type == 0 else "<b", b)[0]
                elif val_type in (2, 3):
                    b = f.read(2)
                    if len(b) == 2:
                        extra_kv[key] = struct.unpack("<H" if val_type == 2 else "<h", b)[0]
                elif val_type in (4, 5):
                    b = f.read(4)
                    if len(b) == 4:
                        val = struct.unpack("<I" if val_type == 4 else "<i", b)[0]
                        extra_kv[key] = val
                        if "context_length" in key:
                            context_length = val
                        elif "embedding_length" in key:
                            embedding_length = val
                elif val_type == 6:  # FLOAT32
                    b = f.read(4)
                    if len(b) == 4:
                        extra_kv[key] = struct.unpack("<f", b)[0]
                elif val_type == 7:  # BOOL
                    b = f.read(1)
                    if len(b) == 1:
                        extra_kv[key] = bool(b[0])
                elif val_type in (10, 11):
                    b = f.read(8)
                    if len(b) == 8:
                        val = struct.unpack("<Q" if val_type == 10 else "<q", b)[0]
                        extra_kv[key] = val
                        if "context_length" in key:
                            context_length = val
                        elif "embedding_length" in key:
                            embedding_length = val
                elif val_type == 12:  # FLOAT64
                    b = f.read(8)
                    if len(b) == 8:
                        extra_kv[key] = struct.unpack("<d", b)[0]
                else:
                    # Array or unknown, stop parsing KV pairs
                    break
        except Exception:
            pass  # Header reading is best-effort for extended KV

    # Infer quant_type from filename if present
    quant_type = None
    for qt in sorted(SUPPORTED_QUANT_TYPES, key=len, reverse=True):
        if qt.upper() in p.stem.upper():
            quant_type = qt
            break

    return GGUFMetadata(
        file_path=str(p.resolve()),
        file_size_bytes=file_size,
        magic="GGUF",
        version=version,
        tensor_count=tensor_count,
        metadata_kv_count=metadata_kv_count,
        architecture=architecture,
        quant_type=quant_type,
        context_length=context_length,
        embedding_length=embedding_length,
        extra_metadata=extra_kv,
    )


def validate_gguf(gguf_path: Union[str, Path]) -> Tuple[bool, List[str]]:
    """
    Validates that a file is a non-empty, well-formed GGUF file.

    Args:
        gguf_path: Path to the GGUF file.

    Returns:
        Tuple of (is_valid, list_of_errors).
    """
    errors: List[str] = []
    p = Path(gguf_path)

    if not p.exists():
        return False, [f"File does not exist: {p}"]
    if not p.is_file():
        return False, [f"Path is not a regular file: {p}"]

    size = p.stat().st_size
    if size == 0:
        return False, [f"File is 0 bytes: {p}"]
    if size < 24:
        return False, [f"File is smaller than minimal GGUF header (24 bytes): {size} bytes"]

    try:
        meta = inspect_gguf(p)
        if meta.version not in (2, 3):
            errors.append(f"Unexpected GGUF version: {meta.version} (expected 2 or 3)")
        if meta.tensor_count == 0:
            errors.append("GGUF file has 0 tensors")
    except Exception as e:
        return False, [f"GGUF header validation error: {e}"]

    return len(errors) == 0, errors


class GGUFQuantizer:
    """
    Orchestrates the two-stage GGUF conversion and quantization toolchain.
    """

    def __init__(
        self,
        convert_script_path: str = DEFAULT_CONVERT_SCRIPT,
        llama_quantize_path: str = DEFAULT_LLAMA_QUANTIZE_BIN,
        gguf_py_dir: str = DEFAULT_GGUF_PY_DIR,
        default_vault_dir: str = DEFAULT_VAULT_DIR,
        python_bin: Optional[str] = None,
    ):
        self.convert_script_path = convert_script_path
        self.llama_quantize_path = llama_quantize_path
        self.gguf_py_dir = gguf_py_dir
        self.default_vault_dir = default_vault_dir
        self.python_bin = python_bin or sys.executable

    def convert_hf_to_gguf(
        self,
        hf_model_dir: Union[str, Path],
        output_gguf_path: Union[str, Path],
        outtype: str = "f16",
        vocab_only: bool = False,
        timeout_sec: float = 600.0,
    ) -> QuantizationResult:
        """
        Stage 1: Converts HuggingFace / Safetensors directory to unquantized GGUF.

        Args:
            hf_model_dir: Directory containing model weights and config.json.
            output_gguf_path: Destination .gguf file path.
            outtype: Output precision ('f16', 'bf16', 'f32').
            vocab_only: If True, extracts only the vocabulary.
            timeout_sec: Process timeout in seconds.

        Returns:
            QuantizationResult dataclass.
        """
        in_p = Path(hf_model_dir)
        if not in_p.exists():
            raise FileNotFoundError(f"Input HF directory does not exist: {in_p}")

        outtype_clean = outtype.lower()
        if outtype_clean not in SUPPORTED_OUTTYPES:
            raise ValueError(f"Unsupported outtype '{outtype}'. Must be one of {sorted(SUPPORTED_OUTTYPES)}")

        out_p = Path(output_gguf_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        convert_script = Path(self.convert_script_path)
        if not convert_script.exists():
            # Fallback: check if local prima_cpp or llama.cpp has convert_hf_to_gguf.py
            alt_paths = [
                Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/prima_cpp/convert_hf_to_gguf.py"),
                Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/llama_cpp/convert_hf_to_gguf.py"),
            ]
            for ap in alt_paths:
                if ap.exists():
                    convert_script = ap
                    break

        cmd = [
            self.python_bin,
            str(convert_script),
            str(in_p),
            "--outfile",
            str(out_p),
            "--outtype",
            outtype_clean,
        ]
        if vocab_only:
            cmd.append("--vocab-only")

        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH", "")
        if self.gguf_py_dir and Path(self.gguf_py_dir).exists():
            env["PYTHONPATH"] = f"{self.gguf_py_dir}:{pythonpath}" if pythonpath else self.gguf_py_dir

        start_time = time.time()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                env=env,
            )
            duration = time.time() - start_time
            size = out_p.stat().st_size if out_p.exists() else 0

            status = "SUCCESS" if proc.returncode == 0 and out_p.exists() and size > 0 else "FAILED"
            err_msg = None if status == "SUCCESS" else (proc.stderr or f"Process returned code {proc.returncode}")

            return QuantizationResult(
                status=status,
                input_path=str(in_p),
                output_path=str(out_p),
                quant_type=outtype.upper(),
                file_size_bytes=size,
                duration_sec=duration,
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                error_message=err_msg,
            )
        except subprocess.TimeoutExpired as e:
            return QuantizationResult(
                status="TIMEOUT",
                input_path=str(in_p),
                output_path=str(out_p),
                quant_type=outtype.upper(),
                duration_sec=time.time() - start_time,
                returncode=-1,
                error_message=f"Conversion timed out after {timeout_sec}s: {e}",
            )
        except Exception as e:
            return QuantizationResult(
                status="ERROR",
                input_path=str(in_p),
                output_path=str(out_p),
                quant_type=outtype.upper(),
                duration_sec=time.time() - start_time,
                returncode=-1,
                error_message=str(e),
            )

    def quantize_gguf(
        self,
        input_gguf_path: Union[str, Path],
        output_gguf_path: Union[str, Path],
        quant_type: str = "Q4_K_M",
        timeout_sec: float = 600.0,
    ) -> QuantizationResult:
        """
        Stage 2: Quantizes an FP16 GGUF file into target quantization type.

        Args:
            input_gguf_path: Source unquantized .gguf file.
            output_gguf_path: Target quantized .gguf file.
            quant_type: Target quantization type (e.g. 'Q4_K_M', 'IQ2_XXS').
            timeout_sec: Process timeout.

        Returns:
            QuantizationResult dataclass.
        """
        in_p = Path(input_gguf_path)
        if not in_p.exists():
            raise FileNotFoundError(f"Input GGUF file does not exist: {in_p}")

        quant_clean = quant_type.upper()
        if quant_clean not in SUPPORTED_QUANT_TYPES:
            raise ValueError(f"Unsupported quant_type '{quant_type}'. Must be one of {sorted(SUPPORTED_QUANT_TYPES)}")

        out_p = Path(output_gguf_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        quant_bin = Path(self.llama_quantize_path)
        if not quant_bin.exists():
            alt_bins = [
                Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/prima_cpp/llama-quantize"),
                Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/llama_cpp/llama-quantize"),
                Path(shutil.which("llama-quantize") or ""),
            ]
            for ab in alt_bins:
                if str(ab) and ab.exists():
                    quant_bin = ab
                    break

        cmd = [
            str(quant_bin),
            str(in_p),
            str(out_p),
            quant_clean,
        ]

        start_time = time.time()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            duration = time.time() - start_time
            size = out_p.stat().st_size if out_p.exists() else 0

            status = "SUCCESS" if proc.returncode == 0 and out_p.exists() and size > 0 else "FAILED"
            err_msg = None if status == "SUCCESS" else (proc.stderr or f"Process returned code {proc.returncode}")

            return QuantizationResult(
                status=status,
                input_path=str(in_p),
                output_path=str(out_p),
                quant_type=quant_clean,
                file_size_bytes=size,
                duration_sec=duration,
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                error_message=err_msg,
            )
        except subprocess.TimeoutExpired as e:
            return QuantizationResult(
                status="TIMEOUT",
                input_path=str(in_p),
                output_path=str(out_p),
                quant_type=quant_clean,
                duration_sec=time.time() - start_time,
                returncode=-1,
                error_message=f"Quantization timed out after {timeout_sec}s: {e}",
            )
        except Exception as e:
            return QuantizationResult(
                status="ERROR",
                input_path=str(in_p),
                output_path=str(out_p),
                quant_type=quant_clean,
                duration_sec=time.time() - start_time,
                returncode=-1,
                error_message=str(e),
            )

    def quantize_model(
        self,
        hf_model_dir: Union[str, Path],
        output_gguf_path: Union[str, Path],
        quant_type: str = "Q4_K_M",
        temp_f16_path: Optional[Union[str, Path]] = None,
        cleanup_intermediate: bool = True,
        outtype: str = "f16",
    ) -> QuantizationResult:
        """
        Complete end-to-end two-stage quantization:
        HuggingFace Model -> Intermediate FP16 GGUF -> Target Quantized GGUF.

        Args:
            hf_model_dir: Path to merged HuggingFace model.
            output_gguf_path: Path to target quantized GGUF file.
            quant_type: Target quantization type ('Q4_K_M', 'IQ2_XXS', etc.).
            temp_f16_path: Optional custom path for intermediate FP16 GGUF.
            cleanup_intermediate: If True, deletes intermediate FP16 file.
            outtype: Intermediate precision ('f16' or 'bf16').

        Returns:
            QuantizationResult dataclass.
        """
        if not hf_model_dir or not output_gguf_path:
            raise ValueError("hf_model_dir and output_gguf_path must be non-empty")

        quant_clean = quant_type.upper()
        if quant_clean not in SUPPORTED_QUANT_TYPES:
            raise ValueError(f"Unsupported quant_type '{quant_type}'. Must be one of {sorted(SUPPORTED_QUANT_TYPES)}")

        out_p = Path(output_gguf_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        if temp_f16_path is not None:
            f16_path = Path(temp_f16_path)
        else:
            f16_path = out_p.parent / f"{out_p.stem}_temp_f16.gguf"

        start_time = time.time()

        # Direct FP16 / BF16 export case
        if quant_clean in ("F16", "BF16", "F32"):
            res1 = self.convert_hf_to_gguf(
                hf_model_dir=hf_model_dir,
                output_gguf_path=output_gguf_path,
                outtype=quant_clean.lower(),
            )
            return res1

        # Stage 1: Convert to FP16 GGUF
        res1 = self.convert_hf_to_gguf(
            hf_model_dir=hf_model_dir,
            output_gguf_path=f16_path,
            outtype=outtype,
        )
        if res1.status != "SUCCESS":
            return res1

        # Stage 2: Quantize FP16 GGUF to target
        res2 = self.quantize_gguf(
            input_gguf_path=f16_path,
            output_gguf_path=output_gguf_path,
            quant_type=quant_clean,
        )

        # Cleanup intermediate
        if cleanup_intermediate and f16_path.exists():
            try:
                f16_path.unlink()
            except Exception:
                pass

        total_duration = time.time() - start_time
        res2.duration_sec = total_duration
        return res2


# Convenience module-level API matching interface contracts
def convert_hf_to_gguf(
    hf_model_dir: Union[str, Path],
    output_gguf_path: Union[str, Path],
    outtype: str = "f16",
    **kwargs: Any,
) -> QuantizationResult:
    quantizer = GGUFQuantizer()
    return quantizer.convert_hf_to_gguf(hf_model_dir, output_gguf_path, outtype=outtype, **kwargs)


def quantize_gguf(
    input_gguf_path: Union[str, Path],
    output_gguf_path: Union[str, Path],
    quant_type: str = "Q4_K_M",
    **kwargs: Any,
) -> QuantizationResult:
    quantizer = GGUFQuantizer()
    return quantizer.quantize_gguf(input_gguf_path, output_gguf_path, quant_type=quant_type, **kwargs)


def quantize_model(
    hf_model_dir: Union[str, Path],
    output_gguf_path: Union[str, Path],
    quant_type: str = "Q4_K_M",
    **kwargs: Any,
) -> QuantizationResult:
    quantizer = GGUFQuantizer()
    return quantizer.quantize_model(hf_model_dir, output_gguf_path, quant_type=quant_type, **kwargs)
