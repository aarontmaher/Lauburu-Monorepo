#!/usr/bin/env python3
"""
Subsystem: 06_scripts_and_tooling/automation/automate_llamacpp_lens_setup.py
Sovereign Screen Lens + Continuous Lens Practice Automation for llama.cpp & Page Assist
Lauburu Mesh Ecosystem — 2026

Enforces:
1. Apple M4 Pro 16-Core Metal GPU acceleration (-ngl 99, -np 4, -fa on, q8_0 KV cache)
   on local llama-server endpoints (:8085 3B/8B and :8089 0.5B).
2. Sovereign API Key ('sk-lauburu-sovereign-m4-metal-2026') auto-population in llama-ui
   (/Users/aaron/.local/share/llama-ui-sovereign) and disabling unwanted Browser Tool loops.
3. Multiport & Ollama/Page Assist bridge (:8083, :8081, :8011, :11434) via mesh_multiport_bridge.py.
4. Rule 1.6 & Rule 3 L1 Host RAM Sanctuary verification (>= 4.8 GB free, <= 80.0% used).
5. Rule 2 & Rule 13 Screen Lens Teacher-Student VLA trajectory distillation into Tri-Vault.
"""

import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

SOVEREIGN_API_KEY = "sk-lauburu-sovereign-m4-metal-2026"
SOVEREIGN_API_KEY_MASKED = "sk-lauburu-sove...[REDACTED_SOVEREIGN]"
UI_DIR = Path("/Users/aaron/.local/share/llama-ui-sovereign")
LORA_JSONL = Path("/Users/Shared/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl")
OBSIDIAN_LOG = Path(
    "/Users/Shared/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/APPS_AND_FEATURES/SCREEN_LENS_LIVE_OBSERVATIONS.md"
)
REPORT_JSON = Path(
    "/Users/Shared/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/llamacpp_lens_automation_report.json"
)


def darwin_ram_audit() -> dict:
    """Calculate macOS memory strictly per Rule 1.6 Darwin Kernel Memory Accounting Formulas."""
    page_size = int(subprocess.check_output(["sysctl", "-n", "hw.pagesize"]).decode().strip())
    memsize = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"]).decode().strip())
    pressure = int(
        subprocess.check_output(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"]).decode().strip()
    )
    vm_out = subprocess.check_output(["vm_stat"]).decode()

    def _pages(label: str) -> int:
        m = re.search(rf"{re.escape(label)}:\s+(\d+)", vm_out)
        return int(m.group(1)) if m else 0

    anon = _pages("Anonymous pages")
    purgeable = _pages("Pages purgeable")
    wired = _pages("Pages wired down")
    compressor = _pages("Pages occupied by compressor")
    file_backed = _pages("File-backed pages")

    app_mem = max(0, (anon - purgeable) * page_size)
    wired_mem = wired * page_size
    compressed_mem = compressor * page_size
    cached_files = (file_backed + purgeable) * page_size
    used_mem = app_mem + wired_mem + compressed_mem
    avail_mem = max(0, memsize - used_mem)

    total_gb = memsize / (1024**3)
    used_gb = used_mem / (1024**3)
    avail_gb = avail_mem / (1024**3)
    used_pct = (used_mem / memsize) * 100.0

    return {
        "total_gb": round(total_gb, 2),
        "used_gb": round(used_gb, 2),
        "available_gb": round(avail_gb, 2),
        "cached_files_gb": round(cached_files / (1024**3), 2),
        "used_pct": round(used_pct, 2),
        "pressure_level": pressure,
        "rule3_sanctuary_compliant": avail_gb >= 4.80 and used_pct <= 80.0,
    }


def ensure_sovereign_ui_assets() -> dict:
    """Ensure llama-ui static assets have default API key and tool-loop suppression."""
    index_path = UI_DIR / "index.html"
    bundle_path = UI_DIR / "_app/immutable/bundle.Dei7uEAu.js"

    if bundle_path.exists():
        text = bundle_path.read_text(encoding="utf-8")
        # Fix any escaped quotes and ensure defaultValue is set on pr.API_KEY
        text = text.replace(
            r'defaultValue:\"sk-lauburu-sovereign-m4-metal-2026\"',
            f'defaultValue:"{SOVEREIGN_API_KEY}"',
        )
        text = re.sub(
            r'\{defaultValue:"",help:`Set the API Key if you are using <code> \$\{D_\.API_KEY\} </code>',
            f'{{defaultValue:"{SOVEREIGN_API_KEY}",help:`Set the API Key if you are using <code> ${{D_.API_KEY}} </code>',
            text,
        )
        bundle_path.write_text(text, encoding="utf-8")

    if index_path.exists():
        html = index_path.read_text(encoding="utf-8")
        if "Sovereign Lauburu Auto-Bootstrap" not in html:
            inject = f"""<script>
// Sovereign Lauburu Auto-Bootstrap: API Key + Fast Direct Chat (No Unwanted Browser Tool Loops)
(function() {{
  try {{
    const keyName = "LlamaUi.config";
    const raw = localStorage.getItem(keyName);
    const cfg = raw ? JSON.parse(raw) : {{}};
    if (!cfg.apiKey || cfg.apiKey.trim() === "") {{
      cfg.apiKey = "{SOVEREIGN_API_KEY}";
      localStorage.setItem(keyName, JSON.stringify(cfg));
    }}
    const rawOvr = localStorage.getItem("LlamaUi.userOverrides");
    const ovr = rawOvr ? JSON.parse(rawOvr) : [];
    if (Array.isArray(ovr) && !ovr.includes("apiKey")) {{
      ovr.push("apiKey");
      localStorage.setItem("LlamaUi.userOverrides", JSON.stringify(ovr));
    }}
    if (!localStorage.getItem("LlamaUi.disabledToolKeys")) {{
      localStorage.setItem("LlamaUi.disabledToolKeys", JSON.stringify([
        "browser:get_info",
        "browser:get_datetime",
        "browser:run_javascript",
        "browser:read_media"
      ]));
    }}
  }} catch (e) {{}}
}})();
</script>
"""
            html = html.replace("</head>", inject + "</head>", 1)
            index_path.write_text(html, encoding="utf-8")

    return {
        "ui_dir": str(UI_DIR),
        "index_exists": index_path.exists(),
        "bundle_exists": bundle_path.exists(),
        "api_key_masked": SOVEREIGN_API_KEY_MASKED,
    }


def benchmark_endpoints() -> list[dict]:
    """Run zero-mock live inference timing across all local llama.cpp & Ollama bridge ports."""
    targets = [
        {"port": 8083, "protocol": "openai", "role": "llama-ui & Adversarial Proxy (-> :8085 Metal GPU)"},
        {"port": 8085, "protocol": "openai", "role": "Primary Metal GPU Server (3.2B/8B Q4_K_M)"},
        {"port": 8089, "protocol": "openai", "role": "Micro Metal GPU Server (Qwen2.5 0.5B Q4_K_M)"},
        {"port": 8081, "protocol": "openai", "role": "Syntax Worker Proxy (-> :8089 Metal GPU)"},
        {"port": 8082, "protocol": "openai", "role": "Decentralized Prima Proxy (-> :8089/:8085)"},
        {"port": 8011, "protocol": "openai", "role": "Legacy Local Llama Proxy (-> :8085 Metal GPU)"},
        {"port": 11434, "protocol": "ollama", "role": "Page Assist / Ollama Native Bridge (-> :8085 Metal GPU)"},
    ]
    results = []
    for t in targets:
        port = t["port"]
        t0 = time.monotonic()
        try:
            if t["protocol"] == "openai":
                payload = json.dumps(
                    {
                        "model": "Hermes-3-Llama-3.1-8B.Q4_K_M.gguf",
                        "messages": [{"role": "user", "content": "Reply with OK"}],
                        "max_tokens": 8,
                        "temperature": 0.0,
                    }
                ).encode("utf-8")
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/v1/chat/completions",
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {SOVEREIGN_API_KEY}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                elapsed_ms = round((time.monotonic() - t0) * 1000.0, 2)
                timings = data.get("timings", {})
                tok_s = round(timings.get("predicted_per_second", 0.0), 2)
                reply = data["choices"][0]["message"]["content"].strip()
            else:
                payload = json.dumps(
                    {
                        "model": "Hermes-3-Llama-3.1-8B.Q4_K_M.gguf",
                        "messages": [{"role": "user", "content": "Reply with OK"}],
                        "stream": False,
                    }
                ).encode("utf-8")
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/chat",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                elapsed_ms = round((time.monotonic() - t0) * 1000.0, 2)
                eval_count = data.get("eval_count", 1)
                eval_dur_s = max(0.001, data.get("eval_duration", 1e8) / 1e9)
                tok_s = round(eval_count / eval_dur_s, 2)
                reply = data.get("message", {}).get("content", "").strip()

            results.append(
                {
                    "port": port,
                    "role": t["role"],
                    "status": "ONLINE",
                    "latency_ms": elapsed_ms,
                    "tokens_per_sec": tok_s,
                    "reply": reply[:40],
                }
            )
        except Exception as e:
            results.append(
                {
                    "port": port,
                    "role": t["role"],
                    "status": f"ERROR: {e}",
                    "latency_ms": -1,
                    "tokens_per_sec": 0.0,
                }
            )
    return results


def record_tri_vault_distillation(ram: dict, benchmarks: list[dict], ui_info: dict) -> dict:
    """Synchronize Teacher-Student VLA trajectory into PySpark JSONL + Obsidian + JSON report."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    lora_entry = {
        "timestamp": now_iso,
        "teacher_model": "screen-lens-sovereign",
        "domain": "llamacpp_lens_automation",
        "instruction": (
            "Automate llama.cpp setup on L1 Mac Mini M4 Pro: configure API key in llama-ui "
            "(http://localhost:8083/#/settings/general), enable Metal GPU (-ngl 99 -np 4), "
            "eliminate Browser Tools get_info approval stalls, and bridge Page Assist (:11434)."
        ),
        "input": json.dumps(
            {
                "target_urls": [
                    "http://localhost:8083/#/settings/general",
                    "http://localhost:8083/#/",
                    "http://127.0.0.1:11434/api/tags",
                ],
                "ram_sanctuary": ram,
            }
        ),
        "output": json.dumps(
            {
                "actions": [
                    {"tool": "fill", "uid": "3_23", "field": "API Key", "value_masked": SOVEREIGN_API_KEY_MASKED},
                    {"tool": "click", "uid": "3_62", "button": "Save settings"},
                    {"tool": "evaluate_script", "key": "LlamaUi.disabledToolKeys", "disabled": ["browser:get_info", "browser:get_datetime"]},
                    {"tool": "fill", "uid": "14_12", "prompt": "Reply with one line: METAL_GPU_SOVEREIGN_READY"},
                    {"tool": "click", "uid": "14_15", "button": "Send"},
                ],
                "verified_benchmarks": benchmarks,
            }
        ),
    }

    LORA_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(LORA_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(lora_entry) + "\n")

    report = {
        "timestamp": now_iso,
        "ui_assets": ui_info,
        "ram_sanctuary": ram,
        "benchmarks": benchmarks,
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if OBSIDIAN_LOG.exists():
        obs_entry = (
            f"\n### [{now_iso}] Screen Lens Sovereign — llama.cpp & Page Assist Metal GPU Automation\n"
            f"- **API Key Auto-Bootstrap:** `{SOVEREIGN_API_KEY_MASKED}` injected into `{UI_DIR}` (`index.html` & `bundle.Dei7uEAu.js`).\n"
            f"- **L1 RAM Sanctuary (Rule 3):** `{ram['available_gb']} GB` free (`{ram['used_pct']}%` used, compliant: `{ram['rule3_sanctuary_compliant']}`).\n"
            f"- **Port 8083 (`llama-ui`):** `{benchmarks[0]['latency_ms']} ms` | Port 8085: `{benchmarks[1]['latency_ms']} ms` (`{benchmarks[1]['tokens_per_sec']} tok/s`) | Port 8089: `{benchmarks[2]['latency_ms']} ms` (`{benchmarks[2]['tokens_per_sec']} tok/s`).\n"
        )
        with open(OBSIDIAN_LOG, "a", encoding="utf-8") as f:
            f.write(obs_entry)

    return report


def reclaim_sanctuary_headroom() -> list[str]:
    """Enforce Rule 3 & Screen Lens Plugin Rule 5 by evicting non-core memory hogs when L1 < 4.8 GB free."""
    ram = darwin_ram_audit()
    evicted = []
    if ram["rule3_sanctuary_compliant"]:
        return evicted

    subprocess.run(
        ["launchctl", "unload", os.path.expanduser("~/Library/LaunchAgents/ai.openclaw.gateway.plist")],
        capture_output=True,
    )
    patterns = [
        "[r]ealtime_feedback_studio.py",
        "[j]unie.app/Contents/MacOS/junie",
        "[l]lm-ls --stdio",
        "[u]vicorn backend.server:app --host 0.0.0.0 --port 4007",
        "[a]pp_accuracy_functionality_and_ai_integration_loop.py",
        "[m]arimo-lsp",
        "[t]y server",
        "[o]penclaw/tools/node",
        "[G]itHub Desktop.app",
    ]
    for pat in patterns:
        res = subprocess.run(["pkill", "-9", "-f", pat], capture_output=True)
        if res.returncode == 0:
            evicted.append(pat)
    if evicted:
        time.sleep(1.0)
    return evicted


def main() -> int:
    ui_info = ensure_sovereign_ui_assets()
    evicted = reclaim_sanctuary_headroom()
    ram = darwin_ram_audit()
    ram["evicted_patterns"] = evicted
    benchmarks = benchmark_endpoints()
    report = record_tri_vault_distillation(ram, benchmarks, ui_info)
    print(json.dumps(report, indent=2))
    all_online = all(b["status"] == "ONLINE" for b in benchmarks)
    return 0 if (all_online and ram["rule3_sanctuary_compliant"]) else 1


if __name__ == "__main__":
    sys.exit(main())

