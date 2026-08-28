import re
with open("tui/services/inference_router.py", "r") as f:
    content = f.read()

content = content.replace("    from services.inference_bridges.petals_bridge import PetalsInferenceBridge", "    from services.inference_bridges.petals_bridge import PetalsInferenceBridge\n    from services.inference_bridges.gemini_bridge import GeminiBridge")
with open("tui/services/inference_router.py", "w") as f:
    f.write(content)
