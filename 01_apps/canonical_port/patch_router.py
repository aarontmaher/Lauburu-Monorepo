import re

with open("tui/services/inference_router.py", "r") as f:
    content = f.read()

# Add import
content = content.replace(
    "from tui.services.inference_bridges.petals_bridge import PetalsInferenceBridge",
    "from tui.services.inference_bridges.petals_bridge import PetalsInferenceBridge\n    from tui.services.inference_bridges.gemini_bridge import GeminiBridge"
)

# Add GeminiBridge to self.bridges
new_bridges_dict = """            self.bridges = {
                "llama_rpc": LlamaRpcInferenceBridge(
                    s2s_client=self.s2s_client,
                    voice_io_manager=self.voice_io_manager,
                    on_token=self._wrap_on_token,
                    on_complete=self._wrap_on_complete,
                    on_code_snippet=self._wrap_on_code_snippet,
                    on_error=self._wrap_on_error,
                ),
                "exo": ExoInferenceBridge(
                    s2s_client=self.s2s_client,
                    voice_io_manager=self.voice_io_manager,
                    on_token=self._wrap_on_token,
                    on_complete=self._wrap_on_complete,
                    on_code_snippet=self._wrap_on_code_snippet,
                    on_error=self._wrap_on_error,
                ),
                "accelerate": AccelerateInferenceBridge(
                    s2s_client=self.s2s_client,
                    voice_io_manager=self.voice_io_manager,
                    on_token=self._wrap_on_token,
                    on_complete=self._wrap_on_complete,
                    on_code_snippet=self._wrap_on_code_snippet,
                    on_error=self._wrap_on_error,
                ),
                "petals": PetalsInferenceBridge(
                    s2s_client=self.s2s_client,
                    voice_io_manager=self.voice_io_manager,
                    on_token=self._wrap_on_token,
                    on_complete=self._wrap_on_complete,
                    on_code_snippet=self._wrap_on_code_snippet,
                    on_error=self._wrap_on_error,
                ),
                "gemini": GeminiBridge(),
            }"""
            
content = re.sub(r'            self.bridges = \{\s+"llama_rpc": LlamaRpcInferenceBridge\(.*?\),\s+\}', new_bridges_dict, content, flags=re.DOTALL)

# Add "gemini" to SUPPORTED_ENGINES
content = content.replace(
    'SUPPORTED_ENGINES = {"auto", "llama_rpc", "exo", "accelerate", "petals"}',
    'SUPPORTED_ENGINES = {"auto", "llama_rpc", "exo", "accelerate", "petals", "gemini"}'
)

with open("tui/services/inference_router.py", "w") as f:
    f.write(content)

