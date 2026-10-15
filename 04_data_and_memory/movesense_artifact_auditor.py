#!/Users/aaron/ai_training_venv/bin/python3
"""
Movesense Artifact Auditor (read-only)
======================================
Answers one question on a schedule: "is the pipeline extracting non-physiological data?"

Layers
  1. Deterministic, beat-level checks (the only layer that can *prove* a defect).
     RR lists in the source are a sliding 5-beat window that is re-logged many times, so records are
     first merged back into a unique beat stream; rates are reported per unique beat, not per record.
  2. Frontier review (two model families: Gemini and NVIDIA NIM) of sampled real windows.
  3. Local medical-model review (MedGemma via llama-cli, or MEDICAL_LLM_URL for an OpenAI-compatible
     server on another node). Gated on free RAM so it never breaches the host sanctuary.

LLM reviewers judge plausibility only; they cannot verify ground truth. Their verdicts are advisory and are
reported next to the deterministic result. Nothing here modifies or deletes source data.
"""
import argparse, json, os, random, statistics as st, subprocess, sys, time, urllib.request, urllib.error
import psutil

ROOT = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
SRC = f"{ROOT}/04_data_and_memory/lora_datasets/movesense_readiness_continuous.jsonl"
OUT_DIR = f"{ROOT}/04_data_and_memory/audit"
HISTORY = f"{OUT_DIR}/artifact_audit_history.jsonl"
OBSIDIAN = f"{ROOT}/obsidian_vault/APPS_AND_FEATURES/MOVESENSE_ARTIFACT_AUDIT_LATEST.md"
MEDGEMMA = f"{ROOT}/02_ai_models_and_inference/models/biomedical/MedGemma-4B-ECG.Q4_K_M.gguf"

TAIL_BYTES = 30_000_000          # audit the most recent ~30 MB only (keeps RAM/disk light)
WINDOW_BEATS = 30
RR_MIN, RR_MAX = 300.0, 2000.0   # 30-200 bpm
KAMATH = 0.20                    # beat deviating >20% from local median
MAX_HR_JUMP = 30                 # bpm within ~2 s
STALE_SECONDS = 10               # no new beats for this long while hr_bpm reported
CONST_RUN = 8                    # identical consecutive RR values
MEDICAL_MIN_FREE_GB = 7.5        # 4.8 GB sanctuary + ~2.5 GB model + headroom
FRONTIER_GEMINI = ["models/gemini-3.8-flash-high"]


# ---------------------------------------------------------------- ingest
def load_real_records():
    size = os.path.getsize(SRC)
    recs = []
    with open(SRC, "rb") as f:
        f.seek(max(0, size - TAIL_BYTES))
        if f.tell():
            f.readline()
        for line in f:
            try:
                r = json.loads(line)
                if "distillation_source" in r.get("metadata", {}):
                    continue  # never audit model-written rows as if they were sensor data
                i = json.loads(r.get("input", "{}"))
            except Exception:
                continue
            if "hr_bpm" in i and isinstance(i.get("rr_intervals"), list):
                recs.append({"ts": r.get("metadata", {}).get("timestamp", ""), "hr": i["hr_bpm"],
                             "rr": [float(x) for x in i["rr_intervals"]]})
    return recs


def merge_beats(recs):
    """Collapse sliding-window records into a unique beat stream. Returns beats + diagnostics."""
    beats, owner = [], []          # owner[k] = record index that introduced beat k
    unmatched = stale_recs = dup_recs = 0
    prev = None
    stale_run, max_stale_run, stale_flagged = 0, 0, 0
    for idx, r in enumerate(recs):
        cur = r["rr"]
        if not cur:
            prev = cur
            continue
        new = None
        if prev:
            for s in range(0, len(cur) + 1):
                k = len(cur) - s
                if k == 0:
                    break
                if len(prev) >= k and prev[len(prev) - k:] == cur[:k]:
                    new = cur[k:]
                    break
            if new is None:
                unmatched += 1
                new = cur          # discontinuity: treat the whole window as new, but count it
        else:
            new = cur
        if not new:
            dup_recs += 1
            stale_run += 1
            if stale_run >= STALE_SECONDS:
                stale_flagged += 1
            max_stale_run = max(max_stale_run, stale_run)
        else:
            stale_run = 0
            for b in new:
                beats.append(b)
                owner.append(idx)
        prev = cur
    return beats, owner, {"records": len(recs), "duplicate_records": dup_recs, "window_discontinuities": unmatched,
                          "stale_records_flagged": stale_flagged, "max_stale_run_records": max_stale_run}


# ---------------------------------------------------------------- deterministic layer
def beat_flags(beats):
    flags = [set() for _ in beats]
    for i, b in enumerate(beats):
        if not (RR_MIN <= b <= RR_MAX):
            flags[i].add("rr_out_of_range")
        lo, hi = max(0, i - 4), min(len(beats), i + 5)
        local = [x for j, x in enumerate(beats[lo:hi], lo) if j != i]
        if local:
            med = st.median(local)
            if abs(b - med) / med > KAMATH:
                flags[i].add("ectopic_or_artifact")
    run = 1
    for i in range(1, len(beats)):
        run = run + 1 if beats[i] == beats[i - 1] else 1
        if run >= CONST_RUN:
            for j in range(i - run + 1, i + 1):
                flags[j].add("constant_rr_run")
    return flags


def record_flags(recs):
    c = {"hr_rr_mismatch": 0, "hr_jump": 0, "hr_outside_45_185": 0}
    prev_hr = None
    for r in recs:
        if r["rr"]:
            hr_rr = 60000.0 / st.mean(r["rr"])
            if r["hr"] and abs(hr_rr - r["hr"]) / r["hr"] > 0.15:
                c["hr_rr_mismatch"] += 1
        if prev_hr is not None and abs(r["hr"] - prev_hr) > MAX_HR_JUMP:
            c["hr_jump"] += 1
        if not (45 <= r["hr"] <= 185):
            c["hr_outside_45_185"] += 1
        prev_hr = r["hr"]
    return c


def deterministic_report(recs):
    beats, owner, diag = merge_beats(recs)
    flags = beat_flags(beats)
    counts = {}
    for fs in flags:
        for f in fs:
            counts[f] = counts.get(f, 0) + 1
    clean = sum(1 for fs in flags if not fs)
    rep = {"unique_beats": len(beats),
           "records_per_unique_beat": round(len(recs) / max(1, len(beats)), 2),
           "beat_flag_counts": counts,
           "beat_artifact_rate": round(1 - clean / max(1, len(beats)), 4),
           "record_flag_counts": record_flags(recs), **diag}
    return rep, beats, flags


def sample_windows(beats, flags, n_clean=10, n_flagged=10, seed=None):
    rng = random.Random(seed)
    starts = list(range(0, max(1, len(beats) - WINDOW_BEATS), WINDOW_BEATS))
    clean_w, flag_w = [], []
    for s in starts:
        fl = set().union(*flags[s:s + WINDOW_BEATS]) if flags[s:s + WINDOW_BEATS] else set()
        (flag_w if fl else clean_w).append((s, sorted(fl)))
    rng.shuffle(clean_w); rng.shuffle(flag_w)
    out = []
    for kind, pool, n in (("passed_all_checks", clean_w, n_clean), ("flagged", flag_w, n_flagged)):
        for s, fl in pool[:n]:
            out.append({"id": f"{kind[:1]}{s}", "group": kind, "deterministic_flags": fl,
                        "rr_ms": [round(x, 1) for x in beats[s:s + WINDOW_BEATS]]})
    rng.shuffle(out)
    return out


# ---------------------------------------------------------------- LLM layer
PROMPT = """You are reviewing real RR-interval windows (milliseconds, consecutive heartbeats) from a chest/bicep
Movesense sensor for NON-PHYSIOLOGICAL ARTIFACT (missed/extra beats, motion noise, stuck/latched values,
impossible rate changes, quantisation replay). You cannot know ground truth; judge plausibility only.
For EACH window return: id, verdict ("physiological" | "artifact" | "uncertain"), reason (<=12 words).
Also return "filter_gaps": up to 3 short strings naming artifact patterns a simple rule-based filter would miss.
Reply with ONLY JSON: {"windows":[{"id":..,"verdict":..,"reason":..}], "filter_gaps":[..]}

WINDOWS:
"""


def _payload(windows, with_flags=False):
    slim = [{"id": w["id"], "rr_ms": w["rr_ms"]} for w in windows]   # blind: do not leak deterministic flags
    return PROMPT + json.dumps(slim)


def _parse(text):
    s, e = text.find("{"), text.rfind("}")
    return json.loads(text[s:e + 1])


def review_gemini(windows):
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return {"status": "skipped", "reason": "GEMINI_API_KEY missing"}
    for m in FRONTIER_GEMINI:
        body = {"contents": [{"parts": [{"text": _payload(windows)}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}}
        req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/{m}:generateContent?key={key}",
                                     data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                txt = json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"]
            return {"status": "ok", "model": m, **_parse(txt)}
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 404):
                continue
            return {"status": "error", "model": m, "reason": f"HTTP {e.code}"}
        except Exception as e:
            return {"status": "error", "model": m, "reason": type(e).__name__}
    return {"status": "unavailable", "reason": "all Gemini candidates rate-limited"}


def review_nvidia(windows):
    key = os.environ.get("NVIDIA_API_KEY", "")
    if not key:
        return {"status": "skipped", "reason": "NVIDIA_API_KEY missing"}
    body = {"model": "meta/llama-3.2-11b-vision-instruct", "temperature": 0.1, "max_tokens": 3000,
            "messages": [{"role": "user", "content": _payload(windows)}]}
    req = urllib.request.Request("https://integrate.api.nvidia.com/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            txt = json.loads(r.read())["choices"][0]["message"]["content"]
        return {"status": "ok", "model": "nvidia/llama-3.2-11b-vision-instruct", **_parse(txt)}
    except Exception as e:
        return {"status": "error", "reason": type(e).__name__}


def review_medical(windows):
    sub = windows[:8]                    # small model: fewer windows, tighter output
    prompt = _payload(sub)
    url = os.environ.get("MEDICAL_LLM_URL")        # e.g. http://<L2-or-L3>:8084/v1/chat/completions
    if url:
        try:
            body = {"messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "max_tokens": 1200}
            req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                txt = json.loads(r.read())["choices"][0]["message"]["content"]
            return {"status": "ok", "model": f"remote:{url}", "windows_reviewed": len(sub), **_parse(txt)}
        except Exception as e:
            return {"status": "error", "reason": f"remote {type(e).__name__}"}
    free_gb = psutil.virtual_memory().available / 1024 ** 3
    if free_gb < MEDICAL_MIN_FREE_GB:
        return {"status": "deferred_ram_gate", "free_gb": round(free_gb, 2), "needed_gb": MEDICAL_MIN_FREE_GB,
                "hint": "set MEDICAL_LLM_URL to a server on L2/L3, or free host RAM"}
    try:
        out = subprocess.run(["llama-cli", "-m", MEDGEMMA, "--single-turn", "-ngl", "99", "-n", "900", "--temp", "0.1",
                              "-p", prompt], capture_output=True, text=True, timeout=300)
        return {"status": "ok", "model": "MedGemma-4B-ECG.Q4_K_M", "windows_reviewed": len(sub), **_parse(out.stdout)}
    except Exception as e:
        return {"status": "error", "reason": type(e).__name__}


def agreement(review, windows):
    """How often a reviewer agrees with the deterministic split (flagged => artifact, passed => physiological)."""
    if review.get("status") != "ok":
        return None
    truth = {w["id"]: w for w in windows}
    agree = n = missed = 0
    for v in review.get("windows", []):
        w = truth.get(v.get("id"))
        if not w or v.get("verdict") == "uncertain":
            continue
        n += 1
        det_art = w["group"] == "flagged"
        llm_art = v["verdict"] == "artifact"
        agree += det_art == llm_art
        if w["group"] == "passed_all_checks" and llm_art:
            missed += 1
    return {"compared": n, "agree": agree, "llm_flags_passed_window": missed}


# ---------------------------------------------------------------- run
def run_once(seed=None, skip_llm=False):
    t0 = time.time()
    recs = load_real_records()
    det, beats, flags = deterministic_report(recs)
    windows = sample_windows(beats, flags, seed=seed)
    result = {"time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "deterministic": det,
              "sampled_windows": len(windows)}
    if not skip_llm and windows:
        g, n = review_gemini(windows), review_nvidia(windows)
        m = review_medical(windows)
        for name, rv in (("gemini", g), ("nvidia", n), ("medical_local", m)):
            result[name] = {k: v for k, v in rv.items() if k != "windows"}
            result[name]["agreement_with_deterministic"] = agreement(rv, windows)
            result[name]["per_window"] = rv.get("windows", [])
        result["windows"] = windows
    result["elapsed_s"] = round(time.time() - t0, 1)
    os.makedirs(OUT_DIR, exist_ok=True)
    slim = {k: v for k, v in result.items() if k != "windows"}
    for k in ("gemini", "nvidia", "medical_local"):
        if k in slim:
            slim[k] = {a: b for a, b in slim[k].items() if a != "per_window"}
    with open(HISTORY, "a") as f:
        f.write(json.dumps(slim) + "\n")
    with open(f"{OUT_DIR}/artifact_audit_latest.json", "w") as f:
        json.dump(result, f, indent=1)
    write_obsidian(result)
    return result


def write_obsidian(r):
    d = r["deterministic"]
    lines = ["---", 'title: "Movesense Artifact Audit (latest)"', "tags: [movesense, audit, rule0]", f'updated: "{r["time_utc"]}"', "---",
             "# Movesense Artifact Audit", "", "Deterministic layer is authoritative; LLM layers are advisory plausibility reviews.", "",
             f"- Records scanned: **{d['records']:,}** -> unique beats: **{d['unique_beats']:,}** ({d['records_per_unique_beat']} records/beat)",
             f"- Beat artifact rate: **{d['beat_artifact_rate']*100:.2f}%**", f"- Beat flags: `{d['beat_flag_counts']}`",
             f"- Record flags: `{d['record_flag_counts']}`",
             f"- Window discontinuities: {d['window_discontinuities']} | stale records: {d['stale_records_flagged']} (max run {d['max_stale_run_records']})", ""]
    for k in ("gemini", "nvidia", "medical_local"):
        if k in r:
            x = r[k]
            lines.append(f"- **{k}**: status `{x.get('status')}` model `{x.get('model','-')}` agreement `{x.get('agreement_with_deterministic')}`")
            if x.get("filter_gaps"):
                lines.append(f"  - filter gaps suggested: {x['filter_gaps']}")
    os.makedirs(os.path.dirname(OBSIDIAN), exist_ok=True)
    with open(OBSIDIAN, "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--interval", type=int, default=1800, help="seconds between audits in loop mode")
    a = ap.parse_args()
    if a.once:
        res = run_once(skip_llm=a.no_llm)
        print(json.dumps({k: v for k, v in res.items() if k not in ("windows",)}, indent=1)[:6000])
        sys.exit(0)
    while True:
        try:
            if psutil.virtual_memory().available / 1024 ** 3 >= 1.5:
                r = run_once()
                print(time.strftime("%H:%M:%S"), "audit ok; beat artifact rate", r["deterministic"]["beat_artifact_rate"], flush=True)
        except Exception as e:
            print("audit error:", type(e).__name__, e, flush=True)
        time.sleep(a.interval)
