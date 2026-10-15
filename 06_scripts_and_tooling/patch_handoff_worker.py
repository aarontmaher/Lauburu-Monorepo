import sys

file_path = "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/bt_ai_handoff_worker.py"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace("escalate_to_neo", "escalate_to_gemini_teacher")
content = content.replace("Escalating task to Cloud (Neo) due to local complexity...", "Escalating task to Gemini 3.8 Flash (Teacher Role) due to local complexity...")
content = content.replace("dispatched to Neo Cloud.", "dispatched to Gemini Teacher.")
content = content.replace("NEO_URL =", "GEMINI_URL =")

with open(file_path, "w") as f:
    f.write(content)

print("Handoff worker patched!")
