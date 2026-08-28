import re
with open("tui/services/inference_bridges/gemini_bridge.py", "r") as f:
    content = f.read()

content = content.replace("    @property\n    def is_connected(self) -> bool:\n", "    def is_connected(self) -> bool:\n")
with open("tui/services/inference_bridges/gemini_bridge.py", "w") as f:
    f.write(content)
