import sys
from rich.console import Console
from pit_tui import generate_layout, update_ui

console = Console(force_terminal=False, width=120)
layout = generate_layout()
update_ui(layout)
console.print(layout)
