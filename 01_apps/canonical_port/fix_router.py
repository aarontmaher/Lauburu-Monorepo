import re

with open("tui/services/inference_router.py", "r") as f:
    content = f.read()

# Fix the duplicate "gemini" in lists and dicts
content = re.sub(r'\n\s+"gemini",', '', content)
content = re.sub(r'from tui\.services\.inference_bridges\.gemini_bridge import GeminiBridge\n?', '', content)

# Inject import carefully once
content = content.replace(
    "from tui.services.inference_bridges.petals_bridge import PetalsInferenceBridge",
    "from tui.services.inference_bridges.petals_bridge import PetalsInferenceBridge\n    from tui.services.inference_bridges.gemini_bridge import GeminiBridge"
)

# Replace SUPPORTED_ENGINES
old_supported = """    SUPPORTED_ENGINES: List[str] = [
        "auto",
        "llama_rpc",
        "exo",
        "accelerate",
        "petals",
    ]"""
new_supported = """    SUPPORTED_ENGINES: List[str] = [
        "auto",
        "llama_rpc",
        "exo",
        "accelerate",
        "petals",
        "gemini",
    ]"""
content = content.replace(old_supported, new_supported)

# Inject GeminiBridge into self.bridges
content = re.sub(
    r'("petals": PetalsInferenceBridge\([^)]+\),\s+)\}',
    r'\1    "gemini": GeminiBridge(),\n            }',
    content,
    flags=re.DOTALL
)

with open("tui/services/inference_router.py", "w") as f:
    f.write(content)
