with open("tui/screens/agi_coding_terminal_screen.py", "r") as f:
    content = f.read()

content = content.replace("default_engine=\"llama_rpc\"", "default_engine=\"gemini\"")
with open("tui/screens/agi_coding_terminal_screen.py", "w") as f:
    f.write(content)
