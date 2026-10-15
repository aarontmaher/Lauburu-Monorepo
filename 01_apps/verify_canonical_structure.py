import os
import shutil
from pathlib import Path

APPS_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps")

def verify_and_restructure():
    restructured = 0
    for item in APPS_DIR.iterdir():
        if item.is_dir() and not item.name.startswith(('.', '__')):
            # Check for required directories
            src_dir = item / "src"
            assets_dir = item / "assets"
            docs_dir = item / "docs"
            tests_dir = item / "tests"
            
            created_any = False
            for directory in [src_dir, assets_dir, docs_dir, tests_dir]:
                if not directory.exists():
                    directory.mkdir(parents=True)
                    created_any = True
            
            # Sub-directories inside src
            for subdir in ["ui", "state", "ai_bindings", "network"]:
                sub_path = src_dir / subdir
                if not sub_path.exists():
                    sub_path.mkdir(parents=True)
                    created_any = True

            if created_any:
                print(f"Created canonical structure for {item.name}")
                restructured += 1
                
    print(f"Restructured {restructured} apps to match Canonical Structure.")

if __name__ == "__main__":
    verify_and_restructure()
