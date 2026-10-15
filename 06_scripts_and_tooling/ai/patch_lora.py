import re

file_path = "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/ai/frontier_swarm_consensus.py"
with open(file_path, "r") as f:
    content = f.read()

replacement = """        f.write(json.dumps({
            "instruction": f"Frontier Swarm Consensus Task: {task}",
            "input": "\\n".join([f"[{m}]: {str(r)[:500]}" for m, r in responses.items()]),
            "output": consensus_synthesis,
            "metadata": metadata,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sha256": entry_sha256,
            "source": "frontier_swarm_consensus"
        }) + "\\n")"""

content = re.sub(r'        f\.write\(json\.dumps\(\{\n\s+"instruction": f"Frontier Swarm Consensus Task: \{task\}",\n\s+"input": "\\n"\.join\(\[f"\[\{m\}\]: \{str\(r\)\[:500\]\}" for m, r in responses\.items\(\)\]\),\n\s+"output": consensus_synthesis,\n\s+"timestamp": datetime\.now\(timezone\.utc\)\.isoformat\(\),\n\s+"sha256": entry_sha256,\n\s+"source": "frontier_swarm_consensus"\n\s+\}\) \+ "\\n"\)', replacement, content)

with open(file_path, "w") as f:
    f.write(content)
print("Patched save_to_lora")
