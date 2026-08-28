import re

with open('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/reconnect_project/LAUBURU_APP_ECOSYSTEM.md', 'r') as f:
    content = f.read()

mermaid_blocks = re.findall(r'```mermaid\s*(.*?)\s*```', content, re.DOTALL)
print(f"Found {len(mermaid_blocks)} Mermaid blocks.")

for i, block in enumerate(mermaid_blocks, 1):
    print(f"\n--- Mermaid Diagram #{i} ---")
    lines = block.strip().splitlines()
    print(f"Header: {lines[0]}")
    print(f"Line count: {len(lines)}")
    
    # Check basic structure
    first_line = lines[0].strip()
    assert first_line in ["sequenceDiagram", "graph TD", "flowchart TD", "graph TB", "flowchart TB", "graph LR"], f"Invalid diagram type: {first_line}"
    
    # Check open/close brackets balance
    open_curly = block.count('{')
    close_curly = block.count('}')
    open_sq = block.count('[')
    close_sq = block.count(']')
    open_paren = block.count('(')
    close_paren = block.count(')')
    
    print(f"Curly: {open_curly} vs {close_curly} | Square: {open_sq} vs {close_sq} | Paren: {open_paren} vs {close_paren}")
    assert open_curly == close_curly, f"Mismatched curly braces in diagram {i}"
    assert open_sq == close_sq, f"Mismatched square brackets in diagram {i}"
    assert open_paren == close_paren, f"Mismatched parentheses in diagram {i}"
    print("Syntax verification: VALID")

print("\nALL MERMAID BLOCKS VALIDATED SUCCESSFULLY!")
