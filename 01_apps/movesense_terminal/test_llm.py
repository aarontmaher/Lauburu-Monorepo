import sys
import asyncio
from pathlib import Path

async def test_llm():
    model_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/models/biomedical/Meditron3-8B.Q4_K_M.gguf")
    llama_cli = "llama-cli"
    prompt = "Analyze ECG telemetry window (50 samples, recent: [1.0, 2.0]): Assess rhythm, arrhythmia, and signal quality. Clinical Impression:"
    cmd = [
        llama_cli,
        "-m", str(model_path),
        "--single-turn",
        "--simple-io",
        "--no-display-prompt",
        "--log-disable",
        "-ngl", "99",
        "-p", prompt,
        "-n", "96",
        "-c", "512",
        "--temp", "0.2"
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    raw_out = stdout.decode("utf-8", errors="ignore")
    print("--- RAW OUT ---")
    print(raw_out)
    print("---------------")

    if "... (truncated)" in raw_out:
        clean = raw_out.split("... (truncated)", 1)[1]
    elif "> " + prompt in raw_out:
        clean = raw_out.split("> " + prompt, 1)[1]
    elif prompt in raw_out:
        clean = raw_out.split(prompt, 1)[1]
    else:
        idx = raw_out.find("> ")
        if idx != -1:
            after = raw_out[idx + 2:]
            if "Clinical Impression:" in after:
                clean = after.split("Clinical Impression:", 1)[1]
            else:
                clean = after
        else:
            clean = raw_out

    if "... (truncated)" in clean:
        clean = clean.split("... (truncated)", 1)[1]

    lines = []
    for l in clean.splitlines():
        ls = l.strip()
        if ls == "Exiting...":
            break
        if ls.startswith(("build", "model", "modalities", "ftype", "available commands", "/exit", "/regen", "/clear", "/read", "/glob", "Loading model...")):
            continue
        if ls.startswith("▄") or ls.startswith("█") or ls.startswith("▀"):
            continue
        if ls:
            lines.append(ls)

    summary = " | ".join(lines[:2]) if lines else "Normal Sinus Rhythm"
    if len(summary) > 160:
        summary = summary[:157] + "..."
    print("--- SUMMARY ---")
    print(summary)

if __name__ == "__main__":
    asyncio.run(test_llm())
