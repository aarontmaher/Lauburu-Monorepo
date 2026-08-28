import re

with open("tui/models/blackboard_models.py", "r") as f:
    content = f.read()

replacement = """        llama_rpc_nodes = [
            LlamaRpcNode(node_name="Linux Head Node", endpoint="100.101.39.98:50052", layers_sharded=28, vram_used_gb=13.5, status="ONLINE", latency_ms=1.20),
            LlamaRpcNode(node_name="MacBook Pro", endpoint="169.254.187.138:50052", layers_sharded=28, vram_used_gb=13.5, status="ONLINE", latency_ms=0.28),
            LlamaRpcNode(node_name="Mac Mini Host", endpoint="127.0.0.1:50052", layers_sharded=24, vram_used_gb=12.0, status="ONLINE", latency_ms=0.05),
            LlamaRpcNode(node_name="MacBook Air", endpoint="100.93.158.96:50052", layers_sharded=0, vram_used_gb=0.0, status="STANDBY", latency_ms=0.35),
            LlamaRpcNode(node_name="Linux Tablet", endpoint="100.81.92.125:50052", layers_sharded=0, vram_used_gb=0.0, status="STANDBY", latency_ms=2.1),
            LlamaRpcNode(node_name="Pixel 10 Pro XL", endpoint="100.73.38.87:50052", layers_sharded=0, vram_used_gb=0.0, status="STANDBY", latency_ms=4.5)
        ]"""

content = re.sub(
    r"        llama_rpc_nodes = \[\n.*?LlamaRpcNode\(node_name=\"Mac Mini Host\".*?\n        \]",
    replacement,
    content,
    flags=re.DOTALL
)

with open("tui/models/blackboard_models.py", "w") as f:
    f.write(content)
