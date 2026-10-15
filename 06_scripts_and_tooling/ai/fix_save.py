import re

with open('frontier_swarm_consensus.py', 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if 'def save_to_lora' in line:
        skip = True
        new_lines.append(line)
        new_lines.append('    """Serialize full consensus deliberation to PySpark/LoRA data lake with valid SHA256 checksum."""\n')
        new_lines.append('    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)\n')
        new_lines.append('    entry = {\n')
        new_lines.append('        "timestamp": datetime.now(timezone.utc).isoformat(),\n')
        new_lines.append('        "task": task,\n')
        new_lines.append('        "responses": responses,\n')
        new_lines.append('        "consensus_synthesis": consensus_synthesis,\n')
        new_lines.append('        "verified": True\n')
        new_lines.append('    }\n')
        new_lines.append('    if metadata:\n')
        new_lines.append('        entry.update(metadata)\n')
        new_lines.append('    payload_str = json.dumps(entry, sort_keys=True)\n')
        new_lines.append('    entry_sha256 = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()\n')
        new_lines.append('    entry["sha256"] = entry_sha256\n')
        new_lines.append('    with open(DATASET_PATH, "a") as f:\n')
        new_lines.append('        f.write(json.dumps(entry) + "\\n")\n')
        new_lines.append('    print(f"[+] Appended consensus trajectory to {DATASET_PATH} (SHA256: {entry_sha256[:16]}...)")\n')
        new_lines.append('    CONTINUOUS_LORA_PATH.parent.mkdir(parents=True, exist_ok=True)\n')
        new_lines.append('    with open(CONTINUOUS_LORA_PATH, "a") as f:\n')
        new_lines.append('        f.write(json.dumps({\n')
        new_lines.append('            "instruction": f"Frontier Swarm Consensus Task: {task}",\n')
        new_lines.append('            "input": "\\n".join([f"[{m}]: {str(r)[:500]}" for m, r in responses.items()]),\n')
        new_lines.append('            "output": consensus_synthesis,\n')
        new_lines.append('            "metadata": metadata,\n')
        new_lines.append('            "timestamp": datetime.now(timezone.utc).isoformat(),\n')
        new_lines.append('            "sha256": entry_sha256,\n')
        new_lines.append('            "source": "frontier_swarm_consensus"\n')
        new_lines.append('        }) + "\\n")\n')
        new_lines.append('    print(f"[+] Appended training pair to {CONTINUOUS_LORA_PATH}")\n')
        new_lines.append('    return entry_sha256\n')
    elif 'def execute_load_balancing_consensus' in line:
        skip = False
        new_lines.append(line)
    elif not skip:
        new_lines.append(line)

with open('frontier_swarm_consensus.py', 'w') as f:
    f.writelines(new_lines)
