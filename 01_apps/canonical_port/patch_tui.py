import re

with open("tui/screens/agi_coding_terminal_screen.py", "r") as f:
    content = f.read()

replacement = """        elif command == "/clear":
            self.terminal.clear()

        elif command.startswith("/key "):
            import os
            key = command.split(" ", 1)[1].strip()
            os.environ["GEMINI_API_KEY"] = key
            self._log_terminal("[bold green]SYSTEM:[/bold green] GEMINI_API_KEY loaded successfully.")
"""

content = content.replace("        elif command == \"/clear\":\n            self.terminal.clear()", replacement)

with open("tui/screens/agi_coding_terminal_screen.py", "w") as f:
    f.write(content)
