#!/usr/bin/env python3
"""Deterministic fake-hardware-data scanner (Rule 23: Zero-Fabrication Hard Gate).

Finds values that are shown as live hardware/network/AI telemetry but are really
literals, fallbacks or synthetic generators. Deterministic and fast; this is the
*verifier* used by the pre-commit gate and by the local-AI bounty hunter.

Usage:
  fake_data_scanner.py --all [ROOT]          # full scan, JSON to stdout
  fake_data_scanner.py --staged              # git staged files only (pre-commit)
  fake_data_scanner.py FILE [FILE...]        # specific files
  fake_data_scanner.py --check FILE LINE     # exit 0 if LINE in FILE is a confirmed finding

Suppress a reviewed line with an inline marker that states why:
  speed_map = {"tb3": 40.0}  # spec-ok: lookup table of standard rates, not a reading
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def get_repo_root() -> Path:
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()
        if out:
            return Path(out)
    except Exception:
        pass
    return Path("/Volumes/Lauburu-Monorepo")


REPO = get_repo_root()
EXTS = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".dart", ".kt", ".html", ".sh"}
SKIP_DIRS = {".venv", "venv", "node_modules", "target", "build", "dist", "__pycache__", ".git",
             "site-packages", "lora_datasets", "obsidian_vault", ".dart_tool", "Pods", "vendor"}
SKIP_PATTERNS = {"*venv*", "*virtualenv*", "*site-packages*"}


def is_skipped_dir(d: str) -> bool:
    if d in SKIP_DIRS or d.startswith("."):
        return True
    if any(fnmatch.fnmatch(d, pat) for pat in SKIP_PATTERNS):
        return True
    return False
TEST_HINT = re.compile(r"(^|/)(tests?|fixtures?|__tests__|testdata)(/|$)|(_test\.(py|go)|\.test\.(js|ts))$")
SUPPRESS = re.compile(r"spec-ok:|zero-mock-ok:")

# Context-scoped Qwen telemetry status pattern
QWEN_TELEMETRY = re.compile(
    r"""(?:["'](?:active_model|running_model|model_used|local_archetype|id)["']\s*:\s*["']?[^"']*(?:Qwen\s*3\.8\s*Max|qwen_38_max)|(?:LOCAL_AI_MODEL|model_used)\s*=\s*["']?[^"']*(?:Qwen\s*3\.8\s*Max|qwen_38_max)|<[^>]*>[^<]*(?:Qwen\s*3\.8\s*Max)|print\(.*(?:Local AI|Duo|model).*Qwen\s*3\.8\s*Max)""",
    re.I
)

# BLOCK: claims proven false for this mesh by live probe (see rules/00_canonical_hardware_matrix.md).
KNOWN_FALSE = [
    (r"(?:(?:rtt|latency|ping)\s*[:=]\s*(?:0\.27|0\.544|0\.56|0\.28)\b|(?:0\.27|0\.544|0\.56|0\.28)\s*ms\b)", "fabricated Thunderbolt RTT constant (measured ~0.45 ms avg)"),
    (r"\b10\s*Gbps\s*Thunderbolt|Thunderbolt[^\n]{0,20}\b10\s*Gbps", "false L1<->L2 TB speed (probed 20 Gb/s)"),
    (r"Tankya|Lintes", "cable e-marker vendor literal (must come from SOP' VDO)"),
    (r"__QWEN_SPECIAL__", "model label not matching any running GGUF (8082 serves Hermes-3 8B)"),
    (r"\b1734(\.0)?\b.{0,20}ELO|ELO.{0,20}\b1734\b", "unattributed ELO claim"),
    (r"148\.1\s*GB|82\.8\s*GB|108\.0\s*GB|85\.0\s*GB", "static pooled-RAM figure"),
    (r"OpenWrt\s*2[34]\.\d+", "wrong router firmware (probed OpenWrt 21.02-SNAPSHOT)"),
    (r"100\.90\.9\.130", "fabricated WAN IP"),
    (r"GL-MT3600BE", "wrong router model (probed GL-BE14000)"),
    (r"prima\.cpp[^\n]{0,40}(ring|connected)[^\n]{0,20}(active|live|online)", "prima.cpp ring claim (no prima.cpp process)"),
    (r"\b10000F\b", "fabricated 10Gbps WAN speed (router eth2 is 2.5 Gbps)"),
    (r"@144\s*Hz\b|\b144\s*Hz\b(?=.*(?:margin|display|monitor|screen|refresh))", "fabricated 144Hz display refresh rate (probed 60 Hz)"),
]

# Hardware field names whose fallbacks must be None/'--'.
HW = r"(speed|gbps|mbps|rtt|latency|watt|power|volt|vendor|chip|arch|ram|memory|tops|rssi|signal|resolution|refresh|hz|link|bandwidth|online|status|model|firmware|temp)"
FALLBACK = [
    (rf"\b\w*{HW}\w*\s*(\|\||\?\?)\s*['\"]?[\w.]*\d[\w. ]*", "JS fallback substitutes a plausible hardware value"),
    (rf"\.get\(\s*['\"]\w*{HW}\w*['\"]\s*,\s*(True|[\d.]+|['\"][^'\"]*(\d|UP|ONLINE|CONNECTED)[^'\"]*['\"])\s*\)", "Python .get default fabricates a hardware value"),
    (rf"['\"]\w*{HW}\w*['\"]\s*:\s*['\"]?(?:\d+(?:\.\d+)?\s*(?:Gbps|Gb/s|Mbps|ms|W|GB|TOPS|dBm|Hz)|10000F|ONLINE|CONNECTED|VERIFIED|ACTIVE|UP)['\"]?", "hardcoded hardware reading in payload"),
]
SYNTHETIC = [
    (r"\brandom\.(uniform|randint|gauss|random|choice)\(|Math\.random\(|np\.random\.", "synthetic generator in runtime path"),
    (r"(simulat|mock|fake|demo)[A-Za-z_]*\s*[=(]", "simulation/mock symbol in runtime path"),
]
OVERCLAIM = [
    (r"['\"][^'\"]*\b(AUTHENTIC|TRUTH_VERIFIED|ZERO[- ]MOCK|LIVE|VERIFIED)\b[^'\"]*['\"]", "overclaiming label (must be gated on a real check)"),
]


def is_vid_lookup(line: str, stripped: str) -> bool:
    """Ignore static USB-IF vendor registry dictionaries."""
    if re.match(r'^(?:0x[0-9a-fA-F]+|\d+)\s*:\s*["\']', stripped):
        return True
    if re.match(r'^(?:case\s+)?(?:0x[0-9a-fA-F]+|\d+)\s*(?:=>|:)', stripped):
        return True
    return False


def is_prompt_or_eval_text(line: str, stripped: str) -> bool:
    """Ignore prompt templates and benchmark dataset instruction entries."""
    if re.match(r'^["\'](?:prompt|input|output|instruction|governing_capacity_boundary)["\']\s*:', stripped):
        return True
    if stripped.startswith(('"You are', "'You are", '"From a local', "'From a local")):
        return True
    return False


def iter_files(root: Path):
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if not is_skipped_dir(d)]
        for f in fn:
            p = Path(dp) / f
            if p.suffix in EXTS:
                yield p


def fingerprint(path: str, text: str) -> str:
    return hashlib.sha1(f"{path}::{text.strip()}".encode()).hexdigest()[:16]


def scan_file(path: Path):
    findings = []
    rel = str(path)
    if path.name in ("fake_data_scanner.py", "benchmark_dataset_50.json"):
        return findings
    if any(is_skipped_dir(part) for part in path.parts[:-1]):
        return findings
    is_test = bool(TEST_HINT.search(rel))
    try:
        lines = path.read_text(errors="ignore").splitlines()
    except Exception:
        return findings

    in_doc = False
    for i, line in enumerate(lines, 1):
        if len(line) > 600 or SUPPRESS.search(line):
            continue
        stripped = line.strip()

        # Track multiline docstrings
        cnt = line.count('"""')
        was_in_doc = in_doc
        if not in_doc and cnt % 2 == 1:
            in_doc = True
        elif in_doc and cnt % 2 == 1:
            in_doc = False

        is_doc_line = was_in_doc or (not was_in_doc and stripped.startswith('"""'))
        if is_doc_line:
            continue

        # Skip comment lines
        if stripped.startswith(("#", "//", "/*", "*", "<!--", ";", "--")):
            continue

        # Separate code from inline comments
        code_part = line
        if "#" in line:
            parts = line.split("#", 1)
            if (parts[0].count('"') % 2 == 0) and (parts[0].count("'") % 2 == 0):
                code_part = parts[0]
        elif "//" in line:
            parts = line.split("//", 1)
            if (parts[0].count('"') % 2 == 0) and (parts[0].count("'") % 2 == 0):
                code_part = parts[0]

        # Scan for BLOCK violations
        for pat, why in KNOWN_FALSE:
            if pat == "__QWEN_SPECIAL__":
                if QWEN_TELEMETRY.search(line):
                    findings.append({
                        "file": rel, "line": i, "severity": "BLOCK" if not is_test else "TEST",
                        "rule": why, "snippet": stripped[:200],
                        "fingerprint": fingerprint(rel, line)
                    })
                continue

            if pat == "Tankya|Lintes" and is_vid_lookup(line, stripped):
                continue

            if pat in ("148\\.1\\s*GB|82\\.8\\s*GB|108\\.0\\s*GB|85\\.0\\s*GB",
                       r"\b1734(\.0)?\b.{0,20}ELO|ELO.{0,20}\b1734\b",
                       "GL-MT3600BE",
                       r"\b10\s*Gbps\s*Thunderbolt|Thunderbolt[^\n]{0,20}\b10\s*Gbps",
                       r"(?:(?:rtt|latency|ping)\s*[:=]\s*(?:0\.27|0\.544|0\.56|0\.28)\b|(?:0\.27|0\.544|0\.56|0\.28)\s*ms\b)",
                       r"\b10000F\b",
                       r"\b144\s*Hz\b"):
                if is_prompt_or_eval_text(line, stripped):
                    continue

            # Match against code_part so comments don't trigger false positives
            if re.search(pat, code_part, re.I):
                findings.append({
                    "file": rel, "line": i, "severity": "BLOCK" if not is_test else "TEST",
                    "rule": why, "snippet": stripped[:200],
                    "fingerprint": fingerprint(rel, line)
                })
                break

        # Scan for WARN and INFO if not test file
        if not is_test:
            for sev, pats in [("WARN", FALLBACK), ("WARN", SYNTHETIC), ("INFO", OVERCLAIM)]:
                matched = False
                for pat, why in pats:
                    if re.search(pat, code_part, re.I if sev != "INFO" else 0):
                        findings.append({
                            "file": rel, "line": i, "severity": sev,
                            "rule": why, "snippet": stripped[:200],
                            "fingerprint": fingerprint(rel, line)
                        })
                        matched = True
                        break
                if matched:
                    break

    return findings


def staged_files():
    out = subprocess.run(["git", "-C", str(REPO), "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                         capture_output=True, text=True).stdout.split()
    return [REPO / f for f in out if Path(f).suffix in EXTS]


def check(path: str, line: int) -> bool:
    return any(f["line"] == line and f["severity"] in ("BLOCK", "WARN") for f in scan_file(Path(path)))


def main(argv):
    exit_on_block = False
    if "--exit-on-block" in argv:
        exit_on_block = True
        argv = [a for a in argv if a != "--exit-on-block"]

    if argv[:1] == ["--check"] and len(argv) == 3:
        sys.exit(0 if check(argv[1], int(argv[2])) else 1)
    if argv[:1] == ["--staged"]:
        files = staged_files()
        exit_on_block = True
    elif argv[:1] == ["--target-apps"]:
        target_dirs = [
            REPO / "01_apps/network_cable_analyzer",
            REPO / "01_apps/screen_lens/screen_life_companion",
            REPO / "01_apps/port_4000_hub",
            REPO / "01_apps/zone_2",
            REPO / "02_ai_models_and_inference/decentralized_prima_daemon.py",
            REPO / "03_biometrics_and_telemetry",
        ]
        files = []
        for d in target_dirs:
            if d.is_dir():
                files.extend(iter_files(d))
            elif d.is_file():
                files.append(d)
    elif argv[:1] == ["--all"]:
        files = list(iter_files(Path(argv[1]) if len(argv) > 1 else REPO))
    else:
        files = []
        for a in argv:
            p = Path(a)
            if p.is_dir():
                files.extend(iter_files(p))
            elif p.is_file():
                files.append(p)

    findings = [f for p in files for f in scan_file(p)]
    summary = {s: sum(1 for f in findings if f["severity"] == s) for s in ("BLOCK", "WARN", "INFO", "TEST")}
    json.dump({"files_scanned": len(files), "summary": summary, "findings": findings}, sys.stdout, indent=1)
    print()
    if (exit_on_block or argv[:1] == ["--staged"]) and summary["BLOCK"]:
        for f in findings:
            if f["severity"] == "BLOCK":
                print(f"BLOCK {f['file']}:{f['line']}  {f['rule']}\n    {f['snippet']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])

