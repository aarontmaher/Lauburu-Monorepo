import re
with open("tui/screens/agi_coding_terminal_screen.py", "r") as f:
    content = f.read()

gateway_logic = """        elif cmd_name == "/gateway_cf":
            if len(parts) > 1:
                os.environ["CLOUDFLARE_GATEWAY_ID"] = parts[1]
                self._log_terminal("SYSTEM: CLOUDFLARE_GATEWAY_ID loaded. All AI traffic will now route through Cloudflare AI Gateway.")
            else:
                self._log_terminal("Usage: /gateway_cf <your_gateway_id>")
        elif cmd_name == "/key_julien":"""

content = content.replace("        elif cmd_name == \"/key_julien\":", gateway_logic)

with open("tui/screens/agi_coding_terminal_screen.py", "w") as f:
    f.write(content)
