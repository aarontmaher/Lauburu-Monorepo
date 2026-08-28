import re
import math
import numpy as np

# 1. Read LAUBURU_APP_ECOSYSTEM.md
path = '/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/reconnect_project/LAUBURU_APP_ECOSYSTEM.md'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

print(f"Total characters: {len(text)}")
print(f"Total lines: {len(text.splitlines())}")

# Extract Mermaid blocks safely
mermaid_blocks = re.findall(r'```mermaid\n(.*?)```', text, re.DOTALL)
print(f"Number of Mermaid blocks: {len(mermaid_blocks)}")

for i, block in enumerate(mermaid_blocks, 1):
    print(f"\n--- Mermaid Block {i} ({len(block.strip().splitlines())} lines) ---")
    print(block.strip()[:120] + "...")

