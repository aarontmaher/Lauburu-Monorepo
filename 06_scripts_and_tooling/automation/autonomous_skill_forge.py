#!/usr/bin/env python3
import sys
import os
import argparse

print("=====================================================")
print("🛠️ Lauburu Autonomous AI Skill Forge")
print("=====================================================")

def forge_skill(skill_name, description, python_code):
    skill_dir = f"/Volumes/Lauburu-Monorepo/.agents/skills/{skill_name}"
    
    if os.path.exists(skill_dir):
        print(f"[!] Skill '{skill_name}' already exists. Updating...")
    else:
        print(f"[+] Forging new specialist skill directory: {skill_dir}")
        os.makedirs(skill_dir, exist_ok=True)
        os.makedirs(f"{skill_dir}/scripts", exist_ok=True)
        
    skill_md = f"""---
name: {skill_name}
description: {description}
---

# 🤖 Autonomous Specialist: {skill_name}

This skill was autonomously forged by the Local AI Swarm to handle repetitive, high-value e-commerce tasks.

## Core Execution
To execute this skill, run the associated python script:
`python3 {skill_dir}/scripts/execute.py`

## Instructions
1. This specialist has zero-mock verification built in.
2. It is bound by the ELO Economy limits.
"""
    
    with open(f"{skill_dir}/SKILL.md", "w") as f:
        f.write(skill_md)
        
    with open(f"{skill_dir}/scripts/execute.py", "w") as f:
        f.write(python_code)
    
    os.chmod(f"{skill_dir}/scripts/execute.py", 0o755)
        
    print(f"[+] Skill {skill_name} successfully compiled and integrated into the Lauburu Mesh.")
    print("    -> Local AIs can now invoke this via standard Swarm tooling.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: autonomous_skill_forge.py \"skill-name\" \"Description...\" \"print('Hello World')\"")
        sys.exit(1)
        
    forge_skill(sys.argv[1], sys.argv[2], sys.argv[3])
