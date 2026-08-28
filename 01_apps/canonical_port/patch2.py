import re
with open("tui/services/inference_router.py", "r") as f:
    content = f.read()

replacement = """                "gemini": GeminiBridge(),
            }"""

content = re.sub(r'                "petals": PetalsInferenceBridge\([^)]+\),\s+\}', replacement, content, flags=re.DOTALL)
with open("tui/services/inference_router.py", "w") as f:
    f.write(content)
