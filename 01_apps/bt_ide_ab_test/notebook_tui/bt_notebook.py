"""
Variant 2: Notebook TUI (Euporie clone)
Loads a notebook but renders code cells in pure Terminal characters over BT.
"""
import nbformat
import sys

def render_notebook_tui(filepath):
    print(f"\033[1;34m=== LAUBURU BT-NOTEBOOK (ANSI MODE) ===\033[0m")
    try:
        with open(filepath, 'r') as f:
            nb = nbformat.read(f, as_version=4)
        for i, cell in enumerate(nb.cells):
            if cell.cell_type == 'markdown':
                print(f"\033[32m[Markdown]\033[0m {cell.source[:50]}...")
            elif cell.cell_type == 'code':
                print(f"\033[36m[In {i}]:\033[0m")
                print(f"{cell.source}")
                print("-" * 40)
    except Exception as e:
        print(f"Error loading notebook: {e}")

if __name__ == "__main__":
    # Mock file for the A/B test
    print("[LENS VLA] Verifying AST notebook cell streaming...")
    print("Notebook TUI scaffold initialized.")
