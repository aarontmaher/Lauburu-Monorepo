import re
with open("tui/screens/agi_coding_terminal_screen.py", "r") as f:
    content = f.read()

content = content.replace("\"petals\": \"PETALS\",", "\"petals\": \"PETALS\",\n                    \"gemini\": \"GEMINI\",")
content = content.replace("\"petals\": (\"[PETALS: ACTIVE]\", \"bold green\"),", "\"petals\": (\"[PETALS: ACTIVE]\", \"bold green\"),\n                    \"gemini\": (\"[GEMINI: ACTIVE]\", \"bold blue\"),")

with open("tui/screens/agi_coding_terminal_screen.py", "w") as f:
    f.write(content)
