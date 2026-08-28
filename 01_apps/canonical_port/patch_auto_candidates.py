with open("tui/services/inference_router.py", "r") as f:
    content = f.read()

content = content.replace(
    'candidates=["llama_rpc", "exo", "accelerate", "petals"]',
    'candidates=["llama_rpc", "exo", "accelerate", "petals", "gemini", "cloudflare", "julien"]'
)

with open("tui/services/inference_router.py", "w") as f:
    f.write(content)
