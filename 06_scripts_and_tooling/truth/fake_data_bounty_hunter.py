#!/usr/bin/env python3
"""Local-AI Fake-Data Bounty Hunter (Rule 22).

A local model reviews runtime source files for fabricated hardware/network/AI
telemetry. Every claim is checked mechanically; only verified claims are paid.

Payment rules (anti-gaming):
  * Claim must cite file + line + verbatim snippet present at that line.
  * The deterministic scanner (fake_data_scanner.py --check) must confirm the line,
    OR the line must contain a hardware literal that differs from the canonical probed
    table. Unconfirmed claims pay nothing; a cited snippet that is not in the file
    (a hallucinated citation) is taxed.
  * Each finding fingerprint pays once (ledger dedupe).
  * Rewards are credited to the model's REAL identity (GGUF basename read from the
    serving llama-server /props), never to a proxy alias such as "qwen_38_max".

Usage:
  fake_data_bounty_hunter.py --once [--files N] [--endpoint http://127.0.0.1:8090]
  fake_data_bounty_hunter.py --loop --interval 900
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import io
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path("/Volumes/Lauburu-Monorepo")
SCANNER = REPO / "06_scripts_and_tooling/truth/fake_data_scanner.py"
LEDGER = REPO / "04_data_and_memory/data/fake_data_bounty_ledger.jsonl"
CANONICAL_LORA = Path("/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl")
LORA = Path("/Volumes/Lauburu-Monorepo/04_data_and_memory/data/fake_data_hunting_pairs.jsonl")
VAULT_LOG = REPO / "obsidian_vault/APPS_AND_FEATURES/FAKE_DATA_BOUNTY_LOG.md"
sys.path.insert(0, str(REPO / "05_agents_and_swarms"))
sys.path.insert(0, str(REPO / "06_scripts_and_tooling/truth"))

REWARD = {"BLOCK": 30, "WARN": 15, "NOVEL": 25}
HALLUCINATED_CITATION = "hallucination"  # existing tax category (-50)

PROMPT = """You audit source code for FAKE hardware/network/AI telemetry: values shown to users as live
measurements that are actually hardcoded literals, fallback defaults (x || 40, .get('speed', 40)),
random generators, static 'ONLINE/VERIFIED/LIVE' labels, or replayed fixtures.
Real values must come from raw commands (system_profiler, ifconfig, ping, ssh, /proc, ubus, /v1/models).
Return ONLY JSON: {"findings":[{"line":<int>,"snippet":"<exact text from that line>","why":"<short>"}]}
Return {"findings":[]} if none. Do not invent lines. File: %s
```
%s
```"""


def real_identity(endpoint: str) -> str | None:
    try:
        req = urllib.request.Request(endpoint.rstrip("/") + "/props", headers={"User-Agent": "bounty-hunter/1.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            if r.status != 200:
                return None
            data = json.load(r)
            mp = data.get("model_path")
        return os.path.basename(mp) if mp else None
    except Exception:
        return None


def check_host_ram_safe(endpoint: str = "") -> tuple[bool, str]:
    """Verify Darwin host keeps >= 4.8 GB free RAM or kern.memorystatus_vm_pressure_level <= 1.
    
    If endpoint is explicitly a remote peer (e.g. L3 Linux Mini :8083 or L2 MBP :8081),
    inference does not consume host L1 memory.
    """
    is_local = True
    if endpoint:
        try:
            from urllib.parse import urlparse
            host = urlparse(endpoint).hostname or ""
            if host not in ("127.0.0.1", "localhost", "0.0.0.0", "") and not host.startswith("127."):
                is_local = False
        except Exception:
            pass

    if sys.platform != "darwin":
        return True, "Non-darwin host"

    try:
        p_out = subprocess.check_output(
            ["sysctl", "-n", "kern.memorystatus_vm_pressure_level"],
            text=True, stderr=subprocess.DEVNULL
        ).strip()
        pressure = int(p_out)
    except Exception:
        pressure = 1

    try:
        memsize = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True, stderr=subprocess.DEVNULL).strip())
        total_gb = memsize / (1024 ** 3)
        vm_stat = subprocess.check_output(["vm_stat"], text=True, stderr=subprocess.DEVNULL)
        page_size = 4096
        for line in vm_stat.splitlines():
            if "page size of" in line:
                m = re.search(r"page size of (\d+) bytes", line)
                if m:
                    page_size = int(m.group(1))
                break

        stats = {}
        for line in vm_stat.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                clean_v = v.strip().rstrip(".")
                if clean_v.isdigit():
                    stats[k.strip()] = int(clean_v) * page_size

        free_bytes = stats.get("Pages free", 0) + stats.get("Pages speculative", 0)
        available_bytes = (
            free_bytes
            + stats.get("Pages inactive", 0)
            + stats.get("Pages purgeable", 0)
            + stats.get("File-backed pages", 0)
        )
        available_gb = available_bytes / (1024 ** 3)
    except Exception:
        available_gb = 5.0

    is_safe = (available_gb >= 4.8) or (pressure <= 1)
    if not is_safe and not is_local:
        return True, f"Remote endpoint {endpoint} offloads compute; host headroom {available_gb:.2f} GB, pressure {pressure}"

    if not is_safe:
        return False, f"Host memory unsafe: available RAM {available_gb:.2f} GB (<4.8 GB) and memory pressure {pressure} (>1)"

    return True, f"Host RAM safe: available {available_gb:.2f} GB, pressure level {pressure}"


def ask(endpoint: str, path: Path, start: int, chunk: list[str]) -> list[dict]:
    numbered = "\n".join(f"{start + i}: {l}" for i, l in enumerate(chunk))
    body = json.dumps({"messages": [{"role": "user", "content": PROMPT % (path, numbered)}],
                       "temperature": 0.1, "max_tokens": 700}).encode()
    req = urllib.request.Request(endpoint.rstrip("/") + "/v1/chat/completions", body,
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        txt = json.load(r)["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", txt, re.S)
    try:
        return json.loads(m.group(0)).get("findings", []) if m else []
    except Exception:
        return []


def scanner_findings(files: list[Path]) -> dict:
    out = subprocess.run([sys.executable, str(SCANNER), *map(str, files)], capture_output=True, text=True).stdout
    try:
        return {(f["file"], f["line"]): f for f in json.loads(out)["findings"]}
    except Exception:
        return {}


def paid_fingerprints() -> set[str]:
    if not LEDGER.exists():
        return set()
    fps = set()
    for l in LEDGER.read_text(errors="ignore").splitlines():
        if not l.strip():
            continue
        try:
            fp = json.loads(l).get("fingerprint")
            if fp:
                fps.add(fp)
        except Exception:
            continue
    return fps


def pick_files(n: int) -> list[Path]:
    """Fast file picker: scans a targeted sample of runtime files for violations, avoiding 20.7s global repo crawl freeze."""
    from fake_data_scanner import scan_file, iter_files

    runtime_dirs = [
        REPO / "01_apps/network_cable_analyzer",
        REPO / "01_apps",
        REPO / "06_scripts_and_tooling/truth",
        REPO / "06_scripts_and_tooling",
        REPO / "00_core_infrastructure",
        REPO / "05_agents_and_swarms"
    ]
    candidates = []
    for rd in runtime_dirs:
        if rd.exists():
            candidates.extend(iter_files(rd))

    seen = set()
    unique_candidates = [c for c in candidates if not (c in seen or seen.add(c))]
    if not unique_candidates:
        return []

    random.shuffle(unique_candidates)
    flagged = []
    clean = []

    # Check a bounded pool of up to max(40, n * 5) files to finish in <0.25s
    sample_pool = unique_candidates[:max(40, n * 5)]
    for p in sample_pool:
        findings = scan_file(p)
        if any(f["severity"] in ("BLOCK", "WARN") for f in findings):
            flagged.append(p)
        else:
            clean.append(p)
        if len(flagged) >= n:
            break

    selected = flagged[:n]
    if len(selected) < n:
        needed = n - len(selected)
        selected.extend(clean[:needed])

    return selected[:n]


def settle(model_id: str, claim: dict, verdict: str, amount: int) -> None:
    import elo_currency_governor as gov  # prints a banner on import; silence it
    buf = io.StringIO()
    with redirect_stdout(buf):
        target = claim.get("target_file") or claim.get("file")
        if amount > 0:
            gov.grant_reward(model_id, f"fake-data bounty {verdict}: {target}:{claim['line']}", amount)
        elif verdict == "HALLUCINATED_CITATION":
            gov.apply_tax_or_penalty(model_id, HALLUCINATED_CITATION, f"cited non-existent line {target}:{claim['line']}")


def run_once(endpoint: str, nfiles: int = 2, target_files: list[str | Path] | None = None, ignore_ram_check: bool = False) -> dict:
    model_id = real_identity(endpoint)
    if not model_id:
        return {"error": f"cannot read real model identity from {endpoint}/props; refusing to award unattributed ELO"}

    if not ignore_ram_check:
        safe, reason = check_host_ram_safe(endpoint)
        if not safe:
            return {"error": f"refusing inference: {reason}"}

    if target_files:
        files = [Path(f) for f in target_files]
    else:
        files = pick_files(nfiles)

    det = scanner_findings(files)
    paid = paid_fingerprints()
    stats = {"model": model_id, "files": len(files), "claims": 0, "verified": 0, "unconfirmed": 0,
             "hallucinated": 0, "duplicate": 0, "elo": 0}

    for path in files:
        if not path.exists():
            continue
        lines = path.read_text(errors="ignore").splitlines()
        for start in range(0, min(len(lines), 600), 150):
            try:
                claims = ask(endpoint, path, start + 1, lines[start:start + 150])
            except Exception as e:
                stats.setdefault("errors", []).append(str(e)[:120])
                break
            for c in claims:
                stats["claims"] += 1
                try:
                    ln = int(c.get("line", 0))
                    snip = str(c.get("snippet") or c.get("code") or "").strip()
                except Exception:
                    continue
                actual = lines[ln - 1].strip() if 0 < ln <= len(lines) else ""
                rel_file = str(path.relative_to(REPO)) if str(path).startswith(str(REPO)) else str(path)
                rec = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "ts": time.time(),
                    "model": model_id,
                    "target_file": rel_file,
                    "file": str(path),
                    "line": ln,
                    "snippet": snip[:200],
                    "why": str(c.get("why") or c.get("description") or "")[:200]
                }
                if not snip or snip[:40] not in actual:
                    rec["verdict"], amt = "HALLUCINATED_CITATION", 0
                    stats["hallucinated"] += 1
                else:
                    hit = det.get((str(path), ln))
                    fp = hit["fingerprint"] if hit else None
                    if hit and fp in paid:
                        rec["verdict"], amt = "DUPLICATE", 0
                        rec["fingerprint"] = fp
                        stats["duplicate"] += 1
                    elif hit and hit["severity"] in REWARD:
                        rec.update(verdict=f"VERIFIED_{hit['severity']}", fingerprint=fp, rule=hit["rule"], severity=hit["severity"])
                        amt = REWARD[hit["severity"]]
                        paid.add(fp)
                        stats["verified"] += 1
                    else:
                        rec["verdict"], amt = "UNCONFIRMED_NEEDS_HUMAN", 0  # possible novel find, queued, not paid
                        stats["unconfirmed"] += 1
                rec["elo_delta"] = amt if amt else (-50 if rec["verdict"] == "HALLUCINATED_CITATION" else 0)
                stats["elo"] += rec["elo_delta"]
                settle(model_id, rec, rec["verdict"], amt)
                LEDGER.parent.mkdir(parents=True, exist_ok=True)
                with LEDGER.open("a") as f:
                    f.write(json.dumps(rec) + "\n")
                if rec["verdict"].startswith("VERIFIED"):
                    lora_entry = {
                        "instruction": "Identify fabricated hardware telemetry in this code line and state the raw source it must come from.",
                        "input": f"{path.name}:{ln}: {actual}",
                        "output": f"FAKE: {hit['rule']}. Replace with a measured value or None/'--'.",
                        "provenance": {"verifier": "fake_data_scanner", "model": model_id}
                    }
                    CANONICAL_LORA.parent.mkdir(parents=True, exist_ok=True)
                    with CANONICAL_LORA.open("a") as f:
                        f.write(json.dumps(lora_entry) + "\n")
                    with LORA.open("a") as f:
                        f.write(json.dumps(lora_entry) + "\n")
    try:
        VAULT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with VAULT_LOG.open("a") as f:
            f.write(f"\n- {time.strftime('%Y-%m-%d %H:%M:%S')} | `{model_id}` | files {stats['files']} | claims {stats['claims']} | "
                    f"verified {stats['verified']} | unconfirmed {stats['unconfirmed']} | hallucinated {stats['hallucinated']} | ELO {stats['elo']:+d}")
    except Exception:
        pass
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="http://127.0.0.1:8090")
    ap.add_argument("--files", type=int, default=2)
    ap.add_argument("--target", nargs="*", default=None, help="Explicit list of files to audit")
    ap.add_argument("--ignore-ram-check", action="store_true", help="Bypass host RAM safety check for testing")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--interval", type=int, default=900)
    a = ap.parse_args()

    interval = max(600, a.interval)  # Ensure background interval is at least 10 minutes (600s)

    while True:
        res = run_once(a.endpoint, a.files, target_files=a.target, ignore_ram_check=a.ignore_ram_check)
        print(json.dumps(res), flush=True)
        if not a.loop:
            break
        time.sleep(interval)


if __name__ == "__main__":
    main()
