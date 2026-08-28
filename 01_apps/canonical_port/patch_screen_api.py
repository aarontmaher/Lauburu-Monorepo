with open("tui/screens/agi_coding_terminal_screen.py", "r") as f:
    content = f.read()

# Add to badge maps
content = content.replace("\"gemini\": \"GEMINI\",", "\"gemini\": \"GEMINI\",\n                    \"cloudflare\": \"CLOUDFLARE\",\n                    \"julien\": \"JULIEN\",")
content = content.replace("\"gemini\": (\"[GEMINI: ACTIVE]\", \"bold blue\"),", "\"gemini\": (\"[GEMINI: ACTIVE]\", \"bold blue\"),\n                    \"cloudflare\": (\"[CLOUDFLARE: ACTIVE]\", \"bold orange3\"),\n                    \"julien\": (\"[JULIEN: ACTIVE]\", \"bold magenta\"),")

# Add API Key commands
key_logic = """
        elif cmd_name == "/key":
            if len(parts) > 1:
                os.environ["GEMINI_API_KEY"] = parts[1]
                self._log_terminal("SYSTEM: GEMINI_API_KEY loaded successfully.")
            else:
                self._log_terminal("Usage: /key <your_api_key>")
        elif cmd_name == "/key_cf":
            if len(parts) > 1:
                os.environ["CLOUDFLARE_API_KEY"] = parts[1]
                self._log_terminal("SYSTEM: CLOUDFLARE_API_KEY loaded successfully.")
            else:
                self._log_terminal("Usage: /key_cf <your_api_key>")
        elif cmd_name == "/account_cf":
            if len(parts) > 1:
                os.environ["CLOUDFLARE_ACCOUNT_ID"] = parts[1]
                self._log_terminal("SYSTEM: CLOUDFLARE_ACCOUNT_ID loaded successfully.")
            else:
                self._log_terminal("Usage: /account_cf <your_account_id>")
        elif cmd_name == "/key_julien":
            if len(parts) > 1:
                os.environ["JULIEN_API_KEY"] = parts[1]
                self._log_terminal("SYSTEM: JULIEN_API_KEY loaded successfully.")
            else:
                self._log_terminal("Usage: /key_julien <your_api_key>")"""

import re
content = re.sub(
    r"\n\s+elif cmd_name == \"/key\":.*?self\._log_terminal\(\"Usage: /key <your_api_key>\"\)",
    key_logic,
    content,
    flags=re.DOTALL
)

with open("tui/screens/agi_coding_terminal_screen.py", "w") as f:
    f.write(content)
