import sys

file_path = "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/screen_life_companion.py"
with open(file_path, "r") as f:
    lines = f.readlines()

out = []
skip = False
for line in lines:
    if "prompt = (" in line and "Analyze these screen captures." in lines[lines.index(line)+1]:
        skip = True
        out.append("                prompt = (\\n")
        out.append("                    \\\"Analyze these screen captures. Track and differentiate between HUMAN activity (manual typing, UI clicking) \\\"\\n")
        out.append("                    \\\"and AI activity (terminal swarms, code generation, background tasks). \\\\n\\\"\\n")
        out.append("                    \\\"Based on this telemetry, determine actionable 'things to do' and structure them as an ROI (Return on Investment) list. \\\"\\n")
        out.append("                    \\\"High ROI tasks are those where AI can automate a tedious human task, or where human intervention unblocks a stalled AI swarm.\\\\n\\\"\\n")
        out.append("                    f\\\"Data:\\\\n{batch_text}\\\\n\\\"\\n")
        out.append("                    \\\"Output a strict JSON array of objects with keys: 'category' (todo|roi_insight), \\\"\\n")
        out.append("                    \\\"'content' (The actionable task, MUST be prefixed with [ROI: XX/100]), \\\"\\n")
        out.append("                    \\\"'context' (Explain why this has high/low ROI and assign to Human or AI), \\\"\\n")
        out.append("                    \\\"'importance' (urgent|high|normal).\\\"\\n")
        out.append("                )\\n")
    elif skip:
        if "'importance' (urgent|high|normal).\"" in line or "                )" in line:
            if "                )" in line:
                skip = False
    else:
        out.append(line)

with open(file_path, "w") as f:
    for item in out:
        f.write(item.replace("\\n", "\n").replace("\\\"", "\"").replace("\\\\n", "\\n"))
