with open("tui/services/inference_router.py", "r") as f:
    content = f.read()

content = content.replace("default_engine: str = \"llama_rpc\",", "default_engine: str = \"gemini\",")
with open("tui/services/inference_router.py", "w") as f:
    f.write(content)
