with open("tui/services/inference_router.py", "r") as f:
    content = f.read()

content = content.replace("    from services.inference_bridges.gemini_bridge import GeminiBridge", "    from services.inference_bridges.gemini_bridge import GeminiBridge\n    from services.inference_bridges.cloudflare_bridge import CloudflareBridge\n    from services.inference_bridges.julien_bridge import JulienBridge")

content = content.replace("                    \"gemini\": GeminiBridge(),", "                    \"gemini\": GeminiBridge(),\n                    \"cloudflare\": CloudflareBridge(),\n                    \"julien\": JulienBridge(),")

content = content.replace("SUPPORTED_ENGINES = {\"auto\", \"llama_rpc\", \"exo\", \"accelerate\", \"petals\", \"gemini\"}", "SUPPORTED_ENGINES = {\"auto\", \"llama_rpc\", \"exo\", \"accelerate\", \"petals\", \"gemini\", \"cloudflare\", \"julien\"}")

with open("tui/services/inference_router.py", "w") as f:
    f.write(content)
