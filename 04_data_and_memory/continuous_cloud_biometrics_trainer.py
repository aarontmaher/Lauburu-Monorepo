#!/Users/aaron/ai_training_venv/bin/python3
"""
Continuous Cloud Interpretation Trainer v2 (real beats only)
============================================================
Replaces v1, which synthesised RR/ECG from HR and wrote model output back into the sensor source file.

  * Input: unique beats merged from the real Movesense stream (movesense_artifact_auditor.merge_beats).
  * Window: 150 beats; skipped if ANY beat fails the auditor's deterministic checks.
  * Metrics computed locally: mean HR, RMSSD, SDNN, DFA-alpha1 (scales 4-16). No other physiology is invented.
  * Cloud model (Gemini chain, NVIDIA NIM fallback) is asked for interpretation + caveats only.
  * Output: lora_datasets/cloud_interpretation_pairs.jsonl (never the sensor source file).
  * Gates: host RAM >= 3.0 GB, >= 120 s between windows, read-only on source.
"""
import argparse, json, os, sys, time, calendar, urllib.request, urllib.error
import numpy as np, psutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import movesense_artifact_auditor as A

A.TAIL_BYTES = 6_000_000
OUT = f"{A.ROOT}/04_data_and_memory/lora_datasets/cloud_interpretation_pairs.jsonl"
STATE = f"{A.OUT_DIR}/trainer_state.json"
LOG = f"{A.ROOT}/04_data_and_memory/cloud_trainer.log"
WIN, MIN_GAP_S, MIN_RAM_GB = 150, 120, 3.0


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [TrainerV2] {msg}"
    print(line, flush=True)
    try:
        if os.path.exists(LOG) and os.path.getsize(LOG) > 2_000_000:
            os.replace(LOG, LOG + ".bak")
        with open(LOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def dfa_alpha1(rr):
    x = np.asarray(rr, float)
    y = np.cumsum(x - x.mean())
    scales, fl = [], []
    for s in range(4, 17):
        n = len(y) // s
        if n < 2:
            continue
        t = np.arange(s)
        res = []
        for k in range(n):
            seg = y[k * s:(k + 1) * s]
            res.append(np.mean((seg - np.polyval(np.polyfit(t, seg, 1), t)) ** 2))
        scales.append(s)
        fl.append(np.sqrt(np.mean(res)))
    if len(scales) < 6:
        return None
    return round(float(np.polyfit(np.log(scales), np.log(fl), 1)[0]), 3)


def metrics(w):
    d = np.diff(w)
    return {"beats": len(w), "mean_hr_bpm": round(60000 / float(np.mean(w)), 1), "rmssd_ms": round(float(np.sqrt(np.mean(d ** 2))), 1),
            "sdnn_ms": round(float(np.std(w, ddof=1)), 1), "dfa_alpha1": dfa_alpha1(w)}


def epoch(ts):
    return calendar.timegm(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ"))


def ask_cloud(prompt):
    key = os.environ.get("GEMINI_API_KEY", "")
    for m in A.FRONTIER_GEMINI if key else []:
        body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}
        req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/{m}:generateContent?key={key}",
                                     data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return m, json.loads(json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"])
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 404):
                continue
        except Exception:
            continue
    nk = os.environ.get("NVIDIA_API_KEY", "")
    if nk:
        body = {"model": "meta/llama-3.2-11b-vision-instruct", "temperature": 0.2, "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}]}
        req = urllib.request.Request("https://integrate.api.nvidia.com/v1/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {nk}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return "nvidia/llama-3.2-11b-vision-instruct", A._parse(json.loads(r.read())["choices"][0]["message"]["content"])
        except Exception:
            pass
    return None, None


def step(force=False):
    if psutil.virtual_memory().available / 1024 ** 3 < MIN_RAM_GB:
        return "ram_gate"
    recs = A.load_real_records()
    beats, owner, _ = A.merge_beats(recs)
    if len(beats) < WIN:
        return "not_enough_beats"
    w = beats[-WIN:]
    if any(A.beat_flags(w)):
        return "skipped_flagged_window"
    end_ts = recs[owner[-1]]["ts"]
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    if not force and state.get("last_end_ts") and epoch(end_ts) - epoch(state["last_end_ts"]) < MIN_GAP_S:
        return "waiting_gap"
    m = metrics(w)
    prompt = ("These are locally computed HRV metrics from a REAL 150-beat chest-strap window. Interpret them for an athlete. "
              "Do NOT invent blood pressure, sleep, VO2max or any value not given. DFA-alpha1 thresholds (~0.75 LT1, ~0.5 LT2) are "
              "approximate and individual; say so. Reply ONLY JSON: {\"interpretation\":str,\"confidence\":\"low|medium|high\",\"caveats\":str}\n"
              + json.dumps(m))
    model, out = ask_cloud(prompt)
    if not out:
        return "cloud_unavailable"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "a") as f:
        f.write(json.dumps({"instruction": "Interpret these real 150-beat HRV metrics; do not invent unmeasured physiology.",
                            "input": json.dumps(m), "output": json.dumps(out),
                            "metadata": {"data_origin": "real_sensor", "window_end_ts": end_ts, "reviewer_model": model}}) + "\n")
    os.makedirs(A.OUT_DIR, exist_ok=True)
    json.dump({"last_end_ts": end_ts}, open(STATE, "w"))
    log(f"pair written via {model}: {m}")
    return "written"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    if a.once:
        print(step(force=True))
        sys.exit(0)
    while True:
        try:
            r = step()
            if r not in ("written", "waiting_gap"):
                log(f"cycle: {r}")
        except Exception as e:
            log(f"error: {type(e).__name__}: {e}")
        time.sleep(60)
