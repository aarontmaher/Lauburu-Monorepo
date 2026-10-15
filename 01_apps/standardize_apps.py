import os
from pathlib import Path

APPS_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps")
OBSIDIAN_LINK = "[[CANONICAL_APP_UI_AND_STRUCTURE_RULE]]"

STANDARD_README = f"""# {{app_name}}

## Overview
Part of the Lauburu AI Mesh ecosystem.

## Canonical Architecture & UI
This application strictly adheres to the visual design language and directory structure defined in {OBSIDIAN_LINK}. 
Its visual layout and accessibility are continuously audited and evolved by the local VL orchestrators under the supervision of the Project Astra Teacher Model via the Screen Lens MCP.

## Structure
- `src/`: Core logic and UI
- `assets/`: Media and design files

*Note: This README is autonomously maintained by the Lauburu Goal agent.*
"""

def standardize():
    count = 0
    for item in APPS_DIR.iterdir():
        if item.is_dir() and not item.name.startswith(('.', '__')):
            # It's an app directory
            readme_path = item / "README.md"
            
            needs_update = False
            if readme_path.exists():
                with open(readme_path, 'r') as f:
                    content = f.read()
                if OBSIDIAN_LINK not in content:
                    needs_update = True
            else:
                needs_update = True
                
            if needs_update:
                print(f"Updating {item.name}")
                # We'll append or create
                if readme_path.exists():
                    with open(readme_path, 'a') as f:
                        f.write(f"\n\n## Canonical Architecture\nThis application adheres to {OBSIDIAN_LINK} and uses the Astra Multimodal Live API via Screen Lens for UI evolution.\n")
                else:
                    with open(readme_path, 'w') as f:
                        f.write(STANDARD_README.format(app_name=item.name))
                count += 1
    print(f"Standardized {count} apps.")

if __name__ == "__main__":
    standardize()
