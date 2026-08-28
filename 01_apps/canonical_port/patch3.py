import re
with open("tui/services/inference_bridges/gemini_bridge.py", "r") as f:
    content = f.read()

replacement = """    @property
    def is_connected(self) -> bool:
        return self._connected
"""

content = content.replace("    def get_display_name(self) -> str:\n        return f\"Gemini ({self.model_name})\"", "    def get_display_name(self) -> str:\n        return f\"Gemini ({self.model_name})\"\n\n" + replacement)
with open("tui/services/inference_bridges/gemini_bridge.py", "w") as f:
    f.write(content)
